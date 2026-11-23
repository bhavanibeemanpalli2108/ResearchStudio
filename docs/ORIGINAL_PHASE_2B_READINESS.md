# Phase 2B preparation — no VM provisioned

2026-11-23, Asia/Calcutta. **Planning and read-only checks only.** No VM directory,
disk/image, guest, package, credential, service, network rule or system setting
was created/changed. Native research and original web restrictions are unchanged.
Existing Git ancestry and release tags are preserved. The requested checkpoint
is a normal follow-up source/documentation commit, not a history rewrite.

## Current readiness

The actual Phase 2A probe remains verified: KVM-only initialization, one paused
vCPU, 128 MiB, three successful QMP replies, exit 0 in 0.112596 seconds, no stderr
or remaining process. [Phase 2A evidence report](ORIGINAL_PHASE_2A_READINESS.md)
and its original ignored stdout/stderr/result files are preserved; it was not rerun.
This is not proof of a Linux boot, daemon isolation or a full research campaign.

The latest checkpoint preflight observed **9.53 GiB Windows available RAM**
(passes the 9-GiB floor), but only **6.51 GiB commit headroom** (fails the 8-GiB
floor). WSL had approximately **10.78 GiB available**, which overlaps Windows
memory and is not added to it. **Full-guest provisioning/startup remains blocked.**
These are point-in-time samples; normal-workload values must pass immediately
before any later authorized provisioning/start. No applications were stopped
and no WSL/swap allocation was changed to meet a threshold.

## Storage allocation checked without creating it

- Proposed root: `/home/sonusunny/.local/share/reseon-worker-acceptance`.
- Proposed disk: that directory's `worker.qcow2`, **64 GiB maximum virtual size**.
- Both proposed root and disk currently **do not exist**; no symlink was observed
  in their path. Native home mount: `/dev/sdd`, **ext4**, not a workstation share.
- Windows registry identifies Ubuntu's backing VHDX on **C:**. The preflight
  measured approximately **282.32 GiB actual C: free**; D: approximately 496.35
  GiB is not extra capacity for this proposed C:-backed guest.
- Require at least **90 GiB physical backing free** and 90 GiB Linux filesystem
  free to cover a disk growing to 64 GiB plus reviewed image/staging/log overhead.
  The Linux filesystem's large virtual free size is not physical Windows space.
- Create a private mode-0700 directory and a fresh sparse qcow2 only after approval.
  Refuse existing targets; no overwrite or automatic deletion. Do not move the
  disk to DrvFs/another volume without re-reviewing filesystem and backing checks.
  Monitor real C: usage: nested qcow2/ext4-VHDX growth and image layers consume it.

## Controller, daemon and network boundary

The trusted backend/OriginalController/Gemini gateway writers belong together on
one trusted Linux host and **local SQLite**. Initial acceptance uses a new Linux
test ledger; the current Windows native application/database stays untouched.
No Windows/WSL dual SQLite writers or remote database file sharing is accepted.
Any later real backend/data cutover needs its own backup/locking/rollback approval.

The disposable guest must have its own Linux kernel and Docker daemon:

| Requirement | Planned value / evidence required |
| --- | --- |
| Daemon socket | `unix:///run/agsci-docker.sock`, no Desktop/default socket |
| Data / exec roots | `/var/lib/agsci-docker`, `/run/agsci-docker` |
| Daemon identity | Native Linux, systemd/cgroup2, dedicated label/process; actual acceptance checks required |
| Research slice | 200% CPU, 4 GiB, zero swap, 1024 PIDs, effective controller/container membership |
| Dedicated daemon service | 100% CPU, 768 MiB, zero swap, 512 PIDs |
| Guest allocation | 4 vCPUs, 6 GiB; remaining guest OS/other margin approximately 1.25 GiB |

The normal Desktop socket or a renamed proxy to it is not compliant. No host
drives, Docker socket, private key/ledger, clipboard or host device shares.

Management uses loopback-only SSH forwarding plus authenticated worker HTTP/TLS.
The trusted controller requires verified HTTPS; the worker's existing TLS launcher
retains its exclusive process lock. Certificates, private transport tokens and
trust setup are **planned, not provisioned**; no verification-disabling flags.
Only scoped, expiring model grants reach the worker; real provider keys stay
outside it and are not authorized at this stage.

Baseline `start-vm.sh` keeps `restrict=on` with only loopback SSH ingress and
**no guest outbound forward**. The later prepared gateway topology permits only
guest `10.0.2.100:8843` to trusted `127.0.0.1:8843`, with verified TLS and bounded
host-side forwarding processes. That gateway forward/socat is not installed or
enabled. Deny direct providers, alternate host services, DNS/raw IPv4/IPv6 and
metadata egress. Actual guest-root/container packet tests with a mock provider
are required; repository policy specifications are not deployed enforcement.

## Read-only preflight and reproducible sequence

From WSL, without starting or creating anything:

```bash
python3 deploy/upstream-worker/preflight_vm.py
```

It reads Windows RAM/commit counters and the physical volume backing Ubuntu,
plus native Linux available memory/filesystem space. It never adds the pools,
reads `.env`, changes resources or executes QEMU. Missing/malformed/non-finite
measurements, unavailable Windows interop/counters or an unknown backing volume
refuse startup. It has no threshold-lowering/bypass option. `start-vm.sh` calls
it before QEMU; the documented bounded gateway-forward variant also gates on it.
Passing this check does not grant provisioning authorization or reserve memory.

After resource gates pass, **request separate approval**, then follow
[the ordered acceptance runbook](../deploy/upstream-worker/ACCEPTANCE.md):

1. Pin the reviewed Phase 2B source checkpoint/archive hash including the preflight
   preparation. Select an official guest image and pin its URL/checksum;
   do not download it under this preparation task.
2. With approval, create only the new private disk and install/stage the native
   Linux guest using verified media/offline artifacts. No workstation directory
   mounts or research internet access as a staging shortcut.
3. Inside that **new guest only**, install the reviewed Docker/Python dependencies,
   private account and existing daemon/slice/worker units. Keep campaigns off;
   use no real provider key. Do not install dockerd on normal WSL or alter Desktop.
4. Separately approve management TLS/token provisioning, trusted mock gateway
   and bounded host forwarding. Validate daemon identity, effective cgroups,
   TLS/auth, egress denial, atomic 20/21-call accounting, cleanup/restart and
   allowlisted artifact hashes against the mock transport before any live request.
5. Shut down by revoking test grants and stopping only new worker/gateway/forwarder
   units; verify empty research cgroup and a successful empty dedicated daemon
   listing, then authenticated guest shutdown. Preserve journals/uncertain usage.
6. Rollback only new units/forwarders; retain the guest disk pending review. No
   Desktop prune, unknown-container removal, automatic disk deletion, uncertain
   reservation refund or overwrite of research evidence. Package, group, trust or
   data-cutover rollback remains separately reviewed as documented in prior phases.

## Remaining blockers and scope

Resolved without privileged changes here: missing automatic RAM/commit startup
gate, physical/virtual storage ambiguity, and stale source-staging references.
Still open: adequate Windows headroom; approved image/source staging; actual guest,
independent daemon/cgroups, TLS/auth, host forwarding and guest packet acceptance.
No original campaign or web enablement follows from a resource/preflight pass.
ISSUE-01/02 remain partial and ISSUE-03 disabled. Genuine provider eligibility,
credentials and requests require a further independent authorization.

## Validation and files changed

- New preflight cases: **14 passed on WSL**, **13 passed / 1 Linux-shell case
  skipped on Windows**. Tests cover exact/below floors, overlapping RAM, commit
  headroom, physical versus virtual disk, invalid/missing measurements and startup
  refusal before QEMU. The shell integration uses only temporary shims and a
  nonexistent filename; no disk image is created or VM launched.
- Full WSL native platform/CLI/Inspector suite: **361 passed, 4 genuine-Docker
  cases excluded**. Existing dependency deprecation warnings remain.
- Ruff lint/format: pass (58 Python files in checked formatting scope).
  Linux-target mypy: pass (38 source files). Launcher `bash -n` and Git whitespace
  checks pass. No frontend code was changed.
- Actual resource-only preflight returns `ready=false`, exit 1, with failed
  Windows commit-headroom and successful RAM/WSL/storage checks. An expected refusal
  is not a startup or provisioning attempt.
- Retained database snapshots and **121 artifact files** still match the original
  baseline. Original Phase 2A command/stdout/stderr/result files were read, hashed
  and preserved without rerunning the probe.

Preparation changes: `deploy/upstream-worker/preflight_vm.py`, `start-vm.sh`,
`README.md`, `ACCEPTANCE.md`, `tests/research_platform/test_vm_preflight.py`, and
this report. The Phase 2A reports are preserved in the same reviewed checkpoint.
Initial preparation was based on `4672bf10ed7d994aedbd87412f22588cb764fce2`.
The owner subsequently authorized a normal commit/push of this preparation;
verify its exact resulting hash with `git log -1` and the publication report.
Existing release tags must remain unchanged. No actual VM/image creation or
provisioning command in the runbook was executed. As the resource gate fails,
the conditional request for a new actual-provisioning proposal is deferred;
the existing command templates remain unexecuted and require fresh approval
only after all resource floors pass.
