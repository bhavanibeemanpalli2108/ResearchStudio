"""Start local API, durable worker and optionally Vite in one terminal."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time

from .config import REPO_ROOT, Settings
from .database import Database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-frontend", action="store_true", help="Serve an existing frontend build from the API"
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.frontend_port <= 65535:
        parser.error("Ports must be between 1 and 65535")
    ports = [args.port] if args.no_frontend else [args.port, args.frontend_port]
    if len(set(ports)) != len(ports):
        parser.error("API and frontend ports must differ")
    for port in ports:
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError:
            parser.error(f"Local port {port} is occupied; choose another port")
    if (
        args.no_frontend
        and not (REPO_ROOT / "apps/research_platform/frontend/dist/index.html").is_file()
    ):
        parser.error(
            "Built frontend is missing; run npm build in apps/research_platform/frontend first"
        )
    settings = Settings.from_env()
    settings.prepare()
    database = Database(settings.database_url)
    database.migrate()
    database.engine.dispose()
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.research_platform.backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
            "--no-access-log",
        ],
        [sys.executable, "-m", "src.research_platform.worker"],
    ]
    directories = [REPO_ROOT, REPO_ROOT]
    if not args.no_frontend:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise SystemExit(
                "Node.js/npm is required for the frontend. Install it or use --no-frontend after building."
            )
        commands.append(
            [
                npm,
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.frontend_port),
                "--strictPort",
            ]
        )
        directories.append(REPO_ROOT / "apps/research_platform/frontend")
    processes: list[subprocess.Popen] = []
    try:
        for command, cwd in zip(commands, directories):
            environment = {**os.environ, "RESEARCH_API_URL": f"http://127.0.0.1:{args.port}"}
            origins = set(settings.cors_origins) | {
                f"http://localhost:{args.frontend_port}",
                f"http://127.0.0.1:{args.frontend_port}",
            }
            environment["CORS_ORIGINS"] = ",".join(sorted(origins))
            processes.append(
                subprocess.Popen(
                    command, cwd=cwd, env=environment, start_new_session=os.name != "nt"
                )
            )
        print(
            f"Research workspace: http://127.0.0.1:{args.port if args.no_frontend else args.frontend_port}",
            flush=True,
        )
        print(f"API documentation: http://127.0.0.1:{args.port}/docs", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise SystemExit(
            next((process.returncode for process in processes if process.returncode is not None), 1)
        )
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                # Children include only trusted dev services, never generated code.
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
