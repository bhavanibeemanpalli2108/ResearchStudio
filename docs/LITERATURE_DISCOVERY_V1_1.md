# Reseon v1.1 — literature discovery

Implementation/live retrieval checked November 20, 2026; final regression checks
and handoff completed November 22, 2026. This extends the existing native app;
there is no new database, model provider, MCP server or infrastructure component.

## Open and use

Open **http://127.0.0.1:5180/literature**, or select **Literature** in the sidebar.
Existing startup/shutdown scripts and [local application instructions](LOCAL_APPLICATION.md)
are unchanged. Backend health: http://127.0.0.1:8010/api/health.

1. Enter a research topic or DOI and select Search literature.
2. Review up to ten deduplicated records: title, available authors/year/DOI,
   source links, provenance and source-supplied abstract excerpt where available.
3. Select relevant papers, then Use selected papers in research.
4. The existing new-task form lists the selected context. Review the question,
   Groq model, unchanged budgets and human approval settings before launching.
   Remove selected papers there if they are not appropriate.

Searching/selecting papers does not launch a research run or invoke a model.
The current service blocks real Groq generation pending separate authorization
and fresh account confirmation. Existing original Sakana launch still returns 409.

## v1 checkpoint created before feature work

The initial working tree was already clean with prior application commits.
Reviewed tracked paths and staged state: no staged files; no tracked .env, local
databases, generated build/evidence directories or exact configured-secret values.
.env, .research-platform, node_modules and dist are ignored.

Created the explicitly requested checkpoint commit without changing its tree:

- Commit: `66713dbc456c9a3705a11350eebe28a3fe94c98a`.
- Message: `Stabilize Reseon native Research Studio v1`.
- Annotated local tag: `reseon-native-v1.0.0`, pointing to that commit.
- Checkpoint and parent tree both: `dd56484986010575b738079b2206440ea6ebd963`.

No prior commit was amended, no history rewritten, and nothing was pushed. v1.1
feature changes remain in the working tree for review; they are not part of the
v1 tag. Local research evidence is preserved separately from source control.

## Retrieval architecture

The existing LiteratureClient/httpx boundary now supports two public sources:

- OpenAlex work search and reconstruction of a genuinely supplied abstract
  inverted index. Invalid/incomplete indexes yield no abstract, not invented text.
- Crossref bibliographic search, DOI singleton lookup, deposited author/date/DOI
  metadata and available journal/publisher/volume/issue/page fields. JATS/HTML
  abstracts become plain text without executing markup or fetching external entities.

Topic search makes at most one GET per source, with up to ten records requested
from each and at most ten returned overall. DOI and stable source identifiers
deduplicate records; duplicates retain both provenance entries and available
complementary metadata. Source ranks are interleaved rather than treating either
source's score as a directly comparable relevance score.

Requests use fixed HTTPS origins, no proxy inheritance, no redirects, no automatic
retries, bounded response size/time, one concurrent request per source/cache and
at least one second between uncached requests. HTTP 429 observes Retry-After
(seconds or HTTP-date, with bounded cooldown up to seven days). Timeouts, invalid
envelopes, unavailable fields, outages and rate limits produce safe source warnings;
the other source can still supply useful results.

Only anonymous public access is used. Existing OPENALEX_API_KEY, model keys and
Crossref paid keys are never sent by this discovery implementation. No new key
or email is required, and no quota/billing upgrade is attempted. Upstream public
limits and availability can change; refusal remains explicit rather than silently
switching to paid access. Source policy documentation consulted during implementation:
[OpenAlex authentication](https://help.openalex.org/api/authentication/) and
[Crossref access/rate limits](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication).

Successful searches, including empty results, cache for 24 hours under the existing
workspace's literature-cache directory. Partial failures are not cached as full
success. Atomic JSON publication and source lock/cooldown files prevent repeated
requests across API/worker processes sharing the cache. Cache corruption is handled
without promoting changed metadata. No model-call ledger reservation is made for
scholarly metadata RPCs; they are not model generation requests.

## Explicit selection and research provenance

Browser selections persist locally; only opaque snapshot IDs are submitted in
RunCreate.selected_paper_ids. Each ID is a content hash of server-retrieved metadata
saved under literature-cache/papers. On creation of a new native run, the backend
resolves and checks those files, rejects unknown/changed snapshots, deduplicates
stable paper IDs and saves selected_literature in the existing run-config JSON.
Clients cannot supply arbitrary selected_literature metadata. No migration is needed.

At the literature stage, explicitly selected snapshots bypass new retrieval. The
worker retains selected-literature.json and an event, and passes that selected
metadata through the existing literature context into ideation. Ideation treats
source text as untrusted context, cites only supplied identifiers and must not
invent findings or novelty claims. New reports retain selected citation provenance.
Original completed reports/configurations/state/artifacts are never rewritten.

Runs without selected papers retain the existing optional OpenAlex workflow;
retrieval failure warns and continues without fabricated citations. Selected
snapshots remain usable during later retrieval outages. Selecting papers does
not establish their relevance, peer review, correctness, or the truth of an abstract.

## Recorded live scholarly retrieval

No live queries were repeated during the November 22 continuation. Retained
November 20 verification used the topic **shortest processing time scheduling**:

- Instrumented five-result query: OpenAlex GET /works HTTP 200 and Crossref
  GET /works HTTP 200; five returned papers, three with actual source abstracts.
- Browser's default ten-result query: ten returned papers, six with source
  abstracts, no source warnings. The page displayed real retrieved metadata,
  allowed selection and carried it into Create. No research run was submitted.
- Two bounded searches total, at most four public scholarly GETs; no API keys,
  paid endpoints, Groq/Gemini generation or automatic retries.

Example real records (metadata retrieval does not validate their findings):

- [Evaluation of the Shortest Processing Time Scheduling Rule with Truncation Process](https://doi.org/10.1080/05695557308974923) — OpenAlex; source abstract available.
- [Guaranteeing timing constraints under shortest remaining processing time scheduling](https://doi.org/10.1109/emwrts.1997.613768) — Crossref; abstract unavailable in the response.
- [Improving Heterogeneous SOA-Based IoT Message Stability by Shortest Processing Time Scheduling](https://doi.org/10.1109/tsc.2013.30) — OpenAlex; source abstract available.

Evidence under .research-platform/validation/literature-v11:
live-query.json, live-browser-query.json, local-api-query.json,
live-literature-page.png and preserved-v1-evidence.json. Query and paper snapshots
are local ignored data, not committed scientific output or evidence of model use.

## Validation

- Windows platform: **206 passed, 39 skipped, 4 deselected**.
- WSL platform: **245 passed, 4 deselected**.
- Frontend: **19 tests passed**; TypeScript, production build and Prettier passed.
- Browser: six journeys cover existing native functionality plus literature
  search/selection and selected-source provenance through native ideation.
- Ruff and focused mypy pass. Existing deprecation/editor-bundle warnings remain.

Four Docker-executing cases were excluded to avoid real experiment reruns. Windows
skips are POSIX worker and opt-in Linux CLI cases. Full native offline integrations
cover both supported protocols with and without selected sources; fake provider
transport and process boundaries are used. Mock tests cover deduplication, abstracts,
missing metadata, cache/snapshot tampering, source failures, numeric/date rate limits,
DOI lookup, selection validation and unavailable search. No real model calls occur.

Commands from repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -k 'not actual_docker_generated_programs_and_independent_evaluator and (not native_application_approvals_docker_metrics_and_report or offline or selected)' -q --tb=short
.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent --platform linux
```

WSL uses the existing Python 3.12 environment and same pytest selection, with
GEMINI_CLI_OFFLINE_TEST=1 after sourcing nvm. Frontend commands are npm test,
npm run typecheck, npm run build and npm run format:check.

Browser fixture (fresh path required; all source/model/process boundaries mocked):

```powershell
.venv\Scripts\python.exe tests/research_platform/offline_native_server.py --offline-boundary --mock-literature --state .research-platform/validation/literature-v11/browser-final-20261122 --port 8012
```

From frontend, set PLATFORM_URL=http://127.0.0.1:5182,
PLATFORM_FRONTEND_PORT=5182, RESEARCH_API_URL=http://127.0.0.1:8012 and
NATIVE_OFFLINE_E2E=1, then run npm run test:e2e -- --workers=1.

The completed scheduling run remains at 13/20 calls with all 22 artifact records
and its original state/ledger snapshot unchanged. Previous completed run remains
at 17/20 with its original configuration/state hash. Existing waiting research
was not approved, resumed or modified. Original campaign HTTP 409 tests pass.

## Files changed

New: frontend/src/literature.tsx; frontend/e2e/literature.spec.ts;
tests/research_platform/test_literature.py; this document.

Modified:

- src/research_platform/literature.py — bounded public retrieval/cache/snapshots.
- src/research_platform/schemas.py — search input and selected snapshot IDs.
- apps/research_platform/backend/app.py — search route and run-creation validation.
- src/research_platform/services.py — explicit-source context/artifact/event.
- src/research_platform/workflow.py — source-grounded, untrusted-context ideation instructions.
- src/research_platform/reports.py — selected citation provenance for new runs.
- apps/research_platform/frontend/src/App.tsx — Literature navigation and route.
- apps/research_platform/frontend/src/create.tsx — selection review/attachment/removal.
- apps/research_platform/frontend/src/types.ts — optional selected IDs.
- apps/research_platform/frontend/src/test/platform.test.tsx — UI/selection regression tests.
- tests/research_platform/test_native_application.py — selected-context full workflow.
- tests/research_platform/offline_native_server.py — mocked scholarly boundary.
- docs/DEVELOPMENT_PROGRESS.md and docs/LOCAL_APPLICATION.md — progress and usage links.

The frontend paths abbreviated above are under apps/research_platform/frontend.

## Remaining limitations

Metadata relevance is provider-ranked and not independently reviewed. Records may
include chapters/reference entries and incomplete dates/authors. Abstracts are
source-supplied excerpts capped at 2,000 characters, may be copyrighted, and are
not full papers. No full-text/PDF crawling, semantic reranking or claim validation.
Source policies/quotas can change; public refusal is surfaced without paid fallback.
Local browser selections need their corresponding server snapshots; after cache
deletion select again. Many selected abstracts can exhaust existing token budgets;
budgets are not raised automatically. Local single-user scope and original-engine
launch restrictions remain. No new infrastructure or database was introduced.
