# Original engine Phase 2 — deployment readiness

**Phase 2A update, 2026-11-23:** the owner completed the authorized QEMU installation
and kvm-group configuration. Native binaries and actual read/write device access
are independently verified. The separately authorized 128-MiB diskless KVM probe
succeeded once at 11:55:52 local time: QMP commands passed, exit 0 in 0.113 seconds,
no stderr or remaining probe process. Full-guest memory headroom currently fails
the earlier floors; Phase 2B remains unapproved. See the current
[Phase 2A readiness report](ORIGINAL_PHASE_2A_READINESS.md). The installation-absent
and commands-not-executed statements below are retained as the earlier dated
assessment, not the current installation status.

Assessment: **2026-11-23, Asia/Calcutta**. This is preparation, not deployment
acceptance. No package, group, VM, genuine credential, firewall, system service or
virtualization setting was installed/changed. Docker Desktop was not started.
No genuine provider request or original campaign occurred. Original web launch
and controls remain HTTP 409. ISSUE-01/02 remain **partially resolved**.

## Phase 1 preservation

Reviewed and committed the exact 14 Phase 1 files as:
`e8b9e27531fa4f15ee6f07fa1585dfeac0861742`
(`Complete offline original-engine controller and grant lifecycle`).
The staged index was checked for configured secret values without displaying
them, private environment files, key patterns, databases, caches, virtual
environments and generated/runtime paths. Exactly source/tests/templates/docs
were staged. The index was clean after the commit. Nothing was pushed or tagged.

All existing tag objects are unchanged:

- `reseon-native-v1.0.0`: `14e31676de116c4b95b395806a077e26d0fc08d2`
- `reseon-native-v1.1.0`: `30c44c51b1176ca29777bbdee1be43275c98941d`
- `reseon-native-v1.2.1`: `cc81711711c51a22dfa9e2c3fbb83cc3bcaa1d99`
  (release commit remains `3a2eecef142a74394e5e093136c521af98750f6b`).

Read-only preservation audit: both retained database row snapshots match the
release baseline; **121 artifact files** match SHA-256 and size. Native run
`42dd6acadbb54b17870c66ed6737215a` remains completed with 15 model calls and audit
snapshot `bc82e0cd8ad70afc2b26c2f88fb326e0afd5417363d770aec73acd31f1d00f30`.
No historical model budget was used, reset or refunded.

## Actual environment

| Item | Read-only observation |
| --- | --- |
| Shell / repository | Windows PowerShell; existing `D:\project\reseon\AI-Scientist-v3` |
| CPU | Intel Core Ultra 5 125H, 18 logical CPUs |
| Windows physical RAM | 23.43 GiB total |
| Windows available RAM | Counter samples approximately **9.59–10.81 GiB**; latest saved sample 10.81 GiB |
| Windows commit | Latest 14.11 / 24.93 GiB, approximately **10.82 GiB commit headroom**; first sample approximately 10.11 GiB headroom |
| Hypervisor | Windows `HypervisorPresent=True`; WSL exposes vmx/VT-x and EPT |
| WMI virtualization fields | Report False while the Microsoft hypervisor is active; these fields do not overturn the observed WSL vmx exposure. Actual KVM initialization is still untested |
| Ubuntu | WSL2, Ubuntu 26.04.1, kernel `6.18.58.1-microsoft-standard-WSL2` |
| WSL memory | MemTotal approximately 11.40 GiB, MemAvailable approximately 10.49 GiB; swap 3 GiB. **Not extra Windows RAM** |
| WSL configuration | No user `.wslconfig`; `/etc/wsl.conf` enables systemd and selects sonusunny. Root cgroup has no additional finite memory/CPU/PID cap |
| Nested virtualization | `/sys/module/kvm_intel/parameters/nested` = Y |
| KVM access | `/dev/kvm` exists root:kvm, GID 991, mode 0660. UID 1000 is not a member of kvm. Read/write access false; read-only open returns errno 13/EACCES |
| QEMU / native dockerd / socat | Absent in Ubuntu PATH; qemu-system-x86 and qemu-utils report not installed |
| Physical free storage | Latest C: approximately 276.26 GiB; D: approximately 496.36 GiB |
| WSL backing storage | Ubuntu ext4 VHDX resides on C:. Its approximately 948-GiB virtual filesystem free space is **not** additional physical capacity |
| Docker Desktop | Context desktop-linux, distribution stopped; named-pipe daemon connection fails. No successful live daemon inspection is claimed |
| Linux Docker command | Resolves to Desktop-provided Windows-side installation path; no independent native Ubuntu daemon is present |

Private read-only inventory/review evidence is retained under ignored
`.research-platform/validation/phase2-20261123/`. `docker info --format` returned
empty/error metadata when the pipe was absent; that output is not daemon readiness.

WSL's documented default memory limit is 50% of Windows RAM and the nested
virtualization setting defaults to enabled on supported Windows 11 systems.
These are configuration defaults, not proof of successful guest acceleration:
[Microsoft WSL configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).
No WSL settings or Windows features need changing based on current evidence.

## Feasibility and allocation

**Conditionally feasible as a small infrastructure lab; not ready to provision.**
CPU and physical storage support the proposed **4 vCPU / 6 GiB / 64 GiB sparse
disk** guest. KVM's immediate observed obstacle is permissions, rather than absent
device/module/CPU exposure. QEMU and native guest acceleration remain untested.
Do not substitute TCG/software emulation: QEMU can otherwise default/fall back
to software acceleration; require KVM explicitly and fail on initialization error.
[QEMU accelerator documentation](https://www.qemu.org/docs/master/system/invocation.html).

Do not add WSL available memory to Windows available memory: they overlap.
Starting a 6-GiB guest grows demand in the same physical/commit pool. Plan roughly
6 GiB guest plus 0.5–1 GiB QEMU overhead and approximately 0.5–1 GiB trusted
mock gateway/controller headroom; these are estimates to measure, not guarantees.
An 8-GiB QEMU/forwarder service ceiling bounds exceptional host-side growth.
The trusted services must have separate finite limits; do not rely on guest limits
to bound host forwarding processes.

The earlier 9-GiB available-Windows-RAM floor is currently met under **light load**,
with Docker Desktop stopped. Prefer 10–12 GiB available, at least 8 GiB commit
headroom and approximately 8.5 GiB available inside WSL immediately before boot.
Recheck with the user's normal native services running and obtain a stable sample.
If the floors fail, stop; do not automatically stop apps, resize WSL or increase
swap. Simultaneous native Docker research plus the guest has not been accepted.

Existing guest limits: research service/controller + containers **2 CPU equivalents,
4 GiB, zero swap, 1024 PIDs**; independent dockerd **1 CPU, 768 MiB, zero swap,
512 PIDs**. About 1.25 GiB guest OS/other margin remains at maximum configured
usage. This supports infrastructure probes, not an assurance that a full original
research/paper workload fits. Reserve at least approximately 90 GiB physical
space for a disk that can grow to 64 GiB, staging images and logs, and monitor
actual C: consumption; no 948-GiB virtual-free-space assumption.

If accelerated nested KVM or memory headroom fails, prefer a separate Linux host
meeting the same contract. An independently isolated Linux VM outside WSL avoids
nested KVM but still competes for laptop RAM and needs separate hypervisor
approval. A second WSL distro or renamed Desktop socket is not equivalent isolation.

## Small repository readiness correction

Phase 1 is committed separately. Phase 2 adds optional `--tls-cert`/`--tls-key`
arguments to the existing worker launcher and passes them to its existing Uvicorn
server **inside the original exclusive controller lock**. Partial TLS arguments
fail before serving. Proxy headers and access logging are disabled. Three offline
tests verify this without sockets, certificates or campaigns.

This closes the launcher mismatch with OriginalController's strict HTTPS check.
Do not use a bare `uvicorn --factory` replacement that bypasses controller_lock.
An authenticated HTTP-over-SSH development capability check is still possible,
but it does not satisfy the controller's authenticated_https capability.
TLS deployment/trust/handshake acceptance is still pending.

## Exact next approval and sequence

**No following command has been executed.** The smallest useful approval is:

1. In the existing WSL Ubuntu, install only QEMU system-x86/utils and add the
   existing user to the existing kvm group:

   ```bash
   sudo apt-get update
   sudo apt-get install --no-install-recommends qemu-system-x86 qemu-utils
   sudo usermod -aG kvm sonusunny
   ```

   Review apt's proposed changes; stop on removals/conflicts with existing
   components. Do not install dockerd in the normal WSL distribution. Group access
   grants device privileges; do not make /dev/kvm world-writable. Re-enter a fresh
   Ubuntu login and verify effective groups without `wsl --shutdown`.

2. If separately included in that approval, perform a **diskless, paused 128-MiB
   KVM initialization probe** (this creates a temporary VM, no disk/OS/network):

   ```bash
   id
   test -r /dev/kvm && test -w /dev/kvm
   printf '%s\n' '{"execute":"qmp_capabilities"}' '{"execute":"query-status"}' '{"execute":"quit"}' |
     timeout 10 qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 1 -m 128 \
       -nodefaults -display none -S -qmp stdio
   ```

   Require exit 0, successful QMP replies and no KVM initialization error.
   A failed probe stops the local path; no emulation fallback or BIOS changes.

3. **Separate later approval**: recheck normal-workload memory/disk headroom,
   select/verify an official guest ISO or cloud image checksum, create a new
   private 64-GiB disk, provision a native Linux guest, stage reviewed source and
   a pinned image, install guest-only Docker/systemd policies, transport/TLS
   credentials and test-only gateway/host-forwarder resource policies. Exact
   commands and fail criteria: [deployment acceptance runbook](../deploy/upstream-worker/ACCEPTANCE.md).
   Package/VM approval does not include real Gemini secrets or campaigns.

4. Run all actual guest, TLS, packet, 20/21-call, concurrency, revocation,
   cancellation, cleanup/restart and artifact checks against local mock upstream
   transport. Use a new local Linux acceptance DB; never the Windows research DB.
   Record evidence before considering either issue's deployed acceptance.

5. Only after mock deployment acceptance, request a **separate** genuine Gemini
   project/model/free-tier attestation, private-key provisioning and one bounded
   generation request authorization. Current Groq approval does not authorize
   Gemini. Unknown cost stays null, monetary-cap refusal remains, and a Free plan
   cannot be independently guaranteed from public documentation. No original
   campaign or web enablement follows automatically.

## Risks and rollback

- Memory/commit or growing ext4/qcow2 storage can affect Windows/native services.
  Stop probes at resource thresholds; shut down only the new guest gracefully.
- KVM access and a Docker-group-equivalent guest account grant broad privilege
  within their boundaries. Guest root is assumed untrusted relative to the trusted
  host; host-controlled egress and no filesystem/socket shares are mandatory.
- Wrong socket/data-root, DNS/IPv6/proxy bypass or unbounded host socat processes
  invalidate acceptance. Do not weaken checks or flip nested enforcement flags.
- TLS/secret paths and the trusted database must remain outside the worker.
  No cross-host or Windows/WSL dual SQLite writers; no existing backend cutover
  under this approval. New acceptance storage is isolated from native evidence.
- Windows SQLAlchemy DLL App Control currently blocks fresh Windows backend-test
  collection. No policy bypass, DLL replacement or package reinstall was attempted;
  existing services were not restarted. Address this separately before relying on
  a Windows backend restart. Linux tests provide current regression evidence.

Rollback after future approved work: revoke test grants, stop only new trusted
gateway/forwarder/worker units, verify the guest research cgroup and dedicated
daemon are empty, then shut down the guest gracefully. Preserve the disk,
journals, ledger and uncertain reservations. Do not prune Desktop, delete research
evidence, refund uncertain calls or restore over newer data. Remove kvm membership
with `sudo gpasswd -d sonusunny kvm` only if this deployment added it and no other
workload relies on it; re-login afterward. Review package reverse dependencies
before any optional apt removal; never use blanket autoremove. No rollback action
is necessary now because no host deployment change occurred.

## Verification record

Before the Phase 1 commit: WSL combined platform/CLI/Inspector **344 passed,
4 genuine-Docker cases deselected**; worker/controller/gateway/installed mock CLI
subset **94 passed**. Ruff and Linux-target mypy (37 sources) pass.
Windows attempted controller/gateway/API collection failed at SQLAlchemy `_row_cy`
with "An Application Control policy has blocked this file"; this is not a pass.
The previously recorded Windows 262-pass result remains historical, not a current
claim. No system policy/dependency was changed to mask this failure.

After the optional worker TLS correction: targeted WSL subset **97 passed**,
including the three new launcher tests. Final WSL platform/CLI/Inspector suite:
**347 passed, 4 genuine-Docker cases deselected**. Ruff lint/format (56 files),
Linux-target mypy (37 sources) and `git diff --check` pass. No frontend/native
workflow code changed; the prior frontend results are not claimed as fresh runs.

All four Python runbook blocks parse. Its actual mock-server block was executed
with Uvicorn replaced by an in-process ASGI test boundary, fresh Linux temporary
state and fake credentials: exactly 20 dispatches/rows, request 21 HTTP403,
repeated request ID after restart HTTP409, unchanged 20 rows/dispatches. There was
no listening socket, TLS handshake, real provider or VM involved in this bench
validation. TLS packet/guest checks have **not** been executed. Local
MockTransport tests are not VM egress proof.

Reproduction commands executed from the existing repository:

```powershell
wsl --list --verbose
Get-CimInstance Win32_OperatingSystem
Get-CimInstance Win32_Processor
Get-Counter '\Memory\Committed Bytes','\Memory\Commit Limit','\Memory\Available Bytes'
Get-PSDrive -PSProvider FileSystem
docker context show
docker info --format '{{json .}}'
.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m mypy --platform linux --follow-imports silent src/research_platform apps/research_platform/backend
wsl -d Ubuntu -- bash -lc '. /home/sonusunny/.nvm/nvm.sh && cd /mnt/d/project/reseon/AI-Scientist-v3 && GEMINI_CLI_OFFLINE_TEST=1 /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/research_platform tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py --confcutdir=tests/research_platform -k "not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline or selected)" -q --tb=short'
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3 && /home/sonusunny/.local/share/agsci-mission1-venv/bin/python .research-platform/validation/release-v121/check_evidence.py'
git diff --cached --check
git commit -m "Complete offline original-engine controller and grant lifecycle"
git show-ref --tags
```

The private inventory, staged-content comparison and runbook-validation scripts
are ignored local validation evidence, not product dependencies or staged runtime
artifacts. Their JSON reports expose classifications/hashes, not API keys.

Phase 2 working-tree files (not part of the Phase 1 commit, not staged):

- `src/research_platform/upstream_worker.py`: optional TLS CLI arguments.
- `tests/research_platform/test_upstream_worker.py`: three offline TLS cases.
- `deploy/upstream-worker/ACCEPTANCE.md`: new ordered acceptance procedures.
- `docs/ORIGINAL_PHASE_2_READINESS.md`: this resource/approval/result report.
- `deploy/upstream-worker/README.md`: current assessment/source-staging links.
- `deploy/upstream-worker/GATEWAY.md`: trusted placement/acceptance link.
- `docs/DEVELOPMENT_PROGRESS.md`: commit, tests, limitations and next gates.
