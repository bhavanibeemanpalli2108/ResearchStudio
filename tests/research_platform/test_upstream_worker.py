"""Dedicated-worker contract tests; synthetic infrastructure, no provider calls."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.research_platform import upstream_worker as module
from src.research_platform.upstream_execution import UpstreamRunRequest, UpstreamWorkerClient

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="POSIX worker contract")


class Infrastructure:
    def __init__(self):
        self.commands = []
        self.info = {
            "Name": "dedicated-guest",
            "OperatingSystem": "Ubuntu",
            "DockerRootDir": "/var/lib/agsci-docker",
            "CgroupDriver": "systemd",
            "CgroupVersion": "2",
            "Labels": [],
        }
        self.image = True
        self.timeout = False
        self.leftover = False
        self.containers = ""
        self.mounts = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        # This boundary must never inherit application credentials/selectors.
        assert "GROQ_API_KEY" not in kwargs["env"]
        assert kwargs["env"]["DOCKER_HOST"] == "unix:///run/agsci-docker.sock"
        output, code = "", 0
        if command[:2] == ["docker", "info"]:
            output = json.dumps(self.info)
        elif command[:3] == ["docker", "image", "inspect"]:
            output, code = ("sha256:" + "a" * 64, 0) if self.image else ("", 1)
        elif command[:2] == ["docker", "run"]:
            assert "--network=none" in command and "--pull=never" in command
            assert "--memory=256m" in command and "--cpus=1" in command
            if self.timeout:
                raise subprocess.TimeoutExpired(command, 30)
            output = "0::/agsci.slice/agsci-research.slice/docker-fixture.scope\n"
        elif command[:3] == ["docker", "ps", "-aq"]:
            output = "leftover" if "--filter" in command and self.leftover else self.containers
        elif command[:2] == ["docker", "inspect"]:
            output = json.dumps([{"Mounts": self.mounts, "State": {"Running": False}}])
        elif command[:3] == ["docker", "rm", "-f"] and not command[-1].startswith(
            "agsci-capability-"
        ):
            self.containers = ""
        return subprocess.CompletedProcess(
            command, code, stdout=output, stderr="sensitive fixture response never returned"
        )


@pytest.fixture
def configured(tmp_path, monkeypatch):
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    credentials = tmp_path / "agent.env"
    credentials.write_text("GEMINI_API_KEY=fixture-not-a-real-provider-key\n")
    credentials.chmod(0o600)
    cgroup = tmp_path / "agsci-research.slice"
    cgroup.mkdir()
    for name, value in {
        "cpu.max": "200000 100000",
        "memory.max": str(4 * 1024**3),
        "pids.max": "1024",
        "cgroup.events": "populated 0\nfrozen 0\n",
    }.items():
        (cgroup / name).write_text(value)
    daemon = tmp_path / "daemon.json"
    policy = json.loads(
        (Path(__file__).parents[2] / "deploy/upstream-worker/daemon.json").read_text()
    )
    daemon.write_text(json.dumps(policy))
    settings = module.WorkerSettings(
        enabled=True,
        root=root,
        token="fixture-transport-token-" + "x" * 32,
        isolation_ack=module.ISOLATION_ACK,
        env_file=credentials,
        cgroup=cgroup,
        daemon_config=daemon,
    )
    # Synthetic administrator/kernel identities, never evidence of live readiness.
    monkeypatch.setattr(module, "_trusted_config", lambda path: True)
    monkeypatch.setattr(module, "_native_controller", lambda: True)
    monkeypatch.setattr(
        module,
        "_controller_membership",
        lambda: "0::/agsci.slice/agsci-research.slice/controller.service",
    )
    monkeypatch.setattr(
        module, "_cgroup_path", lambda settings: "/agsci.slice/agsci-research.slice"
    )
    monkeypatch.setattr(module.platform, "release", lambda: "6.8.0-generic")
    infra = Infrastructure()
    worker = module.UpstreamWorker(
        settings, runner=infra, popen=lambda *a, **kw: pytest.fail("Campaign launched")
    )
    return settings, worker, infra


def request():
    return UpstreamRunRequest(
        run_id=str(uuid4()),
        question="Does this bounded dry-run avoid every model request?",
        model="fixture-model-not-live-verified",
        runtime_seconds=60,
        nested_budget_policy="operator_managed",
        nested_budget_approved=True,
    )


def journal(settings, status="running"):
    identifier = str(uuid4())
    job = settings.root / identifier
    job.mkdir(mode=0o700)
    module._write_json(
        job / "job.json", {"run_id": identifier, "status": status, "cleanup_verified": False}
    )
    return identifier, job


def test_infrastructure_ready_does_not_enable_campaigns_or_claim_nested_budget(configured):
    settings, worker, infra = configured
    result = worker.capabilities()
    assert result["infrastructure_ready"] and all(result["checks"].values())
    assert not result["ready"] and not result["campaigns_enabled"]
    assert result["nested_call_budget_enforced"] is False
    with pytest.raises(HTTPException) as error:
        worker.submit(request())
    assert error.value.status_code == 409
    assert all(command[0] != settings.python or command[1] == "-c" for command in infra.commands)


@pytest.mark.parametrize(
    "details",
    [
        {"OperatingSystem": "Docker Desktop"},
        {"Name": "docker-desktop"},
        {"Labels": ["com.docker.desktop.address=socket"]},
        {"DockerRootDir": "/var/lib/docker"},
        {"CgroupDriver": "cgroupfs"},
        {"CgroupVersion": "1"},
    ],
)
def test_ordinary_or_mismatched_daemon_rejected_before_container_probe(configured, details):
    _, worker, infra = configured
    infra.info.update(details)
    result = worker.capabilities()
    assert not result["infrastructure_ready"] and not result["checks"]["docker_daemon"]
    assert not any(command[:2] == ["docker", "run"] for command in infra.commands)


def test_default_desktop_socket_rejected_without_contacting_daemon(configured):
    settings, _, infra = configured
    worker = module.UpstreamWorker(
        replace(settings, docker_host="unix:///var/run/docker.sock"), runner=infra
    )
    assert not worker.capabilities()["checks"]["dedicated_docker_socket"]
    assert not infra.commands


@pytest.mark.parametrize(
    "name,value",
    [
        ("cpu.max", "max 100000"),
        ("cpu.max", "500000 100000"),
        ("cpu.max", "100000 0"),
        ("memory.max", "max"),
        ("memory.max", "0"),
        ("pids.max", "4097"),
    ],
)
def test_invalid_aggregate_limits_rejected(configured, name, value):
    settings, worker, infra = configured
    (settings.cgroup / name).write_text(value)
    assert not worker.capabilities()["checks"]["finite_cgroup_limits"]
    assert not infra.commands


def test_missing_credentials_do_not_prevent_safe_infrastructure_probe(configured):
    settings, worker, _ = configured
    settings.env_file.write_text("GEMINI_API_KEY=\n")
    result = worker.capabilities()
    assert result["infrastructure_ready"] and not result["ready"]
    assert not result["checks"]["gemini_credentials_configured"]
    settings.env_file.chmod(0o644)
    assert not worker.capabilities()["checks"]["private_credentials"]


@pytest.mark.parametrize("token", ["", "short", "REPLACE" * 10])
def test_invalid_transport_configuration_fails_closed(configured, token):
    settings, worker, infra = configured
    settings = replace(settings, token=token)
    assert not module.UpstreamWorker(settings, runner=infra).capabilities(probe=False)[
        "infrastructure_ready"
    ]
    with TestClient(module.create_app(settings, worker=worker)) as client:
        assert (
            client.get("/v1/capabilities", headers={"Authorization": "Bearer " + token}).status_code
            == 401
        )


def test_authenticated_capabilities_and_bounded_command_preview(configured):
    settings, worker, infra = configured
    with TestClient(module.create_app(settings, worker=worker)) as client:
        assert client.get("/v1/capabilities").status_code == 401
        headers = {"Authorization": "Bearer " + settings.token}
        result = client.get("/v1/capabilities", headers=headers)
        assert result.status_code == 200 and result.json()["infrastructure_ready"]
        assert (
            settings.token not in result.text
            and "fixture-not-a-real-provider-key" not in result.text
        )
        preview = client.post("/v1/dry-run", json=request().model_dump(), headers=headers)
        assert preview.status_code == 200
        data = preview.json()
        assert data["executed"] is False and "--dry-run" in data["command"]
        assert "container.enabled=true" in data["command"]
        assert "investigation.execution.run_timeout_seconds=60" in data["command"]
        assert (
            client.post("/v1/runs", json=request().model_dump(), headers=headers).status_code == 409
        )
        assert list(settings.root.iterdir()) == []  # preview does not create a job
        invalid = request().model_dump()
        invalid["runtime_seconds"] = 0
        assert client.post("/v1/dry-run", json=invalid, headers=headers).status_code == 422


def test_missing_image_and_probe_cleanup_failure_are_not_ready(configured):
    _, worker, infra = configured
    infra.image = False
    assert not worker.capabilities()["checks"]["agent_image"]
    assert not any(command[:2] == ["docker", "run"] for command in infra.commands)
    infra.image, infra.leftover = True, True
    assert not worker.capabilities()["infrastructure_ready"]


def test_timed_out_capability_probe_is_explicitly_cleaned(configured):
    _, worker, infra = configured
    infra.timeout = True
    result = worker.capabilities()
    assert not result["infrastructure_ready"] and result["checks"]["capability_probe_cleanup"]
    assert any(command[:3] == ["docker", "rm", "-f"] for command in infra.commands)


def test_controller_must_share_real_nested_slice_and_not_be_wsl(configured, monkeypatch):
    _, worker, infra = configured
    monkeypatch.setattr(
        module, "_controller_membership", lambda: "0::/system.slice/unbounded.service"
    )
    assert not worker.capabilities()["checks"]["controller_cgroup_enforced"]
    assert not infra.commands
    monkeypatch.setattr(module.platform, "release", lambda: "6.18-microsoft-standard-WSL2")
    assert not worker.capabilities()["checks"]["non_wsl_controller"]


def test_restart_fences_interrupted_job_and_offline_recovery_never_resumes(configured):
    settings, _, infra = configured
    identifier, job = journal(settings)
    restarted = module.UpstreamWorker(settings, runner=infra)
    assert restarted.status(identifier)["status"] == "cleanup_unverified"
    assert not restarted.capabilities()["infrastructure_ready"]
    with module.controller_lock(settings):
        result = restarted.recover(identifier)
    assert result["status"] == "interrupted" and result["cleanup_verified"]
    assert json.loads((job / "job.json").read_text())["status"] == "interrupted"
    assert not any(command[:2] == ["docker", "run"] for command in infra.commands)


@pytest.mark.parametrize("populated,containers", [("1", ""), ("0", "unknown-container")])
def test_recovery_refuses_live_processes_or_any_remaining_containers(
    configured, populated, containers
):
    settings, _, infra = configured
    identifier, _ = journal(settings)
    restarted = module.UpstreamWorker(settings, runner=infra)
    (settings.cgroup / "cgroup.events").write_text("populated " + populated)
    infra.containers = containers
    with module.controller_lock(settings), pytest.raises(RuntimeError):
        restarted.recover(identifier)
    assert restarted.status(identifier)["status"] == "cleanup_unverified"
    assert not any(command[:2] == ["docker", "rm"] for command in infra.commands)


def test_cleanup_does_not_remove_unowned_stopped_container(configured):
    settings, worker, infra = configured
    _, job = journal(settings, "failed")
    infra.containers = "unowned-stopped"
    assert not worker._cleanup(job)
    assert not any(command[:2] == ["docker", "rm"] for command in infra.commands)


def test_controller_lock_excludes_second_controller_or_recovery(configured):
    settings, _, _ = configured
    with module.controller_lock(settings):
        with pytest.raises(BlockingIOError), module.controller_lock(settings):
            pytest.fail("Second controller acquired lock")


def test_untrusted_daemon_policy_is_not_probed(configured, monkeypatch):
    _, worker, infra = configured
    monkeypatch.setattr(module, "_trusted_config", lambda path: False)
    assert not worker.capabilities()["checks"]["trusted_daemon_config"]
    assert not infra.commands


def test_nonempty_dedicated_daemon_does_not_launch_another_probe(configured):
    _, worker, infra = configured
    infra.containers = "abandoned-probe-or-unowned-container"
    assert not worker.capabilities()["checks"]["exclusive_daemon_idle"]
    assert not any(command[:2] == ["docker", "run"] for command in infra.commands)


def test_successful_cleanup_removes_only_job_owned_container(configured):
    settings, worker, infra = configured
    _, job = journal(settings, "failed")
    infra.containers = "owned"
    infra.mounts = [{"Type": "bind", "Source": str(job / "run")}]
    assert worker._cleanup(job)
    assert ["docker", "rm", "-f", "owned"] in infra.commands


def test_failed_execution_cleanup_keeps_worker_fenced(configured, monkeypatch):
    settings, worker, _ = configured
    identifier, job = journal(settings)
    payload = request().model_copy(update={"run_id": identifier})
    record = {"run_id": identifier, "status": "running", "attempts": 1}
    process = type("Finished", (), {"poll": lambda self: 1, "wait": lambda self, **kw: 1})()
    worker.popen = lambda *args, **kwargs: process
    monkeypatch.setattr(worker, "_cleanup", lambda job: False)
    worker._execute(payload, job, record, "sha256:" + "a" * 64, False, threading.Event())
    assert record["status"] == "cleanup_unverified" and record["cleanup_verified"] is False
    assert worker.active == identifier


def test_corrupt_journal_fences_startup(configured):
    settings, _, infra = configured
    identifier, job = journal(settings)
    (job / "job.json").write_text("[]")
    restarted = module.UpstreamWorker(settings, runner=infra)
    assert restarted.active is not None
    assert not restarted.capabilities()["infrastructure_ready"]


def test_actual_slice_hierarchy_and_transport_contract():
    settings = module.WorkerSettings()
    assert module._cgroup_path(settings) == "/agsci.slice/agsci-research.slice"
    assert module._in_cgroup(settings, "0::/agsci.slice/agsci-research.slice/controller.service")
    assert not module._in_cgroup(settings, "0::/agsci-research.slice-other/controller.service")
    client = UpstreamWorkerClient(
        {
            "RESEARCH_UPSTREAM_WORKER_URL": "http://192.0.2.1:8801",
            "RESEARCH_UPSTREAM_WORKER_TOKEN": "x" * 32,
        }
    )
    try:
        assert not client.capabilities()["ready"]  # validation only, no network
    finally:
        client.close()


@pytest.mark.parametrize("invalid", [None, "real_key", "wrong_run"])
def test_gateway_cli_setup_is_scoped_and_never_uses_real_key(configured, invalid):
    settings, worker, _ = configured
    identifier, job = journal(settings, "failed")
    (job / "auth").mkdir(mode=0o700)
    payload = request().model_copy(update={"run_id": identifier})
    gateway_id = identifier.replace("-", "") if invalid != "wrong_run" else "a" * 32
    token = "gw_" + "x" * 43 if invalid != "real_key" else "fixture-provider-key-not-scoped"
    settings.env_file.write_text(
        "GEMINI_API_KEY="
        + token
        + "\nGOOGLE_GEMINI_BASE_URL=https://10.0.2.100:8843/runs/"
        + gateway_id
        + "\n"
    )
    if invalid:
        with pytest.raises(ValueError):
            worker._prepare_gateway_cli(payload, job)
        assert not (job / "auth/.gemini/settings.json").exists()
    else:
        worker._prepare_gateway_cli(payload, job)
        worker._prepare_gateway_cli(payload, job)  # safe existing private profile on resume
        profile = json.loads((job / "auth/.gemini/settings.json").read_text())
        assert profile["security"]["auth"]["selectedType"] == "gemini-api-key"
        assert profile["privacy"]["usageStatisticsEnabled"] is False
    assert not settings.campaigns_enabled


def test_gateway_mode_refuses_unmarked_existing_auth_home(configured):
    settings, worker, _ = configured
    identifier, job = journal(settings, "failed")
    home = job / "auth"
    home.mkdir(mode=0o700)
    (home / ".gemini").mkdir(mode=0o700)
    (home / ".gemini/settings.json").write_text(
        json.dumps(
            {
                "security": {"auth": {"selectedType": "gemini-api-key"}},
                "privacy": {"usageStatisticsEnabled": False},
                "telemetry": {"enabled": False},
            }
        )
    )
    settings.env_file.write_text(
        "GEMINI_API_KEY=gw_"
        + "x" * 43
        + "\nGOOGLE_GEMINI_BASE_URL=https://10.0.2.100:8843/runs/"
        + identifier.replace("-", "")
        + "\n"
    )
    with pytest.raises(FileNotFoundError):
        worker._prepare_gateway_cli(request().model_copy(update={"run_id": identifier}), job)


def test_authenticated_scoped_delivery_binding_rotation_and_private_storage(configured):
    settings, worker, _ = configured
    worker.settings = replace(settings, gateway_origin="https://10.0.2.100:8843", env_file=None)
    identifier = str(uuid4())
    token = "gw_" + "a" * 43
    app = module.create_app(worker.settings, worker=worker)
    path = f"/v1/runs/{identifier}/gateway-credential"
    headers = {"Authorization": "Bearer " + settings.token}
    with TestClient(app) as client:
        assert client.post(path, json={"scoped_token": token}).status_code == 401
        for body in (
            {"scoped_token": "not-scoped"},
            {"scoped_token": token, "url": "https://evil.invalid"},
            {"scoped_token": [token]},
        ):
            response = client.post(path, headers=headers, json=body)
            assert response.status_code == 400 and token not in response.text
        response = client.post(path, headers=headers, json={"scoped_token": token})
        assert response.json() == {"run_id": identifier, "credential_ready": True}
        assert token not in response.text
        credential = worker._gateway_file(identifier)
        assert credential.stat().st_mode & 0o077 == 0
        assert "/runs/" + identifier.replace("-", "") in credential.read_text()
        worker.active = identifier
        assert client.post(path, headers=headers, json={"scoped_token": token}).status_code == 200
        assert (
            client.post(path, headers=headers, json={"scoped_token": "gw_" + "b" * 43}).status_code
            == 409
        )
        assert (
            client.get(
                f"/v1/runs/{identifier}/artifacts/{credential.name}", headers=headers
            ).status_code
            == 404
        )
        worker.active = None
        assert (
            client.post(path, headers=headers, json={"scoped_token": "gw_" + "b" * 43}).status_code
            == 200
        )
    assert worker.capabilities()["nested_call_budget_enforced"] is False
    assert not worker.settings.campaigns_enabled


def test_scoped_credential_symlink_and_expired_worker_resume_rejected(configured, monkeypatch):
    settings, worker, _ = configured
    worker.settings = replace(
        settings, gateway_origin="https://10.0.2.100:8843", campaigns_enabled=True
    )
    payload = request().model_copy(update={"nested_budget_policy": "gateway_scoped"})
    identifier = payload.run_id
    credential = worker._gateway_file(identifier)
    credential.symlink_to(settings.env_file)
    with pytest.raises(HTTPException):
        worker.deliver_grant(identifier, "gw_" + "a" * 43)
    credential.unlink()
    worker.deliver_grant(identifier, "gw_" + "a" * 43)
    job = worker._job(identifier)
    job.mkdir(mode=0o700)
    import hashlib

    module._write_json(
        job / "job.json",
        {
            "run_id": identifier,
            "status": "interrupted",
            "cleanup_verified": True,
            "attempts": 1,
            "campaign_deadline": time.time() - 1,
            "request_digest": hashlib.sha256(payload.model_dump_json().encode()).hexdigest(),
        },
    )
    monkeypatch.setattr(worker, "capabilities", lambda: {"ready": True})
    with pytest.raises(HTTPException, match="Scoped execution window expired"):
        worker.submit(payload, resume=True)


def test_optional_tls_launch_keeps_worker_lock_and_disabled_campaigns(configured, monkeypatch):
    import uvicorn

    settings, worker, _ = configured
    entered = []
    launched = []

    @contextmanager
    def locked(config):
        assert config == settings
        entered.append(True)
        yield
        entered.pop()

    def serve(app, **kwargs):
        assert entered == [True]
        assert app.state.worker is worker
        assert not worker.settings.campaigns_enabled
        launched.append(kwargs)

    monkeypatch.setattr(module, "controller_lock", locked)
    monkeypatch.setattr(module.WorkerSettings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(module, "UpstreamWorker", lambda config: worker)
    monkeypatch.setattr(uvicorn, "run", serve)
    monkeypatch.setattr(
        sys,
        "argv",
        ["worker", "--tls-cert", "/private/fixture.crt", "--tls-key", "/private/fixture.key"],
    )
    module.main()
    assert not entered
    assert launched[0]["ssl_certfile"] == "/private/fixture.crt"
    assert launched[0]["ssl_keyfile"] == "/private/fixture.key"
    assert launched[0]["host"] == "127.0.0.1"
    assert launched[0]["access_log"] is False and launched[0]["proxy_headers"] is False


@pytest.mark.parametrize("flag", ["--tls-cert", "--tls-key"])
def test_partial_worker_tls_configuration_fails_before_serving(monkeypatch, flag):
    monkeypatch.setattr(sys, "argv", ["worker", flag, "/private/fixture"])
    monkeypatch.setattr(
        module, "controller_lock", lambda settings: pytest.fail("Partial TLS entered worker lock")
    )
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
