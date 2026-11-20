# Research engine acceptance — Mission 1

2026-11-20 Phase 1 update: original-worker deployment templates and contract tests
are prepared, but the dedicated guest is not provisioned or accepted. See
[ISSUE_01_REPORT.md](ISSUE_01_REPORT.md). Original campaign acceptance and web launch
remain blocked by infrastructure verification and ISSUE-02; no original campaign
was launched by this update.

Validation began 2026-11-17 and continued on 2026-11-18 (Asia/Calcutta).
The native two-domain research milestone **PASSED**. The separate original Sakana
campaign remains **BLOCKED**; this document does not declare full original-engine
acceptance. Existing source changes, credentials, projects and research artifacts
were preserved. All acceptance databases and outputs are isolated beneath
[`mission1-20261117/`](../.research-platform/validation/mission1-20261117/).

## Acceptance status

| Criterion | Status | Observed evidence |
| --- | --- | --- |
| Two genuine model-authored native studies | PASSED | Both runs completed; real Groq responses, generated code, Docker measurements and reports |
| Independent evaluation and fixed data | PASSED | Nine analytical/rejection checks; host-owned scorer, frozen private fixtures, exact digest approvals |
| Scientific measurement audit | PASSED | Independent weighted-duration and NumPy SVD references match every live seed; artifact/provenance/binding checks pass |
| Restricted Docker execution | PASSED | Separate baseline/candidate containers for all three seeds in both studies; no host execution fallback |
| Durable checkpoints and protocol compatibility | PASSED | SQLite reopen, failed-node recovery, pause/cancel, receipt reconciliation, missing/stale approval rejection and versioned job fence covered |
| Provider limits and failure accounting | PASSED | Both runs used 14 of their original 20 calls; failed/uncertain requests retained reservations; no billing or budget increases |
| LangSmith export | PASSED | 8 scheduling and 70 regression references; six sampled remote spans retrieved with empty inputs/outputs |
| Frontend and browser integration | PASSED | 11 React tests, 4 Chromium flows, and GET-only inspection of both genuine completed studies |
| Markdown and PDF reports | PASSED | Immutable Markdown downloads; browser PDF exports, six pages each, rasterized and visually reviewed |
| Original upstream regression suite | PASSED | 55 Linux/WSL tests; actual task-drafting gates, CLI and Inspector checks |
| Real original Sakana CPU campaign | BLOCKED | No campaign launched; nested coding-agent requests lack an enforced hard quota and compliant dedicated worker infrastructure is absent |
| Original web campaign launch | BLOCKED | Remains fail closed; recovered standalone worker/client are not connected to web submission |
| Public production hosting / multi-user authentication | NOT TESTED | Local loopback application only |
| PostgreSQL and distributed checkpoint/artifact storage | NOT TESTED | Acceptance uses SQLite and local files |

The native engine currently supports trusted small synthetic regression and
single-machine scheduling protocols. Unsupported questions stop at feasibility.
It does not claim arbitrary-domain science, scientific novelty, or a completed
original Sakana campaign. See [architectural corrections](ARCHITECTURAL_CORRECTIONS.md),
[deployment](DEPLOYMENT.md) and [original-worker diagnostics](UPSTREAM_WORKER.md).

## Study A — scheduling

Question: “Does shortest-processing-time scheduling reduce total completion time
compared with FIFO on the same fixed job set?”

- Run: `e2dcc7048b654d0daef9ba68d5010079`, status **completed**.
- Successful research provider/model: `groq` / `openai/gpt-oss-20b`.
- Protocol: `scheduling_v1`; 50 jobs, integer durations 1–10, one machine;
  paired seeds 42, 43, 44; 256 MiB, 10 seconds per generated process.
- Model-authored baseline returns FIFO indices. Model-authored candidate sorts
  job indices by duration. Both use the same input for each seed.
- Human experiment approval:
  `25d4c4a622a8102a253a18f05534fe0dd8ecbce08ded8a40863577c0d0c98db7`.
- Data commitment:
  `78356f8100d9ddfdddcd1253e5301039da1ed2542b40c67a25b1306a1215daba`.
- Baseline source:
  `d5e5ecbbe4a928fc0e2a79276c9e15d7721e2635f41ddf470cfb53b738384dff`.
- Candidate source:
  `f1c6ef1a1c0e883c908211a76e3dbce6fddfc4ef8c25a6068960afe7afb787ca`.

| Seed | FIFO total completion time | SPT total completion time | Reduction |
| --- | ---: | ---: | ---: |
| 42 | 7182 | 5029 | 2153 |
| 43 | 7193 | 5366 | 1827 |
| 44 | 7501 | 5145 | 2356 |
| Mean | **7292** | **5180** | **2112 (28.96%)** |

The paired Student-t 95% interval for the mean reduction is
[1449.0516, 2774.9484], conditional on its assumptions. The exact two-sided
sign-flip p-value is **0.25**. Three replications do not justify a significance
or universal superiority claim. The initial model hypothesis used “strictly
lower for any job set”; ties such as equal processing times are a counterexample.
The measurements establish improvement only for these three frozen job sets.

Evidence: [run/state](../.research-platform/validation/mission1-20261117/live/scheduling/run.json),
[events](../.research-platform/validation/mission1-20261117/live/scheduling/events.json),
[experiments](../.research-platform/validation/mission1-20261117/live/scheduling/experiments.json),
[graph/checkpoint history](../.research-platform/validation/mission1-20261117/live/scheduling/graph.json),
[usage ledger](../.research-platform/validation/mission1-20261117/live/scheduling/model-usage.json),
[artifact inventory](../.research-platform/validation/mission1-20261117/live/scheduling/artifacts.json).
The immutable [Markdown report](../.research-platform/validation/mission1-20261117/live/artifacts/e2dcc7048b654d0daef9ba68d5010079/65a648d8289925391d4a706dda694503)
has SHA-256 `c9c96cc9dff649a7291d6228bba36e31882545f2bbb1a0a596bb0368aced7e61`.

## Study B — regression

Question: “Does ordinary least squares improve held-out RMSE compared with a
training-mean predictor on a reproducible small linear regression dataset?”

- Run: `65742d40a84442a7b1fecedbee043d14`, status **completed**.
- Provider/model: `groq` / `openai/gpt-oss-20b`.
- Final protocol: `regression_v1`; 64 training and 32 held-out rows per seed,
  three features, linear coefficients [2, -1.5, 0.5], intercept 5, noise SD 0.5;
  seeds 42, 123, 987; 256 MiB and 10 seconds per generated process.
- The first concrete proposal claimed feature scaling beat raw OLS, which its
  two-arm experiment could not test. It was returned for model revision before
  execution, with an explicit constraint retaining the original primary question.
  The replacement specification and evaluator received a new digest approval.
- Generated candidate fits OLS with an intercept using matrix operations and
  Gaussian elimination with partial pivoting. It receives training labels and
  held-out features, **never held-out targets or evaluator source**.
- Approved digest:
  `aca4313751a56659d112ea80682afb736eae66854684242e0ba04568f6674891`.
- Data commitment:
  `3752c16638ae82feb49a8bcb35868752ea2df16e26db8f76a9d96a01457c657a`.
- Baseline source:
  `d8eeba878bbf251033f595a8acc6e52f73d9495e9487c8891ea762ec7ba96ce4`.
- Candidate source:
  `491b767a0c315425e685681c14411441463feb84609e6dc5971a88c25921a413`.

| Seed | Training-mean RMSE | OLS RMSE | Reduction |
| --- | ---: | ---: | ---: |
| 42 | 1.324594939 | 0.509298534 | 0.815296405 |
| 123 | 1.794901644 | 0.462615488 | 1.332286156 |
| 987 | 1.584137590 | 0.455774931 | 1.128362659 |
| Mean | **1.567878058** | **0.475896318** | **1.091981740 (69.65%)** |

The paired Student-t 95% interval is [0.445092632, 1.738870848]; the exact
two-sided sign-flip p-value is **0.25**. These are exploratory synthetic-data
measurements with three paired replications, not a generalization or significance
claim. Normal-equation OLS can be numerically unstable on ill-conditioned data;
this run's outputs independently match an SVD least-squares reference.

Evidence: [run/state](../.research-platform/validation/mission1-20261117/live/regression/run.json),
[events](../.research-platform/validation/mission1-20261117/live/regression/events.json),
[experiments](../.research-platform/validation/mission1-20261117/live/regression/experiments.json),
[graph history](../.research-platform/validation/mission1-20261117/live/regression/graph.json),
[usage ledger](../.research-platform/validation/mission1-20261117/live/regression/model-usage.json),
[artifact inventory](../.research-platform/validation/mission1-20261117/live/regression/artifacts.json).
The immutable [Markdown report](../.research-platform/validation/mission1-20261117/live/artifacts/65742d40a84442a7b1fecedbee043d14/073a8d21b81f056516d305450efe82bc)
has SHA-256 `f9f9362b309f70ca4ce8de5b17ab31037a8a6869e739f8a116df684a38507b7d`.

## Requests, failures and accounting

| Live run | All dispatched calls | Provider-reported input / output | Reported total | Final reserved input / output | Active seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scheduling | 14 | 9517 / 4055 | 13572 | 20241 / 7383 | 40.123 |
| Regression | 14 | 16083 / 5935 | 22018 | 16083 / 5935 | 61.431 |

Each run retained the existing limits: 20 calls, 32000 input tokens, 16000 output
tokens, 2 candidate iterations, 3 experiment attempts and 300 active seconds.
No monetary budget was raised, billing enabled, or implicit alternative selected.
Actual API price/free-tier eligibility remains unknown; unknown cost is not zero.

Scheduling contains four incomplete/failed dispatches: Gemini generation 404,
two Groq structured-output 400s, and one truncated synthesis. Their durable
reservations remain charged. Discovery listed `gemini-2.5-flash`, but generation
did not work for this account/endpoint. An explicit operator switch selected the
already-discovered Groq `openai/gpt-oss-20b`; it did not reset usage.

The structured-output failure exposed a missing schema in the actual prompt.
Provider schema metadata alone was insufficient. The router now transmits the
schema in the prompt as well as supported provider options, suppresses returned
reasoning, classifies malformed/truncated responses, and bounds component repairs.
The synthesis was recovered with a concise prompt and a stage allocation of 2048
output tokens inside the unchanged total budget. Its failed call was retained.

A Windows atomic-write temporary path reached 262 characters. Compact internal
fixture directories and short temporary names fixed it. Resuming evaluator
validation used **zero additional model calls** and reused the approved preparation.
UTF-8 artifact roundtrips pass; decoding source as Windows ANSI would corrupt
Unicode and correctly fail its digest.

Regression used 14 successfully reported calls, including its rejected proposal
and three replacement preparation components. No initial experiment was executed
under the rejected proposal. Model-generated semantic alignment is not proved by
JSON validation: concrete human review remains a required boundary.

Final source review found another defect: native selection context omitted the
generated idea list. The stored scheduling selection response was an error object;
regression returned `regression_v1` instead of an idea ID. The old narrative parser
silently chose the first idea. Both later concrete designs were explicitly reviewed
and approved, and their real measurements remain valid, but those selection calls
were **FAILED** autonomous decisions. The implementation now supplies the actual
options, validates typed narrative responses, bounds repair and rejects foreign
IDs instead of inventing a fallback. Targeted post-completion live validation,
if performed, is accounted separately in the same run budgets and never rewrites
the completed studies' scientific state or frozen criteria.

## Genuine execution, literature and tracing

Both result envelopes state `demo=false`, `protocol_version=2` and
`source=isolated_generated_trusted_protocol_v1`. The execution image was
`python:3.12-slim`, resolved to
`sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`.
Generated code was never executed/imported on the host. Twelve generated-program
containers performed the two live baseline/candidate comparisons. Containers used
non-root users, no network, no host mounts/socket/credentials, read-only roots,
capability dropping, no-new-privileges, and CPU/memory/PID/output/time limits.
Dependencies were standard-library only; no model-controlled installation ran.

The validation operator (Codex, acting under this implementation mission) reviewed
the persisted proposals and submitted separate approval API calls with their exact
digests. This exercises the same gate used by the React approval dialog; it is not
an independent human scientist's review. No claim of such a review is made.

The private fixtures, including their salt and held-out targets, are retained
outside downloadable artifacts under the isolated live root. Exact reproduction
requires that operator-owned fixture; published seeds and a data hash alone do not
reconstruct its private noise. The audit reads it as trusted validation code and
does not disclose its targets to a model or candidate process.

The [independent audit](../.research-platform/validation/mission1-20261117/live/measurement-audit.json)
verifies every artifact SHA, source equality with persisted real provider responses,
human approval/data bindings, and all seed measurements. Its trusted audit code
uses an independent weighted-duration formula and NumPy 2.5.4 SVD least squares;
it never imports or executes model-authored source. The maximum OLS reference
discrepancy is below 8e-16. Neither fixed demonstration programs nor prerecorded
responses were supplied by the [validation runner](../scripts/validate_research_engine.py).

Each study saved six OpenAlex literature metadata records with DOI/source URLs
and retrieval timestamps. Metadata retrieval does not establish paper relevance,
full-text verification or support for generated scientific claims. Model analysis
is explicitly labeled unverified; deterministic measurements/statistics are a
separate report section. Markdown reports are downloadable immutable artifacts.
PDF export uses the existing browser Print/PDF path, rather than the original
Sakana manuscript generator, whose real campaign remains blocked.

Tracing was initially disabled despite configured credentials. It was explicitly
enabled only for the scheduling synthesis recovery and throughout regression,
without editing the secret file. Earlier scheduling stages have no exported spans.
[Delivery evidence](../.research-platform/validation/mission1-20261117/live/langsmith-delivery.json)
records six successfully retrieved actual SDK spans with empty inputs/outputs,
safe metadata keys and no serialized errors. Automatic graph tracing remains off;
model prompts/responses, private datasets and credentials are excluded. Trace IDs
in state are correlation IDs; actual remote URLs come from saved SDK references.

## Exact validation commands

Commands run from the repository root in PowerShell unless marked Linux. Approval
commands below were separate operator invocations after reading saved proposals.
Re-running completed markers inspects them; use a new isolated root for new studies.

```powershell
# Initial scheduling call, availability failure and explicit alternative
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study scheduling --provider gemini --model gemini-2.5-flash --advance
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study scheduling --select-model --provider groq --model openai/gpt-oss-20b --resume
# Additional --resume invocations retained all failed reservations during diagnosis.
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study scheduling --approve research_plan
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study scheduling --resume
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study scheduling --approve 25d4c4a622a8102a253a18f05534fe0dd8ecbce08ded8a40863577c0d0c98db7
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study scheduling --resume --trace

.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study regression --provider groq --model openai/gpt-oss-20b --advance --trace
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study regression --approve research_plan --trace
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study regression --revise 'The primary comparison must be ordinary least squares versus the training-mean predictor on the same held-out data. The hypothesis must test whether OLS lowers held-out RMSE relative to that baseline only. Remove claims about feature scaling outperforming raw OLS, noise sensitivity, or training-size trends because those require additional experiment arms. Retain a reproducible small linear dataset and fixed seed replications.' --trace
.\.venv\Scripts\python.exe scripts/validate_research_engine.py --root .research-platform/validation/mission1-20261117/live --study regression --approve aca4313751a56659d112ea80682afb736eae66854684242e0ba04568f6674891 --trace

.\.venv\Scripts\python.exe .research-platform/validation/mission1-20261117/audit_measurements.py
.\.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform --basetemp=.test-tmp-mission1-strict-final -q
.\.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform scripts/validate_research_engine.py
.\.venv\Scripts\python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform scripts/validate_research_engine.py
.\.venv\Scripts\python.exe -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent --platform linux
npm.cmd --prefix apps/research_platform/frontend run typecheck
npm.cmd --prefix apps/research_platform/frontend test
npm.cmd --prefix apps/research_platform/frontend run build
git diff --check
```

Mypy uses Linux semantics because the standalone original worker intentionally
uses POSIX APIs and refuses Windows at runtime. This flag does not bypass its
runtime isolation checks. Windows checks exercise the native platform; upstream
POSIX tests run in a distinct WSL environment, not via stubs or modified algorithms.

```bash
cd /mnt/d/project/reseon/AI-Scientist-v3
UV_PROJECT_ENVIRONMENT=/home/sonusunny/.local/share/agsci-mission1-venv \
  /home/sonusunny/.local/bin/uv run --group dev pytest -q \
  tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py \
  tests/task_drafting/test_task_drafting_checks.py tests/task_drafting/test_task_qualification.py
UV_PROJECT_ENVIRONMENT=/home/sonusunny/.local/share/agsci-mission1-venv \
  /home/sonusunny/.local/bin/uv lock --check
UV_PROJECT_ENVIRONMENT=/home/sonusunny/.local/share/agsci-mission1-venv \
  /home/sonusunny/.local/bin/uv sync --locked --extra platform --group dev
UV_PROJECT_ENVIRONMENT=/home/sonusunny/.local/share/agsci-mission1-venv \
  /home/sonusunny/.local/bin/uv run --locked --extra platform --group dev \
  pytest tests/research_platform --confcutdir=tests/research_platform \
  --basetemp=.test-tmp-mission1-linux-strict -q
```

| Final check | Observed result |
| --- | --- |
| Windows platform / compatibility SDKs | **133 passed**, 70.66 seconds; includes real Docker tests, no skips |
| WSL platform / current locked SDKs | **133 passed**, 73.82 seconds; includes real Docker tests, no skips |
| WSL upstream CLI/Inspector/task-drafting | **55 passed**, 27.60 seconds |
| Mypy Linux target | PASSED, 28 source files |
| Ruff lint / format | PASSED |
| Lockfile / editor diagnostics / whitespace | PASSED; Windows has no uv executable, so lock check ran in WSL |
| Frontend typecheck / format / build | PASSED; build 40.72 seconds |
| React tests | **11 passed**, 28.13 seconds |
| Chromium flows | **4 passed**, 54.8 seconds |
| Completed genuine-study UI | PASSED, both studies; zero browser errors or mutation requests |
| Browser PDF export and raster QA | PASSED; 6 pages per genuine report, 2 for demo; zero PDF renderer errors |

The Linux environment uses Python 3.12.16, LangGraph 1.2.21, checkpoint 4.3.1,
SQLite saver 3.1.3, LangSmith 0.14.17, SQLAlchemy 2.1.8 and Pydantic 2.12.5,
installed with `uv sync --locked --extra platform --group dev` in the separate
environment. [SDK identities](../.research-platform/validation/mission1-20261117/linux-platform-sdk-versions.json)
and [Linux test log](../.research-platform/validation/mission1-20261117/linux-platform-tests.txt)
are saved. Windows retains its documented compatibility environment. The Windows
checkpoint dependency emits a deprecation notice; frontend builds retain the
existing large Monaco chunk advisory. Neither is a failed check.

[Backend log](../.research-platform/validation/mission1-20261117/backend-tests.txt),
[upstream log](../.research-platform/validation/mission1-20261117/upstream-tests.txt),
and [type-check log](../.research-platform/validation/mission1-20261117/typecheck.txt)
remain in the validation directory.

The [browser evidence and exact reproduction commands](../.research-platform/validation/mission1-20261117/browser/README.md)
include separate mock database startup on ports 5173/8011, the accepted Chromium
output directory, and API-only native inspection on port 8012 **without a worker**.
The final PDFs are [scheduling](../.research-platform/validation/mission1-20261117/browser/native-verified/scheduling-report.pdf)
and [regression](../.research-platform/validation/mission1-20261117/browser/native-verified/regression-report.pdf).
Chromium generated them through the existing print styles. Poppler was unavailable;
PDF.js 6.5.438, installed only in the ignored evidence directory, rasterized every
page for visual inspection. These are browser exports, not upstream LaTeX output.

Browser tests exposed and fixed stale approval cache state (a duplicate approval
409), rapid typing loss in the controlled Monaco draft, literal Markdown metric
tables, and dark print margins/skip-link overlays. The original failing traces are
preserved alongside the final passing run. Source previews remain read-only and
same-origin; local report edits do not alter server evidence.

## Original-engine gap

The original algorithms and CLI were preserved. The installed Headless 0.6.1
commit and Gemini CLI 0.68.0 agree on their generated flags. A read-only-home
diagnostic error disappeared with a writable ephemeral home; no genuine streaming
protocol defect was reproduced. Doctor and a bounded CPU dry-run were exercised,
but **zero real campaign phases completed** in this mission. Task drafting,
investigation, ablations, sealed final evaluation, post-hoc analysis and manuscript
generation remain unvalidated together under a real coding agent.

The ordinary workstation Docker daemon does not meet the recovered dedicated
worker's isolation contract. Nested Gemini CLI calls also bypass the platform
router's 20-call ledger. Finite idea/time limits do not enforce a provider-request
cap. A dedicated Linux controller/daemon with resource isolation plus an enforceable
provider quota boundary or separately approved operator budget policy is needed.
No available infrastructure or authorization established that boundary here.
The UI/API keep original campaign launch unavailable. No native study, mock test,
doctor result, dry-run or agent initialization is counted as that campaign.


## ISSUE-02 offline gateway checkpoint — 2026-11-20

Gateway-routed nested requests now use shared transactional ModelUsage accounting.
Installed Gemini CLI 0.68.0 text/tool SSE cases passed with a local mock provider;
concurrency tests enforce 20 dispatches maximum for a 20-call run. Linux platform
220 passed, Windows 181 passed/39 skipped, separate CLI/Inspector 41 passed.
Completed native run e2dcc7048b654d0daef9ba68d5010079 remains at 17/20 calls.

This is offline gateway acceptance only. No real provider calls or original
campaign were executed. Dedicated VM/daemon, TLS trust, grant lifecycle and actual
host-enforced direct-egress denial remain unvalidated. ISSUE-02 is partially
resolved; original campaign acceptance remains blocked and web creation HTTP 409
is preserved. See [ISSUE-02 evidence](ISSUE_02_REPORT.md).
