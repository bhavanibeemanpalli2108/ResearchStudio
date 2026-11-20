"""Run only a reviewed CPU program inside a constrained Docker container."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class ExecutionError(RuntimeError):
    code = "execution_failed"


class CapabilityError(ExecutionError):
    code = "capability_unavailable"


class ExecutionCancelled(ExecutionError):
    code = "cancelled"


class ExecutionTimeout(ExecutionError):
    code = "execution_timeout"


class OutputLimitError(ExecutionError):
    code = "output_limit_exceeded"


# This reviewed program is fixed application code. Prompts, generated code and
# uploaded files are never interpolated into it or executed on the host.
CURATED_CPU_PROGRAM = """import json, math, signal, time
signal.alarm(20)
started = time.perf_counter()
def packing(columns, rows):
    radius = 1 / (2 * max(columns, rows))
    centers = [((x + .5) / columns, (y + .5) / rows) for y in range(rows) for x in range(columns)][:26]
    valid = all(radius <= x <= 1-radius and radius <= y <= 1-radius for x,y in centers)
    valid = valid and all(math.hypot(x-a,y-b) + 1e-12 >= 2*radius for i,(x,y) in enumerate(centers) for a,b in centers[i+1:])
    return {"columns":columns,"rows":rows,"circles":len(centers),"sum_radii":len(centers)*radius,"radius":radius,"valid":valid}
baseline, candidate = packing(7,4), packing(6,5)
print(json.dumps({"baseline":baseline,"candidate":candidate,"improvement":candidate["sum_radii"]-baseline["sum_radii"],"wall_seconds":time.perf_counter()-started,"program":"curated_square_grid_packing_v1"}))
"""


def sanitized_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    source = environ if environ is not None else os.environ
    # Keep the Docker client usable, but do not forward provider tokens, tracing
    # credentials, PYTHONPATH, or arbitrary user shell configuration.
    allowed = {
        "PATH",
        "SystemRoot",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
    }
    return {key: value for key, value in source.items() if key in allowed}


class DockerExecutor:
    def __init__(
        self,
        *,
        image: str = "python:3.12-slim",
        timeout_seconds: float = 30,
        output_limit_bytes: int = 65536,
        popen: Any = subprocess.Popen,
        runner: Any = subprocess.run,
    ):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./:@_-]{0,255}", image):
            raise ValueError("Invalid Docker image reference")
        self.image = image
        self.timeout_seconds = min(max(timeout_seconds, 1), 300)
        self.output_limit_bytes = min(max(output_limit_bytes, 1024), 1024 * 1024)
        self.popen, self.runner = popen, runner

    def capabilities(self) -> dict[str, Any]:
        docker = shutil.which("docker")
        result: dict[str, Any] = {
            "docker_cli": bool(docker),
            "docker_daemon": False,
            "image": self.image,
            "image_available": False,
            "ready": False,
        }
        if not docker:
            result["reason"] = "Docker is not installed or is absent from PATH."
            return result
        try:
            probe = self.runner(
                [docker, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=8,
                env=sanitized_environment(),
            )
            result["docker_daemon"] = probe.returncode == 0
            if result["docker_daemon"]:
                image = self.runner(
                    [docker, "image", "inspect", self.image, "--format", "{{.Id}}"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    env=sanitized_environment(),
                )
                result["image_available"] = image.returncode == 0
        except (OSError, subprocess.SubprocessError):
            result["reason"] = "Docker capability probe failed or timed out."
        result["ready"] = result["docker_daemon"] and result["image_available"]
        if not result["ready"] and "reason" not in result:
            result["reason"] = (
                "Start Docker and pre-pull the configured CPU image; execution never downloads images automatically."
            )
        return result

    def command(self, name: str) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--cpus=1",
            "--memory=256m",
            "--memory-swap=256m",
            "--ulimit",
            "nofile=128:128",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--log-driver=none",
            "--init",
            self.image,
            "python",
            "-I",
            "-B",
            "-c",
            CURATED_CPU_PROGRAM,
        ]

    def _remove(self, name: str) -> None:
        try:
            self.runner(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=8,
                env=sanitized_environment(),
            )
        except (OSError, subprocess.SubprocessError):
            pass

    def execute(self, *, cancel_check: Callable[[], bool] | None = None) -> dict[str, Any]:
        capabilities = self.capabilities()
        if not capabilities["ready"]:
            raise CapabilityError(
                capabilities.get("reason", "Docker CPU execution is unavailable.")
            )
        if cancel_check and cancel_check():
            raise ExecutionCancelled("Execution was cancelled before launch.")
        name = "research-cpu-" + uuid.uuid4().hex[:20]
        output = bytearray()
        output_exceeded = threading.Event()
        try:
            process = self.popen(
                self.command(name),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=sanitized_environment(),
            )
        except OSError:
            raise ExecutionError("The Docker CPU process could not be started.") from None

        def drain() -> None:
            assert process.stdout is not None
            while True:
                block = process.stdout.read(4096)
                if not block:
                    break
                room = self.output_limit_bytes - len(output)
                if room > 0:
                    output.extend(block[:room])
                if len(block) > room:
                    output_exceeded.set()

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        deadline = time.monotonic() + self.timeout_seconds
        failure: ExecutionError | None = None
        try:
            while process.poll() is None:
                if cancel_check and cancel_check():
                    failure = ExecutionCancelled("Execution was cancelled.")
                    break
                if output_exceeded.is_set():
                    failure = OutputLimitError("Execution exceeded its output limit.")
                    break
                if time.monotonic() >= deadline:
                    failure = ExecutionTimeout("Execution exceeded its wall-clock deadline.")
                    break
                time.sleep(0.05)
            if failure:
                self._remove(name)
                process.kill()
                process.wait(timeout=5)
                raise failure
            reader.join(timeout=2)
            if output_exceeded.is_set():
                raise OutputLimitError("Execution exceeded its output limit.")
            if process.returncode:
                raise ExecutionError(
                    "The isolated CPU experiment failed; inspect Docker readiness."
                )
            try:
                metrics = json.loads(output.decode("utf-8").strip())
                if (
                    not isinstance(metrics, dict)
                    or metrics.get("program") != "curated_square_grid_packing_v1"
                ):
                    raise ValueError("Unexpected experiment output")
            except (ValueError, UnicodeError):
                raise ExecutionError("The isolated experiment returned invalid output.") from None
            return metrics
        finally:
            self._remove(name)
            if process.poll() is None:
                process.kill()
            reader.join(timeout=1)
            if process.stdout:
                process.stdout.close()


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(path)
