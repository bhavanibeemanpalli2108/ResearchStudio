"""Budgeted model-authored experiment preparation with component-level repair.

Only declarations and source text are inspected here. Source execution belongs
to the Docker sandbox; metrics belong to the independent trusted evaluator.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .experiment_contract import (
    EvaluationDeclaration,
    ExperimentSpec,
    Feasibility,
    GeneratedProgram,
    PreparationProvenance,
    PreparedExperiment,
    ProgramArtifact,
    canonical_hash,
    expected_evaluation,
    program_artifact,
    validate_prepared_experiment,
)
from .prompt_budget import literature_context, idea_context, OUTPUT_LIMITS
from .providers import StructuredOutputError

T = TypeVar("T", bound=BaseModel)
ComponentCallback = Callable[[str, dict[str, Any]], Any]


class ModelCall(Protocol):
    def __call__(
        self,
        stage: str,
        prompt: str,
        *,
        json_schema: dict[str, Any] | None = None,
        max_output_tokens: int = 2048,
    ) -> str: ...


class TaskPreparationError(RuntimeError):
    code = "preparation_invalid"


class UnsupportedResearchError(TaskPreparationError):
    code = "research_unsupported"


def response_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 80000:
        raise ValueError("Stage response exceeds the supported JSON size")
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(
            cleaned,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError("Nonfinite JSON value")
            ),
        )
    except (ValueError, TypeError, RecursionError):
        raise ValueError(
            "Return one complete finite JSON object without surrounding prose"
        ) from None
    if not isinstance(value, dict):
        raise ValueError("Return a JSON object, not an array or scalar")
    return value


def _validation_summary(error: Exception) -> str:
    # ValidationError.__str__ includes rejected input/code; only locations and
    # classifications are used in repair requests or persisted public errors.
    if isinstance(error, ValidationError):
        return "; ".join(
            ".".join(str(part) for part in item["loc"]) + ": " + item["type"]
            for item in error.errors(include_input=False, include_context=False)[:12]
        )
    return str(error)[:600]


def _question(state: Mapping[str, Any]) -> str:
    value = state.get("question")
    if not isinstance(value, str) or not 10 <= len(value) <= 4000:
        raise TaskPreparationError("A research question of 10 to 4000 characters is required")
    return value


def _emit(
    emit: Callable[..., Any] | None, stage: str, kind: str, message: str, data: dict[str, Any]
) -> None:
    if emit is not None:
        emit(stage, kind, message, data)


def _stage(
    name: str,
    schema: type[T],
    prompt: str,
    model_call: ModelCall,
    *,
    previous: Any = None,
    max_repairs: int = 1,
    validator: Callable[[T], Any] | None = None,
    on_component: ComponentCallback | None = None,
    emit: Callable[..., Any] | None = None,
    max_output_tokens: int = 2048,
) -> tuple[T, PreparationProvenance]:
    if previous is not None:
        try:
            cached = schema.model_validate(previous)
            if validator:
                validator(cached)
            return cached, PreparationProvenance(attempts=1, content_sha256=canonical_hash(cached))
        except (ValidationError, ValueError):
            pass
    repairs = max(0, min(int(max_repairs), 2))
    max_output_tokens = min(max_output_tokens, OUTPUT_LIMITS.get(name, max_output_tokens))
    feedback = ""
    last_error = "Stage output was not validated"
    for attempt in range(repairs + 1):
        request = prompt
        if feedback:
            request += (
                "\nRepair ONLY this component. Previously validated components are immutable. "
                + feedback
            )
        _emit(
            emit,
            name,
            "preparation_request",
            "Preparing a validated research component",
            {"component": name, "attempt": attempt + 1},
        )
        try:
            answer = model_call(
                name,
                request,
                json_schema=schema.model_json_schema(),
                max_output_tokens=max_output_tokens,
            )
            component = schema.model_validate(response_object(answer))
            if validator:
                validator(component)
        except (ValidationError, ValueError, StructuredOutputError) as error:
            last_error = _validation_summary(error)
            feedback = "Validation requirements: " + last_error
            _emit(
                emit,
                name,
                "preparation_rejected",
                "Component rejected before execution",
                {"component": name, "attempt": attempt + 1, "validation": last_error},
            )
            continue
        serialized = component.model_dump(mode="json")
        if on_component:
            on_component(name, serialized)
        provenance = PreparationProvenance(
            attempts=attempt + 1, content_sha256=canonical_hash(component)
        )
        _emit(
            emit,
            name,
            "preparation_validated",
            "Research component validated before execution",
            {"component": name, **provenance.model_dump()},
        )
        return component, provenance
    raise TaskPreparationError(
        f"{name} failed its bounded validation and repair budget: {last_error}"
    )


def assess_feasibility(
    state: Mapping[str, Any],
    model_call: ModelCall,
    *,
    max_repairs: int = 1,
    previous: Mapping[str, Any] | Feasibility | None = None,
    emit: Callable[..., Any] | None = None,
    on_component: ComponentCallback | None = None,
) -> Feasibility:
    question = _question(state)
    context = {
        "question": question,
        "domain": state.get("domain"),
        "objectives": state.get("objectives", []),
        "constraints": state.get("constraints", {}),
    }
    prompt = (
        "Assess whether the EXACT user research question can be studied honestly with the available CPU protocols. "
        "Return only JSON matching the supplied schema. Do not replace the question with an unrelated benchmark. "
        "Available protocols: regression_v1 predicts scalar numerical targets from synthetic linear, quadratic or sinusoidal feature data; "
        "scheduling_v1 compares single-machine job ordering using total completion time, FIFO baseline. "
        "Only Python standard library, no network, filesystem access, packages, private data, real-world interventions or hardware. "
        "A synthetic computational study cannot establish real-world medical, financial, legal or causal conclusions. "
        "If the question cannot be answered within this scope, supported=false, protocol=null; explain the concrete missing capability. "
        "State assumptions and limitations. Scope is a proposal, never measured evidence.\nContext:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    value, _ = _stage(
        "feasibility",
        Feasibility,
        prompt,
        model_call,
        previous=previous.model_dump(mode="json")
        if isinstance(previous, Feasibility)
        else previous,
        max_repairs=max_repairs,
        emit=emit,
        on_component=on_component,
        max_output_tokens=1536,
    )
    return value


def _prior_components(previous: Mapping[str, Any] | PreparedExperiment | None) -> dict[str, Any]:
    if isinstance(previous, PreparedExperiment):
        return previous.model_dump(mode="json")
    if not previous:
        return {}
    values = dict(previous.get("components", previous))
    # Persisted per-stage callback names are also accepted on restart.
    for stage, field in (
        ("experiment_spec", "spec"),
        ("baseline_program", "baseline"),
        ("evaluation_contract", "evaluation_contract"),
    ):
        if stage in values and field not in values:
            values[field] = values[stage]
    return values


def prepare_experiment(
    state: Mapping[str, Any],
    model_call: ModelCall,
    *,
    previous: Mapping[str, Any] | PreparedExperiment | None = None,
    emit: Callable[..., Any] | None = None,
    on_component: ComponentCallback | None = None,
    max_repairs: int = 1,
    include_candidate: bool = False,
) -> PreparedExperiment:
    question = _question(state)
    prior = _prior_components(previous)
    prior_feasibility = prior.get("feasibility", state.get("feasibility"))
    feasibility = assess_feasibility(
        state,
        model_call,
        previous=prior_feasibility,
        max_repairs=max_repairs,
        emit=emit,
        on_component=on_component,
    )
    if not feasibility.supported:
        raise UnsupportedResearchError(
            "Research is outside the supported computational scope: " + feasibility.reason[:600]
        )
    provenance: dict[str, PreparationProvenance] = {
        "feasibility": PreparationProvenance(attempts=1, content_sha256=canonical_hash(feasibility))
    }

    def verify_spec(value: ExperimentSpec) -> None:
        if value.research_question != question:
            raise ValueError("research_question must copy the original question byte-for-byte")
        if value.protocol != feasibility.protocol:
            raise ValueError("Protocol must match the validated feasibility assessment")
        if state.get("config", {}).get("selected_literature") and value.hypothesis != state.get(
            "selected_idea", {}
        ).get("hypothesis"):
            raise ValueError(
                "hypothesis must copy the selected literature-grounded hypothesis exactly"
            )

    context = {
        "question": question,
        "selected_idea": idea_context(state.get("selected_idea", {})),
        "scope": feasibility.scope_statement,
        "constraints": state.get("constraints", {}),
    }
    if state.get("config", {}).get("selected_literature"):
        context["selected_literature"] = literature_context(state, "experiment_spec")
    specification, provenance["experiment_spec"] = _stage(
        "experiment_spec",
        ExperimentSpec,
        "Design the actual selected experiment. Return only an ExperimentSpec JSON using the supplied schema. "
        "Copy research_question EXACTLY, including whitespace and punctuation. Choose frozen synthetic generator parameters, 2-5 distinct seeds and an appropriate metric. "
        "If a selected hypothesis is supplied, copy it EXACTLY into hypothesis. Keep other text concise. "
        "Test the exact primary comparison requested by that question using ONE reference baseline and ONE candidate. "
        "The selected idea is advisory: preserve the user's requested algorithms, comparator and outcome when translating it into this protocol. "
        "Do not introduce extra comparison arms, orthogonal sensitivity studies or additional factors unless the question explicitly requests them and the selected protocol supports measuring them. "
        "The hypothesis must describe only the comparison actually measured by this baseline and candidate; never assert an advantage over an unmeasured third method or claim an effect of an uncontrolled factor. "
        "No results exist yet. For regression each feature is uniform [-1,1]; target = intercept + sum(coefficients[j]*basis(x[j])) + independent Gaussian noise, "
        "basis is x for linear, x*x for quadratic, sin(pi*x) for sinusoidal. Train/test rows are distinct; held-out labels and private noise are never sent to programs. "
        "For scheduling, generate uniform positive integer job durations for one machine; metric total_completion_time sums job completion times. "
        "Resource bounds: stdlib only, at most30 seconds,128-512MiB; use timeout_seconds=10,memory_mb=256 unless a reason requires more. "
        "Select minimum_improvement as an absolute metric reduction to test, not a promised outcome.\nContext:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":")),
        model_call,
        previous=prior.get("spec"),
        max_repairs=max_repairs,
        validator=verify_spec,
        on_component=on_component,
        emit=emit,
        max_output_tokens=1536,
    )
    public_spec = specification.model_dump(mode="json")
    protocol_description = _protocol_description(specification)
    baseline_prompt = (
        "Author the executable BASELINE program for this approved protocol. Return only JSON {source:string,description:string}. "
        "Import json and sys. Read one object using json.load(sys.stdin), print exactly one JSON object; no Markdown, logs, packages, filesystem, network, eval, exec or subprocess. "
        "Use only allowed stdlib modules json,sys,math,statistics,random,itertools,functools,collections,heapq,bisect,array,operator. "
        "The baseline is INDEPENDENTLY checked: regression must predict the arithmetic mean of the observed training y values for EVERY test row; "
        "scheduling must return order=list(range(len(durations))) (FIFO). Do not weaken this reference. "
        "Do not return a candidate, evaluator, scores or observations.\nInterface:\n"
        + protocol_description
        + "\nSpec:\n"
        + json.dumps(public_spec, separators=(",", ":"), ensure_ascii=False)
    )
    prior_baseline = prior.get("baseline")
    if isinstance(prior_baseline, Mapping):
        prior_baseline = {key: prior_baseline.get(key) for key in ("source", "description")}
    generated_baseline, provenance["baseline_program"] = _stage(
        "baseline_program",
        GeneratedProgram,
        baseline_prompt,
        model_call,
        previous=prior_baseline,
        max_repairs=max_repairs,
        on_component=on_component,
        emit=emit,
    )
    baseline = program_artifact(generated_baseline)
    expected = expected_evaluation(specification)

    def verify_evaluation(value: EvaluationDeclaration) -> None:
        if value != expected:
            raise ValueError(
                "Use the frozen spec hash, selected metric, reference baseline and trusted independent evaluator declaration exactly"
            )

    evaluation, provenance["evaluation_contract"] = _stage(
        "evaluation_contract",
        EvaluationDeclaration,
        "Review and explicitly accept this frozen independent evaluation contract. Return exactly the supplied declaration as JSON, no evaluator code. "
        "The host generator and scorer are trusted application code, not authored by you or the candidate. "
        "RMSE=sqrt(mean((prediction-hidden_target)^2)); MAE=mean(abs(prediction-hidden_target)). "
        "Scheduling requires an exact permutation of all job indices; total_completion_time is the sum of cumulative duration in that order. "
        "Malformed, nonfinite, incorrect-length outputs are invalid; program-reported scores are never trusted.\nDeclaration:\n"
        + json.dumps(expected.model_dump(mode="json"), separators=(",", ":")),
        model_call,
        previous=prior.get("evaluation_contract"),
        max_repairs=max_repairs,
        validator=verify_evaluation,
        on_component=on_component,
        emit=emit,
        max_output_tokens=512,
    )
    digest = canonical_hash(
        {
            "spec": public_spec,
            "baseline": baseline.model_dump(mode="json"),
            "evaluation_contract": evaluation.model_dump(mode="json"),
        }
    )
    prepared = PreparedExperiment(
        feasibility=feasibility,
        spec=specification,
        baseline=baseline,
        evaluation_contract=evaluation,
        spec_hash=canonical_hash(specification),
        approval_digest=digest,
        provenance=provenance,
    )
    if include_candidate:
        candidate = generate_candidate(
            prepared, model_call, max_repairs=max_repairs, emit=emit, on_component=on_component
        )
        prepared = PreparedExperiment.model_validate(
            {**prepared.model_dump(mode="json"), "candidate": candidate.model_dump(mode="json")}
        )
    return prepared


def _protocol_description(specification: ExperimentSpec) -> str:
    if specification.protocol == "regression_v1":
        return 'stdin={"train":[{"x":[number,...],"y":number},...],"test":[{"x":[number,...]},...],"seed":integer}; stdout={"predictions":[finite number for each test row]}. No test targets are present.'
    return 'stdin={"durations":[positive integer,...],"seed":integer}; stdout={"order":[every input job index exactly once]}. A single machine runs jobs sequentially in that order.'


def generate_candidate(
    prepared: PreparedExperiment | Mapping[str, Any],
    model_call: ModelCall,
    previous_results: Mapping[str, Any] | None = None,
    *,
    previous: Mapping[str, Any] | ProgramArtifact | None = None,
    max_repairs: int = 1,
    emit: Callable[..., Any] | None = None,
    on_component: ComponentCallback | None = None,
) -> ProgramArtifact:
    contract = validate_prepared_experiment(prepared)
    # Only aggregate measured feedback is allowed into a revision request.
    # Hidden inputs, target labels, scorer code, raw predictions and salts are
    # deliberately not accepted into this stateless code-generation context.
    feedback: dict[str, Any] = {}
    if previous_results:
        for key in ("status", "aggregate_metrics", "metrics", "failure_code"):
            value = previous_results.get(key)
            if key in {"status", "failure_code"} and isinstance(value, str):
                feedback[key] = value[:150]
            elif key in {"aggregate_metrics", "metrics"} and isinstance(value, Mapping):
                feedback[key] = {
                    str(k)[:80]: v
                    for k, v in value.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                }
    public_spec = contract.spec.model_dump(mode="json")
    if contract.spec.protocol == "regression_v1":
        # A stateless candidate may know the chosen function family but must
        # estimate its parameters from training labels, not copy the generator.
        public_spec["dataset"] = {
            key: value
            for key, value in public_spec["dataset"].items()
            if key not in {"coefficients", "intercept"}
        }
    public = {
        "spec": public_spec,
        "baseline_source": contract.baseline.source,
        "previous_aggregate_observations": feedback,
    }
    prompt = (
        "Author a genuine CANDIDATE algorithm to investigate this exact question and hypothesis. Return only JSON {source:string,description:string}. "
        "Import json and sys; read JSON with json.load(sys.stdin), print only one JSON observation object. "
        "Use only Python stdlib json,sys,math,statistics,random,itertools,functools,collections,heapq,bisect,array,operator; no packages/files/network/subprocess/eval/exec. "
        "Learn from supplied training data or optimize the supplied scheduling instance. Never hardcode hidden answers, report your own metric, inspect other processes, or fabricate measurements. "
        "The dataset, baseline, scorer, seeds, split and success criterion are frozen; improve only this candidate implementation. "
        "No held-out labels, evaluator source, private fixture data or previous raw predictions are available. "
        "This call is stateless with respect to private evaluation preparation.\nInterface:\n"
        + _protocol_description(contract.spec)
        + "\nPublic research context:\n"
        + json.dumps(public, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    )
    cached = previous.model_dump(mode="json") if isinstance(previous, ProgramArtifact) else previous
    if cached:
        cached = {key: cached.get(key) for key in ("source", "description")}

    def verify_candidate(value: GeneratedProgram) -> None:
        if value.source == contract.baseline.source:
            raise ValueError(
                "Candidate must be a separately authored implementation, not the unchanged baseline"
            )

    generated, _ = _stage(
        "candidate_program",
        GeneratedProgram,
        prompt,
        model_call,
        previous=cached,
        max_repairs=max_repairs,
        validator=verify_candidate,
        on_component=on_component,
        emit=emit,
    )
    artifact = program_artifact(generated)
    return artifact
