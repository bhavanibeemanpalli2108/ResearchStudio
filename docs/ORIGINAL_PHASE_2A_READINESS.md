# Phase 2A — installed QEMU and KVM device-access readiness

Verified **2026-11-23, Asia/Calcutta**: device access approximately 11:46–11:47;
separately authorized diskless probe at **11:55:52** local time.
Status: **QEMU/KVM hardware-accelerated guest initialization verified** with one
paused, diskless, networkless 128-MiB probe. No full guest, OS installation,
research workload, provider request or Docker/WSL configuration change occurred.
Original research web launch and all budget protections remain unchanged.

## Authorized installation and observed changes

The owner authorized only:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends qemu-system-x86 qemu-utils
sudo usermod -aG kvm sonusunny
```

The agent's earlier `sudo -n apt-get update` stopped at an interactive-authentication
requirement before executing apt. The owner subsequently completed installation
and group configuration in Ubuntu. The observations below independently verify
the resulting state; no privileged command was rerun by this verification.

| Check | Actual result |
| --- | --- |
| Effective user/session | UID 1000, sonusunny; supplementary kvm GID 991 present |
| Persistent group entry | `kvm:x:991:sonusunny` |
| KVM device ownership/mode | root:kvm, `0660`, not world-writable |
| Effective read/write permission | True |
| Actual device access | `os.open('/dev/kvm', os.O_RDWR | os.O_CLOEXEC)` succeeded; descriptor closed immediately |
| QEMU system binary | `/usr/bin/qemu-system-x86_64`, native Linux ELF, 10.2.1 |
| QEMU image utility | `/usr/bin/qemu-img`, native Linux ELF, 10.2.1 |
| Installed package versions | Both `1:10.2.1+ds-1ubuntu3.3` |
| Before/after package inventory | **35 new packages; zero existing-version changes; zero removals** |
| Current simulated installation | 0 upgraded, 0 new, 0 removed; both requested packages already installed |

The 35 additions match the reviewed QEMU dependency set, including firmware,
libraries, `ubuntu-virt` and `ubuntu-helper-virt-hwe`. The exact added-package list
and before/after package inventories are retained in ignored local validation
storage. No libvirt/Docker daemon or guest has been provisioned by this task.

The earlier device-access check alone issued no KVM ioctl and created no VM.
The later, separately authorized probe below demonstrates initialization. Version
output and group membership alone were not treated as acceleration proof.

## Resource snapshot and full-guest gate

| Resource | Measured value |
| --- | --- |
| Windows available RAM | **7.78 GiB**, probe preflight at 11:54:51 |
| Windows commit headroom | **5.68 GiB**, same preflight |
| WSL available memory | **10.81 GiB**, overlapping Windows memory, not an additional pool |
| Physical free space | Earlier 11:46 sample: C: **282.47 GiB**; D: **496.35 GiB**; no guest disk was created |
| CPU/virtualization | 18 logical CPUs, VMX exposed, nested KVM parameter Y; no virtualization setting changed |
| WSL distributions | Ubuntu running on WSL2; docker-desktop stopped, left unchanged |

Windows and WSL memory overlap and are not added. The resource values fluctuate
and must be rechecked immediately before the next authorized action. The existing
full 6-GiB guest floor is 9 GiB Windows available RAM and 8 GiB commit headroom,
plus the separate Linux/physical-storage checks in the Phase 2 report. **Both
Windows memory floors currently fail. Full-guest provisioning is blocked at
this snapshot**, regardless of available disk space and installed QEMU.

The 128-MiB, paused, diskless probe is a separate small test; it does not authorize
or establish readiness for the 6-GiB guest. Recheck its headroom before execution.
Do not stop applications, resize WSL, change swap or start Docker automatically
to meet any gate. No software-emulation fallback is permitted.

## Exact existing diskless probe — executed once

This is the same bounded QMP procedure in
[the Phase 2 report](ORIGINAL_PHASE_2_READINESS.md). The owner explicitly authorized
this probe separately from the completed package/group approval:

```bash
id
test -r /dev/kvm && test -w /dev/kvm
printf '%s\n' '{"execute":"qmp_capabilities"}' '{"execute":"query-status"}' '{"execute":"quit"}' |
  timeout 10 qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 1 -m 128 \
    -nodefaults -display none -S -qmp stdio
```

It requests one virtual CPU and 128 MiB RAM, KVM explicitly, paused CPUs, no guest
disk or default network devices, no display and no operating-system installation.
The three QMP commands negotiate management, inspect state and quit. The 10-second
timeout bounds a failed/hung probe. There is no model/research workload or API key.

The capture wrapper asserted that this was the exact reviewed command and used
a clean environment without provider credentials. The command's 10-second
timeout was retained; an additional 10-second watchdog could terminate only the
new probe process session if needed. Neither timeout/watchdog fired. No retry,
additional QMP query or emulation fallback was used.

### Actual result

| Item | Observed result |
| --- | --- |
| Attempts | **1** |
| Elapsed command time | **0.112596 seconds** |
| Process exit status | **0** |
| Stderr | Empty |
| QMP command errors | None |
| CPU state | `prelaunch`, `running: false` |
| Shutdown | `host-qmp-quit` event, followed by successful quit response |
| Probe process group remaining | **No**; no forced cleanup needed |
| KVM initialization | **Verified**: QEMU initialized with KVM as its only requested accelerator and responded successfully |

Actual QMP output (after the successful `id` and device-access prechecks):

```json
{"QMP": {"version": {"qemu": {"micro": 1, "minor": 2, "major": 10}, "package": "Debian 1:10.2.1+ds-1ubuntu3.3"}, "capabilities": ["oob"]}}
{"return": {}}
{"return": {"status": "prelaunch", "running": false}}
{"timestamp": {"seconds": 1795415152, "microseconds": 845697}, "event": "SHUTDOWN", "data": {"guest": false, "reason": "host-qmp-quit"}}
{"return": {}}
```

The returns correspond in order to `qmp_capabilities`, `query-status`, and `quit`.
Full stdout, empty stderr, exact command and structured result are retained in
ignored local validation storage:
`.research-platform/validation/phase2a-20261123/diskless-probe-20261123T062552Z/`.
No key, research artifact or private configuration was passed into the process.

This proves **hardware-accelerated paused VM initialization**, not a Linux OS boot,
guest instruction execution, full-worker isolation, performance, networking,
Docker/cgroup behavior or original-engine acceptance. The tiny probe is finished;
no further VM action is authorized by its success.

## Rollback — proposal only, not executed

Only remove changes introduced for this task, after reviewing current dependency
use and obtaining operator approval. Group rollback:

```bash
sudo gpasswd -d sonusunny kvm
```

Close/re-enter affected Ubuntu login sessions to discard existing supplementary
group access; do not use an automatic WSL/Docker shutdown.

Conservative QEMU package rollback (leaves dependency cleanup for review):

```bash
sudo apt-get --simulate remove qemu-system-x86 qemu-utils
# Review the proposed removals before executing:
sudo apt-get remove qemu-system-x86 qemu-utils
```

For a complete removal plan, the recorded 35 additions can be supplied explicitly
to APT, from the repository root in WSL:

```bash
xargs -r -a .research-platform/validation/phase2a-20261123/new-packages.txt sudo apt-get --simulate remove --
# Only after review confirms no pre-existing/newly depended-on package is affected:
xargs -r -a .research-platform/validation/phase2a-20261123/new-packages.txt sudo apt-get remove --
```

Do not use blanket autoremove, purge personal configuration or uninstall packages
that now support another workload. Package-index refresh is metadata, not an OS
upgrade; no attempt to force older indexes is proposed. The probe exited normally;
there is no guest disk to delete or persistent VM service to roll back.

## Preservation and next approvals

This verification changes documentation and ignored validation records only.
Application code, existing Git commit/tag history, provider keys, budgets,
research evidence and Docker settings are preserved. No commit, push or history
rewrite is part of Phase 2A verification. Documentation-only changes do not require
rerunning research experiments or consuming completed-run budgets.

The authorized Phase 2A probe is complete; **stop before Phase 2B**. Phase 2B
requires fresh resource checks and separate explicit authorization for
the 4-vCPU/6-GiB/64-GiB guest, verified image/disk provisioning, dedicated daemon,
resource policies and mock-only deployment acceptance. Genuine Gemini credentials
and model requests remain a further independent approval. Current full-guest
memory thresholds fail; do not provision or silently change resources to bypass
that blocker. No additional packages, permissions or system configuration changes
were made during the probe.
