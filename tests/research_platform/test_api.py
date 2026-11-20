"""REST-to-worker integration tests using real SQLite migrations/checkpoints."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.research_platform.backend.app import create_app
from src.research_platform.artifacts import ArtifactStore
from src.research_platform.config import Settings
from src.research_platform.database import Artifact, Database, Job, ModelUsage, Run
from src.research_platform.worker import Worker


@pytest.fixture
def settings(tmp_path, monkeypatch):
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'platform.sqlite').as_posix()}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.sqlite",
        upstream_results_root=tmp_path / "upstream",
    )


@pytest.fixture
def platform(settings):
    database = Database(settings.database_url)
    with TestClient(create_app(settings, database=database)) as client:
        yield client, settings, database


def project(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/projects",
        json={
            "title": "Reproducible grid study",
            "question": "Can a controlled grid comparison improve circle packing?",
            "domain": "Computational geometry",
            "objectives": ["Measure feasibility and packed radius"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def run(client: TestClient, project_id: str, **config: Any) -> dict[str, Any]:
    response = client.post(f"/api/projects/{project_id}/runs", json=config)
    assert response.status_code == 201, response.text
    return response.json()


def detail(client: TestClient, run_id: str) -> dict[str, Any]:
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    return response.json()


def approve(client: TestClient, run_id: str, **payload: Any):
    return client.post(
        f"/api/runs/{run_id}/approve", json={"approved": True, "action": "continue", **payload}
    )


def test_default_no_key_demo_plan_idea_gates_report_and_download(platform):
    client, settings, database = platform
    assert client.get("/api/health").json()["demo_requires_keys"] is False
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/projects/{project_id}/imports" in schema.json()["paths"]
    record = run(client, project(client)["id"])
    worker = Worker(settings, database)
    assert record["status"] == "queued"
    assert worker.run_once()
    first = detail(client, record["id"])
    assert first["status"] == "awaiting_approval", first
    assert first["approval"]["gate"] == "research_plan"
    assert first["current_stage"] == "research_plan"
    assert first["state"]["plan"]["summary"]
    assert client.get(f"/api/runs/{record['id']}/experiments").json() == []
    assert approve(client, record["id"]).status_code == 200
    assert worker.run_once()
    second = detail(client, record["id"])
    assert second["status"] == "awaiting_approval", second
    assert second["approval"]["gate"] == "approval"
    assert second["current_stage"] == "approval"
    idea_id = second["state"]["ideas"][0]["id"]
    assert approve(client, record["id"], idea_id=idea_id).status_code == 200
    assert worker.run_once()
    finished = detail(client, record["id"])
    assert finished["status"] == "completed", finished
    assert finished["state"]["results"]["demo"] is True
    assert finished["usage"]["calls"] >= 5
    assert finished["usage"]["estimated_cost"] == 0
    experiments = client.get(f"/api/runs/{record['id']}/experiments").json()
    assert len(experiments) == 1 and experiments[0]["status"] == "completed"
    assert client.get(f"/api/runs/{record['id']}/metrics").json()[0]["metrics"]
    artifacts = client.get(f"/api/runs/{record['id']}/artifacts").json()
    manuscript = next(item for item in artifacts if item["name"] == "research_report.md")
    response = client.get(manuscript["download_url"])
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert "AI-generated" in response.text and "DEMONSTRATION / MOCK RUN" in response.text
    assert "relative_path" not in manuscript
    events = client.get(f"/api/runs/{record['id']}/events").json()
    kinds = {item["kind"] for item in events}
    assert {"node_started", "node_completed", "decision", "approval_required", "usage"} <= kinds
    cursor = int(events[-2]["id"])
    later = client.get(f"/api/runs/{record['id']}/events", params={"after": cursor}).json()
    assert all(int(item["id"]) > cursor for item in later)
    assert client.get(f"/api/runs/{record['id']}/traces").json()["decisions"]
    nodes = client.get(f"/api/runs/{record['id']}/graph").json()["nodes"]
    assert next(n for n in nodes if n["id"] == "completion")["status"] == "completed"
    assert worker.run_once() is False
    with database.sessions() as session:
        assert session.scalar(select(Job).where(Job.run_id == record["id"])).status == "done"


def test_sqlite_restart_resumes_serialized_interrupts_without_repeating_planning(settings):
    database = Database(settings.database_url)
    with TestClient(create_app(settings, database=database)) as client:
        record = run(client, project(client)["id"])
        assert Worker(settings, database).run_once()
        assert detail(client, record["id"])["approval"]["gate"] == "research_plan"
    second_db = Database(settings.database_url)
    with TestClient(create_app(settings, database=second_db)) as client:
        assert detail(client, record["id"])["status"] == "awaiting_approval"
        assert approve(client, record["id"]).status_code == 200
        assert Worker(settings, second_db).run_once()
        assert detail(client, record["id"])["approval"]["gate"] == "approval"
    third_db = Database(settings.database_url)
    with TestClient(create_app(settings, database=third_db)) as client:
        assert approve(client, record["id"]).status_code == 200
        assert Worker(settings, third_db).run_once()
        assert detail(client, record["id"])["status"] == "completed"
        with third_db.sessions() as session:
            planning = list(
                session.scalars(
                    select(ModelUsage).where(
                        ModelUsage.run_id == record["id"], ModelUsage.stage == "planning"
                    )
                )
            )
            assert len(planning) == 1


def test_duplicate_approval_and_unknown_idea_are_rejected(platform):
    client, settings, database = platform
    record = run(client, project(client)["id"])
    worker = Worker(settings, database)
    worker.run_once()
    assert approve(client, record["id"], idea_id="foreign-idea").status_code == 422
    assert approve(client, record["id"]).status_code == 200
    assert approve(client, record["id"]).status_code == 409
    assert client.post(f"/api/runs/{record['id']}/resume").status_code == 409
    worker.run_once()
    assert detail(client, record["id"])["approval"]["gate"] == "approval"


def test_queued_pause_resume_and_cancellation(platform):
    client, settings, database = platform
    record = run(client, project(client)["id"])
    worker = Worker(settings, database)
    assert client.post(f"/api/runs/{record['id']}/pause").json()["status"] == "paused"
    assert worker.run_once() is False
    assert client.post(f"/api/runs/{record['id']}/resume").json()["status"] == "queued"
    assert worker.run_once()
    assert detail(client, record["id"])["status"] == "awaiting_approval"
    assert client.post(f"/api/runs/{record['id']}/cancel").json()["status"] == "cancelled"
    assert worker.run_once() is False
    assert client.post(f"/api/runs/{record['id']}/cancel").json()["status"] == "cancelled"
    assert approve(client, record["id"]).status_code == 409
    assert client.get(f"/api/runs/{record['id']}/experiments").json() == []


def test_cancel_queued_run_does_not_invoke_any_model(platform):
    client, settings, database = platform
    record = run(client, project(client)["id"])
    assert client.post(f"/api/runs/{record['id']}/cancel").json()["status"] == "cancelled"
    assert Worker(settings, database).run_once() is False
    assert client.get("/api/usage").json()["calls"] == 0


def test_missing_resources_validation_origin_and_host_guards(platform):
    client, _, _ = platform
    assert client.get("/api/projects/missing").status_code == 404
    assert client.post("/api/projects/missing/runs", json={}).status_code == 404
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/runs/missing/events").status_code == 404
    assert client.get("/api/artifacts/missing/download").status_code == 404
    assert client.post("/api/projects", json={"title": "x", "question": "short"}).status_code == 422
    assert (
        client.post(
            "/api/projects",
            json={"title": "Valid", "question": "A sufficiently long question"},
            headers={"Origin": "https://untrusted.example"},
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"host": "untrusted.example"}).status_code == 400
    assert client.get("/api/health", headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_download_rejects_database_path_escape(platform, tmp_path):
    client, settings, database = platform
    record = run(client, project(client)["id"])
    item = ArtifactStore(settings.artifact_root, database).save(
        record["id"], "safe.txt", "inside", "text/plain", "report"
    )
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("outside storage", encoding="utf-8")
    with database.sessions.begin() as session:
        row = session.get(Artifact, item["id"])
        row.relative_path = "../outside-secret.txt"
    response = client.get(item["download_url"])
    assert response.status_code == 404
    assert "outside storage" not in response.text


def test_worker_budget_failure_is_paused_and_checkpoint_survives(platform):
    client, settings, database = platform
    record = run(
        client, project(client)["id"], require_approval=False, budgets={"max_input_tokens": 128}
    )
    assert Worker(settings, database).run_once()
    failed = detail(client, record["id"])
    assert failed["status"] == "paused", failed
    assert "budget_exhausted" in failed["error"]
    assert failed["usage"]["calls"] == 0
    assert failed["state"]["question"]
    with database.sessions.begin() as session:
        row = session.get(Run, record["id"])
        row.config = {**row.config, "budgets": {**row.config["budgets"], "max_input_tokens": 32000}}
    assert client.post(f"/api/runs/{record['id']}/resume").status_code == 200
    assert Worker(settings, database).run_once()
    assert detail(client, record["id"])["status"] == "completed"


def test_demo_rejects_real_provider_and_free_profile_rejects_mock(platform):
    client, _, _ = platform
    identifier = project(client)["id"]
    assert (
        client.post(
            f"/api/projects/{identifier}/runs",
            json={"profile": "demo", "provider": "gemini", "model": "model"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/projects/{identifier}/runs",
            json={"profile": "free_research", "provider": "mock"},
        ).status_code
        == 422
    )


def test_disabled_paper_and_sse_cursor_validation(platform):
    client, settings, database = platform
    record = run(client, project(client)["id"], require_approval=False, generate_report=False)
    assert Worker(settings, database).run_once()
    result = detail(client, record["id"])
    assert result["status"] == "completed", result
    assert result["state"]["paper"] == ""
    assert not any(
        item["name"] == "research_report.md"
        for item in client.get(f"/api/runs/{record['id']}/artifacts").json()
    )
    assert (
        client.get(f"/api/runs/{record['id']}/stream", headers={"Last-Event-ID": "bad"}).status_code
        == 400
    )
    latest = client.get(f"/api/runs/{record['id']}/events").json()[-1]["id"]
    stream = client.get(f"/api/runs/{record['id']}/stream", headers={"Last-Event-ID": latest})
    assert stream.status_code == 200 and "text/event-stream" in stream.headers["content-type"]
    assert stream.text == ""


def test_import_endpoint_validates_body_and_preserves_real_upstream_evidence(platform):
    client, settings, _ = platform
    program = (
        settings.upstream_results_root
        / "circpack"
        / "gemini"
        / "test_run"
        / "investigation"
        / "ideas"
        / "001_grid"
        / "program_0"
    )
    program.mkdir(parents=True)
    (program / "metrics.json").write_text(json.dumps({"combined_score": 0.5}), encoding="utf-8")
    (program / "correct.json").write_text('{"correct":true}', encoding="utf-8")
    inventory = client.get("/api/upstream/runs").json()
    assert inventory["runs"][0]["id"] == "circpack/gemini/test_run"
    identifier = project(client)["id"]
    imported = client.post(
        f"/api/projects/{identifier}/imports", json={"upstream_id": "circpack/gemini/test_run"}
    )
    assert imported.status_code == 201, imported.text
    record = imported.json()
    assert record["status"] == "completed" and record["profile"] == "full_research"
    assert (
        record["state"]["results"]["metrics"]["evaluations"][0]["metrics"]["combined_score"] == 0.5
    )
    files = client.get(f"/api/runs/{record['id']}/artifacts").json()
    assert files[0]["name"] == "upstream_evidence.json"
    assert client.get(files[0]["download_url"]).json()["source"] == "upstream_agsci"
    assert (
        client.post(
            f"/api/projects/{identifier}/imports", json={"upstream_id": "../.env"}
        ).status_code
        == 422
    )


def test_explicit_paused_provider_switch_preserves_ledger(platform):
    from src.research_platform.services import refresh_usage

    client, settings, database = platform
    record = run(
        client,
        project(client)["id"],
        profile="free_research",
        provider="gemini",
        model="gemini-2.5-flash",
    )
    path = f"/api/runs/{record['id']}/model"
    assert (
        client.patch(path, json={"provider": "groq", "model": "another-model"}).status_code == 409
    )
    with database.sessions.begin() as session:
        row = session.get(Run, record["id"])
        row.status = "paused"
        job = session.scalar(select(Job).where(Job.run_id == row.id))
        job.status = "waiting_v2"
        session.add(
            ModelUsage(
                run_id=row.id,
                provider=row.provider,
                model=row.model,
                stage="provider_preflight",
                input_tokens=80,
                output_tokens=0,
                reserved_output_tokens=128,
                status="reserved",
                reported=False,
            )
        )
        session.flush()
        refresh_usage(session, row)
    before = detail(client, record["id"])
    response = client.patch(path, json={"provider": "groq", "model": "another-model"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["provider"] == "groq" and updated["model"] == "another-model"
    assert (
        updated["usage"] == before["usage"]
        and updated["config"]["budgets"] == before["config"]["budgets"]
    )
    assert updated["status"] == "paused"
    assert (
        client.patch(path, json={"provider": "mock", "model": "mock-researcher"}).status_code == 422
    )
    for _ in range(2):
        assert client.get(f"/api/runs/{record['id']}/provider-readiness").json() == []
    assert detail(client, record["id"])["usage"] == before["usage"]


def test_original_web_launch_stays_disabled_without_creating_run(platform):
    client, _, _ = platform
    identifier = project(client)["id"]
    before = client.get("/api/runs").json()
    response = client.post(
        f"/api/projects/{identifier}/runs",
        json={
            "engine": "original",
            "profile": "full_research",
            "provider": "gemini",
            "model": "fixture-model",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "capability_unavailable"
    assert client.get("/api/runs").json() == before


def test_worker_pauses_before_research_when_discovered_model_cannot_generate(platform):
    import httpx
    from src.research_platform.providers import ProviderRouter
    from src.research_platform.services import ResearchServices

    client, settings, database = platform
    record = run(
        client,
        project(client)["id"],
        profile="free_research",
        provider="gemini",
        model="gemini-2.5-flash",
    )
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-2.5-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                },
            )
        posts.append(request)
        return httpx.Response(404, json={"error": {"message": "secret provider echo"}})

    def factory(*args):
        return ResearchServices(
            *args,
            router=ProviderRouter(
                client=httpx.Client(transport=httpx.MockTransport(handler)),
                environ={"GEMINI_API_KEY": "fixture"},
            ),
        )

    assert Worker(settings, database, services_factory=factory).run_once()
    updated = detail(client, record["id"])
    assert updated["status"] == "paused" and "model_unavailable" in updated["error"]
    assert updated["usage"]["calls"] == 1 and updated["usage"]["remaining_calls"] == 19
    assert client.get(f"/api/runs/{record['id']}/experiments").json() == []
    for _ in range(2):
        readiness = client.get(f"/api/runs/{record['id']}/provider-readiness").json()
        assert readiness[0]["error"] == "model_unavailable"
        assert readiness[0]["generation_verified"] is False
        assert "secret provider echo" not in str(readiness)
    assert len(posts) == 1
