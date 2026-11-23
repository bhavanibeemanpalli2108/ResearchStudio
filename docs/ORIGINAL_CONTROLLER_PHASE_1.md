# Original controller lifecycle — offline Phase 1

2026-11-22, Asia/Calcutta. ISSUE-01/02 remain **partially resolved**;
ISSUE-03 creation and controls remain HTTP 409. No deployment, real provider
request, credential provisioning, original campaign or privileged change occurred.
The `reseon-native-v1.2.1` checkpoint and historical research are preserved.

## Implementation and limits

`src/research_platform/original_controller.py` provides an explicitly opt-in
trusted Python interface: `create`, `submit`, `snapshot`, `reconcile`, `pause`,
`resume`, `cancel`. `ControllerPolicy.enabled` defaults to false. This is offline
lifecycle integration, **not a newly running service or public submission API**.
No native queue dispatcher, LangGraph workflow, frontend launch or provider
selection has been replaced. Tests instantiate this interface against temporary
databases and mock HTTP transports with fake credentials.

Existing Run/Job/GatewayGrant/ModelUsage/WorkflowEvent/Artifact tables suffice;
no schema migration or extra database service is needed. New work includes:

- Canonical worker UUID ↔ platform hex identity, immutable request digest,
  idempotent exact run creation and rejection of identity collisions.
- Separate `original_*` Job statuses: native workers cannot claim or recover
  these jobs. Generic web controls reject original runs rather than enqueueing
  them for the native worker.
- Leased controller ownership and per-instance serialized controls. Another
  controller can reconcile only after the old lease expires. Terminal runs
  cannot restart. Native run/ledger state is never managed by this controller.
- Authenticated HTTPS capability checks require dedicated infrastructure,
  pinned image identity, run-scoped credentials and an accepted nested-budget
  capability before submission. The real worker deliberately still advertises
  `nested_call_budget_enforced=false`: configuration alone cannot prove egress
  enforcement. Mock capability success is not deployment acceptance.
- Atomic grant issuance and Run/Job/audit binding under the existing accounting
  lock. Only a token hash is in the database. A private, separate trusted-host
  escrow permits restart checks; raw scoped tokens are never artifacts/events.
- Authenticated private credential delivery to a canonical worker run. Gateway
  origin comes from worker operator configuration, never research input. Tokens
  must use the scoped format. Credential rotation requires an idle worker;
  same-token delivery is idempotent. POSIX files are owner-only, written through
  private temporary files, and unavailable through artifact APIs.
- Worker commands in `gateway_scoped` mode use that run's credential file and
  the existing isolated Gemini CLI profile. Legacy operator-managed mode stays
  default-off; its existence is not a budget enforcement claim.
- Grant expiry, revocation on stop/failure/control, request/run/model binding,
  controller lease checks and a fixed execution deadline. Reconciliation blocks
  new admissions until worker status is confirmed. Restart never silently renews
  grants or replays a submit POST.
- An explicit `x-reseon-request-id` (32 lowercase hexadecimal characters) maps
  deterministically to a ModelUsage primary key. Repeated identities return
  HTTP 409 without a second reservation or provider dispatch, across restarts
  and independent of optional audit retention. Without this header each attempt
  receives a fresh ID and consumes a separate slot. Identical prompts are not
  deduplicated. Failed/uncertain reservations remain charged. Required grant/
  request accounting audit links survive the optional diagnostic event cap.
- Stopped-worker cleanup must be verified before resume or completion import.
  Only existing allowlisted artifacts are collected into content-addressed
  storage. Their IDs/hashes link to the original run and lifecycle journal.
  Partial collection can be reconciled again without another campaign submit.
  Imported worker output remains worker evidence, not independent scientific
  verification of an original campaign.

## State and recovery contract

| Situation | Durable outcome and operator action |
| --- | --- |
| Created | Run queued, Job original_pending; no grant or model request |
| Submitted | Grant and intent committed, authenticated delivery then submit once; Run running / Job original_running |
| Proven pre-submit failure | Paused/not_submitted, grants revoked; explicit submit may retry without replaying an execution |
| Ambiguous submit response or controller crash after intent | Reconcile existing UUID; never automatically resubmit; pause/revoke on unavailable status |
| Controller restart | Wait for old lease expiry, reconcile HTTP status and escrow; no replacement grant for a running job; expired leases block gateway admissions |
| Pause/interruption | Revoke, request worker stop; resume only after verified stopped cleanup, same request and remaining budgets |
| Resume | Rotate scoped grant, keep absolute deadline and previous ModelUsage; at most three controller dispatch attempts in total |
| Cancel | Revoke before remote cancel; preserve cancel intent on disconnect; remain paused/unconfirmed until cleanup verified, then cancelled |
| Worker/gateway unavailable | No fallback provider, refund or automatic replay. Retain uncertainty; gateway admission requires current run, grant, lease and budget |
| Completion | Revoke before import; verify cleanup and artifact allowlist, collect hashes, mark terminal and release lease |

Phase 1 deliberately bounds the **entire execution window to one grant period**:
request runtime must be at most the Run runtime budget and policy grant duration
(default 300, maximum 900 seconds). Pause/restart time counts against this
conservative wall-clock window. Resuming never resets the controller or scoped
worker deadline. An expired window cannot obtain another grant. Longer campaigns
need separately reviewed renewal and resource/runtime acceptance; they are not
supported by this milestone. Grants normally expire slightly before the deadline
because remaining whole seconds are rounded down.

The default controller lease is 120 seconds; an eventual supervisor must reconcile
regularly before it expires. Operations use existing bounded HTTP timeouts.
There is no auto-start supervisor here. Revocation/expiry blocks **new** admissions;
already-dispatched requests can finish or remain uncertain and are never refunded.
Remote cancellation is not reported as verified cleanup when disconnected.

## Trusted persistence boundary decision

Use **one trusted Linux host**, its **local POSIX filesystem**, and the existing
SQLite database for the backend, original controller and Gemini gateway writers.
Use the existing transactional `BEGIN IMMEDIATE` admission lock and ModelUsage
primary keys. File-based transactions survive process restart without a new DB
framework. No direct cross-host SQLite access, SMB/NFS sharing or Windows/WSL
DrvFs dual writing is accepted. The constructor accepts SQLite for offline tests;
that does not attest the filesystem's real deployment locality or locking.

The disposable dedicated worker receives only authenticated HTTP management and
run-scoped gateway access. It receives **no database file, database credentials,
host directory mount, ledger permission or real provider key**. SQLite and token
escrow paths must not be mounted/exported into it. Worker root/container privilege
must not permit access to the trusted host. The existing actual dedicated-worker
and host-controlled egress contract remains mandatory.

Windows temporary-database tests validate logic, not production ACLs. Private
escrow owner/mode enforcement is POSIX; production Windows escrow is not accepted.
Keep the current Windows native application unchanged. A future coordinated
backend/database move to the trusted Linux host requires explicit approval,
consistent backups, stopping competing writers, restore/locking checks and a
tested rollback. Never point a new Linux gateway at the running Windows DB.

Escrow files are private and outside the downloadable ArtifactStore. On rollback
an orphan file can exist without a committed grant; it cannot authorize a model
request. Revoked escrow/journals are retained for now. Operator-approved retention
and garbage collection can remove only definitively revoked/expired scoped
credentials after recovery checks; never delete ModelUsage or refund uncertainty.

## Offline validation

Final verified results:

| Check | Result |
| --- | --- |
| Windows platform | **262 passed, 41 skipped, 4 deselected** |
| WSL Ubuntu platform + CLI/Inspector | **344 passed, 4 deselected** (303 platform + 41 CLI/Inspector) |
| New controller cases | **21 passed** on Windows and Linux |
| React/Vitest | **21 passed** |
| Chromium offline journeys | **6 passed**; no Docker/research program or real provider execution |
| Ruff lint / formatting | Pass; 56 Python files formatted |
| Linux-target mypy | Pass; 37 source files |
| TypeScript / production build / Prettier | Pass; existing large-bundle warning retained |
| Windows original CLI | Cannot collect: existing POSIX-only `fcntl` import; use WSL (passed there) |
| Historical evidence | Both database snapshots unchanged; 121 artifact files verified |

The four deselected cases are the genuine Docker research execution cases; no
new real experiment was authorized. POSIX/installed-CLI checks skipped on Windows
are covered in WSL. Offline acceptance does not establish deployed worker isolation
or genuine Gemini readiness.

Tests cover identity/collision, authenticated transport, readiness denial,
grant issuance failure, delivery failure, ambiguous submission, concurrent
controllers, request deduplication, expiry/revoke/deadline/lease enforcement,
concurrent call accounting, exhausted budgets, gateway timeout retention,
pause/resume/cancel/disconnect, controller/worker restart, missing escrow,
unverified cleanup, artifact rejection/recovery, native queue/web fencing,
historical native preservation, credential privacy and worker deadline refusal.

All research Docker/provider tests are excluded; mock CLI tests may start local
fixture processes but have no genuine key or public provider transport.

Executed checks from the existing repository (no dependency installation):

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -k 'not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline or selected)' -q --tb=short
.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m mypy --platform linux --follow-imports silent src/research_platform apps/research_platform/backend
.venv\Scripts\python.exe .research-platform/validation/release-v121/check_evidence.py
git log -1 --format=%H reseon-native-v1.2.1
git diff --name-only --cached
git check-ignore .env .research-platform/local-app/platform.db .venv apps/research_platform/frontend/node_modules
git diff --check
```

WSL combined platform/CLI/Inspector regression command:

```powershell
wsl -d Ubuntu -- bash -lc '. /home/sonusunny/.nvm/nvm.sh && cd /mnt/d/project/reseon/AI-Scientist-v3 && GEMINI_CLI_OFFLINE_TEST=1 /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/research_platform tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py --confcutdir=tests/research_platform -k "not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline or selected)" -q --tb=short'
```

From `apps/research_platform/frontend`: `npm.cmd run test`,
`npm.cmd run typecheck`, `npm.cmd run build`, `npm.cmd run format:check`.
Browser checks used this **fresh test-only** server/state, with no program/Docker
execution and mock scholarly responses:

```powershell
.venv\Scripts\python.exe tests/research_platform/offline_native_server.py --offline-boundary --mock-literature --state .research-platform/validation/original-phase1/browser-fixture --port 8012
# Separate frontend shell in apps/research_platform/frontend:
$env:PLATFORM_URL='http://127.0.0.1:5182'
$env:PLATFORM_FRONTEND_PORT='5182'
$env:RESEARCH_API_URL='http://127.0.0.1:8012'
$env:NATIVE_OFFLINE_E2E='1'
npm.cmd run test:e2e -- --workers=1
```

After browser completion, the server's PID/command line were verified and only
that fixture process was stopped. Existing native application services were not
reconfigured/restarted. Temporary evidence remains in ignored validation storage.

Attempting the combined platform/CLI command on Windows failed collection at
`src/orchestrator/state.py: import fcntl`. This is the existing POSIX original CLI
dependency, not a successful Windows CLI check. CLI tests are validated in WSL;
the Windows platform suite is run separately. No fake `fcntl` shim or unrequested
original-engine portability change was introduced. Other known warnings are the
existing LangGraph/websockets deprecations and frontend bundle-size warning.

Preservation check: both retained database row snapshots match the release
baseline; all **121 artifact files** match SHA-256/size. Native acceptance run
`42dd6acadbb54b17870c66ed6737215a` remains completed with 15 calls and snapshot
`bc82e0cd8ad70afc2b26c2f88fb326e0afd5417363d770aec73acd31f1d00f30`.
The release tag still resolves to `3a2eecef142a74394e5e093136c521af98750f6b`.
The index is empty; no secret, database, cache or generated artifact is staged.
No new commit/tag was requested or created for this phase.

## Exact repository changes

| File | Change |
| --- | --- |
| `src/research_platform/original_controller.py` (new) | Opt-in controller, private escrow, persistent coordination/recovery |
| `src/research_platform/model_gateway.py` | Transactional grant helper, deadline/lease fencing, request deduplication, critical audit retention |
| `src/research_platform/ledger.py` | Optional caller-supplied reservation identity; native default remains random |
| `src/research_platform/upstream_execution.py` | Scoped policy and authenticated credential delivery client |
| `src/research_platform/upstream_worker.py` | Private scoped delivery, run-specific environment/profile, non-resetting execution deadline |
| `apps/research_platform/backend/app.py` | Reject original web controls; preserve original create restriction |
| `deploy/upstream-worker/worker.env.example` | Empty optional gateway-origin setting; no secrets |
| `tests/research_platform/test_original_controller.py` (new) | 21 lifecycle/integration scenarios with fake services/temporary state |
| `tests/research_platform/test_upstream_worker.py` | Two additional POSIX credential/deadline tests |
| `docs/ORIGINAL_CONTROLLER_PHASE_1.md` (new) | This implementation, persistence, validation and deployment-boundary report |
| `docs/ORIGINAL_SAKANA_NEXT_MILESTONE.md` | Distinguish historical gaps from this implementation |
| `docs/ISSUE_01_REPORT.md` | Link follow-up, retain partial status |
| `docs/ISSUE_02_REPORT.md` | Link lifecycle/persistence follow-up, retain partial status |
| `docs/DEVELOPMENT_PROGRESS.md` | Current implementation and security/deployment boundary |

## Remaining blockers and approval boundary

1. Dedicated Linux worker/independent Docker daemon, effective cgroups, pinned
   image and cleanup/restart acceptance remain unprovisioned/unverified.
2. Trusted Linux backend/controller/gateway placement, private POSIX directories,
   TLS/CA/authentication and supervised reconciliation need deployment acceptance.
3. Host-controlled egress/forwarder policy must be installed and packet-tested
   from guest root and containers with a **mock** provider before advertising
   nested enforcement. Docker Desktop's normal socket is not compliant.
4. Gemini account/model free-tier eligibility and fail-closed genuine dispatch
   authorization are not established by native Groq approval. Do not provision
   real credentials or make a Gemini request under this task.
5. A real original campaign, paper generation and longer-window grant renewal
   remain unaccepted. Original web launch/controls stay disabled until ISSUE-01/02
   deployment acceptance and separately authorized campaign acceptance.

Explicit approval is required before package/KVM permission changes, VM or daemon
provisioning, cgroup/firewall/forwarder/systemd/TLS changes, trusted backend/data
cutover, real Gemini credential provisioning/requests, any original campaign, or
web enablement. No such operation was performed or is implicitly authorized here.
Hardware sizing remains the conditional 4-vCPU/6-GiB/64-GiB lab plan in
[the infrastructure assessment](ORIGINAL_SAKANA_NEXT_MILESTONE.md), with a fresh
memory/KVM feasibility check required before provisioning.
