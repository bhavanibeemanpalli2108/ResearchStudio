"""Deterministic prompt projections and conservative stage allocations, not usage."""

from __future__ import annotations

from typing import Any, Mapping
import json

OUTPUT_LIMITS = {
    "feasibility": 1024,
    "planning": 1024,
    "ideas": 1024,
    "selection": 512,
    "experiment_spec": 1536,
    "baseline_program": 1536,
    "evaluation_contract": 512,
    "candidate_program": 2048,
    "evaluation": 1024,
    "synthesis": 1024,
}


def compact_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove annotations only; preserve constraints, field names and $refs."""
    result: dict[str, Any] = {}
    maps = {"properties", "$defs", "definitions", "patternProperties"}
    nodes = {"items", "additionalProperties", "not", "if", "then", "else", "contains"}
    lists = {"anyOf", "allOf", "oneOf", "prefixItems"}
    for key, value in schema.items():
        if key in {"title", "description", "default", "examples"}:
            continue
        if key in maps and isinstance(value, dict):
            result[key] = {
                k: compact_schema(v) if isinstance(v, dict) else v for k, v in value.items()
            }
        elif key in nodes and isinstance(value, dict):
            result[key] = compact_schema(value)
        elif key in lists and isinstance(value, list):
            result[key] = [compact_schema(v) for v in value]
        else:
            result[key] = value
    return result


def budgeted_prompt(prompt: str, schema: dict[str, Any] | None) -> str:
    return prompt + (
        "\nRequired JSON schema:\n"
        + json.dumps(
            compact_schema(schema), ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        if schema is not None
        else ""
    )


def literature_context(state: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    """Full provenance stays in snapshots/manifests, not repeated model context."""
    papers = state.get("config", {}).get("selected_literature", []) or state.get("literature", [])
    rows: list[dict[str, Any]] = []
    seen = set()
    abstracts: dict[str, str] = {}
    excerpt_budget = 2400
    for paper in papers[:10]:
        if not isinstance(paper, dict):
            continue
        identity = paper.get("id") or paper.get("url")
        if not isinstance(identity, str) or identity in seen:
            continue
        seen.add(identity)
        row: dict[str, Any] = {"id": identity}
        title = paper.get("title")
        if isinstance(title, str):
            row["title"] = title[:200]
            if len(title) > 200:
                row["title_truncated"] = True
        if isinstance(paper.get("year"), int):
            row["year"] = paper["year"]
        if stage in {"planning", "ideas"}:
            abstract = paper.get("abstract")
            if isinstance(abstract, str) and abstract.strip() in abstracts:
                row["abstract_same_as"] = abstracts[abstract.strip()]
                rows.append(row)
                continue
            if isinstance(abstract, str) and abstract.strip() and excerpt_budget:
                excerpt = abstract.strip()[: min(480, excerpt_budget)]
                excerpt_budget -= len(excerpt)
                row.update(
                    abstract=excerpt,
                    abstract_source=paper.get("abstract_source"),
                    excerpt_truncated=len(excerpt) < len(abstract.strip())
                    or bool(paper.get("abstract_truncated")),
                )
                abstracts[abstract.strip()] = identity
        rows.append(row)
    return rows


def idea_context(idea: Mapping[str, Any]) -> dict[str, Any]:
    return {k: idea[k] for k in ("id", "hypothesis", "method", "citation_ids") if k in idea}


def future_capacity(stage: str) -> tuple[int, int, int]:
    """Protect a minimal next candidate/evaluation/report path, not a success guarantee."""
    if stage in {
        "feasibility",
        "planning",
        "ideas",
        "selection",
        "experiment_spec",
        "baseline_program",
        "evaluation_contract",
    }:
        return 10240, 4096, 3
    if stage == "candidate_program":
        return 6144, 2048, 2
    if stage == "evaluation":
        return 3072, 1024, 1
    return 0, 0, 0
