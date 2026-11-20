"""Preparation tests use explicit local fixtures; acceptance uses genuine models."""

import copy
import json

import pytest
from pydantic import ValidationError

from src.research_platform.experiment_contract import (
    ExperimentSpec,
    GeneratedProgram,
    PreparedExperiment,
    canonical_hash,
    expected_evaluation,
    validate_prepared_experiment,
)
from src.research_platform.preparation import (
    TaskPreparationError,
    UnsupportedResearchError,
    assess_feasibility,
    generate_candidate,
    prepare_experiment,
)

QUESTION = "Does shortest-processing-time ordering reduce total completion time versus FIFO?"
BASELINE = 'import json, sys\nd = json.load(sys.stdin)\nprint(json.dumps({"order": list(range(len(d["durations"])))}))\n'
CANDIDATE = 'import json, sys\nd = json.load(sys.stdin)\norder = sorted(range(len(d["durations"])), key=lambda i: d["durations"][i])\nprint(json.dumps({"order": order}))\n'


def spec(question=QUESTION):
    return {
        "schema_version": 1,
        "title": "Single-machine scheduling comparison",
        "research_question": question,
        "hypothesis": "Shortest processing time reduces total completion time compared with FIFO.",
        "protocol": "scheduling_v1",
        "dataset": {
            "kind": "scheduling",
            "generator": "uniform_jobs",
            "job_count": 16,
            "machine_count": 1,
            "duration_min": 1,
            "duration_max": 40,
        },
        "evaluation": {
            "metric": "total_completion_time",
            "direction": "minimize",
            "minimum_improvement": 0.0,
        },
        "resource_limits": {"timeout_seconds": 5, "memory_mb": 256},
        "seeds": [13, 29, 47],
    }


def feasibility(protocol="scheduling_v1"):
    return {
        "supported": True,
        "protocol": protocol,
        "reason": "Synthetic computational comparison is within the available CPU scope.",
        "scope_statement": "Compare ordering policies on independent synthetic job instances.",
        "assumptions": ["Known positive durations on one machine."],
        "limitations": ["Synthetic jobs do not represent all real workloads."],
    }


class FixtureModel:
    def __init__(self, responses=None, specification=None):
        self.responses = responses or {}
        self.specification = specification or spec()
        self.calls = []

    def __call__(self, stage, prompt, **kwargs):
        self.calls.append((stage, prompt, kwargs))
        if stage in self.responses and self.responses[stage]:
            value = self.responses[stage].pop(0)
        else:
            defaults = {
                "feasibility": feasibility(self.specification["protocol"]),
                "experiment_spec": self.specification,
                "baseline_program": {
                    "source": BASELINE,
                    "description": "FIFO reference implementation in Python.",
                },
                "evaluation_contract": expected_evaluation(
                    ExperimentSpec.model_validate(self.specification)
                ).model_dump(mode="json"),
                "candidate_program": {
                    "source": CANDIDATE,
                    "description": "Order jobs by shortest processing time.",
                },
            }
            value = defaults[stage]
        return value if isinstance(value, str) else json.dumps(value)


def test_preparation_freezes_only_model_authored_components_before_approval():
    model = FixtureModel()
    persisted = {}
    prepared = prepare_experiment(
        {"question": QUESTION},
        model,
        on_component=lambda stage, value: persisted.update({stage: value}),
    )
    assert [stage for stage, _, _ in model.calls] == [
        "feasibility",
        "experiment_spec",
        "baseline_program",
        "evaluation_contract",
    ]
    assert prepared.candidate is None and prepared.baseline.origin == "model"
    assert prepared.baseline.source == BASELINE
    assert set(persisted) == {
        "feasibility",
        "experiment_spec",
        "baseline_program",
        "evaluation_contract",
    }
    assert (
        validate_prepared_experiment(prepared.contract).approval_digest == prepared.approval_digest
    )


def test_question_preserved_exactly_and_only_invalid_spec_is_repaired():
    question = QUESTION + "  \nRetain punctuation!"
    wrong = spec("An unrelated question that must not replace the user's question.")
    correct = spec(question)
    model = FixtureModel({"experiment_spec": [wrong, correct]}, specification=correct)
    prepared = prepare_experiment({"question": question}, model)
    assert prepared.spec.research_question == question
    assert [stage for stage, _, _ in model.calls].count("experiment_spec") == 2
    assert [stage for stage, _, _ in model.calls].count("baseline_program") == 1
    assert prepared.provenance["experiment_spec"].attempts == 2


def test_bad_program_repaired_without_discarding_valid_spec():
    model = FixtureModel(
        {
            "baseline_program": [
                {"source": "bad source " * 5, "description": "This is malformed source."}
            ]
        }
    )
    prepared = prepare_experiment({"question": QUESTION}, model)
    assert prepared.baseline.source == BASELINE
    counts = [stage for stage, _, _ in model.calls]
    assert counts.count("experiment_spec") == 1 and counts.count("baseline_program") == 2
    assert all("bad source" not in prompt for _, prompt, _ in model.calls)


def test_resume_retains_valid_components_without_extra_model_requests():
    persisted = {}
    model = FixtureModel()
    prepared = prepare_experiment(
        {"question": QUESTION},
        model,
        on_component=lambda stage, value: persisted.update({stage: value}),
    )
    no_calls = lambda *args, **kwargs: pytest.fail("Valid frozen component was regenerated")
    replay = prepare_experiment({"question": QUESTION}, no_calls, previous=persisted)
    assert replay.approval_digest == prepared.approval_digest


def test_model_cannot_replace_independent_evaluator():
    wrong = expected_evaluation(ExperimentSpec.model_validate(spec())).model_dump(mode="json")
    wrong["evaluator"] = "model_authored_code"
    model = FixtureModel({"evaluation_contract": [wrong, wrong]})
    with pytest.raises(TaskPreparationError, match="evaluation_contract"):
        prepare_experiment({"question": QUESTION}, model)
    counts = [stage for stage, _, _ in model.calls]
    assert counts.count("baseline_program") == 1 and counts.count("evaluation_contract") == 2


def test_candidate_generated_separately_and_cannot_change_approval_digest():
    model = FixtureModel()
    prepared = prepare_experiment({"question": QUESTION}, model)
    digest = prepared.approval_digest
    candidate = generate_candidate(
        prepared,
        model,
        {
            "metrics": {"candidate_mean": 10.0},
            "evaluation_input": {"private_label": 123456},
            "raw_predictions": [123456],
        },
    )
    with_candidate = PreparedExperiment.model_validate(
        {**prepared.model_dump(mode="json"), "candidate": candidate.model_dump(mode="json")}
    )
    assert with_candidate.approval_digest == digest
    prompt = model.calls[-1][1]
    assert "123456" not in prompt and "evaluation_input" not in prompt
    assert model.calls[-1][0] == "candidate_program"


def test_candidate_cannot_mutate_frozen_contract():
    prepared = prepare_experiment({"question": QUESTION}, FixtureModel())
    modified = prepared.model_dump(mode="json")
    modified["spec"]["seeds"] = [1, 2]
    with pytest.raises(ValidationError, match="digest mismatch"):
        validate_prepared_experiment(modified)


def test_json_artifact_roundtrip_preserves_unicode_question_and_digest():
    question = QUESTION + "  \nRetain nonbreaking hyphen: \u2011 and Unicode: \u03b4."
    specification = spec(question)
    specification["evaluation"]["minimum_improvement"] = 5
    prepared = prepare_experiment({"question": question}, FixtureModel(specification=specification))
    serialized = prepared.model_dump_json(indent=2)
    restored = PreparedExperiment.model_validate_json(serialized)
    from_dict = validate_prepared_experiment(json.loads(serialized))
    assert restored.spec.research_question == question
    assert restored.spec_hash == from_dict.spec_hash == prepared.spec_hash
    assert restored.approval_digest == from_dict.approval_digest == prepared.approval_digest


def test_mutated_prepared_instance_is_revalidated_before_candidate_generation():
    prepared = prepare_experiment({"question": QUESTION}, FixtureModel())
    prepared.spec.seeds[0] = 99
    model = lambda *args, **kwargs: pytest.fail("Mutated contract reached the model boundary")
    with pytest.raises(ValidationError, match="digest mismatch"):
        generate_candidate(prepared, model)


def test_unsupported_question_stops_without_substituting_benchmark():
    rejection = {
        **feasibility(),
        "supported": False,
        "protocol": None,
        "reason": "Requires a real clinical intervention and cannot be answered using synthetic CPU data.",
    }
    model = FixtureModel({"feasibility": [rejection]})
    with pytest.raises(UnsupportedResearchError, match="clinical"):
        prepare_experiment({"question": "Will this treatment cure a patient's disease?"}, model)
    assert [stage for stage, _, _ in model.calls] == ["feasibility"]


def test_source_validation_rejects_network_and_dynamic_execution_without_running_code():
    with pytest.raises(ValidationError):
        GeneratedProgram(
            source="import json, sys, socket\ndata = json.load(sys.stdin)\nprint(json.dumps({}))",
            description="This source uses an unavailable module.",
        )
    with pytest.raises(ValidationError):
        GeneratedProgram(
            source='import json, sys\ndata = json.load(sys.stdin)\neval("do not execute")\nprint(json.dumps({}))',
            description="This source uses dynamic evaluation.",
        )


def test_independent_regression_contract_and_candidate_redacts_generator_parameters():
    regression = spec(
        "Does a linear predictor improve held-out RMSE over a training-mean baseline?"
    )
    regression.update(
        {
            "protocol": "regression_v1",
            "dataset": {
                "kind": "regression",
                "generator": "linear",
                "train_size": 64,
                "test_size": 24,
                "feature_count": 2,
                "noise_std": 0.1,
                "coefficients": [17.654321, -23.987654],
                "intercept": 11.222333,
            },
            "evaluation": {"metric": "rmse", "direction": "minimize", "minimum_improvement": 0.0},
        }
    )
    model = FixtureModel(specification=regression)
    prepared = prepare_experiment({"question": regression["research_question"]}, model)
    generate_candidate(prepared, model)
    prompt = model.calls[-1][1]
    assert "17.654321" not in prompt and "23.987654" not in prompt and "11.222333" not in prompt
    assert prepared.evaluation_contract.output_key == "predictions"
    assert prepared.evaluation_contract.baseline_reference == "train_mean"


def test_nonfinite_json_and_bool_seed_rejected():
    from src.research_platform.preparation import response_object

    with pytest.raises(ValueError):
        response_object('{"value": NaN}')
    wrong = copy.deepcopy(spec())
    wrong["seeds"] = [True, 2]
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(wrong)


def test_schema_is_passed_to_budgeted_model_boundary():
    model = FixtureModel()
    assess_feasibility({"question": QUESTION}, model)
    _, _, kwargs = model.calls[0]
    assert kwargs["json_schema"]["type"] == "object"
    assert kwargs["max_output_tokens"] == 1536
    assert canonical_hash({"b": 1, "a": 2}) == canonical_hash({"a": 2, "b": 1})


def test_provider_structured_generation_failure_repairs_only_failed_stage():
    from src.research_platform.providers import StructuredOutputError

    fixture = FixtureModel()
    first = True
    failures = []

    def model(stage, prompt, **kwargs):
        nonlocal first
        if stage == "feasibility" and first:
            first = False
            failures.append(stage)
            raise StructuredOutputError("Provider failed to generate valid JSON", provider="groq")
        return fixture(stage, prompt, **kwargs)

    prepared = prepare_experiment({"question": QUESTION}, model)
    assert failures == ["feasibility"] and prepared.candidate is None
    assert [stage for stage, _, _ in fixture.calls] == [
        "feasibility",
        "experiment_spec",
        "baseline_program",
        "evaluation_contract",
    ]
