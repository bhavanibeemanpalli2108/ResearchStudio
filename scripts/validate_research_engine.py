"""Run genuine studies through the public API and real durable worker, in isolation.

No responses or programs are supplied by this runner. Approvals require a separate
operator invocation after inspecting each persisted proposal. Existing data and
the configured daily/per-run budget defaults are not changed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from apps.research_platform.backend.app import create_app
from src.research_platform.config import Settings
from src.research_platform.database import Database
from src.research_platform.database import Run
from src.research_platform.services import record_event
from src.research_platform.schemas import Budgets
from src.research_platform.worker import Worker

QUESTIONS = {
    "scheduling": "Does shortest-processing-time scheduling reduce total completion time compared with FIFO on the same fixed job set?",
    "regression": "Does ordinary least squares improve held-out RMSE compared with a training-mean predictor on a reproducible small linear regression dataset?",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--study", choices=list(QUESTIONS), required=True)
    parser.add_argument("--provider", choices=["gemini", "groq", "ollama"])
    parser.add_argument("--model")
    parser.add_argument("--advance", action="store_true")
    parser.add_argument(
        "--select-model",
        action="store_true",
        help="Explicitly change provider/model on a paused run, retaining all usage",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--revise",
        help="Return a concrete proposal for model revision with this operator constraint; never author code or measurements",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable the configured redacted LangSmith exporter for this validation process",
    )
    parser.add_argument(
        "--approve", help="research_plan, or the actual 64-character experiment approval digest"
    )
    args = parser.parse_args()
    target = args.root.resolve()
    target.mkdir(parents=True, exist_ok=True)
    original = Settings.from_env()
    if args.trace:
        os.environ["LANGSMITH_TRACING"] = "true"
    settings = replace(
        original,
        database_url=f"sqlite:///{(target / 'metadata.db').as_posix()}",
        artifact_root=target / "artifacts",
        checkpoint_path=target / "checkpoints.db",
    )
    database = Database(settings.database_url)
    marker = target / f"{args.study}.json"
    with TestClient(create_app(settings, database=database)) as client:
        if marker.exists():
            identifier = json.loads(marker.read_text())["run_id"]
        else:
            if not args.provider or not args.model:
                parser.error("New studies require an explicitly selected discovered provider/model")
            project = client.post(
                "/api/projects",
                json={
                    "title": f"Live acceptance: {args.study}",
                    "question": QUESTIONS[args.study],
                    "domain": "Algorithmic optimization"
                    if args.study == "scheduling"
                    else "Machine learning",
                },
            ).json()
            # Existing defaults are used as approved; this script never inflates
            # budgets to obtain a passing result.
            budgets = Budgets().model_dump()
            budgets["max_llm_calls"] = min(budgets["max_llm_calls"], original.max_llm_calls)
            budgets["max_runtime_seconds"] = min(
                budgets["max_runtime_seconds"], original.max_runtime
            )
            response = client.post(
                f"/api/projects/{project['id']}/runs",
                json={
                    "execution_protocol": 2,
                    "engine": "native",
                    "profile": "free_research",
                    "provider": args.provider,
                    "model": args.model,
                    "budgets": budgets,
                    "require_approval": True,
                    "constraints": {"validation_study": args.study, "packages": "stdlib only"},
                },
            )
            if response.status_code != 201:
                raise RuntimeError(response.text)
            identifier = response.json()["id"]
            marker.write_text(
                json.dumps(
                    {
                        "run_id": identifier,
                        "question": QUESTIONS[args.study],
                        "provider": args.provider,
                        "model": args.model,
                        "budgets": budgets,
                    },
                    indent=2,
                )
            )
        current = client.get(f"/api/runs/{identifier}").json()
        if args.select_model:
            if current["status"] != "paused" or not args.provider or not args.model:
                raise ValueError(
                    "Explicit model selection requires a paused run and named provider/model"
                )
            with database.sessions.begin() as session:
                row = session.get(Run, identifier)
                row.provider, row.model = args.provider, args.model
                row.config = {**row.config, "provider": args.provider, "model": args.model}
                record_event(
                    session,
                    identifier,
                    row.current_stage or "feasibility",
                    "operator_model_selection",
                    "Validation operator explicitly selected another discovered model; usage retained",
                    {"provider": args.provider, "model": args.model},
                )
        if args.resume:
            response = client.post(f"/api/runs/{identifier}/resume")
            if response.status_code != 200:
                raise RuntimeError(response.text)
        if args.revise:
            if (current.get("approval") or {}).get("gate") != "approval":
                raise ValueError("A concrete proposal is required before requesting revision")
            response = client.post(
                f"/api/runs/{identifier}/approve",
                json={
                    "approved": False,
                    "action": "retry",
                    "feedback": args.revise,
                    "constraints": {"operator_revision": args.revise},
                },
            )
            if response.status_code != 200:
                raise RuntimeError(response.text)
        if args.approve:
            gate = (current.get("approval") or {}).get("gate")
            if gate == "research_plan" and args.approve != "research_plan":
                raise ValueError("Review and approve the research_plan gate first")
            expected = current.get("state", {}).get("experiment_config", {}).get("approval_digest")
            if gate == "approval" and args.approve != expected:
                raise ValueError("Explicit approval must match the displayed experiment digest")
            response = client.post(
                f"/api/runs/{identifier}/approve",
                json={
                    "approved": True,
                    "action": "continue",
                    **({"approval_digest": expected} if gate == "approval" else {}),
                },
            )
            if response.status_code != 200:
                raise RuntimeError(response.text)
        if args.advance or args.approve or args.resume or args.revise:
            Worker(settings, database).run_once()
        result = client.get(f"/api/runs/{identifier}").json()
        evidence = target / args.study
        evidence.mkdir(exist_ok=True)
        for part in ["events", "experiments", "traces", "artifacts", "graph"]:
            response = client.get(f"/api/runs/{identifier}/{part}")
            (evidence / f"{part}.json").write_text(
                json.dumps(response.json(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
        (evidence / "run.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    k: result.get(k)
                    for k in [
                        "id",
                        "status",
                        "current_stage",
                        "provider",
                        "model",
                        "error",
                        "usage",
                        "approval",
                    ]
                },
                indent=2,
                ensure_ascii=True,
            )
        )


if __name__ == "__main__":
    main()
