import io
import json
import pytest

from src.research_platform.execution import (
    CapabilityError,
    DockerExecutor,
    ExecutionCancelled,
    ExecutionTimeout,
    OutputLimitError,
    sanitized_environment,
)
from src.research_platform.scientist_adapter import ScientistAdapter


class FakeProcess:
    def __init__(self, output, *, running=False):
        self.stdout = io.BytesIO(output)
        self.returncode = None if running else 0
        self.killed = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


def test_cpu_command_enforces_isolation_without_host_mounts():
    command = DockerExecutor().command("test-run")
    for option in [
        "--pull=never",
        "--network=none",
        "--read-only",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--cpus=1",
        "--memory=256m",
        "--memory-swap=256m",
        "--log-driver=none",
    ]:
        assert option in command
    assert "-v" not in command and "--mount" not in command and "--privileged" not in command
    assert "-e" not in command and "--env-file" not in command


def test_subprocess_environment_never_inherits_keys():
    assert sanitized_environment(
        {
            "PATH": "bin",
            "GEMINI_API_KEY": "secret",
            "GROQ_API_KEY": "secret",
            "LANGSMITH_API_KEY": "secret",
            "PYTHONPATH": "bad",
        }
    ) == {"PATH": "bin"}


def test_free_does_not_fallback_to_host_when_docker_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("src.research_platform.execution.shutil.which", lambda name: None)
    adapter = ScientistAdapter(
        executor=DockerExecutor(popen=lambda *args, **kwargs: pytest.fail("launched"))
    )
    with pytest.raises(CapabilityError, match="Docker"):
        adapter.execute("run", "free", {}, tmp_path)
    assert not (tmp_path / "execution_result.json").exists()


def test_successful_cpu_capture_is_bounded_and_cleaned(monkeypatch):
    commands = []
    process = FakeProcess(
        json.dumps(
            {
                "program": "curated_square_grid_packing_v1",
                "baseline": {"sum_radii": 2},
                "candidate": {"sum_radii": 2.5},
            }
        ).encode()
    )
    executor = DockerExecutor(
        popen=lambda *args, **kwargs: process, runner=lambda cmd, **kw: commands.append(cmd)
    )
    monkeypatch.setattr(executor, "capabilities", lambda: {"ready": True})
    result = executor.execute()
    assert result["candidate"]["sum_radii"] == 2.5
    assert commands[-1][:3] == ["docker", "rm", "--force"]


def test_timeout_kills_and_removes_container(monkeypatch):
    process = FakeProcess(b"", running=True)
    removed = []
    executor = DockerExecutor(
        popen=lambda *args, **kwargs: process, runner=lambda cmd, **kw: removed.append(cmd)
    )
    executor.timeout_seconds = 0
    monkeypatch.setattr(executor, "capabilities", lambda: {"ready": True})
    with pytest.raises(ExecutionTimeout):
        executor.execute()
    assert process.killed and removed


def test_output_overflow_raises(monkeypatch):
    process = FakeProcess(b"x" * 10000)
    executor = DockerExecutor(
        output_limit_bytes=1024,
        popen=lambda *args, **kwargs: process,
        runner=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(executor, "capabilities", lambda: {"ready": True})
    with pytest.raises(OutputLimitError):
        executor.execute()


def test_prelaunch_cancel_does_not_run_program(monkeypatch):
    executor = DockerExecutor(popen=lambda *args, **kwargs: pytest.fail("launched"))
    monkeypatch.setattr(executor, "capabilities", lambda: {"ready": True})
    with pytest.raises(ExecutionCancelled):
        executor.execute(cancel_check=lambda: True)


def test_demo_fixture_and_receipt_are_idempotent(tmp_path):
    adapter = ScientistAdapter()
    first = adapter.execute("run", "demo", {"plan": "one"}, tmp_path)
    replay = adapter.execute("run", "demo", {"plan": "changed"}, tmp_path)
    assert first == replay and first["demo"] and first["metrics"]["fixture"]
    assert "not measured evidence" in first["logs"][0]
    with pytest.raises(CapabilityError):
        adapter.execute("other-run", "demo", {}, tmp_path)


def test_full_mode_has_honest_capability_error(tmp_path):
    with pytest.raises(CapabilityError, match="isolated Linux worker"):
        ScientistAdapter().execute("run", "full", {}, tmp_path)
    preview = ScientistAdapter.upstream_command_preview(model="discovered-model")
    assert preview[:3] == ["agsci", "run", "examples/circpack"]
    assert "--dry-run" in preview and "container.enabled=true" in preview
    assert "container.enabled=false" not in preview


def test_import_only_accepts_inventory_identifier(tmp_path):
    adapter = ScientistAdapter(results_root=tmp_path)
    with pytest.raises(CapabilityError):
        adapter.import_existing_run("../../.env")


def test_import_reuses_upstream_inspector_numeric_artifacts(tmp_path):
    investigation = tmp_path / "circpack" / "gemini" / "test_run" / "investigation"
    investigation.mkdir(parents=True)
    (investigation / "outer_state.json").write_text("{}")
    program = investigation / "ideas" / "001_grid" / "program_0"
    program.mkdir(parents=True)
    (program / "metrics.json").write_text(
        '{"combined_score": 0.5, "secret_string": "do-not-import"}'
    )
    (program / "correct.json").write_text('{"correct": true}')
    adapter = ScientistAdapter(results_root=tmp_path)
    assert adapter.list_existing_runs()[0]["id"] == "circpack/gemini/test_run"
    result = adapter.import_existing_run("circpack/gemini/test_run")
    assert result["source"] == "upstream_agsci" and result["status"] == "imported"
    assert not result["demo"]
    assert result["metrics"]["evaluations"] == [
        {"worker": 1, "program": 0, "metrics": {"combined_score": 0.5}, "correct": True}
    ]
    assert "do-not-import" not in json.dumps(result)
