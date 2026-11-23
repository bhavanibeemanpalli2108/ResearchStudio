# Development checkpoint

## Authorized GH013 history correction — 2026-11-23

The owner authorized a targeted rewrite after GitHub rejected a synthetic Slack
redaction fixture in upstream history. A verified external bundle and full Git
metadata copy preserve the original 16 commits and all release objects. Cleaned
history changes only that fixture in historical trees, preserves the destination
LICENSE commit verbatim and retargets all three annotated tags with their names,
descriptions and tagger dates intact. Two invalidated upstream merge signatures
were removed from cleaned objects; originals remain in the recovery copy.

The test still exercises complete credential-shaped input against the unchanged
checkpoint scanner. No GitHub bypass or scanner suppression was added. A final
tip-only formatting cleanup is AST-identical. Historical research evidence,
application code and budgets remain unchanged. Private backup/Codex refs are not
selected for publication. Full old/new commit and release mappings, verification
gates and signature details: [GH013 recovery report](GH013_HISTORY_REPAIR.md).
Older entries below retain their original commit references intentionally.
Post-rewrite results: checkpoint/redaction suites 194 passed; native platform/
CLI/Inspector 347 passed with four real Docker cases excluded; frontend 21 passed.
Ruff, formatting, Linux-target mypy, TypeScript/build/Prettier and full Git
integrity pass. Main and the three release tags have zero original Slack-value
or Slack-pattern hits and zero unreviewed/configured credential matches. Other
matches remain reviewed synthetic redaction fixtures (16 across reachable blob
versions after tip formatting, including three duplicate fixture values). Both retained database
snapshots and all 121 artifact files remain unchanged. Publication proceeds only
through a normal non-force push with GitHub protection still enabled.

## GitHub publication preparation — 2026-11-23

Destination: `https://github.com/bhavanibeemanpalli2108/ResearchStudio.git`.
Fetched GitHub main `77bddd3289e2c99e0a2d6df09fbd4180a30c2ad8` is already an
ancestor of local main; no unrelated-history merge or force push is required.
Phase 1 commit e8b9e27 and the three native release tags remain preserved.

Pre-publication inspection scanned all 15 currently reachable commits and 756
unique blobs (approximately 19 MB), commit/tag metadata and pending source/docs.
No private/runtime paths or configured secret values were found. Fourteen
credential-pattern matches and nine assignment candidates were reviewed as
synthetic upstream redaction-test fixtures (ordered canary strings, dummy proxy
credentials and an incomplete dummy private-key payload), not genuine secrets.
No credential validation/provider request was made. No established secret scanner
was installed in Windows or WSL; this used a local full-blob audit and structural
review, without printing credential values or installing tools. No automated
scanner can guarantee absence of every possible unknown secret format.

Strengthened Git exclusions for private `*.env`, key material, SQLite sidecars
and personal credential/config files. Source templates remain tracked. Actual
research state, caches, runtime outputs and private audit reports stay local and
ignored. Fresh WSL platform/CLI/Inspector checks: 347 passed, four real-Docker
cases excluded; Ruff lint/format and Linux-target mypy pass. Windows's previously
reported SQLAlchemy App Control blocker was not bypassed. Publication is attempted
only after reviewed staging and a final history audit; this entry records
preparation, not a claim that an unverified push succeeded.

## Original engine Phase 2 deployment readiness — 2026-11-23

Reviewed and committed exactly 14 Phase 1 source/test/template/doc files as
`e8b9e27531fa4f15ee6f07fa1585dfeac0861742`. Configured-secret/runtime exclusions
and staged diff checks passed; all release tags remain unchanged. Fresh WSL
platform/CLI regression: 344 passed/4 genuine-Docker cases deselected. Both
retained database snapshots and 121 artifact files remain unchanged.

Read-only hardware check: Windows available RAM approximately 9.59–10.81 GiB,
latest commit headroom approximately 10.82 GiB; WSL memory is overlapping, not
additional. Native nested KVM exposure exists but current user lacks kvm GID991
access (EACCES). QEMU is absent. Desktop is stopped/unreachable; it was not
restarted. CPU/disk are adequate for a conditional 4-vCPU/6-GiB/64-GiB lab, but
normal-workload memory and actual accelerated KVM must pass before provisioning.

Added only optional TLS certificate/key arguments to the existing worker launcher,
retaining the exclusive controller lock; three offline tests cover TLS forwarding,
disabled campaigns and incomplete configuration refusal. Targeted WSL checks now
97 passed. No certificates, service configuration or sockets were created by these
launcher tests. No native frontend/workflow/provider change was made.
Final WSL full platform/CLI/Inspector suite after TLS correction: 347 passed,
4 genuine-Docker cases deselected. Ruff lint/format (56 files), mypy (37 sources)
and Git whitespace checks pass. The runbook mock gateway block was validated with
an in-process ASGI boundary: exactly 20 dispatches/rows, request 21 HTTP403,
duplicate after restart HTTP409, no real sockets/provider/VM traffic. Packet/TLS
and deployed recovery acceptance remain pending.

Current Windows Python regression collection is blocked by Application Control
rejecting SQLAlchemy's `_row_cy` DLL. No policy bypass or package reinstall was
attempted. Prior Windows test results are historical; current Linux verification
remains passing. No host/VM/provider changes or original campaigns occurred.
ISSUE-01/02 remain partial and original web launch/controls remain HTTP 409.

Resource facts, exact next approval, risks and rollback:
[Phase 2 readiness](ORIGINAL_PHASE_2_READINESS.md). Ordered mock-first deployment
and security checks: [acceptance runbook](../deploy/upstream-worker/ACCEPTANCE.md).

## Original engine offline controller lifecycle — 2026-11-22

Added the default-off original controller using existing Run/Job/GatewayGrant/
ModelUsage/event/artifact persistence: UUID/request identity, dedicated queue
fencing, authenticated worker readiness/submission and per-run credential
delivery, bounded grants/deadlines, cancellation, interruption/restart recovery,
duplicate dispatch/reservation protection and safe artifact import. Native web
controls now explicitly reject original runs. Original creation remains HTTP 409.
No new database/schema/framework or native research dispatcher was introduced.

The trusted production boundary is one Linux host/local POSIX SQLite for backend,
controller and gateway; the disposable worker gets HTTP only and no ledger/key
access. No Windows/WSL cross-filesystem production sharing is accepted. Deployment,
Gemini free-policy/credential readiness and host-controlled egress acceptance are
still required. ISSUE-01/02 remain partial and ISSUE-03 disabled. No provider call,
original campaign, infrastructure change or release tag modification occurred.

Implementation, recovery behavior, test commands/results, limitations and approval
requirements: [Phase 1 report](ORIGINAL_CONTROLLER_PHASE_1.md).
Final checks: Windows platform 262 passed/41 skipped/4 deselected; WSL combined
platform and CLI/Inspector 344 passed/4 deselected; React 21 and Chromium offline
journeys 6 passed. Ruff, formatting, mypy (37 sources), TypeScript/build/Prettier
pass. Windows original CLI collection remains unavailable due to its existing
POSIX `fcntl` dependency; its 41 tests pass in WSL. No portability shim was added.
Both retained DB snapshots and 121 artifact files match the release baseline;
native acceptance remains at 15 calls. Release tag/commit is unchanged.

## Native release freeze and original-engine next milestone — 2026-11-22

Local release checkpoint: `reseon-native-v1.2.1`, created only after reviewed Git
staging, configured-secret/exclusion checks, revalidated native evidence and passing
Windows/WSL/frontend/browser checks. Existing v1.0/v1.1 tags and scientific evidence
remain unchanged; no push, provider request, original campaign or privileged host
change belongs to this release task.

Fresh inspection: 23.43 GiB Windows RAM, approximately 5.85–7.85 GiB free during
checks, below the reviewed 9-GiB available-RAM target before starting a 6-GiB guest.
CPU vmx and kvm_intel nested=Y are exposed, but /dev/kvm access fails errno 13
for the current user. No QEMU/native Ubuntu dockerd found. Docker Desktop is shared
and noncompliant for the dedicated original-worker contract.

ISSUE-01 and ISSUE-02 remain partially resolved; ISSUE-03 remains blocked/HTTP 409.
Existing worker/gateway code is not deployed enforcement. Next work is trusted
run/grant lifecycle and database placement, approved dedicated deployment, actual
egress/accounting packet tests with mocks, then a separately authorized genuine
Gemini readiness check. Only after ISSUE-01/02 acceptance should original CLI
campaign/paper and default-off API/frontend integration proceed.
Hardware, exact gaps, approval operations, rollback and issue acceptance criteria:
[ORIGINAL_SAKANA_NEXT_MILESTONE.md](ORIGINAL_SAKANA_NEXT_MILESTONE.md).

## Reseon v1.2.1 — live acceptance passed, 2026-11-22

After explicit authorization of both gates, NEW run
`42dd6acadbb54b17870c66ed6737215a` completed the exact approved scheduling_v1
contract with genuine Groq/openai/gpt-oss-20b source and ten successful isolated
Docker executions (five paired seeds). Actual candidate is stable SPT sorting.
FIFO mean 2853.8, SPT mean 2095.4, mean improvement 758.4 >0.1; exact two-sided
sign-flip p=.0625, so no 5% significance claim. One iteration/one experiment only.

Final accounting: 15/20 completed calls, 10,924 reported input/4,576 output tokens,
no uncertain reservations. Limits unchanged at 40k input/16k output/300 active
seconds; active use ~26.28 seconds, cost unknown/null. No provider/cleanup/execution
errors or post-first-gate schema repairs; initial failed-schema responses retained.

Independent read-only audit verifies all five genuine measurement pairs, 26 artifact
hashes, program/approval/dataset/grounding identities, statistics and ledger totals.
Docker daemon evidence records ten exit-code-0 containers and cleanup leaves none.
The cited final report displays in the real frontend and Markdown export matches
the server byte-for-byte. Full selected source/provenance remains unchanged.

The previous paused run and both historical completed runs remain untouched; no
budgets reset or reused. Original Sakana launch restrictions remain. Offline tests
still pass as recorded below; no extra campaign or API request is needed for audit.
Completed evidence snapshot:
`bc82e0cd8ad70afc2b26c2f88fb326e0afd5417363d770aec73acd31f1d00f30`.
Actual results, scope and remaining limits:
[RESEON_V1_2_1_LIVE_ACCEPTANCE.md](RESEON_V1_2_1_LIVE_ACCEPTANCE.md).

## Reseon v1.2.1 — second gate ready, 2026-11-22

The user approved first-gate preparation for run
`42dd6acadbb54b17870c66ed6737215a` with explicit mean-improvement/statistical
corrections. Preparation completed through the existing worker with six additional
completed calls, 4,562 reported input/1,143 output tokens, zero new provider errors
or repairs. Total 11/20 calls; 7,916 input/3,410 output charged; 32,084 input/12,590
output and nine calls remain. All limits and full source provenance are unchanged.

All nine analytical evaluator selfchecks passed, the five seed cases are committed,
and preparation/spec/baseline/grounding/final digest identities independently verify.
Final second-gate digest:
`2b59be4e2cc62f8acb85297bea17e6a39426e0229242fa9631fa8c9a48b16d2d`.
Strict mean FIFO-minus-SPT >0.1 is separate from the exploratory exact sign-flip
p-value. An AI idea still mentions median in advisory historical text; the frozen
evaluator does not compute one and no median result is claimed.

No candidate source, Docker execution, experiment or live research report exists.
The run is awaiting the separate digest-bound second approval. Historical/paused
runs remain unchanged. Full contract, all validation cases and per-request
reservation/usage evidence: [RESEON_V1_2_1_SECOND_GATE.md](RESEON_V1_2_1_SECOND_GATE.md).

## Reseon v1.2.1 provider reliability — 2026-11-22

Offline reliability work complete; live v1.2 acceptance remains incomplete.
No external API request or research execution was made in this task. Preserved
the paused 060988269faf4d1dbfde7a362b4718fb run and both completed runs byte-for-byte
across run/ledger/artifact metadata/experiment/decision/event snapshots.

Native prompts now use bounded unique abstract excerpts for planning/ideation and
stable references later. Full provenance and approved hypotheses/constraints stay
intact. Schemas transmit once without annotations; application validators remain
unchanged. Native HTTP defaults to one uncertain attempt, while existing bounded
same-model schema compatibility/repair stays accounted. Typed context and timeout
diagnostics never expose request bodies or credentials. Atomic request-budget
events retain original estimates after completion; pre-dispatch checks protect
candidate/evaluation/report capacity and never raise existing limits.

Retained specification estimate projects 10,120 -> 7,530 (-25.6%). A full mocked
selected-paper flow charged conservative input bytes and completed at 13 calls,
26,520 estimated input and 11,648 output caps under 20/32k/16k. These are offline
projections, not live savings or scientific results. The old uncertain HTTP causes
remain unknowable from retained evidence; 9/20 and 29,923/32k remain unchanged.

Final validation: Windows 241 passed/39 skipped/4 deselected; WSL 280 passed/
4 deselected; WSL CLI/Inspector 41 passed; React 21 passed; Chromium 6 passed.
TypeScript/build/Prettier/Ruff and Linux-target mypy (36 sources) pass. Research
Docker cases excluded; mock transports and process stubs used. No new dependencies,
providers, infrastructure, protocol, migration or original campaign activation.
Existing local API/worker/frontend reloaded with generation blocked, not resumed.

Proposed fresh live acceptance: Groq/openai/gpt-oss-20b, one retained paper,
scheduling_v1, both approvals, NEW 20-call/40k-input/16k-output/one-iteration/
one-experiment/300-second limits; no change to old budgets. Await explicit
authorization and current Free-plan confirmation before any real request.
After separate explicit authorization/confirmation, NEW run
`42dd6acadbb54b17870c66ed6737215a` reached its first human gate: 5/20 completed
calls, 3,354 reported input/2,267 output tokens, no uncertain reservations or
provider failures. Feasibility/planning each used one retained bounded schema
repair. The live plan cites the actual selected DOI. It remains awaiting first
approval, with a requested correction separating descriptive positive-seed counts
from exact sign-flip p-values. No candidate, experiment, final digest or live report
exists; historical/paused runs are untouched. Live acceptance remains incomplete.
Exact changes, stage analysis, commands and caveats:
[PROVIDER_RELIABILITY_V1_2_1.md](PROVIDER_RELIABILITY_V1_2_1.md).

## Reseon v1.2 literature-grounded integration — 2026-11-22

Preserved reviewed v1.1 in commit `fffd4c9` and annotated local tag
`reseon-native-v1.1.0`; v1.0 tag remains unchanged. No secrets, databases,
generated evidence or caches were staged; nothing was pushed. V1.2 is uncommitted
for review. This section records the latest native application status; earlier
milestones below retain their historical scope.

Selected metadata/excerpts now survive the native prompt compaction path into
planning, ideation and preparation. Typed hypotheses/ideas must reference actual
selected IDs; rationale and the experiment hypothesis are linked explicitly.
A content-hashed source/hypothesis manifest is retained as an artifact and bound
to the final human approval digest, dataset and prepared design. Candidate work
and execution reject changed grounding. Unselected/historical approval digests,
budgets, evaluator restrictions and original campaign HTTP 409 are preserved.

Reports separate retrieved source metadata/excerpts, unverified AI interpretation
and trusted measurements/statistics. They retain the approved contract and DOI
references. Citation links open in the frontend and exports match server Markdown;
measurement-table preview handles blank-separated retained rows. No original
report or completed scientific evidence was rewritten.

Validation: Windows platform 222 passed/39 skipped/4 deselected; WSL platform
261 passed/4 deselected; WSL CLI/Inspector 41 passed; frontend 21 passed;
full Chromium suite 6 passed, plus 1 final grounded-flow browser recheck after the
table preview correction. TypeScript, production build, formatting, Ruff and
Linux-target mypy (35 platform/backend sources) pass. Actual Docker-running tests
were deliberately excluded; scholarly/model/process boundaries in integrations
are mocked. The existing build chunk/dependency deprecation warnings remain.
Initial shell initialization/default-platform check failures and their fixes are
documented rather than concealed.

Live metadata validation: one three-result query, exactly two keyless public GETs,
OpenAlex 200/Crossref 200; one actual abstract, no fabricated missing abstracts or
source warnings. The first paper studies quadratic lateness; native total-flow-time
experiments would be related-method checks, not reproduction of that paper.
Offline implementation/tests made no Groq/Gemini requests or Docker campaigns.
After explicit authorization and fresh Free-plan confirmation, NEW live run
`060988269faf4d1dbfde7a362b4718fb` reached its first gate with real Groq responses
and the exact selected DOI in its hypothesis. The user approved preparation with
pairing/statistical clarifications. It then paused safely at `experiment_spec`:
9/20 calls (seven completed, two uncertain reserved attempts), 9,683 reported input /
2,664 output tokens; 29,923/32,000 input reservations leave 2,077 capacity. No
candidate, contract, final digest, experiment or live research report exists; the
second gate was not reached. Reservations and budgets remain intact. Initial
HTTP/transport failure statuses were not retained, so no specific quota/API cause
can be claimed. Added safe per-attempt failure events, validated with three offline
regressions, without retrying the live run or changing retry/accounting rules.
The existing Docker Desktop app was started after daemon unavailability; no
installation, reconfiguration or pull. No historical call budget was consumed.

Historical scheduling audit retains snapshot `f1407818736521ad9fb6140da6edf5b3b56646e86c60e18d916eba9c61a41e77`,
22 verified artifacts and 13 calls. Older completed run remains at 17 calls with
its config/state hash unchanged. Existing local launcher starts API, worker and
Vite; frontend http://127.0.0.1:5180/literature and health
http://127.0.0.1:8010/api/health returned HTTP 200. The application was restarted
with generation blocked after the preparation pause. The authorized live run and
existing unrelated waiting research remain idle. Live end-to-end acceptance is
partial; deterministic offline complete-workflow acceptance passed.

Exact files, commands, evidence, usage and limitations:
[LITERATURE_GROUNDED_RESEARCH_V1_2.md](LITERATURE_GROUNDED_RESEARCH_V1_2.md).

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


## Reseon v1.1 literature discovery — finalized 2026-11-22

Preserved v1 with tree-identical checkpoint commit 66713db and annotated local tag
reseon-native-v1.0.0 before implementation; no tracked local state or configured
secrets found, no history rewritten or push performed. Extended the existing
LiteratureClient/httpx boundary with public OpenAlex/Crossref retrieval, DOI/stable
ID deduplication, genuine source abstracts, cache, bounded requests and rate-limit
cooldowns. Added Literature navigation/page and explicit paper selection/review.

New runs resolve selected snapshot IDs against server-side content hashes and
retain metadata/provenance in existing config/state plus a source artifact/event.
Selected context grounds the existing ideation stage without new retrieval; source
text is untrusted and cannot establish findings or novelty. Optional retrieval
outages preserve the existing native workflow. No database migration or framework.

Recorded November 20 live retrieval: both public endpoints returned HTTP 200;
five-result query had three abstracts; actual default browser query returned ten
papers with six abstracts and no source warnings. Bounded to two scholarly GETs
per uncached query; no keys, paid endpoints or model generation. Live queries were
not repeated during the November 22 continuation.

Final checks: Windows platform 206 passed/39 skipped/4 deselected; WSL 245 passed/
4 deselected; frontend 19 passed; browser suite covers six journeys including
selected citation provenance at the native ideation gate. Ruff/mypy, TypeScript,
production build and formatting pass. Docker-executing tests were excluded; all
external test responses and model/process boundaries are mocked.

Completed evidence remains unchanged at 13/20 and 17/20 calls. Original Sakana
campaign HTTP 409 remains. No generation, research campaign, VM or MCP integration
was added. Details, exact files, usage and limitations:
[LITERATURE_DISCOVERY_V1_1.md](LITERATURE_DISCOVERY_V1_1.md).
