# Original-engine worker audit and operation

Phase 1 update, 2026-11-20: see [ISSUE_01_REPORT.md](ISSUE_01_REPORT.md) and the
[dedicated deployment runbook](../deploy/upstream-worker/README.md). Repository
configuration and contract tests are prepared; no dedicated VM has been installed
or verified. Campaigns now default to disabled independently of worker enablement.
Earlier observations below remain historical; ISSUE-04/05 verification is recorded
separately and does not make Docker Desktop an isolated original-engine worker.

Audit date: 2026-11-17. This document distinguishes observed local diagnostics from the dedicated-worker contract recovered from a later validation image. A command preview, successful parser check, or Docker installation does not establish a completed original-engine research run.

## Final Mission-1 checkpoint — 2026-11-18

The original campaign is still **BLOCKED**; no real coding-agent campaign was
executed. Two native Groq/Docker studies completed with measured reports. See
[RESEARCH_ENGINE_ACCEPTANCE.md](RESEARCH_ENGINE_ACCEPTANCE.md) for request/token
ledgers, the later strict selection fix and separately accounted validation.
Native success does not count as original-engine completion.

The final original CLI/Inspector/task-drafting suite was rerun in WSL:
**55 passed in 27.60 seconds**. Platform suites passed **133 tests** on both
Windows compatibility SDKs and Linux/current locked SDKs, including Docker.
Frontend verification passed **11 React tests, 4 Chromium flows**, type checking,
formatting and build. All pages of both native browser PDF exports were rasterized
and visually inspected. These supersede the earlier diagnostic counts below.

## Observed environment

| Component | Observed value |
| --- | --- |
| Windows Docker client | 29.9.2, build `a82e528` |
| WSL distribution | Ubuntu 26.04.1 LTS, WSL2; kernel `6.18.58.1-microsoft-standard-WSL2` |
| Dedicated WSL Python environment | `/home/sonusunny/.local/share/agsci-mission1-venv`, CPython 3.12.16 |
| Project package | `agentic-scientist==0.1.0`, installed with the checked-in lockfile |
| Agent image | `agentic-scientist/agent-cli:latest`, image ID `sha256:748bf058909de762ab857a6a196957edea031c2fd4d31f6122ab557828b1a070` |
| Agent-image Node / npm | 22.23.5 / 10.9.9 |
| Agent-image Headless | 0.6.1, Git commit `93cd9b06b85f848af1308c41e018991b33907c5e` |
| Agent-image Gemini CLI | 0.68.0 |
| WSL Git | 2.53.0 |
| WSL host Node | Missing at the end of the recorded doctor check |
| WSL host npm / npx | 11.20.0 through Windows interoperability; this is not a complete Linux Node installation |

At the initial observation both Ubuntu and Docker Desktop's WSL distribution were stopped, and the Linux Docker named pipe was absent. After Docker Desktop startup, the WSL doctor check found the daemon reachable and the agent image present. No existing listeners on the platform's usual ports were stopped or replaced during this audit. The repository `.env` exists; doctor reported Gemini credential configuration by variable name only. No credential values were printed or copied into this document.

The Windows `.venv` was preserved. The separate Linux environment was created with:

```bash
UV_PROJECT_ENVIRONMENT=/home/sonusunny/.local/share/agsci-mission1-venv \
  /home/sonusunny/.local/bin/uv sync \
  --project /mnt/d/project/reseon/AI-Scientist-v3 \
  --python 3.12 --no-dev --locked
```

That operation installed 78 project/core packages. No agent prompt or provider request was submitted by this audit.

## Headless and Gemini compatibility

The repository [agent command builder](../src/scripts/lib/container_agent.sh) selects the pinned Headless revision, then supplies `--debug --usage --allow yolo`, an optional explicit model, and the prompt. It explicitly rejects Gemini reasoning-effort overrides.

The following no-network, no-credential parser check was run inside the existing agent image:

```bash
headless gemini --debug --usage --allow yolo \
  --model gemini-2.5-flash --print-command \
  --prompt runtime-contract-smoke
```

Its observed output was:

```text
gemini --model gemini-2.5-flash --skip-trust -p runtime-contract-smoke --output-format stream-json --approval-mode yolo
```

Installed Gemini CLI 0.68.0 help lists `--model`, `--skip-trust`, `-p/--prompt`, `--output-format stream-json`, and `--approval-mode yolo`. Thus these installed parsers agree on the emitted flags. This did not contact Gemini and does not verify model availability, account quota, streaming behavior during a real tool call, or research completion. The model in this parser example is not an availability recommendation.

The first diagnostic container deliberately had a read-only home and emitted `.gemini` directory cleanup errors. Repeating the check with a writable ephemeral home removed those errors. They are filesystem setup errors, not evidence of a Gemini streaming protocol defect.

No historical original-engine `results/` directory or saved streaming-error log was present in the inspected checkout. No streaming incompatibility was reproduced. The [Dockerfile](../src/docker/agent-cli/Dockerfile) pins Headless but installs Gemini CLI without a version pin, and its build-time Headless smoke loop excludes Gemini. Future image rebuilds should record the installed Gemini version and repeat the no-network command-rendering check before any paid or quota-limited call. No upstream pipeline algorithm or CLI flag implementation was changed by this audit.

## Doctor and bounded command preview

The real WSL command below ran against the current checkout and existing Docker daemon:

```bash
/home/sonusunny/.local/share/agsci-mission1-venv/bin/agsci doctor --json \
  examples/circpack agent.name=gemini agent.model=gemini-2.5-flash \
  execution.phases=investigation \
  investigation.execution.max_idea_cycles=1 \
  investigation.execution.max_program_evals_per_attempt=1 \
  container.image=agentic-scientist/agent-cli:latest
```

Doctor exited 1 because host `node` was absent. It reported Python, Git, Docker client and daemon, pipeline configuration, agent image, auth root, `.env`, Gemini credential configuration, and the circle-packing scaffold as ready. Missing host agent CLIs were warnings because this selected run obtains Gemini from the image. Install a real Linux Node runtime before treating this mixed WSL/Windows toolchain as fully ready. The doctor implementation does not contact remote model services.

A no-model Linux dry-run also succeeded, using the existing platform validation image, the repository mounted read-only at `/repo`, and a temporary existing auth directory. Its initial attempt without a repository mount correctly failed because that image did not include `examples/circpack` and the default auth root was absent. The corrected invocation validated the following bounds and printed the investigation subprocess command:

```bash
python -m src.agsci.main run examples/circpack --dry-run \
  agent.name=gemini agent.model=gemini-2.5-flash \
  execution.phases=investigation \
  investigation.execution.max_idea_cycles=1 \
  investigation.execution.max_idea_generation_attempts=1 \
  investigation.execution.max_program_evals_per_attempt=1 \
  investigation.execution.workers=1 \
  investigation.execution.run_timeout_seconds=300 \
  investigation.execution.idea_timeout_seconds=90 \
  investigation.execution.harness_evaluated_attempts=true \
  investigation.execution.harness_evaluation_timeout_seconds=60 \
  container.image=agentic-scientist/agent-cli:latest \
  container.auth_root=/tmp/auth \
  versioning.enabled=false
```

`/tmp/auth` above belongs to that temporary parser-check container. An actual trusted WSL campaign must use its real auth directory, an available model confirmed separately by the provider, and a fresh run identity/output location. Removing `--dry-run` would make real coding-agent calls and was not performed by this audit. The dry-run logger uses completion labels for a command preview; these labels are not experimental results.

These are cycle, evaluation, and time bounds. They do **not** impose a hard cap on nested provider requests made by Gemini CLI. The platform router's 20-call cap does not govern those nested requests. A live original campaign under a hard 20-call budget needs an enforceable provider gateway or independently approved operator quota policy first. Do not report that limit as enforced solely because `max_idea_cycles=1` is set.

## Recovered dedicated-worker contract

The image `ai-scientist-platform:validation-current` (ID `sha256:dccf4449038b7512bff7cab5df4e0c3f215db05fae109f5d4c3129c84b7d26f6`) preserved later Python sources under `/app/src/research_platform/`, including `upstream_execution.py` and `upstream_worker.py`. Their recovered reference code is distinct from the older checkout inspected initially. Their existence does not establish that an operator deployed a compliant remote worker.

The recovered client uses an operator-configured HTTPS origin and bearer token, forbids redirects and URL credentials/paths/query strings, disables ambient proxy inheritance, and bounds response sizes. Explicitly opted-in loopback HTTP is a development exception. Operator configuration includes:

- `RESEARCH_UPSTREAM_WORKER_URL` and `RESEARCH_UPSTREAM_WORKER_TOKEN` (at least 32 characters).
- Worker-side enablement, a private root and credential file, and `RESEARCH_UPSTREAM_ISOLATION_ACK=dedicated-disposable-worker-v1`.
- A dedicated native Linux VM/controller, dedicated Unix Docker socket and data root, finite CPU/memory/PID cgroup limits, and matching daemon cgroup policy.

The recovered worker refuses a controller inside a container. It does not accept the workstation's normal Docker socket or default Docker data root as its dedicated daemon. The expected cgroup has finite limits no greater than four CPU cores, 16 GiB memory, and 4096 PIDs. It probes the original Python dependencies, immutable agent-image identity, Gemini/Headless/TeX tools, and effective cgroup placement before reporting ready. These configuration checks and operator attestations do not certify a production security boundary.

| Operation | Reference endpoint |
| --- | --- |
| Readiness | `GET /v1/capabilities` |
| Preview without execution | `POST /v1/dry-run` |
| Submit / inspect | `POST /v1/runs`, `GET /v1/runs/{uuid}` |
| Events | `GET /v1/runs/{uuid}/events?after=...` |
| Control | `POST /v1/runs/{uuid}/cancel`, `POST /v1/runs/{uuid}/resume` |
| Allowed artifacts | `GET /v1/runs/{uuid}/artifacts/{name}` |

The request is strict and bounded: canonical UUID, question, objectives, Gemini model, CPU runtime/cycle/evaluation/replication bounds, and an explicit `nested_budget_policy=operator_managed` plus `nested_budget_approved=true`. The worker reports `nested_call_budget_enforced=false`; it does not pretend that the platform router accounts for coding-agent internals. Artifact access is restricted to a fixed allowlist and bounded regular files without run-controlled symlink traversal.

On service restart, an abandoned running process is marked `cleanup_unverified` and keeps the exclusive worker fenced until an operator verifies cleanup. The web application must keep original execution unavailable when authentication, isolation, budget policy, capabilities, or recovery state are incomplete. It must never silently substitute a demo fixture, the curated legacy benchmark, or native generated research for an original-engine request.

The native question-driven engine is a separate execution path. Its generated baseline, frozen specification/evaluator, hidden-dataset commitment, and approval digest do not constitute an original Sakana campaign. Keep those execution identities visible in results and reports.

## Regression checks performed

The following focused upstream suite ran in the separate WSL environment, without model calls:

```bash
UV_PROJECT_ENVIRONMENT=/home/sonusunny/.local/share/agsci-mission1-venv \
  /home/sonusunny/.local/bin/uv run \
  --project /mnt/d/project/reseon/AI-Scientist-v3 --group dev \
  pytest -q \
  tests/pipeline/test_agsci_cli.py \
  tests/pipeline/test_run_inspector.py \
  tests/task_drafting/test_task_drafting_checks.py \
  tests/task_drafting/test_task_qualification.py
```

Result: **55 passed in 31.26 seconds**. These checks cover CLI dispatch/doctor behavior, the original Run Inspector, task drafting gates, and qualification contracts. A suggested `tests/investigation/test_idea_retry_feedback.py` path was not present in this checkout and was not reported as tested. Development test dependencies were added only to the dedicated Linux environment; the Windows `.venv` and upstream pipeline source were preserved.

The frontend integration separately passed TypeScript checking, a production build, and nine focused Vitest/React Testing Library tests. Those include native protocol-v2 requests with 20-call defaults, digest-bound experiment approval, refusal of conflicting digests, and refusal of cross-origin artifact source previews. The existing lazy Monaco chunk-size notice remains a build warning. These software checks do not substitute for a completed genuine or original-engine campaign.


## ISSUE-02 scoped Gemini gateway preparation — 2026-11-20

Gateway-mode private configuration accepts only a scoped gw_ GEMINI_API_KEY and
operator-controlled GOOGLE_GEMINI_BASE_URL. The URL run ID must match the worker
request UUID's hex form. A new private profile selects supported gemini-api-key
auth and disables telemetry/statistics. Resume requires its matching profile
marker and unchanged private auth settings; existing OAuth homes are refused.
No real provider key belongs in this file or the disposable worker.

Gemini CLI 0.68.0 text and functionResponse SSE compatibility passed installed-CLI
mock tests. Other CLI versions require revalidation. The gateway reuses existing
ModelUsage accounting, not worker cycle limits. Trusted key storage, grant
lifecycle and actual VM host-controlled egress remain deployment work. Existing
operator-managed mode remains explicit; nested_call_budget_enforced=false and
campaigns-disabled defaults remain unchanged. See
[gateway runbook](../deploy/upstream-worker/GATEWAY.md) and
[ISSUE-02 verification](ISSUE_02_REPORT.md).
