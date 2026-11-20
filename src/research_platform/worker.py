"""Independent, lease-based durable worker. Run with python -m ...worker."""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import signal
import socket
import threading
import time
from typing import Any

from langgraph.types import Command
from sqlalchemy import func, select, text

from .checkpoints import checkpoints
from .config import Settings
from .database import Database, Job, Project, Run, new_id, utcnow
from .services import (
    TERMINAL,
    LostLease,
    ResearchServices,
    persist_research_items,
    record_event,
    refresh_usage,
    safe_error,
)
from .workflow import create_workflow, initial_state

logger = logging.getLogger("research_platform.worker")


class Worker:
    def __init__(
        self,
        settings: Settings,
        database: Database | None = None,
        services_factory: Any = ResearchServices,
    ) -> None:
        self.settings = settings
        settings.prepare()
        self.database = database or Database(settings.database_url)
        self.owner = f"{socket.gethostname()}:{os.getpid()}:{new_id()[:8]}"
        self.services_factory = services_factory
        self.stop = threading.Event()

    def claim(self) -> tuple[str, dict[str, Any] | None] | None:
        now = time.time()
        with self.database.sessions.begin() as session:
            if self.database.engine.dialect.name == "sqlite":
                session.execute(text("BEGIN IMMEDIATE"))
            else:
                session.execute(text("SELECT pg_advisory_xact_lock(7213922)"))
            # Stale owners are reconciled only after their heartbeat lease has
            # expired. Old workers lose ownership before any more side effects.
            for expired_job in session.scalars(
                select(Job).where(Job.status.in_(["running", "running_v2"]), Job.lease_until < now)
            ):
                run = session.get(Run, expired_job.run_id)
                assert run is not None
                expired_job.status, expired_job.owner, expired_job.lease_until = (
                    ("queued_v2" if run.profile != "demo" else "queued"),
                    None,
                    0,
                )
                if run.status not in TERMINAL:
                    run.status, run.updated_at = "queued", utcnow()
                    record_event(
                        session,
                        run.id,
                        run.current_stage or "intake",
                        "recovery",
                        "Expired worker lease recovered; checkpoint and experiment receipt will be reconciled",
                    )
            session.flush()
            active = (
                session.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(Job.status.in_(["running", "running_v2"]), Job.lease_until >= now)
                )
                or 0
            )
            if active >= self.settings.max_concurrent_jobs:
                return None
            job = session.scalar(
                select(Job).where(Job.status.in_(["queued", "queued_v2"])).order_by(Job.id).limit(1)
            )
            if job is None:
                return None
            run = session.get(Run, job.run_id)
            assert run is not None
            if run.profile != "demo" and run.config.get("execution_protocol") != 2:
                job.status = "waiting_v2"
                run.status, run.error = (
                    "paused",
                    "Obsolete genuine execution protocol; create a protocol-v2 research run",
                )
                return None
            if run.status in TERMINAL:
                job.status = "done"
                return None
            payload = job.resume_payload
            job.status, job.owner = (
                ("running_v2" if run.profile != "demo" else "running"),
                self.owner,
            )
            job.lease_until, job.heartbeat_at = now + self.settings.lease_seconds, utcnow()
            job.attempts += 1
            run.status, run.updated_at, run.error = "running", utcnow(), None
            run.started_at = run.started_at or utcnow()
            return run.id, payload

    def heartbeat(self, run_id: str, finished: threading.Event) -> None:
        while not finished.wait(max(1, self.settings.lease_seconds / 3)):
            try:
                with self.database.sessions.begin() as session:
                    job = session.scalar(select(Job).where(Job.run_id == run_id))
                    if job is None or job.owner != self.owner:
                        return
                    job.lease_until = time.time() + self.settings.lease_seconds
                    job.heartbeat_at = utcnow()
            except Exception:
                logger.warning(json.dumps({"event": "heartbeat_failed", "run_id": run_id}))

    def run_once(self) -> bool:
        claimed = self.claim()
        if not claimed:
            return False
        run_id, resume_payload = claimed
        finished = threading.Event()
        heartbeat = threading.Thread(target=self.heartbeat, args=(run_id, finished), daemon=True)
        heartbeat.start()
        services = self.services_factory(self.settings, self.database, run_id, self.owner)
        graph: Any = None
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 1000}
        try:
            with checkpoints(self.settings.checkpoint_path) as saver:
                graph = create_workflow(services, saver)
                snapshot = graph.get_state(config)
                with self.database.sessions() as session:
                    run = session.get(Run, run_id)
                    assert run is not None
                    project = session.get(Project, run.project_id)
                    assert project is not None
                    initial = initial_state(
                        project.id,
                        run.id,
                        project.question,
                        domain=project.domain,
                        objectives=project.objectives,
                        constraints=run.config.get("constraints", {}),
                        provider=run.provider,
                        model=run.model,
                        config={
                            **run.config,
                            "supported_phases": list(services.adapter.supported_phases),
                        },
                        budget=run.config["budgets"],
                    )
                # Automatic graph tracing would serialize research state. Only
                # explicit redacted spans in services are sent to LangSmith.
                from langsmith import tracing_context

                with tracing_context(enabled=False):
                    command: Any = initial if not snapshot.values else None
                    if (
                        snapshot.values
                        and resume_payload is not None
                        and any(task.interrupts for task in snapshot.tasks)
                    ):
                        command = Command(resume=resume_payload)
                    graph.invoke(command, config)
                snapshot = graph.get_state(config)
                state = dict(snapshot.values)
                interruptions = [
                    interrupt.value for task in snapshot.tasks for interrupt in task.interrupts
                ]
                approval = interruptions[0] if interruptions else None
                status = state.get("status", "running")
                if interruptions:
                    status = (
                        "paused"
                        if approval and approval.get("kind") == "pause"
                        else "awaiting_approval"
                    )
                elif not snapshot.next and status not in TERMINAL:
                    status = "completed"
                with self.database.sessions.begin() as session:
                    run = session.get(Run, run_id)
                    job = session.scalar(select(Job).where(Job.run_id == run_id))
                    assert run is not None and job is not None
                    if job.owner != self.owner:
                        raise LostLease("Run ownership changed before checkpoint publication")
                    if run.control == "cancel":
                        status = "cancelled"
                    run.state, run.status, run.approval = state, status, approval
                    run.current_stage = (
                        (approval.get("stage") or approval.get("gate"))
                        if approval
                        else state.get("stage", run.current_stage)
                    )
                    run.updated_at = utcnow()
                    persist_research_items(session, run_id, state)
                    refresh_usage(session, run)
                    run.usage = {
                        **run.usage,
                        "runtime_seconds": run.usage.get("runtime_seconds", 0)
                        + time.monotonic()
                        - services.active_started,
                    }
                    job.status = (
                        "done"
                        if status in TERMINAL
                        else ("waiting_v2" if run.profile != "demo" else "waiting")
                    )
                    job.resume_payload, job.owner, job.lease_until = None, None, 0
                    record_event(
                        session,
                        run_id,
                        run.current_stage or "completion",
                        "status",
                        f"Research run {status.replace('_', ' ')}",
                        {"status": status, "approval": approval},
                    )
        except Exception as error:
            # Saver is reopened because the graph's context is now closed.
            state = {}
            with contextlib.suppress(Exception):
                with checkpoints(self.settings.checkpoint_path) as saver:
                    state = dict(create_workflow(services, saver).get_state(config).values)
            code = getattr(error, "code", "")
            status = (
                "paused"
                if code
                in {
                    "budget_exhausted",
                    "rate_limit",
                    "provider_unavailable",
                    "capability_unavailable",
                    "docker_unavailable",
                    "authentication_error",
                    "model_unavailable",
                    "context_budget_exceeded",
                    "literature_unavailable",
                    "execution_interrupted",
                }
                else "failed"
            )
            with self.database.sessions.begin() as session:
                run = session.get(Run, run_id)
                job = session.scalar(select(Job).where(Job.run_id == run_id))
                assert run is not None and job is not None
                if job.owner == self.owner:
                    if run.control == "cancel" or code in {"execution_cancelled", "cancelled"}:
                        status = "cancelled"
                    run.status, run.error, run.updated_at = status, safe_error(error), utcnow()
                    if state:
                        run.state = state
                    run.usage = {
                        **run.usage,
                        "runtime_seconds": run.usage.get("runtime_seconds", 0)
                        + time.monotonic()
                        - services.active_started,
                    }
                    job.status, job.owner, job.lease_until = (
                        ("waiting_v2" if run.profile != "demo" else "waiting"),
                        None,
                        0,
                    )
                    job.resume_payload = None
                    record_event(
                        session,
                        run_id,
                        run.current_stage or "intake",
                        "error",
                        run.error,
                        {"code": code or "internal_error", "status": status},
                    )
            logger.error(
                json.dumps(
                    {
                        "event": "run_error",
                        "run_id": run_id,
                        "type": type(error).__name__,
                        "code": code,
                    }
                )
            )
        finally:
            finished.set()
            heartbeat.join(timeout=2)
            services.close()
        return True

    def serve(self) -> None:
        while not self.stop.is_set():
            try:
                if not self.run_once():
                    self.stop.wait(0.5)
            except Exception as error:
                logger.error(
                    json.dumps({"event": "worker_poll_error", "type": type(error).__name__})
                )
                self.stop.wait(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Transport INFO logs include full query URLs, which may contain credentials.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    settings = Settings.from_env()
    worker = Worker(settings)
    worker.database.migrate()
    signal.signal(signal.SIGINT, lambda *_: worker.stop.set())
    signal.signal(signal.SIGTERM, lambda *_: worker.stop.set())
    if args.once:
        worker.run_once()
    else:
        worker.serve()


if __name__ == "__main__":
    main()
