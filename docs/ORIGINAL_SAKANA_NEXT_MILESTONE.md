# Original Sakana integration after Reseon native v1.2.1

Assessment: 2026-11-22. Scope: release verification and a plan only. No QEMU,
guest, privileged configuration, real Gemini request or original campaign was
started. Original web launch remains HTTP 409. Existing native services, evidence,
credentials, virtual environments and Docker Desktop configuration are preserved.

## Native release boundary

Release tag: `reseon-native-v1.2.1`, created locally only after reviewed staging,
secret/exclusion checks and passing tests. Resolve the release commit with:

```powershell
git show --no-patch reseon-native-v1.2.1
```

The release includes the previously uncommitted v1.2/v1.2.1 literature grounding,
approval binding, report presentation, provider diagnostics, compact prompts,
protected token capacity and their tests/documentation. It adds this assessment;
it does not enable original-engine execution. Previous tags are not overwritten
and nothing is pushed.

Revalidated live native evidence, without another model call or experiment:

- Run `42dd6acadbb54b17870c66ed6737215a`: completed, real Groq SPT candidate,
  one scheduling experiment, ten Docker executions, five paired seeds.
- Mean FIFO/SPT completion times 2853.8/2095.4, improvement 758.4 >0.1,
  exact sign-flip p=.0625; no 5% significance claim.
- 15/20 completed calls, 10,924 reported input / 4,576 output, cost null.
- Independent audit verifies all 26 artifacts, measurements, statistics, approval,
  source/dataset identities and ledger; snapshot remains
  `bc82e0cd8ad70afc2b26c2f88fb326e0afd5417363d770aec73acd31f1d00f30`.
- Read-only release audit also hashes all run/ledger/artifact/experiment/decision/
  event/project rows in both retained application databases and verifies **121
  artifact files**. No data is migrated, resumed, reset or rewritten.

Release checks: Windows platform 241 passed/39 skipped/4 deselected; WSL platform
280 passed/4 deselected; WSL CLI/Inspector 41 passed; React 21 passed; Chromium
six offline journeys; TypeScript/build/Prettier/Ruff and Linux-target mypy
(36 sources) pass. Real Docker research cases are excluded from reruns. Existing
build chunk-size and dependency deprecation warnings remain. Detailed commands
and scientific evidence: [live acceptance](RESEON_V1_2_1_LIVE_ACCEPTANCE.md),
[reliability validation](PROVIDER_RELIABILITY_V1_2_1.md).

## What exists, and what remains

The dated implementation reports remain historical:
[ISSUE-01](ISSUE_01_REPORT.md), [ISSUE-02](ISSUE_02_REPORT.md),
[issue register/ISSUE-03](../issues.md), [worker contract](UPSTREAM_WORKER.md),
[engine acceptance](RESEARCH_ENGINE_ACCEPTANCE.md),
[architecture](ARCHITECTURAL_CORRECTIONS.md).
There is no separate ISSUE_03_REPORT.md. Native success does not close these issues.

| Area | Completed repository work | Remaining acceptance work |
| --- | --- | --- |
| Dedicated worker, ISSUE-01 | upstream_worker/upstream_execution; authenticated capability/status/control/dry-run/artifact APIs; dedicated-daemon identity/cgroup checks; private journals, process lock, cleanup and restart fencing; deployment units/runbooks | No dedicated Linux guest/controller/daemon has been provisioned. Prove real effective cgroups, socket/data-root separation, authentication, immutable image, cleanup and interrupted-worker recovery. Desktop remains unsuitable. |
| Gemini gateway, ISSUE-02 | model_gateway.py, gateway_client.py, GatewayGrant migration, owner-only POSIX key loader, TLS requirement, fixed Google endpoint, JSON/SSE and scoped CLI profiles | No trusted gateway/TLS deployment or genuine-credential generation readiness accepted. Windows ACL key loader is not implemented; select a supported trusted-host placement first. |
| Nested budgets, ISSUE-02 | Existing ModelUsage ledger, atomic run/daily/token admission, scoped/expiring/revocable grants, cancellation/SSE/uncertain retention; concurrent cap tests; installed CLI text/tool tests with fake keys | Integrate actual controller run creation and UUID binding, grant issuance/delivery/renewal/revocation with campaign lifecycle. Validate shared accounting and every real nested/helper caller in the intended deployment. |
| Network egress, ISSUE-02 | gateway_network.py plus JSON policy; QEMU restrict/forward arguments and CA image template; negative policy fixtures | These are specifications, not installed filters. start-vm.sh currently blocks all outbound access and does not yet apply the prepared gateway forward. Deploy host-controlled policy, bound forwarder processes and packet-test bypass denial from guest root/containers. |
| Campaign lifecycle | Strict request/Hydra command builder, UUID/idempotency checks, one active job, bounded phases, stop/resume, once-only final-evaluation handling and artifact allowlist | End-to-end trusted orchestrator linking platform Job/Run, worker journal and GatewayGrant is absent. Actual original campaign phases and recovery have not been accepted. |
| FastAPI/frontend, ISSUE-03 | Existing run/job/event/approval views and APIs, original client methods, read-only upstream import/artifact support | full_research creation is deliberately rejected; original adapter is not wired into launch. Add an existing-queue dispatcher/control/event/artifact mapping only after ISSUE-01/02 proof, behind a default-off guard. |
| Original paper workflow | Pipeline phases and src/scripts/paper.sh/paper_edit.sh, evidence/manifest/review/finalization helpers, bounded paper phase and fixed paper.pdf/paper.tex artifact exports | No accepted original paper execution. Verify image TeX/figure dependencies, real citations/retained scientific evidence, all paper/helper calls through the gateway, and compile/export without general guest internet. Native Markdown success is not original PDF acceptance. |

Important code-level gaps that infrastructure alone will not fix:

- UpstreamRunRequest still requires `nested_budget_policy=operator_managed` and
  `nested_budget_approved=true`; worker capability/job records still explicitly
  report `nested_call_budget_enforced=false`. Add a reviewed gateway-enforced mode
  bound to verified deployment policy and run/grant identity. Never just flip a
  boolean or equate a gateway URL with prevention of bypass.
- Gateway grant issuance accepts an existing running original/full_research run;
  current web creation cannot create one. A trusted, opt-in controller path must
  establish that record and the worker canonical UUID/platform hex mapping while
  the web guard remains closed. Reuse existing Run/Job/GatewayGrant tables.
- Grants expire in at most 900 seconds; the worker's campaign allowance can be
  longer. Implement bounded just-in-time renewal/revocation tied to active state,
  pauses, completion and restart. Do not use a long-lived real key inside the worker.
- The gateway has no Gemini account/model free-tier verification equivalent to
  native Groq attestation. Establish explicit fail-closed authorization for the
  chosen Gemini project/model before genuine dispatch; Groq confirmation does not
  apply to Gemini. Preserve null cost and existing monetary-cap refusal.
- Current gateway launcher requires a trusted POSIX host. Native production state
  is presently served by Windows. Cross-OS SQLite writers on the DrvFs workspace
  have not been accepted. Choose a reviewed same-host backend/gateway writer
  topology and validate it, rather than assuming shared path means shared atomicity.
  A coordinated, backed-up move of the existing backend/accounting to trusted Linux
  is one option; a separately reviewed Windows ACL key loader is another. No new
  database service is required or proposed, and no cutover occurs in this task.
- Installed-CLI mock evidence contained ~31.7k/32.1k-byte initial/tool payloads.
  A native 32k-input budget cannot be assumed sufficient for a multi-turn original
  campaign. Measure full phase/helper context with mocks first, then propose an
  explicit fresh-run budget. Never increase existing run limits to fit a campaign.

## Current laptop feasibility — actual read-only observations

| Resource | Observation |
| --- | --- |
| CPU | Intel Core Ultra 5 125H, 14 cores, 18 logical processors; Windows hypervisor present |
| Windows RAM | 23.43 GiB visible; available samples during release checks approximately 5.85–7.85 GiB |
| WSL memory/swap | ~11.40 GiB visible, ~10.16 GiB available at inspection; 3 GiB swap |
| Storage free | C: ~278.75 GiB; D: ~496.37 GiB |
| WSL distributions | Ubuntu and docker-desktop running, both WSL2 |
| CPU/KVM exposure | vmx present; kvm_intel nested=Y; /dev/kvm exists root:kvm, mode 0660 |
| Effective KVM access | UID 1000, not in KVM GID 991; Python os.access denies read/write; read-only open fails errno 13. No VM or accelerator was created. |
| Native QEMU/dockerd | Neither found in the inspected Ubuntu PATH |
| Linux controls | systemd PID1; cgroup v2 cpu/memory/pids controllers present |
| Desktop daemon | Name docker-desktop, /var/lib/docker, cgroupfs, cgroup v2; not a dedicated worker daemon |
| User .wslconfig | Not present; no setting changed |

The immediate KVM obstacle is permissions, not evidence that CPU virtualization
support is absent. Permission repair would not itself prove successful KVM guest
initialization. A shell exit-status echo was ambiguous, so the assessment relies
on direct Python access/open checks saved as local read-only evidence.
Microsoft documents nested virtualization as a Windows 11 WSL2 setting, default
true; device/module observations still do not prove guest acceleration works:
[WSL configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

Conditional free local lab allocation remains **4 vCPUs, 6 GiB RAM, private 64 GiB
sparse disk**, with no host drives/socket/device shares. Existing templates bound
controller plus research containers to 2 CPU equivalents, 4 GiB RAM, zero swap,
1024 PIDs; dockerd separately has 1 CPU, 768 MiB, 512 PIDs. Allow approximately
1.25 GiB of the guest for OS/other overhead at the maximum configured workloads.
Trusted host gateway/forwarder and QEMU overhead require additional headroom.

CPU and disk look adequate for this lab allocation; **current free Windows memory
is below the previously reviewed 9 GiB pre-start target**. Do not provision/start
the guest under this load. Recheck after the operator makes headroom, without
stopping applications automatically. This is infrastructure-test sizing, not a
guarantee that full original research/paper workloads fit. Profile bounded tasks
before proposing larger limits.

If memory headroom or accelerated nested KVM cannot be established, consider an
independently isolated Linux VM outside WSL or a separate Linux host with the same
worker contract. A VM outside WSL avoids the nested-WSL dependency but still competes
for laptop RAM; a separate host avoids that local memory pressure. Both require
approved hypervisor/network provisioning. Do not silently substitute
unaccelerated QEMU: QEMU defaults can use TCG, so the existing launcher explicitly
requires KVM and stops on failure. See [QEMU accelerators](https://www.qemu.org/docs/master/system/invocation.html).

## Minimal ordered next milestone

1. **Freeze native v1.2.1 and choose deployment topology.** Keep the release tag,
   current evidence and default-off original guards. Decide trusted backend/DB/
   gateway placement and worker location before provisioning; document backups,
   effective filesystem locking and rollback. No Windows/Linux dual writer shortcut.
2. **Finish trusted lifecycle glue offline.** Reuse upstream client/worker, shared
   ledger and GatewayGrant. Add controller run/UUID binding and gateway-enforced
   request/capability mode, per-job secret delivery and bounded grant lifecycle.
   Add Gemini free-plan/model authorization policy and stop/restart tests. Keep
   campaigns/web disabled; mocks and fake credentials only.
3. **After separate infrastructure approval, accept ISSUE-01.** First test KVM
   acceleration under the permitted user, then provision the reviewed guest and
   independent daemon. Install the existing units/policy, stage pinned tools/image,
   use private directories and authenticated SSH tunnel/capabilities. Demonstrate
   effective resource limits, Desktop rejection, bounded dry-run and cleanup/restart.
   Do not provide a real provider key to this guest.
4. **Deploy and packet-test ISSUE-02 with a mock upstream.** Trusted gateway stays
   outside the guest. Apply the prepared restrict=on policy plus fixed TLS forward
   (not an unrestricted Docker Desktop bridge), with bounded host-side socat.
   Pin/verify the public CA in the agent image; never disable TLS verification.
   Prove direct providers/DNS/raw IPv4/IPv6/metadata/host services/socket bypasses
   fail from guest root and containers. Test valid gateway access, invalid tokens,
   revoke/expire/restart and 20 admitted versus rejected request 21, including
   concurrency. Use temporary/new acceptance state; never spend native budgets.
5. **Request one genuine Gemini readiness authorization.** Confirm current model
   eligibility and project Free plan, provision the real key privately only on the
   trusted gateway, then propose one exact-model/output-bounded call through the
   installed CLI and gateway ledger. No retry/provider switch. Record actual
   response, accounting and network boundary; stop if unsupported or potentially
   billable. The current task does not authorize this call.
6. **Only after ISSUE-01/02 acceptance, prepare a separately approved bounded
   original CLI campaign.** Inventory all phase/helper/compression/paper model calls
   and allowed models. Reuse the existing task_drafting → investigation → ablations
   → once-only final_evaluation → posthoc → paper lifecycle. Define one small CPU
   task, exact fresh budget and failure/recovery checkpoints, then request approval.
   Validate genuine scientific provenance and original paper compilation/export.
7. **Then implement ISSUE-03 using existing API/frontend components.** Add a
   default-off capability-gated original dispatcher, persistent upstream identity,
   grant lifecycle, status/event/control/artifact mapping and approvals to the
   existing durable Job/Run flow. Continue returning 409 until deployment evidence,
   budget enforcement and explicit launch authorization are valid. Test failures
   and native regressions before any guarded opt-in release. No new queue/framework.

Paper/reference retrieval must not force a general network exception: upstream
paper scripts include citation-enrichment calls and TeX/figure preparation. Stage
reviewed dependencies and source metadata offline or reuse trusted platform
literature retrieval outside the guest with a narrow audited handoff. Inventory
each actual caller; an environment base URL alone does not prove all phases use
the gateway. Unsupported calls/phases remain blocked rather than bypass accounting.

QEMU documents that restrict=on blocks general guest routing while explicit
forwards remain possible; the deployed deny policy must therefore be packet-tested
and every allowed forward reviewed:
[QEMU user networking](https://www.qemu.org/docs/master/system/invocation.html).
Gemini limits depend on project/model/tier and apply per project, not per key;
native Groq Free-plan verification does not establish Gemini eligibility:
[Gemini rate-limit policy](https://aistudio.google.com/docs/rate-limits).

## Acceptance criteria and status

| Issue | Current status | Required closure evidence |
| --- | --- | --- |
| ISSUE-01 | Partially resolved; deployed infrastructure blocked pending approval/headroom | Real dedicated Linux controller/daemon/socket/data root; effective controller/container cgroups and aggregate limits; private auth/storage; immutable image; authenticated capability/dry-run; Desktop rejection; no leftovers after stop; restart/interruption fencing and non-destructive recovery. A native run or mock daemon does not count. Original campaign acceptance remains a separate downstream check. |
| ISSUE-02 | Partially resolved; ledger/gateway/CLI mocks pass | Trusted external key/TLS service, supported authoritative DB topology, genuine scoped CLI path and fresh account/model authorization; all nested/helper requests counted atomically; no direct-egress/key/socket bypass in actual guest tests; request 21 blocked at a 20-call cap; concurrent/retry/cancel/expire/revoke/restart cases preserve charges; effective capability attests enforcement. Model discovery or static destination_allowed tests alone do not count. |
| ISSUE-03 | Blocked and disabled | ISSUE-01/02 accepted first; original CLI lifecycle and genuine evidence accepted; existing API/worker/frontend mapping tested; missing prerequisites still return 409 without creating a run; explicit approvals/budgets/provenance persist across controls/restart; original PDF/TeX/manifests open/export; native functionality remains passing. Enable only under separate explicit authorization. |

## Operations requiring explicit approval — none performed

Host package/KVM proposal from the existing runbook:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends qemu-system-x86 qemu-utils
sudo usermod -aG kvm sonusunny
# Only if the reviewed gateway network route is chosen:
sudo apt-get install --no-install-recommends socat
```

Separately approve: verified guest image download/private disk creation; guest
packages and root-owned Docker/systemd/cgroup policy installation; image loading/
CA derivative build; TLS/CA/SSH key provisioning; host gateway/forwarder service and
resource policy; any existing-state/backend cutover or migration; private genuine
Gemini key provisioning; the exact live readiness request; a later original
campaign; and eventually original web enablement. No blanket approval is inferred.

No BIOS/Windows feature/WSL resource change is currently justified by the evidence.
If later needed, stop for a concrete separately reviewed change. Do not chmod
/dev/kvm world-writable or shut down WSL/Docker Desktop to apply settings silently.

Rollback after an approved deployment: stop only the new gateway/worker/forwarder/
VM, revoke grants, verify processes/cgroups/containers empty and retain journals
and uncertain ledger rows. Disable the new guest units without touching Desktop.
Shut the guest down gracefully and preserve its disk pending review. Restore any
coordinated backend cutover from its consistent backup only with no concurrent
writers; never overwrite newer research evidence or refund uncertain requests.
Remove the added KVM membership only if it was introduced for this deployment and
after verifying no other workload depends on it. Keep original launch disabled.

Runbooks to extend, not replace: [dedicated worker](../deploy/upstream-worker/README.md),
[gateway](../deploy/upstream-worker/GATEWAY.md). No infrastructure change is
requested or implied by creating the native release checkpoint.
