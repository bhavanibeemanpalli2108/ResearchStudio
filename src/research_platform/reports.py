"""Deterministic report presentation from persisted evidence; no I/O or model calls."""

from __future__ import annotations
import json
import math
from collections.abc import Mapping
from typing import Any

REPORT_VERSION = "native-studio-v1"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, allow_nan=False)


def _native(state: Mapping[str, Any]) -> bool:
    return state.get("config", {}).get("profile") == "free_research"


def render_report(state: Mapping[str, Any]) -> str:
    if _native(state):
        return _native_report(state)
    result, analysis = state.get("results", {}), state.get("analysis", {})
    demo = bool(result.get("demo") or state.get("provider") == "mock")
    rows = []
    metrics = result.get("metrics", {})
    if isinstance(metrics, dict):
        for key, value in metrics.items():
            rows.append(f"| {str(key).replace('|', '/')} | `{_json(value).replace('|', '/')}` |")
    table = (
        "\n".join(["| Recorded metric | Value |", "| --- | --- |", *rows])
        if rows
        else "No measured metrics are available."
    )
    measured_statistics = ""
    refs = (
        "\n".join(
            f"- {p.get('title', 'Untitled source')} â€” {p.get('url', p.get('doi', 'No source URL'))}"
            for p in state.get("literature", [])
            if isinstance(p, dict)
        )
        or "No literature sources were retrieved."
    )
    history = [
        {
            "iteration": r.get("iteration"),
            "phase": r.get("execution_phase"),
            "status": r.get("status"),
            "metrics": r.get("metrics", {}),
            "source": r.get("source"),
        }
        for r in state.get("experiment_history", [])
    ]
    manuscript = (
        f"# Research report: {state.get('question', '')}\n\n"
        "AI-generated draft. Human scientific review is required before use or publication.\n\n"
        + (
            "**DEMONSTRATION / MOCK RUN:** These results illustrate the workflow and do not support scientific claims.\n\n"
            if demo
            else ""
        )
        + f"## Research question and plan\n\n{state.get('question', '')}\n\n"
        + f"Plan: {_json(state.get('plan', {}))}\n\n"
        + f"## Selected hypothesis\n\n{_json(state.get('selected_idea', {}))}\n\n"
        + f"## Reproducibility\n\nProvider: {state.get('provider')}; model: {state.get('model')}; "
        + f"run: {state.get('run_id')}; execution source: {result.get('source', 'unavailable')}.\n\n"
        + f"Constraints: `{_json(state.get('constraints', {}))}`\n\n"
        + f"Proposed experiment: `{_json(state.get('experiment_config', {}))}`\n\n"
        + f"Actual execution configuration: `{_json(result.get('configuration', {}))}`\n\n"
        + f"## Recorded observations\n\nExecution status: **{result.get('status', 'not executed')}**.\n\n{table}\n\n"
        + measured_statistics
        + f"All attempts (recorded evidence):\n\n```json\n{_json(history)}\n```\n\n"
        + f"## Model interpretation (unverified)\n\n{state.get('synthesis', '')}\n\n"
        + f"## Limitations\n\nModel limitations: {_json(analysis.get('limitations', []))}\n\n"
        + f"Execution adapter limitations: {_json(result.get('limitations', []))}\n\n"
        + "Metrics are supplied by the execution adapter. A model's interpretation is not independently verified evidence. "
        + "Missing measurements, independent replications, statistical tests, or evaluator correctness are not implied.\n\n"
        + f"## Literature\n\n{refs}\n\n"
        + f"## Provenance\n\nTrace ID: {state.get('trace_id')}. Outcome: {state.get('outcome')}. "
        + "The event timeline records stage inputs, outputs, approvals, and decision summaries.\n"
        + "\nSoftware attribution: Research Studio extends SakanaAI's Agentic Scientist, "
        + "licensed under Apache-2.0: https://github.com/SakanaAI/AI-Scientist-v3. "
        + "See the upstream CITATION.cff for the original project's scholarly citation.\n"
    )
    return manuscript


def _cell(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ")


def _native_report(state: Mapping[str, Any]) -> str:
    result = state.get("results", {})
    plan = state.get("experiment_config", {})
    spec = plan.get("spec", {})
    observed = result.get("per_seed", [])
    summary = result.get("statistical_summary", {})
    identity = result.get("execution_identity", {})
    references = {
        "report_version": REPORT_VERSION,
        "run_id": state.get("run_id"),
        "approval_digest": plan.get("approval_digest"),
        "prepared_digest": plan.get("prepared_digest", result.get("frozen_hash")),
        "spec_hash": result.get("spec_hash"),
        "dataset_sha256": result.get("dataset_sha256"),
        "evaluator_sha256": result.get("evaluator_sha256"),
        "baseline_sha256": identity.get("baseline_sha256"),
        "candidate_sha256": identity.get("candidate_sha256"),
        "image_id": result.get("image_id"),
        "source": result.get("source", "unavailable"),
        "artifact_ids": result.get("artifact_ids", []),
    }
    sections = [
        f"# Research report: {state.get('question', '')}",
        "AI-generated research draft with deterministic evidence presentation. Human scientific review is required before publication.",
        "## Final approved experiment contract",
        "This specification and final approval digest define the approved design. Historical proposals below do not override them.",
        f"Final approved digest: `{plan.get('approval_digest', 'unavailable')}`",
        "```json\n" + _json(spec) + "\n```",
        f"Provider: {state.get('provider')}; model: {state.get('model')}; run: {state.get('run_id')}.",
    ]
    if not spec or not plan.get("approval_digest"):
        sections.append(
            "**Incomplete approval provenance:** an exact approved contract cannot be established from this state."
        )
    if result.get("configuration", {}).get("spec") not in (None, spec):
        sections.append(
            "**Provenance mismatch:** recorded execution specification differs from the approved specification. Do not accept this report without investigation."
        )
    sections += [
        "## Recorded observations",
        f"Execution status: **{result.get('status', 'not executed')}**. Source: `{result.get('source', 'unavailable')}`.",
        "Values below are retained trusted execution measurements, not predictions or reconstructed model claims.",
    ]
    if observed:
        sections += [
            "Per-seed paired observations:",
            "| Seed | Baseline | Candidate | Baseline minus candidate |",
            "| --- | ---: | ---: | ---: |",
            *[
                "| "
                + " | ".join(
                    _cell(row.get(key, "unavailable"))
                    for key in ("seed", "baseline", "candidate", "improvement")
                )
                + " |"
                for row in observed
            ],
            f"Paired seed observations: {len(observed)}. One baseline/candidate pair per listed seed; no additional replications are implied.",
        ]
    else:
        sections.append(
            "No per-seed measurements are available. No experimental success is implied."
        )
    sections += [
        "Recorded aggregate metrics:\n\n```json\n" + _json(result.get("metrics", {})) + "\n```",
        "## Independently computed statistics",
        "Recorded host-computed summary and assumptions:\n\n```json\n" + _json(summary) + "\n```",
    ]
    p = summary.get("paired_sign_flip_p_value")
    if isinstance(p, (int, float)) and not isinstance(p, bool) and math.isfinite(p) and 0 <= p <= 1:
        sections.append(
            f"Exact two-sided paired sign-flip p-value: **{p}**. "
            + (
                "This does not meet the 0.05 threshold; statistical significance at that level is not established."
                if p >= 0.05
                else "This is below 0.05 under the stated test assumptions; it does not certify validity, novelty or generalization, and adaptive selection remains exploratory."
            )
        )
    else:
        sections.append(
            "No valid recorded p-value is available; statistical significance is not established."
        )
    sections += [
        "A positive baseline-minus-candidate difference favors the candidate for this minimizing metric; zero is a tie. Improvement alone is not statistical significance. A Student-t interval uses different assumptions from the exact sign-flip test.",
        f"Approved minimum mean improvement: `{spec.get('evaluation', {}).get('minimum_improvement', 'unavailable')}`. Recorded threshold outcome: `{result.get('meets_minimum_improvement', 'unavailable')}` (strictly greater, not a significance test).",
        "## Frozen execution references",
        "The final approval digest binds preparation and frozen evaluation. A preparation-only digest in an execution receipt is a separate identity, not a replacement for final approval.",
        "```json\n" + _json(references) + "\n```",
        "## Recorded attempts and execution logs",
        "```json\n"
        + _json(
            [
                {
                    k: row.get(k)
                    for k in ("iteration", "execution_phase", "status", "metrics", "source")
                }
                for row in state.get("experiment_history", [])
            ]
        )
        + "\n```",
        "```json\n" + _json(result.get("logs", [])) + "\n```",
        "## Limitations",
        "Synthetic data support conclusions only for the approved generator and frozen inputs. Reported model prose is not independently verified scientific evidence. No unrecorded runs, extra replications, novelty or generalization are claimed.",
        "Recorded execution limitations:\n\n```json\n"
        + _json(result.get("limitations", []))
        + "\n```",
        "Model interpretation and its claims remain in the original model-response artifacts and persisted state for audit; they are not used to derive this report's measured conclusions.",
        "## Historical proposals — superseded, not executed as written",
        "The following original plan and idea are historical model proposals. Counts, signs, replication suggestions and resource requests may have been rejected or corrected. Only the final approved contract above and actual observations describe this execution.",
        "```json\n"
        + _json(
            {"initial_plan": state.get("plan", {}), "proposed_idea": state.get("selected_idea", {})}
        )
        + "\n```",
        "## Literature metadata",
        "Metadata retrieval is not verification of claims, novelty or coverage.",
        *[
            f"- {_cell(row.get('title', 'Untitled'))} — {row.get('url', row.get('doi', 'No URL'))}"
            for row in state.get("literature", [])
            if isinstance(row, dict)
        ],
        "## Provenance",
        f"Report renderer: {REPORT_VERSION}. This is a read-only presentation of retained evidence; original state and immutable artifacts are not rewritten.",
        "Software attribution: Research Studio extends SakanaAI's Agentic Scientist (Apache-2.0), https://github.com/SakanaAI/AI-Scientist-v3; see CITATION.cff.",
    ]
    return "\n\n".join(sections) + "\n"
