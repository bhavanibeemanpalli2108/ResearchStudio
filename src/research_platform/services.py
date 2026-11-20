"""Durable research I/O, accounting and lifecycle operations."""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from typing import Any

import httpx
from sqlalchemy import select

from .artifacts import ArtifactStore
from .config import Settings
from .database import (
    Database,
    Artifact,
    Decision,
    Experiment,
    Job,
    ModelUsage,
    ResearchItem,
    Run,
    TraceReference,
    WorkflowEvent,
    as_dict,
    utcnow,
)
from .execution import DockerExecutor, ExecutionCancelled
from .ledger import BudgetExceeded, accounting_lock, reserve_model_call, refresh_usage
from .ledger import usage_summary as usage_summary
from .literature import LiteratureClient, LiteratureError
from .providers import Completion, ProviderError, ProviderRouter, estimate_tokens
from .scientist_adapter import ScientistAdapter
from .tracing import redacted_trace

TERMINAL = {"completed", "failed", "cancelled", "canceled", "rejected"}


class LostLease(RuntimeError):
    code = "lost_lease"


class ExecutionInterrupted(RuntimeError):
    code = "execution_interrupted"


def record_event(
    session: Any, run_id: str, stage: str, kind: str, message: str, data: dict | None = None
) -> WorkflowEvent:
    row = WorkflowEvent(run_id=run_id, stage=stage, kind=kind, message=message, data=data or {})
    session.add(row)
    return row


class ResearchServices:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        run_id: str,
        owner: str,
        *,
        router: ProviderRouter | None = None,
        adapter: ScientistAdapter | None = None,
    ) -> None:
        self.settings, self.database, self.run_id, self.owner = settings, database, run_id, owner
        self.artifacts = ArtifactStore(settings.artifact_root, database)
        self.adapter = adapter or ScientistAdapter(
            results_root=settings.upstream_results_root,
            executor=DockerExecutor(
                image=os.environ.get("RESEARCH_CPU_IMAGE", "python:3.12-slim"),
                timeout_seconds=settings.max_experiment_runtime,
            ),
        )
        self.router = router or ProviderRouter(
            on_request=self.reserve_call, sleep=self.provider_wait
        )
        self.router.on_request = self.reserve_call
        self.retrieval = LiteratureClient(settings.artifact_root.parent / "literature-cache")
        self.reservation_ids: list[str] = []
        self.last_request_at = 0.0
        self.active_started = time.monotonic()
        self.verified_models: set[tuple[str, str]] = set()

    def provider_wait(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.control() == "cancel":
                raise ExecutionCancelled("Run cancelled while waiting for the provider")
            time.sleep(min(0.2, max(0, deadline - time.monotonic())))

    def bound_request_timeout(self) -> None:
        self.control()
        run = self.run_record()
        remaining = (
            run["config"]["budgets"]["max_runtime_seconds"]
            - run["usage"].get("runtime_seconds", 0)
            - (time.monotonic() - self.active_started)
        )
        self.router.client.timeout = httpx.Timeout(
            max(0.1, min(45.0, remaining)), connect=max(0.1, min(5.0, remaining))
        )

    def run_record(self) -> dict[str, Any]:
        with self.database.sessions() as session:
            run = session.get(Run, self.run_id)
            assert run is not None
            return as_dict(run)

    def execution_identity(self) -> dict[str, Any]:
        """Use the current operator selection when resuming an older checkpoint."""
        run = self.run_record()
        return {"provider": run["provider"], "model": run["model"]}

    def control(self) -> str:
        with self.database.sessions() as session:
            job = session.scalar(select(Job).where(Job.run_id == self.run_id))
            if job is None or job.owner != self.owner or job.lease_until < time.time():
                raise LostLease("Worker no longer owns this run")
            run = session.get(Run, self.run_id)
            assert run is not None
            if run.control == "cancel" or run.status in {"cancelled", "canceled"}:
                return "cancel"
            if run.control == "pause":
                return "pause"
            if (
                run.usage.get("runtime_seconds", 0) + time.monotonic() - self.active_started
                > run.config["budgets"]["max_runtime_seconds"]
            ):
                raise BudgetExceeded(
                    "Maximum active execution duration reached. Start a new run with a larger duration."
                )
            return "none"

    def budget_available(self) -> bool:
        self.control()
        run = self.run_record()
        budget = run["config"]["budgets"]
        usage = run["usage"]
        return (
            usage.get("calls", 0) < budget["max_llm_calls"]
            and usage.get("reserved_input_tokens", 0) < budget["max_input_tokens"]
            and usage.get("reserved_output_tokens", 0) < budget["max_output_tokens"]
        )

    def emit(self, stage: str, kind: str, message: str, data: dict[str, Any]) -> None:
        self.control()
        with self.database.sessions.begin() as session:
            self.assert_lease(session)
            run = session.get(Run, self.run_id)
            assert run is not None
            run.current_stage, run.updated_at = stage, utcnow()
            record_event(session, self.run_id, stage, kind, message, data)
            if kind in {"decision", "node_completed", "stage_completed"}:
                session.add(Decision(run_id=self.run_id, stage=stage, summary=message, data=data))
        if kind in {"node_completed", "node_failed"}:
            with self.trace(
                "Research stage",
                stage,
                {
                    "status": "failed" if kind == "node_failed" else "completed",
                    "duration_seconds": data.get("duration_seconds"),
                    "iteration": data.get("iteration"),
                },
            ):
                pass

    def assert_lease(self, session: Any) -> None:
        job = session.scalar(select(Job).where(Job.run_id == self.run_id).with_for_update())
        if job is None or job.owner != self.owner or job.lease_until < time.time():
            raise LostLease("Worker no longer owns this run")

    @contextmanager
    def trace(self, name: str, stage: str, metadata: dict[str, Any]):
        run = self.run_record()
        with redacted_trace(
            name, self.run_id, stage, {**metadata, "project_id": run["project_id"]}
        ) as reference:
            yield reference
        if reference.get("trace_id"):
            with self.database.sessions.begin() as session:
                self.assert_lease(session)
                session.merge(
                    TraceReference(
                        id=reference["trace_id"],
                        run_id=self.run_id,
                        url=reference.get("trace_url"),
                        data=reference,
                    )
                )

    def reserve_call(
        self, provider: str, model: str, stage: str, prompt: str, maximum: int
    ) -> None:
        control = self.control()
        if control == "cancel":
            raise ExecutionCancelled("Run cancelled before provider request")
        self.bound_request_timeout()
        # Pauses are applied by graph interrupts at a durable node boundary.
        delay = max(0.0, self.last_request_at + 0.2 - time.monotonic())
        if delay:
            time.sleep(delay)
        with self.database.sessions.begin() as session:
            accounting_lock(session)
            run = session.get(Run, self.run_id)
            assert run is not None
            self.assert_lease(session)
            row = reserve_model_call(
                session,
                run,
                daily_limit=self.settings.daily_api_call_budget,
                provider=provider,
                model=model,
                stage=stage,
                predicted=estimate_tokens(prompt),
                maximum=maximum,
            )
            self.reservation_ids.append(row.id)
        self.last_request_at = time.monotonic()

    def finish_call(self, completion: Completion) -> None:
        self.control()
        with self.database.sessions.begin() as session:
            self.assert_lease(session)
            row = session.get(ModelUsage, self.reservation_ids[-1])
            assert row is not None
            row.status = "completed"
            row.input_tokens, row.output_tokens = completion.input_tokens, completion.output_tokens
            row.reported = not completion.usage_is_estimated
            row.estimated_cost = completion.estimated_cost
            row.reserved_output_tokens = 0
            run = session.get(Run, self.run_id)
            assert run is not None
            refresh_usage(session, run)
            record_event(
                session,
                self.run_id,
                row.stage,
                "usage",
                "Model invocation completed",
                {
                    "provider": completion.provider,
                    "model": completion.model,
                    "input_tokens": row.input_tokens,
                    "output_tokens": row.output_tokens,
                    "reported": row.reported,
                },
            )

    def generation_preflight(self, provider: str, model: str) -> None:
        """Verify the exact selection before research calls, on this run's ledger.

        Recheck on worker resume: readiness is a point-in-time observation, not
        a promise about future quota. Failures keep their existing reservations.
        """
        identity = (provider, model)
        if provider == "mock" or identity in self.verified_models:
            return
        self.bound_request_timeout()
        self.reservation_ids = []
        readiness: dict[str, Any] = {
            "provider": provider,
            "model": model,
            "generation_verified": False,
            "status": "unavailable",
            "ledger": "run",
            "max_attempts": 1,
            "max_output_tokens": 128,
        }
        try:
            result = self.router.preflight(provider, model)
            self.finish_call(result)
        except (ProviderError, BudgetExceeded) as error:
            readiness.update(
                {
                    "error": error.code,
                    "detail": str(error),
                    "status_code": getattr(error, "status_code", None),
                    "retryable": getattr(error, "retryable", False),
                    "action": "Check credentials, account quota and model access; explicitly select another configured provider/model or retry when available. Reservations are retained.",
                }
            )
            self.emit(
                "provider_preflight", "provider_readiness", "Generation preflight failed", readiness
            )
            raise
        readiness.update(
            {
                "status": "generation_verified",
                "generation_verified": True,
                "detail": "Bounded generation succeeded at this time; future requests may still fail.",
            }
        )
        self.emit(
            "provider_preflight", "provider_readiness", "Generation preflight succeeded", readiness
        )
        self.verified_models.add(identity)

    def model(
        self,
        stage: str,
        prompt: str,
        *,
        json_schema: dict[str, Any] | None = None,
        max_output_tokens: int = 1024,
    ) -> str:
        self.bound_request_timeout()
        run = self.run_record()
        selected = (
            run["config"]
            .get("stage_models", {})
            .get(stage, {"provider": run["provider"], "model": run["model"]})
        )
        maximum = min(max_output_tokens, run["config"]["budgets"]["max_output_tokens"])
        options: dict[str, Any] = {"json_schema": json_schema} if json_schema else {}
        self.generation_preflight(selected["provider"], selected["model"])
        self.reservation_ids = []
        with self.trace("Model invocation", stage, {**selected, "profile": run["profile"]}):
            try:
                result = self.router.complete(
                    selected["provider"], selected["model"], stage, prompt, maximum, **options
                )
            except ProviderError:
                for fallback in run["config"].get("fallback_models", []):
                    try:
                        self.emit(
                            stage,
                            "provider_selection",
                            "Using an explicitly configured fallback",
                            fallback,
                        )
                        self.generation_preflight(fallback["provider"], fallback["model"])
                        self.reservation_ids = []
                        result = self.router.complete(
                            fallback["provider"],
                            fallback["model"],
                            stage,
                            prompt,
                            maximum,
                            **options,
                        )
                        break
                    except ProviderError:
                        continue
                else:
                    raise
            self.finish_call(result)
            if run["profile"] != "demo":
                self.save_artifact(
                    f"model-{stage}-{self.reservation_ids[-1]}.txt",
                    result.text,
                    "text/plain",
                    "model_response",
                )
            return result.text

    def literature(self, question: str) -> list[dict[str, Any]]:
        run = self.run_record()
        with self.trace("Literature discovery", "literature", {"profile": run["profile"]}):
            try:
                return self.retrieval.search(question, demo=run["profile"] == "demo")
            except LiteratureError:
                self.emit(
                    "literature",
                    "warning",
                    "Literature metadata is unavailable; continuing without retrieved citations. "
                    "This run cannot establish novelty or literature coverage.",
                    {"code": "literature_unavailable", "verified_citations": 0},
                )
                return []

    def read_artifact(self, artifact_id: str) -> str:
        with self.database.sessions() as session:
            row = session.get(Artifact, artifact_id)
            if row is None or row.run_id != self.run_id:
                raise ValueError("Artifact does not belong to this research run")
            content = self.artifacts.checked_path(row.relative_path).read_bytes()
            if hashlib.sha256(content).hexdigest() != row.sha256:
                raise ValueError("Artifact content digest mismatch")
            return content.decode("utf-8")

    def feasibility(self, state: dict[str, Any]) -> dict[str, Any]:
        from .preparation import assess_feasibility

        return assess_feasibility(state, self.model).model_dump(mode="json")

    def prepare(self, state: dict[str, Any]) -> dict[str, Any]:
        from .preparation import prepare_experiment
        from .experiment_contract import canonical_hash

        context_id = canonical_hash(
            {k: state.get(k) for k in ("question", "objectives", "constraints", "selected_idea")}
        )[:16]
        previous: dict[str, Any] = {"feasibility": state.get("feasibility")}
        with self.database.sessions() as session:
            components = list(
                session.scalars(
                    select(Artifact)
                    .where(Artifact.run_id == self.run_id, Artifact.kind == "preparation_component")
                    .order_by(Artifact.created_at)
                )
            )
        for component in components:
            prefix = f"prepare-{context_id}-"
            if component.name.startswith(prefix):
                previous[component.name[len(prefix) : -5]] = json.loads(
                    self.read_artifact(component.id)
                )

        def on_component(stage: str, data: dict[str, Any]) -> None:
            self.save_artifact(
                f"prepare-{context_id}-{stage}.json",
                json.dumps(data),
                "application/json",
                "preparation_component",
            )

        prepared = prepare_experiment(
            state, self.model, previous=previous, emit=self.emit, on_component=on_component
        )
        item = self.save_artifact(
            f"prepared-{prepared.approval_digest}.json",
            prepared.model_dump_json(indent=2),
            "application/json",
            "prepared_experiment",
        )
        self.save_artifact(
            f"baseline-{prepared.baseline.sha256[:16]}.py",
            prepared.baseline.source,
            "text/x-python",
            "source",
        )
        return {
            "prepared_artifact_id": item["id"],
            "approval_digest": prepared.approval_digest,
            "spec": prepared.spec.model_dump(mode="json"),
            "baseline_sha256": prepared.baseline.sha256,
            "evaluation_contract": prepared.evaluation_contract.model_dump(mode="json"),
            "context_id": context_id,
        }

    def dynamic_executor(self):
        from .dynamic_execution import DynamicExperimentExecutor

        return DynamicExperimentExecutor(
            image=os.getenv("RESEARCH_CPU_IMAGE", "python:3.12-slim"),
            timeout_seconds=self.settings.max_experiment_runtime,
            fixture_root=self.settings.artifact_root.parent / "private-evaluations",
        )

    def evaluator_validation(self, state: dict[str, Any]) -> dict[str, Any]:
        from .experiment_contract import validate_prepared_experiment, canonical_hash

        prepared = validate_prepared_experiment(
            json.loads(self.read_artifact(state["experiment_config"]["prepared_artifact_id"]))
        )
        commitment = self.dynamic_executor().freeze_evaluation(
            self.run_id, prepared, self.settings.artifact_root / self.run_id / "evaluation"
        )
        # Approval binds both the public design and the actual hidden dataset commitment.
        approval_digest = canonical_hash(
            {
                "prepared_digest": prepared.approval_digest,
                "dataset_sha256": commitment["dataset_sha256"],
            }
        )
        artifact = self.save_artifact(
            f"evaluator-validation-{approval_digest}.json",
            json.dumps(commitment, indent=2),
            "application/json",
            "evaluator_validation",
        )
        return {
            **state["experiment_config"],
            "prepared_digest": prepared.approval_digest,
            "approval_digest": approval_digest,
            "evaluation_validation": commitment,
            "validation_artifact_id": artifact["id"],
        }

    def generate_program(self, state: dict[str, Any]) -> dict[str, Any]:
        from .experiment_contract import validate_prepared_experiment
        from .preparation import generate_candidate

        plan = state["experiment_config"]
        approved_digest = state.get("approval", {}).get("approval_digest")
        if (
            not isinstance(approved_digest, str)
            or len(approved_digest) != 64
            or any(character not in "0123456789abcdef" for character in approved_digest)
            or approved_digest != plan.get("approval_digest")
        ):
            from .execution import CapabilityError

            raise CapabilityError(
                "Candidate generation requires approval of this exact frozen experiment"
            )
        prepared = validate_prepared_experiment(
            json.loads(self.read_artifact(plan["prepared_artifact_id"]))
        )
        candidate = generate_candidate(
            prepared, self.model, previous_results=state.get("results") or None
        )
        item = self.save_artifact(
            f"candidate-{candidate.sha256[:16]}.py", candidate.source, "text/x-python", "source"
        )
        return {"artifact_id": item["id"], "sha256": candidate.sha256, "origin": "model"}

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        self.control()
        run = self.run_record()
        if run["profile"] != "demo" and run["config"].get("execution_protocol") != 2:
            from .execution import CapabilityError

            raise CapabilityError(
                "Obsolete genuine execution protocol; create a new protocol-v2 run"
            )
        iteration = int(state.get("iteration", 1))
        retry = int(state.get("retries", 0))
        phase = str(state.get("execution_phase", "investigation"))
        experiment_id = hashlib.sha256(
            f"{self.run_id}:{iteration}:{phase}:{retry}".encode()
        ).hexdigest()[:40]
        with self.database.sessions.begin() as session:
            self.assert_lease(session)
            previous = session.get(Experiment, experiment_id)
            if previous and previous.status == "completed":
                return previous.configuration["result"]
            recovering = bool(previous and previous.status == "running")
            attempts = list(
                session.scalars(select(Experiment).where(Experiment.run_id == self.run_id))
            )
            count = sum(int(item.configuration.get("launch_attempts", 1)) for item in attempts)
            if count >= run["config"]["budgets"]["max_experiments"] and not recovering:
                raise BudgetExceeded("Experiment-attempt budget exhausted")
            if previous is None:
                session.add(
                    Experiment(
                        id=experiment_id,
                        run_id=self.run_id,
                        status="running",
                        hypothesis=str(state.get("selected_idea", {}).get("hypothesis", "")),
                        configuration={**state.get("experiment_config", {}), "launch_attempts": 1},
                    )
                )
            elif not recovering:
                previous.configuration = {
                    **previous.configuration,
                    "launch_attempts": int(previous.configuration.get("launch_attempts", 1)) + 1,
                }
                previous.status = "running"
        directory = self.settings.artifact_root / self.run_id / "execution" / experiment_id
        profile = {"demo": "demo", "free_research": "free", "full_research": "full"}[run["profile"]]
        try:
            if recovering and not (directory / "execution_result.json").is_file():
                raise ExecutionInterrupted(
                    "The prior worker stopped without an experiment receipt. Execution was not repeated. Review the run, then Resume explicitly to retry within the remaining attempt budget."
                )
            with self.trace(
                "Experiment execution",
                "execution",
                {"profile": run["profile"], "iteration": iteration},
            ):
                if profile == "free":
                    from .experiment_contract import validate_prepared_experiment, canonical_hash
                    from .execution import CapabilityError

                    plan = state["experiment_config"]
                    prepared = validate_prepared_experiment(
                        json.loads(self.read_artifact(plan["prepared_artifact_id"]))
                    )
                    digest = canonical_hash(
                        {
                            "prepared_digest": prepared.approval_digest,
                            "dataset_sha256": plan["evaluation_validation"]["dataset_sha256"],
                        }
                    )
                    if (
                        digest != plan["approval_digest"]
                        or state.get("approval", {}).get("approval_digest") != digest
                    ):
                        raise CapabilityError(
                            "Execution is not bound to the approved dataset and evaluator"
                        )
                    source = self.read_artifact(state["program"]["artifact_id"])
                    if hashlib.sha256(source.encode()).hexdigest() != state["program"]["sha256"]:
                        raise CapabilityError("Candidate source digest mismatch")
                    result = self.dynamic_executor().execute(
                        self.run_id,
                        prepared,
                        directory,
                        candidate_source=source,
                        dataset_sha256=plan["evaluation_validation"]["dataset_sha256"],
                        cancel_check=lambda: self.control() == "cancel",
                    )
                else:
                    result = self.adapter.execute(
                        self.run_id,
                        profile,
                        state.get("experiment_config", {}),
                        directory,
                        cancel_check=lambda: self.control() == "cancel",
                    )
            artifact = self.save_artifact(
                f"experiment-{experiment_id}.json",
                json.dumps(result, indent=2),
                "application/json",
                "experiment",
            )
            result = {**result, "experiment_id": experiment_id, "artifact_ids": [artifact["id"]]}
            with self.database.sessions.begin() as session:
                self.assert_lease(session)
                row = session.get(Experiment, experiment_id)
                assert row is not None
                row.status, row.finished_at = "completed", utcnow()
                row.metrics = result.get("metrics", {})
                logs = result.get("logs", "")
                row.logs = "\n".join(logs) if isinstance(logs, list) else str(logs)
                row.configuration = {**row.configuration, "result": result}
                row.artifact_ids = [artifact["id"]]
            return result
        except Exception as error:
            with self.database.sessions.begin() as session:
                self.assert_lease(session)
                row = session.get(Experiment, experiment_id)
                assert row is not None
                row.status, row.finished_at = "failed", utcnow()
                row.error = safe_error(error)
            if profile == "free" and getattr(error, "code", "") in {
                "experiment_protocol_error",
                "execution_failed",
                "execution_timeout",
            }:
                return {
                    "status": "failed",
                    "error": safe_error(error),
                    "metrics": {},
                    "demo": False,
                    "source": "dynamic_python_v2",
                    "experiment_id": experiment_id,
                }
            raise

    def save_artifact(self, name: str, content: str, media_type: str, kind: str) -> dict[str, Any]:
        self.control()
        with self.trace("Artifact publication", "report", {"status": "completed"}):
            result = self.artifacts.save(self.run_id, name, content, media_type, kind)
        self.emit(
            "report" if kind in {"paper", "report"} else "collection",
            "artifact",
            "Research artifact published",
            result,
        )
        return result

    def close(self) -> None:
        self.router.close()
        self.retrieval.close()


def safe_error(error: Exception) -> str:
    # Only our explicitly classified errors are safe for clients. Arbitrary
    # transport/process exceptions can carry environment paths or credentials.
    if getattr(error, "code", None):
        return f"{getattr(error, 'code')}: {str(error)[:500]}"
    return f"{type(error).__name__}: The operation failed; inspect local server logs."


def persist_research_items(session: Any, run_id: str, state: dict[str, Any]) -> None:
    for key, kind in [("ideas", "idea"), ("hypotheses", "hypothesis")]:
        for index, item in enumerate(state.get(key, [])):
            item_id = f"{run_id}:{kind}:{index}"
            existing = session.get(ResearchItem, item_id)
            if existing:
                existing.data = item
            else:
                session.add(ResearchItem(id=item_id, run_id=run_id, kind=kind, data=item))
