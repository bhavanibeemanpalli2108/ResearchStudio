# Native research engine: architectural corrections

Phase 1 infrastructure update (2026-11-20): the standalone original worker now
defaults to RESEARCH_UPSTREAM_CAMPAIGNS_ENABLED=0. Infrastructure readiness requires
private configuration and authenticated transport but not a live provider key;
it is distinct from campaign readiness. Dedicated guest templates, aggregate
controller/container cgroup verification, Desktop rejection, cross-process locking
and offline recovery are described in [ISSUE_01_REPORT.md](ISSUE_01_REPORT.md).
No native workflow or web launch integration was changed; nested model-call
accounting remains unenforced.

Updated for Mission 1, 2026-11-18. This document describes the implementation in
the current checkout. Measured campaign outcomes and incomplete acceptance items
belong in [the acceptance record](RESEARCH_ENGINE_ACCEPTANCE.md).

## Recovery provenance

The initial checkout contained the earlier platform implementation whose genuine
profile executed a fixed circle-packing comparison. A later local validation
image contained additional platform source:

| Recovery item | Recorded identity |
| --- | --- |
| Image reference | `ai-scientist-platform:validation-current` |
| Image ID | `sha256:dccf4449038b7512bff7cab5df4e0c3f215db05fae109f5d4c3129c84b7d26f6` |
| Image creation date | 2026-11-14 |
| Source location in image | `/app/src/research_platform/` |
| Preserved extraction | `../.research-platform/validation/mission1-20261117/recovered/` |
| Initial platform source snapshot | `../.research-platform/validation/mission1-20261117/workspace-before/research_platform/` |

Selected source was recovered through Docker filesystem extraction. The original
repository algorithms, examples and result directories were preserved. This was
a source recovery, not evidence that the image had completed any research run.
The recovered bundle protocol and execution runner supplied useful contracts and
isolation machinery; they did not establish independent scientific scoring.

The recovered general bundle preparation remains in
[legacy_preparation.py](../src/research_platform/legacy_preparation.py). The native
workflow uses [preparation.py](../src/research_platform/preparation.py) and the new
[experiment contracts](../src/research_platform/experiment_contract.py). It does
not fall back to the legacy bundle, a fixture, or the fixed circle benchmark
when a genuine request fails. The standalone recovered
[upstream client](../src/research_platform/upstream_execution.py) and
[worker](../src/research_platform/upstream_worker.py) are not wired into web
campaign submission.

## Execution identities and supported scope

| Profile / engine | Current behavior |
| --- | --- |
| `demo` / `native` | Explicit deterministic model responses and fixture measurements. Reports disclose the demonstration. |
| `free_research` / `native`, protocol 2 | Model-authored specification, baseline and candidate; independently scored bounded Python programs in Docker. |
| `full_research` / `original` | Web creation returns capability unavailable. The existing upstream CLI and run importer remain separate. |

The genuine native engine currently supports two trusted protocols:

| Protocol | Data and output | Independent metric and reference baseline |
| --- | --- | --- |
| `regression_v1` | Synthetic linear, quadratic or sinusoidal data; 32–256 training rows, 16–128 test rows, 1–8 features; candidate emits predictions. | Held-out RMSE or MAE; baseline must equal the mean of training labels. |
| `scheduling_v1` | 8–64 jobs with generated positive durations on one machine; candidate emits a permutation of job indices. | Total completion time; baseline must use FIFO input order. |

Both use 2–5 distinct fixed seeds, bounded noise/data parameters, 128–512 MiB
memory, and a declared per-process timeout of at most 30 seconds. Feasibility
must select one implemented protocol and retain the exact user question. An
unsupported question stops with an explanation of the missing capability; its
domain label does not authorize an unrelated experiment.

These protocols permit multiple generated algorithms and specifications. Their
conclusions remain limited to the declared synthetic data or job generator.
They do not establish arbitrary-domain research, novelty, a production model,
or completion of the original Sakana pipeline.

## Staged preparation and durable approvals

The existing [LangGraph workflow](../src/research_platform/workflow.py) now runs:

```text
intake → feasibility → planning → research-plan approval
       → literature → ideas → selection
       → experiment specification + baseline + evaluation declaration
       → trusted evaluator validation + dataset freeze
       → experiment approval → candidate generation → Docker execution
       → collection → interpretation → bounded decision
       → synthesis → report → validation → completion
```

Feasibility, specification, baseline, evaluation declaration and candidate are
separate model outputs with separate schema validation. Valid preparation
components are saved as immutable artifacts and reused for the same question,
objectives, constraints and selected idea. A malformed component receives its
own bounded repair request; valid components are not regenerated as a side
effect. Provider truncation and structured-output errors participate in that
repair path and still consume the request budget.

Planning, generated ideas, selection and interpretation also use
[typed narrative contracts](../src/research_platform/narrative_contracts.py) and
the same bounded component repair. The selector receives the actual validated
ideas and must return one of their IDs. Invalid native ideas are rejected rather
than replaced, and an unknown selection cannot silently choose the first idea.
The historical missing-options/fallback defect and subsequent live checks are
disclosed in the acceptance record. Schema validation cannot prove a hypothesis
is scientifically sound; concrete review remains required.

The research-plan gate approves direction. The later experiment gate approves a
concrete, frozen design. Its digest binds the complete specification, generated
baseline source, trusted evaluation declaration and actual private dataset
commitment. Missing, malformed or different digests fail closed in the API,
graph and candidate-generation boundary. A changed idea or constraint returns
to preparation and review. Candidate code is generated only after approval;
bounded iterations may replace the candidate while keeping the approved task,
baseline and data fixed.

Genuine jobs use `queued_v2`, `running_v2` and `waiting_v2` internally. Earlier
workers that claim only `queued` or recover only `running` cannot pick up a new
genuine job. Current workers also reject obsolete genuine execution protocols
before processing. User-facing run status remains `queued`, `running`,
`paused`, or the applicable terminal status. This queue fence prevents an old
fixed-benchmark worker from silently handling a new research request; it is not
a substitute for updating all API and worker processes together.

## Independent measurement and frozen data

The model supplies an evaluation declaration selecting a supported host-owned
protocol; it does not author the accepted scoring function. The
[dynamic executor](../src/research_platform/dynamic_execution.py) validates that
declaration against the specification. Nine host-authored analytical cases
check metric values and invalid outputs before experiment approval, including
weakened baselines, duplicate indices, nonfinite predictions and extra fields.

The host generates the actual fixture once using the declared seeds and a
private salt. Its manifest retains full run, specification, evaluator and data
identities. The private fixture is outside the downloadable artifact store.
Compact hashed directories and short atomic-write sibling names avoid the
Windows path-length failure observed during live validation.

Baseline and candidate receive the same public inputs in separate fresh
containers. Regression test labels and fixture salts stay on the host; neither
is mounted or passed through stdin. Candidate-generation context excludes
private data, evaluator code, raw prior predictions and regression generating
coefficients/intercept. Held-out features become available only as required by
the execution interface. Scheduling durations are necessarily public because
they are the problem input.

The host rejects malformed JSON, duplicate keys, nonfinite numbers, unexpected
fields, wrong prediction lengths and invalid permutations. It independently
verifies the generated training-mean/FIFO baseline before accepting the
comparison. Candidate-reported scores are not accepted. Results contain paired
seed observations, aggregate improvement, a Student-t interval and an exact
paired sign-flip calculation. With only 2–5 replications these summaries are
exploratory; generator scope and statistical assumptions remain explicit.

## Program execution and dependencies

Generated source is parsed and qualified on the host but never imported or
executed there. Static import/source checks are qualification, not a security
sandbox. The Docker boundary supplies the runtime controls:

- A locally available, operator-reviewed image is resolved to its content ID;
  runtime uses `--pull=never`.
- Each baseline/candidate process has no network, host mounts, provider keys or
  Docker socket; it runs as UID/GID 65534 with a read-only root filesystem.
- All capabilities are dropped, privilege escalation is disabled, and CPU,
  memory, PID, file descriptor, output and wall-clock bounds apply.
- A small ephemeral tmpfs supplies scratch space. Container removal is checked;
  inability to verify cleanup is a failure.

Current generated artifacts declare no third-party dependencies and can import
only the approved standard-library modules. The runner never installs packages
or downloads images on behalf of a research question. Missing Docker, an absent
reviewed image or unsupported dependencies stop execution. There is no host
execution fallback.

Receipts bind source digests, the frozen data commitment, run identity, image
reference and evaluator version; measurements also record the resolved image
ID. A matching receipt is reused without a second experiment. A terminated
process cannot be resumed: absent a valid receipt, recovery pauses for explicit
review and charges any subsequent attempt within the existing durable cap.

## Budgets, diagnostics and remaining boundaries

The default run request retains 20 model calls, 32,000 input tokens, 16,000
output tokens, two iterations, three experiment attempts and 300 seconds of
active runtime. Provider retries and repairs count. Failed requests with
unknown usage retain conservative reservations. A model listed by discovery
can still reject generation for an account; discovery is not a successful
generation test. No quota or billing increase follows from a provider failure.

Structured schemas are included in actual model instructions as well as the
provider request format. Safe diagnostic classifications retain status and
bounded error metadata without publishing credentials, provider response bodies
or private reasoning. Optional LangSmith export uses explicit redacted spans;
automatic graph tracing is disabled. Local source artifacts are evidence, not
proof that an external trace was delivered.

The web service remains single-user and local-only. It has host/origin checks
but no implemented multi-user authentication or tenancy boundary. The original
engine's nested coding-agent requests bypass the native provider ledger. Its
standalone worker requires a dedicated Linux controller, separate daemon and
finite cgroup limits, private credentials and an independently enforceable or
explicitly approved operator budget policy. That recovered worker reports
`nested_call_budget_enforced=false`; its existence does not remove the current
web-launch block. See [local deployment](DEPLOYMENT.md) and the
[original-worker audit](UPSTREAM_WORKER.md).


## ISSUE-02 gateway accounting update — 2026-11-20

The offline Gemini gateway now shares ledger.py with native ResearchServices:
same ModelUsage rows and SQLite/PostgreSQL accounting lock, run/daily/token caps
and unknown-price rejection under monetary caps. Native reservation still asserts
its worker lease; gateway reservation instead rechecks an expiring hashed grant
and active original-run identity inside that transaction. Failed/uncertain calls
remain charged; no replay/refund dispatcher was added.

CLI text/function SSE compatibility and concurrency caps pass mocked tests. This
closes the repository routing/accounting gap only for gateway-routed requests.
Dedicated host egress is prepared, not deployed or packet-tested, so original
execution still lacks a verified global hard budget. Legacy operator-managed mode
is not relabelled; campaigns and web launch stay disabled. See
[ISSUE-02 evidence](ISSUE_02_REPORT.md) and
[gateway runbook](../deploy/upstream-worker/GATEWAY.md).
