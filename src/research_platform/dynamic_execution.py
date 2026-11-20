"""Separate, resource-bounded Docker sandboxes for proposed Python experiments.

No generated program is imported, compiled, or executed by the application.
Only the fixed bootstrap below runs with Docker's stdin. Each baseline,
candidate and evaluator invocation receives a fresh container and no mounts.
Docker remains an operator-managed security boundary, not a production claim.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import random
import re
import secrets
import statistics
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any

from .execution import (
    CapabilityError,
    DockerExecutor,
    ExecutionCancelled,
    ExecutionError,
    ExecutionTimeout,
    OutputLimitError,
    sanitized_environment,
)
from .tasks import ExperimentBundle, ResourceRequirements, canonical_json
from .experiment_contract import (
    GeneratedProgram,
    PreparedExperiment,
    canonical_hash,
    program_artifact,
    validate_prepared_experiment,
)


class ProtocolError(ExecutionError):
    code = "experiment_protocol_error"


class EvaluatorValidationError(ExecutionError):
    code = "evaluator_validation_failed"


class FrozenTaskError(ExecutionError):
    code = "frozen_task_mismatch"


class CleanupUnverified(ExecutionError):
    code = "cleanup_unverified"


BOOTSTRAP = """import io,json,sys
payload=json.load(sys.stdin)
sys.stdin=io.StringIO(json.dumps(payload['input'],allow_nan=False))
exec(compile(payload['code'],'<isolated-research>','exec'),{'__name__':'__main__'})
"""


def _strict_output(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value

    def constant(value: str) -> Any:
        raise ValueError("Nonfinite JSON number")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        if type(result) is not dict:
            raise ValueError("Output must be an object")
        canonical_json(result)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise ProtocolError("The sandbox must emit exactly one finite JSON object.") from None


def _evaluation(value: dict[str, Any], metric_names: set[str]) -> dict[str, Any]:
    if set(value) - {"valid", "metrics", "reason"} or type(value.get("valid")) is not bool:
        raise ProtocolError("Evaluator output must contain valid, metrics and optional reason.")
    metrics = value.get("metrics")

    def finite_number(number: Any) -> bool:
        try:
            return type(number) in (int, float) and math.isfinite(number)
        except OverflowError:
            return False

    if type(metrics) is not dict or any(not finite_number(number) for number in metrics.values()):
        raise ProtocolError("Evaluator measurements must be finite numbers.")
    if value["valid"] and set(metrics) != metric_names:
        raise ProtocolError("A valid evaluator result must contain every declared measurement.")
    if set(metrics) - metric_names:
        raise ProtocolError("Evaluator returned an undeclared measurement.")
    if "reason" in value and (type(value["reason"]) is not str or len(value["reason"]) > 4000):
        raise ProtocolError("Evaluator reason must be a bounded string.")
    return value


class DynamicDockerExecutor:
    """Execute an approved bundle using only packages in a reviewed CPU image.

    ``image`` and ``allowed_dependencies`` are operator configuration, never
    accepted from a research task. Images are pre-pulled; no runtime installs.
    With the default Python image, dependencies must be empty (stdlib only).
    """

    def __init__(
        self,
        *,
        image: str = "python:3.12-slim",
        allowed_dependencies: Collection[str] = (),
        popen: Any = subprocess.Popen,
        runner: Any = subprocess.run,
    ):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./:@_-]{0,255}", image):
            raise ValueError("Invalid reviewed Docker image reference")
        self.image = image
        self.allowed_dependencies = frozenset(allowed_dependencies)
        self.popen, self.runner = popen, runner

    def capabilities(self) -> dict[str, Any]:
        result = DockerExecutor(image=self.image, runner=self.runner).capabilities()
        result["generated_experiments"] = result["ready"]
        result["allowed_dependencies"] = sorted(self.allowed_dependencies)
        if result["ready"]:
            try:
                inspected = self.runner(
                    ["docker", "image", "inspect", self.image, "--format", "{{.Id}}"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    env=sanitized_environment(),
                )
                image_id = inspected.stdout.strip()
                if inspected.returncode or not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
                    raise ValueError("Invalid image identity")
                result["image_id"] = image_id
            except (OSError, subprocess.SubprocessError, ValueError):
                result.update(ready=False, generated_experiments=False)
                result["reason"] = (
                    "Could not pin the reviewed CPU image to its local content digest."
                )
        return result

    def command(
        self, name: str, resources: ResourceRequirements, *, image_id: str | None = None
    ) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--interactive",
            "--label=ai-scientist.dynamic=1",
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            f"--cpus={resources.cpus:g}",
            f"--memory={resources.memory_mb}m",
            f"--memory-swap={resources.memory_mb}m",
            "--ulimit",
            "nofile=128:128",
            "--ulimit",
            "core=0:0",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=32m",
            "--workdir=/tmp",
            "--log-driver=none",
            "--init",
            image_id or self.image,
            "python",
            "-I",
            "-B",
            "-c",
            BOOTSTRAP,
        ]

    def _remove(self, name: str) -> bool:
        try:
            removed = self.runner(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=8,
                env=sanitized_environment(),
            )
            if removed.returncode == 0:
                return True
            # --rm can remove the container between poll() and this cleanup.
            # Confirm absence rather than interpreting that race as an escape.
            inspected = self.runner(
                ["docker", "container", "inspect", name],
                capture_output=True,
                text=True,
                timeout=8,
                env=sanitized_environment(),
            )
            error = inspected.stderr or ""
            if isinstance(error, bytes):
                error = error.decode("utf-8", errors="replace")
            return inspected.returncode == 1 and bool(
                re.search(r"(?i)no such (container|object)", error)
            )
        except (OSError, subprocess.SubprocessError):
            return False

    def _execute_program(
        self,
        code: str,
        input_value: dict[str, Any],
        resources: ResourceRequirements,
        *,
        image_id: str,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        if cancel_check and cancel_check():
            raise ExecutionCancelled("Execution was cancelled before launch.")
        payload = canonical_json({"code": code, "input": input_value}).encode("utf-8")
        name = "research-generated-" + uuid.uuid4().hex[:20]
        try:
            process = self.popen(
                self.command(name, resources, image_id=image_id),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=sanitized_environment(),
            )
        except OSError:
            self._remove(name)
            raise ExecutionError("Could not launch the isolated research container.") from None

        captured = {"stdout": bytearray(), "stderr": bytearray()}
        output_exceeded = threading.Event()
        write_failed = threading.Event()
        capture_lock = threading.Lock()
        captured_bytes = 0

        def drain(stream: Any, channel: str) -> None:
            nonlocal captured_bytes
            try:
                while True:
                    block = stream.read(4096)
                    if not block:
                        return
                    with capture_lock:
                        room = resources.output_limit_bytes - captured_bytes
                        if room > 0:
                            captured[channel].extend(block[:room])
                            captured_bytes += min(len(block), room)
                        if len(block) > room:
                            output_exceeded.set()
            except (OSError, ValueError):
                pass  # Main thread closes streams only after container teardown.

        def supply() -> None:
            try:
                process.stdin.write(payload)
                process.stdin.flush()
            except (OSError, ValueError):
                write_failed.set()
            finally:
                try:
                    process.stdin.close()
                except (OSError, ValueError):
                    pass

        threads = [
            threading.Thread(target=drain, args=(process.stdout, "stdout"), daemon=True),
            threading.Thread(target=drain, args=(process.stderr, "stderr"), daemon=True),
            threading.Thread(target=supply, daemon=True),
        ]
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + resources.wall_seconds
        try:
            while process.poll() is None:
                if cancel_check and cancel_check():
                    raise ExecutionCancelled("Execution was cancelled.")
                if output_exceeded.is_set():
                    raise OutputLimitError(
                        "Sandbox stdout/stderr exceeded the combined byte limit."
                    )
                if time.monotonic() >= deadline:
                    raise ExecutionTimeout(
                        "The research container exceeded its wall-clock deadline."
                    )
                time.sleep(0.025)
            for thread in threads:
                thread.join(timeout=1)
            if output_exceeded.is_set():
                raise OutputLimitError("Sandbox stdout/stderr exceeded the combined byte limit.")
            if process.returncode or write_failed.is_set():
                # Generated stderr is untrusted and can contain arbitrary text.
                # Artifacts may store approved program source; errors remain bounded.
                raise ExecutionError(
                    f"The isolated research program exited unsuccessfully ({process.returncode})."
                )
            return _strict_output(bytes(captured["stdout"]))
        finally:
            active = process.poll() is None
            cleanup_confirmed = self._remove(name)
            if active:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            for thread in threads:
                thread.join(timeout=1)
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
            if active and not cleanup_confirmed:
                raise CleanupUnverified(
                    "Docker could not confirm removal of the running research container; operator cleanup is required."
                )

    def execute_bundle(
        self,
        bundle: ExperimentBundle,
        *,
        frozen_hash: str | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        # Snapshot nested dicts/lists so caller mutation cannot alter an approved
        # input, evaluator or baseline while a candidate is running.
        bundle = ExperimentBundle.model_validate_json(
            canonical_json(bundle.model_dump(mode="json"))
        )
        if not frozen_hash or bundle.frozen_hash() != frozen_hash:
            raise FrozenTaskError(
                "An approved frozen task, baseline, evaluator and input hash is required."
            )
        unsupported = set(bundle.task.dependencies) - self.allowed_dependencies
        if unsupported:
            raise CapabilityError(
                "Dependencies are absent from the reviewed CPU image: "
                + ", ".join(sorted(unsupported))
            )
        capabilities = self.capabilities()
        if not capabilities["ready"]:
            raise CapabilityError(
                capabilities.get("reason", "Isolated Docker research execution is unavailable.")
            )
        image_id = capabilities.get("image_id")
        if not image_id:
            raise CapabilityError("The reviewed CPU image must have a pinned content digest.")
        resources = bundle.task.resources
        metric_names = {metric.name for metric in bundle.task.metrics}

        def evaluate(output: dict[str, Any]) -> dict[str, Any]:
            value = self._execute_program(
                bundle.evaluator_code,
                {
                    "task": bundle.task.model_dump(mode="json"),
                    "experiment_input": bundle.experiment_input,
                    "evaluation_input": bundle.evaluation_input,
                    "output": output,
                },
                resources,
                image_id=image_id,
                cancel_check=cancel_check,
            )
            return _evaluation(value, metric_names)

        validation = []
        for case in bundle.evaluator_tests:
            measurement = evaluate(case.output)
            if measurement["valid"] != case.expected_valid or any(
                key not in measurement["metrics"]
                or not math.isclose(
                    measurement["metrics"][key], expected, rel_tol=1e-7, abs_tol=1e-9
                )
                for key, expected in case.expected_metrics.items()
            ):
                raise EvaluatorValidationError(
                    "Evaluator failed the frozen validation case: " + case.name
                )
            validation.append({"name": case.name, "passed": True})

        results: dict[str, Any] = {}
        for label, code in (
            ("baseline", bundle.baseline_code),
            ("candidate", bundle.candidate_code),
        ):
            started = time.monotonic()
            output = self._execute_program(
                code,
                bundle.experiment_input,
                resources,
                image_id=image_id,
                cancel_check=cancel_check,
            )
            execution_seconds = time.monotonic() - started
            evaluation_started = time.monotonic()
            evaluated = evaluate(output)
            results[label] = {
                "output": output,
                **evaluated,
                "wall_seconds": execution_seconds,
                "evaluation_wall_seconds": time.monotonic() - evaluation_started,
                "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
            }
        improvements = {}
        if results["baseline"]["valid"] and results["candidate"]["valid"]:
            improvements = {
                metric.name: (
                    results["candidate"]["metrics"][metric.name]
                    - results["baseline"]["metrics"][metric.name]
                )
                * (1 if metric.direction == "maximize" else -1)
                for metric in bundle.task.metrics
            }
            if any(not math.isfinite(value) for value in improvements.values()):
                raise ProtocolError("The comparison overflowed its finite measurement range.")
        return {
            "protocol_version": 1,
            "source": "isolated_generated_experiment",
            "demo": False,
            "frozen_hash": frozen_hash,
            "bundle_hash": bundle.bundle_hash(),
            "image": self.image,
            "image_id": image_id,
            "evaluator_sha256": hashlib.sha256(bundle.evaluator_code.encode()).hexdigest(),
            "evaluator_validation": validation,
            **results,
            "metrics": {
                "baseline": results["baseline"]["metrics"],
                "candidate": results["candidate"]["metrics"],
                "improvement": improvements,
            },
            "valid": results["baseline"]["valid"] and results["candidate"]["valid"],
        }


TRUSTED_EVALUATOR_VERSION = "trusted_protocols_v1"


def _evaluator_hash() -> str:
    return canonical_hash(
        {
            "generator": inspect.getsource(_generate_cases),
            "metric": inspect.getsource(_measure),
            "statistics": inspect.getsource(_paired_summary),
            "finite_output": inspect.getsource(_finite_number),
            "analytical_checks": inspect.getsource(trusted_evaluator_selfcheck),
        }
    )


def _write_json(path: Path, value: Any) -> None:
    """Publish host-owned metadata atomically; none of these paths are mounted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Compact sibling names keep publication inside Win32's ordinary path
    # limit even when the application's data root is deeply nested.
    temporary = path.with_name(".w-" + secrets.token_hex(4) + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(value))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1e12
    except OverflowError:
        return False


def _generate_cases(prepared: PreparedExperiment, salt: str) -> list[dict[str, Any]]:
    """Generate frozen splits; noise RNG identities never enter candidate input.

    The public seed labels a replication. Private PRNG seeds are derived from a
    host-only random salt, preventing the source from reconstructing held-out
    noise by knowing the published dataset generator and replication seed.
    """
    spec = prepared.spec.model_dump(mode="json")
    dataset = spec["dataset"]
    cases = []
    for seed in spec["seeds"]:

        def rng(partition: str) -> random.Random:
            digest = hashlib.sha256(f"{salt}:{seed}:{partition}".encode()).hexdigest()
            return random.Random(int(digest, 16))

        if spec["protocol"] == "regression_v1":
            train_rng, test_rng = rng("train"), rng("heldout")

            def examples(generator: random.Random, count: int):
                rows = []
                for _ in range(count):
                    features = [
                        generator.uniform(-1.0, 1.0) for _ in range(dataset["feature_count"])
                    ]
                    if dataset["generator"] == "linear":
                        transformed = features
                    elif dataset["generator"] == "quadratic":
                        transformed = [value * value for value in features]
                    else:
                        transformed = [math.sin(math.pi * value) for value in features]
                    target = (
                        math.fsum(
                            coefficient * value
                            for coefficient, value in zip(dataset["coefficients"], transformed)
                        )
                        + dataset["intercept"]
                    )
                    target += generator.gauss(0.0, dataset["noise_std"])
                    rows.append({"x": features, "y": target})
                return rows

            train = examples(train_rng, dataset["train_size"])
            heldout = examples(test_rng, dataset["test_size"])
            public = {"train": train, "test": [{"x": row["x"]} for row in heldout], "seed": seed}
            hidden = [row["y"] for row in heldout]
        else:
            generator = rng("durations")
            public = {
                "durations": [
                    generator.randint(dataset["duration_min"], dataset["duration_max"])
                    for _ in range(dataset["job_count"])
                ],
                "seed": seed,
            }
            hidden = []
        cases.append({"seed": seed, "public_input": public, "hidden_targets": hidden})
    return cases


def _measure(
    protocol: str,
    metric: str,
    output: dict[str, Any],
    case: dict[str, Any],
    *,
    baseline: bool = False,
) -> float:
    """Independent host measurement. Self-reported scores are never accepted."""
    public = case["public_input"]
    if protocol == "regression_v1":
        predictions = output.get("predictions")
        targets = case["hidden_targets"]
        if (
            set(output) != {"predictions"}
            or type(predictions) is not list
            or len(predictions) != len(targets)
            or not all(_finite_number(v) for v in predictions)
        ):
            raise ProtocolError(
                "Regression output must contain exactly one finite prediction per held-out example."
            )
        if baseline:
            mean = statistics.fmean(row["y"] for row in public["train"])
            if any(
                not math.isclose(value, mean, rel_tol=1e-9, abs_tol=1e-9) for value in predictions
            ):
                raise EvaluatorValidationError(
                    "The generated baseline does not implement the approved train-label mean reference."
                )
        errors = [float(prediction) - target for prediction, target in zip(predictions, targets)]
        measurement = (
            math.sqrt(statistics.fmean(error * error for error in errors))
            if metric == "rmse"
            else statistics.fmean(abs(error) for error in errors)
        )
    else:
        order = output.get("order")
        durations = public["durations"]
        if (
            set(output) != {"order"}
            or type(order) is not list
            or any(type(i) is not int for i in order)
            or sorted(order) != list(range(len(durations)))
        ):
            raise ProtocolError(
                "Scheduling output must contain an exact permutation of every job index."
            )
        if baseline and order != list(range(len(durations))):
            raise EvaluatorValidationError(
                "The generated baseline does not implement the approved FIFO reference."
            )
        elapsed = 0
        completion_times = []
        for index in order:
            elapsed += durations[index]
            completion_times.append(elapsed)
        measurement = float(sum(completion_times))
    if not math.isfinite(measurement):
        raise ProtocolError("Trusted measurement exceeded the supported finite range.")
    return measurement


def _paired_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = [row["baseline"] for row in observations]
    candidate = [row["candidate"] for row in observations]
    differences = [row["improvement"] for row in observations]
    count = len(differences)
    mean = statistics.fmean(differences)
    deviation = statistics.stdev(differences) if count > 1 else 0.0
    sem = deviation / math.sqrt(count)
    critical = {2: 12.7062047364, 3: 4.3026527297, 4: 3.1824463053, 5: 2.7764451052}[count]
    # Exact paired sign-flip test of the mean under a symmetric zero-effect
    # null. Small replication counts necessarily give coarse p-values.
    extremes = sum(
        abs(
            statistics.fmean(
                value * (1 if mask & (1 << index) else -1)
                for index, value in enumerate(differences)
            )
        )
        >= abs(mean) - 1e-12
        for mask in range(1 << count)
    )
    return {
        "replications": count,
        "baseline_mean": statistics.fmean(baseline),
        "candidate_mean": statistics.fmean(candidate),
        "paired_improvement_mean": mean,
        "paired_improvement_stddev": deviation,
        "paired_improvement_sem": sem,
        "paired_t_95_interval": {"lower": mean - critical * sem, "upper": mean + critical * sem},
        "paired_sign_flip_p_value": extremes / (1 << count),
        "method": "Paired seed observations; Student-t mean interval and exact two-sided sign-flip test",
        "assumptions": [
            "The Student-t interval assumes approximately normal independent paired seed effects.",
            "The sign-flip test assumes symmetry under the zero-effect null.",
            "Repeated candidate selection against these frozen splits is adaptive; these are exploratory measurements, not independent final confirmation.",
        ],
    }


def trusted_evaluator_selfcheck() -> dict[str, Any]:
    """Analytical, independently authored cases checked before human approval.

    These tiny public examples are unrelated to the frozen experiment splits.
    They test trusted metric formulae and rejection behavior, rather than a
    model-authored evaluator's consistency with its own proposed examples.
    """
    regression = {
        "public_input": {"train": [{"x": [0.0], "y": 2.0}], "test": [{"x": [1.0]}, {"x": [2.0]}]},
        "hidden_targets": [1.0, 3.0],
    }
    scheduling = {"public_input": {"durations": [3, 1, 2]}, "hidden_targets": []}
    cases = []
    for name, protocol, metric, output, case, expected in (
        (
            "known_rmse",
            "regression_v1",
            "rmse",
            {"predictions": [0.0, 1.0]},
            regression,
            math.sqrt(2.5),
        ),
        ("known_mae", "regression_v1", "mae", {"predictions": [0.0, 1.0]}, regression, 1.5),
        (
            "known_fifo_completion",
            "scheduling_v1",
            "total_completion_time",
            {"order": [0, 1, 2]},
            scheduling,
            13.0,
        ),
        (
            "known_spt_completion",
            "scheduling_v1",
            "total_completion_time",
            {"order": [1, 2, 0]},
            scheduling,
            10.0,
        ),
    ):
        actual = _measure(protocol, metric, output, case)
        passed = math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
        cases.append({"name": name, "passed": passed, "expected": expected, "actual": actual})
    for name, protocol, metric, output, case, baseline in (
        (
            "duplicate_job_rejected",
            "scheduling_v1",
            "total_completion_time",
            {"order": [0, 0, 2]},
            scheduling,
            False,
        ),
        (
            "nonfinite_prediction_rejected",
            "regression_v1",
            "rmse",
            {"predictions": [float("nan"), 1.0]},
            regression,
            False,
        ),
        (
            "undeclared_label_field_rejected",
            "regression_v1",
            "rmse",
            {"predictions": [1.0, 3.0], "hidden_targets": [1.0, 3.0]},
            regression,
            False,
        ),
        (
            "weakened_mean_baseline_rejected",
            "regression_v1",
            "rmse",
            {"predictions": [0.0, 0.0]},
            regression,
            True,
        ),
        (
            "changed_fifo_baseline_rejected",
            "scheduling_v1",
            "total_completion_time",
            {"order": [1, 2, 0]},
            scheduling,
            True,
        ),
    ):
        rejected = False
        try:
            _measure(protocol, metric, output, case, baseline=baseline)
        except (ProtocolError, EvaluatorValidationError):
            rejected = True
        cases.append(
            {
                "name": name,
                "passed": rejected,
                "expected": "rejected",
                "actual": "rejected" if rejected else "accepted",
            }
        )
    if not all(case["passed"] for case in cases):
        raise EvaluatorValidationError(
            "Trusted evaluator failed an independently authored analytical validation case."
        )
    return {
        "passed": True,
        "case_count": len(cases),
        "cases": cases,
        "source": "host_owned_analytical_examples",
        "experiment_labels_shared": False,
    }


class DynamicExperimentExecutor(DynamicDockerExecutor):
    """Trusted regression/scheduling protocols over the preserved Docker runner.

    Candidate and baseline each receive only one public JSON example collection
    in a fresh container. Labels and host evaluator functions are never mounted,
    passed as code, or sent through their stdin. ``execute_bundle`` remains the
    legacy proposed-evaluator API; this class's ``execute`` never invokes it.
    """

    def __init__(
        self,
        *,
        fixture_root: str | Path | None = None,
        timeout_seconds: float = 30,
        output_limit_bytes: int = 65536,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.fixture_root = Path(fixture_root).resolve() if fixture_root is not None else None
        self.timeout_seconds = max(1, min(30, int(timeout_seconds)))
        self.output_limit_bytes = max(1024, min(1024 * 1024, int(output_limit_bytes)))

    @staticmethod
    def _prepared(value: Any) -> PreparedExperiment:
        try:
            original = validate_prepared_experiment(value)
            # Nested Pydantic members are mutable: bind a private snapshot.
            return validate_prepared_experiment(
                json.loads(canonical_json(original.model_dump(mode="json")))
            )
        except (ValueError, TypeError):
            raise FrozenTaskError(
                "Prepared experiment does not match its frozen approved specification, baseline and trusted evaluator."
            ) from None

    def _fixture(
        self, run_id: str, prepared: PreparedExperiment, workdir: str | Path
    ) -> tuple[Path, dict[str, Any]]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
            raise FrozenTaskError("Invalid internal run identifier.")
        root = self.fixture_root or (Path(workdir).resolve().parent / ".frozen-evaluations")
        # Full identities remain inside the checksummed manifest. Compact the
        # directory key to avoid appending 100+ characters to a Windows root.
        fixture_key = canonical_hash(
            {"run_id": run_id, "approval_digest": prepared.approval_digest}
        )[:32]
        path = root / fixture_key / "private_fixture.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.with_suffix(".lock")
        deadline = time.monotonic() + 5
        while True:
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(descriptor)
                break
            except FileExistsError:
                # A killed worker may leave its tiny fixture publication lock.
                # Generation is bounded and takes milliseconds; leases expire
                # before this conservative stale-lock recovery threshold.
                try:
                    if time.time() - lock.stat().st_mtime > 60:
                        lock.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise FrozenTaskError(
                        "Frozen dataset is locked by another worker; retry after recovery."
                    ) from None
                time.sleep(0.025)
        try:
            if path.exists():
                if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
                    raise FrozenTaskError("Frozen dataset is not a bounded regular host file.")
                fixture = _strict_output(path.read_bytes())
            else:
                salt = secrets.token_hex(32)
                core = {
                    "schema_version": 1,
                    "run_id": run_id,
                    "approval_digest": prepared.approval_digest,
                    "spec_hash": prepared.spec_hash,
                    "private_salt": salt,
                    "evaluator_version": TRUSTED_EVALUATOR_VERSION,
                    "evaluator_sha256": _evaluator_hash(),
                    "cases": _generate_cases(prepared, salt),
                }
                fixture = {**core, "dataset_sha256": canonical_hash(core)}
                _write_json(path, fixture)
                try:
                    path.chmod(0o600)
                except OSError:
                    pass  # Windows ACLs belong to the operator-managed data directory.
            core = {key: value for key, value in fixture.items() if key != "dataset_sha256"}
            if (
                fixture.get("run_id") != run_id
                or fixture.get("approval_digest") != prepared.approval_digest
                or fixture.get("spec_hash") != prepared.spec_hash
                or fixture.get("evaluator_version") != TRUSTED_EVALUATOR_VERSION
                or fixture.get("evaluator_sha256") != _evaluator_hash()
                or fixture.get("dataset_sha256") != canonical_hash(core)
            ):
                raise FrozenTaskError(
                    "Frozen dataset integrity or approved contract identity changed."
                )
            if canonical_hash(fixture.get("cases")) != canonical_hash(
                _generate_cases(prepared, fixture["private_salt"])
            ):
                raise FrozenTaskError("Frozen dataset does not match the trusted generator.")
            return path, fixture
        finally:
            lock.unlink(missing_ok=True)

    def freeze_evaluation(self, run_id: str, prepared: Any, workdir: str | Path) -> dict[str, Any]:
        contract = self._prepared(prepared)
        validation = trusted_evaluator_selfcheck()
        _, fixture = self._fixture(run_id, contract, workdir)
        splits = []
        for case in fixture["cases"]:
            public = case["public_input"]
            splits.append(
                {
                    "seed": case["seed"],
                    "public_input_sha256": canonical_hash(public),
                    "train_sha256": canonical_hash(public.get("train", [])),
                    "test_features_sha256": canonical_hash(
                        public.get("test", public.get("durations", []))
                    ),
                }
            )
        return {
            "schema_version": 1,
            "run_id": run_id,
            "approval_digest": contract.approval_digest,
            "spec_hash": contract.spec_hash,
            "dataset_sha256": fixture["dataset_sha256"],
            "case_seeds": contract.spec.seeds,
            "split_hashes": splits,
            "evaluator": TRUSTED_EVALUATOR_VERSION,
            "evaluator_sha256": fixture["evaluator_sha256"],
            "hidden_labels_shared": False,
            "evaluator_validation": validation,
        }

    def execute(
        self,
        run_id: str,
        prepared: Any,
        workdir: str | Path,
        candidate_source: str | None = None,
        *,
        dataset_sha256: str | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        contract = self._prepared(prepared)
        candidate = contract.candidate
        if candidate_source is not None:
            try:
                candidate = program_artifact(
                    GeneratedProgram(
                        source=candidate_source,
                        description="Model-authored candidate supplied after approval",
                    )
                )
            except ValueError:
                raise FrozenTaskError(
                    "Candidate source does not meet the approved JSON program interface."
                ) from None
        if candidate is None:
            raise FrozenTaskError(
                "Generate a candidate program after approving the frozen experiment."
            )
        if not dataset_sha256 or not re.fullmatch(r"[a-f0-9]{64}", dataset_sha256):
            raise FrozenTaskError("The approved frozen dataset SHA-256 commitment is required.")
        _, fixture = self._fixture(run_id, contract, workdir)
        if fixture["dataset_sha256"] != dataset_sha256:
            raise FrozenTaskError(
                "Evaluation inputs differ from the approved frozen dataset commitment."
            )
        unsupported = (
            set(contract.baseline.dependencies + candidate.dependencies) - self.allowed_dependencies
        )
        if unsupported:
            raise CapabilityError(
                "Dependencies are absent from the reviewed CPU image: "
                + ", ".join(sorted(unsupported))
            )
        directory = Path(workdir).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        receipt = directory / "execution_result.json"
        identity = {
            "run_id": run_id,
            "approval_digest": contract.approval_digest,
            "dataset_sha256": dataset_sha256,
            "baseline_sha256": contract.baseline.sha256,
            "candidate_sha256": candidate.sha256,
            "image_reference": self.image,
            "evaluator_version": TRUSTED_EVALUATOR_VERSION,
        }
        if receipt.exists():
            previous = _strict_output(receipt.read_bytes())
            if previous.get("execution_identity") != identity:
                raise FrozenTaskError(
                    "Execution receipt belongs to another approved experiment, candidate, image or dataset."
                )
            return previous
        capabilities = self.capabilities()
        image_id = capabilities.get("image_id")
        if (
            not capabilities.get("ready")
            or not isinstance(image_id, str)
            or not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id)
        ):
            raise CapabilityError(
                capabilities.get("reason", "A local, pinned Docker CPU image is required.")
            )
        resources = ResourceRequirements(
            cpus=1.0,
            memory_mb=contract.spec.resource_limits.memory_mb,
            wall_seconds=min(contract.spec.resource_limits.timeout_seconds, self.timeout_seconds),
            output_limit_bytes=self.output_limit_bytes,
        )
        (directory / "baseline.py").write_text(
            contract.baseline.source, encoding="utf-8", newline=""
        )
        (directory / "candidate.py").write_text(candidate.source, encoding="utf-8", newline="")
        _write_json(
            directory / "public_inputs.json", [case["public_input"] for case in fixture["cases"]]
        )
        observations = []
        execution_times = {"baseline": 0.0, "candidate": 0.0}
        for case in fixture["cases"]:
            row: dict[str, Any] = {
                "seed": case["seed"],
                "public_input_sha256": canonical_hash(case["public_input"]),
            }
            for role, program in (("baseline", contract.baseline), ("candidate", candidate)):
                started = time.monotonic()
                output = self._execute_program(
                    program.source,
                    case["public_input"],
                    resources,
                    image_id=image_id,
                    cancel_check=cancel_check,
                )
                execution_times[role] += time.monotonic() - started
                measurement = _measure(
                    contract.spec.protocol,
                    contract.spec.evaluation.metric,
                    output,
                    case,
                    baseline=role == "baseline",
                )
                row[role] = measurement
                row[f"{role}_output_sha256"] = canonical_hash(output)
                _write_json(directory / f"{role}_{case['seed']}.output.json", output)
            row["improvement"] = row["baseline"] - row["candidate"]
            observations.append(row)
        summary = _paired_summary(observations)
        metric = contract.spec.evaluation.metric
        result = {
            "status": "completed",
            "protocol_version": 2,
            "source": "isolated_generated_trusted_protocol_v1",
            "demo": False,
            "valid": True,
            "protocol": contract.spec.protocol,
            "execution_identity": identity,
            "frozen_hash": contract.approval_digest,
            "dataset_sha256": dataset_sha256,
            "spec_hash": contract.spec_hash,
            "image": self.image,
            "image_id": image_id,
            "evaluator_sha256": fixture["evaluator_sha256"],
            "evaluator_validation": trusted_evaluator_selfcheck(),
            "baseline": {
                "valid": True,
                "metrics": {metric: summary["baseline_mean"]},
                "code_sha256": contract.baseline.sha256,
                "wall_seconds": execution_times["baseline"],
            },
            "candidate": {
                "valid": True,
                "metrics": {metric: summary["candidate_mean"]},
                "code_sha256": candidate.sha256,
                "wall_seconds": execution_times["candidate"],
            },
            "metrics": {
                "baseline": {metric: summary["baseline_mean"]},
                "candidate": {metric: summary["candidate_mean"]},
                "improvement": {metric: summary["paired_improvement_mean"]},
            },
            "per_seed": observations,
            "statistical_summary": summary,
            "meets_minimum_improvement": summary["paired_improvement_mean"]
            > contract.spec.evaluation.minimum_improvement,
            "configuration": {
                "spec": contract.spec.model_dump(mode="json"),
                "approval_digest": contract.approval_digest,
                "dataset_sha256": dataset_sha256,
                "resources": resources.model_dump(mode="json"),
                "evaluator": TRUSTED_EVALUATOR_VERSION,
                "hidden_labels_shared": False,
            },
            "artifacts": [
                "baseline.py",
                "candidate.py",
                "public_inputs.json",
                "measurements.json",
                "execution_result.json",
            ],
            "logs": [
                "Generated baseline and candidate ran in separate isolated Docker containers per seed.",
                "Trusted host scorer validated baseline semantics and independently measured both outputs; hidden labels and evaluator were never sent to either program.",
            ],
            "limitations": [
                "Synthetic data support conclusions only for the approved generator and frozen splits.",
                *summary["assumptions"],
                "Docker shares the host kernel and remains an operator-managed security boundary.",
            ],
        }
        _write_json(
            directory / "measurements.json",
            {"per_seed": observations, "statistical_summary": summary},
        )
        _write_json(receipt, result)
        return result

    execute_prepared = execute
