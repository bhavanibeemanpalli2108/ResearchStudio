"""Constrained protocol for an administrator-provisioned original-engine worker.

The application never starts the unrestricted upstream agent on its own host.
Worker URLs and bearer tokens are operator configuration, never research input.
"""

from __future__ import annotations

import contextlib
import ipaddress
import os
import re
from collections.abc import Mapping
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .execution import CapabilityError, ExecutionCancelled, ExecutionError


class UpstreamRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str = Field(min_length=36, max_length=36)
    question: str = Field(min_length=10, max_length=30000)
    domain: str = Field(default="computational science", max_length=200)
    objectives: list[str] = Field(default_factory=list, max_length=20)
    constraints: str = Field(default="CPU only; no GPU training.", max_length=10000)
    model: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    agent: Literal["gemini"] = "gemini"
    runtime_seconds: int = Field(default=3600, ge=60, le=86400)
    idea_cycles: int = Field(default=1, ge=1, le=10)
    evaluations_per_attempt: int = Field(default=1, ge=1, le=5)
    replications: int = Field(default=2, ge=1, le=10)
    generate_paper: bool = True
    # Original coding agents make nested model calls outside the platform router.
    # This acknowledgment must come from the operator's separately approved policy.
    nested_budget_policy: Literal["operator_managed"]
    nested_budget_approved: Literal[True]

    @field_validator("run_id")
    @classmethod
    def canonical_uuid(cls, value: str) -> str:
        if str(UUID(value)) != value:
            raise ValueError("run_id must be a canonical lowercase UUID")
        return value

    @field_validator("objectives")
    @classmethod
    def bounded_objectives(cls, value: list[str]) -> list[str]:
        if any(len(item) > 2000 for item in value):
            raise ValueError("Each objective must contain at most 2000 characters")
        return value

    def checked_id(self) -> str:
        try:
            value = str(UUID(self.run_id))
        except ValueError as exc:
            raise ValueError("run_id must be a UUID") from exc
        if value != self.run_id:
            raise ValueError("run_id must be a canonical lowercase UUID")
        if any(len(item) > 2000 for item in self.objectives):
            raise ValueError("Each objective must contain at most 2000 characters")
        return value


class UpstreamWorkerClient:
    """Authenticated HTTPS client; no redirects, host execution or demo fallback."""

    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.environ = environ if environ is not None else os.environ
        self.url = self.environ.get("RESEARCH_UPSTREAM_WORKER_URL", "").rstrip("/")
        self.token = self.environ.get("RESEARCH_UPSTREAM_WORKER_TOKEN", "")
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(15, connect=5), follow_redirects=False, trust_env=False
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _configured(self) -> None:
        if not self.url or len(self.token) < 32:
            raise CapabilityError(
                "Configure a dedicated upstream worker URL and a token of at least 32 characters."
            )
        parsed = urlparse(self.url)
        try:
            loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
        except ValueError:
            loopback = parsed.hostname == "localhost"
        local_http = (
            self.environ.get("RESEARCH_UPSTREAM_ALLOW_LOOPBACK_HTTP") == "1"
            and loopback
            and parsed.scheme == "http"
        )
        if (
            (parsed.scheme != "https" and not local_http)
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise CapabilityError(
                "Upstream worker must be an HTTPS origin without credentials, path or query."
            )

    def _request(
        self, method: str, path: str, *, payload: dict[str, Any] | None = None, binary: bool = False
    ) -> Any:
        self._configured()
        try:
            with self.client.stream(
                method,
                self.url + path,
                headers={"Authorization": "Bearer " + self.token},
                json=payload,
                timeout=httpx.Timeout(
                    90 if path in {"/v1/capabilities", "/v1/runs"} else 15, connect=5
                ),
            ) as response:
                if response.status_code >= 300:
                    raise CapabilityError(
                        f"Upstream worker rejected the request (HTTP {response.status_code})."
                    )
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > (16 * 1024 * 1024 if binary else 2 * 1024 * 1024):
                        raise ExecutionError("Upstream worker response exceeded its size limit.")
                if binary:
                    return bytes(content)
                import json

                value = json.loads(content)
                if not isinstance(value, dict):
                    raise ValueError("Expected object")
                return value
        except (httpx.HTTPError, ValueError) as exc:
            raise CapabilityError(
                "Upstream worker is unreachable or returned an invalid response."
            ) from exc

    def capabilities(self) -> dict[str, Any]:
        try:
            result = self._request("GET", "/v1/capabilities")
            return {
                **result,
                "transport": "authenticated_https"
                if self.url.startswith("https:")
                else "explicit_loopback_development",
            }
        except CapabilityError as exc:
            return {
                "ready": False,
                "reason": str(exc),
                "source": "upstream_agsci",
                "nested_call_budget_enforced": False,
            }

    @staticmethod
    def _job_id(job_id: str) -> str:
        try:
            checked = str(UUID(job_id))
        except ValueError as exc:
            raise CapabilityError("Invalid upstream job identifier.") from exc
        if checked != job_id:
            raise CapabilityError("Invalid upstream job identifier.")
        return checked

    def submit(self, request: UpstreamRunRequest) -> dict[str, Any]:
        request.checked_id()
        return self._request("POST", "/v1/runs", payload=request.model_dump())

    def dry_run(self, request: UpstreamRunRequest) -> dict[str, Any]:
        request.checked_id()
        return self._request("POST", "/v1/dry-run", payload=request.model_dump())

    def status(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", "/v1/runs/" + self._job_id(job_id))

    def events(self, job_id: str, *, after: int = 0) -> dict[str, Any]:
        if type(after) is not int or not 0 <= after <= 1000000:
            raise CapabilityError("Invalid event cursor.")
        return self._request("GET", f"/v1/runs/{self._job_id(job_id)}/events?after={after}")

    def cancel(self, job_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/runs/{self._job_id(job_id)}/cancel")

    def resume(self, job_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/runs/{self._job_id(job_id)}/resume")

    def artifact(self, job_id: str, name: str) -> bytes:
        if name not in {
            "paper.pdf",
            "paper.tex",
            "final_manifest.json",
            "best_program_manifest.json",
            "pipeline_events.jsonl",
        }:
            raise CapabilityError("Unsupported upstream artifact.")
        return self._request(
            "GET", f"/v1/runs/{self._job_id(job_id)}/artifacts/{name}", binary=True
        )

    def wait(
        self,
        job_id: str,
        *,
        cancel_check: Any = None,
        progress_callback: Any = None,
        timeout_seconds: float = 3600,
        poll_seconds: float = 2,
    ) -> dict[str, Any]:
        import time

        deadline = time.monotonic() + max(1, min(timeout_seconds, 86460))
        cursor = 0
        try:
            while time.monotonic() < deadline:
                if cancel_check and cancel_check():
                    raise ExecutionCancelled(
                        "Cancellation requested from the isolated upstream worker; consult worker status for verified cleanup."
                    )
                result = self.status(job_id)
                if progress_callback:
                    batch = self.events(job_id, after=cursor)
                    cursor = batch.get("next_cursor", cursor)
                    progress_callback({**result, "events": batch.get("events", [])})
                if result.get("status") in {"completed", "completed_degraded"}:
                    return result
                if result.get("status") in {
                    "failed",
                    "cancelled",
                    "interrupted",
                    "cleanup_unverified",
                }:
                    raise ExecutionError(
                        "Original upstream run ended with status "
                        + str(result["status"])
                        + "; inspect its worker events and retained artifacts."
                    )
                time.sleep(max(0.1, min(poll_seconds, 10)))
            raise ExecutionError(
                "Upstream worker wait expired; cancellation was requested and cleanup must be checked."
            )
        except BaseException:
            # Ownership/budget callbacks may raise instead of returning True.
            # They must still fence off work on the independent remote worker.
            with contextlib.suppress(Exception):
                self.cancel(job_id)
            raise


def hydra_string(value: str) -> str:
    """A literal Hydra string, never a shell fragment or interpolation."""
    import json

    if "${" in value or "\x00" in value:
        raise ValueError("Hydra interpolation and NUL are forbidden in command values")
    return json.dumps(value, ensure_ascii=True)


def upstream_command(
    request: UpstreamRunRequest,
    *,
    python: str,
    task_dir: str,
    run_dir: str,
    auth_root: str,
    env_file: str,
    image: str,
    resume: bool = False,
    dry_run: bool = False,
    remaining_phases: list[str] | None = None,
) -> list[str]:
    """Only fixed keys derived from a strict request reach original Hydra CLI."""
    request.checked_id()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./:@_-]{0,255}", image):
        raise ValueError("Invalid upstream image")
    phases = "task_drafting,investigation,ablations,final_evaluation,posthoc"
    if request.generate_paper:
        phases += ",paper"
    if resume:
        phases = phases.replace("task_drafting,", "")
    if remaining_phases is not None:
        permitted = phases.split(",") + ["task_drafting"]
        if not remaining_phases or any(phase not in permitted for phase in remaining_phases):
            raise ValueError("Invalid remaining upstream phases")
        phases = ",".join(remaining_phases)
    command = [
        python,
        "-m",
        "src.agsci.main",
        "run",
        "task.dir=" + hydra_string(task_dir),
        "paths.run_dir=" + hydra_string(run_dir),
        "run_id=" + hydra_string(request.run_id),
        "agent.name=gemini",
        "agent.model=" + hydra_string(request.model),
        "container.enabled=true",
        "container.gpu_count=0",
        "container.network=bridge",
        "container.image=" + hydra_string(image),
        "container.auth_root=" + hydra_string(auth_root),
        "container.env_file=" + hydra_string(env_file),
        "execution.phases=" + hydra_string(phases),
        "execution.fail_fast=true",
        "versioning.enabled=true",
        "investigation.execution.workers=1",
        f"investigation.execution.max_idea_cycles={request.idea_cycles}",
        f"investigation.execution.max_program_evals_per_attempt={request.evaluations_per_attempt}",
        f"investigation.execution.run_timeout_seconds={request.runtime_seconds}",
        f"investigation.execution.idea_timeout_seconds={min(request.runtime_seconds, 600)}",
        f"task_drafting.timeout_seconds={request.runtime_seconds}",
        f"ablations.execution.num_replications={request.replications}",
        f"ablations.execution.max_evals_per_variant={request.evaluations_per_attempt}",
        f"final.timeout_seconds={request.runtime_seconds}",
        "posthoc.execution.max_selected_analyses=1",
        "paper.paper_min_refs=8",
        "paper.paper_max_refs=15",
    ]
    if resume:
        command.append("investigation.execution.resume=true")
    if dry_run:
        command.append("--dry-run")
    return command
