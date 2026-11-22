"""Selected-source identity checks and approval binding; no scientific claim certification."""

from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from .experiment_contract import canonical_hash

SOURCE_FIELDS = (
    "id",
    "selection_id",
    "title",
    "authors",
    "year",
    "doi",
    "url",
    "abstract",
    "abstract_source",
    "abstract_truncated",
    "retrieved_at",
    "provenance",
)


def selected_sources(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("config", {}).get("selected_literature", []))


def source_context(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected = selected_sources(state)
    if selected:
        return [
            {key: paper[key] for key in SOURCE_FIELDS if paper.get(key) is not None}
            for paper in selected[:10]
        ]
    return [{"title": p.get("title"), "url": p.get("url")} for p in state.get("literature", [])[:4]]


def validate_citations(
    items: list[Any], state: Mapping[str, Any], *, rationale: bool = False
) -> None:
    papers = selected_sources(state)
    if not papers:
        return
    allowed = {paper["id"] for paper in papers}
    for item in items:
        value = item.model_dump() if hasattr(item, "model_dump") else item
        ids = value.get("citation_ids", [])
        if not ids or len(set(ids)) != len(ids) or not set(ids) <= allowed:
            raise ValueError(
                "citation_ids must be distinct, nonempty exact IDs from selected literature: "
                + ", ".join(sorted(allowed))
            )
        if rationale and not value.get("literature_rationale"):
            raise ValueError(
                "A literature_rationale based only on available metadata/excerpts is required"
            )


def grounding_manifest(state: Mapping[str, Any]) -> dict[str, Any] | None:
    if not selected_sources(state):
        return None
    idea = state.get("selected_idea", {})
    validate_citations([idea], state, rationale=True)
    return {
        "version": 1,
        "sources": source_context(state),
        "idea_id": str(idea["id"]),
        "hypothesis": idea["hypothesis"],
        "citation_ids": idea["citation_ids"],
        "literature_rationale": idea["literature_rationale"],
        "claim_status": "AI interpretation; source identifiers checked, paper findings and novelty unverified",
    }


def verify_grounding(state: Mapping[str, Any]) -> dict[str, Any] | None:
    expected = grounding_manifest(state)
    plan = state.get("experiment_config", {})
    if expected is not None:
        if plan.get("grounding_manifest") != expected or plan.get(
            "grounding_sha256"
        ) != canonical_hash(expected):
            raise ValueError(
                "Literature/hypothesis grounding differs from prepared contract; new preparation and approval required"
            )
        if plan.get("spec", {}).get("hypothesis") != expected["hypothesis"]:
            raise ValueError(
                "Approved experiment hypothesis differs from literature-grounded hypothesis"
            )
    elif plan.get("grounding_manifest") or plan.get("grounding_sha256"):
        raise ValueError("Unexpected grounding in unselected research")
    return expected


def approval_binding(prepared_digest: str, dataset_sha256: str, plan: Mapping[str, Any]) -> str:
    payload = {"prepared_digest": prepared_digest, "dataset_sha256": dataset_sha256}
    if plan.get("grounding_sha256"):
        payload["grounding_sha256"] = plan["grounding_sha256"]
    return canonical_hash(payload)
