# Reseon — local native Research Studio v1

Literature discovery: http://127.0.0.1:5180/literature. Search OpenAlex/Crossref,
select papers and review their attachment to a new native task. Searching does
not start generation. See [v1.1 instructions and verification](LITERATURE_DISCOVERY_V1_1.md).

Current checkpoint: [v1 verification and release recommendation](RESEARCH_STUDIO_V1.md).

## v1 report presentation and operation

Native preview and Markdown export share GET /api/runs/RUN_ID/report: a
deterministic read-only presentation of the final approved contract/digest and
trusted measurements. Superseded proposals are labeled historical. Unverified
model narrative remains in original response artifacts, not final measured claims.
Original reports, code, outputs, state, ledger and scientific evidence are unchanged;
the page links the immutable original report. Saved browser drafts are separate
user edits; reset to generated paper to use the current presentation.

Report review/export consumes no model calls. The current review instance blocks
Groq requests until fresh Free-plan verification is configured for authorized live
use. Never resume a completed run merely to refresh presentation. Original-engine
launch remains HTTP 409. The sidebar is now Reseon and its personal-workspace
placeholder card is removed. Evidence refreshes on status changes so completed
measurements are not hidden by an earlier empty response.

Startup/stop troubleshooting:

- Windows frontend http://127.0.0.1:5180; health
  http://127.0.0.1:8010/api/health; docs http://127.0.0.1:8010/docs.
  Built mode uses the API port for both frontend and backend.
- The launcher starts the independent worker automatically. Manual API and worker
  processes must use identical Python and storage settings. Health alone is not
  proof of worker execution.
- Stop with Ctrl+C; answer Y if Windows npm asks to terminate its batch job.
  Keep workspace paths unchanged when restarting. Do not run Windows/WSL workers
  against the same workspace simultaneously.
- Occupied ports: select another API/frontend port; do not stop unrelated services.
  Vite uses strictPort. Missing built index now fails before state preparation;
  build the frontend once before -Built or WSL --no-frontend.
- WSL Rollup missing: serve the portable built frontend, preserving shared Windows
  node_modules. RESEARCH_PYTHON selects the existing native Linux venv.
- Docker unavailable: start the existing Linux Docker Desktop engine and inspect
  daemon/image readiness. No image pulls or installation happen automatically.
- Inspect worker events/logs and artifacts. Verbose httpx/httpcore INFO logs are
  suppressed because URLs can carry credentials. Avoid enabling transport debug
  output or sharing older unredacted terminal logs.

Verified 2026-11-20. Single-user, loopback-only. This guide uses the existing
checkout, Python environments, Docker Desktop and Groq provider. No VM or
original-engine campaign is needed. The current Windows frontend is
http://127.0.0.1:5180 and API documentation is http://127.0.0.1:8010/docs.
Existing services on 8000/5173 were left untouched.

## Start from Windows 11 / PowerShell

Run from D:\project\reseon\AI-Scientist-v3. Docker Desktop must already be running
with its Linux engine. Dependencies and the reviewed python:3.12-slim image are
already present on this machine; no reinstall/pull is part of these steps.

```powershell
$env:DATABASE_URL='sqlite:///./.research-platform/local-app/platform.db'
$env:ARTIFACT_ROOT='./.research-platform/local-app/artifacts'
$env:CHECKPOINT_PATH='./.research-platform/local-app/checkpoints.db'
./scripts/start_research_platform.ps1 -Port 8010 -FrontendPort 5180
```

Open http://127.0.0.1:5180. The launcher starts FastAPI, the separate durable
worker and Vite. Keep that terminal open. Stop with Ctrl+C; only its child services
are stopped, and runs/artifacts/checkpoints are retained. Occupied ports now fail
explicitly instead of silently moving the frontend. Choose other free ports when
needed. Development service logs appear in the launcher terminal; use a second
terminal to inspect the UI/API. The worker emits safe run IDs/error classes.

For the built single-origin application:

```powershell
npm.cmd --prefix apps/research_platform/frontend run build
./scripts/start_research_platform.ps1 -Built -Port 8010
```

Open http://127.0.0.1:8010. Keep the same three storage variables when restarting.
The new local-app workspace contains validation demo runs; it is separate from
prior research evidence. Default project storage and prior live databases were
not migrated or overwritten. Do not switch a running API/worker to a different
storage path. To use another existing workspace later, stop its services, back up
metadata/checkpoints/artifacts/private fixtures together and select matching paths
for both API and worker. Startup applies existing migrations to the selected DB.

## Start from WSL Ubuntu

The existing native Linux Python environment is separate from Windows .venv.
Use the frontend build produced above; it is portable browser JavaScript.
Windows node_modules currently lacks Linux's optional Rollup binary. Do not run
npm ci in that shared directory as a repair: it would replace Windows dependencies.
No Linux frontend packages were installed for this milestone.

```bash
cd /mnt/d/project/reseon/AI-Scientist-v3
export RESEARCH_PYTHON=/home/sonusunny/.local/share/agsci-mission1-venv/bin/python
export DATABASE_URL=sqlite:///./.research-platform/local-app/platform.db
export ARTIFACT_ROOT=./.research-platform/local-app/artifacts
export CHECKPOINT_PATH=./.research-platform/local-app/checkpoints.db
bash scripts/start_research_platform.sh --no-frontend --port 8010
```

Stop the Windows instance first before using the same workspace from WSL. Open
http://127.0.0.1:8010. Ctrl+C stops the WSL API/worker groups. The verification
used a separate temporary WSL workspace on port 8014 and stopped it afterwards.
Native Node/Gemini CLI are not needed to serve the built native application.
If using existing Linux CLI tools separately, source ~/.nvm/nvm.sh first.

## Configure Groq safely and enforce the Free-plan prerequisite

Keep your existing GROQ_API_KEY in repository-root .env or the service environment.
Do not paste it into the browser, task instructions, source files or reports.
The key is already configured on this machine; it was not displayed or changed.
.env is Git-ignored. Generated experiments receive no host mounts, environment
secrets, Docker socket or network; programs/data go through bounded stdin.
No other provider key is required for these native protocols.

Groq's public documentation supports Free-plan access, but it cannot establish
the billing state of your organization. You confirmed Free plan/no paid usage in
this conversation. Model discovery, HTTP 200 and a configured key are not billing
verification. Recheck that key's organization in Groq Console Billing and Limits
before enabling requests. Paid Developer-plan usage is not authorized here.

Every Groq transport attempt, including discovery, requires a key-bound operator
attestation no older than 24 hours. Missing, malformed, naive, future, expired or
wrong-key attestations fail before dispatch/reservation. The app cannot detect a
remote plan change after attestation; this is not a provider-enforced no-charge
header or a guarantee of zero cost. Unknown monetary cost remains null, and a
monetary cap still rejects unpriced remote calls. No automatic billing upgrade,
fallback or budget increase is performed.

After verifying the Free plan, and only when ready to authorize your live use,
set these **nonsecret** variables in the same terminal before starting services:

```powershell
$env:GROQ_FREE_TIER_VERIFIED_AT=(Get-Date).ToUniversalTime().ToString('o')
$env:GROQ_FREE_TIER_KEY_SHA256=(& .venv\Scripts\python.exe -c "import os,hashlib; from dotenv import load_dotenv; load_dotenv('.env'); print(hashlib.sha256(os.environ['GROQ_API_KEY'].strip().encode()).hexdigest())")
```

WSL equivalent, with RESEARCH_PYTHON set above:

```bash
export GROQ_FREE_TIER_VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
export GROQ_FREE_TIER_KEY_SHA256="$("$RESEARCH_PYTHON" -c 'import os,hashlib; from dotenv import load_dotenv; load_dotenv(".env"); print(hashlib.sha256(os.environ["GROQ_API_KEY"].strip().encode()).hexdigest())')"
```

These commands read the existing key locally and output only its hash into the
shell variable. They do not verify billing remotely, change keys or call Groq.
Do not routinely renew the timestamp without checking the account. You can store
the two nonsecret values in .env instead, but expiry still applies. Restart API
and worker after configuration changes. Without an attestation, browsing/demo work remains available and Groq requests are blocked. After explicit chat authorization the current instance was restarted with a process-local attestation; its new live scheduling study completed after both explicit human approvals.

Sources: [Groq Billing FAQ](https://console.groq.com/docs/billing-faqs),
[organization rate limits](https://console.groq.com/docs/rate-limits),
[supported models](https://console.groq.com/docs/models). Free quotas are shared
across the organization, including other applications. A quota failure is not a
reason to upgrade or switch providers automatically.

## Complete a supported research run

1. Open New research / Free research. Use the regression example or a single-
   machine scheduling question. Select Groq and openai/gpt-oss-20b (now defaults).
   The locally configured choice makes no discovery request and is labelled
   unverified until actual generation succeeds.
2. Review the 20-call, 32k input/16k output token, two-iteration, three-experiment,
   300-active-second limits. Keep human approvals enabled. Launch creates a new
   run; it does not reuse a completed run's remaining budget.
3. Review and approve the research plan. The worker then prepares the baseline,
   independent evaluator and frozen dataset commitment.
4. Review the exact experiment and digest at the second gate. Only approving that
   digest authorizes candidate generation/execution. Reject or pause if the plan
   does not answer the intended question.
5. Watch events, node progress and logs. Experiments show actual paired seed
   measurements; this scope supports synthetic regression and scheduling only.
   Docker containers are CPU-only: one CPU, 128–512 MiB RAM, 64 PIDs and at most
   30 seconds per isolated execution, with no network/mounts/secrets.
6. Open Experiments and Paper & artifacts. Download Markdown; Print/PDF opens the
   browser's print/save-as-PDF flow. Public report/artifact downloads preserve
   immutable server evidence; browser draft edits do not rewrite it.

Preflight is charged again on each worker start/approval resume. The tested
three-phase journey used three preflights, all inside the run's call budget.
Retries, repairs and failed/uncertain requests also count. Exhaustion fails closed;
inspect the event and remaining budget rather than resetting accounting.

OpenAlex metadata is optional: failures now emit an explicit warning and the run
continues without retrieved citations. No citations are invented, and such a run
cannot establish novelty or literature coverage. Report limitations still need
human review. Synthetic results are not general scientific acceptance.

## Inspect, stop and recover

- Run views expose progress, events/logs, measurements, usage and artifacts.
- GET /api/health checks API/database; /api/system/capabilities checks Docker/scope.
  GET /api/providers exposes configuration/attestation state, never keys.
- Pause/Cancel apply the existing durable controls. After restarting, inspect
  recovery events before explicitly resuming. Approval waits do not consume active
  runtime. Missing execution receipts do not magically resurrect interrupted work.
- Back up the selected workspace as a unit. Never clear usage or edit job states
  to bypass a budget. Keep the real key outside backups shared as evidence.

## What is unavailable

Original Sakana campaigns and their HTTP 409 launch protection remain unchanged.
Dedicated VM provisioning, global original-engine gateway bypass prevention,
public hosting, multi-user access and independently validated additional research
protocols remain unavailable. No new provider/MCP/OpenRouter integration was added.
The authorized live Groq scheduling study completed with actual Docker measurements and report generation after both explicit approvals. Its immutable original draft retains superseded proposal text; the current v1 presentation now labels that text historical and identifies the approved executed contract first. Offline mock transport is not represented as live generation.
