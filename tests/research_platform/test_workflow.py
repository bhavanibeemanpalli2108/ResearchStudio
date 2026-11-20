"""Exercise actual LangGraph checkpoints and human interrupts, without network I/O."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.research_platform.workflow import (
    WorkflowBudgetExceeded,
    create_workflow,
    initial_state,
)


class Services:
    def __init__(self):
        self.events: list[tuple[str, str, dict[str, Any]]] = []
        self.calls: list[str] = []
        self.executions: list[dict[str, Any]] = []
        self.artifacts: dict[str, str] = {}
        self.available = True
        self.command = "none"
        self.fail_execution = False
        self.iterate = False
        self.provider_error: Exception | None = None

    def emit(self, stage, kind, message, data):
        self.events.append((stage, kind, data))

    def model(self, stage, prompt):
        self.calls.append(stage)
        if self.provider_error:
            raise self.provider_error
        responses = {
            "planning": {
                "summary": "Compare fixed policies",
                "steps": ["control", "intervention"],
                "hypotheses": [{"id": "h1", "statement": "A may improve B", "test": "fixed seeds"}],
            },
            "ideas": {
                "ideas": [
                    {"id": "a", "title": "Candidate A", "hypothesis": "A may improve B"},
                    {"id": "b", "title": "Candidate B", "hypothesis": "B may improve A"},
                ]
            },
            "selection": {"idea_id": "a", "rationale": "Lower compute cost"},
            "experiment_plan": {
                "baseline": "fixed",
                "metrics": ["score"],
                "success_criteria": "larger score",
                "reproducibility": "seed=7",
            },
            "evaluation": {
                "interpretation": "Observed score only",
                "limitations": ["one seed"],
                "decision": "iterate" if self.iterate else "synthesize",
            },
        }
        return (
            json.dumps(responses[stage])
            if stage in responses
            else "Recorded evidence needs replication."
        )

    def literature(self, question):
        return [{"title": "A source", "url": "https://example.org/study", "source": "fixture"}]

    def execute(self, state):
        self.executions.append(dict(state))
        return {
            "status": "failed" if self.fail_execution else "completed",
            "metrics": {"score": 0.75},
            "logs": "adapter log",
            "configuration": {"seed": 7},
            "source": "deterministic_fixture",
            "demo": True,
        }

    def save_artifact(self, name, content, media_type, kind):
        self.artifacts[name] = content
        return {"id": name, "name": name, "media_type": media_type, "kind": kind}

    def control(self):
        return self.command

    def budget_available(self):
        return self.available


@pytest.fixture
def saver():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    yield SqliteSaver(connection)
    connection.close()


def state(**config):
    return initial_state("p", "r", "Does A improve B?", objectives=["measure score"], config=config)


CONFIG = {"configurable": {"thread_id": "r"}, "recursion_limit": 1000}


def test_real_graph_records_observations_and_discloses_mock(saver):
    service = Services()
    graph = create_workflow(service, saver)
    result = graph.invoke(state(require_approval=False), CONFIG)
    assert result["status"] == "completed"
    assert result["analysis"]["observed_metrics"] == {"score": 0.75}
    assert "DEMONSTRATION / MOCK RUN" in result["paper"]
    assert "AI-generated" in result["paper"]
    assert "0.75" in result["paper"]
    assert "one seed" in result["paper"]
    assert "deterministic_fixture" in result["paper"]
    assert result["validation"]["scientific_validity"] == "not_certified"
    assert service.artifacts["research_report.md"] == result["paper"]
    assert any(kind == "decision" for _, kind, _ in service.events)
    assert graph.get_state(CONFIG).next == ()


def test_human_gates_resume_after_sqlite_reopen(tmp_path):
    path = str(tmp_path / "checkpoints.sqlite3")
    service = Services()
    with SqliteSaver.from_conn_string(path) as checkpoint:
        graph = create_workflow(service, checkpoint)
        graph.invoke(state(), CONFIG)
        snapshot = graph.get_state(CONFIG)
        assert snapshot.next == ("research_plan",)
        assert snapshot.tasks[0].interrupts[0].value["gate"] == "research_plan"
        assert not service.executions
    with SqliteSaver.from_conn_string(path) as checkpoint:
        restarted = create_workflow(service, checkpoint)
        restarted.invoke(Command(resume={"approved": True}), CONFIG)
        assert restarted.get_state(CONFIG).next == ("approval_stage",)
        assert not service.executions
        result = restarted.invoke(Command(resume={"approved": True}), CONFIG)
        assert result["status"] == "completed"
        assert len(service.executions) == 1
        assert service.calls.count("planning") == 1


def test_approval_rejection_never_executes(saver):
    service = Services()
    graph = create_workflow(service, saver)
    graph.invoke(state(), CONFIG)
    result = graph.invoke(Command(resume={"approved": False, "action": "continue"}), CONFIG)
    assert result["status"] == "rejected"
    assert not service.executions
    assert result["approval"]["gate"] == "research_plan"


def test_changed_idea_and_constraints_require_concrete_plan_review(saver):
    service = Services()
    graph = create_workflow(service, saver)
    graph.invoke(state(), CONFIG)
    graph.invoke(Command(resume={"approved": True}), CONFIG)
    graph.invoke(
        Command(resume={"approved": True, "idea_id": "b", "constraints": {"max_seconds": 5}}),
        CONFIG,
    )
    snapshot = graph.get_state(CONFIG)
    assert snapshot.next == ("approval_stage",)
    assert snapshot.values["selected_idea"]["id"] == "b"
    assert snapshot.values["constraints"]["max_seconds"] == 5
    assert not service.executions
    graph.invoke(Command(resume={"approved": True}), CONFIG)
    assert service.executions[0]["selected_idea"]["id"] == "b"
    assert service.calls.count("experiment_plan") == 2


def test_failed_execution_retries_with_finite_attempt_budget(saver):
    service = Services()
    service.fail_execution = True
    result = create_workflow(service, saver).invoke(
        state(require_approval=False, max_iterations=3, max_retries=1), CONFIG
    )
    assert [trial["iteration"] for trial in service.executions] == [1, 2]
    assert result["outcome"] == "experiment_failed"
    assert "failed" in result["paper"]
    assert result["analysis"]["source"] == "execution_status"


def test_model_iterations_cannot_exceed_configured_limit(saver):
    service = Services()
    service.iterate = True
    result = create_workflow(service, saver).invoke(
        state(require_approval=False, max_iterations=2), CONFIG
    )
    assert len(service.executions) == 2
    assert result["iteration"] == 2
    assert "Iteration limit" in result["decisions"][-1]["rationale"]


def test_provider_quota_failure_can_resume_without_repeating_completed_nodes(saver):
    service = Services()
    service.provider_error = RuntimeError("provider quota unavailable")
    graph = create_workflow(service, saver)
    with pytest.raises(RuntimeError, match="quota"):
        graph.invoke(state(require_approval=False), CONFIG)
    assert graph.get_state(CONFIG).next == ("planning",)
    service.provider_error = None
    result = graph.invoke(None, CONFIG)
    assert result["status"] == "completed"
    assert len(service.executions) == 1
    intake_events = [event for event in service.events if event[:2] == ("intake", "node_completed")]
    assert len(intake_events) == 1


def test_budget_failure_is_resumable_at_stage_boundary(saver):
    service = Services()
    service.available = False
    graph = create_workflow(service, saver)
    with pytest.raises(WorkflowBudgetExceeded, match="planning"):
        graph.invoke(state(require_approval=False), CONFIG)
    service.available = True
    assert graph.invoke(None, CONFIG)["status"] == "completed"


def test_budget_exhausted_after_execution_routes_to_report_without_model(saver):
    service = Services()
    original_execute = service.execute

    def execute(current):
        result = original_execute(current)
        service.available = False
        return result

    service.execute = execute
    result = create_workflow(service, saver).invoke(state(require_approval=False), CONFIG)
    assert result["status"] == "completed"
    assert "synthesis" not in service.calls
    assert "evaluation" not in service.calls
    assert "budget" in result["synthesis"]
    assert result["results"]["metrics"]["score"] == 0.75


def test_pause_interrupt_and_cancel_at_node_boundaries(saver):
    service = Services()
    service.command = "pause"
    graph = create_workflow(service, saver)
    graph.invoke(state(require_approval=False), CONFIG)
    assert graph.get_state(CONFIG).tasks[0].interrupts[0].value["kind"] == "pause"
    assert not service.calls
    service.command = "none"
    result = graph.invoke(Command(resume={"action": "cancel"}), CONFIG)
    assert result["status"] == "cancelled"
    assert not service.executions


def test_pause_resume_runs_the_saved_stage_after_control_is_cleared(saver):
    service = Services()
    service.command = "pause"
    graph = create_workflow(service, saver)
    graph.invoke(state(require_approval=False), CONFIG)
    assert graph.get_state(CONFIG).next == ("pause",)
    assert graph.get_state(CONFIG).values["paused_node"] == "intake"
    service.command = "none"
    result = graph.invoke(Command(resume={"action": "continue", "approved": True}), CONFIG)
    assert result["status"] == "completed"
    assert result["paused_node"] == ""
    assert len(service.executions) == 1


def test_cancel_skips_models_and_experiments(saver):
    service = Services()
    service.command = "cancel"
    result = create_workflow(service, saver).invoke(state(), CONFIG)
    assert result["status"] == "cancelled"
    assert not service.calls
    assert not service.executions


def test_paper_disabled_still_validates_recorded_evidence(saver):
    service = Services()
    result = create_workflow(service, saver).invoke(
        state(require_approval=False, generate_report=False), CONFIG
    )
    assert result["status"] == "completed"
    assert result["paper"] == ""
    assert "research_report.md" not in service.artifacts
    assert result["validation"]["passed"]


def test_unknown_human_selection_does_not_execute(saver):
    service = Services()
    graph = create_workflow(service, saver)
    graph.invoke(state(), CONFIG)
    graph.invoke(Command(resume={"approved": True}), CONFIG)
    with pytest.raises(ValueError, match="Unknown selected idea"):
        graph.invoke(Command(resume={"approved": True, "idea_id": "missing"}), CONFIG)
    assert not service.executions


def test_large_logs_not_stored_in_checkpoint(saver):
    service = Services()
    original_execute = service.execute

    def execute(current):
        return {**original_execute(current), "logs": "x" * 100000, "binary": b"opaque bytes"}

    service.execute = execute
    result = create_workflow(service, saver).invoke(state(require_approval=False), CONFIG)
    assert len(result["results"]["logs"]) < 8100
    assert result["results"]["binary"] == "[binary content omitted; see artifact]"


def test_crash_after_execution_resumes_collection_without_reexecution(saver):
    service = Services()
    original_save = service.save_artifact
    failing = True

    def save(name, content, media_type, kind):
        if failing and name.startswith("results_"):
            raise OSError("artifact storage temporarily unavailable")
        return original_save(name, content, media_type, kind)

    service.save_artifact = save
    graph = create_workflow(service, saver)
    with pytest.raises(OSError, match="storage"):
        graph.invoke(state(require_approval=False), CONFIG)
    assert graph.get_state(CONFIG).next == ("collection",)
    assert len(service.executions) == 1
    failing = False
    assert graph.invoke(None, CONFIG)["status"] == "completed"
    assert len(service.executions) == 1


def test_unsupported_optional_phases_are_not_simulated(saver):
    service = Services()
    result = create_workflow(service, saver).invoke(
        state(
            require_approval=False,
            ablations=True,
            final_evaluation=True,
            supported_phases=["investigation"],
        ),
        CONFIG,
    )
    assert len(service.executions) == 1
    assert result["execution_phase"] == "investigation"
    assert not any(stage in {"ablation", "final_evaluation"} for stage, _, _ in service.events)


def test_supported_optional_phases_retain_actual_observations(saver):
    service = Services()
    result = create_workflow(service, saver).invoke(
        state(
            require_approval=False,
            ablations=True,
            final_evaluation=True,
            supported_phases=["investigation", "ablations", "final_evaluation"],
        ),
        CONFIG,
    )
    assert [trial["execution_phase"] for trial in service.executions] == [
        "investigation",
        "ablations",
        "final_evaluation",
    ]
    assert result["execution_phase"] == "final_evaluation"
    assert len(result["experiment_history"]) == 3
    assert "final_evaluation_1.json" in service.artifacts
