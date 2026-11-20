# ISSUE-04 and ISSUE-05 implementation and verification

Date: 2026-11-20 (Asia/Calcutta)

Current status after final verification on 2026-11-20:

- **ISSUE-04 resolved for Groq / openai/gpt-oss-20b**: explicitly authorized live
  generation returned HTTP 200 and `OK`; accounting and frontend display verified.
- **ISSUE-05 resolved for this WSL Ubuntu host**: native Linux Node/npm/npx verified,
  with latest doctor result **13 OK, 7 warnings, 0 failures**.
- Gemini API generation and other provider/model combinations remain unverified.
  Gemini CLI installation is not evidence of Gemini API generation availability.

The earlier verification sections below are historical evidence. The final
verification section supersedes their previously outstanding runtime blockers.
No system components or optional CLI agents were installed during this task.

## Root causes and changes

ISSUE-04: discovery health was labelled ready even though it only queried model
metadata. Research calls lacked a real generation preflight. The UI also selected
the first discovered model automatically. The worker now sends one bounded
128-output-token preflight before research calls for each selected provider/model,
with no preflight retry or provider fallback. Its reservation uses the existing
run ledger and daily cap. Failed/uncertain requests retain reservations; unknown
pricing remains null. Success is cached only for the current services instance;
worker resumes recheck on the next model call. This consumes one of the run's
configured calls (20 by default), not a separate free quota. Discovery and
point-in-time generation verification are distinct statuses.

Structured readiness events contain safe diagnostics, HTTP status, retryability
and remediation. GET /api/runs/{run_id}/provider-readiness only reads these events;
polling never calls a model. An idle paused native genuine run can explicitly
replace all future model selections using PATCH /api/runs/{run_id}/model, retaining
its ledger, checkpoint and budgets. The UI supports selection and a separate
resume. Existing explicitly configured fallback attempts emit selection events
and must pass preflight. Full original research launch still returns HTTP 409;
Groq selection does not imply Gemini CLI compatibility. Workflow integration is
in ResearchServices.model; the graph and execution approval gates are unchanged.

ISSUE-05: doctor accepted tools merely found on PATH and did not validate the
Node runtime platform or version. Ubuntu had no node, but found Windows npm/npx.
Doctor now checks node/npm/npx execution, verifies Node's process.platform,
process.version and process.execPath, rejects Windows paths/executables on Linux,
and enforces >=22.18.0. This matches the documented platform minimum, the Node 22
agent image and Autoillustrate's >=22 requirement. Tests cover missing tools,
broken package managers, unsupported versions, native Linux and Windows runtimes,
and Windows tools accidentally resolved in WSL.

## Exact files changed by this task

- src/research_platform/providers.py
- src/research_platform/services.py
- apps/research_platform/backend/app.py
- apps/research_platform/frontend/src/create.tsx
- apps/research_platform/frontend/src/run.tsx
- apps/research_platform/frontend/src/test/platform.test.tsx
- src/agsci/doctor.py
- tests/pipeline/test_agsci_cli.py
- tests/research_platform/test_providers.py
- tests/research_platform/test_storage.py
- tests/research_platform/test_api.py
- docs/install.md
- docs/RESEARCH_PLATFORM_API.md
- docs/ISSUE_04_05_REPORT.md

Substantial pre-existing modifications/untracked files were present before work.
They were preserved. No new checkout, virtual environment, database migration,
provider-key change, Docker configuration change or system installation was made.

## Earlier Windows verification

Runtime: PowerShell 7.6.9, checkout D:/project/reseon/AI-Scientist-v3,
existing .venv Python 3.13.14. Windows Node v26.13.1 is installed; npm and npx both report 11.20.0.
The actual Windows Node runtime probe reports process.platform=win32.

From the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -q
# 148 passed; one existing LangChain pending-deprecation warning
.venv/Scripts/python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform src/agsci/doctor.py tests/pipeline/test_agsci_cli.py
# All checks passed
.venv/Scripts/python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform src/agsci/doctor.py tests/pipeline/test_agsci_cli.py
# 39 files already formatted
.venv/Scripts/python.exe -m mypy src/research_platform/providers.py src/research_platform/services.py apps/research_platform/backend/app.py src/agsci/doctor.py --follow-imports=silent
# Success: no issues found in 4 source files
git diff --check
# passed; Git also reported an existing uv.lock line-ending warning
```

From apps/research_platform/frontend:

```powershell
npm.cmd run build
# passed; existing large-chunk warning
npm.cmd test
# 11 passed
npm.cmd run typecheck
# passed
npx.cmd --no-install prettier --write src/create.tsx src/run.tsx src/test/platform.test.tsx
# formatted changed UI files
```

A plain upstream pytest invocation is blocked on Windows by the existing Unix-only
fcntl import in src/orchestrator/state.py. The documented isolated platform test
command above passes without changing that upstream code. Importing the actual
Windows doctor module also hits this pre-existing fcntl dependency; native Windows
Node was verified directly, while validator Windows behavior was tested through
injected hosts in the Linux CLI suite. Full Windows platform
mypy reports 11 existing Unix-API errors in upstream_worker.py; focused checks pass,
and full platform mypy passes in Linux. Initial regression failures caused by
changed preflight retry and explicit-selection behavior were corrected in tests;
the final test runs above passed.

## Earlier WSL verification

`wsl --list --verbose` found Ubuntu and docker-desktop, both WSL2, initially stopped.
Ubuntu was started for checks. Commands ran against the SAME requested checkout:
/mnt/d/project/reseon/AI-Scientist-v3. An already-existing Linux interpreter at
/home/sonusunny/AI-Scientist-v3/.venv/bin/python (Python 3.11.18) supplied installed
test dependencies; that other checkout was not used as the source or modified.
The distro's default python3 is 3.14.4. Windows Node was never treated as Linux Node.

From Ubuntu in the requested checkout (PY below is just a command abbreviation):

```bash
PY=/home/sonusunny/AI-Scientist-v3/.venv/bin/python
$PY -m pytest tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py -q
# 41 passed
$PY -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent
# Success: no issues found in 28 source files
$PY -m pytest tests/research_platform --confcutdir=tests/research_platform -q
# 148 passed
$PY -m src.agsci.main doctor --json
# ok:false; actual Node/PATH and Docker failures correctly diagnosed
```

Actual doctor results: node missing; npm/npx rejected because they resolve under
/mnt/c/Program Files/nodejs. Docker client is installed but the Docker Desktop
Linux-engine pipe is unavailable, confirmed from Windows and WSL. Optional agent
CLIs, GPU visibility and agent-image/frontend availability produce their own
warnings. Doctor does not establish full original-engine readiness on this host.

## Earlier provider verification and outstanding actions (superseded below)

Only presence booleans were inspected: GEMINI_API_KEY and GROQ_API_KEY settings
exist; validity was NOT tested. All successful/failing generation evidence here
uses deterministic HTTP test fixtures. No provider output is claimed as live
readiness. Live credentialed preflight requires separate explicit authorization
under the task instructions. A real native run then performs preflight on its
existing ledger; no unaudited standalone request is needed.

Native WSL Node is still missing. Exact optional per-user nvm installation,
PATH checks and doctor rerun commands are in docs/install.md under
“Native Node.js in Ubuntu/WSL”, based on https://github.com/nvm-sh/nvm.
They install Node 22 LTS inside Ubuntu without changing Windows Node. They were
provided for operator approval/execution, not run. No WSL/Ubuntu/Docker reinstall
is needed. Start the existing Docker Desktop manually if execution is desired,
then verify `docker info`; the agent image and other doctor warnings still need
independent checks. No live Docker research experiment was run.


## Final verification — 2026-11-20

### ISSUE-05: resolved for the verified Ubuntu host

Native tools resolve to:

```text
node /home/sonusunny/.nvm/versions/node/v26.13.1/bin/node
npm  /home/sonusunny/.nvm/versions/node/v26.13.1/bin/npm
npx  /home/sonusunny/.nvm/versions/node/v26.13.1/bin/npx
```

The runtime probe returned platform `linux`, version `v26.13.1`, and the native
Linux executable above. npm/npx report 11.20.0; Gemini CLI reports 0.68.0.
Node 26.13.1 satisfies the repository's >=22.18.0 requirement. Doctor using
/home/sonusunny/.venvs/ai-scientist-v3/bin/python (Python 3.12.16) reports `ok:true`,
**13 OK, 7 warnings, 0 failures** in the saved final JSON. Docker CLI resolves to
/usr/bin/docker, daemon is reachable and the agent image is present. The seven
warnings concern GPU visibility, optional Claude/Cursor/OpenCode/pi/Autoillustrate
CLIs, and the unbuilt inspector frontend. None is a required Node readiness failure.
No optional CLI agents were installed. The user's hello-world result was not
rerun; actual isolated experiment tests below independently exercised Docker.

Important launch distinction: a plain noninteractive `bash -lc` does not source
nvm on this machine and still finds Windows npm/npx with no node. The verified
interactive Ubuntu shell loads nvm correctly. For unattended jobs explicitly
source `/home/sonusunny/.nvm/nvm.sh` or configure the native bin directory in the
job's PATH; no system PATH or shell configuration was changed here.

Commands actually executed (from PowerShell unless otherwise noted):

```powershell
wsl --list --verbose
wsl -d Ubuntu -- bash -ic 'command -v node npm npx gemini; node -p "JSON.stringify({platform:process.platform,version:process.version,execPath:process.execPath})"; npm --version; npx --version; gemini --version; /home/sonusunny/.venvs/ai-scientist-v3/bin/python --version; cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.venvs/ai-scientist-v3/bin/python -m src.agsci.main doctor --json'
wsl -d Ubuntu -- bash -ic 'cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.venvs/ai-scientist-v3/bin/python -m src.agsci.main doctor --json' | Out-File -LiteralPath .research-platform/validation/issue-04-05-final/doctor.json -Encoding utf8
docker ps --format '{{.Names}} {{.Ports}}'
```

Existing unrelated AegisFlow services on ports 8000/5173 were inspected and left
untouched. This project's read-only verification server used port 8876 and was
stopped afterward. No research worker was started.

### ISSUE-04: live generation and accounting verified

Before any provider request, the operator explicitly authorized this exact run,
provider, model, prompt and request limits in chat. Existing configured key
presence was checked without displaying values. Only the authorized Groq identity
was used. This is a real provider response, not an HTTP fixture:

| Field | Actual evidence |
|---|---|
| Existing run | e2dcc7048b654d0daef9ba68d5010079 |
| Existing database | .research-platform/validation/mission1-20261117/live/metadata.db |
| Provider / model | Groq / openai/gpt-oss-20b |
| Prompt | Reply with OK. |
| Output limit | 128 tokens |
| Discovery requests | 1 GET, HTTP 200 |
| Generation requests | 1 POST, HTTP 200 |
| Actual generated response | `OK` |
| Readiness | generation_verified: true |
| Verified event time | 2026-11-20 12:17:19 IST (06:47:19 UTC) |
| Before / after model calls | 16/20 -> 17/20 |
| Remaining calls | 4 -> 3 |
| Provider-reported usage for this probe | 75 input, 23 output tokens |
| New ledger row | dbb725c109d04d0394567a0d856772a4 |
| Ledger stage / status | provider_preflight / completed |
| Remaining input capacity | 8021 -> 7946 |
| Remaining output capacity | 7733 -> 7710 |
| Estimated monetary cost | null before and after; unknown, not zero |
| API errors or quota rejection | none |

The verification invoked the existing
`ResearchServices.generation_preflight("groq", "openai/gpt-oss-20b")`, which calls
`ProviderRouter.preflight()` with its existing accounting callback. The metadata
GET is discovery only; the generation POST added exactly one existing-ledger row.
An operator-owned idle job lease was acquired and released without queuing,
resuming or executing a campaign. Request hooks enforced the approved host,
endpoint, identity, prompt, output cap, one GET and one POST. No retry, fallback,
provider/model change, budget reset or reservation refund occurred.

The completed run status, previous current stage, research state, configuration,
approval and error/control fields were preserved; the job returned to `done`
with no owner or lease. A before/after SHA-256 signature verified saved state
and configuration preservation. No historical experiment or research-artifact
writes were performed. Only authorized audit events, readiness, usage accounting
and elapsed verification runtime were added. Provider-generated hidden reasoning
and response envelopes were not exposed; the visible response and usage above
are sufficient evidence of generation.

The one-shot local runner and machine-readable receipt are retained under
`.research-platform/validation/issue-04-05-final/`. The runner refuses to execute
again while its receipt exists. Do not rerun it: authorization was for one attempt.

```powershell
.venv/Scripts/python.exe .research-platform/validation/issue-04-05-final/authorized_preflight.py --execute-authorized-once
```

### Frontend/API verification

The built frontend was opened in installed Chromium through Playwright against
a temporary local API server with all writes and provider endpoints disabled.
The server served this existing database, not a synthetic readiness fixture.
The actual rendered status was:

```text
groq / openai/gpt-oss-20b: generation_verified. Bounded generation succeeded at this time; future requests may still fail.
```

GET /api/runs/{run_id}/provider-readiness returned HTTP 200 and the same persisted
readiness event. Refresh displayed Completed and 17 model calls; usage remained
17/20 with 3 remaining. The browser made only local GET requests, no provider
endpoint requests and no JavaScript errors. It was prevented from accessing
external origins. A screenshot and the request/result log were saved. The
verification server was then stopped.

Two UI regression cases were added to
apps/research_platform/frontend/src/test/platform.test.tsx, checking successful
and failed readiness rendering and that refreshing does not call providers.
No production application code was changed during final verification.

### Final automated validation

| Environment / check | Actual result |
|---|---|
| Windows platform suite | 148 passed, one existing LangChain pending-deprecation warning |
| Existing Linux platform environment (Python 3.11.18) | 148 passed |
| Current Linux Python 3.12.16, CLI/doctor/inspector tests | 41 passed |
| Actual Docker experiment regression tests (Windows client) | 2 passed, 21 deselected; scheduling and regression protocols |
| Frontend Vitest including readiness display regressions | 13 passed |
| Frontend production build | passed; large-chunk warning only |
| Frontend TypeScript check | passed |
| Python Ruff lint | passed |
| Focused Python mypy, four changed production files | passed |
| git diff --check | passed; existing uv.lock line-ending warning |

Commands executed:

```powershell
.venv/Scripts/python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -q
wsl -d Ubuntu -- bash -lc '. /home/sonusunny/.nvm/nvm.sh; cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/AI-Scientist-v3/.venv/bin/python -m pytest tests/research_platform --confcutdir=tests/research_platform -q'
wsl -d Ubuntu -- bash -lc '. /home/sonusunny/.nvm/nvm.sh; cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.venvs/ai-scientist-v3/bin/python -m pytest tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py -q'
.venv/Scripts/python.exe -m pytest tests/research_platform/test_dynamic_execution.py -k actual_docker -q --confcutdir=tests/research_platform
npm.cmd --prefix apps/research_platform/frontend test
npm.cmd --prefix apps/research_platform/frontend run build
npm.cmd --prefix apps/research_platform/frontend run typecheck
.venv/Scripts/python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform src/agsci/doctor.py tests/pipeline/test_agsci_cli.py
.venv/Scripts/python.exe -m mypy src/research_platform/providers.py src/research_platform/services.py apps/research_platform/backend/app.py src/agsci/doctor.py --follow-imports=silent
git diff --check
```

The Python 3.12.16 environment was also tried for the full platform suite: it
stopped during collection with five import errors because SQLAlchemy/LangGraph
platform extras are absent. No dependencies were installed. Its CLI suite and
doctor pass; platform regression coverage used the already-existing Linux 3.11.18
environment against the requested checkout. No duplicate project was created.
The actual Docker tests use isolated test fixtures and independent evaluators;
no model requests or research campaign are involved.

### Evidence and remaining limits

- `.research-platform/validation/issue-04-05-final/doctor.json`
- `.research-platform/validation/issue-04-05-final/live-preflight.json`
- `.research-platform/validation/issue-04-05-final/frontend-verification.json`
- `.research-platform/validation/issue-04-05-final/live-readiness.png`

ISSUE-04 is resolved for the tested Groq account/model/endpoint at verification
time. Future quota/access changes can still fail. Gemini API generation and
other model combinations have not been live-verified, and original full-research
HTTP 409 protection remains in place. ISSUE-05 is resolved for the correctly
initialized WSL environment; noninteractive jobs must load nvm explicitly.
Python 3.12 platform extras remain a separate environment dependency gap.
The unrelated existing Windows upstream fcntl limitation was not changed.
