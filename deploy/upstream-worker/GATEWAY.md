# Original-engine model budget gateway — offline implementation

This is prepared configuration, not a deployed or approved VM/network. The gateway
has passed temporary-database and local mock-CLI tests. Direct provider bypass is
**not** claimed prevented until actual VM packet tests pass. Original campaigns
and HTTP 409 web-launch protection remain disabled. No provider requests are
authorized by these instructions.

## Accounting and authorization

Run the gateway on the trusted platform host **outside** the disposable worker.
It uses the same database, ModelUsage rows, run budgets, daily count and atomic
accounting lock as native ResearchServices. The native lease check is unchanged;
gateway admission uses a separately issued, hashed, expiring GatewayGrant for an
already-authorized original run. Grants cannot be issued for native/completed
runs. There is no grant-issuing, run-creating or campaign-launching HTTP endpoint.

Migration 0002 adds only rp_gateway_grants. It does not modify scientific evidence
or existing ledger rows. Apply migrations explicitly during an approved deployment,
not against research databases to run a test. Main API startup also uses the usual
migration mechanism; back up state before a coordinated version rollout.

Trusted code can call `issue_grant(db, platform_run_id, allowed_models=[...])`.
It returns a grant ID and the scoped token once; store/transmit the token privately.
Never log it. TTL is 1–900 seconds (300 by default), and output policy is bounded
at issuance. Expiry/revocation/run state/model scope are checked on every request
and rechecked under the reservation transaction lock. `revoke_grant` stops new
admissions; already admitted in-flight requests stay charged. Streaming checks
authorization between frames; stalled requests remain bounded by timeout.

Each new incoming generation attempt reserves a distinct ModelUsage row before
dispatch. This includes SDK retries, helper calls and repairs. There is no gateway
retry, queue, automatic replay or reservation refund after ambiguous failures.
Restarts leave reserved/uncertain rows charged. A committed reservation whose
dispatch never happened can therefore consume a slot conservatively. Rejecting a
request for an exhausted budget makes no provider request and creates no usage row.

Successful complete provider usage includes reasoning tokens. Missing/incomplete
usage retains the reservation. Remote monetary cost stays null. A configured
monetary cap blocks requests because pricing is not verified. All generation
requests, including compatibility/preflight calls, share the run cap. Metadata
requests use a separate bounded **local** RPC quota and do not dispatch to Google.
This bounds HTTP generation attempts, not Google's undisclosed internal computation.

## Gemini protocol and CLI 0.68.0

The base URL is `https://GATEWAY/runs/PLATFORM_RUN_HEX_ID`; the SDK appends
`/v1beta/models/MODEL:streamGenerateContent?alt=sse` or `:generateContent`.
The token is supplied in x-goog-api-key (Bearer authentication is also accepted).
The gateway substitutes the real provider key only in its own outgoing request.
Run identity comes from the scoped credential and matching path, not body claims.
Upstream origin is fixed to Google's Gemini API; no OpenAI/Groq translation,
arbitrary URL/header forwarding or redirects are supported.

Installed CLI 0.68.0 accepts a scoped `gw_...` credential in its supported
`gemini-api-key` auth mode. A custom base URL alone selected an auth mode that
headless CLI rejected (exit 41). `prepare_cli_environment` creates a fresh private
job profile with API-key auth explicitly selected, usage statistics disabled and
telemetry disabled. It refuses existing profiles rather than overwrite OAuth state.
The worker invokes this preparation for operator-owned gateway configuration and
checks the URL's 32-character platform run ID against its canonical UUID's hex form.
Resumes verify the existing profile; changed auth/statistics settings fail closed.

The worker's gateway-mode private agent file must contain **only**:

```dotenv
GEMINI_API_KEY=RUN_SCOPED_GATEWAY_TOKEN
GOOGLE_GEMINI_BASE_URL=https://10.0.2.100:8843/runs/PLATFORM_RUN_HEX_ID
```

The token above must be an issued gw_ token, never a Google API key. No
GOOGLE_API_KEY, Vertex/ADC/OAuth credentials or workstation profile is copied.
The Gemini environment allowlist now permits the operator-owned base URL. Research
questions cannot set this URL, credential or daemon configuration. Legacy explicit
operator-managed worker mode is not relabelled as hard-budget enforcement;
campaigns remain disabled and nested_call_budget_enforced remains false.

Supported offline cases include Gemini SSE text and a read-only tool/function
call plus functionResponse follow-up. Every dispatch in these tests is a mock.
The API supports v1/v1beta text/function requests, bounded output, local model
policy metadata and conservative **estimated** countTokens responses. Estimates
are labelled gatewayEstimated; discovery metadata is not generation readiness.

Explicit binary/file/cache input, batch jobs, multiple candidates, non-text output
and provider-side tools such as Google Search are rejected until their accounting
can be established. CLI compression/helper requests still require an explicitly
approved model. No automatic model/provider substitution occurs. Long contexts
can exceed the existing input reservation budget and must fail rather than raise
the budget automatically. The CLI protocol fixture uses a larger explicit fake-run
input budget solely to exercise its system prompt/tool schema; live defaults are
not increased. A full original campaign was not tested.

## Trusted gateway deployment (not executed)

Use gateway.env.example outside the worker. Set the existing platform-wide
DAILY_API_CALL_BUDGET consistently with native services. Store the real provider
key in a separate owner-only POSIX regular file, outside all worker mounts/images.
The launcher refuses symlinks, permissive ownership/modes, missing TLS and missing
trusted-host acknowledgement. It does not auto-load the research .env or issue
grants. Windows offline tests pass; a real Windows NTFS-ACL credential loader is
not implemented, so the deployment launcher uses a reviewed POSIX trusted host.

```bash
python -m src.research_platform.model_gateway --serve --host 127.0.0.1 --port 8843 \
  --tls-cert /private/gateway/server.crt --tls-key /private/gateway/server.key
```

This requires RESEARCH_GATEWAY_ENABLED=1 and the explicit private configuration;
the checked-in default is disabled. Access logs are disabled. Audit events retain
request/grant/usage identifiers, classifications and payload digests, not prompts,
credentials or provider error bodies. Provider headers are not relayed and known
credentials are redacted from JSON/SSE responses. Diagnostics and metadata quotas
are bounded. Revocation and cancellation do not refund in-flight calls.

## Prepared network boundary

gateway-network-policy.json and `python -m src.research_platform.gateway_network`
describe a **trusted host-side** QEMU user network with restrict=on. The only guest
egress is virtual IP 10.0.2.100:8843, forwarded by a fixed socat command to the
trusted gateway's 127.0.0.1:8843. SSH management ingress remains loopback-only.
No general DNS, IPv4/IPv6 egress, provider TCP access, Docker TCP/socket access or
host filesystem share is enabled. TLS cert SAN must match the virtual gateway
address. The optional gateway-agent.Dockerfile installs only a reviewed public CA
in a derivative agent image; real keys, scoped tokens and TLS private keys never
belong in that build context. Do not disable certificate verification.

This is an alternative prepared network argument set, **not** a change applied to
start-vm.sh or the shared Docker Desktop. It requires an approved QEMU installation,
reviewed host socat and trusted CA setup. No such packages were installed here.
The host QEMU/forwarder needs independent PID, memory, file-descriptor and connection
limits: guest cgroups alone cannot bound spawned host forwarder processes.

Before claiming bypass prevention, deploy and verify from the actual guest,
including privileged/container contexts: gateway TLS/auth success; direct Google
and other provider access denied; raw IP, DNS, IPv6, metadata IP and host-service
access denied; no proxy CONNECT/SSRF; exhaustion/revocation prevents further real
provider dispatch; gateway restart preserves counts; worker cannot alter the
host-side policy or read the real key. A guest-local firewall or JavaScript test
guard alone is not this security boundary.

No VM packet tests, live TLS trust, hosted gateway deployment, provider-key access
or paid generation were performed. ISSUE-02 therefore remains partially resolved.
