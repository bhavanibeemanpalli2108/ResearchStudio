# Execution issues and obstacles

Prepared: 2026-11-20. Original campaign checkpoint: 2026-11-18.
ISSUE-01 infrastructure preparation was rechecked on 2026-11-20; see
[ISSUE_01_REPORT.md](docs/ISSUE_01_REPORT.md). Later ISSUE-04/05 verification is
recorded in [ISSUE_04_05_REPORT.md](docs/ISSUE_04_05_REPORT.md); older entries below
retain their historical context.

This register is based on [DEVELOPMENT_PROGRESS.md](docs/DEVELOPMENT_PROGRESS.md)
and its linked acceptance, architecture and deployment records. It records
documented findings; services, credentials and live campaigns were not rechecked
for this documentation update. Older progress entries are historical where the
2026-11-18 checkpoint supersedes them.

## Current execution status

Native Mission 1 passed with two genuine Groq/Docker studies: scheduling and
synthetic regression. Each completed within its original 20-call budget, using
14 calls. The latest record reports 133 platform tests passing on each of Windows
and WSL, 55 upstream CLI/Inspector/task-drafting tests, 11 React tests and four
Chromium flows. These results establish the bounded native milestone.

Full original Sakana campaign acceptance remains **blocked**. No real original
campaign phases completed in this mission. Docker installation, parser checks,
doctor output and a bounded dry-run do not establish original campaign execution.

Source: [acceptance status](docs/RESEARCH_ENGINE_ACCEPTANCE.md#acceptance-status).

## Open issues and blockers

### ISSUE-01 — Dedicated original-engine execution infrastructure is absent

- **Status / priority:** Partially resolved / critical for original campaign execution.
- **Phase 1 evidence (2026-11-20):** Dedicated deployment templates and worker
  contract tests are prepared. Ordinary Docker Desktop and the current WSL
  controller are rejected. No dedicated guest has been provisioned; host changes
  await explicit approval. See [ISSUE_01_REPORT.md](docs/ISSUE_01_REPORT.md).
- **Cause:** The ordinary workstation Docker daemon does not meet the recovered
  worker contract. A dedicated native Linux controller, separate Docker socket
  and data root, finite cgroup limits, private credentials and authenticated
  transport have not been provisioned as a compliant deployment.
- **Impact:** The original coding-agent campaign cannot be accepted under the
  required isolation boundary. The recovered standalone worker code alone does
  not establish a deployed worker.
- **Next action:** Provision the dedicated controller/daemon, verify effective
  resource limits, tool/image readiness, transport and cleanup/recovery behavior.
- **Closure evidence:** A deployed worker passes its capability checks and a real
  bounded campaign produces retained execution evidence after ISSUE-02 is handled.
- **Sources:** [original-engine gap](docs/RESEARCH_ENGINE_ACCEPTANCE.md#original-engine-gap),
  [worker contract](docs/UPSTREAM_WORKER.md#recovered-dedicated-worker-contract).

### ISSUE-02 — Nested coding-agent requests bypass the platform budget ledger

- **Status / priority:** Partially resolved / critical for original campaign execution.
- **Implementation evidence (2026-11-20):** Run-scoped Gemini gateway reuses atomic
  ModelUsage accounting, with expiring hashed credentials, retained failure
  reservations and no automatic replay. Installed CLI 0.68.0 passed text and tool
  SSE tests using fake credentials/local mock provider; no real provider calls.
- **Validation:** Linux platform 220 passed; Windows 181 passed, 39 skipped;
  separate CLI/Inspector 41 passed. A 20-call run cannot dispatch request 21,
  including concurrent requests. Completed native history remains at 17/20.
- **Remaining boundary:** The dedicated VM/gateway/host egress policy is not
  deployed or packet-tested. Legacy operator-managed mode is not hard-budget
  enforcement; worker capability still reports nested_call_budget_enforced=false.
- **Next action:** After infrastructure approval, validate trusted key placement,
  TLS, grant lifecycle and shared DB plus actual VM direct-egress denial and
  exhaustion/restart behavior. Keep original campaigns/web launch disabled.
- **Closure evidence:** Both gateway accounting and provider bypass prevention
  demonstrated in the intended isolated deployment. Mock or static policy tests
  alone do not establish closure.
- **Sources:** [ISSUE_02_REPORT.md](docs/ISSUE_02_REPORT.md),
  [gateway runbook](deploy/upstream-worker/GATEWAY.md).

### ISSUE-03 — Original-engine web launch is disabled and not integrated

- **Status / priority:** Blocked / high for the full web workflow.
- **Cause:** The recovered upstream client and worker are not wired into web
  campaign submission. Worker isolation and nested-budget prerequisites remain
  incomplete.
- **Impact:** `full_research` creation returns HTTP 409. Users cannot launch a
  full original campaign from the UI/API; the preserved CLI, Inspector and result
  importer remain separate capabilities.
- **Next action:** Resolve ISSUE-01 and ISSUE-02, then integrate submission,
  capability checks, events, cancellation/resume and artifact retrieval.
- **Closure evidence:** Validate a real campaign through the integrated lifecycle,
  including failure/recovery behavior and imported evidence. Keep launch disabled
  until the prerequisites pass.
- **Sources:** [execution identities](docs/ARCHITECTURAL_CORRECTIONS.md#execution-identities-and-supported-scope),
  [original campaigns](docs/DEPLOYMENT.md#tracing-and-original-campaigns).

### ISSUE-04 — Provider discovery does not establish generation availability

- **Status / priority:** Observed external dependency issue / high when affected.
- **Observed breakdown:** Discovery listed `gemini-2.5-flash`, but generation
  returned HTTP 404 for the recorded account/endpoint. Scheduling completed only
  after an explicit switch to Groq `openai/gpt-oss-20b`. No later successful
  generation with that Gemini account/model is established by the cited record.
- **Impact:** A discovered model can stop execution. Failed or uncertain requests
  retain budget reservations; retries and repairs can exhaust the remaining cap.
  Account quota, pricing and free-tier eligibility remain external dependencies.
- **Next action:** Verify the chosen account/model's generation capability within
  the existing budget. Record any explicit alternative selection and preserve
  usage reservations; do not infer zero cost from unknown pricing.
- **Closure evidence:** A successful generation request for the affected
  account/endpoint, or a recorded decision to use a working alternative.
- **Source:** [requests, failures and accounting](docs/RESEARCH_ENGINE_ACCEPTANCE.md#requests-failures-and-accounting).

### ISSUE-05 — WSL host Node readiness was incomplete at the last doctor check

- **Status / priority:** Last recorded environment gap / medium; current state
  needs rechecking.
- **Cause:** Host Linux `node` was absent. Windows npm/npx interoperability did
  not constitute a complete Linux Node installation, so `agsci doctor` exited 1.
- **Impact:** The original WSL toolchain was not fully ready, despite Docker,
  Python, Git and the agent image passing their recorded checks. Native studies
  subsequently completed, so this is not a general native execution blocker.
- **Next action:** Install or verify a native Linux Node runtime in the intended
  controller environment and rerun doctor there.
- **Closure evidence:** Doctor confirms host toolchain readiness; separately
  retain the infrastructure and budget requirements above.
- **Source:** [doctor findings](docs/UPSTREAM_WORKER.md#doctor-and-bounded-command-preview).

## Remaining scope and acceptance gaps

These limit supported use or stronger acceptance claims; they do not invalidate
the completed native milestone.

| Gap | Impact | Work needed |
| --- | --- | --- |
| Only two trusted native protocols | Genuine execution supports small synthetic regression and single-machine scheduling. Unsupported questions stop at feasibility; generated programs use approved standard-library dependencies. | Add independently evaluated protocols and explicitly reviewed dependency support before expanding scope. |
| Original research phases unvalidated together | Real task drafting, investigation, ablations, sealed final evaluation, post-hoc analysis and manuscript generation have not completed together under a real coding agent. | After the blockers are cleared, retain evidence from a real bounded original campaign. |
| Limited scientific evidence | Both native studies used three paired seeds and exact two-sided sign-flip p-values of 0.25. Results do not establish significance, novelty or broad generalization. Literature retrieval supplies metadata rather than full-text claim verification. | Review scientific claims, verify supporting literature and design additional studies before making stronger claims. |
| Public and multi-user operation unavailable | The service is single-user and loopback-only. Host/origin checks provide no user authentication or tenant isolation. Public production hosting is unvalidated. | Implement authentication/authorization, tenancy, TLS, execution isolation and process supervision, then validate the intended deployment. |
| Shared storage deployment unvalidated | Acceptance uses SQLite and local checkpoints/artifacts. PostgreSQL deployment and distributed checkpoint/artifact storage are not established. | Validate the intended storage, backups, migrations and restart recovery before relying on shared or distributed operation. |
| Manuscript and collaborative editing limits | Native reports are immutable Markdown with browser Print/PDF export. Original manuscript generation remains in the blocked original campaign; browser draft edits are local. | Validate the original manuscript workflow and implement server-side draft persistence if required. |

Sources: [supported scope](docs/ARCHITECTURAL_CORRECTIONS.md#execution-identities-and-supported-scope),
[study evidence](docs/RESEARCH_ENGINE_ACCEPTANCE.md),
[deployment boundaries](docs/DEPLOYMENT.md),
[implementation limitations](docs/IMPLEMENTATION_REPORT.md#mission-1-validated-continuation--2026-11-18).

## Operational obstacles that can recur

| Condition | Execution effect | Existing handling / follow-up |
| --- | --- | --- |
| Docker daemon stopped, reviewed image missing or unsupported dependencies requested | Genuine native execution stops. | Preflight the daemon/image; provision reviewed images explicitly. The runner does not pull images or install dependencies. |
| Windows Application Control rejects current native SDK extensions | Standard dependency installation may fail to import. | Use the tested [Windows compatibility constraints](requirements-platform-windows.txt); keep Windows and WSL environments separate. Current locked SDKs passed separately in WSL. |
| Malformed/truncated model output or a semantically invalid proposal | Repairs consume the original budget; valid JSON alone cannot establish a sound experiment. | Typed contracts and bounded repairs handle structure. Review the concrete design and approve its exact digest before execution. |
| Crash without a matching completed execution receipt | An interrupted process cannot be resurrected; a new attempt consumes the remaining attempt/runtime budget. | Inspect the failure and use explicit Resume within existing limits. An original worker's `cleanup_unverified` state requires operator verification before reuse. |
| API/worker revision mismatch or incomplete state backup | Recovery may fail or jobs may be refused by the versioned protocol fence. | Update both services together and back up metadata, checkpoints, artifacts and private evaluation fixtures consistently. |
| Dependency/build advisories | Large lazy Monaco bundle and compatibility checkpoint deprecation remain warnings. Gemini CLI is unpinned in the agent image build, creating rebuild compatibility risk. | Treat the warnings as nonblocking; record rebuilt Gemini versions and repeat parser compatibility checks before live use. |

Sources: [deployment and recovery](docs/DEPLOYMENT.md),
[program execution](docs/ARCHITECTURAL_CORRECTIONS.md#program-execution-and-dependencies),
[Gemini/Headless compatibility](docs/UPSTREAM_WORKER.md#headless-and-gemini-compatibility),
[validation notices](docs/RESEARCH_ENGINE_ACCEPTANCE.md#exact-validation-commands).

## Historical breakdowns already corrected or mitigated

| Breakdown encountered | Recorded correction / remaining caveat |
| --- | --- |
| Initial Docker/credential gaps | Later genuine Docker studies, Groq calls and remotely retrieved LangSmith spans supersede the old claims that none were available. Readiness remains an operational prerequisite. |
| Missing dynamic engine sources in the initial checkout | Selected later sources were recovered from an identified local validation image and integrated; native protocol 2 now exists. Recovery alone did not prove execution. |
| Windows atomic-write temporary path reached 262 characters | Compact fixture directories and shorter temporary names fixed publication. Resumed evaluator validation reused approved preparation with zero additional model calls. |
| Two Groq structured-output HTTP 400 failures | Schemas are now transmitted in the actual prompt as well as supported provider options; repairs are bounded. |
| Truncated scheduling synthesis | A concise prompt and 2,048-token stage allocation recovered synthesis within the unchanged total budget. The failed reservation was retained. |
| Missing/stale approval digests, retry routing and resumed provider identity | Guards and routing were corrected with regression coverage. |
| Selection omitted actual ideas and silently chose the first idea | Typed selection now receives the options and rejects foreign IDs. Historical selection calls remain failed autonomous decisions; later reviewed designs and audited measurements remain valid. The acceptance narrative does not establish a fresh full campaign after this correction. |
| Unsupported feature-scaling claim in the regression proposal | The proposal was returned for revision before execution and the replacement received a new digest approval. Scientific alignment still requires concrete review. |
| Stale approval UI cache, Monaco typing loss, Markdown tables and print defects | Fixed with final passing browser checks and visual inspection of exported PDF pages. |
| Read-only agent home caused diagnostic errors | A writable ephemeral home removed the errors. No genuine Gemini streaming incompatibility was reproduced. |

Sources: [current checkpoint](docs/DEVELOPMENT_PROGRESS.md),
[failure accounting](docs/RESEARCH_ENGINE_ACCEPTANCE.md#requests-failures-and-accounting),
[browser validation](docs/RESEARCH_ENGINE_ACCEPTANCE.md#exact-validation-commands),
[worker diagnostics](docs/UPSTREAM_WORKER.md#headless-and-gemini-compatibility).

## Recommended resolution order

1. Provision and verify the dedicated original-engine worker boundary (ISSUE-01).
2. Establish the nested-provider budget boundary (ISSUE-02).
3. Recheck the intended controller's toolchain and provider generation readiness
   (ISSUE-04 and ISSUE-05).
4. Execute and audit a real bounded original campaign; then integrate and validate
   web submission and lifecycle handling (ISSUE-03).
5. Address additional protocols, manuscript/draft capabilities and deployment
   storage/authentication gaps according to the intended release scope.
