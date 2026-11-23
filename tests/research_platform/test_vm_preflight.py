"""Resource gates and refusal paths only. No VM, disk image or privileged action."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "vm_preflight", ROOT / "deploy/upstream-worker/preflight_vm.py"
)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
GIB = 1024**3


def measurements():
    return (
        {
            "available_bytes": 9 * GIB,
            "committed_bytes": 16 * GIB,
            "commit_limit_bytes": 24 * GIB,
            "physical_free_bytes": 90 * GIB,
            "backing_drive": "C",
        },
        {"available_bytes": int(8.5 * GIB), "filesystem_free_bytes": 1000 * GIB},
    )


def test_exact_floors_pass_without_granting_start_authorization():
    result = preflight.assess(*measurements())
    assert result["ready"] and not result["vm_started"]


def test_linux_ram_cannot_make_up_for_windows_ram():
    windows, linux = measurements()
    windows["available_bytes"] -= 1
    linux["available_bytes"] = 100 * GIB
    result = preflight.assess(windows, linux)
    assert not result["ready"] and not result["checks"]["windows_available_ram"]


def test_commit_headroom_is_independent_of_available_ram():
    windows, linux = measurements()
    windows["available_bytes"] = 20 * GIB
    windows["committed_bytes"] += 1
    assert not preflight.assess(windows, linux)["checks"]["windows_commit_headroom"]


def test_large_virtual_disk_does_not_override_physical_backing_space():
    windows, linux = measurements()
    windows["physical_free_bytes"] -= 1
    result = preflight.assess(windows, linux)
    assert result["checks"]["linux_filesystem_space"]
    assert not result["ready"] and not result["checks"]["physical_backing_space"]


def test_wsl_memory_has_its_own_compatibility_floor():
    windows, linux = measurements()
    linux["available_bytes"] -= 1
    assert not preflight.assess(windows, linux)["ready"]


@pytest.mark.parametrize("invalid", [True, "90000000000", None, -1, float("nan"), float("inf")])
def test_invalid_measurements_fail_closed(invalid):
    windows, linux = measurements()
    windows["available_bytes"] = invalid
    with pytest.raises(ValueError):
        preflight.assess(windows, linux)


def test_missing_windows_counter_never_reports_ready(monkeypatch, capsys):
    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
    assert preflight.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["ready"] is False and result["vm_started"] is False


def test_windows_query_uses_bounded_fixed_read_only_command(monkeypatch):
    windows, _ = measurements()
    monkeypatch.setattr(preflight.shutil, "which", lambda name: "powershell.exe")

    def run(arguments, **kwargs):
        assert arguments == [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            preflight.WINDOWS_QUERY,
        ]
        assert kwargs["timeout"] == 15 and kwargs["check"] is True
        return subprocess.CompletedProcess(arguments, 0, stdout=json.dumps(windows))

    monkeypatch.setattr(preflight.subprocess, "run", run)
    assert preflight.windows_metrics() == windows


@pytest.mark.skipif(sys.platform != "linux", reason="WSL launcher shell path")
def test_startup_refused_before_qemu_and_without_creating_a_disk(tmp_path):
    # All shims are temporary test files, never system settings or executables.
    powershell = tmp_path / "powershell.exe"
    powershell.write_text(
        "#!/usr/bin/python3\nimport json\nprint(json.dumps("
        + repr(
            {
                "available_bytes": 0,
                "committed_bytes": 0,
                "commit_limit_bytes": 0,
                "physical_free_bytes": 200 * GIB,
                "backing_drive": "C",
            }
        )
        + "))\n"
    )
    powershell.chmod(0o700)
    qemu = tmp_path / "qemu-system-x86_64"
    qemu.write_text("#!/bin/sh\necho QEMU_SHOULD_NOT_RUN >&2\nexit 97\n")
    qemu.chmod(0o700)
    disk = tmp_path / "not-created.qcow2"
    script = ROOT / "deploy/upstream-worker/start-vm.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    result = subprocess.run(
        ["bash", str(script), "--start-approved-vm", str(disk)],
        env={**os.environ, "PATH": str(tmp_path) + ":/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["ready"] is False
    assert "QEMU_SHOULD_NOT_RUN" not in result.stderr
    assert not disk.exists()
