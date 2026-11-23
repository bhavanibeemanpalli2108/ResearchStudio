"""Offline lifecycle acceptance: fake TLS worker, fake gateway, temporary ledger."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.research_platform import original_controller as module
from src.research_platform.artifacts import ArtifactStore
from src.research_platform.database import (
    Database,
    Project,
    Run,
    Job,
    GatewayGrant,
    ModelUsage,
    WorkflowEvent,
    as_dict,
)
from src.research_platform.model_gateway import GatewaySettings, create_gateway_app
from src.research_platform.original_controller import (
    ControllerPolicy,
    OriginalController,
    ScopedSecrets,
)
from src.research_platform.schemas import Budgets
from src.research_platform.services import LostLease
from src.research_platform.upstream_execution import UpstreamRunRequest, UpstreamWorkerClient

MODEL = "gemini-2.5-flash"
TOKEN = "offline-transport-" + "x" * 40
PAYLOAD = {"contents": [{"parts": [{"text": "Offline only"}]}]}


class WorkerTransport:
    def __init__(self):
        self.calls = []
        self.tokens = []
        self.status = "running"
        self.fail = None
        self.ready = True
        self.artifacts = []
        self.clean = None

    def __call__(self, request):
        assert request.url.host == "dedicated.invalid"
        assert request.headers["authorization"] == "Bearer " + TOKEN
        path = request.url.path
        self.calls.append((request.method, path))
        if self.fail and (self.fail == path if self.fail == "/v1/runs" else self.fail in path):
            raise httpx.ConnectError("fixture secret must never reach audit", request=request)
        if path == "/v1/capabilities":
            return httpx.Response(
                200,
                json={
                    "ready": self.ready,
                    "infrastructure_ready": True,
                    "nested_call_budget_enforced": self.ready,
                    "gateway_credentials": True,
                    "gateway_protocol": "run-scoped-v1",
                    "image_id": "sha256:" + "a" * 64,
                },
            )
        if path.endswith("/gateway-credential"):
            self.tokens.append(json.loads(request.content)["scoped_token"])
            return httpx.Response(
                200, json={"run_id": path.split("/")[3], "credential_ready": True}
            )
        if "/artifacts/" in path:
            return httpx.Response(200, content=b'{"fixture": "not scientific evidence"}')
        if path == "/v1/runs":
            identifier = json.loads(request.content)["run_id"]
        else:
            identifier = path.split("/")[3]
        if path.endswith("/cancel") and self.status in {"running", "queued"}:
            self.status = "cancelled"
        if path.endswith("/resume"):
            self.status = "running"
        return httpx.Response(
            200,
            json={
                "run_id": identifier,
                "status": self.status,
                "cleanup_verified": self.status != "running" if self.clean is None else self.clean,
                "artifacts": self.artifacts,
            },
        )


@pytest.fixture
def controller(tmp_path):
    db = Database(f"sqlite:///{(tmp_path / 'trusted.db').as_posix()}")
    db.migrate()
    with db.sessions.begin() as session:
        project = Project(
            title="Synthetic lifecycle", question="No scientific campaign", domain="offline"
        )
        session.add(project)
        session.flush()
        project_id = project.id
        # Sentinel for preservation across controller operations.
        native = Run(
            project_id=project_id,
            status="completed",
            profile="free_research",
            provider="mock",
            model="fixture",
            config={"engine": "native"},
            state={"immutable": True},
        )
        session.add(native)
        session.flush()
        native_id = native.id
        before = as_dict(native)
    transport = WorkerTransport()
    client = UpstreamWorkerClient(
        {
            "RESEARCH_UPSTREAM_WORKER_URL": "https://dedicated.invalid",
            "RESEARCH_UPSTREAM_WORKER_TOKEN": TOKEN,
        },
        client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    ctrl = OriginalController(
        db,
        client,
        ScopedSecrets(tmp_path / "private"),
        ArtifactStore(tmp_path / "artifacts", db),
        ControllerPolicy(enabled=True),
    )
    request = UpstreamRunRequest(
        run_id=str(uuid4()),
        question="Can an offline controller be reconciled safely?",
        model=MODEL,
        runtime_seconds=120,
        nested_budget_policy="gateway_scoped",
        nested_budget_approved=True,
    )
    run_id = ctrl.create(project_id, request, Budgets(max_llm_calls=2))
    yield ctrl, transport, run_id, project_id, request
    with db.sessions() as session:
        assert as_dict(session.get(Run, native_id)) == before
        events = list(session.scalars(select(WorkflowEvent)))
        serialized = json.dumps([as_dict(e) for e in events])
        assert TOKEN not in serialized
        assert all(secret not in serialized for secret in transport.tokens)
        assert "fixture secret" not in serialized
    client.client.close()
    db.engine.dispose()


def grants(ctrl):
    with ctrl.db.sessions() as session:
        return list(session.scalars(select(GatewayGrant)))


def expire_lease(ctrl, run_id):
    with ctrl.db.sessions.begin() as session:
        job = session.scalar(select(Job).where(Job.run_id == run_id))
        job.lease_until = 0


def gateway(ctrl, *, fail=False):
    dispatch = []

    async def provider(request):
        dispatch.append(request)
        if fail:
            raise httpx.ReadTimeout("fixture provider failure", request=request)
        return httpx.Response(
            200,
            json={
                "usageMetadata": {
                    "promptTokenCount": 5,
                    "candidatesTokenCount": 2,
                    "totalTokenCount": 7,
                },
                "candidates": [{"content": {"parts": [{"text": "fixture"}]}}],
            },
        )

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_gateway_app(
        ctrl.db, GatewaySettings(enabled=True, provider_key="fake-provider-key"), client=upstream
    )
    return app, dispatch


def generate(client, run_id, token, identity=None):
    headers = {"x-goog-api-key": token}
    if identity:
        headers["x-reseon-request-id"] = identity
    return client.post(
        f"/runs/{run_id}/v1beta/models/{MODEL}:generateContent", headers=headers, json=PAYLOAD
    )


def test_identity_submission_completion_artifacts_and_terminal_fence(controller):
    ctrl, worker, run_id, project, request = controller
    assert ctrl.create(project, request, Budgets(max_llm_calls=2)) == run_id
    with pytest.raises(ValueError, match="collision"):
        ctrl.create(
            project,
            request.model_copy(update={"question": "Different offline question"}),
            Budgets(),
        )
    with ctrl.db.sessions() as session:
        assert session.scalar(select(Job).where(Job.run_id == run_id)).status == "original_pending"
    ctrl.submit(run_id)
    assert ctrl.snapshot(run_id)["status"] == "running"
    assert len(grants(ctrl)) == 1
    with pytest.raises(ValueError, match="Duplicate"):
        ctrl.submit(run_id)
    assert worker.calls.count(("POST", "/v1/runs")) == 1
    worker.status = "completed"
    worker.artifacts = ["final_manifest.json", "paper.tex"]
    ctrl.reconcile(run_id)
    result = ctrl.snapshot(run_id)
    assert result["status"] == "completed"
    assert len(result["state"]["original"]["artifact_ids"]) == 2
    assert all(g.revoked for g in grants(ctrl))
    assert result["usage"]["calls"] == 0
    with pytest.raises(ValueError, match="Terminal"):
        ctrl.resume(run_id)


def test_request_identity_is_persistent_concurrent_and_budgeted(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    app, dispatch = gateway(ctrl)
    with TestClient(app) as client:
        with ThreadPoolExecutor(max_workers=5) as pool:
            statuses = list(
                pool.map(
                    lambda _: generate(client, run_id, worker.tokens[-1], "a" * 32).status_code,
                    range(5),
                )
            )
        assert sorted(statuses) == [200, 409, 409, 409, 409]
        assert generate(client, run_id, worker.tokens[-1], "b" * 32).status_code == 200
        assert generate(client, run_id, worker.tokens[-1], "c" * 32).status_code == 403
        assert generate(client, run_id, worker.tokens[-1], "a" * 32).status_code == 409
    assert len(dispatch) == 2
    with ctrl.db.sessions() as session:
        usage = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == run_id)))
        assert len(usage) == 2 and all(row.status == "completed" for row in usage)
        event = session.scalar(
            select(WorkflowEvent).where(
                WorkflowEvent.kind == "gateway_decision",
                WorkflowEvent.message == "Gateway reserved",
            )
        )
        assert event.data["grant_id"] == grants(ctrl)[0].id
        assert event.data["usage_id"] in [row.id for row in usage]


def test_pause_resume_rotates_grant_without_extending_deadline(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    before = ctrl.snapshot(run_id)["state"]["original"]["deadline"]
    old = worker.tokens[-1]
    ctrl.pause(run_id)
    assert ctrl.snapshot(run_id)["status"] == "paused"
    assert all(g.revoked for g in grants(ctrl))
    ctrl.resume(run_id)
    assert ctrl.snapshot(run_id)["state"]["original"]["deadline"] == before
    assert worker.tokens[-1] != old
    assert sum(not g.revoked for g in grants(ctrl)) == 1
    assert worker.calls.count(("POST", "/v1/runs")) == 1
    worker_id = ctrl.snapshot(run_id)["state"]["original"]["worker_id"]
    assert worker.calls.count(("POST", f"/v1/runs/{worker_id}/resume")) == 1
    app, _ = gateway(ctrl)
    with TestClient(app) as client:
        assert generate(client, run_id, old).status_code == 401
        assert generate(client, run_id, worker.tokens[-1]).status_code == 200


def test_cancel_fails_closed_when_worker_disconnects(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    worker.fail = "/cancel"
    ctrl.cancel(run_id)
    snapshot = ctrl.snapshot(run_id)
    assert snapshot["status"] == "paused" and snapshot["control"] == "cancel"
    assert all(g.revoked for g in grants(ctrl))
    with pytest.raises(ValueError, match="paused"):
        ctrl.resume(run_id)
    worker.fail = None
    ctrl.reconcile(run_id) if worker.status != "running" else ctrl.cancel(run_id)
    assert ctrl.snapshot(run_id)["status"] == "cancelled"


def test_restart_reconciles_existing_execution_never_resubmits(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    restarted = OriginalController(ctrl.db, ctrl.client, ctrl.secrets, ctrl.artifacts, ctrl.policy)
    with pytest.raises(LostLease):
        restarted.reconcile(run_id)
    expire_lease(ctrl, run_id)
    restarted.reconcile(run_id)
    assert restarted.snapshot(run_id)["status"] == "running"
    worker.status = "interrupted"
    restarted.reconcile(run_id)
    assert restarted.snapshot(run_id)["status"] == "paused"
    restarted.resume(run_id)
    assert worker.calls.count(("POST", "/v1/runs")) == 1
    assert len(grants(ctrl)) == 2


@pytest.mark.parametrize("failure", ["credential", "/v1/runs"])
def test_delivery_and_ambiguous_submission_failure(controller, failure):
    ctrl, worker, run_id, _, _ = controller
    worker.fail = failure
    with pytest.raises(ValueError, match="stopped"):
        ctrl.submit(run_id)
    assert ctrl.snapshot(run_id)["status"] == "paused"
    assert all(g.revoked for g in grants(ctrl))
    worker.fail = None
    if failure == "/v1/runs":
        with pytest.raises(ValueError, match="Duplicate"):
            ctrl.submit(run_id)
    else:
        ctrl.submit(run_id)  # Delivery failure proves generation submission was never attempted.
        assert worker.calls.count(("POST", "/v1/runs")) == 1


def test_readiness_and_grant_issuance_fail_before_submission(controller, monkeypatch):
    ctrl, worker, run_id, _, _ = controller
    worker.ready = False
    with pytest.raises(ValueError):
        ctrl.submit(run_id)
    assert not grants(ctrl) and ("POST", "/v1/runs") not in worker.calls
    worker.ready = True

    def unavailable(*args, **kwargs):
        raise RuntimeError("fake gateway unavailable")

    monkeypatch.setattr(module, "issue_grant_locked", unavailable)
    with pytest.raises(ValueError):
        ctrl.submit(run_id)
    assert not grants(ctrl) and ("POST", "/v1/runs") not in worker.calls


@pytest.mark.parametrize("expired", ["grant", "deadline", "revoked"])
def test_gateway_expiry_and_revocation(controller, expired):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    with ctrl.db.sessions.begin() as session:
        grant = session.get(GatewayGrant, grants(ctrl)[0].id)
        if expired == "grant":
            grant.expires_at = time.time() - 1
        elif expired == "revoked":
            grant.revoked = True
        else:
            run = session.get(Run, run_id)
            run.state = {
                **run.state,
                "original": {**run.state["original"], "deadline": time.time() - 1},
            }
    app, dispatch = gateway(ctrl)
    with TestClient(app) as client:
        assert generate(client, run_id, worker.tokens[-1]).status_code in {401, 403}
    assert not dispatch
    with pytest.raises(ValueError, match="unavailable"):
        ctrl.reconcile(run_id)
    assert all(g.revoked for g in grants(ctrl))


def test_gateway_failure_retains_reservation_through_controller_recovery(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    app, dispatch = gateway(ctrl, fail=True)
    with TestClient(app) as client:
        assert generate(client, run_id, worker.tokens[-1], "d" * 32).status_code == 502
    worker.fail = "/v1/runs/"
    with pytest.raises(ValueError):
        ctrl.reconcile(run_id)
    assert all(g.revoked for g in grants(ctrl))
    with ctrl.db.sessions() as session:
        usage = session.scalar(select(ModelUsage).where(ModelUsage.run_id == run_id))
        assert usage.status == "uncertain" and usage.reserved_output_tokens > 0
    assert len(dispatch) == 1


def test_missing_escrow_and_unverified_cleanup_never_reissue(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    ctrl.secrets.path(grants(ctrl)[0].id).unlink()
    with pytest.raises(ValueError):
        ctrl.reconcile(run_id)
    worker.status = "running"
    with pytest.raises(ValueError, match="cleanup"):
        ctrl.resume(run_id)
    assert len(grants(ctrl)) == 1 and grants(ctrl)[0].revoked


def test_disabled_controller_and_misplaced_secret_root(controller):
    ctrl, _, _, project, request = controller
    disabled = OriginalController(ctrl.db, ctrl.client, ctrl.secrets, ctrl.artifacts)
    with pytest.raises(ValueError, match="disabled"):
        disabled.create(project, request, Budgets())
    with pytest.raises(ValueError, match="separate"):
        OriginalController(
            ctrl.db, ctrl.client, ScopedSecrets(ctrl.artifacts.root / "private"), ctrl.artifacts
        )


def test_native_queue_and_web_controls_cannot_dispatch_original(controller, tmp_path):
    from apps.research_platform.backend.app import create_app
    from src.research_platform.config import Settings
    from src.research_platform.worker import Worker

    ctrl, _, run_id, project, _ = controller
    settings = Settings(
        database_url=str(ctrl.db.engine.url),
        artifact_root=ctrl.artifacts.root,
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    assert Worker(settings, database=ctrl.db).claim() is None
    with TestClient(create_app(settings, database=ctrl.db)) as client:
        for action in ["resume", "pause", "cancel"]:
            assert client.post(f"/api/runs/{run_id}/{action}").status_code == 409
        assert (
            client.post(
                f"/api/projects/{project}/runs",
                json={"profile": "full_research", "provider": "gemini", "model": MODEL},
            ).status_code
            == 409
        )
    assert ctrl.snapshot(run_id)["state"]["original"]["operation"] == "created"


def test_expired_window_and_budget_exhaustion_never_resume(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    app, _ = gateway(ctrl)
    with TestClient(app) as client:
        for _ in range(2):
            assert generate(client, run_id, worker.tokens[-1]).status_code == 200
    ctrl.pause(run_id)
    with pytest.raises(ValueError):
        ctrl.resume(run_id)
    assert len(grants(ctrl)) == 1 and grants(ctrl)[0].revoked


def test_two_controllers_cannot_duplicate_submission(controller):
    ctrl, worker, run_id, _, _ = controller
    second = OriginalController(ctrl.db, ctrl.client, ctrl.secrets, ctrl.artifacts, ctrl.policy)

    def submit(one):
        try:
            one.submit(run_id)
            return "submitted"
        except (ValueError, LostLease):
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, [ctrl, second])) == ["blocked", "submitted"]
    assert worker.calls.count(("POST", "/v1/runs")) == 1
    assert len(grants(ctrl)) == 1


def test_expired_controller_lease_blocks_gateway_until_reconciled(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    expire_lease(ctrl, run_id)
    app, dispatch = gateway(ctrl)
    with TestClient(app) as client:
        assert generate(client, run_id, worker.tokens[-1]).status_code == 403
        assert not dispatch
        ctrl.reconcile(run_id)
        assert generate(client, run_id, worker.tokens[-1]).status_code == 200


def test_duplicate_request_does_not_depend_on_retained_audit_events(controller):
    from sqlalchemy import delete

    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    app, dispatch = gateway(ctrl)
    identity = "e" * 32
    with TestClient(app) as client:
        assert generate(client, run_id, worker.tokens[-1], identity).status_code == 200
    with ctrl.db.sessions.begin() as session:
        session.execute(delete(WorkflowEvent).where(WorkflowEvent.kind == "gateway_decision"))
    restarted, dispatched_after_restart = gateway(ctrl)
    with TestClient(restarted) as client:
        assert generate(client, run_id, worker.tokens[-1], identity).status_code == 409
    assert len(dispatch) == 1 and not dispatched_after_restart


def test_cleanup_and_artifact_failures_cannot_publish_completion(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    worker.status = "completed"
    worker.clean = False
    ctrl.reconcile(run_id)
    assert ctrl.snapshot(run_id)["status"] == "paused"
    assert not ctrl.artifacts.list(run_id) and all(g.revoked for g in grants(ctrl))
    worker.clean = True
    worker.artifacts = ["../../private.env"]
    with pytest.raises(ValueError):
        ctrl.reconcile(run_id)
    assert ctrl.snapshot(run_id)["status"] == "paused"
    assert not ctrl.artifacts.list(run_id)
    worker.artifacts = ["final_manifest.json"]
    ctrl.reconcile(run_id)
    assert ctrl.snapshot(run_id)["status"] == "completed"
    assert len(ctrl.artifacts.list(run_id)) == 1
    assert worker.calls.count(("POST", "/v1/runs")) == 1


def test_critical_audit_linkage_survives_optional_event_cap(controller):
    ctrl, worker, run_id, _, _ = controller
    ctrl.submit(run_id)
    with ctrl.db.sessions.begin() as session:
        session.add_all(
            [
                WorkflowEvent(
                    run_id=run_id,
                    stage="upstream_gateway",
                    kind="gateway_decision",
                    message="fixture optional denial",
                    data={},
                )
                for _ in range(1000)
            ]
        )
    app, _ = gateway(ctrl)
    with TestClient(app) as client:
        assert generate(client, run_id, worker.tokens[-1]).status_code == 200
    with ctrl.db.sessions() as session:
        event = session.scalar(
            select(WorkflowEvent).where(WorkflowEvent.message == "Gateway reserved")
        )
        assert event.data["grant_id"] == grants(ctrl)[0].id
        assert session.get(ModelUsage, event.data["usage_id"]) is not None
