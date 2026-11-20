# Repository audit

Audited 2026-11-14 at upstream commit `df83138` (SakanaAI/AI-Scientist-v3).
The initial Git working tree was clean. No AGENTS.md was found. This is the
Agentic Scientist v3 Python 3.11+ project, Apache-2.0, not the older chat-API
AI Scientist implementation. Attribution, LICENSE, CITATION.cff, examples and
all upstream algorithms are retained.

## Existing architecture and callable boundaries

`src.agsci.main:main` dispatches `agsci run`, `investigate`, `doctor`, `inspect`
and `review`. `src.pipeline.cli:main` composes Hydra configs from
`configs/pipeline_config.yaml` and `src/pipeline/config.py`. A task's `task.md`,
program, requirements, evaluator, rubric and public contract form its input.
The pipeline snapshots that task into an immutable run-local task directory.

| Operation | Existing boundary and contract |
| --- | --- |
| Task drafting and hypotheses | `src/task_drafting/`, `src/investigation/idea_generation.py`; structured agent outputs and task qualification |
| Idea search and investigation | `src/investigation/campaign_loop.py`, `cli.py`; bounded cycles, attempts, evaluator results, winner/optimizer memory |
| Literature | `src/orchestrator/semantic_scholar.py`, reference query planning and enrichment; paper-agent retrieval |
| Ablations and baselines | `src/variants_pipeline/pipeline.py:run_variants_pipeline`; extraction, generation, selection, materialization, execution, aggregation |
| Sealed final evaluation | `src/final_evaluation/runner.py`; manifests and verified evaluation evidence |
| Post-hoc/statistical analysis | `src/posthoc_pipeline/pipeline.py:run_posthoc_pipeline`; artifact-based analyses, aggregate publication |
| Manuscript | `src/orchestrator/paper_step.py`, `src/scripts/paper.sh`; evidence/claims/reference audits, LaTeX compilation, AI watermark |
| Review/revision | `src/pipeline/review.py`, `revision.py`, `src/aireview.py`; optional paid reviewer |
| Persistence/recovery | `src/investigation/run_checkpoint.py`, `src/pipeline/resume_config.py`, portable storage publication and locks |
| Observability | `pipeline_events.jsonl`, per-stage `events.jsonl`, `metrics/cost_events.jsonl`, manifests and paper journals |
| Inspection | `apps/run_inspector/backend/app.py:create_app`, discovery, graph/views/performance builders; existing React UI |

Run envelope: `results/<task>/<agent>/<run_id>/{task_drafting,task,investigation,
ablations,final_evaluation,posthoc,paper}`. Resume uses the same `paths.run_dir`
and original agent/model. A persisted checkpoint does not resurrect a subprocess.
Structured journals and manifests should be consumed instead of terminal output.

## Inspector decision

The existing Inspector is a read-only explorer of upstream campaign artifacts,
not a durable job submission service. Its APIs and frontend remain intact. The
new research workspace manages application projects, budgets, graph checkpoints
and approval gates; it links to and reuses the existing Inspector for original
runs. It does not reimplement the detailed upstream campaign graph/parser.

## Model and hardware constraints

Original runs invoke coding-agent CLIs through Headless (Claude, Codex, Cursor,
OpenCode, Gemini, Pi). Runtime credentials/subscriptions are independent of the
model used to develop this application. Ordinary Gemini/Groq chat APIs cannot
replace that protocol. Reviews/illustrations can require paid APIs. GRPO needs
two GPUs per worker and model weights; circle packing is CPU-friendly. Bare-brief
task drafting is explicitly experimental upstream.

The new free workflow uses real scholarly metadata and a restricted, curated CPU
circle-packing benchmark inspired by the supplied task. It is not the original
agentic search or sealed upstream evaluator. Model suggestions never become host
commands. Demo values are deterministic fixtures and always labeled.

## Execution risks and integration limits

Upstream's agent containers intentionally have full agent tool permissions,
provider credentials and default host networking. Several execution paths need
host Bash, Docker and POSIX filesystem operations. The original agent helper does
not offer all the web platform's required hard resource controls or nested-model
call caps. Launching it from the public request process or mounting the Docker
socket into an outer container would weaken isolation. The new API therefore
exposes original-engine prerequisites and a source-derived CLI preview, and imports its
structured results read-only; original launch remains the existing trusted CLI.
Full research web execution requires a separate hardened worker and is reported
unavailable, rather than silently running unsafely or claiming free compatibility.

## Local tool observations

Windows PowerShell; Node 26.13.1, npm 11.20.0, Python 3.13.14 and Git are present.
Neither uv nor Docker was found on PATH. `rg` is unavailable; inspection used Git
file inventory and PowerShell. Existing tests assume POSIX in places (including
`fcntl` imports and `os.getuid()` in conftest); local focused tests need
`--confcutdir=tests/research_platform` and an explicit `--basetemp`.
Windows Application Control blocks some current Rust-extension wheels. A tested
official LangGraph/LangSmith compatibility constraint set is supplied without
disabling the policy. Standard installations use the current dependency family.

## Required additions

SQLAlchemy metadata and Alembic migrations; FastAPI REST/SSE; durable database job
leases/heartbeats and recovery; real LangGraph with SQLite checkpoints and human
interrupts; budgeted provider routing; optional redacted LangSmith traces; safe
Docker-only execution; verified literature cache; filesystem artifacts; a typed
React workspace; local scripts and integrated tests. SQLite is the zero-service
default. PostgreSQL metadata is configurable; graph checkpoint storage remains
local SQLite in this single-worker release.
