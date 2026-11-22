"""Validated API contracts and conservative resource limits."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Provider = Literal["mock", "gemini", "groq", "ollama"]
Profile = Literal["demo", "free_research", "full_research"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProjectCreate(StrictModel):
    title: str = Field(min_length=3, max_length=180)
    question: str = Field(min_length=10, max_length=4000)
    domain: str = Field(default="Computer science", min_length=1, max_length=120)
    objectives: list[str] = Field(default_factory=list, max_length=20)
    references: list[str] = Field(default_factory=list, max_length=30)


class LiteratureSearch(StrictModel):
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=10, ge=1, le=10)


class Budgets(StrictModel):
    max_llm_calls: int = Field(default=20, ge=1, le=100)
    max_input_tokens: int = Field(default=32000, ge=128, le=250000)
    max_output_tokens: int = Field(default=16000, ge=128, le=100000)
    max_iterations: int = Field(default=2, ge=1, le=10)
    max_experiments: int = Field(default=3, ge=1, le=10)
    max_runtime_seconds: int = Field(default=300, ge=10, le=7200)
    monetary_cap_usd: float | None = Field(default=None, ge=0, le=10)


class ModelSelection(StrictModel):
    provider: Provider
    model: str = Field(min_length=1, max_length=180, pattern=r"^[a-zA-Z0-9._:/@+\-]+$")


class RunCreate(StrictModel):
    execution_protocol: Literal[2] = 2
    engine: Literal["native", "original"] = "native"
    profile: Profile = "demo"
    provider: Provider = "mock"
    model: str = Field(
        default="mock-researcher", min_length=1, max_length=180, pattern=r"^[a-zA-Z0-9._:/@+\-]+$"
    )
    budgets: Budgets = Field(default_factory=Budgets)
    generate_report: bool = True
    require_approval: bool = True
    constraints: dict[str, Any] = Field(default_factory=dict)
    stage_models: dict[str, ModelSelection] = Field(default_factory=dict)
    fallback_models: list[ModelSelection] = Field(default_factory=list, max_length=3)
    selected_paper_ids: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_mode(self) -> RunCreate:
        if self.profile != "free_research" and self.selected_paper_ids:
            raise ValueError("Selected literature requires the native research profile")
        if self.profile == "free_research" and not self.require_approval:
            raise ValueError("Genuine dynamic experiments require digest-bound human approval")
        if self.engine == "original" and self.profile != "full_research":
            raise ValueError("Original engine requires the full_research profile")
        if self.profile == "demo" and (
            self.provider != "mock" or self.stage_models or self.fallback_models
        ):
            raise ValueError("Demo requires the deterministic mock provider for every stage")
        if self.profile == "free_research" and (
            self.provider == "mock"
            or any(
                item.provider == "mock"
                for item in [*self.stage_models.values(), *self.fallback_models]
            )
        ):
            raise ValueError(
                "Free research requires a genuine provider; choose demo for mock responses"
            )
        return self


class Approval(StrictModel):
    approved: bool = True
    feedback: str = Field(default="", max_length=4000)
    idea_id: str | None = Field(default=None, max_length=100)
    constraints: dict[str, Any] | None = None
    action: Literal["continue", "retry", "report", "regenerate"] = "continue"
    approval_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class UpstreamImport(StrictModel):
    upstream_id: str = Field(min_length=1, max_length=303)


class APIRecord(BaseModel):
    """Persisted domain records are JSON; OpenAPI preserves their extensible fields."""

    model_config = ConfigDict(extra="allow")
    id: str


class ProjectResponse(APIRecord):
    title: str
    question: str
    domain: str
    objectives: list[str]
    references: list[str]
    created_at: str
    runs: list[dict[str, Any]] = Field(default_factory=list)


class RunResponse(APIRecord):
    project_id: str
    status: str
    current_stage: str | None
    profile: str
    provider: str
    model: str
    config: dict[str, Any]
    state: dict[str, Any]
    usage: dict[str, Any]
    created_at: str
    updated_at: str
    error: str | None
    approval: dict[str, Any] | None
