# Local deployment and operation

Updated for native protocol 2, 2026-11-18. This checkout supports a single-user
workspace bound to loopback. Public hosting, shared tenancy, remote native
execution and original-engine web submission are not configured by these steps.
See [the architectural scope](ARCHITECTURAL_CORRECTIONS.md) and
[acceptance evidence](RESEARCH_ENGINE_ACCEPTANCE.md) before treating a software
check as a completed research campaign.

## Preserve the current installation

Run commands from the repository root. Reuse an existing environment and secret
file when present. API and worker must use the same code revision and the same
`DATABASE_URL`, `CHECKPOINT_PATH` and `ARTIFACT_ROOT`. Do not point a new test
instance at an existing research database or overwrite an existing `.env`.

The [configuration example](../.env.example) supplies nonsecret defaults. The
default profile/provider are `demo`/`mock`; credentials are unnecessary for a
demo. The API's `APP_ENV` value is descriptive and does not enable public
authentication.

## Windows / PowerShell

For a fresh environment, use Python 3.11+ and an available supported Node/npm
installation. The Mission 1 Windows environment used Python 3.13.14 and Node
26.13.1. These commands preserve existing environment/configuration paths:

```powershell
if (-not (Test-Path -LiteralPath '.venv')) { py -3.13 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e ".[platform]"
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
npm.cmd --prefix apps/research_platform/frontend ci
.\.venv\Scripts\python.exe -m src.research_platform.dev
```

If Windows Application Control rejects native `ormsgpack`/`xxhash` extensions,
use the tested official compatibility constraints rather than changing system
security policy:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[platform]" -c requirements-platform-windows.txt
```

[Those constraints](../requirements-platform-windows.txt) select LangGraph
0.2.76, checkpoint 2.0.10, SQLite saver 2.0.3 and LangSmith 0.3.45. Mission 1
also repaired an incomplete local `msgpack` installation; that was an
environment repair, not a requirement to reinstall it on every machine.

The launcher runs API, a separate durable worker and Vite. Open the workspace
at <http://127.0.0.1:5173> and API documentation at
<http://127.0.0.1:8000/docs>. To avoid an occupied API port, pass `--port 8001`;
the launcher gives Vite the corresponding API proxy URL. Stop the launcher with
Ctrl+C; it cleans up its own child services and preserves persisted runs.

## Linux / WSL

Keep a Linux environment separate from a Windows environment when both access
this checkout. Use a distinct `UV_PROJECT_ENVIRONMENT` if necessary. A fresh
Linux setup can use:

```bash
uv sync --locked --extra platform
test -e .env || cp .env.example .env
npm --prefix apps/research_platform/frontend ci
.venv/bin/python -m src.research_platform.dev
```

The original pipeline and its POSIX tests belong in Linux/WSL. The separate
Mission 1 WSL environment and original CLI diagnostics are recorded in
[UPSTREAM_WORKER.md](UPSTREAM_WORKER.md). No GPU is required for the native
regression/scheduling protocols or the demo.

## Run a built frontend on one local origin

```powershell
npm.cmd --prefix apps/research_platform/frontend run build
.\.venv\Scripts\python.exe -m src.research_platform.dev --no-frontend
```

Open <http://127.0.0.1:8000>. The API serves the existing SPA build and the
launcher still starts the durable worker. Alternatively, launch the components
in separate terminals:

```powershell
# API terminal
.\.venv\Scripts\python.exe -m uvicorn apps.research_platform.backend.main:app --host 127.0.0.1 --port 8000
# Worker terminal
.\.venv\Scripts\python.exe -m src.research_platform.worker
# Frontend terminal, if using Vite instead of a built SPA
npm.cmd --prefix apps/research_platform/frontend run dev
```

For separately started Vite, set `RESEARCH_API_URL` if the API uses a different
port. Default permitted browser origins are localhost/127.0.0.1 on port 5173.
The API checks hosts/origins; these checks do not provide user authentication.
The launcher is a development supervisor, not an unattended service manager.

## Prepare genuine native execution

Start Docker Desktop's Linux engine on Windows, or the reviewed local Linux
daemon. Provision the image before launching a study:

```powershell
docker info
docker pull python:3.12-slim
docker image inspect python:3.12-slim --format '{{.Id}}'
```

Image retrieval above is an explicit operator operation. The experiment runner
does not pull images or install dependencies. `RESEARCH_CPU_IMAGE` can select an
operator-reviewed digest; each launch additionally resolves the local content
ID. Generated programs currently use only the approved standard library, and
each baseline/candidate runs separately without network, mounts, credentials or
the Docker socket. An unavailable daemon/image stops genuine execution.

Add only the credentials required by the chosen provider to the local `.env`:
`GEMINI_API_KEY` or `GROQ_API_KEY`. Ollama uses an already installed model at a
loopback `OLLAMA_BASE_URL`. Select models from provider discovery and verify
generation availability for the account. A listed model can still fail to
generate. Provider quota/free eligibility is external to this application.

Choose **Free research** and keep human approvals enabled. Native requests use
`execution_protocol=2`, `engine=native`; supported tasks are independently
evaluated synthetic regression and single-machine scheduling. The first gate
reviews research direction. The second shows the specification, baseline,
evaluation validation and frozen dataset commitment. Approve the displayed
digest only after reviewing that concrete experiment. Candidate code is authored
after this approval. Missing or mismatched approval digests do not advance.

The default run request is 20 calls, 32,000 input/16,000 output tokens, two
iterations, three experiment attempts and 300 active seconds. Default daily
requests are 100 and concurrency is one. Preserve the configured limits;
provider failures are not a reason to enable billing or raise budgets. Retries
and repairs consume calls, uncertain usage retains reservations, and approval
waits do not consume active runtime. The optional monetary cap rejects remote
calls whose cost cannot be established.

## Storage, updates and recovery

Default state is under the Git-ignored `../.research-platform/` directory:

| State | Purpose |
| --- | --- |
| `platform.db` | Projects, runs, job leases, usage ledger, events, artifact metadata |
| `checkpoints.db` | Durable LangGraph state and approval interrupts |
| `artifacts/` | Immutable downloadable evidence and generated source |
| `private-evaluations/` | Frozen host-owned fixtures and held-out targets; never exposed as public artifacts |

The fixture directory is a sibling of the configured artifact root. Back up the
metadata, checkpoints, artifacts and private fixtures together, with services
stopped or a consistent SQLite backup procedure. A downloaded report alone is
not sufficient to resume an experiment. Keep credentials separate from shared
evidence. API startup performs Alembic metadata upgrades; preserve a consistent
backup before changing versions. PostgreSQL metadata support is optional and
was not established as a tested deployment in this mission; checkpoints and
artifacts remain local files.

Update API and worker together. Genuine jobs use a versioned queue fence
(`queued_v2`/`running_v2`/`waiting_v2`) and obsolete genuine runs are refused.
Do not manually edit a job status or reset usage to bypass this boundary.
After a crash, heartbeat leases expire, graph state is recovered and a matching
completed receipt can be reused. A process without a valid receipt cannot be
resurrected; inspect the failed attempt and use explicit Resume only when the
remaining budget permits another attempt.

## Verify a local instance

Read <http://127.0.0.1:8000/api/health> and
<http://127.0.0.1:8000/api/system/capabilities>. Health proves the API/database
respond; it does not prove a worker, provider generation or experiment ran.
Capabilities should advertise execution protocol 2 and the two native domains.
The Docker readiness check must pass before genuine execution.

Complete a labeled no-key demo, including both approval gates. With development
test dependencies installed, the focused backend and frontend checks are:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -q
npm.cmd --prefix apps/research_platform/frontend run typecheck
npm.cmd --prefix apps/research_platform/frontend test
npm.cmd --prefix apps/research_platform/frontend run build
```

The dynamic-execution tests include real restricted Docker runs when Docker and
the reviewed image are available; otherwise they report skips. Tests using
fixture/model stubs are software checks and are not live research evidence.
The acceptance record identifies actual provider-backed studies separately.

## Tracing and original campaigns

Optional LangSmith export uses `LANGSMITH_TRACING=true`, a private
`LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`. Restart services after changing the
environment. Only explicit redacted spans export allowlisted identifiers,
counts and status; automatic graph tracing is disabled. Verify remote receipt
before claiming delivery from a stored SDK trace URL alone.

The original CLI, Inspector and bounded result importer remain available.
`full_research` web creation returns HTTP 409. Recovered standalone worker code
requires a dedicated native Linux controller, its own Docker socket/data root,
finite cgroup limits, private credentials and authenticated transport. The
ordinary workstation Docker daemon is not that dedicated worker boundary.
Original coding agents make nested provider requests outside the native
ledger; a hard request cap needs an enforceable provider gateway or a separately
approved operator quota policy. Cycle/time limits and a dry-run do not supply
that cap. Follow [the worker audit](UPSTREAM_WORKER.md); do not remove a dry-run
flag and treat the resulting campaign as budget-controlled by this web app.

Public deployment remains outside this release. A public service needs actual
authentication/authorization, tenant isolation, TLS, hardened execution,
supervision and a reviewed operating boundary. No reverse proxy or environment
flag in this checkout completes those requirements.


## Dedicated original-worker Phase 1 (2026-11-20)

The new [guest-only deployment configuration](../deploy/upstream-worker/README.md)
prepares a dedicated VM/controller/daemon; it must not be applied to this
workstation's normal Docker/WSL environment. [ISSUE_01_REPORT.md](ISSUE_01_REPORT.md)
records resource inspection, tests, approval requirements and remaining blockers.
Campaigns default to disabled, original web launch stays HTTP 409, and ISSUE-02
nested request accounting is still unresolved. No guest or system component was
installed by the repository preparation.


## Prepared nested-call gateway — 2026-11-20

[Gateway deployment runbook](../deploy/upstream-worker/GATEWAY.md) describes the
opt-in trusted POSIX service, migration 0002, private scoped CLI configuration,
TLS and prepared host-side restricted network. These assets are not deployed.
No shared Docker Desktop or host settings were changed. Back up existing state
before coordinated migration; no migration was applied to live research data.
Original launch remains disabled until isolated network and lifecycle validation;
see [ISSUE-02 report](ISSUE_02_REPORT.md) for exact offline results and blockers.


## Current native application launch — 2026-11-20

Use [LOCAL_APPLICATION.md](LOCAL_APPLICATION.md) for verified Windows/WSL startup,
Groq-only configuration, Free-plan attestation, start/stop and results/export.
Windows runs on 8010/5180 to preserve occupied 8000/5173 services. WSL serves the
built frontend with its existing native Python environment; do not replace shared
Windows node_modules to repair Linux Rollup. The authorized scheduling study
completed and its v1 read-only report presentation is verified; see
[verification report](LOCAL_APPLICATION_REPORT.md) and
[v1 checkpoint](RESEARCH_STUDIO_V1.md). Future live runs require fresh authorization.
