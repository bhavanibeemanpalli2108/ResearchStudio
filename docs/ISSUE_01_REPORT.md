# ISSUE-01 — Phase 1 dedicated original-worker infrastructure

2026-11-22 follow-up: [offline controller integration](ORIGINAL_CONTROLLER_PHASE_1.md)
adds persistent run/grant coordination and scoped credential delivery. This does
not provision or accept a dedicated worker. Status remains **partially resolved**.

Current 2026-11-22 assessment and ordered acceptance plan:
[Original Sakana next milestone](ORIGINAL_SAKANA_NEXT_MILESTONE.md).
The dated report below is retained. ISSUE-02 now has a separate offline gateway
implementation report; neither issue has deployed infrastructure acceptance.

Verified 2026-11-20, Asia/Calcutta. Status: **PARTIALLY RESOLVED**.
Repository preparation and automated contract verification are complete. No
compliant guest VM/controller/daemon has been provisioned or accepted. Provisioning
requires explicit approval. No privileged host configuration, system installation,
provider credential use or original research campaign occurred.

## Findings: implemented versus missing

The existing upstream_worker.py and upstream_execution.py already supply strict
Gemini-only request validation, operator-managed budget acknowledgement, a bounded
Hydra command builder, authenticated capability/dry-run/status/control/artifact
endpoints, bounded HTTP client responses, explicit loopback-development transport,
private job journals/logs, fixed artifact allowlists, wall-clock/output checks,
job-owned container cleanup and restart fencing. They are separate from the native
LangGraph worker; original web launch was not integrated and remains HTTP 409.

Missing infrastructure was not a Python provider problem: the workstation daemon
is shared Docker Desktop, not an administrator-owned isolated original worker.
There were no checked-in dedicated daemon/systemd/environment deployment files or
offline recovery procedure, and no focused tests of this worker contract.

Inspection also identified implementation gaps corrected here:

- systemd's `agsci-research.slice` lives below `agsci.slice`; the old default/check
  assumed a root-level slice and could not verify the intended nested placement.
- The controller's own cgroup placement was not checked alongside container limits.
- A renamed socket alone did not exclude Desktop daemon identity.
- Capability-probe client timeout did not explicitly verify container removal.
- Cleanup could accept an unowned stopped container and only checked running ones.
- Restart fencing lacked a safe offline reconciliation operation; corrupt journals
  could be silently ignored. Multiple serving processes lacked a shared root lock.
- Worker enablement did not separately default original campaigns to disabled.

## Host feasibility and recommended architecture

Observed read-only on this laptop:

| Item | Evidence |
|---|---|
| OS / project shell | Windows 11 Home Single Language; PowerShell, existing D:/project/reseon/AI-Scientist-v3 checkout |
| CPU | Intel Core Ultra 5 125H; 14 cores / 18 logical processors |
| Physical memory visible | 25,158,090,752 bytes, about 23.4 GiB |
| Windows free RAM samples | about 7.1 GiB initially, 6.1 GiB in saved final sample; varies with active workloads |
| Windows hypervisor | Present; vmcompute running |
| Windows optional features | VirtualMachinePlatform enabled; HypervisorPlatform disabled; full Hyper-V unavailable on Home |
| Existing distributions | Ubuntu and docker-desktop, both WSL2 and running |
| Ubuntu | 26.04.1 LTS; systemd PID 1; kernel 6.18.58.1-microsoft-standard-WSL2 |
| WSL memory | about 11.4 GiB visible, about 10 GiB available at initial sample |
| Docker Desktop | 18 CPUs / about 11.4 GiB visible; Name docker-desktop; DockerRootDir /var/lib/docker; cgroupfs driver; cgroup v2 |
| Independent local dockerd | Not found in the current Ubuntu PATH |
| QEMU / VirtualBox / VMware command tools | Not found in inspected Windows/Ubuntu PATHs |
| KVM | /dev/kvm exists (root:kvm); current user lacks read/write access and kvm group membership |
| Cgroup v2 controllers in WSL | cpu, memory, pids present, but this is not a dedicated controller/daemon |
| Free disk at inspection | roughly 271 GiB on C:, 496 GiB on D: |

The CIM virtualization-firmware/SLAT flags were not used to conclude virtualization
is disabled: an active Windows hypervisor and WSL2 were independently observed.
KVM initialization/guest boot remain untested; a device node is not proof of access
or acceleration. No .wslconfig was found at the inspected user-profile path, and
no WSL global resource/virtualization settings were changed.

The recommended free local development option is **a separate Ubuntu Server VM
under QEMU/KVM in WSL**, conditional on approved package/KVM access setup and a
successful accelerator smoke test. It is not a second WSL distro. Its guest kernel,
root filesystem, native controller, Docker daemon, Unix socket and data root are
separate from Desktop. Proposed VM allocation: 4 vCPUs, 6 GiB RAM, private 64 GiB
sparse disk. Prefer at least 9 GiB free Windows RAM before starting it; current free
RAM is tight and no applications were stopped to make space. The aggregate
controller/container slice is limited to 2 CPUs, 4 GiB RAM, no swap and 1024 PIDs;
the daemon service has independent finite CPU/memory/PID limits. This can support
bounded lab checks, not a claim that arbitrary original campaigns fit the laptop.

The deployment boots with guest outbound networking blocked, only loopback SSH
forwarded, no host filesystem/socket/device/clipboard shares, and an authenticated
SSH tunnel carrying the worker bearer-token protocol. Administrator-owned daemon
policy fixes the socket, data root, systemd driver and research cgroup parent.
Private token/empty provider files and private job storage are separate from the
workstation's .env and native-run databases.

A conventional Linux VM on another host is an alternative if nested KVM fails.
Direct Windows QEMU/WHPX would require a separate feature/install approval;
VirtualBox/VMware coexistence with the active hypervisor was not tested and is not
recommended as a blind install. No Windows edition upgrade is required for the
proposed QEMU/KVM route. Official references:
[WSL nested virtualization](https://learn.microsoft.com/en-us/windows/wsl/wsl-config),
[QEMU accelerators/network isolation](https://www.qemu.org/docs/master/system/invocation.html),
[Hyper-V edition requirements](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/Install-Hyper-V),
[Docker daemon configuration](https://docs.docker.com/engine/daemon/),
[systemd aggregate limits](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html).

## Repository changes

Production behavior stays in the existing worker; no new execution service or queue
was introduced. `RESEARCH_UPSTREAM_CAMPAIGNS_ENABLED` defaults to false. Authenticated
capability checks can distinguish `infrastructure_ready` from campaign `ready` with
a private but empty provider file. Infrastructure readiness still requires valid
transport-token configuration, private storage/policy and the isolation checks;
absence of a real Gemini key is expected in Phase 1. This does not validate provider
credential validity or nested-call accounting.

Docker info rejects Desktop identity/labels, default data root, non-systemd driver
and non-v2 cgroups. Matching root-owned daemon policy and controller/container
placement are required. Probes run only on a verified empty dedicated daemon,
without network/credentials, with an immutable local image, 1 CPU, 256 MiB, 32 PIDs
and bounded time; a unique container name is explicitly removed and absence checked.
Probes/submissions are serialized. A nonempty daemon is not probed again.

Private-root process locking excludes concurrent controllers and offline recovery.
Restarted/invalid job journals fence execution. Offline recovery requires the
service lock to be free, research cgroup empty and verified dedicated daemon empty;
it marks only the chosen journal interrupted/cleanup-verified. It never kills,
deletes containers, resumes, resets attempts, refunds budgets or launches work.
Unknown ownership/corrupt journals need operator inspection or guest replacement.

Exact repository files changed by this task:

- src/research_platform/upstream_worker.py
- tests/research_platform/test_upstream_worker.py
- tests/research_platform/test_api.py
- deploy/upstream-worker/README.md
- deploy/upstream-worker/daemon.json
- deploy/upstream-worker/worker.env.example
- deploy/upstream-worker/agent.env.example
- deploy/upstream-worker/client.env.example
- deploy/upstream-worker/agsci-research.slice
- deploy/upstream-worker/agsci-daemon.service
- deploy/upstream-worker/agsci-upstream-worker.service
- deploy/upstream-worker/start-vm.sh
- docs/ISSUE_01_REPORT.md
- docs/UPSTREAM_WORKER.md
- docs/RESEARCH_ENGINE_ACCEPTANCE.md
- docs/ARCHITECTURAL_CORRECTIONS.md
- docs/DEPLOYMENT.md
- docs/DEVELOPMENT_PROGRESS.md
- issues.md

The pre-existing uncommitted changes were preserved. No .env, dependencies,
Docker Desktop configuration, WSL configuration, historical results, model ledger,
virtual environment or system service was modified. The existing completed native
Groq run still reports completed, at 17 model calls after the earlier authorized
ISSUE-04 verification. This task made no provider requests.

## Validation and actual results

| Check | Actual result |
|---|---|
| Full Linux platform suite, existing Python 3.12.16 environment | **182 passed**, 26.66 seconds |
| Full Windows platform suite | **149 passed, 33 skipped**, 42.58 seconds; POSIX worker tests explicitly skipped on Windows |
| Focused new worker contract tests on Linux | **33 passed** |
| Focused worker + existing API tests after serialization review | **46 passed**; final added web-launch regression included in full suites above |
| Ruff lint / format | passed |
| Mypy Linux target | passed, 28 source files |
| VM launcher `bash -n` | passed; launcher not executed |
| Current host rejection | actual Desktop identity rejected; actual WSL controller rejected |
| Dedicated guest capability endpoint / effective cgroups | not live-verified: guest has not been provisioned |
| systemd-analyze verify on current WSL host | incomplete/exit 1: guest dockerd and /opt/agsci-worker/venv/bin/python do not exist here; DrvFs file-mode warnings also reported |
| Real original-engine campaign | not launched; no campaign phases claimed |

The worker tests simulate the administrator/kernel/daemon responses explicitly;
they are not evidence of a running compliant guest. They cover correct dedicated
controller/daemon, default socket and Desktop identity rejection, private/missing
credential configuration, invalid transport tokens, invalid cgroup limits,
unavailable image, failed/timed-out probe cleanup, unowned stopped containers,
failed execution cleanup, restart and corrupt-journal fencing, offline recovery
refusal with live processes/containers, process-lock exclusion, authenticated
capabilities, bounded request/preview and execution-disabled submission. A native
API regression confirms full original web launch still returns HTTP 409 without
creating a run. No fixture claims valid live Gemini credentials.

Systemd units must be installed root-owned mode 0644 in the guest and validated
there. Do not interpret successful text parsing/tests or WSL's filesystem-mode
warnings as a deployed service. No placeholder executable was installed to make
this check appear successful. CPUQuota enables CPU control without the obsolete
CPUAccounting directive; aggregate resource limits still require live guest proof.

Commands executed from the existing repository (PowerShell and explicit WSL):

```powershell
Get-CimInstance Win32_ComputerSystem
Get-CimInstance Win32_OperatingSystem
Get-CimInstance Win32_Processor
Get-CimInstance Win32_OptionalFeature
wsl --list --verbose
docker info --format '{{json .}}'
# WSL read-only inventory: uname, /etc/os-release, id, free, df, cgroup files,
# command -v dockerd/qemu/systemctl, and /dev/kvm access checks.
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/research_platform --confcutdir=tests/research_platform -q'
.venv/Scripts/python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -q
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/research_platform/test_upstream_worker.py tests/research_platform/test_api.py --confcutdir=tests/research_platform -q'
.venv/Scripts/python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform
.venv/Scripts/python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform
.venv/Scripts/python.exe -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent --platform linux
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3; bash -n deploy/upstream-worker/start-vm.sh'
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3; systemd-analyze verify deploy/upstream-worker/agsci-research.slice deploy/upstream-worker/agsci-daemon.service deploy/upstream-worker/agsci-upstream-worker.service'
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m src.research_platform.upstream_worker --check'
git diff --check
```

The last offline capability command correctly returns not ready in the current
unprovisioned WSL environment. An additional read-only script applied the daemon
identity check to the actual saved Desktop info; it returned false without running
containers. Evidence is saved under .research-platform/validation/issue-01-phase1/:
hardware.json, windows-memory.json, desktop-daemon.json, host-capabilities.json,
host-rejection.json and unit-verification.txt. Git retains its pre-existing uv.lock
line-ending warning. Windows retains an existing LangChain pending-deprecation
warning; neither was changed to obscure a failure.

## Approval boundary and remaining blockers

The [deployment runbook](../deploy/upstream-worker/README.md) contains the exact
proposed package/KVM access commands, guest-only staging/service installation,
private token generation, image loading, startup, SSH transport, shutdown and
non-destructive recovery steps. They were prepared for review, not executed.

The next approval would permit WSL QEMU installation and access to /dev/kvm:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends qemu-system-x86 qemu-utils
sudo usermod -aG kvm sonusunny
```

Then, after re-entering the user session and verifying accelerator initialization,
provision one new private Ubuntu guest with the reviewed 4-vCPU/6-GiB/64-GiB plan.
No Windows feature enablement, WSL reinstall/shutdown, Docker Desktop change,
shared workstation socket, real provider key or paid provider call is authorized
by repository preparation. Do not create the guest until the operator approves
and sufficient memory headroom is available. If acceleration cannot initialize,
stop and reassess; do not silently change hypervisor/BIOS/WSL settings.

ISSUE-01 remains partially resolved until an approved guest demonstrates actual
dedicated daemon identity, controller/container cgroups, authenticated capability
and bounded preview, container absence after shutdown, and interrupted-worker
recovery. **ISSUE-02 remains unresolved:** nested calls do not have a hard request
budget. Campaigns stay disabled. **ISSUE-03 remains disabled:** original web launch
still returns HTTP 409. No native success, fixture, doctor result or preview is
reported as a completed original research campaign.
