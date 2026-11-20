"""Opt-in browser fixture server. Fake provider only; real local Docker execution.

Run from the repository root; never point this at a research database.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import threading
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import uvicorn
from apps.research_platform.backend.app import create_app
from src.research_platform.config import Settings
from src.research_platform.database import Database
from src.research_platform.worker import Worker
from test_dynamic_execution import FixtureExecutor, prepared
from src.research_platform.services import ResearchServices
from test_native_application import offline_factory, offline_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument(
        "--offline-boundary",
        action="store_true",
        help="Stub external program boundary; no Docker/program execution",
    )
    args = parser.parse_args()
    if args.offline_boundary:
        ResearchServices.dynamic_executor = lambda self: FixtureExecutor(
            fixture_root=self.settings.artifact_root.parent / "private-evaluations"
        )
    root = Path(args.state).resolve()
    root.mkdir(parents=True, exist_ok=False)
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{root / 'app.db'}",
        checkpoint_path=root / "checkpoints.db",
        artifact_root=root / "artifacts",
        cors_origins=("http://127.0.0.1:5182",),
    )
    db = Database(settings.database_url)
    db.migrate()
    contract = prepared("regression_v1")
    worker = Worker(
        settings,
        db,
        services_factory=offline_factory(db, contract, [], [], offline_values(contract)),
    )
    thread = threading.Thread(target=worker.serve, daemon=True)
    thread.start()
    try:
        uvicorn.run(
            create_app(settings, database=db), host="127.0.0.1", port=args.port, access_log=False
        )
    finally:
        worker.stop.set()
        thread.join(timeout=10)


if __name__ == "__main__":
    main()
