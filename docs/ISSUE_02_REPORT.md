# ISSUE-02 — Nested model-call budget gateway

Current 2026-11-22 review, remaining lifecycle/free-policy/database-placement gaps
and ordered deployment/packet acceptance plan:
[Original Sakana next milestone](ORIGINAL_SAKANA_NEXT_MILESTONE.md).
The implementation evidence below remains historical; no live Gemini or original
campaign was authorized by the native release freeze.

Verified: 2026-11-20. Status: **partially resolved**.

Repository implementation and offline validation pass. Requests routed through the
new gateway use the existing transactional ledger. The intended dedicated VM,
trusted gateway service and host-controlled egress boundary are not deployed or
packet-tested. Original campaigns remain disabled; original web creation still
returns HTTP 409. This is not full original-engine acceptance.

## Root cause and transaction boundary

The native provider router reserved ModelUsage rows before generation, but nested
Gemini CLI requests used their own provider connection. Worker cycle/runtime
limits did not count those HTTP generation attempts. Giving the CLI a real key
would also permit bypassing an application-only gateway.

Previously embedded accounting is now shared in ledger.py. Native ResearchServices
retains its worker-lease assertion inside the locked reservation transaction. The
gateway does not pretend to own that native worker lease: it validates an expiring
GatewayGrant and an existing running original/full_research Gemini run, then
revalidates authorization under the same accounting lock before reserving.
SQLite uses BEGIN IMMEDIATE; PostgreSQL uses the existing transaction advisory
lock 7213921. Reservations, daily counts, run usage refresh and admission are in
one transaction. PostgreSQL deployment was not exercised in this validation.

There is one model-accounting system: existing ModelUsage rows. Each admitted
generation attempt gets a distinct row and request ID before any provider dispatch.
The gateway shares run/daily call, input/output reservation and monetary-cap
checks with native execution. Unknown remote pricing remains null; monetary caps
block unpriced remote requests. Failed, ambiguous, cancelled and interrupted
requests retain their reservations. No dispatcher retries, replay queue or
uncertain-request refunds were introduced. A crash after reservation but before
dispatch can conservatively consume a slot. A client retry requires a new slot.

## Implemented architecture

- Trusted gateway outside the disposable worker owns the real provider key.
  Production startup is opt-in, requires explicit DB configuration, trusted-host
  acknowledgement, TLS and an owner-only POSIX regular key file. Startup does not
  load the research .env, issue grants, migrate databases or start campaigns.
- Trusted Python grant issuance returns a random scoped token once; only its
  SHA-256 hash is stored. TTL defaults to 300 seconds, maximum 900. Grants bind an
  existing original run, explicit model allowlist and output cap. Native/completed
  runs, expired/revoked grants and mismatched run/model requests are rejected.
  There is no HTTP grant issuer or run creator.
- Authenticated Gemini v1/v1beta JSON and SSE endpoints use a fixed Google Gemini
  origin, server-side key substitution, no redirects/proxy inheritance and zero
  transport retries. There is no Groq/OpenAI translation or automatic fallback.
  Generation body/response sizes and overall dispatch duration are bounded.
- Run-scoped requests reserve first, then forward. Successful complete usage
  records reported input/output, including reasoning tokens; partial/missing usage
  keeps conservative reservations. Local model metadata/countTokens responses are
  bounded, do not call Google and label token estimates as estimates.
- Audit events carry request/grant/usage identifiers, classifications and payload
  digest, without request prompts or raw provider errors. Known credentials are
  redacted from returned JSON/SSE. Diagnostic and metadata counts are bounded.
- Gateway-mode worker configuration accepts only the scoped GEMINI_API_KEY and
  operator-controlled GOOGLE_GEMINI_BASE_URL. It checks platform-run binding,
  creates a fresh private CLI profile and refuses unmarked or changed profiles on
  resume. No OAuth/workstation profile or real key is copied into that profile.
- Prepared QEMU restrict=on user-network policy permits a fixed virtual gateway
  route via a fixed host-side socat target and loopback SSH management. It is a
  specification, not an installed filter. Existing start-vm.sh, Docker Desktop,
  WSL and host networking were not reconfigured.

The gateway is disabled by default. Existing explicitly operator-managed worker
mode is preserved, but still reports nested_call_budget_enforced=false. Neither
campaigns_enabled nor web-launch protection was enabled by this implementation.

## Database change

Migration 0002_gateway_grants adds rp_gateway_grants and its token-hash index only:
ID, run foreign key, unique token hash, allowed models, output policy, expiry,
revocation and creation time. It adds no competing call counters and does not
rewrite ModelUsage, scientific results or historical runs. Downgrade removes only
the new table/index. Temporary test databases exercise migration and preservation.

The existing live metadata database was opened read-only for verification, not
migrated. It remains at 0001_platform. A coordinated deployment must back up the
metadata/checkpoint/artifact state and explicitly apply the migration; ordinary
main-API startup has its existing migration behavior and must be included in that
rollout plan. No production migration was performed here.

## Installed Gemini CLI 0.68.0: actual offline evidence

Two opt-in WSL tests invoked the installed native Linux CLI, with fresh temporary
HOME/work directories, fake credentials, a temporary loopback gateway and
httpx.MockTransport as the provider. Both exited 0:

| Case | Mock provider generation dispatches | Observed request shape |
| --- | ---: | --- |
| Text response | 1 | streamGenerateContent, Gemini SSE |
| Read-only tool turn | 2 | functionCall then functionResponse follow-up, Gemini SSE |

Both produced the mocked OK response; each dispatch had a corresponding existing
ledger row. Costs remained null. A Node connection guard blocked non-loopback
network access; final evidence records zero external connections. This guard is
a test precaution, not an OS isolation claim. No real Gemini or Groq request was
made. Only fake provider credentials were used.

A custom GOOGLE_GEMINI_BASE_URL alone selected an auth mode that headless CLI
rejected with exit 41. Explicit supported gemini-api-key authentication accepts
the scoped gw_ token without modifying CLI validation. Usage statistics and
telemetry are disabled in the new profile; during investigation the test guard
blocked a telemetry attempt before transmission. Final runs made no such attempts.

Actual initial request size was 31,704 bytes; tool follow-up was 32,141 bytes.
The conservative UTF-8 reservation includes payload overhead, and prior usage
also consumes the run budget. The existing default 32,000-input-token budget may
therefore stop a later CLI turn. Compatibility fixtures explicitly use a synthetic
250,000-input-token budget; production defaults and historical budgets were not
increased. This validates transport/tool compatibility, not campaign capacity.

Supported protocol scope is text and client function tools. Binary/file/cache
inputs, batch jobs, multiple candidates, non-text output and provider-side tools
such as Google Search are refused until their accounting can be established.
Full Sakana campaign behavior and helper/compression model selection remain
unvalidated; every model requires an explicit grant allowlist entry.

Local evidence (not scientific results):

- .research-platform/validation/issue-02/cli-text-mock.json
- .research-platform/validation/issue-02/cli-tool-mock.json
- .research-platform/validation/issue-02/native-history-preserved.json

## Validation commands and results

All results below use the final code, fake credentials and temporary databases.
No new packages were installed.

```powershell
.venv\Scripts\python.exe -m pytest tests/research_platform --confcutdir=tests/research_platform -q --tb=short
```

Windows: **181 passed, 39 skipped, 1 warning**. Skips are 37 POSIX worker tests
and two explicitly opt-in installed Linux CLI tests. Existing LangChain warning
is nonfatal.

```powershell
wsl -d Ubuntu --exec bash -lc '. /home/sonusunny/.nvm/nvm.sh; cd /mnt/d/project/reseon/AI-Scientist-v3; GEMINI_CLI_OFFLINE_TEST=1 /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/research_platform --confcutdir=tests/research_platform -q --tb=short'
wsl -d Ubuntu --exec bash -lc 'cd /mnt/d/project/reseon/AI-Scientist-v3; /home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/pipeline/test_agsci_cli.py tests/pipeline/test_run_inspector.py -q --tb=short'
```

WSL Python 3.12: **220 passed, 2 warnings** for the platform, including 32 gateway
unit tests, two installed CLI mock tests and 37 POSIX worker tests. Existing
websockets deprecation warnings are nonfatal. Separate CLI/Inspector suite:
**41 passed**.

Gateway coverage includes: 21st request rejected at a 20-call cap; 40 concurrent
requests across ten threads/independent gateway DB engines dispatch exactly 20;
new retries consume slots; provider 401/403/404/429/503 and ambiguous timeouts
retain reservations; reopen/restart preserves charged pending rows; daily/token/
unknown-price caps; shared native-style reservations; expired/revoked/cross-run/
wrong-model credentials; completed native run rejection; SSE fragmentation,
client cancellation and upstream close; missing usage; reasoning usage; redirect
rejection; secret redaction; local metadata; unsupported inputs; scoped CLI
profiles; prepared network-policy negative cases. The existing HTTP 409/no-created-
run regression passes. These are repository/mocked checks, not VM packet tests.

```powershell
.venv\Scripts\python.exe -m ruff check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m ruff format --check src/research_platform apps/research_platform/backend tests/research_platform
.venv\Scripts\python.exe -m mypy src/research_platform apps/research_platform/backend --follow-imports=silent --platform linux
wsl -d Ubuntu --exec bash -n /mnt/d/project/reseon/AI-Scientist-v3/src/scripts/lib/container_agent.sh
git diff --check
```

Ruff and format pass (45 formatted files); Linux-target mypy passes (33 source
files); shell syntax and diff whitespace checks pass. Frontend code was unchanged;
no new browser acceptance or original research campaign is claimed.

Historical native run e2dcc7048b654d0daef9ba68d5010079 remains completed at **17/20**
calls, with three unspent calls. Its raw config/state SHA-256 is unchanged:
`e28fe4bc3e91767ea35f41ed20a6b60206c1c2479e1f61dd12b97696b59b6ee3`.
No experiment artifacts or prior scientific evidence were overwritten.

## Exact repository changes in this implementation

New:

- src/research_platform/ledger.py — shared transactional accounting.
- src/research_platform/model_gateway.py — authenticated Gemini gateway/launcher.
- src/research_platform/gateway_client.py — private scoped CLI profile.
- src/research_platform/gateway_network.py — prepared host network specification.
- apps/research_platform/backend/migrations/versions/0002_gateway_grants.py.
- tests/research_platform/test_model_gateway.py.
- tests/research_platform/test_gateway_cli.py.
- deploy/upstream-worker/GATEWAY.md.
- deploy/upstream-worker/gateway.env.example.
- deploy/upstream-worker/gateway-network-policy.json.
- deploy/upstream-worker/gateway-agent.Dockerfile.
- docs/ISSUE_02_REPORT.md (this report).

Modified:

- src/research_platform/services.py — reuse shared accounting; preserve lease check.
- src/research_platform/database.py — GatewayGrant authorization model.
- src/research_platform/upstream_worker.py — controlled scoped CLI preparation.
- src/scripts/lib/container_agent.sh — operator base-URL allowlist entry.
- tests/research_platform/test_storage.py — migration revision expectation.
- tests/research_platform/test_upstream_worker.py — gateway binding/profile cases.
- issues.md; docs/DEVELOPMENT_PROGRESS.md; docs/ARCHITECTURAL_CORRECTIONS.md;
  docs/UPSTREAM_WORKER.md; docs/DEPLOYMENT.md; docs/RESEARCH_ENGINE_ACCEPTANCE.md
  — current status, architecture and deployment references.

Pre-existing uncommitted repository changes were preserved; this list does not
attribute unrelated dependency or earlier issue changes to ISSUE-02.

## Remaining requirements and closure criteria

1. ISSUE-01 dedicated controller/daemon and resource isolation remain on hold.
   No QEMU, socat, VM, certificates or packages were installed/provisioned.
2. Provision the trusted gateway outside the disposable worker, protected provider
   key, reviewed TLS trust chain and bounded service/forwarder resources. The
   production key loader is POSIX-only; Windows ACL deployment is not implemented.
3. Integrate trusted controller run identity, grant delivery/renewal/revocation and
   stop/recovery lifecycle. TTL is deliberately short; no automatic renewal was
   added. Validate these with the intended shared database; PostgreSQL is untested.
4. Deploy immutable host-controlled egress and verify packets from the actual
   guest, including privileged/container contexts. Prove gateway TLS/auth works
   while direct provider/raw-IP/DNS/IPv6/metadata/host-service/proxy routes fail.
   Verify no worker access to real keys, shared sockets or host filesystem.
   Bound host-side socat processes independently of guest cgroups. The policy
   checker and Node mock guard alone cannot prove this boundary.
5. In the intended deployment, demonstrate exhaustion/revocation/restart accounting
   across nested CLI requests without direct bypass. Any real provider request
   still requires separate explicit authorization. Do not enable campaigns or
   ISSUE-03 merely because mocked requests pass.

ISSUE-02 can become resolved only when gateway accounting and network bypass
prevention are both validated in that deployment. Runbook:
[dedicated gateway deployment](../deploy/upstream-worker/GATEWAY.md).
