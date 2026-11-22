# Reseon v1.2 literature-grounded native research

Latest acceptance: [the separately authorized v1.2.1 live study succeeded](RESEON_V1_2_1_LIVE_ACCEPTANCE.md),
including genuine Groq generation, both human approvals, ten Docker executions,
five paired measurements and cited report/export. The older paused run described
below remains untouched. This success applies to the bounded native scheduling path.

2026-11-22 follow-up: [v1.2.1 provider reliability and prompt budgets](PROVIDER_RELIABILITY_V1_2_1.md)
records compact stage context, protected later-stage capacity, single-attempt native
HTTP behavior and 241 Windows/280 WSL platform passes. The live paused run below
remains unchanged; no live retry or new research campaign was made for v1.2.1.

Verified locally on 2026-11-22. This implementation extends the existing native
workflow; it adds no provider, infrastructure, database or experimental protocol.
Following separate explicit authorization, live Groq planning reached the first
human gate and the user approved preparation. Preparation then paused at the
unchanged token reservation boundary. No new Docker research experiment has run.

## Preserved checkpoint and evidence

Reviewed the v1.1 changes, passing tests and staged content, including comparison
against configured secret values without printing them. Created local commit
`fffd4c9` (Add Reseon v1.1 literature discovery) and annotated tag
`reseon-native-v1.1.0`. The v1.0 commit/tag remains unchanged. Nothing was pushed.
`.env`, virtual environments, local databases, caches, node_modules, build outputs
and validation artifacts remain Git-ignored. V1.2 changes are left for review.

The historical scheduling run `be08d9e5f154486ea8b1ff9eebce6882` retains its exact
state/config/ledger/artifact-record snapshot:
`f1407818736521ad9fb6140da6edf5b3b56646e86c60e18d916eba9c61a41e77`.
All 22 artifact hashes verify, including original report hash
`67c8e7997098cfd3753cf8b089bf5d7585001b4a149285e3f2485855a2969ffb`.
The read-only audit independently recomputes five paired observations, mean
improvement 700 and exact sign-flip p=0.0625; ledger remains 13 calls.
Older run `e2dcc7048b654d0daef9ba68d5010079` remains 17 calls and its raw
config/state SHA remains
`e28fe4bc3e91767ea35f41ed20a6b60206c1c2479e1f61dd12b97696b59b6ee3`.
Neither historical run was resumed or rewritten. The unrelated waiting run was
not approved or resumed. Original campaign launch remains HTTP 409.

## Integration corrections

V1.1 already resolved browser-selected snapshot IDs against server-side cached
papers and retained source provenance. Inspection found that the later native
prompt reduced context to four title/URL pairs: abstracts and citation identity
were lost. V1.2 passes available metadata and excerpts for all selected sources
(up to ten) into planning, ideation and preparation. Missing abstracts remain
missing. Source text is explicitly untrusted context, never instructions.

Typed planning hypotheses and ideas require nonempty, distinct citation IDs from
the actual selected papers. Unknown, fabricated, duplicate or absent references
fail validation through the existing bounded repair/ledger path. Ideas require
an explicit literature rationale. The experiment specification must retain the
selected hypothesis exactly. Identifier validation does not certify that an AI
interpretation faithfully describes a paper; the UI/report marks it unverified.
Retrieval does not establish novelty or constitute full-text review.

Preparation saves a content-hashed grounding manifest containing selected source
snapshots, hypothesis, idea ID, citations and rationale. The final human approval
digest binds the prepared experiment, hidden dataset commitment and grounding
hash. Existing unselected-run digest calculations are unchanged. Source,
hypothesis, citation or manifest changes require new preparation/approval.
Validation runs before evaluator approval, candidate generation and execution.
Experiment configuration retains the manifest; results retain its hash and the
idea/hypothesis/citation association. No evaluator capability or budget is widened.

## Reports and frontend

For new grounded runs, deterministic reports include the question, AI hypothesis
and rationale, approved specification/digest, protocol and dataset, seeds,
baseline reference, proposed candidate method, actual program hashes, selected
metadata/provenance, genuine available abstract excerpts and DOI/source references.
Existing trusted measurements, statistical calculations, limitations and labeled
historical proposals remain the source of final measured claims. Source metadata,
model interpretation and measured findings are separate sections.

The frozen approval review shows the grounding hash and source manifest. Idea
cards link their checked citations and label AI interpretation. Report preview
now renders HTTP/HTTPS Markdown citation links, including in reference lists;
unsafe URL schemes and raw HTML remain inert. Browser export is checked against
the exact server-rendered Markdown. Original immutable reports are not replaced.
The preview also accepts retained measurement tables with blank lines between
rows, preserving accessible headers/cells without changing Markdown evidence.
Reports without a new grounding manifest keep their previous presentation.

## Live scholarly check

One query: `shortest processing time single machine scheduling`, limit 3.
Exactly two public keyless GETs: OpenAlex `/works` HTTP 200 and Crossref `/works`
HTTP 200. No retries, paid metadata keys, provider calls or research execution.
The normalized results were:

| Source record | Year | DOI | Supplied abstract |
| --- | --- | --- | --- |
| A Worst-Case Performance of the Shortest-Processing-Time Heuristic for Single Machine Scheduling | 1991 | https://doi.org/10.1057/jors.1991.170 | Yes, OpenAlex |
| Single machine flow-time scheduling with scheduled maintenance | 1992 | https://doi.org/10.1007/bf01178778 | No |
| Guaranteeing timing constraints under shortest remaining processing time scheduling | unavailable | https://doi.org/10.1109/emwrts.1997.613768 | No |

No source warnings. Provider ranking does not establish relevance to the exact
native evaluator. Public receipt/cache is local and ignored at
`.research-platform/validation/grounded-research-v12/live-literature.json`.
The three public paper snapshots were copied into the existing local-app source
cache for later explicit selection; no run, experiment or additional request was
created. The first paper's supplied abstract concerns quadratic job lateness,
not the native evaluator's total-completion-time metric. Any native study using
it must describe a related-method synthetic check, not a reproduction of its
claims or experimental setting.

## Validation commands and results

From the repository, Windows:

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -k 'not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline or selected)' -q --tb=short
.venv\Scripts\python.exe -m ruff check src/research_platform tests/research_platform scripts/verify_native_reproducibility.py
.venv\Scripts\python.exe -m ruff format --check src/research_platform tests/research_platform scripts/verify_native_reproducibility.py
.venv\Scripts\python.exe -m mypy --platform linux --follow-imports silent src/research_platform apps/research_platform/backend
.venv\Scripts\python.exe scripts/verify_native_reproducibility.py --workspace .research-platform/local-app --run-id be08d9e5f154486ea8b1ff9eebce6882
```

Windows platform: **222 passed, 39 skipped, 4 deselected**. POSIX-specific worker
checks are skipped on Windows. WSL platform: **261 passed, 4 deselected**, using
the same pytest selection with native Linux Python after sourcing
`/home/sonusunny/.nvm/nvm.sh`. Initial WSL invocation omitted nvm initialization;
two installed-CLI tests failed for missing Node, then both and the full suite
passed with the existing native installation. No installation was needed.

WSL CLI/Inspector: **41 passed**:

```bash
. /home/sonusunny/.nvm/nvm.sh
GEMINI_CLI_OFFLINE_TEST=1 /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py -q --tb=short
```

The CLI suite cannot run directly on Windows because its upstream imports require
`fcntl`. An initial default-Windows-target mypy invocation reported POSIX API
errors; the repository's Linux target passes for all 35 platform/backend sources.
Ruff and formatting pass. These environment failures are not suppressed in tests.

In `apps/research_platform/frontend`:

```powershell
npm.cmd run test
npm.cmd run typecheck
npm.cmd run build
npm.cmd run format:check
```

Frontend: **21 unit tests passed**. Type checking, production build and formatting
pass; there is no separate frontend ESLint script in the existing package. The
full Chromium suite passed **6 tests**, including both grounded and unselected
native workflows. The final targeted grounded-flow recheck passed **1 test**,
verifying the table parser, citation links and byte-identical Markdown export. The
production build retains its existing large editor/visualization chunk warning.

Browser fixture uses a fresh ignored state path, mocked scholarly/model responses
and a stub process boundary; it does not run Docker or contact AI providers:

```powershell
.venv\Scripts\python.exe tests/research_platform/offline_native_server.py --offline-boundary --mock-literature --state .research-platform/validation/grounded-research-v12/browser-fixture --port 8012
```

From frontend, set `PLATFORM_URL=http://127.0.0.1:5182`,
`PLATFORM_FRONTEND_PORT=5182`, `RESEARCH_API_URL=http://127.0.0.1:8012` and
`NATIVE_OFFLINE_E2E=1`; run `npm.cmd run test:e2e -- --workers=1`.
The extended literature case traverses search, explicit selection, native plan,
both approvals, experiment/evaluation, report, real-format source links and export.
Fixture paper IDs and measurements are test data, not live scientific evidence.

## Usage and remaining live acceptance

Use the existing launch/stop commands in [LOCAL_APPLICATION.md](LOCAL_APPLICATION.md).
The Windows launcher starts API, worker and Vite. Verified local frontend:
http://127.0.0.1:5180/literature; health: http://127.0.0.1:8010/api/health.
Search, select papers, choose **Use selected papers in research**, review sources,
choose the existing Groq model and supported task. Launching live research requires
explicit authorization and fresh Free-plan/key-bound verification; it is not part
of offline validation. Stop/review at both existing approval gates. The second
gate freezes dataset/design/source/hypothesis commitments before candidate work.

Proposed live acceptance is a NEW scheduling_v1 study: metadata-inspired SPT/FIFO
comparison, 32 jobs, durations 1–10, five fixed seeds, subject to both human reviews.
Groq/openai/gpt-oss-20b; at most 20 calls including preflights/repairs/retries,
32k input/16k output tokens, 2 iterations, 3 experiment attempts, 300 active seconds.
Per isolated program: 1 CPU, 256 MiB, 64 PIDs, 10 seconds, no network or mounts.
No provider switching, paid fallback or budget increase. Account billing cannot
be independently verified; unknown monetary cost stays null. Offline implementation
and tests made no live model calls or Docker campaigns. The separately authorized
live planning check is recorded below.

## Authorized live validation — first gate and preparation pause

The user explicitly authorized the bounded new run and freshly confirmed Free
plan/no paid usage, with a stop at both human gates. A fresh key-bound attestation
was applied only to service-process environment variables; `.env` and keys were
not changed or displayed. Docker Desktop was stopped when checked. Started only
the existing application using `docker desktop start --detach`; no installation,
reconfiguration or image pull. Read-only `docker info` then reported Linux Engine
29.9.2; the existing `python:3.12-slim` image was present with ID
`sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`.

Created a new project/run using the existing HTTP application, retaining the
selected paper snapshot. Run creation returned HTTP 201:
`060988269faf4d1dbfde7a362b4718fb`.

- Status: `awaiting_approval`, stage/gate: `research_plan`.
- Provider/model: Groq / `openai/gpt-oss-20b` for every request.
- Four completed real-generation ledger entries: preflight (75 input/23 output),
  feasibility (913/430), first planning response (2114/536), repaired planning
  response (2182/531). Totals: **4/20 calls, 5,284 input, 1,520 output tokens**;
  unknown monetary cost remains null; 16 calls remain.
- First planning JSON misplaced required fields in nested step lists and failed
  typed schema validation. The existing one-repair path produced a valid plan;
  both real responses and all attempted calls remain retained. This was a schema
  repair, not an API error, provider switch or fabricated fallback.
- Valid hypothesis H1 predicts SPT total completion time <= FIFO across the five
  fixed seeds and retains exact citation `https://doi.org/10.1057/jors.1991.170`.
  The DOI/source identity is verified, not its applicability as scientific proof.
- Plan respects 32 jobs, durations 1–10, five specified seeds, FIFO/SPT, paired
  inputs, 1 CPU/256 MiB/64 PIDs/10 seconds and existing budgets.
- No candidate, prepared contract, final approval digest or experiment exists.
  No Docker research executions have occurred for this run.
- The real frontend first-review dialog was inspected read-only in Chromium;
  it displayed the bounded plan, and browser inspection submitted no mutations.

Requested first-gate clarification: each seed defines a reproducible instance;
only baseline/candidate inputs within each pair are identical. The generated
plan's wording about "five identical" instances should not imply identical data
across seeds. Its claim of "no statistical inference" should be replaced with
the existing trusted exploratory paired summaries/sign-flip test, with small-seed
limitations and no automatic significance claim. Human feedback can correct this
before model-assisted preparation; candidate generation/execution remains behind
the separate digest-bound second gate.

Local receipt and original planning responses are retained in ignored validation
storage and run artifacts. The first-gate review URL is
http://127.0.0.1:5180/workspace/060988269faf4d1dbfde7a362b4718fb.
Historical scheduling snapshot/13 calls and older config/state hash/17 calls
remain unchanged after application startup and live planning.

The user subsequently approved preparation with those clarifications. Submitted
the approval through the existing endpoint (HTTP 200), retaining the exact
clarifications in feedback and constraints. The worker rechecked generation
readiness and produced genuine literature-grounded ideas and a selected hypothesis.
The chosen hypothesis retains the DOI; its rationale discusses the actual supplied
abstract as a possible motivation for a different metric, which remains AI
interpretation rather than verified paper evidence.

Specification preparation then stopped automatically:

| Current accounting | Value |
| --- | --- |
| Status/stage | paused / experiment_spec |
| Error | budget_exhausted: input-token reservation budget exhausted |
| Model-call ledger | 9/20: seven completed, two unreported reserved attempts |
| Provider-reported tokens | 9,683 input / 2,664 output |
| Input charged/reserved | 29,923/32,000 |
| Remaining input reservation capacity | 2,077 |
| Output charged/reserved | 5,736/16,000 |
| Active runtime | approximately 16.12 seconds |
| Monetary cost | unknown/null |
| Candidates/experiments/Docker research executions | zero |

Each failed or uncertain specification attempt retained a 10,120-input-token and
1,536-output-token reservation. A later attempt was refused before dispatch; it
did not create another ledger entry. Reported tokens alone cannot justify releasing
uncertain reservations. The next specification request cannot fit the remaining
capacity. No reservation was cleared, budget increased, provider switched, new
run created or automatic resume attempted after this pause. The second gate was
not reached, and no frozen contract/final digest or live research report exists.

The earlier implementation did not persist individual request-failure statuses
before retrying. The final budget error masks the original HTTP/transport cause;
the retained evidence cannot distinguish quota, transient server/network errors
or a schema-compatibility rejection followed by a retryable failure. A specific
HTTP status must not be invented or inferred as verified. No API request was
made to reproduce the failure. Diagnose with Groq Console request/usage evidence
before authorizing any separate new attempt; this run should remain paused under
its existing limits.

Added a small optional ProviderRouter failure callback wired to existing workflow
events. Future generation failures record provider/model/stage, attempt, status
code/category and reservation-retained flag before retry/budget refusal. Request
bodies, provider messages, URLs, headers, exception strings and secrets are never
included. Three offline regressions (429, 503, transport failure) prove the first
two failures survive a later blocked reservation and that no third request or
secret-bearing diagnostics are emitted. Ledger/retry/budget rules are unchanged.

Restarted the existing local application to load the diagnostic fix, with live
generation blocked again in its service environment. The paused run and unrelated
waiting run are not resumed. The fresh attestation/keys were never written to `.env`.
Large contexts and retained uncertain attempts can exhaust conservative byte-based
input reservations even when reported usage is lower. Keep limits intact; a new
live attempt would require separate explicit authorization and a bounded plan.

Only regression_v1 and scheduling_v1 evaluators are supported. Full-text scientific
claim validation, automated novelty assessment, paper-specific arbitrary studies
and original Sakana campaigns remain unavailable. Large selections may exhaust
existing token limits; there is no automatic budget increase. Retrieved abstracts
remain bounded source excerpts, not verified paper conclusions.

## Exact v1.2 files

New: `src/research_platform/grounding.py`,
`tests/research_platform/test_grounding.py`, this document.

Modified:

- `src/research_platform/narrative_contracts.py` — citation/rationale fields.
- `src/research_platform/workflow.py` — metadata/excerpt context and citation validation.
- `src/research_platform/preparation.py` — selected hypothesis/spec alignment.
- `src/research_platform/services.py` — grounding artifacts, digest binding and execution association.
- `src/research_platform/providers.py` — safe per-attempt failure metadata callback.
- `src/research_platform/reports.py` — grounded deterministic report sections.
- `scripts/verify_native_reproducibility.py` — conditional grounding commitment audit.
- `apps/research_platform/frontend/src/types.ts` — optional idea citation fields.
- `apps/research_platform/frontend/src/run.tsx` — citation/rationale presentation and safe report links.
- `apps/research_platform/frontend/src/evidence.tsx` — frozen grounding review.
- `apps/research_platform/frontend/src/test/platform.test.tsx` — safe citation rendering regression.
- `apps/research_platform/frontend/e2e/literature.spec.ts` — complete grounded browser workflow/export.
- `tests/research_platform/test_native_application.py` — both selected-protocol integrations/provenance.
- `tests/research_platform/test_reports.py` — source/interpretation/measured-report separation.
- `tests/research_platform/test_providers.py` — failure diagnostics before a later budget refusal, without secrets.
- `docs/LOCAL_APPLICATION.md`, `docs/DEVELOPMENT_PROGRESS.md` — usage and verified progress.
