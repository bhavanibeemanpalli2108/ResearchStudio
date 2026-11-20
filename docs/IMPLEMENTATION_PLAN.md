# Implementation plan

Use a modular monolith and preserve upstream code. Application modules live in
`src/research_platform`, API entry points in `apps/research_platform/backend`, and
the React application in `apps/research_platform/frontend`.

1. Audit upstream entry points, security, data contracts and installed tools.
2. Add settings, typed schemas, SQLAlchemy models, migrations, safe artifacts,
   persistent events and a database-backed job worker. Bind locally by default.
3. Implement mock, Gemini, Groq and Ollama discovery/routing, classified retry,
   request/token reservations, per-run/daily budgets and explicit free fallback.
4. Compile an actual LangGraph with durable checkpoints, bounded conditional
   routing, plan/experiment interrupts, cancellation and restart reconciliation.
5. Keep upstream CLI and Inspector. Expose truthful original capability and
   read-only result integration. Execute the restricted real CPU benchmark only
   inside resource-bounded Docker; demo is an explicit fixture.
6. Build connected React dashboard, creation form, workspace graph, hypotheses,
   experiment views, charts, report downloads, traces, settings and history.
7. Instrument decisions and operations with optional redacted official LangSmith
   tracing. Report captured evidence and rationale, never hidden chain of thought.
8. Test providers/security, graph persistence/failures, API lifecycle and a
   browser demo from creation through approvals, metrics and report download.
9. Document exact setup/start/verify commands, profile limitations, attribution,
   remaining optional prerequisites and tested versus untested integrations.

The API never executes generated host code. Worker leases and experiment receipts
prevent duplicate experiment execution. Model retries each reserve a request
before HTTP dispatch; uncertain/crashed calls retain conservative reservations.
SSE replays persisted events and never starts jobs. No cloud service is required
for the default demo.
