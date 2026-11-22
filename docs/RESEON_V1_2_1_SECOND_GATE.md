# Reseon v1.2.1 — prepared experiment, second approval gate

Subsequent status: the user explicitly authorized this digest; execution and cited
report generation completed successfully. This document retains the pre-execution
gate evidence. See [final live acceptance](RESEON_V1_2_1_LIVE_ACCEPTANCE.md) for the
actual candidate, ten Docker executions, measurements and 15/20 final accounting.

Verified 2026-11-22 for NEW run `42dd6acadbb54b17870c66ed6737215a`.
The user approved first-gate preparation with explicit statistical corrections.
The existing approval endpoint returned HTTP 200; feedback and corrected constraints
were retained. Status is now **awaiting_approval / approval**. No second approval
has been submitted, candidate generated, Docker program executed or experiment run.

## Exact prepared specification

```json
{
  "schema_version": 1,
  "title": "Synthetic Evaluation of SPT vs FIFO on Single‑Machine Job Sets",
  "research_question": "Does shortest-processing-time ordering reduce total completion time versus FIFO on reproducible synthetic single-machine job instances?",
  "hypothesis": "SPT ordering yields lower total completion time than FIFO on uniformly generated job sets.",
  "protocol": "scheduling_v1",
  "dataset": {
    "kind": "scheduling",
    "generator": "uniform_jobs",
    "job_count": 32,
    "machine_count": 1,
    "duration_min": 1,
    "duration_max": 10
  },
  "evaluation": {
    "metric": "total_completion_time",
    "direction": "minimize",
    "minimum_improvement": 0.1
  },
  "resource_limits": {
    "timeout_seconds": 10,
    "memory_mb": 256
  },
  "seeds": [42, 123, 456, 789, 101112]
}
```

The literal model hypothesis is operationalized by the frozen evaluator:
mean(FIFO total completion time minus candidate total completion time) **>0.1**.
This is a strict engineering acceptance rule, separate from statistical significance.
The exact two-sided paired sign-flip p-value tests a symmetric zero-effect null;
with five pairs its minimum is .0625, so no 5% significance claim is allowed.
Existing mean, standard deviation, SEM and assumption-dependent Student-t interval
are exploratory summaries, not independent evidence of generalization.

The retained AI idea's method still mentions a median. That is superseded advisory
proposal text, not a field in the approved evaluator declaration or a promised
measurement. No median is computed/reported as a result. Original model text was
preserved rather than rewritten. The exact specification and trusted evaluator
control the actual experiment; no study results exist at this gate.

## Frozen identities

- Final **second-gate approval digest**:
  `2b59be4e2cc62f8acb85297bea17e6a39426e0229242fa9631fa8c9a48b16d2d`
- Preparation-only digest:
  `0a6f39b3bd25d9ab6ff237e44f2aa28e5c9e894b7548b1206a1408d856ffbb09`
- Specification hash:
  `0e24912692ad0f7b0101fc8e060cd880102013e5113af86e53ef798bcf878a74`
- Dataset commitment:
  `6053c53b2da1cb0087308a6437f1a8a1dd5cf2b30de11c9fc36619624b5e0d6a`
- Literature/hypothesis grounding hash:
  `4bffc81c391d86ed66f4c3b82ec5728f6918700f0cbb993d7d349cc979541674`
- Generated FIFO baseline source hash:
  `16306262bb9cae5d6f612737298d5a92a6c99d267d3934eb1d3ae5379cadb9ae`
- Trusted evaluator hash:
  `9be095cbcd456e1ea009881cfe2a77d5875a3699c02de0316a74367afa45fd66`

Independent read-only checks validate the prepared artifact schema and digest,
specification hash, baseline source hash, full grounding manifest and final binding
of preparation + dataset + grounding. No final approval is implied by a hash.

## All evaluator selfcheck results

These are host-owned analytical examples, not measurements from the new study.
No generated baseline/candidate was executed for these checks.

| Check | Expected | Actual | Passed |
| --- | --- | --- | --- |
| known_rmse | 1.5811388300841898 | 1.5811388300841898 | yes |
| known_mae | 1.5 | 1.5 | yes |
| known_fifo_completion | 13.0 | 13.0 | yes |
| known_spt_completion | 10.0 | 10.0 | yes |
| duplicate_job_rejected | rejected | rejected | yes |
| nonfinite_prediction_rejected | rejected | rejected | yes |
| undeclared_label_field_rejected | rejected | rejected | yes |
| weakened_mean_baseline_rejected | rejected | rejected | yes |
| changed_fifo_baseline_rejected | rejected | rejected | yes |

Result: **9/9 passed**. Five case commitments retain exactly the approved seeds.
Private fixture integrity is established by the existing freeze procedure; hidden
labels and private salt were not shared with models or exported in this report.
Generated baseline runtime behavior will still be checked by the trusted scorer
if execution is separately approved; static source inspection currently confirms
that it returns `list(range(len(durations)))`.

## Baseline/candidate contract

- Baseline: generated standard-library FIFO program. JSON stdin with durations
  and seed; JSON stdout with `order` equal to original job-index order.
- Candidate required by the study: SPT, a permutation of all job indices ordered
  by nondecreasing duration. **No candidate source exists yet.** No claim is made
  about an actual generated algorithm until candidate generation is authorized.
- Both programs receive identical inputs within each seed pair. Trusted host
  code measures total completion time and rejects malformed/duplicate indices.
- One experiment attempt, five pairs, ten isolated program executions if approved.
- Each process: 1 CPU, 256 MiB, 64 PIDs, 10 seconds, no network/mounts.
- No paper replication/novelty claim, no provider/model change or paid fallback.

Full selected source snapshot and provenance equal the run-creation receipt.
DOI remains https://doi.org/10.1057/jors.1991.170, OpenAlex/Crossref source IDs and
retrieval records unchanged. The manifest keeps the full supplied abstract while
model prompts use bounded excerpts. Lee (1991) concerns quadratic lateness and
remains related-method context rather than proof of this different outcome.

## Actual preparation accounting

| Additional request | Initial input reservation | Output cap | Reported input | Reported output |
| --- | ---: | ---: | ---: | ---: |
| Resume preflight | 78 | 128 | 75 | 23 |
| Ideas | 5,113 | 1,024 | 1,190 | 449 |
| Selection | 3,579 | 512 | 868 | 152 |
| Specification | 6,408 | 1,536 | 1,516 | 248 |
| Baseline program | 1,904 | 1,536 | 477 | 170 |
| Evaluation declaration | 1,589 | 512 | 436 | 101 |
| Total: six completed calls | **18,671** | **5,248** | **4,562** | **1,143** |

The initial allowances are conservative per-request estimates, not cumulative
actual charges. Each successful completion replaced its reservation with reported
usage; there are no uncertain reservations. The budget-event records preserve the
original estimates separately. No provider errors or additional schema repairs
occurred during this preparation phase. Earlier first-gate feasibility/planning
repairs remain in the ledger and original response artifacts.

| Current budget | Used | Remaining | Limit |
| --- | ---: | ---: | ---: |
| Model calls | 11 | 9 | 20 |
| Input tokens, reported and charged | 7,916 | 32,084 | 40,000 |
| Output tokens, reported and charged | 3,410 | 12,590 | 16,000 |
| Active seconds | ~10.64 | ~289.36 | 300 |
| Experiment attempts | 0 | 1 | 1 |

One iteration remains the limit. Unknown monetary cost stays null. Later-stage
capacity remains available; all budgets, gates and accounting rules are unchanged.
Nominal continuation needs one resume readiness preflight plus candidate generation,
evaluation and synthesis (four model calls), subject to bounded repair and guards.
No continuation request has been made.

## Review and evidence

Local review URL:
http://127.0.0.1:5180/workspace/42dd6acadbb54b17870c66ed6737215a.
The frontend shows the exact final digest and literature/hypothesis commitment;
read-only browser inspection submits no approvals. Original prepared/grounding/
validation artifacts remain linked from the application. Ignored public receipts
are under `.research-platform/validation/reliability-v121/`.

The prior paused run and both completed historical snapshots remain unchanged.
The next step requires explicit authorization of the exact final digest above
before candidate generation or any Docker execution. Live acceptance remains
incomplete until a genuine experiment and cited final report succeed.
