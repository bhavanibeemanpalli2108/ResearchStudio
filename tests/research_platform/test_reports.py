"""Deterministic final reports and read-only historical presentation regressions."""

from copy import deepcopy
from dataclasses import replace
import hashlib

from fastapi.testclient import TestClient

from apps.research_platform.backend.app import create_app
from src.research_platform.artifacts import ArtifactStore
from src.research_platform.config import Settings
from src.research_platform.database import Database, Project, Run
from src.research_platform.reports import render_report


def state():
    return {
        "run_id": "a" * 32,
        "provider": "groq",
        "model": "openai/gpt-oss-20b",
        "question": "Does SPT reduce total completion time versus FIFO?",
        "config": {"profile": "free_research", "engine": "native"},
        "plan": {"jobs": 128, "claim": "negative means better"},
        "selected_idea": {"replications_per_seed": 5},
        "synthesis": "FABRICATED CLAIM: statistically significant p=0.0001 with 9999 jobs",
        "experiment_config": {
            "approval_digest": "d" * 64,
            "spec": {
                "protocol": "scheduling_v1",
                "dataset": {"job_count": 32},
                "seeds": [42, 123, 456, 789, 101112],
                "evaluation": {"minimum_improvement": 0.1},
            },
        },
        "results": {
            "status": "completed",
            "source": "retained_fixture",
            "per_seed": [
                {
                    "seed": seed,
                    "baseline": baseline,
                    "candidate": candidate,
                    "improvement": baseline - candidate,
                }
                for seed, baseline, candidate in [
                    (42, 2845, 2150),
                    (123, 2946, 2316),
                    (456, 2993, 2027),
                    (789, 2412, 1657),
                    (101112, 2116, 1662),
                ]
            ],
            "metrics": {"baseline": 2662.4, "candidate": 1962.4, "improvement": 700.0},
            "statistical_summary": {"paired_sign_flip_p_value": 0.0625},
            "meets_minimum_improvement": True,
        },
    }


def test_approved_contract_precedes_explicit_history_and_model_claims_are_not_promoted():
    snapshot = state()
    before = deepcopy(snapshot)
    report = render_report(snapshot)
    current, history = report.split("## Historical proposals", 1)
    assert '"job_count": 32' in current and "d" * 64 in current
    assert '"jobs": 128' not in current and '"jobs": 128' in history
    assert "FABRICATED CLAIM" not in report
    assert "0.0625" in current and "does not meet the 0.05 threshold" in current
    assert "| 42 | 2845 | 2150 | 695 |" in current
    assert snapshot == before


def test_missing_measurements_or_p_value_cannot_imply_significance():
    snapshot = state()
    snapshot["results"] = {}
    report = render_report(snapshot)
    assert "No per-seed measurements" in report
    assert "statistical significance is not established" in report


def test_grounded_report_separates_source_excerpt_interpretation_and_measurement():
    from test_grounding import grounded_state

    snapshot = state()
    grounded = grounded_state()
    snapshot["selected_idea"] = grounded["selected_idea"]
    snapshot["experiment_config"].update(grounded["experiment_config"])
    report = render_report(snapshot)
    assert "Literature-grounded hypothesis" in report
    assert "not verified paper findings or novelty" in report
    assert "Genuine provided abstract excerpt." in report
    assert "No abstract was supplied" in report
    assert "## References" in report and "https://doi.org/10.1000/source1" in report
    assert "Baseline minus candidate" in report
    assert "FABRICATED CLAIM" not in report


def test_report_endpoint_preserves_state_budget_and_original_artifact(tmp_path):
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path / 'platform.db'}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    db = Database(settings.database_url)
    with TestClient(create_app(settings, database=db)) as client:
        snapshot = state()
        snapshot["paper"] = "Original immutable 128-job draft"
        with db.sessions.begin() as session:
            project = Project(
                title="Retained study", question=snapshot["question"], domain="Scheduling"
            )
            session.add(project)
            session.flush()
            session.add(
                Run(
                    id="a" * 32,
                    project_id=project.id,
                    profile="free_research",
                    provider="groq",
                    model="openai/gpt-oss-20b",
                    status="completed",
                    config=snapshot["config"],
                    state=snapshot,
                    usage={"calls": 13},
                )
            )
        source = ArtifactStore(settings.artifact_root, db).save(
            "a" * 32, "research_report.md", snapshot["paper"], "text/markdown", "paper"
        )
        before = client.get("/api/runs/" + "a" * 32).json()
        for _ in range(2):
            response = client.get("/api/runs/" + "a" * 32 + "/report")
            assert response.status_code == 200
            assert response.json()["markdown"] == render_report(snapshot)
            assert (
                response.json()["original_sha256"]
                == hashlib.sha256(snapshot["paper"].encode()).hexdigest()
            )
        assert client.get(source["download_url"]).text == snapshot["paper"]
        assert client.get("/api/runs/" + "a" * 32).json() == before
        assert client.get("/api/runs/" + "b" * 32 + "/report").status_code == 404


def test_approval_or_execution_mismatch_is_visible():
    snapshot = state()
    snapshot["results"]["configuration"] = {"spec": {"changed": True}}
    assert "Provenance mismatch" in render_report(snapshot)
    snapshot["experiment_config"] = {}
    assert "Incomplete approval provenance" in render_report(snapshot)


def test_transport_logging_does_not_publish_query_credentials(tmp_path, caplog):
    import logging

    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path / 'platform.db'}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    with caplog.at_level(logging.INFO):
        app = create_app(settings)
        assert app is not None
        logging.getLogger("httpx").info("GET https://example.invalid/?api_key=FAKE_ONLY_QUERY_KEY")
        logging.getLogger("httpcore").info("Authorization: FAKE_ONLY_HEADER_KEY")
    assert "FAKE_ONLY_QUERY_KEY" not in caplog.text
    assert "FAKE_ONLY_HEADER_KEY" not in caplog.text
