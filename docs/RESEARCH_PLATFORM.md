# Research Studio: local research workspace

A React/TypeScript workspace, FastAPI API, SQLAlchemy metadata store and separate
durable worker extend the existing Sakana Agentic Scientist repository. Upstream
commands, algorithms, examples, license and Run Inspector are preserved.

## Profiles and scope

| Profile | Model calls | Experiments | Output |
| --- | --- | --- | --- |
| `demo` | Deterministic mock, no keys | Explicit prerecorded fixtures | Clearly disclosed demonstration report |
| `free_research` / native | Discovered Gemini/Groq model or installed Ollama model | Model-generated baseline and candidate in restricted Docker; trusted regression or scheduling evaluator | Seed measurements, statistical summary, source/data hashes, artifacts and Markdown report |
| `full_research` | Original coding-agent CLI protocol | Existing upstream campaign | Web launch is unavailable; use the trusted original CLI and import its numeric evidence |

Native protocol-v2 runs preserve the question and perform feasibility, planning,
literature discovery, hypotheses, typed experiment preparation, independent
evaluator checks, digest approval, generated implementation and measured execution
in the existing LangGraph. Supported protocols currently cover small synthetic
regression (RMSE/MAE against a training-mean baseline) and single-machine scheduling
(total completion time against FIFO). Dataset parameters, seeds and implementation
are question-specific. Unsupported questions fail feasibility rather than silently
run a fixed benchmark. This is a bounded computational research system, not an
arbitrary-domain scientific-validity or novelty certification.

The former fixed circle-packing genuine route is retired and fails closed.
Demo fixtures remain explicitly labeled. Independent host-owned scoring verifies
baseline semantics and finite, correctly shaped outputs. Hidden regression labels
and evaluator source never enter the generated programs. Candidate changes retain
the approved data, baseline and evaluation. See [live acceptance evidence](RESEARCH_ENGINE_ACCEPTANCE.md)
and [the protocol details](ARCHITECTURAL_CORRECTIONS.md).

## Windows setup (PowerShell)

Use Python 3.11+ and Node.js 22.18+; commands run from the repository root. Keep
your upstream environment if you have one. For a fresh installation:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[platform]"
Copy-Item .env.example .env
npm.cmd --prefix apps/research_platform/frontend ci
.\.venv\Scripts\python.exe -m src.research_platform.dev
```

If Windows Application Control blocks the `ormsgpack` or `xxhash` extensions,
install the tested official compatibility versions into the venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[platform]" -c requirements-platform-windows.txt
```

That constraint set uses LangGraph 0.2.76, checkpoint 2.0.10, SQLite saver 2.0.3
and LangSmith 0.3.45. Standard installs resolve the current compatible release
family in `uv.lock`. The app supplies an explicit allow-list JSON checkpoint
serializer; it never reconstructs arbitrary Python types or executes pickle.
Do not disable Windows security policy to install the application.

The development launcher starts API, worker and Vite together. URLs:

- Workspace: <http://127.0.0.1:5173>
- API and OpenAPI UI: <http://127.0.0.1:8000/docs>
- Original Run Inspector: <http://127.0.0.1:8765> after `agsci inspect start`

If port 8000 is occupied, use `python -m src.research_platform.dev --port 8001`.
The launcher passes the matching proxy address to Vite. Mission-1 browser
validation used an isolated mock database and API port **8011**; this is separate
from the live acceptance database and your default projects.

The provided `scripts/start_research_platform.ps1` starts the same services.
VS Code tasks are supplied for the launcher and focused backend tests. Ctrl+C
stops only the launcher-owned development processes. Persisted jobs and graph
checkpoints remain available on restart.

### Linux / WSL2

```bash
uv sync --extra platform
cp .env.example .env
npm --prefix apps/research_platform/frontend ci
.venv/bin/python -m src.research_platform.dev
```

For Windows experiments install Docker Desktop using its Linux-container/WSL2
backend. Keep the original multi-stage engine in its documented Linux/WSL setup.
No discrete GPU is required for native CPU studies or demo.

## Separate processes and built frontend

```powershell
# Terminal 1: API
.\.venv\Scripts\python.exe -m uvicorn apps.research_platform.backend.main:app --host 127.0.0.1 --port 8000
# Terminal 2: durable worker (required to advance research)
.\.venv\Scripts\python.exe -m src.research_platform.worker
# Terminal 3: frontend
npm.cmd --prefix apps/research_platform/frontend run dev
```

For one origin, first build the frontend and start the API plus worker:

```powershell
npm.cmd --prefix apps/research_platform/frontend run build
.\.venv\Scripts\python.exe -m src.research_platform.dev --no-frontend
```

Open <http://127.0.0.1:8000>. The backend serves the built SPA and artifacts.
Neither the development launcher nor API is a production process supervisor.

## Complete the no-key demo

1. Open the workspace and choose **Launch a demo** / **New research**.
2. Choose **Use example**, continue and leave the **Demo** profile selected.
3. Keep human approvals and report generation enabled; launch the run.
4. In the live workspace choose **Review proposal**, then **Approve & continue**
   for the research plan. Repeat for the experiment proposal.
5. Inspect the completed workflow, idea, fixture-labeled experiment metrics,
   explainability journal and **Paper & artifacts**.
6. Download the server-generated `research_report.md` and experiment JSON.
   Markdown editing in the browser is explicitly a local draft; it does not
   overwrite the immutable server evidence. Browser print supports local PDF
   export. Full upstream LaTeX/PDF remains in its original pipeline/Inspector.

Refresh the browser or restart the backend/worker between approvals to verify
durability. Event streaming only replays events; it does not start a second job.

## Runtime providers and budgets

Copy nonsecret defaults from `.env.example`. Supply `GEMINI_API_KEY` or
`GROQ_API_KEY` only if you want that provider. Ollama uses a loopback-only
`OLLAMA_BASE_URL` and models already installed locally; pull a CPU-suitable model
yourself. Settings and the creation form discover models from provider APIs;
remote model IDs are not hardcoded. Your Codex development model does not
configure this runtime.

Select **Free research**, a genuine provider and a currently discovered model.
Free quota, eligibility and API model availability depend on the account and can
change. This application does not enable billing or silently change providers.
There is no way for an API client to certify that an account is on a free plan;
check its billing settings. Only explicitly configured fallback models are used.
The API supports per-stage model selections and fallback models in run creation.

Limits include model requests (every retry is charged), conservative UTF-8 token
reservations, output limits, active runtime, iterations, experiment attempts,
daily requests and concurrent jobs. Unknown/crashed requests retain reservations.
Reported token counts are separate from estimates. Cost is unknown unless the
adapter has a reliable basis (mock/local inference has zero API charges).
An optional monetary cap blocks unknown-price remote calls rather than inventing
a price. GPU/electricity costs are not estimated.

Human approval wait time does not consume active execution runtime. A completed
receipt is reconciled without executing the same experiment again. If a crashed
worker left an experiment without a receipt, the run pauses and explains that
the process cannot be resumed; an explicit Resume retries within the durable
attempt cap. No checkpoint can resurrect a terminated subprocess.

## Docker experiments

Before using free mode:

```powershell
docker info
docker pull python:3.12-slim
```

`RESEARCH_CPU_IMAGE` can pin an administrator-reviewed image digest. Containers
run without network, mounts, provider keys or Docker socket; UID/GID is non-root,
root filesystem read-only, all capabilities dropped, no-new-privileges set, and
CPU/memory/process/output/runtime limits applied. Each model-authored baseline and
candidate runs separately for each seed. The local image ID is resolved and used
immutably for the actual processes. Only the standard library is supported;
dependencies outside the reviewed image are rejected rather than installed using
run-controlled commands. The interpreter has an additional in-container alarm.
No native execution fallback exists when Docker or the image is unavailable.

## Original-engine integration

Use the existing documented `agsci doctor`, `agsci run` and `agsci inspect`
commands on a suitable trusted Linux/WSL worker. Its result envelope remains
unchanged. Under **Research projects**, use **Import upstream run** to select an
inventory entry under administrator-configured `UPSTREAM_RESULTS_ROOT` and a
destination project. The adapter invokes the original Inspector's discovery
parser and imports numeric evidence/correctness metadata. It never imports or
executes a candidate Python module. Original campaign inspection stays in the
existing Inspector; no competing campaign parser is maintained.

Full web launch is deliberately reported unavailable: upstream forwards agent
credentials and allows full tool execution, and it does not enforce this
platform's hard nested-provider call budgets or all requested container limits.
An isolated worker with its own daemon and a credential/budget boundary is
required before exposing original campaign launch through the API.

## Literature and LangSmith

Free mode queries cached OpenAlex metadata. Returned identifiers, titles, source
URLs/DOIs and retrieval timestamps are saved; generated citations are never
accepted as sources. `OPENALEX_API_KEY` is optional depending on the service's
current access policy. Retrieval failures pause with a clear error; they do not
create fictional references. Demo retrieves no literature. User reference links
are persisted as inputs; their contents are not automatically trusted or fetched.

Tracing is optional. Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` and
`LANGSMITH_PROJECT`, then restart services. Only explicit spans containing
allow-listed project/run/stage/model IDs, counts and status are exported through
the official SDK. Automatic graph tracing is disabled to avoid exporting state,
prompts, responses, documents, private exception text and credentials. Actual SDK
trace IDs/URLs are persisted when available; local correlation IDs are not
fabricated external trace links. Trace failures do not stop research.

The explainability journal records attempted stages, captured inputs/outputs,
evidence references, routing rationale, durations and usage. It does not expose
private model chain-of-thought or certify model interpretations.

## Storage, recovery and security boundary

SQLite metadata, graph checkpoints and artifacts default to `.research-platform/`
(Git ignored). Alembic upgrades run before startup; API and worker share the same
`DATABASE_URL`, `CHECKPOINT_PATH` and `ARTIFACT_ROOT`. Do not run an older worker
against a newer schema. PostgreSQL metadata can be configured using the
`postgres` optional dependency, but local SQLite checkpoint storage and
single-machine file artifacts remain; PostgreSQL has not been exercised here.
Genuine jobs use `queued_v2` / `running_v2` / `waiting_v2` statuses so old workers
cannot claim or recover them. Old genuine checkpoints are rejected on resume.

Jobs use atomic claims, bounded concurrency, heartbeat leases and ownership
fencing. After a crash, an expired lease is recovered and graph/receipt state is
reconciled. Artifacts have internal hashed names and content digests; client
paths, symlink escapes and traversal are rejected. SSE supports Last-Event-ID
replay. Provider keys never appear in public settings responses.

This release is **local-only**. It binds to loopback, checks host/origin, and has
no multi-user authentication. Before public deployment add authentication,
authorization, TLS, tenancy, a hardened remote execution boundary, dependency
security review, backups and worker supervision. Do not expose the ports publicly.

## Troubleshooting

- **Queued forever:** start the separate worker; check both processes share paths.
- **Paused / quota / budget:** inspect the exact error and usage. Correct provider
  credentials or availability and Resume. Exhausted hard budgets require a new run
  with suitable limits; retries do not reset usage.
- **Docker unavailable:** start Docker Desktop's Linux engine and pull the image.
  Demo works while Docker is unavailable.
- **Original run missing:** use the documented task/agent/run envelope and an
  `investigation/ideas` or worker result directory; outer-state files alone are
  not a valid Inspector result. Unsafe/oversized metadata imports are rejected.
- **Port conflict:** choose `--port 8001`; `RESEARCH_API_URL` also configures a
  separately launched Vite server. The launcher sets it automatically.
- **Upstream Windows tests fail on fcntl:** the original engine/fixtures assume
  POSIX. Run upstream tests in Linux/WSL. Focused platform tests use `--confcutdir`
  and do not rewrite or stub the original engine.

See [the implementation report](IMPLEMENTATION_REPORT.md),
[repository audit](REPOSITORY_AUDIT.md) and [API reference](RESEARCH_PLATFORM_API.md).
