# Reseon v1.2.1 — provider reliability and prompt budgets

Latest state: both human gates were subsequently authorized. Live run completed
with an actual SPT candidate, ten successful Docker executions, independent
evaluation and cited report/export, using 15/20 calls. See
[final live acceptance](RESEON_V1_2_1_LIVE_ACCEPTANCE.md). Earlier first/second-gate
figures below remain historical verification checkpoints.

Verified 2026-11-22. Initial implementation and automated validation were offline:
zero external provider/scholarly requests and zero research-program executions.
The separately authorized live first-gate check is recorded at the end below.
Local HTTP tests use mock transports and a stub execution boundary. Live v1.2
acceptance remains incomplete. No commit/tag was created for these uncommitted
v1.2/v1.2.1 changes; the reviewed v1.1 checkpoint remains unchanged.

## Findings from retained evidence

Run `060988269faf4d1dbfde7a362b4718fb` stays paused at experiment_spec. It retains
9/20 calls (seven completed, two uncertain), 29,923/32,000 input reservations,
2,077 remaining input capacity, 9,683 reported input and 2,664 reported output
tokens. Output reservations total 5,736/16,000. Cost is unknown/null. No candidate,
frozen final contract, experiment, measured result or live final report exists.

| Question | Actual finding |
| --- | --- |
| Original HTTP status, 429 rate limiting, 5xx or timeout | Not recoverable from the retained failure records. Do not label any as the verified cause. |
| Model context-length rejection | Not established. The run's cumulative input reservation limit is distinct from model context length. |
| Structured output | The first planning response misplaced required fields into nested step lists. Its retained raw response fails the typed schema; one bounded repair succeeded. |
| Request cancellation | No retained cancellation event explains the final pause. The recorded terminal cause is input reservation exhaustion. |
| Literature overload | One selected source was present, not a full-paper corpus. Nevertheless full metadata/provenance and abstracts were repeated into stages that only needed references. |
| Retry amplification | The default service router allowed up to three HTTP/transport attempts. Two specification attempts retained 10,120 input plus 1,536 output reservations each; the next reservation was refused. These are conservative allowances, not measured tokens spent by those attempts. |
| Conversation history | Native prompts already omitted full chat histories, raw logs, hidden fixtures and raw experiment outputs. That boundary remains; whole conversation history was not the observed problem. |

Successful ledger rows replace their initial estimates with reported usage. Thus
original pre-dispatch estimates for those completed rows are unavailable; no
historical values were reconstructed and presented as actual provider usage.

## Actual token accounting by stage

| Stage | Completed calls | Reported input | Reported output | Uncertain input allowance |
| --- | ---: | ---: | ---: | ---: |
| Literature context preparation | 0 | — | — | — |
| Provider preflights, including first resume | 2 | 150 | 46 | 0 |
| Feasibility | 1 | 913 | 430 | 0 |
| Planning, including schema repair | 2 | 4,296 | 1,067 | 0 |
| Ideas | 1 | 2,365 | 890 | 0 |
| Selection | 1 | 1,959 | 231 | 0 |
| Experiment specification | 0 | unknown | unknown | 20,240 across two attempts |
| Baseline/candidate/evaluation/synthesis | 0 | — | — | — |

Selected-source preparation is local and shares context with later model stages;
it is not a separate model call. The largest *retained* input charges are the two
uncertain specification reservations, followed by completed planning and ideation.

## Changes and safety boundaries

1. Added pure deterministic prompt projections. Planning/ideation receive at most
   480 characters per supplied abstract and 2,400 abstract characters total,
   up to ten stable IDs. Repeated IDs are deduplicated; identical abstracts are
   supplied once with an explicit source-reference marker. Missing/non-string or
   blank abstracts are omitted, never synthesized. Title excerpts are capped at
   200 characters and truncation is labeled. Later stages receive references,
   not repeated abstracts/authors/retrieval records.
2. Original selected snapshots, full available abstracts and provenance stay in
   run config/artifacts and grounding manifests. Hash/digest binding still uses
   the full evidence, not the compact model projection. Constraints and hypotheses
   are not truncated. ExperimentSpec must copy the selected hypothesis exactly.
3. Native context drops empty/out-of-stage outcome fields, reduces the selected
   idea projection, requests two concise idea variants, and avoids duplicating
   question/hypothesis beside the already complete candidate specification.
4. Response schemas previously appeared both in the text and structured-output
   envelope. Structured requests now send them once in the envelope. The existing
   same-model compatibility fallback includes the schema once in its JSON prompt.
   Annotation-only title/description/default/example fields are removed from the
   transmitted schema. Required fields, constraints, property names, references,
   protocol semantics and full application-side validation remain unchanged.
5. Native services default to one HTTP/transport attempt, exposing errors instead
   of spending three uncertain reservations automatically. Standalone router
   defaults are unchanged. Existing one-component repair and one same-model schema
   compatibility fallback remain explicitly bounded and fully accounted. No
   automatic provider switching is introduced.
6. Added a non-mutating request-fit check before model discovery/preflight and a
   second check inside the existing atomic reservation transaction. Early stages
   protect 10,240 input/4,096 output tokens and three calls for a minimal candidate,
   evaluation and report path. Candidate dispatch protects 6,144 input/2,048 output
   and two calls; evaluation protects 3,072 input/1,024 output and one call. A needed
   readiness preflight is also included in advisory capacity checks. These are
   conservative capacity floors, not promises that arbitrary prompts will fit.
7. Oversized requests report stage, estimated request size, remaining allowance,
   protected future allowance and no-dispatch status. Request-budget metadata is
   saved atomically with every new reservation so completed usage cannot erase
   the original estimate. Estimates remain UTF-8 bytes plus 64; no unverified
   characters/4 estimate or tokenizer was substituted. Failed/uncertain charges,
   unknown monetary cost and all existing budget ceilings remain intact.
8. Safe failure events now distinguish provider-reported context-length patterns,
   structured JSON failures, 404, authentication, 429, 5xx, timeout and other
   transport failure. Context-length rejections are typed so the worker pauses.
   Diagnostics include identifiers/status/category only, never provider bodies,
   headers, URLs, prompts, exception strings or credentials. Cancellation before
   reservation/checks makes no request or charge. These diagnostics do not recover
   missing historical statuses retroactively.

Output caps: feasibility/planning/ideas/evaluation/synthesis 1,024 each; selection
and evaluation declaration 512 each; specification/baseline 1,536 each; candidate
2,048; generation readiness preflight 128. Caps are further bounded by run limits.

## Prompt-size results — offline estimates, not provider measurements

Rebuilding the same retained specification-stage context with the new builder
projects **7,530** input allowance versus the retained **10,120**: **25.6% lower**.
Its schema shrinks from 3,324 to 2,625 compact JSON bytes. The schema also no longer
appears a second time in the structured request text. Actual provider-token savings
remain unmeasured. The reconstruction does not update the paused run.

A fresh SQLite/mock-Groq/stub-executor selected-paper scheduling integration
completed both approvals, candidate preparation, host evaluation and cited report.
The mock charged every successful input at its full conservative byte reservation,
rather than the usual fixed small fixture usage. No live scientific result is
implied. Its stage profile was:

| Stage | Estimated input reservation | Output cap |
| --- | ---: | ---: |
| Three readiness preflights combined | 234 | 384 |
| Feasibility | 1,679 | 1,024 |
| Planning | 2,583 | 1,024 |
| Ideas | 3,282 | 1,024 |
| Selection | 1,663 | 512 |
| Specification | 4,890 | 1,536 |
| Baseline | 1,749 | 1,536 |
| Evaluation declaration | 1,589 | 512 |
| Candidate | 2,119 | 2,048 |
| Evaluation | 3,431 | 1,024 |
| Synthesis | 3,301 | 1,024 |
| Total, 13 calls | **26,520** | **11,648** |

This small synthetic fixture completed under 20 calls/32k input/16k output. A live
paper, longer constraints, output quality, repairs and uncertain attempts change
the requirement. No live completion guarantee follows from the fixture.
The local ignored receipt is
`.research-platform/validation/reliability-v121/prompt-profile.json`.

## Validation and preservation

- Windows platform: **241 passed, 39 skipped, 4 deselected**.
- WSL Ubuntu platform: **280 passed, 4 deselected**.
- WSL CLI/Inspector: **41 passed**, native nvm/Node initialized, offline mode.
- Frontend: **21 passed**; Chromium **6 passed**, including complete selected-source
  workflow, both human gates and byte-identical frontend/Markdown report export.
- TypeScript, production build, Prettier, Ruff/check-format and Linux-target mypy
  (**36 platform/backend sources**) pass. Existing build-size/deprecation warnings
  remain. There is no separate frontend ESLint script.

New regressions cover large/duplicate/malformed source context, annotation-safe
schemas, HTTP 400/404/429/503, timeout, rejection before discovery or generation,
atomic future-stage capacity, cancellation, repair-loop refusal and restart with
uncertain reservations. Existing worker recovery, concurrent accounting, both
supported native protocols, citation binding, report exports and HTTP 409 original
launch restriction tests remain passing. Selected-protocol integration tests now
charge full estimated input to exercise the 32k budget rather than tiny mock usage.

An initial WSL test-fixture import mechanism failed to expose shared fixtures;
explicit fixture aliases fixed it. Golden tests for old output caps were updated
to the deliberately smaller stage caps. Final suites pass without test retries or
network-provider access. Docker-running research cases were deliberately excluded.

Before/after read-only hashes cover each preserved run's complete run row,
ledger, artifact metadata, experiments, decisions and events, sorted by ID:

| Run | Preserved snapshot SHA-256 |
| --- | --- |
| 060988269faf4d1dbfde7a362b4718fb | be85273ba3d3dea8f5802e8e89654fbaacc29397a0ef3ac544f96ebccd96ced8 |
| be08d9e5f154486ea8b1ff9eebce6882 | 75a97ec9ea3194606a5dd553060e1285f57cb619795f3dc6f12e83abbf71c3c6 |
| e2dcc7048b654d0daef9ba68d5010079 | 201ee722073883ad3f5d610a9b2d069bbe61242adc3345004c560aaf13eceeef |

No counter reset, reservation release, approval edit, resume or historical artifact
rewrite. All **54 retained artifact files** across these three runs also match
their stored byte sizes and SHA-256 hashes. The original scheduling measurement
audit retains snapshot f1407818736521ad9fb6140da6edf5b3b56646e86c60e18d916eba9c61a41e77.
Existing secrets/databases/caches/validation receipts remain ignored.
The local launcher was restarted with generation blocked, after confirming only
done/waiting jobs, to load the changes. No external request is needed to browse
http://127.0.0.1:5180/literature. Stop/start instructions remain in LOCAL_APPLICATION.md.

## Commands

Windows, repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -k 'not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline or selected)' -q --tb=short
.venv\Scripts\python.exe -m ruff check src/research_platform tests/research_platform
.venv\Scripts\python.exe -m ruff format --check src/research_platform tests/research_platform
.venv\Scripts\python.exe -m mypy --platform linux --follow-imports silent src/research_platform apps/research_platform/backend
```

WSL, same repository path `/mnt/d/project/reseon/AI-Scientist-v3`: source
`/home/sonusunny/.nvm/nvm.sh`, then use
`/home/sonusunny/.local/share/agsci-mission1-venv/bin/python` with the same pytest
selection and `GEMINI_CLI_OFFLINE_TEST=1`. CLI check:

```bash
GEMINI_CLI_OFFLINE_TEST=1 /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py -q --tb=short
```

Frontend directory: `npm.cmd run test`, `npm.cmd run typecheck`, `npm.cmd run build`,
`npm.cmd run format:check`. Browser fixture:

```powershell
.venv\Scripts\python.exe tests/research_platform/offline_native_server.py --offline-boundary --mock-literature --state .research-platform/validation/reliability-v121/browser-fixture --port 8012
```

Fresh state path required. In frontend set PLATFORM_URL=http://127.0.0.1:5182,
PLATFORM_FRONTEND_PORT=5182, RESEARCH_API_URL=http://127.0.0.1:8012,
NATIVE_OFFLINE_E2E=1; run `npm.cmd run test:e2e -- --workers=1`.
The test-only server was stopped after verification.

## Proposed live acceptance — subsequently authorized to the first gate

Keep the paused run unchanged. It cannot fit its next full specification request
under the remaining allowance, even after compaction. Recommend a fresh run only
after explicit authorization and current Free-plan confirmation:

- Groq / openai/gpt-oss-20b; one explicitly selected retained paper, Lee (1991),
  DOI https://doi.org/10.1057/jors.1991.170. Use cached genuine metadata; no new
  scholarly query is required. The abstract concerns quadratic lateness, so the
  native total-completion-time comparison is related-method context only.
- Scheduling_v1, FIFO versus SPT, 32 jobs, durations 1–10, seeds
  [42,123,456,789,101112], identical paired inputs. Preserve both approval gates;
  exact contract and grounding/dataset digest must be reviewed before execution.
- **20 total generation attempts, 40,000 input and 16,000 output tokens,
  one iteration and one experiment attempt, 300 active seconds**. This is a proposed
  NEW run's budget, not a change to any past run. Nominal no-repair path: 13 calls.
  Allow approximately 30–34k conservative input for the small real source/design,
  plus 6–10k contingency; these are projections, not provider usage. Capacity
  guards can still stop safely if responses or failures exceed the allowance.
- Nominal stage guidance: preflights <0.3k input combined; feasibility ~2k,
  planning ~3–4k, ideas ~4k, selection ~2k, spec ~5–6k, baseline ~2–3k,
  declaration ~1.6k, candidate ~2–3k, evaluation/report ~4k each. Caps above total
  11,648 nominal output tokens, leaving 4,352 for bounded repairs.
- Each isolated process: 1 CPU, 256 MiB, 64 PIDs, 10 seconds, no network/mounts.
  One experiment entails ten program executions (baseline/candidate per seed).
  No paid fallback/provider switch or automatic budget increase. Unknown cost
  stays null; account Free-plan status needs operator confirmation, not inference.
- No claim of novelty, paper reproduction or statistical significance. Five paired
  seeds cannot produce p<0.05 in the exact two-sided sign-flip test (minimum .0625).

Live acceptance remains incomplete until a separately authorized new run generates
a candidate, executes the exact approved contract, evaluates genuine measurements
and produces a cited report. This change does not mark it complete.

## Separately authorized live check — first gate

After the offline report/tests, the user explicitly authorized the proposed fresh
20-call/40k-input/16k-output/one-iteration/one-experiment run and confirmed current
Free plan/no paid usage. A key-bound attestation was applied to service-process
environment only; no key or `.env` was changed/displayed. Read-only Docker checks
confirmed the existing Linux daemon and existing reviewed image, with no pull,
installation or research execution. The cached paper snapshot was reused without
a new scholarly request. A separate project/run was created via the existing API:
HTTP 201, **42dd6acadbb54b17870c66ed6737215a**.

Current state: **awaiting_approval / research_plan**, not approved or resumed.

| Real completed stage | Initial input reservation | Reported input | Reported output |
| --- | ---: | ---: | ---: |
| Readiness preflight | 78 | 75 | 23 |
| Feasibility | 2,512 | 589 | 463 |
| Feasibility schema repair | 2,634 | 607 | 463 |
| Planning | 4,281 | 1,024 | 746 |
| Planning schema repair | 4,482 | 1,059 | 572 |
| Totals | per-request estimates, not cumulative charged usage | **3,354** | **2,267** |

Five of 20 calls used, all completed, no uncertain reservations. Remaining allowance:
36,646 input / 13,733 output tokens, 15 calls; approximately 5.02 active seconds
used. Cost remains unknown/null. No provider_attempt_failed event occurred, so no
rate-limit/HTTP/timeout failure is being claimed. The original estimates are now
retained independently in atomic request_budget events, demonstrating that they
remain distinguishable from actual reported usage.

Both original failed-schema responses are retained. First feasibility exceeded
the assumptions-list limit; the bounded repair validated. First planning response
misplaced required fields and exceeded the steps limit; its single repair validated.
These are completed real generations rejected by application schema validation,
not uncertain network attempts or fabricated fallback outputs. Feasibility's direct
caller currently does not emit local rejection events; its raw response and budget/
usage events allow the above independent validation. Native HTTP failure diagnostics
remain separate and are exercised with mocks, not deliberately induced live errors.

The resulting plan retains the exact selected DOI on both hypotheses, uses the
authorized 32 jobs/durations/seeds/resources, and treats the paper as method context.
No candidate, prepared contract, final digest, experiment or report exists yet.
The first review dialog was inspected in the real frontend without any mutation.
URL: http://127.0.0.1:5180/workspace/42dd6acadbb54b17870c66ed6737215a.

First-gate clarification requested: use mean FIFO-minus-SPT as the single primary
outcome; positive-seed fraction is descriptive and is not the exact sign-flip
p-value. Use only actual host-computed statistics, with assumptions and no automatic
significance claim; do not promise an uncomputed median. Both paper-scoping and
pairing constraints stay unchanged. Preparation still requires this human approval;
candidate generation/execution requires the later separate digest-bound approval.

The paused v1.2 run and both completed historical snapshots/reservations remain
unchanged. Full live acceptance is still incomplete at this first gate.

## Exact v1.2.1 file changes

New: `src/research_platform/prompt_budget.py`,
`tests/research_platform/test_prompt_budget.py`, this document.

Modified:

- `src/research_platform/providers.py`: single schema transmission, annotation
  compaction, early check hook and typed/classified safe failure diagnostics.
- `src/research_platform/services.py`: native single-attempt default, stage output
  allocations, preflight-aware advisory checks and atomic request-budget events.
- `src/research_platform/ledger.py`: atomic protected-capacity checks and diagnostics.
- `src/research_platform/workflow.py`: stage-specific compact literature/idea context
  and concise planning/ideation/evaluation/synthesis allocations.
- `src/research_platform/preparation.py`: reference-only literature during spec
  preparation, exact hypothesis instruction and reduced candidate duplication.
- `tests/research_platform/test_native_application.py`: optional prompt profiling
  and conservative-input selected-protocol integrations.
- `tests/research_platform/test_providers.py`: require schema once in the envelope.
- `tests/research_platform/test_native_workflow.py`, `test_preparation.py`: explicit
  assertions for the smaller stage output caps.
- `docs/LITERATURE_GROUNDED_RESEARCH_V1_2.md`, `docs/DEVELOPMENT_PROGRESS.md`,
  `docs/LOCAL_APPLICATION.md`: current status and reliability guidance.

Earlier uncommitted v1.2 files remain present and were not discarded or committed.
