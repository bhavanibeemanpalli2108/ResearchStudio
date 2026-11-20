# Research platform API

OpenAPI: `/openapi.json`; interactive docs: `/docs`. The API is intended for local
use. Provider keys are configured on the backend, never accepted as UI state.

| Route | Purpose |
| --- | --- |
| `GET /api/health` | Metadata storage readiness |
| `GET /api/system/capabilities` | Profiles, Docker, tracing, limits, prerequisites |
| `GET /api/providers` | Provider configuration status without keys |
| `GET /api/providers/models?provider=mock` | Live model discovery |
| `GET /api/providers/{provider}/health` | Discovery-based readiness |
| `GET/POST /api/projects` | Persistent research projects |
| `GET /api/projects/{id}` | Project and run history |
| `POST /api/projects/{id}/runs` | Queue a durable run |
| `GET /api/runs` | Run inventory |
| `GET /api/runs/{id}` | Status, checkpoint view, approval and usage |
| `GET /api/runs/{id}/events?after=0` | Persisted event replay |
| `GET /api/runs/{id}/stream` | SSE; Last-Event-ID or after cursor |
| `POST /api/runs/{id}/pause` | Pause at a durable stage boundary |
| `POST /api/runs/{id}/resume` | Requeue an eligible paused/failed run |
| `POST /api/runs/{id}/cancel` | Durable cancellation signal |
| `POST /api/runs/{id}/approve` | Approve/reject/change idea or constraints |
| `GET /api/runs/{id}/graph` | Actual compiled graph topology and stored stage status |
| `GET /api/runs/{id}/experiments` | Persisted configuration, logs, metrics, errors |
| `GET /api/runs/{id}/metrics` | Actual recorded experiment metric objects |
| `GET /api/runs/{id}/traces` | Decisions, model invocations, available SDK links |
| `GET /api/runs/{id}/artifacts` | Safe artifact metadata and download URLs |
| `GET /api/artifacts/{id}/download` | Attachment download by internal ID |
| `GET /api/usage` | Model calls, reported/estimated tokens and daily limits |
| `GET /api/upstream/runs` | Original Inspector-compatible run inventory |
| `POST /api/projects/{id}/imports` | Read-only evidence import by inventory ID |

Example project body:

```json
{"title":"26-circle grid study","question":"Can a more balanced grid increase the radius sum of 26 valid circles?","domain":"Optimization","objectives":["Compare two valid fixed layouts"],"references":[]}
```

Example no-key run body (all fields can use validated defaults):

```json
{"profile":"demo","provider":"mock","model":"mock-researcher","require_approval":true,"generate_report":true,"budgets":{"max_llm_calls":20,"max_input_tokens":32000,"max_output_tokens":16000,"max_iterations":2,"max_experiments":3,"max_runtime_seconds":300},"constraints":{}}
```

At each `awaiting_approval` interrupt:

```json
{"approved":true,"action":"continue"}
```

Optional approval fields: `idea_id`, `constraints`. Actions include `continue`,
`regenerate`, `retry`, `report`. Changing a plan's constraints or selected idea
requires review of the regenerated concrete proposal before execution. Unknown
or foreign idea IDs are rejected. Duplicate approvals return conflict once queued.

Free runs require a genuine provider. Optional `stage_models` maps stage IDs to
`{"provider":"groq","model":"<discovered ID>"}`. `fallback_models` is an explicit
ordered list of the same shape; there is no paid-provider or implicit fallback.
Unknown pricing plus a `monetary_cap_usd` blocks remote requests conservatively.

Native runs require `"execution_protocol":2`, `"engine":"native"`,
`"profile":"free_research"` and human approval. These are schema-validated;
original-engine web requests remain unavailable until a compliant separate worker
is integrated. A research-plan approval uses the body above. At the concrete
experiment gate, submit the exact `experiment_config.approval_digest`:

```json
{"approved":true,"action":"continue","approval_digest":"<64 lowercase hexadecimal characters from the frozen proposal>"}
```

Missing/stale digests return 409 before queuing candidate generation. Changing
constraints, selecting another idea or retrying preparation requires a new concrete
review. Candidate iteration alone preserves the frozen evaluation. Legacy genuine
runs without protocol 2 cannot resume. Native queue status names prevent an old
worker from claiming the new work; public lifecycle statuses remain unchanged.

Errors use standard FastAPI `detail` with a clear message or code/message object.
Validation: 422; missing resource: 404; invalid lifecycle/capability: 409; model
discovery failure: 503. Asynchronous provider/experiment errors persist on the run
and event stream. Run submission does not synchronously execute a research job.


### Generation readiness (ISSUE-04)

Provider health/model discovery is metadata only (`status: discovered`,
`generation_verified: false`). It never sends a generation request. Creating a
native genuine run authorizes a one-attempt, 128-output-token generation probe
before its first research model call for each selected provider/model. The probe
uses the run's existing reservation ledger and daily cap, including one of the
default 20 calls. It is not an independent free quota. Demo never claims live
readiness. Workers recheck on resume because credentials/access/quota can change.

`GET /api/runs/{run_id}/provider-readiness` returns chronological readiness events
with provider, model, timestamp, status, generation_verified, error code, HTTP
status (when applicable), retryability, and remediation. Reading it spends no
calls. Success is a point-in-time generation check, not proof of structured
output compatibility or future availability. Provider error bodies and generated
probe text are not exposed. Failed/uncertain calls retain their reservations;
unknown pricing stays null and monetary caps still block unknown-cost requests.

After a provider failure pauses the run, the workspace allows explicit provider
selection. `PATCH /api/runs/{run_id}/model` takes `{"provider":"groq","model":"MODEL_ID"}`
for an idle paused native genuine run. This explicitly replaces all future stage
and fallback selections, retains budgets, reservations, checkpoints and approval
protections, and records an audit event. Resume separately to trigger preflight.
No model requests occur during selection or polling. Explicitly configured
fallbacks also emit selection events and must pass preflight on the same ledger.
Groq selection applies to the native engine; it does not enable the original
Gemini CLI. Full original research launch continues to return HTTP 409.

Live credentialed verification is a separate operator action; unit-test HTTP
fixtures are not evidence of a working provider account.
