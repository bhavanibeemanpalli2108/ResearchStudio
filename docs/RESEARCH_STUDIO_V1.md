# Reseon — Native Research Studio v1 checkpoint

Verified locally on 2026-11-20. **Locally usable within the existing native
scheduling and synthetic-regression scope.** This is a verified working-tree
checkpoint recommendation, not a created Git release, public deployment or
original-engine acceptance.

Current frontend: http://127.0.0.1:5180.
Backend health: http://127.0.0.1:8010/api/health.
API docs: http://127.0.0.1:8010/docs.

## Final report corrections

Future native report generation and the current read-only report endpoint share
one deterministic renderer. GET /api/runs/RUN_ID/report returns Markdown and its
renderer/source metadata without writing state, artifacts, events or usage.
The frontend previews and exports that same presentation. User browser drafts
remain explicitly separate.

The report now puts the exact approved contract and final approval digest first,
then retained per-seed measurements and host-computed statistics. Historical
plans/ideas are fenced and clearly marked superseded; rejected job counts, signs
or replication suggestions cannot be mistaken for the executed design. Raw model
interpretation remains in original response artifacts/state and is not promoted
to measured conclusions. Missing or mismatched provenance is explicitly flagged.
Improvement-threshold success and statistical significance are distinguished.

The existing completed study's original report was not overwritten. The page
provides an explicit original-report download alongside the current presentation.
Raw state.paper remains the original persisted document for historical clients;
use the report endpoint for the current native presentation.

## Retained-evidence reproducibility

Run: be08d9e5f154486ea8b1ff9eebce6882.
Final approved digest:
e79b03b5fb8bb4b704eaedb111acb9a56ad4415dee63f141894d394f3cd4edd0.

| Seed | FIFO total completion time | SPT | FIFO minus SPT |
| --- | ---: | ---: | ---: |
| 42 | 2845 | 2150 | 695 |
| 123 | 2946 | 2316 | 630 |
| 456 | 2993 | 2027 | 966 |
| 789 | 2412 | 1657 | 755 |
| 101112 | 2116 | 1662 | 454 |
| Mean | 2662.4 | 1962.4 | 700.0 |

Read-only audit recalculates completion times directly from retained input
durations and output permutations, validates FIFO semantics, source/output/input
hashes, all 22 registered artifact hashes/sizes, the private fixture commitment,
final approval binding, approved/executed specification and ledger totals. It
never executes program code, launches Docker, loads .env or contacts a provider.
Private fixture salts/labels are not exported.

Independent enumeration of all 32 sign assignments gives exact two-sided
p=0.0625. Numerical integration of Student-t density gives critical value
2.776445105197695 and interval [468.3522813181381, 931.6477186818619], matching the
saved interval within 1e-6. The positive mean exceeds the approved 0.1-unit
threshold, but p=0.0625 does not establish significance at 0.05. Five synthetic
paired seeds do not establish novelty or generalization.

The earlier execution evidence retains ten successful Docker create/exit/removal
events and ten output files for five baseline/candidate pairs. No experiments
were rerun in this stabilization. Logs, actual metrics and retained code agree.
The candidate is stable shortest-processing-time ordering by duration/input index.

Before/after snapshot of status, configuration, state, usage, artifact metadata
and ledger is identical:
f1407818736521ad9fb6140da6edf5b3b56646e86c60e18d916eba9c61a41e77.
The run remains completed at 13/20 calls, 13,589 input/4,402 output tokens and
unknown/null cost. Prior run e2dcc7048b654d0daef9ba68d5010079 remains unchanged at
17/20. No remaining model-call budget was consumed.

Original report SHA-256 remains
67c8e7997098cfd3753cf8b089bf5d7585001b4a149285e3f2485855a2969ffb.
Current presentation and screenshots are separate validation outputs under
.research-platform/validation/studio-v1, not replacements for scientific evidence.

## Usability and startup

The sidebar now reads **Reseon** and its Personal workspace placeholder card is
removed, as requested. An actual polling race was fixed: when a run changed to
Completed before the last experiment poll returned, the view could retain an
empty experiment list. Evidence queries now refresh on run-status transitions.

Windows launcher starts API, separate durable worker and Vite on 8010/5180 using
the existing local-app workspace. WSL launcher starts API/worker plus the portable
built frontend; the isolated validation instance on 8014 returned health/SPA 200
and shut down normally. Temporary browser fixture/WSL services were stopped.
Windows application remains available on 5180. No infrastructure was installed.

Use [LOCAL_APPLICATION.md](LOCAL_APPLICATION.md) for exact Windows/WSL commands,
Groq configuration, URLs, stop/restart and troubleshooting. Ctrl+C stops owned
services; Windows npm may ask for Y. The launcher starts the worker automatically,
refuses occupied ports and now refuses built mode when dist/index.html is missing.
WSL uses RESEARCH_PYTHON to preserve Windows .venv and serves the Windows-built
frontend rather than replacing shared node_modules.

Verbose HTTP-client INFO logs could contain credential-bearing query URLs.
API/worker startup now suppresses those transport logs, verified with fake secrets.
Existing credentials were not changed and older terminal logs were not erased;
do not share unredacted old logs or enable verbose transport debugging.

The current review instance blocks Groq dispatch. Future live research requires
current key-bound Free-plan confirmation and explicit operator authorization.
The key remains in the existing ignored .env, never the browser or experiments.
No provider request, paid usage, additional campaign, VM, QEMU or MCP action was
performed during this stabilization.

## Final regression results

| Check | Result |
| --- | --- |
| Windows Python platform | 192 passed, 39 skipped, 4 deselected |
| WSL Python platform | 231 passed, 4 deselected |
| WSL CLI/Inspector | 41 passed |
| Frontend unit | 16 passed |
| Chromium | 5 passed, including complete offline native workflow and matching preview/export |
| Ruff / formatting | Passed; 50 files checked |
| Linux-target mypy | Passed; 35 source files |
| TypeScript, production build, Prettier | Passed |
| Shell syntax / Git whitespace | Passed |

Four existing Docker-executing cases were deliberately excluded to honor the
no-rerun requirement; their source remains intact. Windows skips are 37 POSIX
worker cases and two opt-in installed Linux CLI cases. Offline full-workflow
tests cover both protocols through the existing API, ledger, worker and both
approval gates using fake provider and process boundaries. Browser native tests
likewise use only the explicit offline fixture. Tests also preserve original
HTTP 409 protection, budget limits, grant/concurrency enforcement and report
immutability. Initial test-fixture/selector issues were corrected; the browser
race was fixed rather than hidden by weakening assertions.

Nonfatal warnings: existing LangChain/websockets deprecations and a large lazy
Monaco bundle. No dependency or lockfile change was needed for this checkpoint.

Validation commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -k 'not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline)' -q --tb=short
.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform scripts/verify_native_reproducibility.py
.venv\Scripts\python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform scripts/verify_native_reproducibility.py
.venv\Scripts\python.exe -m mypy src/research_platform apps/research_platform/backend scripts/verify_native_reproducibility.py --follow-imports=silent --platform linux
.venv\Scripts\python.exe scripts/verify_native_reproducibility.py --workspace .research-platform/local-app --run-id be08d9e5f154486ea8b1ff9eebce6882
git diff --check
```

WSL uses the existing Python 3.12 environment and same pytest selection, with
GEMINI_CLI_OFFLINE_TEST=1 after sourcing ~/.nvm/nvm.sh. CLI tests use mock provider
transport and fake credentials. Separate CLI/Inspector command:

```bash
/home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py -q --tb=short
```

From frontend: npm.cmd test, npm.cmd run typecheck, npm.cmd run build,
npm.cmd run format:check. Browser fixture from root:

```powershell
.venv\Scripts\python.exe tests/research_platform/offline_native_server.py --offline-boundary --state .research-platform/validation/studio-v1/browser-fixture --port 8012
```

Use a fresh fixture state path on a repeat run. From frontend:

```powershell
$env:PLATFORM_URL='http://127.0.0.1:5182'
$env:PLATFORM_FRONTEND_PORT='5182'
$env:RESEARCH_API_URL='http://127.0.0.1:8012'
$env:NATIVE_OFFLINE_E2E='1'
npm.cmd run test:e2e -- --workers=1
```

## Exact files changed for this checkpoint

New:

- src/research_platform/reports.py
- scripts/verify_native_reproducibility.py
- tests/research_platform/test_reports.py
- docs/RESEARCH_STUDIO_V1.md

Modified:

- src/research_platform/workflow.py — shared deterministic report rendering.
- src/research_platform/worker.py — safe transport log level.
- src/research_platform/dev.py — built-frontend startup guard.
- apps/research_platform/backend/app.py — read-only report endpoint and log level.
- apps/research_platform/frontend/src/App.tsx — Reseon name, remove workspace card.
- apps/research_platform/frontend/src/api.ts — report presentation request.
- apps/research_platform/frontend/src/run.tsx — shared report preview/export and evidence refresh.
- apps/research_platform/frontend/src/test/platform.test.tsx — report/error/race regressions.
- apps/research_platform/frontend/e2e/native.spec.ts — complete offline workflow/export assertion.
- tests/research_platform/test_native_application.py — offline process-boundary coverage for both protocols.
- tests/research_platform/offline_native_server.py — explicit no-Docker browser mode.
- docs/LOCAL_APPLICATION.md, docs/LOCAL_APPLICATION_REPORT.md,
  docs/DEVELOPMENT_PROGRESS.md, docs/DEPLOYMENT.md — verified usage/progress links.

Existing unrelated modifications and untracked files were preserved.

## Remaining limits

Local single-user operation only; no public authentication/tenancy. Native Docker
shares the host kernel. Only scheduling and synthetic regression are validated.
Free-plan eligibility is operator-confirmed and expires; no provider-enforced
zero-charge guarantee or invented zero cost. Raw model drafts require scientific
review. Metadata retrieval does not establish literature claims. WSL shared
Windows node_modules still lacks Linux Rollup, so built-SPA mode is the supported
WSL launch. PostgreSQL/distributed deployment is unvalidated. Original campaigns,
dedicated VM/network enforcement and ISSUE-03 launch remain unavailable.

## Recommended local Git checkpoint — not executed

Suggested commit: **Stabilize Reseon native Research Studio v1**.
Suggested annotated local tag: **reseon-native-v1.0.0**.

The repository still contains earlier uncommitted and untracked application work;
the current HEAD is the upstream base, not this verified application. Review and
stage the complete application/dependency/deployment/test documentation scope,
including required untracked modules, using git status --short and the staged
diff. Do not stage .env, .research-platform, browser results, private evaluations
or machine-specific settings. This task did not stage, commit, tag or push.

After reviewing the exact staged checkpoint:

```bash
git diff --cached --stat
git diff --cached --check
git commit -m "Stabilize Reseon native Research Studio v1"
git tag -a reseon-native-v1.0.0 -m "Reseon native Research Studio v1 — verified local scope"
```

Tag the new reviewed commit, not the existing upstream HEAD. Keep a separate
consistent backup of the ignored research workspace; a source commit does not
contain the retained scientific data. No public release or push is proposed.
