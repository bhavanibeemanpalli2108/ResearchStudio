"""Offline prompt limits, provenance and dispatch accounting regression tests."""

from copy import deepcopy
import json
import httpx
import pytest
import test_api as api_tests
from sqlalchemy import select
from test_api import project, run

from test_grounding import grounded_state
from src.research_platform.prompt_budget import literature_context, compact_schema, future_capacity
from src.research_platform.grounding import grounding_manifest
from src.research_platform.experiment_contract import ExperimentSpec
from src.research_platform.providers import ProviderRouter, ProviderError
from src.research_platform.services import ResearchServices
from src.research_platform.worker import Worker
from src.research_platform.ledger import BudgetExceeded
from src.research_platform.database import Run, ModelUsage

settings = api_tests.settings
platform = api_tests.platform


def test_large_literature_is_bounded_deduplicated_without_changing_snapshot_binding():
    state = grounded_state()
    for paper in state["config"]["selected_literature"]:
        paper["abstract"] = "source excerpt " * 4000
        paper["provenance"] *= 100
    before = deepcopy(state)
    manifest = grounding_manifest(state)
    rows = literature_context(state, "ideas")
    assert len(rows) == 5 and sum(len(p.get("abstract", "")) for p in rows) == 480
    assert rows[1]["abstract_same_as"] == rows[0]["id"]
    assert all("provenance" not in p for p in rows)
    assert all("abstract" not in p for p in literature_context(state, "selection"))
    assert state == before and grounding_manifest(state) == manifest
    for i, paper in enumerate(state["config"]["selected_literature"]):
        paper["abstract"] += str(i)
    assert sum(len(p.get("abstract", "")) for p in literature_context(state, "planning")) <= 2400


@pytest.mark.parametrize("abstract", [None, "", "   ", {}, [], 12])
def test_missing_or_malformed_abstracts_are_not_invented(abstract):
    state = {"config": {"selected_literature": [{"id": "doi:real", "abstract": abstract}] * 2}}
    assert literature_context(state, "planning") == [{"id": "doi:real"}]


def test_schema_annotations_removed_without_losing_validation_or_property_names():
    schema = ExperimentSpec.model_json_schema()
    compact = compact_schema(schema)
    assert len(json.dumps(compact)) < len(json.dumps(schema))
    assert "title" in compact["properties"] and compact["required"] == schema["required"]
    assert compact["$defs"]["SchedulingDataset"]["properties"]["job_count"]["maximum"] == 64


def claimed_services(platform, *, budgets=None):
    client, config, db = platform
    record = run(
        client,
        project(client)["id"],
        profile="free_research",
        provider="gemini",
        model="model",
        **({"budgets": budgets} if budgets else {}),
    )
    worker = Worker(config, db)
    assert worker.claim()[0] == record["id"]
    requests = []
    router = ProviderRouter(
        client=httpx.Client(
            transport=httpx.MockTransport(lambda req: requests.append(req) or httpx.Response(500))
        ),
        environ={"GEMINI_API_KEY": "fake-only"},
        max_attempts=1,
    )
    service = ResearchServices(config, db, record["id"], worker.owner, router=router)
    return service, db, record["id"], requests


def test_oversized_prompt_rejected_before_discovery_or_generation_and_no_reservation(platform):
    service, db, rid, requests = claimed_services(platform)
    try:
        with pytest.raises(BudgetExceeded, match="No provider request dispatched"):
            service.model("planning", "x" * 40000)
        assert not requests
        with db.sessions() as session:
            assert list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == rid))) == []
        events = platform[0].get(f"/api/runs/{rid}/events").json()
        diagnostic = next(e["data"] for e in events if e["kind"] == "budget_request_rejected")
        assert diagnostic["dispatched"] is False and diagnostic["protected_future_input"] >= 8192
    finally:
        service.close()


def test_atomic_headroom_and_uncertain_reservations_survive_service_restart(platform):
    service, db, rid, requests = claimed_services(platform)
    try:
        service.reserve_call("gemini", "model", "planning", "x" * 18000, 1024)
        with pytest.raises(BudgetExceeded):
            service.reserve_call("gemini", "model", "planning", "y" * 10000, 1024)
        other = ResearchServices(
            service.settings, db, rid, service.owner, router=ProviderRouter(environ={})
        )
        try:
            with pytest.raises(BudgetExceeded):
                other.check_request("gemini", "model", "planning", "y" * 10000, 1024)
            with db.sessions() as session:
                rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == rid)))
                assert len(rows) == 1 and rows[0].status == "reserved" and not rows[0].reported
        finally:
            other.close()
        assert requests == [] and future_capacity("synthesis") == (0, 0, 0)
    finally:
        service.close()


@pytest.mark.parametrize(
    "status,code,category",
    [
        (400, "context_length_exceeded", "context_budget_exceeded"),
        (400, "json_validate_failed", "malformed_structured_output"),
        (404, "model_not_found", "model_unavailable"),
        (429, "rate_limit_exceeded", "rate_limit"),
        (503, "error", "provider_unavailable"),
    ],
)
def test_safe_classified_failures_do_not_expose_body_or_credential(status, code, category):
    failures = []
    router = ProviderRouter(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    status, json={"error": {"code": code, "message": "private credential in body"}}
                )
            )
        ),
        environ={"GEMINI_API_KEY": "private"},
        max_attempts=1,
        on_failure=lambda stage, data: failures.append(data),
    )
    with pytest.raises(ProviderError):
        router._request(
            "gemini",
            "POST",
            "https://example.invalid",
            request_context=("model", "planning", "private prompt", 128),
        )
    assert failures[0]["category"] == category and failures[0]["status_code"] == status
    assert "private" not in json.dumps(failures)


def test_timeout_is_distinct_from_transport_and_keeps_uncertainty():
    def timeout(req):
        raise httpx.ReadTimeout("private detail", request=req)

    failures = []
    router = ProviderRouter(
        client=httpx.Client(transport=httpx.MockTransport(timeout)),
        environ={"GEMINI_API_KEY": "fake"},
        max_attempts=1,
        on_failure=lambda stage, data: failures.append(data),
    )
    with pytest.raises(ProviderError):
        router._request(
            "gemini",
            "POST",
            "https://example.invalid",
            request_context=("model", "planning", "secret", 128),
        )
    assert failures[0]["category"] == "timeout" and failures[0]["reservation_retained"]


def test_cancel_before_reservation_does_not_dispatch_or_charge(platform):
    from src.research_platform.execution import ExecutionCancelled

    service, db, rid, requests = claimed_services(platform)
    try:
        with db.sessions.begin() as session:
            session.get(Run, rid).control = "cancel"
        with pytest.raises(ExecutionCancelled):
            service.reserve_call("gemini", "model", "planning", "question", 128)
        with db.sessions() as session:
            assert list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == rid))) == []
        assert not requests
    finally:
        service.close()


def test_component_repair_cannot_consume_protected_final_stage_capacity(platform):
    from src.research_platform.preparation import _stage
    from src.research_platform.narrative_contracts import ResearchPlan

    service, db, rid, requests = claimed_services(platform)
    attempts = []

    def malformed(stage, prompt, **kwargs):
        attempts.append(stage)
        service.reserve_call("gemini", "model", stage, "x" * 12000, 1024)
        return "not JSON"

    try:
        with pytest.raises(BudgetExceeded):
            _stage("planning", ResearchPlan, "bounded component", malformed, max_repairs=2)
        assert len(attempts) == 2 and not requests
        with db.sessions() as session:
            assert (
                len(list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == rid)))) == 1
            )
    finally:
        service.close()


def test_native_default_stops_after_one_uncertain_http_attempt(platform):
    service, db, rid, requests = claimed_services(platform)
    default = ResearchServices(service.settings, db, rid, service.owner)
    try:
        assert default.router.max_attempts == 1
    finally:
        default.close()
        service.close()
