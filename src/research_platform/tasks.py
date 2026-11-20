"""Reviewable, domain-independent contracts for isolated computational research.

These contracts describe proposed research, never a preset benchmark. Programs
consume one JSON object from stdin and emit exactly one JSON object on stdout.
The evaluator is frozen with the task and runs without access to candidate code.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class DatasetSpec(StrictContract):
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=4000)
    license: str = Field(min_length=1, max_length=1000)
    split: str = Field(min_length=1, max_length=4000)


class MetricSpec(StrictContract):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    description: str = Field(min_length=1, max_length=2000)
    direction: Literal["maximize", "minimize"]


class ResourceRequirements(StrictContract):
    cpus: float = Field(default=1.0, ge=1, le=2)
    memory_mb: int = Field(default=256, ge=64, le=2048)
    wall_seconds: int = Field(default=30, ge=1, le=300)
    output_limit_bytes: int = Field(default=65536, ge=1024, le=1048576)
    accelerator: Literal["cpu"] = "cpu"


class ResearchSafety(StrictContract):
    network_access: Literal[False] = False
    contains_personal_data: Literal[False] = False
    requires_hardware: Literal[False] = False
    notes: str = Field(min_length=1, max_length=4000)


class ReproducibilitySpec(StrictContract):
    seeds: list[int] = Field(min_length=1, max_length=20)
    procedure: str = Field(min_length=1, max_length=4000)


class ResearchTask(StrictContract):
    question: str = Field(min_length=10, max_length=8000)
    objectives: list[str] = Field(min_length=1, max_length=20)
    domain: str = Field(min_length=1, max_length=200)
    hypotheses: list[str] = Field(min_length=1, max_length=20)
    datasets: list[DatasetSpec] = Field(min_length=1, max_length=20)
    methodology: str = Field(min_length=10, max_length=16000)
    baselines: list[str] = Field(min_length=1, max_length=20)
    metrics: list[MetricSpec] = Field(min_length=1, max_length=20)
    success_criteria: list[str] = Field(min_length=1, max_length=20)
    resources: ResourceRequirements
    dependencies: list[str] = Field(default_factory=list, max_length=32)
    safety: ResearchSafety
    reproducibility: ReproducibilitySpec

    @field_validator("objectives", "hypotheses", "baselines", "success_criteria")
    @classmethod
    def nonempty_statements(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 4000 for item in value):
            raise ValueError("Research statements must be nonempty and bounded.")
        return value

    @field_validator("dependencies")
    @classmethod
    def dependency_names(cls, value: list[str]) -> list[str]:
        # Dependencies identify packages in an administrator-reviewed image;
        # they are never fed to pip, a shell, or a network-enabled container.
        import re

        if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}", item) for item in value):
            raise ValueError("Dependencies must be package names from the reviewed image.")
        if len(value) != len(set(value)):
            raise ValueError("Dependency names must be unique.")
        return value

    @model_validator(mode="after")
    def unique_metrics(self) -> "ResearchTask":
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("Metric names must be unique.")
        return self


def canonical_json(value: Any) -> str:
    """Disallow non-JSON values, NaN/Infinity, excessive depth and large payloads."""

    def check(item: Any, depth: int = 0) -> None:
        if depth > 32:
            raise ValueError("JSON nesting exceeds 32 levels.")
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child, depth + 1)
            return
        if type(item) is list:
            for child in item:
                check(child, depth + 1)
            return
        raise ValueError("Only finite JSON values are permitted.")

    check(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("JSON payload exceeds 2 MiB.")
    return encoded


class EvaluatorTestCase(StrictContract):
    name: str = Field(min_length=1, max_length=200)
    output: dict[str, Any]
    expected_valid: bool
    expected_metrics: dict[str, float] = Field(default_factory=dict)

    @field_validator("output")
    @classmethod
    def json_output(cls, value: dict[str, Any]) -> dict[str, Any]:
        canonical_json(value)
        return value

    @field_validator("expected_metrics")
    @classmethod
    def finite_metrics(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not math.isfinite(number) for number in value.values()):
            raise ValueError("Expected measurements must be finite.")
        return value


class ExperimentBundle(StrictContract):
    task: ResearchTask
    experiment_input: dict[str, Any]
    evaluation_input: dict[str, Any] = Field(default_factory=dict)
    baseline_code: str = Field(min_length=1, max_length=65536)
    candidate_code: str = Field(min_length=1, max_length=65536)
    evaluator_code: str = Field(min_length=1, max_length=65536)
    evaluator_tests: list[EvaluatorTestCase] = Field(min_length=2, max_length=20)

    @field_validator("experiment_input", "evaluation_input")
    @classmethod
    def json_input(cls, value: dict[str, Any]) -> dict[str, Any]:
        canonical_json(value)
        return value

    @model_validator(mode="after")
    def evaluator_examples(self) -> "ExperimentBundle":
        if not any(case.expected_valid for case in self.evaluator_tests):
            raise ValueError("Evaluator validation requires a known valid output.")
        if not any(not case.expected_valid for case in self.evaluator_tests):
            raise ValueError("Evaluator validation requires a known invalid output.")
        metric_names = {metric.name for metric in self.task.metrics}
        for case in self.evaluator_tests:
            if case.expected_valid and set(case.expected_metrics) != metric_names:
                raise ValueError(
                    "Valid evaluator fixtures must specify every declared measurement."
                )
        return self

    def frozen_hash(self) -> str:
        """Bind review/approval to everything except the optimizable candidate."""
        frozen = self.model_dump(mode="json", exclude={"candidate_code"})
        return hashlib.sha256(canonical_json(frozen).encode()).hexdigest()

    def bundle_hash(self) -> str:
        return hashlib.sha256(canonical_json(self.model_dump(mode="json")).encode()).hexdigest()
