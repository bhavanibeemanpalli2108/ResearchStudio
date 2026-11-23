"""Trusted original-run coordination, opt-in only; never part of native/web dispatch.

Deploy alongside the gateway/backend on one trusted host and local SQLite volume.
The disposable worker receives only a scoped token and authenticated HTTP controls.
No provider client, real-key loader, migration, automatic replay or campaign daemon.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
import time
import threading
from functools import wraps
from typing import Any
from uuid import UUID

from sqlalchemy import select

from .artifacts import ArtifactStore
from .database import Database, Run, Job, Project, GatewayGrant, new_id, as_dict, utcnow
from .experiment_contract import canonical_hash
from .ledger import accounting_lock, refresh_usage, BudgetExceeded
from .model_gateway import issue_grant_locked
from .schemas import Budgets
from .services import record_event, LostLease
from .upstream_execution import UpstreamRunRequest, UpstreamWorkerClient

ARTIFACT_NAMES = {
    "paper.pdf",
    "paper.tex",
    "final_manifest.json",
    "best_program_manifest.json",
    "pipeline_events.jsonl",
}
TERMINAL = {"completed", "completed_degraded", "failed", "cancelled"}


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return call


@dataclass(frozen=True)
class ControllerPolicy:
    enabled: bool = False
    lease_seconds: int = 120
    grant_seconds: int = 300
    output_cap: int = 1024

    def __post_init__(self):
        if (
            not 30 <= self.lease_seconds <= 300
            or not 60 <= self.grant_seconds <= 900
            or not 1 <= self.output_cap <= 4096
        ):
            raise ValueError("Invalid bounded controller policy")


class ScopedSecrets:
    """Trusted-host private escrow; never under downloadable artifact storage."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        if any(p.is_symlink() for p in [self.root, *self.root.parents]):
            raise ValueError("Private secret root cannot contain symlinks")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.root.stat()
        if os.name == "posix" and (
            info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise ValueError("Private owner-only secret root required")

    def path(self, grant_id: str) -> Path:
        if not re.fullmatch("[a-f0-9]{32}", grant_id):
            raise ValueError("Invalid grant identity")
        return self.root / grant_id

    def put(self, grant_id: str, token: str) -> None:
        fd = os.open(self.path(grant_id), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(token)
            output.flush()
            os.fsync(output.fileno())

    def get(self, grant: GatewayGrant) -> str:
        path = self.path(grant.id)
        if path.is_symlink():
            raise ValueError("Unsafe credential file")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or (
                os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077)
            ):
                raise ValueError("Unsafe credential ownership")
            token = stream.read(257)
        if hashlib.sha256(token.encode()).hexdigest() != grant.token_hash:
            raise ValueError("Credential digest mismatch")
        return token


class OriginalController:
    def __init__(
        self,
        database: Database,
        client: UpstreamWorkerClient,
        secrets: ScopedSecrets,
        artifacts: ArtifactStore,
        policy: ControllerPolicy = ControllerPolicy(),
    ):
        if secrets.root.is_relative_to(artifacts.root) or artifacts.root.is_relative_to(
            secrets.root
        ):
            raise ValueError("Private credentials and artifacts must be separate")
        if database.engine.dialect.name != "sqlite":
            raise ValueError("Phase 1 supports same-host local SQLite only")
        self.db, self.client, self.secrets, self.artifacts, self.policy = (
            database,
            client,
            secrets,
            artifacts,
            policy,
        )
        self.owner = "original:" + new_id()
        self.lock = threading.RLock()

    def _enabled(self):
        if not self.policy.enabled:
            raise ValueError("Original controller disabled; web launch remains unavailable")

    @contextmanager
    def _locked(self, run_id: str, *, owned: bool = False):
        if not re.fullmatch("[a-f0-9]{32}", run_id):
            raise ValueError("Invalid run identity")
        with self.db.sessions.begin() as session:
            accounting_lock(session)
            run = session.get(Run, run_id)
            job = session.scalar(select(Job).where(Job.run_id == run_id))
            if (
                run is None
                or job is None
                or run.profile != "full_research"
                or run.config.get("engine") != "original"
                or not run.state.get("original")
            ):
                raise ValueError("Not a controller-owned original run")
            if owned and (job.owner != self.owner or job.lease_until < time.time()):
                raise LostLease("Original controller lease lost")
            yield session, run, job

    def _event(self, session, run, decision, **data):
        run.updated_at = utcnow()
        record_event(
            session,
            run.id,
            "original_controller",
            "original_lifecycle",
            decision,
            {"decision": decision, "worker_id": str(UUID(hex=run.id)), **data},
        )

    def _revoke(self, session, run):
        for grant in session.scalars(
            select(GatewayGrant).where(
                GatewayGrant.run_id == run.id, GatewayGrant.revoked.is_(False)
            )
        ):
            grant.revoked = True
            self._event(session, run, "grant_revoked", grant_id=grant.id)

    def create(self, project_id: str, request: UpstreamRunRequest, budgets: Budgets) -> str:
        self._enabled()
        request.checked_id()
        if request.nested_budget_policy != "gateway_scoped" or request.runtime_seconds > min(
            budgets.max_runtime_seconds, self.policy.grant_seconds
        ):
            raise ValueError("Scoped gateway and runtime bounded by budget/grant required")
        run_id = UUID(request.run_id).hex
        config = {
            "engine": "original",
            "profile": "full_research",
            "execution_protocol": 2,
            "provider": "gemini",
            "model": request.model,
            "budgets": budgets.model_dump(),
            "original_request": request.model_dump(),
            "request_sha256": canonical_hash(request.model_dump()),
        }
        with self.db.sessions.begin() as session:
            accounting_lock(session)
            existing = session.get(Run, run_id)
            if existing:
                if existing.project_id != project_id or existing.config != config:
                    raise ValueError("Run identity collision")
                return run_id
            if session.get(Project, project_id) is None:
                raise ValueError("Project unavailable")
            run = Run(
                id=run_id,
                project_id=project_id,
                status="queued",
                profile="full_research",
                provider="gemini",
                model=request.model,
                config=config,
                state={
                    "original": {
                        "operation": "created",
                        "worker_id": request.run_id,
                        "attempts": 0,
                        "artifact_ids": [],
                    }
                },
            )
            session.add(run)
            session.flush()
            session.add(Job(run_id=run_id, status="original_pending"))
            refresh_usage(session, run)
            self._event(session, run, "created", request_sha256=config["request_sha256"])
        return run_id

    def _claim(self, run_id, *, reconciling=False):
        self._enabled()
        with self._locked(run_id) as (session, run, job):
            if run.status in TERMINAL:
                raise ValueError("Terminal original run cannot restart")
            if job.owner and job.owner != self.owner and job.lease_until >= time.time():
                raise LostLease("Original run already leased")
            job.owner = self.owner
            job.lease_until = time.time() + self.policy.lease_seconds
            if reconciling:
                run.state = {
                    **run.state,
                    "original": {**run.state["original"], "operation": "reconciling"},
                }

    def _ready(self):
        caps = self.client.capabilities()
        if not (
            caps.get("ready") is True
            and caps.get("infrastructure_ready") is True
            and caps.get("nested_call_budget_enforced") is True
            and caps.get("gateway_credentials") is True
            and caps.get("gateway_protocol") == "run-scoped-v1"
            and caps.get("transport") == "authenticated_https"
            and re.fullmatch("sha256:[a-f0-9]{64}", caps.get("image_id", ""))
        ):
            raise ValueError(
                "Dedicated worker and deployed gateway/egress readiness not established"
            )

    def _pause(self, run_id, reason):
        with self._locked(run_id, owned=True) as (session, run, job):
            self._revoke(session, run)
            run.status = "paused"
            run.control = "cancel" if run.control == "cancel" else "pause"
            run.error = reason
            run.state = {**run.state, "original": {**run.state["original"], "operation": reason}}
            job.status = "original_waiting"
            job.owner = None
            job.lease_until = 0
            self._event(session, run, reason)

    def _send(self, run_id, *, resume=False):
        self._claim(run_id)
        submission_started = resume
        try:
            self._ready()
            with self._locked(run_id, owned=True) as (session, run, job):
                original = run.state["original"]
                if not resume and original["operation"] not in {"created", "not_submitted"}:
                    raise ValueError("Reconcile uncertain submission; never replay it")
                if original["attempts"] >= 3:
                    raise ValueError("Original resume limit exhausted")
                usage = refresh_usage(session, run)
                if (
                    min(
                        usage["remaining_calls"],
                        usage["remaining_input_tokens"],
                        usage["remaining_output_tokens"],
                    )
                    <= 0
                ):
                    raise BudgetExceeded("Original run budget exhausted")
                self._revoke(session, run)
                run.status = "running"
                run.started_at = run.started_at or utcnow()
                run.control = None
                run.error = None
                request = UpstreamRunRequest.model_validate(run.config["original_request"])
                deadline = original.get("deadline", time.time() + request.runtime_seconds)
                remaining = int(deadline - time.time())
                if remaining < 1:
                    raise ValueError("Original execution window expired")
                run.state = {**run.state, "original": {**original, "deadline": deadline}}
                grant_id, token = issue_grant_locked(
                    session,
                    run.id,
                    allowed_models=[run.model],
                    ttl_seconds=min(self.policy.grant_seconds, remaining),
                    max_output_tokens=min(
                        self.policy.output_cap, run.config["budgets"]["max_output_tokens"]
                    ),
                )
                self.secrets.put(grant_id, token)
                run.state = {
                    **run.state,
                    "original": {
                        **original,
                        "operation": "delivering",
                        "grant_id": grant_id,
                        "attempts": original["attempts"] + 1,
                        "deadline": deadline,
                    },
                }
                job.status = "original_submitting"
                job.lease_until = time.time() + self.policy.lease_seconds
                job.heartbeat_at = utcnow()
                job.attempts += 1
                self._event(
                    session,
                    run,
                    "grant_bound",
                    grant_id=grant_id,
                    request_sha256=run.config["request_sha256"],
                )
            result = self.client.deliver_grant(request.run_id, token)
            if result.get("run_id") != request.run_id or result.get("credential_ready") is not True:
                raise ValueError("Credential delivery unconfirmed")
            with self._locked(run_id, owned=True) as (session, run, job):
                grant = session.get(GatewayGrant, grant_id)
                if run.control or grant is None or grant.revoked or grant.expires_at <= time.time():
                    raise ValueError("Submission authorization expired")
                run.state = {
                    **run.state,
                    "original": {**run.state["original"], "operation": "submitting"},
                }
                self._event(session, run, "submission_intent", grant_id=grant_id, resume=resume)
            submission_started = True
            result = self.client.resume(request.run_id) if resume else self.client.submit(request)
            self._accept(run_id, result)
        except LostLease:
            raise
        except Exception:
            self._pause(run_id, "submission_unconfirmed" if submission_started else "not_submitted")
            # Revocation/run pause gates new admissions even when worker is unreachable.
            try:
                self.client.cancel(str(UUID(hex=run_id)))
            except Exception:
                pass
            raise ValueError(
                "Original submission stopped; reconcile worker cleanup before retry"
            ) from None

    @serialized
    def submit(self, run_id):
        with self._locked(run_id) as (_, run, _job):
            if run.state["original"]["operation"] not in {"created", "not_submitted"}:
                raise ValueError("Duplicate submission refused; use reconciliation")
        self._send(run_id)

    def _accept(self, run_id, response):
        if response.get("run_id") != str(UUID(hex=run_id)):
            raise ValueError("Worker run identity mismatch")
        status = response.get("status")
        if status not in {
            "running",
            "queued",
            "completed",
            "completed_degraded",
            "failed",
            "cancelled",
            "interrupted",
            "cleanup_unverified",
            "cancellation_requested",
        }:
            raise ValueError("Unknown worker state")
        with self._locked(run_id, owned=True) as (session, run, job):
            original = run.state["original"]
            if status in {"running", "queued"}:
                if run.control or original.get("deadline", 0) <= time.time():
                    raise ValueError("Run not authorized to continue")
                grant = session.get(GatewayGrant, original.get("grant_id"))
                if grant is None or grant.revoked or grant.expires_at <= time.time():
                    raise ValueError("Gateway grant expired or unavailable")
                # Escrow absence after a crash never authorizes a replacement grant.
                self.secrets.get(grant)
                job.status = "original_running"
                job.lease_until = time.time() + self.policy.lease_seconds
                job.heartbeat_at = utcnow()
                run.state = {**run.state, "original": {**original, "operation": "running"}}
                self._event(session, run, "worker_running", grant_id=grant.id)
                return
            self._revoke(session, run)
            clean = response.get("cleanup_verified") is True
            run.status = "paused"
            run.control = "cancel" if run.control == "cancel" else "pause"
            job.status = "original_waiting"
            run.state = {
                **run.state,
                "original": {
                    **original,
                    "operation": "collecting"
                    if clean and status in {"completed", "completed_degraded"}
                    else "stopped",
                    "worker_status": status,
                    "cleanup_verified": clean,
                },
            }
            self._event(
                session, run, "worker_stopped", worker_status=status, cleanup_verified=clean
            )
        if clean and status in {"completed", "completed_degraded"}:
            names = response.get("artifacts", [])
            if not isinstance(names, list) or any(name not in ARTIFACT_NAMES for name in names):
                raise ValueError("Invalid artifact list")
            saved = []
            for name in names:
                with self._locked(run_id, owned=True):
                    pass
                content = self.client.artifact(str(UUID(hex=run_id)), name)
                item = self.artifacts.save(
                    run_id,
                    name,
                    content,
                    "application/pdf" if name.endswith(".pdf") else "application/octet-stream",
                    "original_output",
                )
                saved.append(item["id"])
            with self._locked(run_id, owned=True) as (session, run, job):
                run.status = status
                run.control = None
                run.current_stage = "completion"
                job.status = "original_done"
                run.state = {
                    **run.state,
                    "original": {
                        **run.state["original"],
                        "operation": "completed",
                        "artifact_ids": saved,
                    },
                }
                self._event(session, run, "completed", artifact_ids=saved)
                job.owner = None
                job.lease_until = 0
        else:
            with self._locked(run_id, owned=True) as (session, run, job):
                if clean and status == "cancelled" and run.control == "cancel":
                    run.status = "cancelled"
                    job.status = "original_done"
                job.owner = None
                job.lease_until = 0

    @serialized
    def reconcile(self, run_id):
        self._claim(run_id, reconciling=True)
        try:
            with self._locked(run_id, owned=True) as (_, run, _job):
                worker_id = run.state["original"]["worker_id"]
            self._accept(run_id, self.client.status(worker_id))
        except LostLease:
            raise
        except Exception:
            self._pause(run_id, "reconciliation_unconfirmed")
            try:
                self.client.cancel(str(UUID(hex=run_id)))
            except Exception:
                pass
            raise ValueError("Worker state unavailable; grants revoked and no replay") from None

    @serialized
    def pause(self, run_id):
        self._claim(run_id)
        with self._locked(run_id, owned=True) as (session, run, job):
            self._revoke(session, run)
            run.control = "pause"
            run.status = "paused"
            self._event(session, run, "pause_requested")
        try:
            self._accept(run_id, self.client.cancel(str(UUID(hex=run_id))))
        except LostLease:
            raise
        except Exception:
            self._pause(run_id, "pause_unconfirmed")

    @serialized
    def cancel(self, run_id):
        self._claim(run_id)
        with self._locked(run_id, owned=True) as (session, run, job):
            self._revoke(session, run)
            run.control = "cancel"
            run.status = "paused"
            run.state = {
                **run.state,
                "original": {**run.state["original"], "operation": "cancel_pending"},
            }
            self._event(session, run, "cancel_requested")
        try:
            self._accept(run_id, self.client.cancel(str(UUID(hex=run_id))))
        except LostLease:
            raise
        except Exception:
            self._pause(run_id, "cancel_unconfirmed")

    @serialized
    def resume(self, run_id):
        self._claim(run_id)
        with self._locked(run_id, owned=True) as (_, run, _job):
            if run.status != "paused" or run.control == "cancel":
                raise ValueError("Resume requires a paused, non-cancelled run")
        try:
            response = self.client.status(str(UUID(hex=run_id)))
            if (
                response.get("run_id") != str(UUID(hex=run_id))
                or response.get("status") not in {"interrupted", "failed", "cancelled"}
                or response.get("cleanup_verified") is not True
            ):
                raise ValueError("Worker cleanup unconfirmed")
        except Exception:
            self._pause(run_id, "resume_cleanup_unconfirmed")
            raise ValueError("Resume requires verified stopped worker cleanup") from None
        self._send(run_id, resume=True)

    def snapshot(self, run_id) -> dict[str, Any]:
        with self._locked(run_id) as (_, run, _job):
            return as_dict(run)
