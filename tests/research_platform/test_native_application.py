"""Complete native app with mock Groq transport and actual isolated Docker programs.

Fixtures are test inputs, not live model generation or new scientific evidence.
"""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.research_platform.backend.app import create_app
from src.research_platform.config import Settings
from src.research_platform.database import Database, ModelUsage
from src.research_platform.dynamic_execution import DynamicExperimentExecutor
from src.research_platform.experiment_contract import expected_evaluation
from src.research_platform.literature import LiteratureClient, LiteratureError
from src.research_platform.providers import ProviderRouter
from src.research_platform.services import ResearchServices
from src.research_platform.worker import Worker
from test_dynamic_execution import FixtureExecutor, prepared
from test_native_workflow import NativeServices


@pytest.mark.parametrize("protocol", ["scheduling_v1", "regression_v1"])
@pytest.mark.parametrize("boundary", ["offline", "selected", "docker"])
def test_native_application_approvals_docker_metrics_and_report(
    tmp_path, protocol, boundary, monkeypatch
):
    executor = DynamicExperimentExecutor(fixture_root=tmp_path / "probe")
    if boundary != "docker":
        monkeypatch.setattr(
            ResearchServices,
            "dynamic_executor",
            lambda self: FixtureExecutor(
                fixture_root=self.settings.artifact_root.parent / "private-evaluations"
            ),
        )
    capabilities = executor.capabilities() if boundary == "docker" else {"ready": True}
    if not capabilities["ready"]:
        pytest.skip(capabilities.get("reason", "Reviewed Docker image unavailable"))
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    db = Database(settings.database_url)
    contract = prepared(protocol)
    dispatches = []
    stages = []
    values = offline_values(contract)

    factory = offline_factory(
        db, contract, dispatches, stages, values, conservative_usage=boundary == "selected"
    )

    with TestClient(create_app(settings, database=db)) as client:
        project = client.post(
            "/api/projects",
            json={
                "title": "Offline native application validation",
                "question": contract.spec.research_question,
            },
        ).json()
        selected_ids = []
        if boundary == "selected":
            from test_literature import oa, cr

            with httpx.Client(
                transport=httpx.MockTransport(
                    lambda req: httpx.Response(
                        200, json=oa() if req.url.host == "api.openalex.org" else cr()
                    )
                )
            ) as transport:
                library = LiteratureClient(
                    settings.artifact_root.parent / "literature-cache", client=transport
                )
                selected_ids = [library.discover("Fixture selection")["papers"][0]["selection_id"]]
        response = client.post(
            f"/api/projects/{project['id']}/runs",
            json={
                "profile": "free_research",
                "provider": "groq",
                "model": "openai/gpt-oss-20b",
                "selected_paper_ids": selected_ids,
            },
        )
        assert response.status_code == 201, response.text
        run_id = response.json()["id"]
        worker = Worker(settings, db, services_factory=factory)
        for gate in ["research_plan", "approval"]:
            assert worker.run_once()
            run = client.get(f"/api/runs/{run_id}").json()
            assert run["status"] == "awaiting_approval", run.get("error")
            assert run["approval"]["gate"] == gate
            assert not client.get(f"/api/runs/{run_id}/experiments").json()
            approval = {"approved": True}
            if gate == "approval":
                approval["approval_digest"] = run["state"]["experiment_config"]["approval_digest"]
            assert client.post(f"/api/runs/{run_id}/approve", json=approval).status_code == 200
        assert worker.run_once()
        run = client.get(f"/api/runs/{run_id}").json()
        assert run["status"] == "completed", run.get("error")
        assert run["usage"]["calls"] == len(dispatches) <= 20
        assert run["usage"]["estimated_cost"] is None
        assert stages.count("provider_preflight") == 3
        experiments = client.get(f"/api/runs/{run_id}/experiments").json()
        assert experiments and all(e["status"] == "completed" for e in experiments)
        assert client.get(f"/api/runs/{run_id}/metrics").json()[0]["metrics"]
        events = client.get(f"/api/runs/{run_id}/events").json()
        if boundary == "selected":
            assert run["state"]["literature"][0]["title"] == "A real metadata record"
            assert run["state"]["literature"][0]["selection"] == "explicit_user_selection"
            assert any(e["kind"] == "selected_literature" for e in events)
            from src.research_platform.grounding import verify_grounding

            manifest = verify_grounding(run["state"])
            assert manifest and manifest["citation_ids"] == [run["state"]["literature"][0]["id"]]
            plan = run["state"]["experiment_config"]
            assert plan["spec"]["hypothesis"] == manifest["hypothesis"]
            assert (
                run["state"]["results"]["literature_grounding"]["grounding_sha256"]
                == plan["grounding_sha256"]
            )
            assert experiments[0]["configuration"]["grounding_sha256"] == plan["grounding_sha256"]
        else:
            assert any(
                e["kind"] == "warning" and "without retrieved citations" in e["message"]
                for e in events
            )
        artifacts = client.get(f"/api/runs/{run_id}/artifacts").json()
        manuscript = next(a for a in artifacts if a["name"] == "research_report.md")
        download = client.get(manuscript["download_url"])
        assert (
            download.status_code == 200 and "attachment" in download.headers["content-disposition"]
        )
        assert "AI-generated" in download.text
        assert "test-only" not in download.text
        if boundary == "selected":
            assert "Literature-grounded hypothesis" in download.text
            assert (
                "## References" in download.text and "https://doi.org/10.1000/abc" in download.text
            )
            assert "AI interpretation" in download.text and "not verified" in download.text
        before = run.copy()
        for _ in range(2):
            view = client.get(f"/api/runs/{run_id}/report")
            assert view.status_code == 200
            assert view.json()["markdown"] == download.text
            assert view.json()["original_artifact_id"] == manuscript["id"]
        assert client.get(f"/api/runs/{run_id}").json() == before


def offline_factory(
    db, contract, dispatches, stages, values, *, conservative_usage=False, request_log=None
):
    def factory(*args):
        def respond(request):
            assert request.url.host == "api.groq.com"
            if request.method == "GET":
                return httpx.Response(
                    200, json={"data": [{"id": "openai/gpt-oss-20b", "context_window": 131072}]}
                )
            with db.sessions() as session:
                rows = list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == args[2])))
                row = next(
                    row for row in rows if row.status == "reserved" and row.id not in dispatches
                )
                dispatches.append(row.id)
                stage = row.stage
                stages.append(stage)
                from src.research_platform.database import Run

                selected = session.get(Run, args[2]).config.get("selected_literature")
                charged_input = row.input_tokens if conservative_usage else 80
                if request_log is not None:
                    request_log.append(
                        {
                            "stage": stage,
                            "estimated_input": row.input_tokens,
                            "output_cap": row.reserved_output_tokens,
                            "payload": json.loads(request.content),
                        }
                    )
                if stage == "ideas" and selected:
                    prompt = json.loads(request.content)["messages"][-1]["content"]
                    assert all(
                        paper["title"] in prompt and paper["id"] in prompt for paper in selected
                    )
            value = values.get(stage)
            if value is None:
                value = json.loads(NativeServices().model(stage, "Fixture only"))
            if selected and stage == "planning":
                for hypothesis in value["hypotheses"]:
                    hypothesis["citation_ids"] = [selected[0]["id"]]
            if selected and stage == "ideas":
                for idea in value["ideas"]:
                    idea.update(
                        citation_ids=[selected[0]["id"]],
                        literature_rationale="Fixture AI interpretation of selected source metadata; not verified findings or novelty.",
                        hypothesis=contract.spec.hypothesis,
                    )
            text = value if isinstance(value, str) else json.dumps(value)
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": charged_input, "completion_tokens": 120},
                },
            )

        router = ProviderRouter(
            client=httpx.Client(transport=httpx.MockTransport(respond)),
            max_attempts=1,
            environ={
                "GROQ_API_KEY": "test-only",
                "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
                "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256(b"test-only").hexdigest(),
            },
        )
        services = ResearchServices(*args, router=router)

        class UnavailableLiterature:
            def search(self, *args, **kwargs):
                raise LiteratureError("Test offline retrieval unavailable")

            def close(self):
                pass

        services.retrieval.close()
        services.retrieval = UnavailableLiterature()
        return services

    return factory


def offline_values(contract):
    values = {
        "provider_preflight": "OK",
        "feasibility": contract.feasibility.model_dump(mode="json"),
        "experiment_spec": contract.spec.model_dump(mode="json"),
        "baseline_program": {
            "source": contract.baseline.source,
            "description": contract.baseline.description,
        },
        "evaluation_contract": expected_evaluation(contract.spec).model_dump(mode="json"),
        "candidate_program": {
            "source": contract.candidate.source,
            "description": contract.candidate.description,
        },
        "synthesis": "Offline transport fixture interpretation; measurements are from isolated Docker. No literature or novelty was verified.",
    }

    return values
