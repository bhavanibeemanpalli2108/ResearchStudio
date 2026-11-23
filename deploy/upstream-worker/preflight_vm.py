"""Read-only WSL laptop startup gate; never creates or starts a VM."""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import subprocess

GIB = 1024**3
WINDOWS_AVAILABLE_MIN = 9 * GIB
WINDOWS_COMMIT_MIN = 8 * GIB
LINUX_AVAILABLE_MIN = int(8.5 * GIB)
DISK_FREE_MIN = 90 * GIB

# Fixed read-only commands. No profile, provider configuration or system mutation.
WINDOWS_QUERY = r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$samples=(Get-Counter '\Memory\Available Bytes','\Memory\Committed Bytes','\Memory\Commit Limit').CounterSamples
$available=($samples | Where-Object { $_.Path -like '*available bytes' }).CookedValue
$committed=($samples | Where-Object { $_.Path -like '*committed bytes' }).CookedValue
$limit=($samples | Where-Object { $_.Path -like '*commit limit' }).CookedValue
$distro=@(Get-ChildItem HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss | Get-ItemProperty | Where-Object { $_.DistributionName -eq 'Ubuntu' })
if ($distro.Count -ne 1) { throw 'Cannot identify Ubuntu backing volume' }
$base=[string]$distro[0].BasePath
$prefix=([string][char]92)+[char]92+'?'+[char]92
if ($base.StartsWith($prefix)) { $base=$base.Substring(4) }
if ($base.Length -lt 3 -or $base[1] -ne ':' -or $base[2] -ne [char]92 -or -not [char]::IsLetter($base[0])) { throw 'Unsupported backing location' }
$drive=$base.Substring(0,1)
$free=(Get-PSDrive -Name $drive -PSProvider FileSystem).Free
[ordered]@{available_bytes=$available;committed_bytes=$committed;commit_limit_bytes=$limit;backing_drive=$drive;physical_free_bytes=$free} | ConvertTo-Json -Compress
"""


def windows_metrics() -> dict:
    executable = shutil.which("powershell.exe")
    if executable is None:
        raise ValueError("Windows counters unavailable; refusing VM startup")
    result = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-Command", WINDOWS_QUERY],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=15,
    )
    value = json.loads(result.stdout.lstrip("\ufeff"))
    if not isinstance(value, dict):
        raise ValueError("Invalid Windows counter response")
    return value


def linux_metrics() -> dict:
    memory = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    available = memory["MemAvailable"].split()
    if len(available) != 2 or available[1] != "kB":
        raise ValueError("Invalid Linux available-memory measurement")
    return {
        "available_bytes": int(available[0]) * 1024,
        "filesystem_free_bytes": shutil.disk_usage(Path.home()).free,
    }


def measured(metrics: dict, key: str) -> float:
    value = metrics[key]
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise ValueError("Missing or invalid resource measurement")
    return float(value)


def assess(windows: dict, linux: dict) -> dict:
    available = measured(windows, "available_bytes")
    committed = measured(windows, "committed_bytes")
    limit = measured(windows, "commit_limit_bytes")
    disk = measured(windows, "physical_free_bytes")
    linux_available = measured(linux, "available_bytes")
    linux_disk = measured(linux, "filesystem_free_bytes")
    headroom = limit - committed
    checks = {
        "windows_available_ram": available >= WINDOWS_AVAILABLE_MIN,
        "windows_commit_headroom": headroom >= WINDOWS_COMMIT_MIN,
        "wsl_available_memory": linux_available >= LINUX_AVAILABLE_MIN,
        "physical_backing_space": disk >= DISK_FREE_MIN,
        "linux_filesystem_space": linux_disk >= DISK_FREE_MIN,
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "windows_available_gib": round(available / GIB, 2),
        "windows_commit_headroom_gib": round(headroom / GIB, 2),
        "wsl_available_gib": round(linux_available / GIB, 2),
        "physical_backing_free_gib": round(disk / GIB, 2),
        "backing_drive": windows.get("backing_drive"),
        "note": "Windows/WSL RAM overlaps. Passing is a resource check, not provisioning authorization.",
        "vm_started": False,
    }


def main() -> int:
    try:
        result = assess(windows_metrics(), linux_metrics())
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        result = {
            "ready": False,
            "error": "Resource measurements unavailable or invalid; VM startup refused",
            "vm_started": False,
        }
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
