"""Independent trusted measurements over generated, isolated JSON programs."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from copy import deepcopy

import pytest

from src.research_platform.dynamic_execution import (
    DynamicExperimentExecutor,
    EvaluatorValidationError,
    FrozenTaskError,
    ProtocolError,
    _strict_output,
    _write_json,
    trusted_evaluator_selfcheck,
)
from src.research_platform.experiment_contract import (
    ExperimentSpec,
    GeneratedProgram,
    PreparedExperiment,
    canonical_hash,
    expected_evaluation,
    program_artifact,
)


REGRESSION_BASELINE = """import json,sys
data=json.load(sys.stdin)
mean=sum(row['y'] for row in data['train'])/len(data['train'])
print(json.dumps({'predictions':[mean for row in data['test']]}))
"""
REGRESSION_CANDIDATE = """import json,sys
data=json.load(sys.stdin)
xs=[row['x'][0] for row in data['train']]
ys=[row['y'] for row in data['train']]
xmean=sum(xs)/len(xs)
ymean=sum(ys)/len(ys)
slope=sum((x-xmean)*(y-ymean) for x,y in zip(xs,ys))/sum((x-xmean)**2 for x in xs)
intercept=ymean-slope*xmean
print(json.dumps({'predictions':[slope*row['x'][0]+intercept for row in data['test']]}))
"""
SCHEDULING_BASELINE = """import json,sys
data=json.load(sys.stdin)
print(json.dumps({'order':list(range(len(data['durations'])))}))
"""
SCHEDULING_CANDIDATE = """import json,sys
data=json.load(sys.stdin)
order=sorted(range(len(data['durations'])),key=lambda index:data['durations'][index])
print(json.dumps({'order':order}))
"""


def prepared(protocol="regression_v1", noise=0.0):
    regression = protocol == "regression_v1"
    spec = ExperimentSpec.model_validate(
        {
            "title": "Controlled independent measurement",
            "research_question": "Does the proposed algorithm improve its approved baseline?",
            "hypothesis": "The candidate improves a predeclared independent metric.",
            "protocol": protocol,
            "dataset": {
                "kind": "regression",
                "generator": "linear",
                "train_size": 32,
                "test_size": 16,
                "feature_count": 1,
                "noise_std": noise,
                "coefficients": [3.0],
                "intercept": 1.0,
            }
            if regression
            else {
                "kind": "scheduling",
                "generator": "uniform_jobs",
                "job_count": 12,
                "machine_count": 1,
                "duration_min": 1,
                "duration_max": 40,
            },
            "evaluation": {
                "metric": "rmse" if regression else "total_completion_time",
                "direction": "minimize",
                "minimum_improvement": 0.0,
            },
            "resource_limits": {"timeout_seconds": 30, "memory_mb": 128},
            "seeds": [7, 19, 31],
        }
    )
    baseline = program_artifact(
        GeneratedProgram(
            source=REGRESSION_BASELINE if regression else SCHEDULING_BASELINE,
            description="Generated reference implementation for the approved baseline",
        )
    )
    candidate = program_artifact(
        GeneratedProgram(
            source=REGRESSION_CANDIDATE if regression else SCHEDULING_CANDIDATE,
            description="Generated alternative algorithm for the approved task",
        )
    )
    declaration = expected_evaluation(spec)
    digest = canonical_hash(
        {
            "spec": spec.model_dump(mode="json"),
            "baseline": baseline.model_dump(mode="json"),
            "evaluation_contract": declaration.model_dump(mode="json"),
        }
    )
    return PreparedExperiment.model_validate(
        {
            "feasibility": {
                "supported": True,
                "protocol": protocol,
                "reason": "The task has a bounded independent numeric evaluation.",
                "scope_statement": "Only the declared synthetic generator supports conclusions.",
                "assumptions": ["CPU-only numerical study"],
                "limitations": ["Synthetic data"],
            },
            "spec": spec.model_dump(mode="json"),
            "baseline": baseline.model_dump(mode="json"),
            "candidate": candidate.model_dump(mode="json"),
            "evaluation_contract": declaration.model_dump(mode="json"),
            "spec_hash": canonical_hash(spec),
            "approval_digest": digest,
            "provenance": {},
        }
    )


class FixtureExecutor(DynamicExperimentExecutor):
    """Stub the external process boundary; never execute program source on host."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inputs = []
        self.baseline_wrong = False
        self.candidate_output = None

    def capabilities(self):
        return {"ready": True, "image_id": "sha256:" + "a" * 64}

    def _execute_program(self, code, input_value, resources, **kwargs):
        self.inputs.append(deepcopy(input_value))
        if "train" in input_value:
            if "\nmean=sum" in code:
                mean = sum(row["y"] for row in input_value["train"]) / len(input_value["train"])
                return {
                    "predictions": [0 if self.baseline_wrong else mean for _ in input_value["test"]]
                }
            return self.candidate_output or {
                "predictions": [3 * row["x"][0] + 1 for row in input_value["test"]]
            }
        if "order=sorted" in code:
            return self.candidate_output or {
                "order": sorted(
                    range(len(input_value["durations"])), key=lambda i: input_value["durations"][i]
                )
            }
        return {"order": list(range(len(input_value["durations"])))}


def execute(executor, contract, directory):
    frozen = executor.freeze_evaluation("run1", contract, directory)
    return executor.execute("run1", contract, directory, dataset_sha256=frozen["dataset_sha256"])


def test_frozen_private_labels_are_not_sent_to_either_program_and_are_stable(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    contract = prepared(noise=0.4)
    first = executor.freeze_evaluation("run1", contract, tmp_path / "iteration1")
    recreated = FixtureExecutor(fixture_root=tmp_path / "private")
    second = recreated.freeze_evaluation("run1", contract, tmp_path / "iteration2")
    assert first == second
    assert first["evaluator_validation"]["passed"] is True
    assert first["evaluator_validation"]["case_count"] == 9
    result = execute(executor, contract, tmp_path / "iteration1")
    assert len(executor.inputs) == 2 * len(contract.spec.seeds)
    for public in executor.inputs:
        assert set(public) == {"train", "test", "seed"}
        assert all(set(row) == {"x"} for row in public["test"])
        assert all(set(row) == {"x", "y"} for row in public["train"])
    assert result["configuration"]["hidden_labels_shared"] is False
    assert "private_salt" not in json.dumps(result)
    assert "hidden_targets" not in (tmp_path / "iteration1/public_inputs.json").read_text()


def test_fixture_path_is_compact_but_manifest_retains_full_identity(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    contract = prepared()
    run_id = "a" * 32
    executor.freeze_evaluation(run_id, contract, tmp_path / "evaluation")
    fixture = next((tmp_path / "private").rglob("private_fixture.json"))
    assert len(fixture.parent.name) == 32
    manifest = json.loads(fixture.read_text(encoding="utf-8"))
    assert manifest["run_id"] == run_id
    assert manifest["approval_digest"] == contract.approval_digest
    assert manifest["spec_hash"] == contract.spec_hash


def test_atomic_metadata_publication_uses_short_temporary_sibling(tmp_path, monkeypatch):
    from pathlib import Path

    opened = []
    original_open = Path.open

    def observe_open(path, *args, **kwargs):
        opened.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observe_open)
    destination = tmp_path / ("metadata-" + "a" * 64 + ".json")
    _write_json(destination, {"valid": True})
    assert len(opened) == 1
    assert opened[0].parent == destination.parent
    assert opened[0].name.startswith(".w-")
    assert len(opened[0].name) <= 15
    assert destination.read_text(encoding="utf-8") == '{"valid":true}'
    assert not opened[0].exists()


@pytest.mark.parametrize(
    "plan,approval",
    [
        ({}, {}),
        ({"approval_digest": None}, {"approval_digest": None}),
        ({"approval_digest": "a" * 64}, {}),
        ({"approval_digest": "a" * 64}, {"approval_digest": "b" * 64}),
        ({"approval_digest": "bad"}, {"approval_digest": "bad"}),
    ],
)
def test_candidate_generation_requires_nonempty_exact_approved_digest(plan, approval):
    from src.research_platform.execution import CapabilityError
    from src.research_platform.services import ResearchServices

    # No database/provider is needed: invalid approval must fail before any I/O.
    service = object.__new__(ResearchServices)
    with pytest.raises(CapabilityError, match="approval of this exact frozen experiment"):
        service.generate_program({"experiment_config": plan, "approval": approval})


def test_host_computes_metrics_statistics_and_rejects_self_reported_scores(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    result = execute(executor, prepared(), tmp_path / "valid")
    assert result["metrics"]["candidate"]["rmse"] < 1e-12
    assert result["metrics"]["baseline"]["rmse"] > 0.5
    assert result["metrics"]["improvement"]["rmse"] > 0
    assert len(result["per_seed"]) == 3
    summary = result["statistical_summary"]
    assert summary["replications"] == 3
    assert math.isclose(
        summary["paired_improvement_mean"], sum(r["improvement"] for r in result["per_seed"]) / 3
    )
    assert 0 <= summary["paired_sign_flip_p_value"] <= 1
    executor.candidate_output = {"predictions": [1.0] * 16, "metrics": {"rmse": 0}}
    with pytest.raises(ProtocolError):
        execute(executor, prepared(), tmp_path / "invalid")
    assert not (tmp_path / "invalid/execution_result.json").exists()


def test_independent_reference_rejects_a_generated_weakened_baseline(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    executor.baseline_wrong = True
    with pytest.raises(EvaluatorValidationError, match="train-label mean"):
        execute(executor, prepared(), tmp_path / "run")


def test_scheduling_validates_permutations_and_measures_fifo_vs_spt(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    result = execute(executor, prepared("scheduling_v1"), tmp_path / "valid")
    assert result["metrics"]["improvement"]["total_completion_time"] > 0
    for public, observation in zip(executor.inputs[::2], result["per_seed"]):
        fifo = sum(sum(public["durations"][: i + 1]) for i in range(len(public["durations"])))
        sorted_durations = sorted(public["durations"])
        spt = sum(sum(sorted_durations[: i + 1]) for i in range(len(sorted_durations)))
        assert observation["baseline"] == fifo and observation["candidate"] == spt
    executor.candidate_output = {"order": [0] * 12}
    with pytest.raises(ProtocolError, match="permutation"):
        execute(executor, prepared("scheduling_v1"), tmp_path / "invalid")


def test_approval_and_dataset_changes_fail_before_execution(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    contract = prepared()
    with pytest.raises(FrozenTaskError, match="commitment"):
        executor.execute("run1", contract, tmp_path / "run")
    frozen = executor.freeze_evaluation("run1", contract, tmp_path / "run")
    with pytest.raises(FrozenTaskError, match="commitment"):
        executor.execute("run1", contract, tmp_path / "run", dataset_sha256="f" * 64)
    changed = contract.model_dump(mode="json")
    changed["spec"]["dataset"]["test_size"] = 32
    with pytest.raises(FrozenTaskError, match="frozen"):
        executor.execute("run1", changed, tmp_path / "run", dataset_sha256=frozen["dataset_sha256"])
    assert executor.inputs == []


def test_corrupted_private_fixture_and_changed_receipts_are_rejected(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    contract = prepared()
    result = execute(executor, contract, tmp_path / "run")
    before = len(executor.inputs)
    assert execute(executor, contract, tmp_path / "run") == result
    assert len(executor.inputs) == before
    frozen = executor.freeze_evaluation("run1", contract, tmp_path / "run")
    with pytest.raises(FrozenTaskError, match="receipt"):
        executor.execute(
            "run1",
            contract,
            tmp_path / "run",
            candidate_source=REGRESSION_BASELINE,
            dataset_sha256=frozen["dataset_sha256"],
        )
    private = next((tmp_path / "private").rglob("private_fixture.json"))
    content = json.loads(private.read_text())
    content["cases"][0]["hidden_targets"][0] += 10
    private.write_text(json.dumps(content))
    with pytest.raises(FrozenTaskError, match="integrity"):
        executor.freeze_evaluation("run1", contract, tmp_path / "run")


@pytest.mark.parametrize("raw", [b'{"x":NaN}', b'{"x":1,"x":2}', b"[]", b"{} trailing"])
def test_program_stdout_is_strict_finite_unique_key_json(raw):
    with pytest.raises(ProtocolError):
        _strict_output(raw)


def test_trusted_analytical_validation_precedes_approval_and_checks_metric_formulae():
    validation = trusted_evaluator_selfcheck()
    assert validation["passed"] and validation["case_count"] == 9
    cases = {case["name"]: case for case in validation["cases"]}
    assert cases["known_rmse"]["actual"] == math.sqrt(2.5)
    assert cases["known_mae"]["actual"] == 1.5
    assert cases["known_fifo_completion"]["actual"] == 13
    assert cases["known_spt_completion"]["actual"] == 10
    assert cases["nonfinite_prediction_rejected"]["actual"] == "rejected"
    assert cases["weakened_mean_baseline_rejected"]["actual"] == "rejected"


def test_generated_runner_command_has_no_host_mounts_secrets_or_evaluator(tmp_path):
    from src.research_platform.tasks import ResourceRequirements

    executor = DynamicExperimentExecutor(fixture_root=tmp_path)
    command = executor.command(
        "isolated-test", ResourceRequirements(), image_id="sha256:" + "a" * 64
    )
    for option in (
        "--network=none",
        "--read-only",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--log-driver=none",
    ):
        assert option in command
    assert "--env-file" not in command and "--mount" not in command and "-v" not in command
    assert "--privileged" not in command and "-e" not in command
    assert not any("private_fixture" in arg or "hidden_targets" in arg for arg in command)


def test_cleanup_verifies_auto_removed_container_without_hiding_daemon_failure():
    def absent(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "Error: No such container: test")

    executor = DynamicExperimentExecutor(runner=absent)
    assert executor._remove("test") is True
    executor.runner = lambda command, **kwargs: subprocess.CompletedProcess(
        command, 1, "", "Cannot connect to the Docker daemon"
    )
    assert executor._remove("test") is False


def test_unknown_candidate_dependency_fails_closed_before_docker(tmp_path):
    executor = FixtureExecutor(fixture_root=tmp_path / "private")
    contract = prepared()
    frozen = executor.freeze_evaluation("run1", contract, tmp_path / "run")
    with pytest.raises(FrozenTaskError, match="interface"):
        executor.execute(
            "run1",
            contract,
            tmp_path / "run",
            candidate_source="import json,sys,numpy\ndata=json.load(sys.stdin)\nprint(json.dumps({'predictions':[]}))\n",
            dataset_sha256=frozen["dataset_sha256"],
        )
    assert executor.inputs == []


@pytest.fixture
def docker_executor(tmp_path):
    executor = DynamicExperimentExecutor(fixture_root=tmp_path / "private", timeout_seconds=30)
    capabilities = executor.capabilities()
    if not capabilities.get("ready"):
        pytest.skip(capabilities.get("reason", "Local reviewed Docker image unavailable"))
    return executor


@pytest.mark.parametrize("protocol", ["regression_v1", "scheduling_v1"])
def test_actual_docker_generated_programs_and_independent_evaluator(
    docker_executor, tmp_path, protocol
):
    result = execute(docker_executor, prepared(protocol), tmp_path / "actual")
    metric = "rmse" if protocol == "regression_v1" else "total_completion_time"
    assert result["status"] == "completed" and result["demo"] is False
    assert result["image_id"].startswith("sha256:")
    assert result["metrics"]["candidate"][metric] < result["metrics"]["baseline"][metric]
    assert len(result["per_seed"]) == 3
    assert (tmp_path / "actual/execution_result.json").is_file()
    assert (tmp_path / "actual/baseline.py").read_text() != (
        tmp_path / "actual/candidate.py"
    ).read_text()
    assert (
        hashlib.sha256((tmp_path / "actual/baseline.py").read_bytes()).hexdigest()
        == result["baseline"]["code_sha256"]
    )
    assert (
        hashlib.sha256((tmp_path / "actual/candidate.py").read_bytes()).hexdigest()
        == result["candidate"]["code_sha256"]
    )
