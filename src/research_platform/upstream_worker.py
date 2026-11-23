"""Original Sakana pipeline service for a dedicated, administrator-owned worker.

Run natively on a disposable remote Linux VM with its own Docker daemon and
finite cgroup limits. This is deliberately disabled without that configuration.
Never deploy it by mounting a workstation's Docker socket into a container.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import Response

from .upstream_execution import UpstreamRunRequest, upstream_command

REPO_ROOT = Path(__file__).resolve().parents[2]
ISOLATION_ACK = "dedicated-disposable-worker-v1"
ARTIFACTS = {
    "paper.pdf": "paper/paper.pdf",
    "paper.tex": "paper/paper.tex",
    "final_manifest.json": "final_evaluation/final_manifest.json",
    "best_program_manifest.json": "investigation/best_program_manifest.json",
    "pipeline_events.jsonl": "pipeline_events.jsonl",
}
TERMINAL = {
    "completed",
    "completed_degraded",
    "failed",
    "cancelled",
    "interrupted",
    "cleanup_unverified",
}


@dataclass(frozen=True)
class WorkerSettings:
    enabled: bool = False
    campaigns_enabled: bool = False
    gateway_origin: str = ""
    root: Path | None = None
    token: str = ""
    isolation_ack: str = ""
    env_file: Path | None = None
    docker_host: str = "unix:///run/agsci-docker.sock"
    docker_data_root: str = "/var/lib/agsci-docker"
    daemon_config: Path = Path("/etc/agsci-worker/daemon.json")
    cgroup: Path = Path("/sys/fs/cgroup/agsci.slice/agsci-research.slice")
    image: str = "agentic-scientist/agent-cli:latest"
    python: str = sys.executable
    repo: Path = REPO_ROOT

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> WorkerSettings:
        env = environ if environ is not None else os.environ
        return cls(
            enabled=env.get("RESEARCH_UPSTREAM_WORKER_ENABLED") == "1",
            campaigns_enabled=env.get("RESEARCH_UPSTREAM_CAMPAIGNS_ENABLED") == "1",
            gateway_origin=env.get("RESEARCH_UPSTREAM_GATEWAY_ORIGIN", ""),
            root=Path(env["RESEARCH_UPSTREAM_WORKER_ROOT"])
            if env.get("RESEARCH_UPSTREAM_WORKER_ROOT")
            else None,
            token=env.get("RESEARCH_UPSTREAM_WORKER_TOKEN", ""),
            isolation_ack=env.get("RESEARCH_UPSTREAM_ISOLATION_ACK", ""),
            env_file=Path(env["RESEARCH_UPSTREAM_AGENT_ENV_FILE"])
            if env.get("RESEARCH_UPSTREAM_AGENT_ENV_FILE")
            else None,
            docker_host=env.get("RESEARCH_UPSTREAM_DOCKER_HOST", "unix:///run/agsci-docker.sock"),
            docker_data_root=env.get("RESEARCH_UPSTREAM_DOCKER_DATA_ROOT", "/var/lib/agsci-docker"),
            daemon_config=Path(
                env.get("RESEARCH_UPSTREAM_DAEMON_CONFIG", "/etc/agsci-worker/daemon.json")
            ),
            cgroup=Path(
                env.get(
                    "RESEARCH_UPSTREAM_CGROUP", "/sys/fs/cgroup/agsci.slice/agsci-research.slice"
                )
            ),
            image=env.get("RESEARCH_UPSTREAM_AGENT_IMAGE", "agentic-scientist/agent-cli:latest"),
        )


def _private_owned(path: Path, *, directory: bool = False) -> bool:
    try:
        info = path.lstat()
        return (
            not path.is_symlink()
            and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and info.st_uid in {0, os.getuid()}
            and not info.st_mode & 0o077
        )
    except OSError:
        return False


def _trusted_config(path: Path) -> bool:
    """Nonsecret daemon policy must be administrator-owned and not writable by peers."""
    try:
        info = path.lstat()
        return (
            not path.is_symlink()
            and stat.S_ISREG(info.st_mode)
            and info.st_uid == 0
            and not info.st_mode & 0o022
        )
    except OSError:
        return False


def _cgroup_path(settings: WorkerSettings) -> str:
    return "/" + settings.cgroup.relative_to("/sys/fs/cgroup").as_posix()


def _native_controller() -> bool:
    return (
        not Path("/.dockerenv").exists()
        and not Path("/run/.containerenv").exists()
        and not os.environ.get("container")
    )


def _controller_membership() -> str:
    return Path("/proc/self/cgroup").read_text()


def _in_cgroup(settings: WorkerSettings, membership: str) -> bool:
    try:
        prefix = "0::" + _cgroup_path(settings)
        return any(
            line == prefix or line.startswith(prefix + "/") for line in membership.splitlines()
        )
    except ValueError:
        return False


@contextmanager
def controller_lock(settings: WorkerSettings):
    """Fence serving and offline recovery across controller processes."""
    import fcntl

    if settings.root is None or not _private_owned(settings.root, directory=True):
        raise RuntimeError("Private worker root is unavailable")
    descriptor = os.open(
        settings.root / "controller.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def _read_bounded(path: Path, root: Path, maximum: int = 2 * 1024 * 1024) -> bytes:
    """Read only regular files without following any run-controlled symlinks."""
    relative = path.relative_to(root)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            next_descriptor = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = next_descriptor
        file_descriptor = os.open(
            relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
        )
        with os.fdopen(file_descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
                raise ValueError("Artifact is not a bounded regular file")
            content = stream.read(maximum + 1)
            if len(content) > maximum:
                raise ValueError("Artifact exceeds size limit")
            return content
    finally:
        os.close(descriptor)


def _write_json(path: Path, value: Any) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        os.chmod(temporary, 0o600)
        json.dump(value, stream, ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class UpstreamWorker:
    def __init__(
        self,
        settings: WorkerSettings,
        *,
        runner: Any = subprocess.run,
        popen: Any = subprocess.Popen,
    ) -> None:
        self.settings, self.runner, self.popen = settings, runner, popen
        self.lock = threading.RLock()
        self.processes: dict[str, Any] = {}
        self.cancellations: dict[str, threading.Event] = {}
        self.active: str | None = None
        # A fresh service process cannot prove that a predecessor's subprocess
        # died. Keep the entire exclusive worker fenced until operator recovery.
        if (
            settings.enabled
            and settings.root is not None
            and _private_owned(settings.root, directory=True)
            and os.access(settings.root, os.R_OK | os.W_OK | os.X_OK)
        ):
            for child in settings.root.iterdir():
                if child.is_dir() and not child.is_symlink():
                    try:
                        identifier = str(UUID(child.name))
                        record = json.loads(_read_bounded(child / "job.json", child))
                        if not isinstance(record, dict):
                            raise ValueError("Invalid job journal")
                        if record.get("status") in {"running", "cleanup_unverified"}:
                            record.update(
                                status="cleanup_unverified",
                                cleanup_verified=False,
                                error="Worker restarted; operator must verify abandoned process/container shutdown before a new run.",
                            )
                            _write_json(child / "job.json", record)
                            self.active = identifier
                    except (OSError, ValueError):
                        self.active = "operator_recovery_required"

    def environment(self, job: Path | None = None) -> dict[str, str]:
        # No workstation provider credentials, agent profiles, mounts, proxy
        # settings or daemon selectors leak into the original controller.
        env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
        env.update(
            {
                "DOCKER_HOST": self.settings.docker_host,
                "AGENT_CONTAINER_MOUNT_DOCKER_SOCK": "0",
                "AGENT_CONTAINER_RESTRICT_ENV": "1",
                "AGENT_CONTAINER_DISABLE_HOST_GATEWAY": "1",
                "OMP_NUM_THREADS": "2",
                "OPENBLAS_NUM_THREADS": "2",
                "MKL_NUM_THREADS": "2",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        if job is not None:
            env.update(
                {
                    "HOME": str(job / "auth"),
                    "AGENTIC_TEMP_DIR": str(job / "tmp"),
                    "AGENTIC_CONTAINER_TEMP_ROOT": str(job / "tmp"),
                    "TMPDIR": str(job / "tmp"),
                }
            )
        return env

    def _run(self, command: list[str], *, timeout: float = 10) -> Any:
        return self.runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=self.environment(),
            cwd=self.settings.repo,
        )

    def _daemon_identity(self, details: dict[str, Any]) -> bool:
        if not isinstance(details, dict):
            return False
        desktop = (
            "desktop" in str(details.get("OperatingSystem", "")).lower()
            or "docker-desktop" in str(details.get("Name", "")).lower()
            or any(
                "com.docker.desktop" in str(label).lower()
                for label in (details.get("Labels") or [])
            )
        )
        return (
            not desktop
            and details.get("DockerRootDir") == self.settings.docker_data_root
            and details.get("CgroupDriver") == "systemd"
            and str(details.get("CgroupVersion")) == "2"
        )

    def capabilities(self, *, probe: bool = True) -> dict[str, Any]:
        # Serialize temporary probes with submission and other capability calls.
        with self.lock:
            return self._capabilities(probe=probe)

    def _capabilities(self, *, probe: bool) -> dict[str, Any]:
        checks: dict[str, bool] = {}
        settings = self.settings
        checks["enabled"] = settings.enabled
        checks["linux"] = sys.platform == "linux"
        checks["non_wsl_controller"] = not any(
            marker in platform.release().lower() for marker in ("microsoft", "wsl")
        )
        checks["native_controller"] = _native_controller()
        checks["dedicated_worker_operator_attested"] = settings.isolation_ack == ISOLATION_ACK
        checks["recovery_clear"] = self.active is None
        checks["authentication"] = (
            len(settings.token) >= 32 and "REPLACE" not in settings.token.upper()
        )
        checks["private_root"] = (
            settings.root is not None
            and settings.root.is_absolute()
            and _private_owned(settings.root, directory=True)
            and os.access(settings.root, os.W_OK | os.X_OK)
        )
        checks["private_credentials"] = (
            settings.env_file is not None
            and settings.env_file.is_absolute()
            and _private_owned(settings.env_file)
        )
        checks["gemini_credentials_configured"] = False
        if checks["private_credentials"]:
            try:
                credentials = settings.env_file.read_text()  # type: ignore[union-attr]
                checks["gemini_credentials_configured"] = any(
                    line.partition("=")[0].strip() in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}
                    and bool(line.partition("=")[2].strip().strip("\"'"))
                    for line in credentials.splitlines()
                )
            except (OSError, UnicodeError):
                pass
        checks["dedicated_docker_socket"] = settings.docker_host.startswith(
            "unix:///"
        ) and settings.docker_host not in {"unix:///var/run/docker.sock", "unix:///run/docker.sock"}
        checks["dedicated_docker_data_root"] = Path(
            settings.docker_data_root
        ).is_absolute() and Path(settings.docker_data_root).resolve() != Path("/var/lib/docker")
        checks["original_engine"] = (settings.repo / "src/pipeline/cli.py").is_file() and (
            settings.repo / "src/task_drafting/service.py"
        ).is_file()
        checks["finite_cgroup_limits"] = False
        checks["daemon_cgroup_policy"] = False
        checks["trusted_daemon_config"] = _trusted_config(settings.daemon_config)
        checks["controller_cgroup_enforced"] = False
        try:
            checks["controller_cgroup_enforced"] = _in_cgroup(settings, _controller_membership())
            cpu = (settings.cgroup / "cpu.max").read_text().split()
            memory = (settings.cgroup / "memory.max").read_text().strip()
            pids = (settings.cgroup / "pids.max").read_text().strip()
            checks["finite_cgroup_limits"] = (
                len(cpu) == 2
                and int(cpu[1]) > 0
                and 0 < int(cpu[0]) <= 4 * int(cpu[1])
                and 0 < int(memory) <= 16 * 1024**3
                and 0 < int(pids) <= 4096
            )
            daemon = (
                json.loads(settings.daemon_config.read_text())
                if checks["trusted_daemon_config"]
                else {}
            )
            if not isinstance(daemon, dict):
                daemon = {}
            checks["daemon_cgroup_policy"] = (
                daemon.get("cgroup-parent") == settings.cgroup.name
                and daemon.get("data-root") == settings.docker_data_root
                and daemon.get("hosts") == [settings.docker_host]
                and "native.cgroupdriver=systemd" in daemon.get("exec-opts", [])
                and daemon.get("live-restore") is False
            )
        except (OSError, ValueError, IndexError, TypeError):
            pass
        checks["docker_daemon"] = checks["agent_image"] = checks[
            "gemini_headless_in_image"
        ] = checks["daemon_cgroup_enforced"] = checks["python_prerequisites"] = False
        checks["capability_probe_cleanup"] = False
        checks["exclusive_daemon_idle"] = False
        image_id = None
        # Do not probe arbitrary Docker daemons until the operator boundary is configured.
        if probe and all(
            value
            for key, value in checks.items()
            if key
            not in {
                "docker_daemon",
                "agent_image",
                "gemini_headless_in_image",
                "daemon_cgroup_enforced",
                "python_prerequisites",
                "capability_probe_cleanup",
                "exclusive_daemon_idle",
                "authentication",
                "private_credentials",
                "gemini_credentials_configured",
            }
        ):
            try:
                python_probe = self._run(
                    [
                        settings.python,
                        "-c",
                        "import hydra, numpy, scipy; from src.pipeline.cli import load_pipeline_config; load_pipeline_config([])",
                    ],
                    timeout=20,
                )
                checks["python_prerequisites"] = python_probe.returncode == 0
                info = self._run(["docker", "info", "--format", "{{json .}}"])
                details = json.loads(info.stdout) if info.returncode == 0 else {}
                checks["docker_daemon"] = self._daemon_identity(details)
                if not checks["docker_daemon"]:
                    raise ValueError("Dedicated daemon identity rejected")
                idle = self._run(["docker", "ps", "-aq"])
                checks["exclusive_daemon_idle"] = idle.returncode == 0 and not idle.stdout.strip()
                if not checks["exclusive_daemon_idle"]:
                    raise ValueError(
                        "Dedicated daemon is not empty; no capability container started"
                    )
                image = self._run(
                    ["docker", "image", "inspect", settings.image, "--format", "{{.Id}}"]
                )
                image_id = image.stdout.strip() if image.returncode == 0 else None
                checks["agent_image"] = bool(image_id and image_id.startswith("sha256:"))
                if checks["docker_daemon"] and checks["agent_image"] and isinstance(image_id, str):
                    name = "agsci-capability-" + os.urandom(8).hex()
                    try:
                        result = self._run(
                            [
                                "docker",
                                "run",
                                "--rm",
                                "--name",
                                name,
                                "--pull=never",
                                "--network=none",
                                "--read-only",
                                "--cap-drop=ALL",
                                "--security-opt=no-new-privileges",
                                "--cgroupns=host",
                                "--pids-limit=32",
                                "--memory=256m",
                                "--cpus=1",
                                "--user=65534:65534",
                                "--tmpfs",
                                "/tmp:rw,noexec,nosuid,size=16m",
                                image_id,
                                "bash",
                                "-c",
                                "cat /proc/self/cgroup && command -v gemini >/dev/null && command -v headless >/dev/null && command -v pdflatex >/dev/null && command -v bibtex >/dev/null",
                            ],
                            timeout=30,
                        )
                        checks["gemini_headless_in_image"] = result.returncode == 0
                        checks["daemon_cgroup_enforced"] = _in_cgroup(settings, result.stdout)
                    finally:
                        # A timed-out docker client does not establish container exit.
                        self._run(["docker", "rm", "-f", name])
                        left = self._run(
                            ["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"]
                        )
                        checks["capability_probe_cleanup"] = (
                            left.returncode == 0 and not left.stdout.strip()
                        )
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        if settings.gateway_origin:
            from .gateway_client import validate_gateway_client

            try:
                validate_gateway_client(
                    settings.gateway_origin + "/runs/" + "0" * 32, "gw_" + "a" * 43
                )
                checks["gemini_credentials_configured"] = True
            except ValueError:
                checks["gemini_credentials_configured"] = False
        infrastructure = all(
            value for key, value in checks.items() if key != "gemini_credentials_configured"
        )
        return {
            "ready": all(checks.values()) and settings.campaigns_enabled,
            "infrastructure_ready": infrastructure,
            "campaigns_enabled": settings.campaigns_enabled,
            "source": "upstream_agsci",
            "checks": checks,
            "image_id": image_id,
            "supported_agents": ["gemini"],
            "gpu_support": False,
            "phases": [
                "task_drafting",
                "investigation",
                "ablations",
                "final_evaluation",
                "posthoc",
                "paper",
            ],
            "nested_call_budget_enforced": False,
            "gateway_protocol": "run-scoped-v1",
            "gateway_credentials": bool(settings.gateway_origin),
            "budget_policy": "Original coding agents make nested calls. Operator-managed provider quotas and explicit approval are required; platform request caps do not apply.",
            "isolation": "Dedicated VM and daemon are operator attested; finite cgroup configuration and Docker prerequisites are checked. This does not certify a production security boundary.",
            "reason": None
            if all(checks.values()) and settings.campaigns_enabled
            else "Execution disabled or dedicated worker prerequisites incomplete; inspect checks. No original engine was launched.",
        }

    def recover(self, identifier: str) -> dict[str, Any]:
        """Offline only, under controller_lock; never kills or resumes anything."""
        record = self._record(identifier)
        checks = self.capabilities(probe=False)["checks"]
        required = (
            "enabled",
            "linux",
            "non_wsl_controller",
            "native_controller",
            "dedicated_worker_operator_attested",
            "private_root",
            "dedicated_docker_socket",
            "dedicated_docker_data_root",
            "finite_cgroup_limits",
            "trusted_daemon_config",
            "daemon_cgroup_policy",
        )
        if not all(checks[name] for name in required):
            raise RuntimeError("Dedicated recovery infrastructure is not verified")
        if record.get("status") != "cleanup_unverified":
            raise RuntimeError("Recovery requires an interrupted cleanup-unverified job")
        events = dict(
            line.split()
            for line in (self.settings.cgroup / "cgroup.events").read_text().splitlines()
        )
        if events.get("populated") != "0":
            raise RuntimeError("Research cgroup still contains processes; recovery refused")
        info = self._run(["docker", "info", "--format", "{{json .}}"])
        if info.returncode != 0 or not self._daemon_identity(json.loads(info.stdout)):
            raise RuntimeError("Dedicated recovery daemon is not verified")
        containers = self._run(["docker", "ps", "-aq"])
        if containers.returncode != 0 or containers.stdout.strip():
            raise RuntimeError("Dedicated daemon is not empty; no containers were removed")
        record.update(
            status="interrupted",
            cleanup_verified=True,
            recovered_at=time.time(),
            error="Operator verified empty cgroup and daemon offline; no automatic resume.",
        )
        _write_json(self._job(identifier) / "job.json", record)
        # Re-scan on the next service startup; other journals remain fenced.
        return self._public(record)

    def _root(self) -> Path:
        if (
            self.settings.root is None
            or not _private_owned(self.settings.root, directory=True)
            or not os.access(self.settings.root, os.R_OK | os.W_OK | os.X_OK)
        ):
            raise HTTPException(503, "Private worker root is unavailable")
        return self.settings.root

    def _job(self, identifier: str) -> Path:
        try:
            if str(UUID(identifier)) != identifier:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(400, "Invalid run identifier") from exc
        job = self._root() / identifier
        if job.is_symlink():
            raise HTTPException(409, "Unsafe job directory")
        return job

    def _record(self, identifier: str) -> dict[str, Any]:
        job = self._job(identifier)
        try:
            return json.loads(_read_bounded(job / "job.json", job))
        except (OSError, ValueError) as exc:
            raise HTTPException(404, "Run unavailable") from exc

    def status(self, identifier: str) -> dict[str, Any]:
        with self.lock:
            record = self._record(identifier)
            if (
                record["status"] == "running"
                and identifier not in self.processes
                and self.active != identifier
            ):
                # A restarted controller cannot resurrect its old process or
                # establish container cleanup. Never permit automatic reexecution.
                record.update(
                    status="cleanup_unverified",
                    error="Worker restarted; operator must verify abandoned process/container shutdown before a new run.",
                )
                _write_json(self._job(identifier) / "job.json", record)
                self.active = identifier
            return self._public(record)

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in record.items()
            if key not in {"request", "command", "request_digest"}
        }

    def _command(
        self,
        request: UpstreamRunRequest,
        job: Path,
        image: str,
        *,
        resume: bool = False,
        dry_run: bool = False,
        remaining_phases: list[str] | None = None,
    ) -> list[str]:
        return upstream_command(
            request,
            python=self.settings.python,
            task_dir=str(job / "brief"),
            run_dir=str(job / "run"),
            auth_root=str(job / "auth"),
            env_file=str(
                self._gateway_file(request.run_id)
                if request.nested_budget_policy == "gateway_scoped"
                else self.settings.env_file
            ),
            image=image,
            resume=resume,
            dry_run=dry_run,
            remaining_phases=remaining_phases,
        )

    def dry_run(self, request: UpstreamRunRequest) -> dict[str, Any]:
        request.checked_id()
        # Building an exact command is possible before provisioning, but it is
        # explicitly a preview and not fabricated upstream execution.
        job = self._job(request.run_id)
        return {
            "executed": False,
            "source": "upstream_agsci",
            "command": self._command(request, job, self.settings.image, dry_run=True),
            "capabilities": self.capabilities(),
        }

    def submit(self, request: UpstreamRunRequest, *, resume: bool = False) -> dict[str, Any]:
        if not self.settings.campaigns_enabled:
            raise HTTPException(
                409,
                "Original campaigns are disabled; nested model-call accounting remains unresolved",
            )
        try:
            request.checked_id()
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with self.lock:
            if request.nested_budget_policy == "gateway_scoped" and not _private_owned(
                self._gateway_file(request.run_id)
            ):
                raise HTTPException(409, "Run-scoped gateway credential is required")
            job = self._job(request.run_id)
            digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            if job.exists() and not resume:
                previous = self._record(request.run_id)
                if previous["request_digest"] != digest:
                    raise HTTPException(
                        409, "Run identifier already belongs to a different request"
                    )
                return self._public(previous)
            if self.active is not None and self.active != request.run_id:
                raise HTTPException(409, "Dedicated worker is busy")
            capabilities = self.capabilities()
            if not capabilities["ready"]:
                raise HTTPException(503, "Dedicated upstream worker prerequisites are incomplete")
            if job.exists():
                record = self._record(request.run_id)
                if record["request_digest"] != digest:
                    raise HTTPException(
                        409, "Run identifier already belongs to a different request"
                    )
                if not resume:
                    return self._public(record)
                if record["status"] not in {"failed", "cancelled", "interrupted"} or not record.get(
                    "cleanup_verified"
                ):
                    raise HTTPException(
                        409, "Run cannot resume until process and container cleanup are verified"
                    )
                if record["attempts"] >= 3:
                    raise HTTPException(409, "Worker resume attempt limit exhausted")
                if (
                    request.nested_budget_policy == "gateway_scoped"
                    and record.get("campaign_deadline", 0) <= time.time()
                ):
                    raise HTTPException(409, "Scoped execution window expired")
                self._resume_phases(request, job)
            else:
                if resume:
                    raise HTTPException(404, "Run unavailable")
                existing = self._run(["docker", "ps", "-q"])
                if existing.returncode != 0 or existing.stdout.strip():
                    raise HTTPException(
                        409, "Dedicated Docker daemon must have no running containers before a run"
                    )
                job.mkdir(mode=0o700)
                for name in ("brief", "auth", "tmp"):
                    (job / name).mkdir(mode=0o700)
                brief = (
                    "# Research brief\n\n"
                    + request.question
                    + "\n\nDomain: "
                    + request.domain
                    + "\n\n## Objectives\n\n"
                    + "\n".join("- " + item for item in request.objectives)
                    + "\n\n## Computational constraints\n\nCPU only. No GPUs are available. Use bounded, reproducible computational experiments with independent evaluation, baselines and measured evidence.\n\n"
                    + request.constraints
                    + "\n"
                )
                (job / "brief/task.md").write_text(brief, encoding="utf-8")
                record = {
                    "run_id": request.run_id,
                    "source": "upstream_agsci",
                    "demo": False,
                    "status": "queued",
                    "attempts": 0,
                    "request": request.model_dump(),
                    "request_digest": digest,
                    "created_at": time.time(),
                    "cleanup_verified": False,
                    "nested_call_budget_enforced": False,
                    "artifacts": [],
                }
                if request.nested_budget_policy == "gateway_scoped":
                    record["campaign_deadline"] = time.time() + request.runtime_seconds
            if self.active is not None:
                # No queue is silently created: a busy worker is a retryable
                # external dependency and original request id stays idempotent.
                raise HTTPException(409, "Dedicated worker is busy")
            existing = self._run(["docker", "ps", "-q"])
            if existing.returncode != 0 or existing.stdout.strip():
                raise HTTPException(
                    409, "Dedicated Docker daemon must have no running containers before a run"
                )
            record.update(
                status="running",
                attempts=record["attempts"] + 1,
                cleanup_verified=False,
                started_at=time.time(),
                error=None,
            )
            _write_json(job / "job.json", record)
            self.active = request.run_id
            cancelled = threading.Event()
            self.cancellations[request.run_id] = cancelled
            thread = threading.Thread(
                target=self._execute,
                args=(request, job, record, capabilities["image_id"], resume, cancelled),
                daemon=True,
            )
            thread.start()
            return self._public(record)

    def _cleanup(self, job: Path) -> bool:
        """Only remove containers whose bind mounts prove job ownership."""
        try:
            listed = self._run(["docker", "ps", "-aq"])
            identifiers = listed.stdout.split()
            if listed.returncode != 0 or len(identifiers) > 128:
                return False
            for identifier in identifiers:
                inspected = self._run(["docker", "inspect", identifier])
                if inspected.returncode != 0:
                    return False
                data = json.loads(inspected.stdout)[0]
                sources = [
                    mount.get("Source", "")
                    for mount in data.get("Mounts", [])
                    if mount.get("Type") == "bind"
                ]
                owned = any(
                    source and Path(source).resolve().is_relative_to(job.resolve())
                    for source in sources
                )
                if not owned:
                    return False
                if owned and self._run(["docker", "rm", "-f", identifier]).returncode != 0:
                    return False
            final = self._run(["docker", "ps", "-aq"])
            return final.returncode == 0 and not final.stdout.strip()
        except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError):
            return False

    def _execute(
        self,
        request: UpstreamRunRequest,
        job: Path,
        record: dict[str, Any],
        image: str,
        resume: bool,
        cancelled: threading.Event,
    ) -> None:
        returncode: int | None = None
        status, error = "failed", None
        process = None
        try:
            self._prepare_gateway_cli(request, job)
            remaining = self._resume_phases(request, job) if resume else None
            resume_investigation = bool(remaining and remaining[0] == "investigation")
            command = self._command(
                request, job, image, resume=resume_investigation, remaining_phases=remaining
            )
            # Logs are retained privately on the worker, never sent through the
            # API: original coding-agent output may echo its provider keys.
            log = job / f"attempt-{record['attempts']}.log"
            descriptor = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                process = self.popen(
                    command,
                    cwd=self.settings.repo,
                    env=self.environment(job),
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                with self.lock:
                    self.processes[request.run_id] = process
                remaining_seconds = request.runtime_seconds
                if request.nested_budget_policy == "gateway_scoped":
                    remaining_seconds = min(
                        remaining_seconds, record.get("campaign_deadline", 0) - time.time()
                    )
                deadline = time.monotonic() + remaining_seconds
                while process.poll() is None:
                    if (
                        cancelled.wait(0.25)
                        or time.monotonic() >= deadline
                        or log.stat().st_size > 16 * 1024 * 1024
                    ):
                        error = "cancelled" if cancelled.is_set() else "runtime_or_output_limit"
                        self._terminate(process)
                        break
                returncode = process.wait(timeout=10)
            if error:
                status = "cancelled" if cancelled.is_set() else "failed"
            else:
                events = self._events_from_disk(job)
                ending: dict[str, Any] = next(
                    (event for event in reversed(events) if event.get("event") == "pipeline_end"),
                    {},
                )
                reported = ending.get("status", ending.get("fields", {}).get("status"))
                if returncode == 0 and reported in {"completed", "completed_degraded"}:
                    status = reported
                else:
                    error = "Original pipeline did not publish a successful completion event"
        except Exception as exc:
            status = "failed"
            error = (
                "Original engine infrastructure or output validation failed ("
                + type(exc).__name__
                + ")"
            )
            if process is not None and process.poll() is None:
                self._terminate(process)
        finally:
            cleanup = self._cleanup(job)
            if not cleanup:
                status, error = (
                    "cleanup_unverified",
                    "Container cleanup could not be verified; operator intervention is required",
                )
            elif status in {"completed", "completed_degraded"}:
                try:
                    self._validate_completed_outputs(request, job, record)
                except Exception as exc:
                    status, error = (
                        "failed",
                        "Original engine output validation failed (" + type(exc).__name__ + ")",
                    )
            with self.lock:
                record.update(
                    status=status,
                    error=error,
                    return_code=returncode,
                    ended_at=time.time(),
                    cleanup_verified=cleanup,
                )
                record["artifacts"] = [
                    name
                    for name, relative in ARTIFACTS.items()
                    if (job / "run" / relative).is_file()
                    and not (job / "run" / relative).is_symlink()
                ]
                try:
                    _write_json(job / "job.json", record)
                finally:
                    self.processes.pop(request.run_id, None)
                    self.cancellations.pop(request.run_id, None)
                    # Failed cleanup keeps the worker fenced against further jobs.
                    self.active = None if cleanup else request.run_id

    def _gateway_file(self, identifier: str) -> Path:
        self._job(identifier)  # canonical UUID and private-root checks
        return self._root() / (".gateway-" + identifier + ".env")

    def deliver_grant(self, identifier: str, token: str) -> dict[str, Any]:
        from .gateway_client import validate_gateway_client

        origin = self.settings.gateway_origin
        base = origin + "/runs/" + UUID(identifier).hex
        try:
            validate_gateway_client(base, token)
            from urllib.parse import urlparse

            parsed = urlparse(origin)
            if parsed.scheme != "https" or parsed.path or parsed.query or parsed.fragment:
                raise ValueError
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid scoped gateway configuration") from None
        content = f"GEMINI_API_KEY={token}\nGOOGLE_GEMINI_BASE_URL={base}\n".encode()
        with self.lock:
            path = self._gateway_file(identifier)
            if path.exists():
                if not _private_owned(path):
                    raise HTTPException(409, "Unsafe gateway credential file")
                if _read_bounded(path, path.parent, 8192) == content:
                    return {"run_id": identifier, "credential_ready": True}
            if self.active is not None:
                raise HTTPException(409, "Cannot rotate credentials while worker is active")
            fd, temporary = tempfile.mkstemp(prefix=".credential-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
        return {"run_id": identifier, "credential_ready": True}

    def _prepare_gateway_cli(self, request: UpstreamRunRequest, job: Path) -> None:
        """Operator-owned gateway configuration only; never inferred from research input."""
        import io
        from urllib.parse import urlparse
        from dotenv import dotenv_values
        from .gateway_client import prepare_cli_environment, validate_gateway_client

        path = (
            self._gateway_file(request.run_id)
            if request.nested_budget_policy == "gateway_scoped"
            else self.settings.env_file
        )
        if path is None or not _private_owned(path):
            raise ValueError("Private agent configuration unavailable")
        values = dotenv_values(
            stream=io.StringIO(_read_bounded(path, path.parent, 8192).decode()), interpolate=False
        )
        base = values.get("GOOGLE_GEMINI_BASE_URL")
        if not base:
            return  # Preserve legacy operator-managed mode, still disabled by default.
        token = values.get("GEMINI_API_KEY") or ""
        if set(values) - {"GEMINI_API_KEY", "GOOGLE_GEMINI_BASE_URL"}:
            raise ValueError("Gateway mode accepts only its scoped credential and URL")
        validate_gateway_client(base, token)
        if urlparse(base).path != "/runs/" + UUID(request.checked_id()).hex:
            raise ValueError("Gateway run binding differs from original request")
        home = job / "auth"
        if not _private_owned(home, directory=True):
            raise ValueError("Private gateway agent home unavailable")
        if not (home / ".gemini").exists():
            prepare_cli_environment(home, base, token)
        else:
            marker = json.loads(_read_bounded(home / ".agsci-gateway-profile.json", job, 4096))
            if marker != {"version": 1, "run_id": UUID(request.checked_id()).hex}:
                raise ValueError("Existing home was not prepared for this gateway run")
            settings = json.loads(_read_bounded(home / ".gemini/settings.json", job, 8192))
            if (
                settings.get("security", {}).get("auth", {}).get("selectedType") != "gemini-api-key"
                or settings.get("privacy", {}).get("usageStatisticsEnabled") is not False
                or settings.get("telemetry", {}).get("enabled") is not False
            ):
                raise ValueError("Gateway agent profile changed; operator review required")

    @staticmethod
    def _validate_completed_outputs(
        request: UpstreamRunRequest, job: Path, record: dict[str, Any]
    ) -> None:
        # Read only after all agent containers have stopped. Every path is
        # checked against symlink traversal before original evidence validation.
        if request.generate_paper:
            pdf = _read_bounded(job / "run/paper/paper.pdf", job, 16 * 1024 * 1024)
            if not pdf.startswith(b"%PDF-"):
                raise ValueError("Upstream paper output is not a PDF")
        final = job / "run/final_evaluation"
        if (final / "final_manifest.json").exists():
            _read_bounded(final / "final_manifest.json", job)
            from src.final_evaluation.runner import verify_final_manifest

            verified = verify_final_manifest(final)
            record["metrics"] = verified["metrics"]
            record["evaluation"] = {
                "correct": verified["correct"],
                "outcome": verified.get("outcome"),
                "source": "original_sealed_final_evaluation",
            }
        else:
            record["metrics"] = {}
            record["evaluation"] = {
                "status": "unavailable",
                "reason": "Original pipeline produced no sealed final evaluation; do not infer scientific success from workflow completion.",
            }

    @staticmethod
    def _terminate(process: Any) -> None:
        try:
            os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass

    def _resume_phases(self, request: UpstreamRunRequest, job: Path) -> list[str]:
        phases = ["task_drafting", "investigation", "ablations", "final_evaluation", "posthoc"]
        if request.generate_paper:
            phases.append("paper")
        completed: set[str] = set()
        for event in self._events_from_disk(job):
            fields = event.get("fields", {})
            if event.get("event") == "phase_end" and fields.get("status") in {
                "completed",
                "degraded",
            }:
                completed.add(fields.get("phase_name"))
        remaining = phases[
            next(
                (index for index, phase in enumerate(phases) if phase not in completed), len(phases)
            ) :
        ]
        if not remaining:
            raise HTTPException(
                409, "All original phases already completed; no executable checkpoint remains"
            )
        if remaining[0] == "investigation":
            from src.pipeline.config import validate_investigation_resume_state

            if validate_investigation_resume_state(job / "run/investigation"):
                raise HTTPException(
                    409, "Original investigation checkpoint is unusable; start a new research run"
                )
        if (
            "final_evaluation" in remaining
            and (job / "run/final_evaluation/invocation.json").exists()
        ):
            raise HTTPException(
                409,
                "Sealed final evaluation already started; original once-only evaluation cannot be retried",
            )
        return remaining

    @staticmethod
    def _events_from_disk(job: Path) -> list[dict[str, Any]]:
        try:
            raw = _read_bounded(job / "run/pipeline_events.jsonl", job, 8 * 1024 * 1024)
        except FileNotFoundError:
            return []
        events = []
        for line in raw.splitlines()[-10000:]:
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
            except ValueError:
                continue
        return events

    def events(self, identifier: str, after: int) -> dict[str, Any]:
        self._record(identifier)
        events = self._events_from_disk(self._job(identifier))
        # Structured allow-list only; upstream terminal text, prompts and paths
        # never cross the credential boundary through progress events.
        allowed = {
            "event",
            "phase",
            "phase_name",
            "status",
            "return_code",
            "outcome",
            "elapsed_seconds",
            "timestamp",
        }
        result = []
        for index, event in enumerate(events[after : after + 200], start=after):
            source = {
                **event,
                **(event.get("fields", {}) if isinstance(event.get("fields"), dict) else {}),
            }
            result.append(
                {
                    "sequence": index,
                    **{
                        key: value
                        for key, value in source.items()
                        if key in allowed and isinstance(value, (str, int, float, bool, type(None)))
                    },
                }
            )
        return {"events": result, "next_cursor": after + len(result)}

    def cancel(self, identifier: str) -> dict[str, Any]:
        with self.lock:
            record = self._record(identifier)
            if identifier in self.cancellations:
                self.cancellations[identifier].set()
                return {
                    "run_id": identifier,
                    "status": "cancellation_requested",
                    "cleanup_verified": False,
                }
            return self._public(record)

    def resume(self, identifier: str) -> dict[str, Any]:
        record = self._record(identifier)
        return self.submit(UpstreamRunRequest.model_validate(record["request"]), resume=True)

    def artifact(self, identifier: str, name: str) -> bytes:
        self._record(identifier)
        if name not in ARTIFACTS:
            raise HTTPException(404, "Artifact unavailable")
        if name == "pipeline_events.jsonl":
            # Never expose the raw original journal: some phase failures carry
            # terminal output tails containing prompt text or provider secrets.
            lines: list[str] = []
            cursor = 0
            while cursor < 10000:
                batch = self.events(identifier, cursor)
                lines.extend(
                    json.dumps(event, ensure_ascii=True) + "\n" for event in batch["events"]
                )
                if batch["next_cursor"] == cursor:
                    break
                cursor = batch["next_cursor"]
            return "".join(lines).encode()
        job = self._job(identifier)
        try:
            return _read_bounded(job / "run" / ARTIFACTS[name], job, 16 * 1024 * 1024)
        except (OSError, ValueError) as exc:
            raise HTTPException(404, "Artifact unavailable") from exc


def create_app(
    settings: WorkerSettings | None = None, *, worker: UpstreamWorker | None = None
) -> FastAPI:
    settings = settings or WorkerSettings.from_env()
    worker = worker or UpstreamWorker(settings)

    def authenticate(authorization: str = Header(default="")) -> None:
        if (
            len(settings.token) < 32
            or "REPLACE" in settings.token.upper()
            or not hmac.compare_digest(
                authorization.encode("utf-8"), ("Bearer " + settings.token).encode("utf-8")
            )
        ):
            raise HTTPException(401, "Worker authentication required")

    app = FastAPI(
        title="Isolated original scientist worker",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authenticate)],
    )
    app.state.worker = worker

    @app.middleware("http")
    async def require_bounded_body(request: Any, call_next: Any) -> Any:
        if request.method == "POST":
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return Response(status_code=400)
            if length > 128 * 1024 or request.headers.get("transfer-encoding"):
                return Response(status_code=413)
        return await call_next(request)

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, Any]:
        return worker.capabilities()

    @app.post("/v1/dry-run")
    def dry_run(request: UpstreamRunRequest) -> dict[str, Any]:
        return worker.dry_run(request)

    @app.post("/v1/runs")
    def submit(request: UpstreamRunRequest) -> dict[str, Any]:
        return worker.submit(request)

    @app.post("/v1/runs/{identifier}/gateway-credential")
    async def credential(identifier: str, request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
            if (
                not isinstance(body, dict)
                or set(body) != {"scoped_token"}
                or not isinstance(body["scoped_token"], str)
            ):
                raise ValueError
            return worker.deliver_grant(identifier, body["scoped_token"])
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid scoped credential request") from None

    @app.get("/v1/runs/{identifier}")
    def status(identifier: str) -> dict[str, Any]:
        return worker.status(identifier)

    @app.get("/v1/runs/{identifier}/events")
    def events(identifier: str, after: int = Query(default=0, ge=0, le=1000000)) -> dict[str, Any]:
        return worker.events(identifier, after)

    @app.post("/v1/runs/{identifier}/cancel")
    def cancel(identifier: str) -> dict[str, Any]:
        return worker.cancel(identifier)

    @app.post("/v1/runs/{identifier}/resume")
    def resume(identifier: str) -> dict[str, Any]:
        return worker.resume(identifier)

    @app.get("/v1/runs/{identifier}/artifacts/{name}")
    def artifact(identifier: str, name: str) -> Response:
        content = worker.artifact(identifier, name)
        return Response(
            content,
            media_type="application/pdf" if name == "paper.pdf" else "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8801)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Offline capability check; use authenticated API when service is running",
    )
    parser.add_argument(
        "--recover",
        metavar="UUID",
        help="Offline: verify empty research cgroup and dedicated daemon; never resume",
    )
    args = parser.parse_args()
    settings = WorkerSettings.from_env()
    if args.check and args.recover:
        parser.error("--check and --recover are mutually exclusive")
    try:
        if args.check and not settings.enabled:
            print(json.dumps(UpstreamWorker(settings).capabilities(probe=False)))
            raise SystemExit(1)
        with controller_lock(settings):
            worker = UpstreamWorker(settings)
            if args.recover:
                print(json.dumps(worker.recover(args.recover)))
            elif args.check:
                result = worker.capabilities()
                print(json.dumps(result))
                raise SystemExit(0 if result["infrastructure_ready"] else 1)
            else:
                uvicorn.run(
                    create_app(settings, worker=worker),
                    host=args.host,
                    port=args.port,
                    limit_concurrency=16,
                    access_log=False,
                )
    except (OSError, RuntimeError, ValueError, HTTPException):
        print(
            json.dumps(
                {
                    "ready": False,
                    "reason": "Worker lock, private configuration or offline recovery validation failed; no campaign started.",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
