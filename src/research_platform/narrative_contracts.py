"""Typed native research narratives; schema validation does not certify their claims."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from .experiment_contract import ContractModel

IdeaId = (
    Annotated[str, Field(min_length=1, max_length=80)] | Annotated[int, Field(ge=1, le=2**31 - 1)]
)
ShortText = Annotated[str, Field(min_length=5, max_length=1600)]


class Hypothesis(ContractModel):
    id: IdeaId
    statement: ShortText
    test: ShortText


class ResearchPlan(ContractModel):
    summary: str = Field(min_length=10, max_length=4000)
    steps: list[str | dict[str, Any]] = Field(min_length=1, max_length=12)
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=8)
    baseline: str | dict[str, Any]
    risks: list[str | dict[str, Any]] = Field(min_length=1, max_length=10)
    required_resources: dict[str, Any]


class ResearchIdea(ContractModel):
    id: IdeaId
    title: str = Field(min_length=5, max_length=200)
    hypothesis: ShortText
    method: str = Field(min_length=10, max_length=4000)
    expected_outcome: ShortText
    risks: ShortText | list[ShortText]
    score: float = Field(ge=0, le=10)


class ResearchIdeas(ContractModel):
    ideas: list[ResearchIdea] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def distinct_ids(self) -> ResearchIdeas:
        identifiers = [str(idea.id) for idea in self.ideas]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Every candidate idea must have a distinct ID")
        return self


class IdeaSelection(ContractModel):
    idea_id: IdeaId
    rationale: str = Field(min_length=10, max_length=2000)


class EvidenceInterpretation(ContractModel):
    interpretation: str = Field(min_length=10, max_length=6000)
    limitations: list[ShortText] = Field(min_length=1, max_length=10)
    decision: Literal["iterate", "synthesize", "retry"]
    rationale: str = Field(min_length=10, max_length=2000)
