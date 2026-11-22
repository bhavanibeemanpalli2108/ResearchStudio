# Reseon v1.2.1 — live literature-grounded acceptance

Verified 2026-11-22. **Live acceptance passed for this bounded native scheduling
workflow with Groq/openai/gpt-oss-20b.** This is a real generated program, isolated
execution, independently measured result and cited report, not the offline fixture.
It does not establish scientific novelty, paper reproduction or provider reliability
for every future request. The original uncertain request causes remain unknown.

Run: `42dd6acadbb54b17870c66ed6737215a` — completed / evidence_recorded.

The user separately authorized the fresh run, approved the first gate with
statistical corrections, then explicitly approved candidate generation/execution
for final digest:
`2b59be4e2cc62f8acb85297bea17e6a39426e0229242fa9631fa8c9a48b16d2d`.
Both approvals used the existing HTTP endpoint (200) and durable worker/ledger;
neither gate was bypassed. The previous paused run was never resumed.

## Exact contract and actual generated method

See [the complete second-gate specification](RESEON_V1_2_1_SECOND_GATE.md) for the
immutable prepared design, all nine evaluator selfchecks and commitments.
Executed design matched it: scheduling_v1, one machine, 32 jobs, uniform integer
durations 1–10, seeds [42,123,456,789,101112], identical inputs within each pair.
Primary outcome is mean FIFO-minus-candidate total completion time, strictly >0.1.

The actual baseline returns original indices in FIFO order. The actual generated
candidate is deterministic SPT:

```python
order = sorted(range(len(durations)), key=lambda i: durations[i])
```

Python's stable sort preserves original order for tied durations. The program reads
JSON stdin and emits only JSON with the order permutation. Source inspection and
retained output audits confirm the generated method; no program was rerun for audit.

Candidate source SHA-256:
`15563242d290ca13542e6c7b4cec84a43a53db326f19d4e0291103bf0ed3ea18`.
Baseline source SHA-256:
`16306262bb9cae5d6f612737298d5a92a6c99d267d3934eb1d3ae5379cadb9ae`.
Dataset commitment:
`6053c53b2da1cb0087308a6437f1a8a1dd5cf2b30de11c9fc36619624b5e0d6a`.
Full source/hypothesis grounding hash:
`4bffc81c391d86ed66f4c3b82ec5728f6918700f0cbb993d7d349cc979541674`.

## Genuine results

| Seed | FIFO total completion time | SPT total completion time | FIFO minus SPT |
| --- | ---: | ---: | ---: |
| 42 | 3187 | 2126 | 1061 |
| 123 | 2723 | 2085 | 638 |
| 456 | 3010 | 2151 | 859 |
| 789 | 2759 | 2199 | 560 |
| 101112 | 2590 | 1916 | 674 |
| Mean | **2853.8** | **2095.4** | **758.4** |

The strict engineering criterion passed: **758.4 > 0.1**. Five paired observations,
not 160 independent replications. All five differences are positive; that count
is descriptive and is not the test p-value.

Exact two-sided paired sign-flip p-value: **0.0625**. **No statistical significance
at the 5% level is established.** The test assumes sign symmetry under a zero-effect
null; it does not test the separate 0.1 engineering threshold.
Exploratory Student-t 95% interval: approximately **[508.00, 1008.80]**, with its
normal/independent paired-effects assumptions. That interval does not override the
exact test's p-value. Results apply to the frozen synthetic setting and do not
establish generalization, causal claims or a novel discovery.

## Docker execution and cleanup evidence

Exactly **one experiment attempt**, **ten successful isolated program executions**
(five baseline/candidate pairs). Docker daemon events in the execution-stage window
contain ten labeled container die events, all exit code 0. Execution node timestamps:
2026-11-22 20:45:32–20:45:44 IST (UTC 15:15:32–15:15:44).
Retained files contain ten corresponding output JSON records and one execution receipt.

Each used the existing reviewed image
`sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`,
1 CPU, 256 MiB RAM, 64 PIDs, 10-second limit, no network or host mounts. Existing
read-only filesystem, unprivileged user, dropped capabilities and no-new-privileges
protections remained. Ephemeral /tmp is the existing bounded private tmpfs.
No image pull, installation or infrastructure change occurred.

Backend cleanup confirmed removal; a subsequent read-only
`docker ps -a --filter label=ai-scientist.dynamic=1` returned no containers.
No execution, timeout, cleanup or provider errors occurred during the authorized
candidate/execution/evaluation/report continuation. Failed first-gate schema
responses remain retained, rather than discarded or counted as scientific results.

## Actual model accounting

| Phase | Completed calls | Reported input | Reported output |
| --- | ---: | ---: | ---: |
| Through first gate, including two schema repairs | 5 | 3,354 | 2,267 |
| Preparation through second gate | 6 | 4,562 | 1,143 |
| Second resume readiness | 1 | 75 | 23 |
| Candidate generation | 1 | 616 | 252 |
| Evaluation | 1 | 1,197 | 406 |
| Synthesis | 1 | 1,120 | 485 |
| Total | **15** | **10,924** | **4,576** |

All 15 ledger rows completed; zero failed/uncertain holds. The initial conservative
request reservations remain separately visible in request_budget events. They are
estimates that are reconciled with actual usage, not a second cumulative token bill.
Current charged/reserved totals are 10,924 input and 4,576 output.

Unchanged limits: 20 calls, 40,000 input, 16,000 output, one iteration, one experiment,
300 active seconds. Remaining: **5 calls, 29,076 input, 11,424 output**, approximately
273.72 active seconds. Runtime used approximately **26.28 active seconds**.
The run is completed; none of its remaining allowance will be consumed for review.
Unknown monetary cost remains **null**, not zero. The user confirmed Free plan/no
paid usage; account billing is operator-attested, not independently guaranteed.
No provider switching, paid fallback, budget increase or automatic research retry.

## Literature, final report and independent verification

Full selected metadata, supplied abstract, OpenAlex/Crossref IDs, retrieval records
and snapshot ID remain equal to run creation. Citation:
https://doi.org/10.1057/jors.1991.170 — In-Soo Lee (1991),
*A Worst-Case Performance of the Shortest-Processing-Time Heuristic for Single
Machine Scheduling*. Its quadratic-lateness setting is not reproduced here; it
remains related-method context. Metadata and AI rationale are not verified findings.

Final cited Markdown report generated successfully. Its source artifact hash is
`770aea4e29c8987e63bae7b8da9a0562532c7970a439576aab161d4dffb41869`.
Read-only Chromium verification confirms completed report viewing, five measurement
rows, the real DOI link, threshold/p-value text and browser Markdown export exactly
equal to the server report. No browser mutation or generation request was submitted.
The retained AI proposal still mentions median only in labeled advisory/historical
text; the actual measured findings contain no median value. No original report,
raw proposal or result artifact was rewritten to conceal that discrepancy.

Read-only command:

```powershell
.venv\Scripts\python.exe scripts/verify_native_reproducibility.py --workspace .research-platform/local-app --run-id 42dd6acadbb54b17870c66ed6737215a
```

Result: passed. Independently checks the final approval/grounding/dataset identities,
all **26 artifact hashes**, retained inputs/outputs, actual FIFO/SPT orders, all five
measurements, aggregate means, exact p-value and ledger totals. Independently
integrated t critical value is 2.776445105197695; interval reproduces within numeric
precision. The audit executed **zero programs** and made **zero provider requests**.
Completed run evidence snapshot:
`bc82e0cd8ad70afc2b26c2f88fb326e0afd5417363d770aec73acd31f1d00f30`.

Ignored local receipts, independent audit, Docker event summary, browser export and
screenshots are in `.research-platform/validation/reliability-v121/`.
Original scientific artifacts remain in the existing application workspace.

Open the completed report:
http://127.0.0.1:5180/paper/42dd6acadbb54b17870c66ed6737215a.

## Preserved scope and remaining limitations

The paused `060988269faf4d1dbfde7a362b4718fb` run remains at 9/20 and 29,923/32k;
its two uncertain reservations were not cleared. Both previous completed runs and
their evidence remain unchanged. Their original failure statuses cannot be recovered
from this successful run. Native offline regression results remain those in
[the reliability report](PROVIDER_RELIABILITY_V1_2_1.md); no implementation changed
or automated research experiment was repeated during live verification.

This passes live acceptance for the selected provider/model and native scheduling
path, including literature → ideation → both approvals → generated candidate →
Docker experiment → trusted evaluation → cited report/export. It does not validate
arbitrary scientific protocols, full-text claims or full original Sakana campaigns.
Original launch remains restricted. No public deployment or additional campaign.
