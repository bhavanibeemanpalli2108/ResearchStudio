# Development checkpoint

## Current checkpoint — 2026-11-18

The native Mission-1 milestone is validated with two genuine studies. Full original
Sakana campaign acceptance remains blocked. This section supersedes the older
fixed-benchmark/environment status below; that history is retained for provenance.

- Scheduling run `e2dcc7048b654d0daef9ba68d5010079`: completed; FIFO 7292 versus
  generated SPT 5180 mean total completion time across three frozen seeds.
- Regression run `65742d40a84442a7b1fecedbee043d14`: completed; training-mean
  RMSE 1.567878058 versus generated OLS 0.475896318 across three frozen seeds.
- Both used real Groq `openai/gpt-oss-20b`, independent host evaluation, matching
  digest approvals, generated programs only in restricted Docker and final reports.
  Each used 14/20 calls with the original token/runtime/iteration budgets unchanged.
- Windows path publication, malformed structured output, synthesis truncation,
  missing/stale digest guards, native retry routing, stale approval UI cache and
  resumed provider identity were corrected with regressions. The regression
  proposal's unsupported feature-scaling claim was revised before approval.
- Independent weighted-duration/NumPy SVD audits verify all seed metrics,
  artifact hashes and real-provider source provenance. Six actual LangSmith spans
  were retrieved and checked for empty inputs/outputs; only safe metadata exported.
- Full platform suites: 133 passed on Windows compatibility SDKs; 133 passed in
  separate WSL Python 3.12/current locked SDKs, including real Docker tests.
  Upstream CLI/Inspector/task-drafting suite: 55 passed in WSL. Ruff, formatting,
  Linux-target mypy (28 sources), lock check and editor diagnostics pass.
- Native plan/ideas/selection/interpretation now use typed structured contracts
  and bounded section repair. Selection sees actual idea options and rejects
  foreign IDs; the historical fallback defect is recorded in acceptance evidence.
- Frontend: 11 React tests, 4 Chromium flows, type/build/format and all PDF-page
  visual checks passed. Browser test data is separate; an API-only instance reads the
  two completed live runs without a worker or provider requests.
- Original engine: doctor, parser compatibility and bounded dry-run exercised;
  no real campaign launched. Dedicated daemon/controller isolation and a nested
  coding-agent budget boundary are absent. Original web launch remains disabled.
- Current evidence and exact commands: [RESEARCH_ENGINE_ACCEPTANCE.md](RESEARCH_ENGINE_ACCEPTANCE.md).
  Native limits: [ARCHITECTURAL_CORRECTIONS.md](ARCHITECTURAL_CORRECTIONS.md).
  Local operation: [DEPLOYMENT.md](DEPLOYMENT.md).

No repository reset, research-data removal, credential change, billing change or
approved budget increase was performed. Changes remain uncommitted for review.

## Mission 1 continuation — 2026-11-17

- Reinspection: this checkout contains the original 70-test scoped implementation,
  not the later dynamic engine described in the mission's historical context.
  preparation.py, dynamic_execution.py, protocol-v2 worker implementation and
  ARCHITECTURAL_CORRECTIONS/UPSTREAM_WORKER/DEPLOYMENT documents were absent.
- Existing uncommitted work and all research data are preserved. Acceptance uses
  a fresh, timestamped directory under .research-platform/validation/.
- Docker29.9.2 and WSL2 Ubuntu are installed; Docker Desktop was stopped. Started
  the existing Desktop service; daemon and container checks are in progress.
- Gemini/Groq/LangSmith key presence verified without printing credentials.
- Reinstalled the already-documented compatibility SDK versions into .venv after
  Windows Application Control blocked the globally installed newest tracing DLL.
- Parallel work: strict staged preparation/providers; isolated dynamic execution
  with trusted evaluator; minimal UI integration and upstream CLI diagnostics.
- Root: protocol-v2 fence, existing graph/service integration, isolated live
  acceptance runner, testing, reporting and documentation.

## Completed
- Read attachment, clean Git status, full tracked-file inventory, upstream README,
  license, configs, Inspector and pipeline boundary inspection.
- Audit and architecture selected; upstream code preserved.
- Delegated independent workflow, provider/execution, and frontend work.
- Configured Python and installed actual LangGraph/checkpoint/tracing packages.
- Verified official compatibility versions import under Windows Application Control.

## Implemented and verified
- FastAPI REST/SSE, SQLAlchemy/Alembic, immutable artifacts and OpenAPI.
- Database jobs, independent worker, leases/fencing, bounded attempts, recovery.
- Real LangGraph, durable checkpoints and approvals, cancellation and pause.
- Provider discovery/routing, budgets, retries, OpenAlex cache and redacted traces.
- Docker-only curated CPU adapter, explicit demo fixtures, upstream result import.
- Connected React UI, all views, local Monaco, charts, downloads, themes/mobile.
- 70 Python tests; lint/format/mypy pass; frontend build/type/format pass;
  5 UI tests and 3 full browser tests pass.
- Full details and acceptance gaps: IMPLEMENTATION_REPORT.md.

## Decisions
- Separate new project lifecycle shell; preserve/link upstream Inspector.
- Demo fixtures clearly labeled; free mode real constrained CPU benchmark.
- Original engine launch stays trusted CLI; import results into platform read-only.
- Default SQLite, one durable worker; no Redis/Celery/cloud requirement.

## Verification commands
Use project Python `.venv/Scripts/python.exe`; Windows sandbox execution needs
the host's normal interpreter permission.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform --basetemp=.test-tmp-final -q
npm.cmd --prefix apps/research_platform/frontend run build
npm.cmd --prefix apps/research_platform/frontend test
.\.venv\Scripts\python.exe -m src.research_platform.dev --port 8001
```

Workspace http://127.0.0.1:5173; built SPA and API docs on 8001. Port8000 belongs
to an existing service and was left untouched. Start the stack before Playwright.

## External prerequisites
- Docker not detected; real experiment smoke test cannot run here yet.
- No runtime provider or LangSmith credentials supplied; use HTTP transport tests
  and tracing-disabled mode without sending external model requests.
- Current Rust serializers blocked by Windows Application Control. Use optional
  `requirements-platform-windows.txt` constraints for verified local runtime.
- Full upstream web launch requires isolated execution/budget infrastructure and
  remains disabled; trusted original CLI and Inspector are preserved.


## ISSUE-04 / ISSUE-05 final verification — 2026-11-20

This entry supersedes earlier runtime prerequisite gaps for these two issues.

- ISSUE-05 **resolved on WSL Ubuntu**: saved doctor JSON reports 13 OK, 7 warnings,
  0 failures using Linux Python 3.12.16. Node v26.13.1, npm/npx 11.20.0 and Gemini
  CLI 0.68.0 resolve natively under /home/sonusunny/.nvm/versions/node/v26.13.1/bin.
  Node satisfies >=22.18.0. Docker daemon and agent image are available. Unattended
  shells must explicitly source nvm; no optional CLI agents were installed.
- ISSUE-04 **resolved for Groq / openai/gpt-oss-20b** after explicit chat
  authorization. Exactly one discovery GET and one generation POST returned
  HTTP 200. Actual generated response: `OK`. Existing run
  e2dcc7048b654d0daef9ba68d5010079 used its existing ledger: 16/20 -> 17/20,
  with 75 input and 23 output tokens reported. Cost remains unknown/null.
  No retry, fallback, campaign, budget increase, historical result rewrite or
  experiment-artifact modification occurred. Run remains completed.
- Real persisted readiness displayed in Chromium and returned by the read-only
  readiness API. Refresh kept usage at 17/20 and made no provider requests.
- Validation: Windows platform 148 passed; existing Linux platform environment
  148 passed; current Linux 3.12 CLI suite 41 passed; frontend 13 passed; two
  actual Docker experiment tests passed. Build, TypeScript, Ruff and focused
  mypy checks passed. Added success/failure readiness UI regression cases.
- Current Python 3.12 environment lacks SQLAlchemy/LangGraph platform extras;
  full platform tests used the already-existing Linux 3.11 environment instead.
  Gemini API generation and other model combinations remain unverified.
- Full commands, accounting, screenshot and receipt locations are in
  [ISSUE_04_05_REPORT.md](ISSUE_04_05_REPORT.md). Existing unrelated services on
  ports 8000/5173 were left untouched; temporary read-only port 8876 was stopped.


## ISSUE-01 Phase 1 — 2026-11-20

- Status **partially resolved**: prepared dedicated guest deployment and verified
  software contracts; no VM/daemon installation or privileged host change made.
- Host inspection: Core Ultra 5 125H, 18 logical CPUs, 23.4 GiB visible RAM; Windows
  free RAM about 6.1–7.1 GiB during inspection. Docker Desktop is shared, uses
  /var/lib/docker and cgroupfs, and is explicitly rejected. WSL is not accepted
  as the dedicated controller. /dev/kvm exists but user access and QEMU are absent.
- Recommended conditional free local option: QEMU/KVM guest in existing WSL,
  4 vCPU / 6 GiB / private 64 GiB sparse disk, no workstation shares, SSH-only
  management, dedicated native daemon and bounded controller/container cgroup.
  Package/access/guest provisioning requires explicit approval and memory headroom.
- Reused upstream_worker.py: corrected nested slice path and controller placement,
  strengthened daemon identity/config checks, verified temporary-probe cleanup,
  rejected unknown stopped containers, added process locking and conservative
  offline recovery. Original campaigns now default disabled independently of
  capability service enablement. No hard nested-call budget is claimed.
- Added deploy/upstream-worker/ templates and guest-only operation/recovery runbook;
  no secrets supplied and no provider calls or original campaign executed.
- Linux full platform suite: **182 passed** on existing Python 3.12.16. Windows:
  **149 passed, 33 POSIX skips**. New worker contract suite: **33 passed**. Ruff,
  format, Linux-target mypy (28 files) and shell syntax checks passed. Current-host
  systemd verification remains incomplete because guest executables are absent;
  actual guest startup/cgroups/authenticated endpoint/recovery remain unverified.
- ISSUE-02 unchanged; original web launch remains HTTP 409 with a no-run-created
  regression. The prior completed native Groq run remains completed at 17 calls.
- Full file list, commands, evidence and approval scope:
  [ISSUE_01_REPORT.md](ISSUE_01_REPORT.md).


## ISSUE-02 gateway implementation — 2026-11-20

Status **partially resolved**. Added a run-scoped Gemini JSON/SSE gateway using
shared transactional ModelUsage reservations, hashed expiring grants, fixed
provider origin, bounded requests, conservative failure accounting and no replay.
Native lease checks remain required; completed/native runs cannot receive grants.
Migration 0002 adds only gateway authorization state; the live database remains
unmigrated at 0001. Completed native Groq history remains completed at 17/20,
with unchanged raw config/state hash and no spent remaining calls.

Installed Linux Gemini CLI 0.68.0 passed two actual CLI invocations against a local
mock provider: text and read-only function-call/response. Explicit gemini-api-key
mode accepts scoped tokens; fresh private profiles disable telemetry/statistics.
No real provider requests occurred. Observed requests were 31,704–32,141 bytes;
conservative input reservations can exhaust the unchanged 32k default on later
turns. Larger input budget exists only in synthetic compatibility fixtures.

Final validation: Linux platform **220 passed** (32 gateway unit cases, two CLI
mock cases and 37 POSIX worker cases included); Windows **181 passed, 39 skipped**;
separate CLI/Inspector **41 passed**. Ruff/format, Linux-target mypy (33 sources),
shell syntax and whitespace checks pass. Original HTTP 409 protection passes.

Prepared deployment templates and host-controlled network specification were not
installed or deployed. No QEMU/socat/VM/TLS provisioning, Docker Desktop changes,
provider-key access or campaigns. Actual VM egress, TLS trust, grant lifecycle and
PostgreSQL remain unverified. Worker nested_call_budget_enforced stays false and
original campaigns stay disabled. Full files, commands, evidence and limitations:
[ISSUE_02_REPORT.md](ISSUE_02_REPORT.md).


## First usable native application — 2026-11-20

Existing FastAPI/React/worker/Docker/approval/ledger/report components were retained.
Native defaults now select Groq/openai/gpt-oss-20b without remote discovery when
loading the form. Every Groq transport attempt requires a fresh 24h key-bound
operator Free-plan attestation. The user confirmed Free plan/no paid usage;
account billing is not remotely guaranteed. Existing .env/key were unchanged.
Optional literature failures warn and continue without fabricated citations.
Explicit frontend ports, occupied-port refusal, origin propagation, Linux venv
selection and POSIX child-group shutdown improve the existing launch procedure.

Windows API/worker/Vite started on 8010/5180 and remain available. WSL API/worker
plus built SPA passed health/HTML checks on 8014 and were stopped. Linux Vite
lacks Linux Rollup in shared Windows node_modules; no packages were replaced.

Validation: Windows **189 passed, 39 skipped**; WSL **228 passed**; frontend
**13 passed**; existing Chromium **4 passed**; new native Chromium **1 passed**
with actual Docker, mock provider, both approval gates and report export.
Two protocol API/worker/Docker integrations pass within platform totals. Ruff,
format, mypy, TypeScript, build, Prettier and shell syntax pass.

No real provider requests, installations, infrastructure changes or original
campaigns. Prior completed native run remains unchanged at 17/20. HTTP 409
protection passes. Fresh live Groq research awaits explicit authorization.
[Usage guide](LOCAL_APPLICATION.md) and
[exact changes, commands and limits](LOCAL_APPLICATION_REPORT.md).


### Authorized live native run — first approval gate, 2026-11-20

New run be08d9e5f154486ea8b1ff9eebce6882 received actual Groq/openai/gpt-oss-20b
responses and stopped at research_plan/awaiting_approval as requested. Usage
3/20 calls, 2,261 reported input/1,266 output tokens; cost null; zero experiments.
Read-only Chromium confirmed the live plan dialog. No approval was submitted.

Review identified unsupported 128-job proposal (contract allows 8–64) and a
contradictory difference sign. Recommended approval feedback uses 32 jobs, five
fixed seeds and FIFO-minus-SPT with ties explicit. Await human decision before
preparing the exact experiment and stopping at its second approval gate.
Prior completed run remains unchanged at 17/20; process-local attestation only,
no .env/key changes. Full evidence: LOCAL_APPLICATION_REPORT.md, live continuation.


### Authorized preparation — second approval gate, 2026-11-20

User-approved corrections reached the exact scheduling_v1 contract: 32 jobs,
durations 1–10, seeds [42,123,456,789,101112], FIFO baseline, independent frozen
evaluator. All 9 evaluator self-checks pass. Frozen success threshold is mean
FIFO-minus-candidate > 0.1 time units. One paired observation per seed; no extra
replications are represented by the executable spec. Resources: 1 CPU, 256 MiB,
64 PIDs, 10 seconds per isolated execution, no network or mounts.

Run be08d9e5f154486ea8b1ff9eebce6882 awaits its second digest-bound approval:
9/20 calls, 8,953 input/2,954 output tokens, cost null, candidate/program null,
zero experiments. Final digest:
e79b03b5fb8bb4b704eaedb111acb9a56ad4415dee63f141894d394f3cd4edd0.
Prior completed history remains unchanged at 17/20. No second approval submitted.
Full evidence and remaining acceptance: LOCAL_APPLICATION_REPORT.md.


### Authorized live native study completed — 2026-11-20

Run be08d9e5f154486ea8b1ff9eebce6882 completed after explicit approval of the exact
frozen digest at both gates. Groq generated stable SPT ordering. Actual Docker
history verifies 10 creates, 10 exit-0 events and 10 removals: five FIFO/SPT pairs.
One experiment completed, no failed attempts or execution errors. Approved spec,
model, limits, dataset and digest remained unchanged. Mean completion time:
FIFO 2662.4, SPT 1962.4, improvement 700.0 (> approved 0.1). Five seed results
are retained in LOCAL_APPLICATION_REPORT.md. Exact sign-flip p=0.0625; no 5%
significance or general scientific validity is claimed.

Final ledger: 13/20 calls, 13,589 input/4,402 output tokens, unknown/null cost,
26.94 active seconds. No provider switch, paid fallback or budget increase.
Report generated; completed UI, measured experiment view and Markdown export
verified read-only. Draft still quotes superseded initial plan/replication prose;
that presentation limitation is flagged separately without modifying evidence.
Previous completed native run remains unchanged at 17/20. Original campaigns stay
disabled. No source changes or extra provider requests were needed for audit.

## Reseon native Research Studio v1 — 2026-11-20

Native reports now share a deterministic renderer for workflow generation and a
read-only API presentation. Approved spec/final digest and trusted measurements
come first; superseded plan/idea text is explicitly historical. Unverified model
claims remain in source artifacts. Original immutable reports/state are unchanged;
frontend preview and Markdown export match. Missing presentation fails visibly.

Independent retained-output audit recalculates all five seed metrics, mean
improvement 700.0, exact sign-flip p=0.0625 and Student-t interval using numerical
integration. All 22 artifact hashes/sizes and state/ledger snapshot are unchanged.
No experiment rerun or real provider request; completed budgets remain 13/20 and
17/20. Existing original-engine HTTP 409 protection still passes.

Fixed the terminal-status polling race that could leave experiment/artifact lists
empty after completion. Suppressed HTTP transport INFO logs that could expose
credential-bearing URLs. Added built-index startup guard. Sidebar name is Reseon;
removed the Personal workspace placeholder card per user request.

Windows platform: 192 passed, 39 skipped, 4 Docker cases deselected. WSL: 231
passed, 4 deselected. Separate CLI/Inspector: 41 passed. Frontend: 16 passed;
all five Chromium journeys passed with offline process/provider boundaries.
Ruff/format (50 files), mypy (35 sources), TypeScript, build, Prettier, shell
syntax and whitespace checks pass. Four existing Docker-executing tests were
preserved but not rerun; no additional research campaign was launched.

Windows API/worker/frontend remain on 8010/5180. WSL built-SPA startup/health and
normal shutdown verified on an isolated temporary workspace; fixture services
stopped afterwards. Local single-user native scope is usable. Remaining deployment,
billing-attestation, synthetic-science and dependency limits remain explicit.
No source commit/tag created. Recommendation: reviewed commit followed by annotated
local tag reseon-native-v1.0.0; see [checkpoint report](RESEARCH_STUDIO_V1.md).
