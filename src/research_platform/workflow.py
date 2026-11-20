"""Durable research orchestration around the existing investigation engine.

The graph owns stage ordering and human gates. Model calls, external literature,
artifact storage, and *actual* experiment execution belong to the supplied services.
In particular an LLM's proposed experiment is never treated as measured evidence.
Pass a SqliteSaver to ``create_workflow`` and use the run ID as the thread ID;
recreating this graph against the same saver resumes the same research session.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol, TypedDict, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from .reports import render_report
from .narrative_contracts import (
    EvidenceInterpretation,
    IdeaSelection,
    ResearchIdeas,
    ResearchPlan,
)
from .preparation import TaskPreparationError, _stage


class ResearchState(TypedDict, total=False):
    project_id: str
    run_id: str
    question: str
    domain: str
    objectives: list[str]
    constraints: dict[str, Any]
    provider: str
    model: str
    config: dict[str, Any]
    plan: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    literature: list[dict[str, Any]]
    ideas: list[dict[str, Any]]
    selected_idea: dict[str, Any]
    experiment_config: dict[str, Any]
    execution_phase: str
    results: dict[str, Any]
    experiment_history: list[dict[str, Any]]
    analysis: dict[str, Any]
    artifacts: list[dict[str, Any]]
    approval: dict[str, Any]
    iteration: int
    retries: int
    plan_revision: int
    budget: dict[str, Any]
    status: str
    stage: str
    errors: list[dict[str, Any]]
    trace_id: str
    trace_ids: list[str]
    decisions: list[dict[str, Any]]
    synthesis: str
    paper: str
    validation: dict[str, Any]
    outcome: str
    paused_node: str
    feasibility: dict[str, Any]
    program: dict[str, Any]
    _next: str


class WorkflowServices(Protocol):
    """Synchronous, externally persisted I/O boundary used by worker threads.

    ``execute`` must be idempotent for (run_id, iteration, execution_phase).
    ``save_artifact`` should upsert stable names within the current run.
    ``emit`` persists small structured events, never hidden chain-of-thought.
    ``model`` records/reserves real provider usage and propagates quota failures.
    """

    def emit(self, stage: str, kind: str, message: str, data: dict[str, Any]) -> None: ...

    def model(
        self,
        stage: str,
        prompt: str,
        *,
        json_schema: dict[str, Any] | None = None,
        max_output_tokens: int = 1024,
    ) -> str: ...

    def literature(self, question: str) -> list[dict[str, Any]]: ...

    def execute(self, state: ResearchState) -> dict[str, Any]: ...

    def save_artifact(
        self, name: str, content: str, media_type: str, kind: str
    ) -> dict[str, Any]: ...

    def control(self) -> str: ...

    def budget_available(self) -> bool: ...

    def feasibility(self, state: dict[str, Any]) -> dict[str, Any]: ...
    def prepare(self, state: dict[str, Any]) -> dict[str, Any]: ...
    def evaluator_validation(self, state: dict[str, Any]) -> dict[str, Any]: ...
    def generate_program(self, state: dict[str, Any]) -> dict[str, Any]: ...


class WorkflowBudgetExceeded(RuntimeError):
    """A checkpoint can resume this stage after its budget is increased."""

    code = "budget_exhausted"


# LangGraph 0.2 forbids nodes sharing names with state channels. Keep canonical
# stage IDs in events/interrupts while using stable, unambiguous runtime names.
NODE_NAMES = {
    name: f"{name}_stage"
    for name in ("literature", "ideas", "approval", "synthesis", "validation", "feasibility")
}


def node_name(stage: str) -> str:
    return NODE_NAMES.get(stage, stage)


STAGE_DEFAULTS = {
    "intake": "feasibility",
    "feasibility": "planning",
    "planning": "research_plan",
    "research_plan": "literature",
    "literature": "ideas",
    "ideas": "selection",
    "selection": "experiment_plan",
    "experiment_plan": "evaluator_validation",
    "evaluator_validation": "approval",
    "approval": "program_generation",
    "program_generation": "execution",
    "execution": "collection",
    "collection": "evaluation",
    "evaluation": "decision",
    "decision": "synthesis",
    "ablation": "synthesis",
    "final_evaluation": "synthesis",
    "synthesis": "report",
    "report": "validation",
    "validation": "completion",
}

# These are the *possible* transitions from each decision/gate, shared by the
# compiled graph and its diagram. A complete graph makes every scientific stage
# appear to call every other stage, obscuring the real research algorithm.
STAGE_BRANCHES = {
    "research_plan": {"planning", "synthesis"},
    "approval": {"experiment_plan", "ideas", "synthesis", "execution"},
    "decision": {"execution", "program_generation", "ideas", "ablation", "final_evaluation"},
    "ablation": {"final_evaluation"},
    "synthesis": {"validation"},
}


def workflow_topology() -> dict[str, Any]:
    """Return canonical IDs and real compiled edges, without executing any I/O."""
    diagram = create_workflow(cast(WorkflowServices, None), None).get_graph()
    inverse = {runtime: canonical for canonical, runtime in NODE_NAMES.items()}

    def canonical(name: str) -> str:
        return inverse.get(name, name)

    excluded = {START, END}
    nodes = [
        {"id": canonical(name), "label": canonical(name).replace("_", " ").title()}
        for name in diagram.nodes
        if name not in excluded
    ]
    edges = [
        {
            "source": canonical(edge.source),
            "target": canonical(edge.target),
            "conditional": bool(edge.conditional),
            "kind": "control"
            if "pause" in {edge.source, edge.target}
            or (edge.target == "completion" and edge.source != node_name("validation"))
            else "research",
        }
        for edge in diagram.edges
        if edge.source not in excluded and edge.target not in excluded
    ]
    return {"nodes": nodes, "edges": edges}


def initial_state(
    project_id: str,
    run_id: str,
    question: str,
    domain: str = "general",
    objectives: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
    provider: str = "mock",
    model: str = "mock-researcher",
    config: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> ResearchState:
    """Construct the serializable initial checkpoint, without performing I/O."""
    return ResearchState(
        project_id=project_id,
        run_id=run_id,
        question=question,
        domain=domain,
        objectives=list(objectives or []),
        constraints=dict(constraints or {}),
        provider=provider,
        model=model,
        config=dict(config or {}),
        budget=dict(budget or {}),
        plan={},
        hypotheses=[],
        literature=[],
        ideas=[],
        selected_idea={},
        experiment_config={},
        execution_phase="investigation",
        results={},
        experiment_history=[],
        analysis={},
        artifacts=[],
        approval={},
        iteration=1,
        retries=0,
        plan_revision=0,
        status="queued",
        stage="intake",
        errors=[],
        trace_id=trace_id or run_id,
        trace_ids=[trace_id or run_id],
        decisions=[],
        synthesis="",
        paper="",
        validation={},
        outcome="pending",
        paused_node="",
        _next="",
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, allow_nan=False)


def _compact(value: Any, *, depth: int = 0) -> Any:
    """Keep binary payloads and unbounded logs out of durable checkpoints/events."""
    if depth > 8:
        return "[nested content omitted]"
    if isinstance(value, str):
        return value if len(value) <= 8000 else value[:8000] + "\n[truncated; see artifact]"
    if isinstance(value, bytes):
        return "[binary content omitted; see artifact]"
    if isinstance(value, Mapping):
        return {str(k): _compact(v, depth=depth + 1) for k, v in list(value.items())[:200]}
    if isinstance(value, (list, tuple)):
        return [_compact(v, depth=depth + 1) for v in value[:100]]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)


def _object(text: str) -> dict[str, Any]:
    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(cleaned)
    except (ValueError, TypeError):
        return {"interpretation": cleaned[:8000]}
    return _compact(value) if isinstance(value, dict) else {"interpretation": cleaned[:8000]}


def _limit(state: ResearchState) -> int:
    cfg = state.get("config", {})
    budget = state.get("budget") or cfg.get("budgets", {})
    value = cfg.get(
        "max_iterations",
        cfg.get(
            "max_experiment_attempts",
            cfg.get(
                "max_idea_cycles", budget.get("max_iterations", budget.get("max_experiments", 3))
            ),
        ),
    )
    try:
        experiment_limit = int(budget.get("max_experiments", 50))
        return max(1, min(50, int(value), experiment_limit))
    except (TypeError, ValueError):
        return 3


def _paper_enabled(state: ResearchState) -> bool:
    cfg = state.get("config", {})
    return bool(
        cfg.get("paper_enabled", cfg.get("generate_report", cfg.get("generate_paper", True)))
    )


def _approval_enabled(state: ResearchState) -> bool:
    cfg = state.get("config", {})
    return bool(cfg.get("require_approval", cfg.get("human_approval", True)))


def create_workflow(services: WorkflowServices, checkpointer: BaseCheckpointSaver | None):
    """Compile the real LangGraph, using the caller's durable checkpoint saver.

    Start with ``graph.invoke(initial_state(...), config)``. Resume a human gate
    with ``graph.invoke(Command(resume={"approved": True}), config)``; recover
    a worker crash with ``graph.invoke(None, config)``. ``config`` must contain
    ``{"configurable": {"thread_id": run_id}, "recursion_limit": 1000}``.
    """
    graph = StateGraph(ResearchState)

    def model(
        stage: str,
        prompt: str,
        state: ResearchState,
        *,
        json_schema: dict[str, Any] | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        if not services.budget_available():
            raise WorkflowBudgetExceeded(
                f"Budget exhausted before {stage}; increase budget to resume"
            )
        context = {
            k: state.get(k)
            for k in (
                "question",
                "domain",
                "objectives",
                "constraints",
                "plan",
                "hypotheses",
                "literature",
                "ideas",
                "selected_idea",
                "experiment_config",
                "results",
                "iteration",
                "approval",
                "analysis",
            )
        }
        context["previous_observations"] = [
            {
                k: trial.get(k)
                for k in ("iteration", "execution_phase", "status", "metrics", "source")
            }
            for trial in state.get("experiment_history", [])[-5:]
        ]
        if native(state):
            # Artifact bodies and hidden evaluator data are never model context.
            context = {
                k: context[k]
                for k in (
                    "question",
                    "domain",
                    "objectives",
                    "constraints",
                    "selected_idea",
                    "iteration",
                )
            }
            context["feasibility"] = state.get("feasibility", {})
            prompt += " Only standard-library Python, 2-5 fixed seed replications, <=64 scheduling jobs or <=256 train/128 test regression rows, <=30 seconds per process are available. Do not promise external libraries, extra experiments or large studies. Report negative results without claiming discovery."
            context["metrics"] = state.get("results", {}).get("metrics", {})
            context["literature"] = [
                {"title": p.get("title"), "url": p.get("url")}
                for p in state.get("literature", [])[:4]
            ]
            result = state.get("results", {})
            context["approved_spec"] = state.get("experiment_config", {}).get("spec", {})
            context["statistical_summary"] = result.get("statistical_summary", {})
            context["per_seed"] = [
                {key: item.get(key) for key in ("seed", "baseline", "candidate", "improvement")}
                for item in result.get("per_seed", [])
                if isinstance(item, dict)
            ]
            context["execution"] = {
                key: result.get(key) for key in ("status", "source", "demo", "valid", "protocol")
            }
            if stage == "selection":
                # Selection must see the actual validated proposals. A protocol
                # name or plausible invented ID cannot substitute for one. Its
                # decision precedes execution, so outcome data and predictions
                # are unnecessary context and consume the same finite budget.
                context = {
                    "question": state.get("question"),
                    "objectives": state.get("objectives", []),
                    "constraints": state.get("constraints", {}),
                    "protocol": state.get("feasibility", {}).get("protocol"),
                    "ideas": [
                        {
                            key: item.get(key)
                            for key in ("id", "title", "hypothesis", "method", "risks", "score")
                        }
                        for item in state.get("ideas", [])[:5]
                    ],
                }
        context_json = (
            json.dumps(
                context, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            if native(state)
            else _json(context)
        )
        request = prompt + "\nResearch context:\n" + context_json
        options: dict[str, Any] = {}
        if json_schema is not None:
            options["json_schema"] = json_schema
        if max_output_tokens is not None:
            options["max_output_tokens"] = max_output_tokens
        elif native(state) and stage == "synthesis":
            options["max_output_tokens"] = 2048
        return services.model(stage, request, **options)

    def native(state: ResearchState) -> bool:
        return state.get("config", {}).get("profile") == "free_research"

    def narrative(
        stage: str,
        schema: type[BaseModel],
        prompt: str,
        state: ResearchState,
        *,
        validator: Callable[[Any], Any] | None = None,
    ) -> dict[str, Any]:
        def call(
            stage: str,
            prompt: str,
            *,
            json_schema: dict[str, Any] | None = None,
            max_output_tokens: int = 1024,
        ) -> str:
            return model(
                stage,
                prompt,
                state,
                json_schema=json_schema,
                max_output_tokens=max_output_tokens,
            )

        value, _ = _stage(
            stage,
            schema,
            prompt,
            call,
            max_repairs=1,
            validator=validator,
            emit=services.emit,
            max_output_tokens=1024,
        )
        return value.model_dump(mode="json")

    def feasibility(state: ResearchState) -> dict[str, Any]:
        if not native(state):
            return {}
        finding = services.feasibility(dict(state))
        if not finding.get("supported"):
            raise ValueError(
                "Research infeasible in the available independent execution protocols: "
                + str(finding.get("reason"))
            )
        return {"feasibility": finding}

    def evaluator_validation(state: ResearchState) -> dict[str, Any]:
        if not native(state):
            return {}
        return {"experiment_config": services.evaluator_validation(dict(state))}

    def program_generation(state: ResearchState) -> dict[str, Any]:
        if not native(state):
            return {}
        return {"program": services.generate_program(dict(state))}

    def event_decision(
        state: ResearchState,
        stage: str,
        decision: str,
        rationale: str,
        evidence: Any = None,
        **extra: Any,
    ) -> list[dict[str, Any]]:
        record = {
            "stage": stage,
            "decision": decision,
            "rationale": rationale,
            "evidence": _compact(evidence if evidence is not None else {}),
            "iteration": state.get("iteration", 1),
            "trace_id": state.get("trace_id"),
            **extra,
        }
        services.emit(stage, "decision", rationale, record)
        return [*state.get("decisions", []), record][-200:]

    def artifact(
        state: ResearchState,
        name: str,
        content: str,
        kind: str,
        media_type: str = "application/json",
    ) -> list[dict[str, Any]]:
        saved = services.save_artifact(name, content, media_type, kind)
        return [*state.get("artifacts", []), _compact(saved)][-200:]

    def wrap(stage: str, fn: Callable[[ResearchState], dict[str, Any]]):
        def wrapped(state: ResearchState) -> dict[str, Any]:
            identity: dict[str, Any] = getattr(services, "execution_identity", lambda: {})()
            if identity:
                state = cast(ResearchState, {**state, **identity})
            control = services.control()
            if control == "cancel":
                services.emit(stage, "decision", "Cancellation requested", {"decision": "cancel"})
                return {
                    "status": "cancelled",
                    "stage": stage,
                    "outcome": "cancelled",
                    "_next": "completion",
                }
            if control == "pause":
                # Persist the pause route before interrupting. The pause node
                # always calls interrupt on replay, even after the worker clears
                # the external control flag in order to resume this session.
                return {"status": "paused", "stage": stage, "paused_node": stage, "_next": "pause"}
            started = time.monotonic()
            services.emit(
                stage,
                "node_started",
                f"Started {stage.replace('_', ' ')}",
                {
                    "inputs": {
                        "question": state.get("question"),
                        "iteration": state.get("iteration"),
                        "selected_idea_id": state.get("selected_idea", {}).get("id"),
                    },
                    "trace_id": state.get("trace_id"),
                },
            )
            result = fn(state)
            result.update(identity)
            result.setdefault("status", "running")
            result["stage"] = stage
            result.setdefault("_next", "")
            services.emit(
                stage,
                "node_completed",
                f"Completed {stage.replace('_', ' ')}",
                {
                    "output": _compact(
                        {
                            k: v
                            for k, v in result.items()
                            if k not in {"paper", "artifacts", "decisions"}
                        }
                    ),
                    "duration_seconds": round(time.monotonic() - started, 4),
                    "trace_id": state.get("trace_id"),
                },
            )
            return result

        return wrapped

    def intake(state: ResearchState) -> dict[str, Any]:
        if not str(state.get("question", "")).strip():
            return {
                "status": "failed",
                "outcome": "invalid_intake",
                "errors": [
                    *state.get("errors", []),
                    {"stage": "intake", "message": "Question is required"},
                ],
            }
        return {"status": "running", "iteration": max(1, state.get("iteration", 1))}

    def planning(state: ResearchState) -> dict[str, Any]:
        prompt = (
            "Develop a falsifiable research plan. Return JSON with summary, steps, hypotheses "
            "(objects with id, statement, test), baseline, risks, and required_resources. "
            "Describe testable claims and uncertainty; do not invent observations or references."
        )
        plan = (
            narrative("planning", ResearchPlan, prompt, state)
            if native(state)
            else _object(model("planning", prompt, state))
        )
        hypotheses = plan.get("hypotheses", [])
        if not isinstance(hypotheses, list):
            hypotheses = []
        return {
            "plan": plan,
            "hypotheses": hypotheses,
            "artifacts": artifact(state, "research_plan.json", _json(plan), "research_plan"),
        }

    def gate(state: ResearchState, name: str) -> dict[str, Any]:
        if not _approval_enabled(state):
            return {"approval": {"gate": name, "approved": True, "automatic": True}}
        payload: dict[str, Any] = {
            "kind": "approval",
            "gate": name,
            "stage": name,
            "message": "Review the research plan"
            if name == "research_plan"
            else "Review the selected idea and experiment before execution",
            "plan": state.get("plan", {}),
            "ideas": state.get("ideas", []),
            "selected_idea": state.get("selected_idea", {}),
            "experiment_config": state.get("experiment_config", {}),
            "constraints": state.get("constraints", {}),
            "approval_digest": state.get("experiment_config", {}).get("approval_digest")
            if name == "approval"
            else None,
        }
        services.emit(name, "approval_required", payload["message"], payload)
        response = interrupt(payload)
        if not isinstance(response, dict):
            response = {"approved": bool(response)}
        action = response.get("action", response.get("decision"))
        if not action or action == "continue":
            action = "approve" if response.get("approved") else "reject"
        if native(state) and name == "approval" and action == "approve":
            expected_digest = state.get("experiment_config", {}).get("approval_digest")
            if (
                not isinstance(expected_digest, str)
                or len(expected_digest) != 64
                or any(char not in "0123456789abcdef" for char in expected_digest)
                or response.get("approval_digest") != expected_digest
            ):
                raise ValueError("Human approval does not match this frozen experiment")
        approval = {
            "gate": name,
            "approved": action == "approve",
            "action": action,
            "feedback": str(response.get("feedback", ""))[:4000],
            "approval_digest": response.get("approval_digest"),
        }
        update: dict[str, Any] = {"approval": approval}
        if isinstance(response.get("constraints"), dict):
            update["constraints"] = {**state.get("constraints", {}), **response["constraints"]}
        idea_id = response.get("idea_id", response.get("selected_idea"))
        if idea_id:
            selected = next(
                (idea for idea in state.get("ideas", []) if str(idea.get("id")) == str(idea_id)),
                None,
            )
            if selected is None:
                raise ValueError(f"Unknown selected idea: {idea_id}")
            update["selected_idea"] = selected
            if selected != state.get("selected_idea") and name == "approval":
                update["_next"] = "experiment_plan"
        if action in {"reject", "cancel"}:
            update.update(
                status="rejected" if action == "reject" else "cancelled",
                outcome="rejected" if action == "reject" else "cancelled",
                _next="completion",
            )
        elif action in {"report", "synthesize"}:
            update["_next"] = "synthesis"
        elif action in {"regenerate", "retry"}:
            if name == "research_plan":
                revisions = state.get("plan_revision", 0) + 1
                update["plan_revision"] = revisions
                update["_next"] = "planning" if revisions < 3 else "synthesis"
            elif native(state) and action == "retry":
                # Retrying a preparation is not approval to author or execute a
                # candidate. Revisit the concrete contract and ask again.
                update["_next"] = "experiment_plan"
            elif state.get("iteration", 1) < _limit(state):
                update["iteration"] = state.get("iteration", 1) + 1
                update["_next"] = "ideas" if action == "regenerate" else "execution"
            else:
                update["_next"] = "synthesis"
        elif action != "approve":
            raise ValueError(f"Unsupported approval action: {action}")
        elif name == "approval" and "constraints" in update:
            # Changed constraints need a new plan and a review of that concrete plan.
            if update["constraints"] != state.get("constraints", {}):
                update["_next"] = "experiment_plan"
        update["decisions"] = event_decision(
            state,
            name,
            str(action),
            f"Human decision at {name}: {action}",
            {
                "idea_id": idea_id,
                "constraints": update.get("constraints", state.get("constraints")),
            },
            source="human",
        )
        return update

    def literature(state: ResearchState) -> dict[str, Any]:
        papers = _compact(services.literature(state["question"]))
        return {"literature": papers if isinstance(papers, list) else []}

    def ideas(state: ResearchState) -> dict[str, Any]:
        prompt = (
            "Generate 3 distinct feasible research ideas grounded in the supplied literature. "
            "Return JSON {ideas:[{id,title,hypothesis,method,expected_outcome,risks,score}]}. "
            "Expected outcomes are predictions, never measured results. Respect constraints."
            + (
                " Keep every idea an implementation or replication of the EXACT user research question "
                "within the single feasibility-approved protocol and its one-baseline/one-candidate comparison. "
                "Preserve the requested algorithms, primary comparator and outcome. Vary implementation or "
                "replication details only; do not substitute orthogonal sensitivity studies, additional "
                "comparison arms or hypotheses about unmeasured methods or factors."
                if native(state)
                else ""
            )
        )
        response = (
            narrative("ideas", ResearchIdeas, prompt, state)
            if native(state)
            else _object(model("ideas", prompt, state))
        )
        generated = response.get("ideas", [])
        if not isinstance(generated, list) or not generated:
            if native(state):
                raise TaskPreparationError(
                    "No validated model-authored research ideas are available"
                )
            generated = [
                {
                    "id": f"idea-{state.get('iteration', 1)}",
                    "title": state["question"],
                    "hypothesis": response.get("interpretation", "Requires refinement"),
                    "method": "Compare an intervention against a fixed baseline",
                    "risks": ["Model returned unstructured ideas; human review required"],
                }
            ]
        normalized = [
            dict(item, id=str(item.get("id", f"idea-{i + 1}")))
            for i, item in enumerate(generated[:20])
            if isinstance(item, dict)
        ]
        return {
            "ideas": normalized,
            "results": {},
            "analysis": {},
            "execution_phase": "investigation",
        }

    def selection(state: ResearchState) -> dict[str, Any]:
        options = state.get("ideas", [])
        if not options:
            if native(state):
                raise TaskPreparationError("Selection requires validated candidate ideas")
            return {"status": "failed", "outcome": "no_valid_ideas"}
        prompt = (
            "Choose one provided idea using feasibility, novelty, falsifiability, and resources. "
            "Return JSON {idea_id,rationale}. Cite an exact supplied candidate idea ID; "
            "a protocol name or an invented ID is invalid."
        )
        if native(state):
            # Check checkpoint contents too; a legacy fabricated placeholder is
            # not a qualified proposal for genuine research.
            ResearchIdeas.model_validate({"ideas": options})
            identifiers = {str(item["id"]) for item in options}

            def verify_selection(value: IdeaSelection) -> None:
                if str(value.idea_id) not in identifiers:
                    raise ValueError(
                        "idea_id must match one of the supplied candidate IDs: "
                        + ", ".join(sorted(identifiers))
                    )

            response = narrative(
                "selection", IdeaSelection, prompt, state, validator=verify_selection
            )
        else:
            response = _object(model("selection", prompt, state))
        selected = next(
            (idea for idea in options if str(idea.get("id")) == str(response.get("idea_id"))),
            None if native(state) else options[0],
        )
        if selected is None:
            raise TaskPreparationError("Selection did not identify a validated candidate idea")
        rationale = str(
            response.get(
                "rationale",
                response.get(
                    "interpretation", "Selected the first feasible proposal; requires human review"
                ),
            )
        )
        return {
            "selected_idea": selected,
            "decisions": event_decision(
                state,
                "selection",
                "select_idea",
                rationale,
                {"selected_id": selected["id"], "candidate_ids": [i["id"] for i in options]},
                source="model_interpretation",
            ),
        }

    def experiment_plan(state: ResearchState) -> dict[str, Any]:
        if native(state):
            return {"experiment_config": services.prepare(dict(state))}
        plan = _object(
            model(
                "experiment_plan",
                (
                    "Plan a reproducible controlled experiment for the selected idea. Return JSON with "
                    "objective,baseline,intervention,metrics,success_criteria,reproducibility and limitations. "
                    "A host-controlled execution adapter chooses the supported experimental profile; "
                    "this proposal does not authorize arbitrary code execution."
                ),
                state,
            )
        )
        return {
            "experiment_config": plan,
            "artifacts": artifact(
                state,
                f"experiment_plan_{state.get('iteration', 1)}.json",
                _json(plan),
                "experiment_plan",
            ),
        }

    def run_experiment(state: ResearchState) -> dict[str, Any]:
        if not services.budget_available():
            raise WorkflowBudgetExceeded(
                "Budget exhausted before execution; increase budget to resume"
            )
        result = services.execute(state)
        if not isinstance(result, dict):
            raise TypeError("Execution service must return a result object")
        compact = _compact(result)
        compact["iteration"] = state.get("iteration", 1)
        compact["execution_phase"] = state.get("execution_phase", "investigation")
        return {
            "results": compact,
            "experiment_history": [*state.get("experiment_history", []), compact][-50:],
        }

    def collection(state: ResearchState) -> dict[str, Any]:
        result = state.get("results", {})
        saved = artifact(
            state, f"results_{state.get('iteration', 1)}.json", _json(result), "results"
        )
        for item in result.get("artifacts", []):
            if isinstance(item, dict) and item not in saved:
                saved.append(item)
        return {"artifacts": saved[-200:]}

    def evaluation(state: ResearchState) -> dict[str, Any]:
        result = state.get("results", {})
        metrics = result.get("metrics", {})
        observed = metrics if isinstance(metrics, dict) else {}
        failed = result.get("status") not in {"completed", "succeeded", "success"}
        if failed:
            interpretation = {
                "interpretation": "Execution did not complete successfully; no positive claim is supported.",
                "decision": "retry",
                "rationale": "Experiment execution failed",
            }
        elif services.budget_available():
            prompt = (
                "Interpret the ACTUAL supplied metrics and execution status only. Return JSON "
                "{interpretation,limitations,decision,rationale}, decision one of iterate,synthesize,retry. "
                "Do not invent trials, p-values, baselines, correctness, or causal conclusions. "
                "State that demo/mock results cannot support scientific claims."
            )
            interpretation = (
                narrative("evaluation", EvidenceInterpretation, prompt, state)
                if native(state)
                else _object(model("evaluation", prompt, state))
            )
        else:
            interpretation = {
                "interpretation": "Budget exhausted; inspect recorded metrics directly.",
                "decision": "synthesize",
                "rationale": "No remaining model budget",
            }
        analysis = {
            **interpretation,
            "observed_metrics": observed,
            "execution_status": result.get("status", "unavailable"),
            "source": "model_interpretation" if not failed else "execution_status",
            "evidence_available": bool(observed),
            "demo": bool(result.get("demo") or state.get("provider") == "mock"),
        }
        return {"analysis": analysis}

    def decision(state: ResearchState) -> dict[str, Any]:
        analysis, cfg = state.get("analysis", {}), state.get("config", {})
        proposed = analysis.get("decision", "synthesize")
        iteration = state.get("iteration", 1)
        failed = analysis.get("execution_status") not in {"completed", "succeeded", "success"}
        retries = state.get("retries", 0)
        try:
            retry_limit = max(0, min(10, int(cfg.get("max_retries", 1))))
        except (TypeError, ValueError):
            retry_limit = 1
        available = services.budget_available()
        update: dict[str, Any] = {}
        if iteration < _limit(state) and available and failed and retries < retry_limit:
            target, why = (
                "execution",
                "Retry a failed execution within the configured attempt budget",
            )
            update.update(iteration=iteration + 1, retries=retries + 1)
            if native(state):
                target = "program_generation"
        elif iteration < _limit(state) and available and not failed and proposed == "iterate":
            target, why = (
                "ideas",
                "Refine the hypothesis using observed results within the iteration budget",
            )
            update["iteration"] = iteration + 1
            if native(state):
                target = "program_generation"
        else:
            target = "synthesis"
            why = "Summarize available evidence"
            if not available:
                why = "Budget exhausted; synthesize recorded evidence without further model calls"
            elif iteration >= _limit(state):
                why = "Iteration limit reached; synthesize recorded evidence"
            elif failed:
                why = "Execution retry limit reached; report the failure and limitations"
            supported = cfg.get("supported_phases", [])
            if not failed and available and cfg.get("ablations") and "ablations" in supported:
                target = "ablation"
            elif (
                not failed
                and available
                and cfg.get("final_evaluation")
                and "final_evaluation" in supported
            ):
                target = "final_evaluation"
        update.update(
            _next=target,
            decisions=event_decision(
                state,
                "decision",
                target,
                why,
                {
                    "metrics": analysis.get("observed_metrics", {}),
                    "execution_status": analysis.get("execution_status"),
                    "iteration": iteration,
                    "max_iterations": _limit(state),
                    "budget_available": available,
                },
                model_proposal=proposed,
            ),
        )
        return update

    def optional_execution(state: ResearchState, phase: str) -> dict[str, Any]:
        if not services.budget_available():
            return {"_next": "synthesis"}
        update = run_experiment({**state, "execution_phase": phase})
        update["execution_phase"] = phase
        measured = update["results"]
        update["analysis"] = {
            "observed_metrics": measured.get("metrics", {}),
            "execution_status": measured.get("status", "unavailable"),
            "interpretation": "Optional phase observations are recorded in the execution artifact.",
            "limitations": measured.get("limitations", []),
            "source": "execution_status",
            "demo": bool(measured.get("demo")),
            "evidence_available": bool(measured.get("metrics")),
        }
        update["artifacts"] = artifact(
            state, f"{phase}_{state.get('iteration', 1)}.json", _json(measured), "results"
        )
        cfg = state.get("config", {})
        if (
            phase == "ablations"
            and cfg.get("final_evaluation")
            and "final_evaluation" in cfg.get("supported_phases", [])
        ):
            update["_next"] = "final_evaluation"
        else:
            update["_next"] = "synthesis"
        return update

    def synthesis(state: ResearchState) -> dict[str, Any]:
        if services.budget_available():
            text = model(
                "synthesis",
                (
                    "Write a concise evidence-based research synthesis in Markdown. Distinguish predictions, "
                    "model interpretations, and measured observations. Mention failures, missing measurements, "
                    "constraints, and limitations. Never assert significance without recorded statistical evidence. "
                    "Demo/mock runs must be explicitly described as demonstrations. "
                    + (
                        "Use at most 250 words. Use the actual approved specification, per-seed observations "
                        "and host-computed statistical summary. State the number of replications, the exact "
                        "reported p-value and its assumptions when present; do not describe multiple seeds as "
                        "one trial or infer significance from improvement alone."
                        if native(state)
                        else ""
                    )
                ),
                state,
            )
        else:
            text = "No further model interpretation was requested because the budget was exhausted."
        outcome = (
            "experiment_failed"
            if state.get("results", {}).get("status") in {"failed", "error", "cancelled", "timeout"}
            else "evidence_recorded"
        )
        if not state.get("results"):
            outcome = "no_experiment"
        return {
            "synthesis": str(text)[:16000],
            "outcome": outcome,
            "_next": "report" if _paper_enabled(state) else "validation",
        }

    def report(state: ResearchState) -> dict[str, Any]:
        manuscript = render_report(state)
        return {
            "paper": manuscript,
            "artifacts": artifact(
                state, "research_report.md", manuscript, "paper", "text/markdown"
            ),
        }

    def validation(state: ResearchState) -> dict[str, Any]:
        issues: list[str] = []
        result = state.get("results", {})
        if result and not isinstance(result.get("metrics", {}), dict):
            issues.append("Execution metrics must be an object")
        if _paper_enabled(state) and not state.get("paper"):
            issues.append("Research report is missing")
        validation_result = {
            "passed": not issues,
            "issues": issues,
            "evidence_available": bool(result.get("metrics")),
            "scientific_validity": "not_certified",
            "checks": [
                "report_available" if _paper_enabled(state) else "paper_disabled",
                "observations_separated_from_model_interpretation",
                "execution_provenance_recorded",
            ],
        }
        return {
            "validation": validation_result,
            "status": "failed" if issues else "running",
            "artifacts": artifact(state, "validation.json", _json(validation_result), "validation"),
        }

    def completion(state: ResearchState) -> dict[str, Any]:
        status = state.get("status", "running")
        if status not in {"cancelled", "rejected", "failed"}:
            status = "completed"
        services.emit(
            "completion",
            "node_completed",
            f"Research run {status}",
            {
                "status": status,
                "outcome": state.get("outcome"),
                "artifact_count": len(state.get("artifacts", [])),
                "trace_id": state.get("trace_id"),
            },
        )
        return {"status": status, "stage": "completion", "_next": ""}

    def pause(state: ResearchState) -> dict[str, Any]:
        response = interrupt(
            {
                "kind": "pause",
                "stage": state.get("paused_node"),
                "message": "Paused at a durable node boundary",
            }
        )
        if isinstance(response, dict) and response.get("action") == "cancel":
            return {"status": "cancelled", "outcome": "cancelled", "_next": "completion"}
        return {
            "status": "running",
            "_next": state.get("paused_node") or "intake",
            "paused_node": "",
        }

    nodes: dict[str, Callable[[ResearchState], dict[str, Any]]] = {
        "intake": intake,
        "feasibility": feasibility,
        "planning": planning,
        "research_plan": lambda state: gate(state, "research_plan"),
        "literature": literature,
        "ideas": ideas,
        "selection": selection,
        "experiment_plan": experiment_plan,
        "evaluator_validation": evaluator_validation,
        "approval": lambda state: gate(state, "approval"),
        "program_generation": program_generation,
        "execution": run_experiment,
        "collection": collection,
        "evaluation": evaluation,
        "decision": decision,
        "ablation": lambda state: optional_execution(state, "ablations"),
        "final_evaluation": lambda state: optional_execution(state, "final_evaluation"),
        "synthesis": synthesis,
        "report": report,
        "validation": validation,
    }
    for name, function in nodes.items():
        graph.add_node(node_name(name), wrap(name, function))
    graph.add_node("completion", completion)
    graph.add_node("pause", pause)
    graph.add_edge(START, "intake")

    def router(default: str):
        def route(state: ResearchState) -> str:
            if state.get("status") in {"cancelled", "rejected", "failed"}:
                return "completion"
            return state.get("_next") or default

        return route

    for name, target in STAGE_DEFAULTS.items():
        possible = {target, "completion", "pause", *STAGE_BRANCHES.get(name, set())}
        graph.add_conditional_edges(
            node_name(name), router(target), {key: node_name(key) for key in sorted(possible)}
        )
    graph.add_conditional_edges(
        "pause", router("intake"), {key: node_name(key) for key in [*nodes, "completion"]}
    )
    graph.add_edge("completion", END)
    return graph.compile(checkpointer=checkpointer)
