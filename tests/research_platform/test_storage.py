"""Durable accounting, immutable artifacts, and independent worker ownership."""

from __future__ import annotations

import dataclasses
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from langgraph.types import Interrupt
from sqlalchemy import inspect, select, text

from src.research_platform.artifacts import ArtifactStore
from src.research_platform.checkpoints import CheckpointJSON
from src.research_platform.config import Settings
from src.research_platform.database import (
    Database,
    Experiment,
    Job,
    ModelUsage,
    Project,
    Run,
    WorkflowEvent,
)
from src.research_platform.execution import ExecutionTimeout
from src.research_platform.providers import ProviderRouter, RateLimitError
from src.research_platform.schemas import RunCreate
from src.research_platform.services import (
    BudgetExceeded,
    ExecutionInterrupted,
    LostLease,
    ResearchServices,
    refresh_usage,
)
from src.research_platform.worker import Worker
from src.research_platform.workflow import workflow_topology


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'platform.sqlite').as_posix()}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.sqlite",
        upstream_results_root=tmp_path / "upstream",
    )
    settings.prepare()
    database = Database(settings.database_url)
    database.migrate()
    yield settings, database
    database.engine.dispose()


def seed(database: Database, **configuration) -> str:
    config = RunCreate(**configuration).model_dump()
    with database.sessions.begin() as session:
        project = Project(
            title="Storage test",
            question="Does the bounded baseline improve?",
            domain="Testing",
            objectives=[],
            references=[],
        )
        session.add(project)
        session.flush()
        run = Run(
            project_id=project.id,
            profile=config["profile"],
            provider=config["provider"],
            model=config["model"],
            config=config,
        )
        session.add(run)
        session.flush()
        refresh_usage(session, run)
        session.add(Job(run_id=run.id))
        return run.id


def test_migrations_are_repeatable_and_persist_after_connection_restart(storage):
    settings, database = storage
    identifier = seed(database)
    database.migrate()
    tables = set(inspect(database.engine).get_table_names())
    assert {
        "alembic_version",
        "rp_projects",
        "rp_runs",
        "rp_jobs",
        "rp_events",
        "rp_model_usage",
        "rp_artifacts",
    } <= tables
    database.engine.dispose()
    reopened = Database(settings.database_url)
    reopened.migrate()
    try:
        with reopened.sessions() as session:
            assert session.get(Run, identifier).status == "queued"
            assert (
                session.scalar(text("select version_num from alembic_version"))
                == "0002_gateway_grants"
            )
    finally:
        reopened.engine.dispose()


def test_competing_workers_claim_only_one_job_at_concurrency_limit(storage):
    settings, database = storage
    identifiers = {seed(database), seed(database)}
    workers = [Worker(settings, database), Worker(settings, database)]
    barrier = threading.Barrier(2)

    def claim(worker):
        barrier.wait(timeout=5)
        return worker.claim()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, workers))
    claimed = [item for item in results if item is not None]
    assert len(claimed) == 1
    assert claimed[0][0] in identifiers
    with database.sessions() as session:
        jobs = list(session.scalars(select(Job)))
        assert sorted(job.status for job in jobs) == ["queued", "running"]


def test_expired_job_lease_recovers_once_and_previous_owner_loses_authority(storage):
    settings, database = storage
    identifier = seed(database)
    previous = Worker(settings, database)
    assert previous.claim()[0] == identifier
    with database.sessions.begin() as session:
        job = session.scalar(select(Job).where(Job.run_id == identifier))
        job.lease_until = time.time() - 10
    replacement = Worker(settings, database)
    assert replacement.claim()[0] == identifier
    assert previous.claim() is None
    with database.sessions() as session:
        job = session.scalar(select(Job).where(Job.run_id == identifier))
        assert job.owner == replacement.owner and job.attempts == 2
        recovered = list(
            session.scalars(
                select(WorkflowEvent).where(
                    WorkflowEvent.run_id == identifier, WorkflowEvent.kind == "recovery"
                )
            )
        )
        assert len(recovered) == 1
    services = ResearchServices(settings, database, identifier, previous.owner)
    try:
        with pytest.raises(LostLease):
            services.control()
        with pytest.raises(LostLease):
            services.emit("planning", "node_completed", "A stale worker must not publish", {})
        with pytest.raises(LostLease):
            services.save_artifact("stale.md", "stale worker output", "text/markdown", "paper")
        from src.research_platform.providers import Completion

        with pytest.raises(LostLease):
            services.finish_call(
                Completion("stale response", 1, 1, "mock", "mock-researcher", 0.0, True)
            )
    finally:
        services.close()


def test_artifacts_are_content_addressed_immutable_and_confined(storage):
    settings, database = storage
    identifier = seed(database)
    store = ArtifactStore(settings.artifact_root, database)
    first = store.save(identifier, "report.md", "version one", "text/markdown", "paper")
    replay = store.save(identifier, "report.md", "version one", "text/markdown", "paper")
    second = store.save(identifier, "report.md", "version two", "text/markdown", "paper")
    assert replay["id"] == first["id"] != second["id"]
    assert first["sha256"] == hashlib.sha256(b"version one").hexdigest()
    assert "relative_path" not in first
    assert len(store.list(identifier)) == 2
    assert store.checked_path(f"{identifier}/{first['id']}").read_text() == "version one"
    with pytest.raises(ValueError):
        store.save(identifier, "../report.md", "unsafe", "text/plain", "paper")
    with pytest.raises(ValueError):
        store.checked_path("../outside", must_exist=False)
    with pytest.raises(ValueError):
        store.save("not-an-internal-id", "safe.txt", "unsafe", "text/plain", "paper")


def test_run_call_budget_counts_reservations_and_blocks_additional_requests(storage):
    settings, database = storage
    identifier = seed(database, budgets={"max_llm_calls": 2})
    worker = Worker(settings, database)
    assert worker.claim()[0] == identifier
    services = ResearchServices(settings, database, identifier, worker.owner)
    try:
        services.reserve_call("mock", "mock-researcher", "planning", "short prompt", 128)
        services.reserve_call("mock", "mock-researcher", "planning", "second prompt", 128)
        with pytest.raises(BudgetExceeded, match="model-call"):
            services.reserve_call("mock", "mock-researcher", "planning", "third prompt", 128)
        assert services.budget_available() is False
        with database.sessions() as session:
            rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == identifier)))
            run = session.get(Run, identifier)
            assert len(rows) == 2 and run.usage["calls"] == 2
            assert run.usage["reserved_output_tokens"] == 256
            assert run.usage["output_tokens"] == 0
    finally:
        services.close()


def test_failed_provider_retries_consume_daily_budget_before_network(storage):
    base_settings, database = storage
    settings = replace(base_settings, daily_api_call_budget=2)
    identifier = seed(database, profile="free_research", provider="groq", model="test-model")
    worker = Worker(settings, database)
    assert worker.claim()[0] == identifier
    post_calls = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": "test-model", "context_window": 8192}]}
            )
        post_calls.append(request)
        return httpx.Response(429, json={"error": {"message": "quota"}})

    router = ProviderRouter(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environ={
            "GROQ_API_KEY": "test-only-fixture",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("test-only-fixture".encode()).hexdigest(),
        },
        max_attempts=2,
        sleep=lambda _: None,
        jitter=lambda: 0,
    )
    services = ResearchServices(settings, database, identifier, worker.owner, router=router)
    try:
        with pytest.raises(RateLimitError):
            services.model("planning", "short prompt")
        assert len(post_calls) == 1
        with pytest.raises(RateLimitError):
            services.model("planning", "explicit second preflight attempt")
        assert len(post_calls) == 2
        with pytest.raises(BudgetExceeded, match="daily"):
            services.model("planning", "retry after quota")
        assert len(post_calls) == 2
        with database.sessions() as session:
            rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == identifier)))
            assert len(rows) == 2
            assert all(row.status == "reserved" for row in rows)
            assert all(row.reserved_output_tokens > 0 and row.reported is False for row in rows)
    finally:
        services.close()


def test_checkpoint_json_roundtrips_interrupts_without_dynamic_constructors():
    serializer = CheckpointJSON()
    fields = {field.name for field in dataclasses.fields(Interrupt)}
    kwargs = {"value": {"kind": "approval", "gate": "research_plan"}}
    if "resumable" in fields:
        kwargs["resumable"] = True
    if "ns" in fields:
        kwargs["ns"] = ["research_plan:test"]
    original = {"interrupts": (Interrupt(**kwargs),), "state": {"question": "A question"}}
    restored = serializer.loads_typed(serializer.dumps_typed(original))
    assert isinstance(restored["interrupts"], tuple)
    assert isinstance(restored["interrupts"][0], Interrupt)
    assert restored["interrupts"][0].value == original["interrupts"][0].value
    with pytest.raises(ValueError, match="encoding"):
        serializer.loads_typed(("pickle", b"untrusted"))
    constructor = {"lc": 2, "type": "constructor", "id": ["os", "system"], "args": ["untrusted"]}
    assert serializer.loads(serializer.dumps(constructor)) == constructor


def test_checkpoint_json_stores_exceptions_as_inert_error_information():
    serializer = CheckpointJSON()
    restored = serializer.loads(serializer.dumps(BudgetExceeded("budget unavailable")))
    assert not isinstance(restored, BaseException)
    assert "budget" in str(restored).lower()


def test_workflow_topology_uses_actual_conditional_research_edges():
    topology = workflow_topology()
    nodes = {node["id"] for node in topology["nodes"]}
    edges = {(edge["source"], edge["target"]) for edge in topology["edges"]}
    assert {"intake", "research_plan", "approval", "decision", "pause", "completion"} <= nodes
    assert not any(node.endswith("_stage") for node in nodes)
    assert {
        ("decision", "execution"),
        ("decision", "ideas"),
        ("approval", "experiment_plan"),
        ("synthesis", "validation"),
    } <= edges
    assert ("planning", "execution") not in edges
    assert ("literature", "report") not in edges
    assert any(edge["kind"] == "control" for edge in topology["edges"])


class RecordingAdapter:
    """A controllable external compute boundary; no Docker or model is invoked."""

    supported_phases = ("investigation",)

    def __init__(self):
        self.calls = 0
        self.fail = True

    def execute(self, run_id, profile, configuration, workdir, cancel_check=None):
        self.calls += 1
        if self.fail:
            raise ExecutionTimeout("The fixture compute attempt exceeded its runtime")
        return {
            "status": "completed",
            "metrics": {"score": 0.75},
            "configuration": configuration,
            "logs": ["A controlled test execution completed"],
            "source": "test_fixture",
            "demo": True,
        }


def execution_state():
    return {
        "iteration": 1,
        "retries": 0,
        "execution_phase": "investigation",
        "selected_idea": {"hypothesis": "A bounded fixture hypothesis"},
        "experiment_config": {"seed": 7},
    }


def test_manual_retries_of_failed_compute_consume_the_persisted_attempt_budget(storage):
    settings, database = storage
    identifier = seed(database, budgets={"max_experiments": 2})
    worker = Worker(settings, database)
    assert worker.claim()[0] == identifier
    adapter = RecordingAdapter()
    # New service objects model separate explicit resumptions of the same
    # checkpoint. Failure cannot reset the durable count for that experiment.
    for _ in range(2):
        service = ResearchServices(settings, database, identifier, worker.owner, adapter=adapter)
        try:
            with pytest.raises(ExecutionTimeout):
                service.execute(execution_state())
        finally:
            service.close()
    final_attempt = ResearchServices(settings, database, identifier, worker.owner, adapter=adapter)
    try:
        with pytest.raises(BudgetExceeded, match="Experiment-attempt"):
            final_attempt.execute(execution_state())
    finally:
        final_attempt.close()
    assert adapter.calls == 2
    with database.sessions() as session:
        attempts = list(session.scalars(select(Experiment).where(Experiment.run_id == identifier)))
        assert len(attempts) == 1
        assert attempts[0].status == "failed"
        assert attempts[0].configuration["launch_attempts"] == 2


def test_missing_execution_receipt_pauses_recovery_then_allows_explicit_bounded_retry(storage):
    settings, database = storage
    identifier = seed(database, budgets={"max_experiments": 2})
    worker = Worker(settings, database)
    assert worker.claim()[0] == identifier
    adapter = RecordingAdapter()
    service = ResearchServices(settings, database, identifier, worker.owner, adapter=adapter)
    try:
        with pytest.raises(ExecutionTimeout):
            service.execute(execution_state())
    finally:
        service.close()
    # Reproduce a worker loss after launch: the attempt is running in storage,
    # and no receipt can certify whether the prior external process completed.
    with database.sessions.begin() as session:
        prior = session.scalar(select(Experiment).where(Experiment.run_id == identifier))
        prior.status, prior.finished_at, prior.error = "running", None, None
    adapter.fail = False
    recovered = ResearchServices(settings, database, identifier, worker.owner, adapter=adapter)
    try:
        with pytest.raises(ExecutionInterrupted, match="not repeated"):
            recovered.execute(execution_state())
    finally:
        recovered.close()
    assert adapter.calls == 1
    with database.sessions() as session:
        prior = session.scalar(select(Experiment).where(Experiment.run_id == identifier))
        assert prior.status == "failed" and prior.configuration["launch_attempts"] == 1
    resumed = ResearchServices(settings, database, identifier, worker.owner, adapter=adapter)
    try:
        measured = resumed.execute(execution_state())
        assert measured["status"] == "completed"
        # A completed execution is reconciled without spending a third attempt.
        assert resumed.execute(execution_state()) == measured
    finally:
        resumed.close()
    assert adapter.calls == 2
    with database.sessions() as session:
        prior = session.scalar(select(Experiment).where(Experiment.run_id == identifier))
        assert prior.status == "completed" and prior.configuration["launch_attempts"] == 2


def test_runtime_budget_counts_active_work_and_preserves_usage_across_human_waits(storage):
    settings, database = storage
    identifier = seed(database, budgets={"max_runtime_seconds": 10})
    worker = Worker(settings, database)
    assert worker.claim()[0] == identifier
    with database.sessions.begin() as session:
        prior = session.get(Run, identifier)
        prior.started_at = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        prior.usage = {**prior.usage, "runtime_seconds": 1.0}
    service = ResearchServices(settings, database, identifier, worker.owner)
    try:
        assert service.control() == "none"
        service.reserve_call("mock", "mock-researcher", "planning", "short prompt", 128)
        with database.sessions() as session:
            assert session.get(Run, identifier).usage["runtime_seconds"] == 1.0
        with database.sessions.begin() as session:
            prior = session.get(Run, identifier)
            prior.usage = {**prior.usage, "runtime_seconds": 11.0}
        with pytest.raises(BudgetExceeded, match="active execution"):
            service.control()
    finally:
        service.close()


@pytest.mark.parametrize(
    "outcome,code",
    [
        (404, "model_unavailable"),
        (401, "authentication_error"),
        (429, "rate_limit"),
        (503, "provider_unavailable"),
        ("network", "provider_unavailable"),
        (200, None),
    ],
)
def test_generation_preflight_is_bounded_accounted_and_redacted(storage, outcome, code):
    from src.research_platform.providers import ProviderError

    settings, database = storage
    identifier = seed(
        database,
        profile="free_research",
        provider="groq",
        model="test-model",
        budgets={"max_llm_calls": 1},
    )
    worker = Worker(settings, database)
    assert worker.claim()[0] == identifier
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": "test-model", "context_window": 8192}]}
            )
        posts.append(request)
        if outcome == "network":
            raise httpx.ConnectError("private credential in transport error", request=request)
        if outcome != 200:
            return httpx.Response(
                outcome, json={"error": {"message": "private credential in server response"}}
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "OK"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 1},
            },
        )

    router = ProviderRouter(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environ={
            "GROQ_API_KEY": "private credential",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private credential".encode()).hexdigest(),
        },
        max_attempts=3,
    )
    services = ResearchServices(settings, database, identifier, worker.owner, router=router)
    try:
        if code:
            with pytest.raises(ProviderError) as error:
                services.generation_preflight("groq", "test-model")
            assert error.value.code == code
        else:
            services.generation_preflight("groq", "test-model")
            services.generation_preflight("groq", "test-model")  # no duplicate call
        assert len(posts) == 1
        with pytest.raises(BudgetExceeded):
            services.model("planning", "Research request cannot bypass exhausted budget")
        assert len(posts) == 1
        with database.sessions() as session:
            rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == identifier)))
            run = session.get(Run, identifier)
            events = list(
                session.scalars(
                    select(WorkflowEvent).where(
                        WorkflowEvent.run_id == identifier,
                        WorkflowEvent.kind == "provider_readiness",
                    )
                )
            )
            assert len(rows) == 1 and rows[0].stage == "provider_preflight"
            assert rows[0].status == ("reserved" if code else "completed")
            assert rows[0].estimated_cost is None and run.usage["estimated_cost"] is None
            if code:
                assert rows[0].reserved_output_tokens == 128
            assert events[0].data["generation_verified"] is (code is None)
            assert "private credential" not in str([event.data for event in events])
            assert run.provider == "groq" and run.model == "test-model"
    finally:
        services.close()


def test_successful_preflight_runs_once_before_research_calls(storage):
    settings, database = storage
    identifier = seed(database, profile="free_research", provider="groq", model="test-model")
    worker = Worker(settings, database)
    worker.claim()
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": "test-model", "context_window": 8192}]}
            )
        posts.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "OK"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 1},
            },
        )

    router = ProviderRouter(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environ={
            "GROQ_API_KEY": "fixture",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("fixture".encode()).hexdigest(),
        },
    )
    services = ResearchServices(settings, database, identifier, worker.owner, router=router)
    try:
        assert services.model("planning", "First research prompt") == "OK"
        assert services.model("ideas", "Second research prompt") == "OK"
        assert len(posts) == 3  # preflight + two research calls
        with database.sessions() as session:
            rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == identifier)))
            assert [row.stage for row in rows].count("provider_preflight") == 1
            assert all(row.status == "completed" for row in rows)
    finally:
        services.close()
