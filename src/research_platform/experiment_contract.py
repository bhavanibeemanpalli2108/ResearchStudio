"""Typed public experiment contracts; model code cannot define its own score.

These declarations select independently implemented host generators and scorers.
They contain no hidden test labels, private generation salt, or evaluator code.
"""

from __future__ import annotations

import ast
import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Protocol = Literal["regression_v1", "scheduling_v1"]
Metric = Literal["rmse", "mae", "total_completion_time"]


def canonical_hash(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, allow_inf_nan=False, validate_default=True
    )


class Feasibility(ContractModel):
    supported: bool
    protocol: Protocol | None
    reason: str = Field(min_length=10, max_length=1200)
    scope_statement: str = Field(min_length=10, max_length=1200)
    assumptions: list[str] = Field(min_length=1, max_length=8)
    limitations: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_protocol(self) -> Feasibility:
        if self.supported and self.protocol is None:
            raise ValueError("Supported research must select an implemented protocol")
        return self


class RegressionDataset(ContractModel):
    kind: Literal["regression"]
    generator: Literal["linear", "quadratic", "sinusoidal"]
    train_size: int = Field(ge=32, le=256)
    test_size: int = Field(ge=16, le=128)
    feature_count: int = Field(ge=1, le=8)
    noise_std: float = Field(ge=0, le=3)
    coefficients: list[float] = Field(min_length=1, max_length=8)
    intercept: float = Field(ge=-100, le=100)

    @model_validator(mode="after")
    def check_coefficients(self) -> RegressionDataset:
        if len(self.coefficients) != self.feature_count:
            raise ValueError("One coefficient is required for every feature")
        if any(abs(value) > 100 for value in self.coefficients):
            raise ValueError("Coefficient magnitude exceeds the supported range")
        return self


class SchedulingDataset(ContractModel):
    kind: Literal["scheduling"]
    generator: Literal["uniform_jobs"]
    job_count: int = Field(ge=8, le=64)
    machine_count: Literal[1] = 1
    duration_min: int = Field(ge=1, le=20)
    duration_max: int = Field(ge=2, le=100)

    @model_validator(mode="after")
    def check_durations(self) -> SchedulingDataset:
        if self.duration_max <= self.duration_min:
            raise ValueError("duration_max must exceed duration_min")
        return self


Dataset = Annotated[RegressionDataset | SchedulingDataset, Field(discriminator="kind")]


class EvaluationSpec(ContractModel):
    metric: Metric
    direction: Literal["minimize"]
    minimum_improvement: float = Field(ge=0, le=1000)


class ResourceLimits(ContractModel):
    timeout_seconds: int = Field(ge=1, le=30)
    memory_mb: int = Field(ge=128, le=512)


class ExperimentSpec(ContractModel):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=5, max_length=180)
    research_question: str = Field(min_length=10, max_length=4000)
    hypothesis: str = Field(min_length=10, max_length=1600)
    protocol: Protocol
    dataset: Dataset
    evaluation: EvaluationSpec
    resource_limits: ResourceLimits
    seeds: list[int] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def check_protocol(self) -> ExperimentSpec:
        if len(set(self.seeds)) != len(self.seeds) or any(
            not 0 <= seed <= 2**31 - 1 for seed in self.seeds
        ):
            raise ValueError("Seeds must be distinct nonnegative 31-bit integers")
        if self.protocol == "regression_v1":
            if not isinstance(self.dataset, RegressionDataset) or self.evaluation.metric not in {
                "rmse",
                "mae",
            }:
                raise ValueError("regression_v1 requires regression data and RMSE or MAE")
        elif (
            not isinstance(self.dataset, SchedulingDataset)
            or self.evaluation.metric != "total_completion_time"
        ):
            raise ValueError("scheduling_v1 requires scheduling data and total_completion_time")
        return self


ALLOWED_IMPORTS = frozenset(
    {
        "sys",
        "json",
        "math",
        "statistics",
        "random",
        "itertools",
        "functools",
        "collections",
        "heapq",
        "bisect",
        "array",
        "operator",
    }
)


def validate_program_source(source: str) -> None:
    """Static qualification only; container controls remain the security boundary."""
    if len(source.encode("utf-8")) > 40000:
        raise ValueError("Program source exceeds 40KB")
    try:
        tree = ast.parse(source, filename="main.py")
    except (SyntaxError, ValueError) as exc:
        raise ValueError("Program must be syntactically valid Python") from exc
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                raise ValueError("Relative imports are unavailable")
            imports.add(node.module.split(".")[0])
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id
            in {"exec", "eval", "compile", "__import__", "open", "input", "breakpoint"}
        ):
            raise ValueError(
                "Use sys.stdin.read and JSON stdout; dynamic evaluation and filesystem APIs are unavailable"
            )
    if imports - ALLOWED_IMPORTS:
        raise ValueError("Only the approved Python standard library imports are available")
    if "json" not in imports or "sys" not in imports:
        raise ValueError("Programs must import json and sys for the JSON stdin/stdout interface")
    if "stdin" not in source or "stdout" not in source and "print" not in source:
        raise ValueError("Program must read stdin and produce JSON stdout")


class GeneratedProgram(ContractModel):
    source: str = Field(min_length=30, max_length=40000)
    description: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def check_source(self) -> GeneratedProgram:
        validate_program_source(self.source)
        return self


class ProgramArtifact(GeneratedProgram):
    language: Literal["python"] = "python"
    entrypoint: Literal["main.py"] = "main.py"
    dependencies: list[str] = Field(default_factory=list, max_length=0)
    origin: Literal["model"] = "model"
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def check_digest(self) -> ProgramArtifact:
        if hashlib.sha256(self.source.encode("utf-8")).hexdigest() != self.sha256:
            raise ValueError("Program digest does not match its source")
        return self


class EvaluationDeclaration(ContractModel):
    protocol: Protocol
    metric: Metric
    direction: Literal["minimize"]
    spec_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    evaluator: Literal["trusted_builtin_v1"]
    baseline_reference: Literal["train_mean", "fifo"]
    output_key: Literal["predictions", "order"]
    independent: Literal[True]


def expected_evaluation(spec: ExperimentSpec) -> EvaluationDeclaration:
    regression = spec.protocol == "regression_v1"
    return EvaluationDeclaration(
        protocol=spec.protocol,
        metric=spec.evaluation.metric,
        direction="minimize",
        spec_hash=canonical_hash(spec),
        evaluator="trusted_builtin_v1",
        baseline_reference="train_mean" if regression else "fifo",
        output_key="predictions" if regression else "order",
        independent=True,
    )


class PreparationProvenance(ContractModel):
    attempts: int = Field(ge=1, le=3)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class PreparedExperiment(ContractModel):
    schema_version: Literal[1] = 1
    feasibility: Feasibility
    spec: ExperimentSpec
    baseline: ProgramArtifact
    evaluation_contract: EvaluationDeclaration
    candidate: ProgramArtifact | None = None
    spec_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    approval_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    provenance: dict[str, PreparationProvenance]

    @property
    def baseline_program(self) -> ProgramArtifact:
        return self.baseline

    @property
    def experiment_digest(self) -> str:
        return self.approval_digest

    @property
    def contract(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @model_validator(mode="after")
    def check_frozen_components(self) -> PreparedExperiment:
        if not self.feasibility.supported or self.feasibility.protocol != self.spec.protocol:
            raise ValueError("Prepared research must match its feasibility protocol")
        if self.spec_hash != canonical_hash(self.spec):
            raise ValueError("Specification digest mismatch")
        if self.evaluation_contract != expected_evaluation(self.spec):
            raise ValueError("Model evaluation declaration cannot replace the trusted evaluator")
        expected = canonical_hash(
            {
                "spec": self.spec.model_dump(mode="json"),
                "baseline": self.baseline.model_dump(mode="json"),
                "evaluation_contract": self.evaluation_contract.model_dump(mode="json"),
            }
        )
        if self.approval_digest != expected:
            raise ValueError(
                "Human approval digest does not bind the frozen specification, baseline and evaluation"
            )
        return self


def program_artifact(program: GeneratedProgram) -> ProgramArtifact:
    return ProgramArtifact(
        **program.model_dump(), sha256=hashlib.sha256(program.source.encode("utf-8")).hexdigest()
    )


def validate_prepared_experiment(value: Any) -> PreparedExperiment:
    # Nested models and lists remain mutable after construction. Revalidate a
    # private snapshot at each boundary rather than trusting the instance type.
    # This also keeps the JSON artifact and in-memory paths identical.
    if isinstance(value, PreparedExperiment):
        value = value.model_dump(mode="json")
    return PreparedExperiment.model_validate(value)
