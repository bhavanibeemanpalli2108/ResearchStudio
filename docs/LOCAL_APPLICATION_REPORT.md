# First usable native application — verification

Verified 2026-11-20. **Offline integrated workflow passes; authorized live Groq scheduling run completed with real measurements and report generation.** Windows app: http://127.0.0.1:5180; API/docs:
http://127.0.0.1:8010/docs. The offline checkpoint below used no real provider calls; the authorized live continuation is recorded at the end.

## Existing implementation retained

FastAPI, React, Alembic, the separate durable worker, ModelUsage ledger, protocol
2, both human approval gates, frozen experiment digests, isolated Docker,
paired measurements, event logs and immutable report downloads were reused.
Validated domains remain synthetic regression and single-machine scheduling.
Original full_research HTTP 409/no-run-created protection remains unchanged.

## Exact changes

| Files | Change |
| --- | --- |
| src/research_platform/providers.py | FreeTierUnverifiedError; every Groq network attempt requires a fresh key-bound operator Free-plan attestation before dispatch/reservation. |
| apps/research_platform/backend/app.py | Nonsecret attestation status; locally configured Groq model choice without remote discovery. |
| apps/research_platform/frontend/src/create.tsx | Groq/openai/gpt-oss-20b defaults, configured/unverified label, Free-plan guidance, accurate resume-preflight wording and accessible labels. |
| src/research_platform/services.py | Optional literature failure warns and continues without retrieved citations; no invented citations. |
| src/research_platform/dev.py | Explicit frontend port, invalid/occupied/overlapping-port refusal before migration, Vite strictPort, chosen loopback origin, POSIX child-group shutdown. |
| scripts/start_research_platform.ps1 | API/frontend port forwarding and built mode. |
| scripts/start_research_platform.sh | RESEARCH_PYTHON selects existing Linux venv; LF shell endings. |
| .env.example | Two blank, nonsecret attestation fields. Actual .env/key unchanged. |
| tests/research_platform/test_providers.py | Six denied-attestation cases, including cached models/no dispatch/no reservation; fake keys explicitly attested. |
| tests/research_platform/test_storage.py | Existing mocked Groq ledger tests explicitly attest fake keys. |
| tests/research_platform/test_native_application.py | Both protocols through API, worker, mock Groq, actual Docker, both approvals, metrics, ledger and report export. |
| tests/research_platform/offline_native_server.py | Opt-in test-only fixture server with fresh state, mock provider and actual Docker. |
| apps/research_platform/frontend/e2e/native.spec.ts | Opt-in complete native Chromium journey. |
| apps/research_platform/frontend/playwright.config.ts | Explicit browser-test frontend port. |
| apps/research_platform/frontend/src/test/platform.test.tsx | Groq/native defaults and existing protocol/budget assertions. |
| docs/LOCAL_APPLICATION.md, docs/LOCAL_APPLICATION_REPORT.md, docs/DEVELOPMENT_PROGRESS.md, docs/DEPLOYMENT.md | Instructions and current evidence. |

No dependencies, lockfile, infrastructure settings or provider keys were changed.
Pre-existing uncommitted work was preserved. No new database migration was needed
for these changes; existing migrations run only on selected startup/test state.

## Configuration and billing boundary

GROQ_API_KEY is configured. git check-ignore .env passes. No key was displayed or
copied into experiments. Containers have no network, mounts, secrets or Docker
socket. Existing environment sanitation and isolation regressions pass.

The user confirmed this key's organization is on the Free plan with paid usage
disabled. Public [model documentation](https://console.groq.com/docs/models) and
[rate limits](https://console.groq.com/docs/rate-limits) cannot verify that account.
The [billing FAQ](https://console.groq.com/docs/billing-faqs) describes paid upgrades.
Neither discovery nor HTTP 200 establishes zero cost.

GROQ_FREE_TIER_VERIFIED_AT and GROQ_FREE_TIER_KEY_SHA256 bind an operator
confirmation to the stripped key for at most 24 hours. Missing, malformed, naive,
future, expired or wrong-key attestations fail before each network attempt.
The app cannot independently detect a subsequent remote plan change. This is not
a provider-enforced no-charge guarantee. Unknown monetary cost remains null;
monetary caps still reject unpriced remote generation. No billing upgrade,
automatic provider switch or budget increase occurs. At the offline checkpoint the app had no attestation and blocked Groq calls. The authorized live continuation below uses a fresh process-local attestation; .env and the key remain unchanged.

## Actual startup evidence

Windows PowerShell launcher started API, separate worker and Vite on 8010/5180,
using .research-platform/local-app. Health/docs returned 200 and browser workflow
tests passed through the proxy. Existing occupied services on 8000/5173 were left
untouched. New selected state migrates to 0002; historical DBs remain at 0001.

WSL Ubuntu 2, existing native Python 3.12 and Node v26.13.1: shell launcher started
API/worker and served the portable built frontend on 8014. Health and SPA returned
200. Temporary WSL services were then stopped with normal application shutdown.

WSL Vite encountered missing @rollup/rollup-linux-x64-gnu in the shared Windows
node_modules. The supervisor stopped its children. No destructive npm repair or
installation was performed. WSL built-SPA mode works; independent Linux frontend
development needs a separately reviewed dependency layout. Windows dependencies
were preserved.

## Final tests

| Validation | Result |
| --- | --- |
| Windows platform | 189 passed, 39 skipped; existing LangChain warning |
| WSL platform, installed CLI mock tests enabled | 228 passed; two existing websockets warnings |
| Frontend unit | 13 passed |
| Existing Chromium journeys | 4 passed |
| New native Chromium journey | 1 passed: mock Groq, actual Docker, both approvals, metrics and Markdown download |
| Native API/worker/Docker integration | 2 passed within platform totals: regression and scheduling |
| Ruff/format, Linux-target mypy | Passed; 33 typed source files |
| TypeScript, Vite build, Prettier | Passed; existing large lazy editor chunk warning |
| Shell syntax and whitespace | Passed |

Windows skips are 37 POSIX worker cases and two opt-in Linux CLI cases. Gateway
accounting and original HTTP 409 regressions remain included. Initial fixture
assertions/selectors/origin were corrected before final passing runs.

Offline browser run 5d9bd2f4b74a484c8870b47638a9b0d5 completed with 13 mock
generation calls, including three charged preflights. Fake usage values do not
establish real model cost/capacity. Docker baseline/candidate execution and
independent measurements are real; fixture-authored programs are not live-model
scientific evidence. No fresh Groq generation success is claimed.

Evidence:

- .research-platform/validation/native-product-evidence/offline-browser.json
- .research-platform/validation/native-product-browser-final-20261120
- apps/research_platform/frontend/test-results/native-* (screenshot/report download)

## Commands executed

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -q --tb=short
.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent --platform linux
wsl -d Ubuntu --exec bash -n /mnt/d/project/reseon/AI-Scientist-v3/scripts/start_research_platform.sh
git diff --check
```

Windows startup used the three local-app storage overrides documented in
[LOCAL_APPLICATION.md](LOCAL_APPLICATION.md), then:

```powershell
./scripts/start_research_platform.ps1 -Port 8010 -FrontendPort 5180
```

WSL:

```bash
. /home/sonusunny/.nvm/nvm.sh
cd /mnt/d/project/reseon/AI-Scientist-v3
GEMINI_CLI_OFFLINE_TEST=1 /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/research_platform --confcutdir=tests/research_platform -q --tb=short
RESEARCH_PYTHON=/home/sonusunny/.local/share/agsci-mission1-venv/bin/python DATABASE_URL=sqlite:///./.research-platform/validation/native-product-wsl/platform.db ARTIFACT_ROOT=./.research-platform/validation/native-product-wsl/artifacts CHECKPOINT_PATH=./.research-platform/validation/native-product-wsl/checkpoints.db bash scripts/start_research_platform.sh --no-frontend --port 8014
```

From frontend:

```powershell
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
npm.cmd run format:check
$env:PLATFORM_URL='http://127.0.0.1:5180'
$env:PLATFORM_FRONTEND_PORT='5180'
$env:RESEARCH_API_URL='http://127.0.0.1:8010'
npm.cmd run test:e2e -- demo.spec.ts
```

Native fixture from root (fresh state path required):

```powershell
.venv\Scripts\python.exe tests/research_platform/offline_native_server.py --state .research-platform/validation/native-product-browser-final-20261120 --port 8012
```

Then from frontend:

```powershell
$env:PLATFORM_URL='http://127.0.0.1:5182'
$env:PLATFORM_FRONTEND_PORT='5182'
$env:RESEARCH_API_URL='http://127.0.0.1:8012'
$env:NATIVE_OFFLINE_E2E='1'
npm.cmd run test:e2e -- native.spec.ts
```

Fixture server and Playwright-owned Vite were stopped afterwards. Windows app on
5180 remains running. The exact WSL startup uses the built frontend to preserve
the existing Windows npm installation.

## Preservation and remaining acceptance

Prior native run e2dcc7048b654d0daef9ba68d5010079 is still completed at 17/20 calls,
with unchanged raw config/state SHA-256:
e28fe4bc3e91767ea35f41ed20a6b60206c1c2479e1f61dd12b97696b59b6ee3.
No remaining calls, experiment artifacts or scientific results were modified.
Default platform and prior live databases were inspected read-only.

No known blocking defect remains in the tested native offline journey. Limits:
fresh live Groq research unverified; billing operator-confirmed rather than
remotely guaranteed; shared Windows npm dependencies cannot start Linux Vite;
optional literature may be unavailable; synthetic findings need human review.
Original campaigns, VM/network deployment, public and multi-user use remain blocked.

Proposed live verification: a new native scheduling run, Groq/openai/gpt-oss-20b,
maximum 20 calls, 32k input/16k output tokens, two iterations, three experiments,
300 active seconds. Each isolated execution: one CPU, 128–512 MiB RAM, 64 PIDs,
at most 30 seconds, no network/mounts. Daily configured cap is 100 (93 remained
after demo validation). Retain both human approval gates; do not reuse completed
history or silently change providers/budgets. Live authorization is still required.


## Authorized live continuation — first approval gate, 2026-11-20

The user explicitly authorized one new bounded scheduling run and required a stop
at both existing human approval gates. Reused the same local-app workspace,
API, worker and frontend after a controlled restart on 8010/5180. Set only
process-local Free-plan timestamp/key digest based on the user's confirmation;
.env and API keys were not changed. No historical run budget was reused.

New run: be08d9e5f154486ea8b1ff9eebce6882.
Question: Does shortest-processing-time ordering reduce total completion time
versus FIFO on reproducible synthetic single-machine job instances?
Provider/model: Groq / openai/gpt-oss-20b. Native protocol 2, scheduling_v1,
both approvals enabled, no stage overrides or fallback models. Authorized limits
remain 20 calls, 32,000 input/16,000 output tokens, two iterations, three experiment
attempts and 300 active seconds.

Actual provider generation succeeded. Persisted readiness is generation_verified.
The preflight, feasibility and planning reservations all completed with provider-
reported usage:

| Stage | Input tokens | Output tokens |
| --- | ---: | ---: |
| provider_preflight | 75 | 23 |
| feasibility | 740 | 545 |
| planning | 1,446 | 698 |
| Total | 2,261 | 1,266 |

Budget: 0/20 -> 3/20, 17 calls remaining. Cost remains unknown/null. Active runtime
reported 3.46 seconds. Run status awaiting_approval, stage research_plan; durable
job waiting_v2 with no owner. No experiment has executed, and no results/report
from this fresh study are claimed. Approval was not submitted. Read-only Chromium
inspection displayed the actual live plan and saved a screenshot; non-GET API
requests were blocked in that inspection.

### Plan review findings requiring human decision

The generated plan proposes 128 jobs and five seeds (42, 123, 456, 789, 101112),
uniform durations 1–10. The existing scheduling contract permits only 8–64 jobs;
128 is unsupported. The plan summary also reverses the difference sign relative
to its steps, and strict improvement should not label equal orderings as a failure.
These are provider-authored proposal issues, not measured experimental findings.
The saved provider output was preserved without editing.

Recommended conditional approval feedback: use 32 jobs and those five fixed
seeds, compare both policies on identical inputs, define improvement as
FIFO total completion time minus SPT total completion time (positive is better),
record zero as a tie, retain all isolation/budget limits, and make no novelty or
generalization claim. After human approval, prepare the exact spec/evaluator and
stop at the second digest-bound gate before candidate generation or execution.
No automatic approval or repair generation was performed at this first gate.

Evidence under .research-platform/validation/native-product-evidence/:

- live-start.json — explicit authorization scope and single submission receipt.
- live-first-status.json — actual persisted run/plan, readiness, events and zero experiments.
- live-first-gate.png — actual frontend plan dialog, no approval submitted.

Prior completed run e2dcc7048b654d0daef9ba68d5010079 remains at 17 calls with its
original config/state hash unchanged. This checkpoint establishes live Groq
planning/readiness and accounting, not completed live research acceptance.


## Authorized preparation — second approval gate, 2026-11-20

The user approved preparation with the first-gate corrections. The existing
approval API accepted that feedback/constraint update with HTTP 200. No budgets,
provider or historical outputs were changed. The worker resumed and stopped at
approval/awaiting_approval before candidate generation or experiment execution.

Run be08d9e5f154486ea8b1ff9eebce6882 is now at 9/20 calls (11 remaining).
All nine ledger rows completed: two provider preflights, feasibility, planning,
ideas, selection, experiment_spec, baseline_program and evaluation_contract.
Provider-reported totals: 8,953 input + 2,954 output tokens. Cost remains null;
active runtime 11.09 seconds. No provider error or uncertain reservation occurred.

Prepared and validated contract:

- scheduling_v1, FIFO baseline vs intended SPT candidate.
- 32 jobs, one machine, uniform integer durations 1–10 inclusive.
- Five seeds: 42, 123, 456, 789, 101112; identical frozen inputs for both policies.
- Trusted host evaluator: total_completion_time, minimize; improvement is FIFO
  minus candidate. Positive improves; zero is a tie. The model-selected frozen
  minimum-improvement success threshold is strictly greater than 0.1 time units
  in the mean paired difference, not a percentage or significance claim.
- One paired observation per seed in the trusted protocol. Idea prose mentioned
  extra replications; those are not part of the frozen executable contract and
  must not be claimed as performed.
- Each isolated execution: one CPU, 256 MiB RAM, 64 PIDs, 10-second timeout;
  no network, mounts, credentials or Docker socket.
- Baseline source is standard-library FIFO: emit all indices in input order.
- Prepared contract validated locally; baseline hash verified. Dataset/evaluator
  commitments are frozen and all 9 analytical evaluator self-checks passed.
- Candidate is null; program state is null; experiments list is empty.

Final approval digest (includes frozen evaluation commitment):
`e79b03b5fb8bb4b704eaedb111acb9a56ad4415dee63f141894d394f3cd4edd0`.
Prepared-artifact digest is distinct; the API must receive the final digest above,
not the earlier preparation-only digest. Exact preparation artifact is
12e4eaeebae27a750fac106038847bb6; evaluator validation artifact is
1d2e8de7891136122895e1c691b74a24.

Evidence added under .research-platform/validation/native-product-evidence/:
live-plan-approval.json, live-preparation-status.json, live-prepared-contract.json,
live-second-gate-verification.json and live-second-gate.png. No source-code change
or test rerun was needed for this runtime continuation. Prior completed native
run remains completed at 17/20 with unchanged config/state hash.

Second approval was not submitted. Live candidate generation, Docker experiment
measurements and final report remain pending that explicit digest-bound decision.


## Authorized live execution completed — 2026-11-20

The user explicitly approved final digest
`e79b03b5fb8bb4b704eaedb111acb9a56ad4415dee63f141894d394f3cd4edd0`
and bounded candidate generation/execution. Submitted that exact digest through
the existing approval API (HTTP 200); no design, digest, provider or budget was
changed. Run be08d9e5f154486ea8b1ff9eebce6882 reached completed/completion.

### Actual algorithm and measurements

Groq generated a standard-library Python candidate that constructs (duration,
original_index) pairs, sorts by that pair and emits the sorted job indices.
This is deterministic stable shortest-processing-time ordering; ties preserve
input order. Candidate SHA-256:
86e81557a7dfa4b4d092621b8f018701fff51d4f1e3e4cf4ad97a9726e25eabd.
FIFO emits indices in original input order. Both ran on the same frozen 32-job
inputs for each of the five approved seeds.

| Seed | FIFO total completion time | Candidate total completion time | FIFO minus candidate |
| --- | ---: | ---: | ---: |
| 42 | 2845 | 2150 | 695 |
| 123 | 2946 | 2316 | 630 |
| 456 | 2993 | 2027 | 966 |
| 789 | 2412 | 1657 | 755 |
| 101112 | 2116 | 1662 | 454 |
| Mean | 2662.4 | 1962.4 | 700.0 |

Mean improvement 700.0 exceeds the approved >0.1-time-unit threshold. All five
paired observations improved; no extra replications were performed. This is a
successful measured synthetic comparison, not proof of novelty or generality.
The exact two-sided sign-flip p-value is 0.0625, which does not meet a 0.05
threshold. The Student-t interval [468.35, 931.65] depends on its separate
normality/independence assumptions and does not override that test result.

### Execution, isolation and accounting

One experiment attempt completed. Actual Docker event history in the execution
window contains 10 container-create events, 10 exits with code 0 and 10 destroy
events. Ten retained output files independently match five baseline/candidate
pairs. No failed attempts or execution errors occurred; nothing was discarded.
No additional campaign or experiment was launched.

The unchanged runner configured one CPU, 256 MiB memory and swap cap, 64 PIDs,
10-second per-execution timeout, network=none, read-only filesystem, unprivileged
UID, dropped capabilities, no-new-privileges and no mounts/credentials/socket.
Receipt resource settings match the approved contract. Containers were removed;
post-cleanup live inspection of their cgroups is unavailable, so no new claim of
independent cgroup measurement is made. Docker events substantiate actual starts,
exits and removal. Image ID remained the existing reviewed local image.

Final model ledger: **13/20 calls**, seven remaining; **13,589 input + 4,402 output
= 17,991 provider-reported tokens**. All rows are completed for Groq /
openai/gpt-oss-20b; cost remains unknown/null. No fallback, uncertain reservation,
retry-induced extra attempt or budget increase occurred. Active runtime is
26.94 seconds (approval waits excluded). Final four calls were preflight,
candidate_program, evaluation and synthesis. Actual results/dataset/spec hashes
match the approved preparation and frozen evaluation commitments.

### Report and retained evidence

The workflow generated research_report.md and validation.json. The report
contains the actual five-seed table, correct means, p=0.0625 and limitations.
Original immutable artifacts and failed/approved proposal history were preserved.

**Report presentation limitation:** its historical plan section still quotes the
superseded 128-job proposal and the old sign wording; selected-idea prose also
mentions unperformed extra replications. These are not the executed design.
The frozen spec, actual code, measured results and verified table above establish
32 jobs and one paired observation per seed. The generated draft therefore needs
human editorial review before sharing; the old plan was not silently rewritten
or represented as executed. This audit note is separate from immutable evidence.

New evidence under .research-platform/validation/native-product-evidence/:

- live-execution-approval.json — exact-digest authorization/submission receipt.
- live-execution-status.json — persisted completed state/events/experiment/artifacts.
- live-final-verification.json — checked hashes, ledger and measured outcome.
- live-docker-events.json — actual create/exit/destroy event evidence.
- live-candidate-86e81557a7dfa4b4.py — downloaded actual model-generated candidate.
- live-research_report.md — downloaded immutable generated draft.
- live-browser-report.md — browser-exported Markdown, verified against server artifact.
- live-completed-experiments.png and live-completed-report.png — actual frontend.

Prior run e2dcc7048b654d0daef9ba68d5010079 remains completed at 17/20 with unchanged
raw config/state hash. No source-code change was needed for this continuation;
prior automated test/build results remain the regression checkpoint. Real worker,
Docker events, ledger, artifact and browser checks establish this live execution.
Native scheduling/Groq workflow acceptance is now verified within this exact
scope. Other protocols/models, original-engine campaigns and public deployment
receive no new acceptance from this run.

## v1 stabilization superseding the presentation limitation — 2026-11-20

[Reseon native Research Studio v1](RESEARCH_STUDIO_V1.md) records the completed
read-only report correction, retained-evidence reproducibility audit, offline
regression checks and recommended Git checkpoint. The default frontend/Markdown
presentation now clearly separates the final approved contract from historical
proposals; the original report and all scientific artifacts remain unchanged.
No provider calls or experiment reruns occurred. Completed runs retain 13/20 and
17/20 calls. The current review service blocks Groq dispatch pending future
authorized Free-plan setup. This supersedes earlier pending presentation notes,
without rewriting their historical evidence.
