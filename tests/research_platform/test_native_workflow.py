"""Real durable graph control with synthetic services, never live research evidence."""

from __future__ import annotations

import copy
import json

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.research_platform.preparation import TaskPreparationError
from src.research_platform.workflow import create_workflow, initial_state, node_name

QUESTION = "Does shortest-processing-time scheduling improve total completion time over FIFO?"
DIGEST = "a" * 64
CONFIG = {"configurable": {"thread_id": "native-fixture"}, "recursion_limit": 1000}


class NativeServices:
    """Fixture I/O records what the real graph authorizes and in which order."""

    def __init__(self, *, iterate=False, fail_first=False, missing_digest=False, responses=None):
        self.calls = []
        self.events = []
        self.programs = []
        self.executions = []
        self.artifacts = {}
        self.model_requests = []
        self.iterate = iterate
        self.fail_first = fail_first
        self.missing_digest = missing_digest
        self.identity = {"provider": "fixture-provider", "model": "fixture-model"}
        self.responses = responses or {}

    def execution_identity(self):
        return dict(self.identity)

    def emit(self, stage, kind, message, data):
        self.events.append((stage, kind, copy.deepcopy(data)))

    def control(self):
        return "none"

    def budget_available(self):
        return True

    def model(self, stage, prompt, **kwargs):
        self.calls.append(stage)
        self.model_requests.append((stage, prompt, kwargs))
        responses = {
            "planning": {
                "summary": "Synthetic fixture plan for a paired scheduling comparison.",
                "steps": ["Run both policies on the same frozen job instances."],
                "hypotheses": [
                    {
                        "id": "h1",
                        "statement": "The candidate may reduce total completion time.",
                        "test": "Compare independently measured paired seed observations.",
                    }
                ],
                "baseline": {"policy": "FIFO"},
                "risks": ["Synthetic job instances may not generalize."],
                "required_resources": {"runtime": "Python standard library in Docker"},
            },
            "ideas": {"ideas": [idea()]},
            "selection": {"idea_id": "spt", "rationale": "Fixture selection"},
            "evaluation": {
                "interpretation": "Only synthetic fixture observations are available.",
                "decision": "iterate" if self.iterate else "synthesize",
                "limitations": ["This unit test supplies no live scientific evidence."],
                "rationale": "Summarize or refine only the recorded fixture measurements.",
            },
        }
        if self.responses.get(stage):
            value = self.responses[stage].pop(0)
            return value if isinstance(value, str) else json.dumps(value)
        return json.dumps(responses[stage]) if stage in responses else "Synthetic fixture only."

    def feasibility(self, state):
        self.calls.append("feasibility")
        assert state["question"] == QUESTION
        return {"supported": True, "protocol": "scheduling_v1", "reason": "Fixture scope"}

    def literature(self, question):
        self.calls.append("literature")
        return []

    def prepare(self, state):
        self.calls.append("prepare")
        assert state["feasibility"]["supported"]
        plan = {
            "prepared_artifact_id": "fixture-prepared-artifact",
            "prepared_digest": "b" * 64,
            "baseline_sha256": "c" * 64,
            "spec": {"research_question": QUESTION, "seeds": [7, 11]},
        }
        if not self.missing_digest:
            plan["approval_digest"] = DIGEST
        return plan

    def evaluator_validation(self, state):
        self.calls.append("evaluator_validation")
        assert state["experiment_config"]["prepared_artifact_id"]
        return {
            **state["experiment_config"],
            "evaluation_validation": {"dataset_sha256": "d" * 64, "evaluator_sha256": "e" * 64},
            "validation_artifact_id": "fixture-validation-artifact",
        }

    def generate_program(self, state):
        self.calls.append("generate_program")
        assert state["approval"]["approved"]
        assert state["approval"]["approval_digest"] == DIGEST
        assert state["experiment_config"]["evaluation_validation"]["dataset_sha256"]
        self.programs.append(copy.deepcopy(state))
        return {"artifact_id": f"fixture-candidate-{len(self.programs)}", "origin": "fixture"}

    def execute(self, state):
        self.calls.append("execute")
        assert state["program"]["artifact_id"] == f"fixture-candidate-{len(self.programs)}"
        assert state["approval"]["approved"]
        assert state["approval"]["approval_digest"] == DIGEST
        self.executions.append(copy.deepcopy(state))
        failed = self.fail_first and len(self.executions) == 1
        return {
            "status": "failed" if failed else "completed",
            "metrics": {} if failed else {"baseline_mean": 20.0, "candidate_mean": 15.0},
            "source": "synthetic_workflow_fixture",
            "demo": True,
            "per_seed": [
                {"seed": 7, "baseline": 21.0, "candidate": 15.0, "improvement": 6.0},
                {"seed": 11, "baseline": 19.0, "candidate": 15.0, "improvement": 4.0},
            ]
            if not failed
            else [],
            "statistical_summary": {
                "replications": 2,
                "paired_sign_flip_p_value": 0.5,
                "assumptions": ["Synthetic fixture assumptions only."],
            }
            if not failed
            else {},
            "execution_identity": {"baseline_sha256": "c" * 64, "candidate_sha256": "f" * 64},
            "dataset_sha256": "d" * 64,
            "evaluator_sha256": "e" * 64,
            "artifact_ids": ["fixture-measurements"],
        }

    def save_artifact(self, name, content, media_type, kind):
        self.artifacts[name] = content
        return {"id": name, "name": name, "kind": kind}


def idea(identifier="spt"):
    return {
        "id": identifier,
        "title": "Synthetic fixture candidate implementation",
        "hypothesis": "The candidate may reduce total completion time compared with FIFO.",
        "method": "Sort job indices by supplied processing durations and return the permutation.",
        "expected_outcome": "A measurable paired improvement may occur on the frozen inputs.",
        "risks": "Synthetic instances may not represent operational workloads.",
        "score": 8,
    }


def state(**config):
    return initial_state(
        "fixture-project",
        "native-fixture",
        QUESTION,
        provider="fixture-provider",
        model="fixture-model",
        config={"profile": "free_research", "require_approval": True, **config},
        budget={"max_iterations": 2, "max_experiments": 3},
    )


def advance_to_concrete_approval(graph, **config):
    graph.invoke(state(**config), CONFIG)
    assert graph.get_state(CONFIG).next == ("research_plan",)
    graph.invoke(Command(resume={"approved": True}), CONFIG)
    snapshot = graph.get_state(CONFIG)
    assert snapshot.next == ("approval_stage",)
    return snapshot


def approve(graph):
    return graph.invoke(Command(resume={"approved": True, "approval_digest": DIGEST}), CONFIG)


def test_native_nodes_and_both_approval_gates_survive_checkpoint_reopen(tmp_path):
    path = str(tmp_path / "native.sqlite")
    service = NativeServices()
    with SqliteSaver.from_conn_string(path) as saver:
        graph = create_workflow(service, saver)
        graph.invoke(state(), CONFIG)
        assert graph.get_state(CONFIG).next == ("research_plan",)
        assert service.calls == ["feasibility", "planning"]
    with SqliteSaver.from_conn_string(path) as saver:
        graph = create_workflow(service, saver)
        graph.invoke(Command(resume={"approved": True}), CONFIG)
        snapshot = graph.get_state(CONFIG)
        payload = snapshot.tasks[0].interrupts[0].value
        assert payload["approval_digest"] == DIGEST
        assert payload["experiment_config"]["validation_artifact_id"]
        assert not service.programs and not service.executions
    with SqliteSaver.from_conn_string(path) as saver:
        result = approve(create_workflow(service, saver))
    assert result["status"] == "completed"
    assert service.calls == [
        "feasibility",
        "planning",
        "literature",
        "ideas",
        "selection",
        "prepare",
        "evaluator_validation",
        "generate_program",
        "execute",
        "evaluation",
        "synthesis",
    ]
    assert len(service.executions) == 1
    assert result["validation"]["scientific_validity"] == "not_certified"
    assert "## Independently computed statistics" in result["paper"]
    assert '"paired_sign_flip_p_value": 0.5' in result["paper"]
    assert "Synthetic fixture assumptions only." in result["paper"]
    assert '"baseline_sha256": "' + "c" * 64 in result["paper"]
    assert '"candidate_sha256": "' + "f" * 64 in result["paper"]
    assert "fixture-measurements" in result["paper"]
    for stage, prompt, kwargs in service.model_requests:
        if stage in {"planning", "ideas", "selection", "evaluation"}:
            assert kwargs["json_schema"]["type"] == "object"
            assert kwargs["max_output_tokens"] == (512 if stage == "selection" else 1024)
        if stage in {"evaluation", "synthesis"}:
            context = json.loads(prompt.split("\nResearch context:\n", 1)[1])
            assert context["approved_spec"]["seeds"] == [7, 11]
            assert context["statistical_summary"]["replications"] == 2
            assert [row["seed"] for row in context["per_seed"]] == [7, 11]
            assert context["execution"]["demo"] is True
            assert context["execution"]["source"] == "synthetic_workflow_fixture"
        if stage == "synthesis":
            assert kwargs["max_output_tokens"] == 1024
            assert "at most 250 words" in prompt


@pytest.mark.parametrize("digest", [None, "", "wrong", "f" * 64])
def test_native_approval_rejects_missing_or_wrong_digest_before_program(tmp_path, digest):
    service = NativeServices()
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        advance_to_concrete_approval(graph)
        with pytest.raises(ValueError, match="does not match this frozen experiment"):
            graph.invoke(Command(resume={"approved": True, "approval_digest": digest}), CONFIG)
    assert not service.programs and not service.executions


def test_native_missing_frozen_digest_cannot_be_approved_by_missing_response(tmp_path):
    service = NativeServices(missing_digest=True)
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        advance_to_concrete_approval(graph)
        with pytest.raises(ValueError, match="does not match this frozen experiment"):
            graph.invoke(Command(resume={"approved": True}), CONFIG)
    assert not service.programs and not service.executions


def test_retry_at_first_native_approval_requires_another_concrete_review(tmp_path):
    service = NativeServices()
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        advance_to_concrete_approval(graph)
        graph.invoke(Command(resume={"action": "retry"}), CONFIG)
        snapshot = graph.get_state(CONFIG)
        assert snapshot.next == ("approval_stage",)
        assert snapshot.values["iteration"] == 1
        assert not snapshot.values["approval"]["approved"]
        assert not service.programs and not service.executions
        assert service.calls.count("prepare") == service.calls.count("evaluator_validation") == 2
        result = approve(graph)
    assert result["status"] == "completed"
    assert len(service.programs) == len(service.executions) == 1


@pytest.mark.parametrize("fail_first", [False, True])
def test_native_iterations_revise_only_candidate_under_same_frozen_evaluation(tmp_path, fail_first):
    service = NativeServices(iterate=not fail_first, fail_first=fail_first)
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        advance_to_concrete_approval(graph, max_iterations=2, max_retries=1)
        result = approve(graph)
    assert result["status"] == "completed"
    assert [item["iteration"] for item in service.executions] == [1, 2]
    assert len(service.programs) == 2
    assert service.executions[0]["experiment_config"] == service.executions[1]["experiment_config"]
    assert service.executions[0]["approval"] == service.executions[1]["approval"]
    assert service.calls.count("prepare") == service.calls.count("evaluator_validation") == 1
    assert service.calls.count("ideas") == service.calls.count("selection") == 1
    assert service.programs[1]["results"]["status"] == ("failed" if fail_first else "completed")


def test_resumed_execution_identity_updates_checkpoint_and_report(tmp_path):
    path = str(tmp_path / "native.sqlite")
    service = NativeServices()
    with SqliteSaver.from_conn_string(path) as saver:
        graph = create_workflow(service, saver)
        graph.invoke(state(), CONFIG)
    service.identity = {"provider": "resumed-provider", "model": "resumed-model"}
    with SqliteSaver.from_conn_string(path) as saver:
        graph = create_workflow(service, saver)
        graph.invoke(Command(resume={"approved": True}), CONFIG)
        result = approve(graph)
        assert graph.get_state(CONFIG).values["provider"] == "resumed-provider"
        assert graph.get_state(CONFIG).values["model"] == "resumed-model"
    assert result["provider"] == "resumed-provider"
    assert "Provider: resumed-provider; model: resumed-model" in result["paper"]
    assert "Provider: fixture-provider" not in result["paper"]
    assert service.executions[0]["model"] == "resumed-model"


def test_invalid_native_ideas_stop_without_fabricating_placeholder(tmp_path):
    service = NativeServices(responses={"ideas": ["not JSON", {"ideas": []}]})
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        graph.invoke(state(), CONFIG)
        with pytest.raises(TaskPreparationError, match="ideas failed"):
            graph.invoke(Command(resume={"approved": True}), CONFIG)
        snapshot = graph.get_state(CONFIG)
    assert snapshot.values["ideas"] == []
    assert snapshot.values["selected_idea"] == {}
    assert service.calls.count("ideas") == 2
    assert "selection" not in service.calls and "prepare" not in service.calls
    assert not service.programs and not service.executions


def test_native_ideas_repair_reuses_preceding_validated_graph_stages(tmp_path):
    service = NativeServices(responses={"ideas": [{"ideas": [{"id": "broken"}]}]})
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        snapshot = advance_to_concrete_approval(graph)
    assert snapshot.values["ideas"][0]["id"] == "spt"
    assert service.calls.count("ideas") == 2
    assert service.calls.count("planning") == service.calls.count("literature") == 1


def test_foreign_native_selection_ids_exhaust_bounded_repair_without_fallback(tmp_path):
    foreign = {"idea_id": "scheduling_v1", "rationale": "A protocol is not a proposal ID."}
    service = NativeServices(responses={"selection": [foreign, foreign]})
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        graph.invoke(state(), CONFIG)
        with pytest.raises(TaskPreparationError, match="selection failed"):
            graph.invoke(Command(resume={"approved": True}), CONFIG)
        snapshot = graph.get_state(CONFIG)
    assert snapshot.values["selected_idea"] == {}
    assert service.calls.count("selection") == 2
    assert service.calls.count("ideas") == 1
    assert "prepare" not in service.calls


def test_native_selection_sees_actual_options_and_can_repair_to_second_candidate(tmp_path):
    service = NativeServices(
        responses={
            "ideas": [{"ideas": [idea("first"), idea("second")]}],
            "selection": [
                {"idea_id": "invented", "rationale": "This ID is unavailable."},
                {"idea_id": "second", "rationale": "The second supplied proposal is feasible."},
            ],
        }
    )
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        snapshot = advance_to_concrete_approval(graph)
    assert snapshot.values["selected_idea"]["id"] == "second"
    requests = [prompt for stage, prompt, _ in service.model_requests if stage == "selection"]
    assert len(requests) == 2
    for prompt in requests:
        context_json = prompt.split("\nResearch context:\n", 1)[1]
        context = json.loads(context_json)
        scientific_fields = ("id", "title", "hypothesis", "method", "risks", "score")
        assert context["ideas"] == [
            {key: proposal[key] for key in scientific_fields}
            for proposal in (idea("first"), idea("second"))
        ]
        assert set(context) == {"question", "objectives", "constraints", "protocol", "ideas"}
        assert context["question"] == QUESTION
        assert context["protocol"] == "scheduling_v1"
        assert context_json == json.dumps(
            context, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    assert "Repair ONLY this component" in requests[1]


@pytest.mark.parametrize("stage", ["planning", "evaluation"])
def test_native_narrative_requires_fields_instead_of_lenient_prose(tmp_path, stage):
    service = NativeServices(responses={stage: [{"interpretation": "Incomplete response."}] * 2})
    with SqliteSaver.from_conn_string(str(tmp_path / "native.sqlite")) as saver:
        graph = create_workflow(service, saver)
        if stage == "planning":
            with pytest.raises(TaskPreparationError, match="planning failed"):
                graph.invoke(state(), CONFIG)
        else:
            advance_to_concrete_approval(graph)
            with pytest.raises(TaskPreparationError, match="evaluation failed"):
                approve(graph)
            assert graph.get_state(CONFIG).values["results"]["status"] == "completed"
            assert len(service.executions) == 1
    assert service.calls.count(stage) == 2
    assert "synthesis" not in service.calls


def test_direct_graph_stage_audit_reuses_exact_native_nodes_without_mutating_state():
    service = NativeServices()
    graph = create_workflow(service, None)
    original = state()
    original["feasibility"] = {"supported": True, "protocol": "scheduling_v1"}
    before = copy.deepcopy(original)
    ideas_update = graph.nodes[node_name("ideas")].bound.invoke(copy.deepcopy(original))
    selection_update = graph.nodes[node_name("selection")].bound.invoke(
        {**copy.deepcopy(original), **ideas_update}
    )
    assert original == before
    assert service.calls == ["ideas", "selection"]
    assert selection_update["selected_idea"]["id"] == "spt"
    assert not service.programs and not service.executions
