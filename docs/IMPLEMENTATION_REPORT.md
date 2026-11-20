# Research platform implementation report

## Mission 1 validated continuation — 2026-11-18

This section supersedes the fixed-circle scope and unavailable-runtime findings
in the historical 2026-11-14 report below. Existing work was preserved; later
dynamic source was recovered from an identified local validation image and
integrated selectively into the existing LangGraph and durable API/worker.

Native protocol 2 now performs question feasibility, real literature metadata
retrieval, model plans/ideas, component-level strict experiment preparation,
independent trusted evaluator validation, frozen dataset approval, model code
generation, restricted Docker measurements, bounded candidate iteration,
statistical summaries and evidence-grounded Markdown reports. The first trusted
domains are small synthetic regression and single-machine scheduling. Unsupported
questions fail feasibility. No genuine request silently runs the old circle
benchmark, a fixture or generated code on the host.

Two real Groq `openai/gpt-oss-20b` studies completed: scheduling mean total
completion time 7292 (FIFO) → 5180 (SPT), and held-out regression RMSE
1.567878058 (training mean) → 0.475896318 (OLS). Each used three frozen paired
seeds and 14 of its original 20 model calls. Independent numerical references,
artifact hashes, model-response/source hashes and human approval bindings passed.
Each exact sign-flip p-value is 0.25; these results do not establish significance
or novelty. The system preserves rejected/failed proposals and uncertain request
reservations instead of altering evidence to force a pass.

Validation passed 133 platform tests on Windows compatibility SDKs and 133 on
Linux/current locked SDKs, including actual Docker execution. A further 55 original
CLI/Inspector/task-drafting regressions passed in WSL. Type checking, lint,
formatting, lockfile verification and editor diagnostics passed. Frontend and
browser outcomes, live request/token ledgers, report paths and exact commands are
in [RESEARCH_ENGINE_ACCEPTANCE.md](RESEARCH_ENGINE_ACCEPTANCE.md).

The original Sakana engine is preserved but a real end-to-end campaign remains
**BLOCKED**. Its nested coding-agent calls are outside the platform request ledger,
and the compliant dedicated Linux controller/daemon is not provisioned. Standalone
recovered worker/client code is not advertised as deployed or wired to web launch.
The API keeps original campaign creation unavailable. Doctor/dry-run/parser checks
are diagnostics, not campaign results. Public hosting, authentication/tenancy and
PostgreSQL deployment remain unvalidated. See [UPSTREAM_WORKER.md](UPSTREAM_WORKER.md)
and [DEPLOYMENT.md](DEPLOYMENT.md).

## Historical implementation — 2026-11-14

Implemented 2026-11-14 in the existing SakanaAI/AI-Scientist-v3 repository,
starting at `df83138`. The initial working tree was clean. No original algorithm,
example, result, inspector or license file was removed or replaced. Changes are
uncommitted for review.

## A. Implemented architecture

The React/TypeScript/Vite workspace calls FastAPI REST endpoints and subscribes to
persisted SSE events. SQLAlchemy/Alembic store projects, runs, research items,
experiments, metrics, decisions, events, artifacts, usage, trace references and
jobs. A separate database-backed worker uses atomic claims, heartbeat leases,
ownership fencing and restart reconciliation. Long research does not run inside
HTTP requests or FastAPI BackgroundTasks.

The actual compiled LangGraph coordinates intake, planning, literature, ideas,
selection, experimental design, human interrupts, execution, collection,
evaluation, finite retry/iteration decisions, synthesis, reporting and validation.
Optional advanced phases are routed only when the execution adapter advertises
support. Its real compiled topology drives the UI graph. SQLite checkpoints use
an explicit JSON serializer allowing plain data and known interrupt types, without
arbitrary dynamic Python construction. Human pause time is excluded from the
active execution budget.

The provider boundary implements deterministic mock, Gemini, Groq and loopback
Ollama discovery and calls. Every model dispatch/retry reserves durable request
and token budget first. It handles 429, Retry-After, bounded jittered backoff,
context/output bounds, health errors and explicit fallback selection. Gemini
accounting includes reported thought tokens without exposing their content.
Unknown pricing remains unknown; monetary caps block unknown-price remote calls.

The scientist adapter retains the original engine as an independent trusted CLI
and reuses the existing Inspector parser for imported upstream evidence. Free
mode runs a fixed reviewed 26-circle packing comparison in restricted Docker.
There is no host execution fallback or generated-code execution path. Demo uses
explicit fixtures. Free-mode literature comes from cached OpenAlex metadata.
Reports distinguish recorded observations from unverified model interpretation,
include provenance/limitations, disclose AI generation, and retain attribution.

Optional official LangSmith spans cover safe project/run/stage/model identifiers,
counts, status and timings. Automatic graph tracing is disabled so it cannot
export raw state, prompts, documents, credentials or private error text. SDK trace
links are persisted only when actually supplied by the SDK. Tracing-disabled
research requires no account.

## B. Important files and changes

| Area | Files |
| --- | --- |
| Audit and design | [REPOSITORY_AUDIT.md](REPOSITORY_AUDIT.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |
| Settings/contracts | `src/research_platform/config.py`, `schemas.py`, root `.env.example` |
| Metadata and artifacts | `database.py`, `artifacts.py`, `checkpoints.py`, backend Alembic migration |
| Durable execution | `services.py`, `worker.py`, `workflow.py` |
| Runtime integrations | `providers.py`, `literature.py`, `execution.py`, `scientist_adapter.py`, `tracing.py` |
| API | `apps/research_platform/backend/app.py`, `main.py` |
| Frontend | `apps/research_platform/frontend/src/` and locked npm dependencies |
| Tests | `tests/research_platform/`, frontend Vitest/RTL and Playwright suites |
| Development | `dev.py`, PowerShell/Bash start scripts, VS Code tasks, optional platform dependencies, refreshed `uv.lock` |
| Documentation/CI | [setup](RESEARCH_PLATFORM.md), [API](RESEARCH_PLATFORM_API.md), [checkpoint](DEVELOPMENT_PROGRESS.md), dedicated CI workflow |

The frontend contains dashboard, guided creation, live workspace, ideas,
experiments/logs, stored metric charts, explainability, reports/artifacts,
provider/capability settings and project history with upstream imports. Dark/light
themes, keyboard search, responsive navigation and accessibility labels are
implemented. Monaco and workers are bundled locally and loaded on demand.
Paper edits are explicitly local browser drafts; immutable evidence is preserved.

## C. Installation

From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[platform]"
Copy-Item .env.example .env
npm.cmd --prefix apps/research_platform/frontend ci
```

For this machine's Windows Application Control compatibility:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[platform]" -c requirements-platform-windows.txt
```

Linux/WSL may use `uv sync --extra platform`. Detailed alternatives and the
tested compatibility versions are in [setup](RESEARCH_PLATFORM.md).

## D. Configuration

Demo uses `DEFAULT_MODEL_PROVIDER=mock`, `DEFAULT_MODEL=mock-researcher` and
`DEFAULT_RESEARCH_PROFILE=demo`, requiring no keys. Optional runtime keys:
`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENALEX_API_KEY` and `LANGSMITH_API_KEY`.
Ollama points to an installed local service/model. Model discovery supplies
current model IDs; free eligibility is determined by the provider account.
Provider secrets are read on the backend and never returned to the frontend.

Default budgets are deliberately small. Explicit per-stage and fallback models
are available in the typed API; the UI configures the primary model and research
budgets. Configure LangSmith only if wanted; it is off by default. Configure a
Docker image locally before genuine free-profile execution. The development
assistant's model or subscription does not configure application inference.

## E. Startup and URLs

```powershell
.\.venv\Scripts\python.exe -m src.research_platform.dev --port 8001
```

The implementation session uses API port 8001 because an existing service occupied
8000. The launcher automatically configures Vite's proxy to match.

- Workspace: <http://127.0.0.1:5173>
- Built workspace also served by API: <http://127.0.0.1:8001>
- API docs: <http://127.0.0.1:8001/docs>
- OpenAPI schema: <http://127.0.0.1:8001/openapi.json>

The normal default API port is 8000. The upstream Inspector remains separately
available through its existing `agsci inspect start` command on port 8765.

## F. Demo walkthrough

Choose **Launch a demo**, **Use example**, continue through configuration and
launch with human approval enabled. Approve the research plan, then the concrete
experiment proposal. Inspect the completed graph, fixture-labeled experiment,
decision journal and report. Download the Markdown report and experiment JSON.
Refresh or restart between gates to exercise persistent recovery. Browser paper
editing remains a local draft; browser print offers local PDF export.

## G. Actual validation results

Executed on Windows, Python 3.13.14, Node 26.13.1 and npm 11.20.0, using the
compatibility LangGraph/LangSmith dependency constraints. No live inference keys
or tracing account were used.

| Executed command / check | Observed result |
| --- | --- |
| `python -m pytest tests/research_platform --confcutdir=tests/research_platform --basetemp=.test-tmp-final -q` | **70 passed**; real graphs, SQLite/API/worker integration and failure paths |
| `python -m ruff check src/research_platform apps/research_platform/backend tests/research_platform` | Passed |
| `python -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform` | Passed after formatting |
| `python -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent` | Passed, 20 source files |
| `npm.cmd run typecheck` in frontend | Passed |
| `npm.cmd run build` | Passed; production assets generated |
| `npm.cmd test` | **5 Vitest/RTL tests passed** |
| `npm.cmd run format:check` | Passed |
| `npm.cmd run test:e2e` against Vite/API | Demo and mobile tests passed |
| `PLATFORM_URL=http://127.0.0.1:8001 npm run test:e2e` using equivalent PowerShell environment setting | **3 Playwright tests passed** against built SPA: demo/two gates/report, mobile/theme, local Monaco draft |
| Artifact downloads | Six report/evidence files returned 200 and expected byte sizes; API tests assert content |
| API startup, migrations and project persistence | Passed |
| OpenAPI/schema and original import endpoint | Schema failure found during final check, fixed at the request-schema definition and covered by API regression |
| `uv lock --check` | Passed; 123 resolved packages |
| `git diff --check` and editor Problems | No whitespace/errors reported |
| Dashboard screenshot and mobile layout | Visually inspected; mobile overflow assertion passed |

Coverage includes model routing/discovery, failed-call/retry daily accounting,
token budgets, Gemini thought usage, tracing disabled/redacted instrumentation,
Docker-unavailable blocking, sandbox arguments, execution timeout/output cleanup,
real upstream Inspector parsing/import, approved/rejected hypotheses, cancellation,
crash recovery, no-receipt reconciliation, manual retry attempt caps, atomic
claims, stale-owner fencing, safe artifacts, durable interrupts across reopen,
real graph topology, active-runtime accounting and no-key end-to-end completion.

The upstream POSIX-only suite could not run on this Windows host: its conftest
imports `fcntl`, which is unavailable here. Those upstream files were preserved.
The new CI workflow includes focused upstream CLI/Inspector regressions on Linux;
that CI workflow has been added, **not executed here**.

Build notices: the lazy Monaco editor still creates a large chunk (~2.8 MB
minified), and the tested compatibility checkpoint package emits a deprecation
warning. Neither failed startup or tests. Standard current dependency resolution
is locked but was not executed under this machine's native-wheel restrictions.

## H. Remaining limitations and acceptance gaps

This is a functional local platform with a verified integrated demo and a
restricted genuine-execution adapter. It does **not** satisfy every requested
advanced original-engine feature through the web interface:

1. Original full campaign **web launch is unavailable**, detected and disabled.
   Existing CLI execution remains intact, and numeric results can be imported.
   Hard budgets and safe original-agent launch need a separately isolated worker
   with its own Docker daemon and credential/budget enforcement.
2. Docker is absent here. Sandbox configuration/failure paths were tested, but
   the genuine CPU container was **not executed** on this host.
3. No provider credentials or local Ollama model were supplied. Adapters use real
   service protocols and transport tests, but **live model calls were not tested**.
   A provider's free plan and billing cannot be inferred from a model name.
4. LangSmith SDK instrumentation/redaction was tested with tracing disabled and
   controlled SDK tests; **delivery to a live LangSmith project was not tested**.
5. Free mode is the fixed reviewed 26-circle benchmark, not unrestricted research,
   the sealed upstream evaluator, advanced ablations, independent final evaluation,
   automated peer review or a scientific-validity certification.
6. Fallback reporting is Markdown with browser print/PDF export. Native manuscript
   LaTeX/PDF and original paper audits remain in the upstream CLI/Inspector. Local
   draft edits are not persisted to the server.
7. PostgreSQL metadata and current unpinned-by-compatibility SDK execution were not
   exercised locally. Checkpoints/artifacts remain single-machine storage.
8. This is loopback-only development software without authentication or tenancy;
   it is not suitable for public exposure as-is.

No demo fixture, model-generated interpretation, missing citation, failed
experiment or unavailable integration is advertised as measured scientific evidence.

## I. Next steps

Provision Docker Desktop/WSL2 and exercise the real CPU sandbox. Configure a free
provider and a LangSmith project for explicit live integration checks. Build an
isolated original-engine worker with hard nested-model accounting before enabling
full web campaigns. Before public deployment add authentication/authorization,
tenant isolation, backups, process supervision, dependency security review and a
remote execution boundary. Additional reviewed experiment families can then expand
free mode without allowing arbitrary host code.
