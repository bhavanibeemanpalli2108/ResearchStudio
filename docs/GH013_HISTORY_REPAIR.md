# GH013 recovery and cleaned publication history

2026-11-23, Asia/Calcutta. The owner explicitly authorized a targeted rewrite of
unpublished destination history after an atomic push was rejected. No GitHub
push-protection bypass, remote-history rewrite, force push, provider request,
credential validation call, infrastructure change or evidence deletion is allowed.

## Cause and classification

GitHub GH013 identified a Slack token pattern at original upstream commit
`2b8aa39285c35aaca3b0e06dd121061ef8a2d854`,
`tests/checkpoints/test_run_checkpoint.py:740`. The value is a deterministic
synthetic alphabet canary in `_PROVIDER_TOKENS`, used by
`test_secret_bearing_content_is_excluded` to ensure credential-shaped checkpoint
content is rejected. It is not used to authenticate or contact Slack. Its full
value is deliberately omitted here. Other history findings were reviewed as
synthetic redaction fixtures as recorded in the prior publication preparation.
No suspected genuine credential was identified and no provider was contacted to
test token validity. A genuine-credential suspicion would stop publication and
require provider-specific revocation/rotation; no scanner guarantee is claimed.

The Slack canary is now assembled from fixed, repetitive components at test
runtime. The test still passes the complete token-shaped value into the existing
secret scanner and asserts exclusion. Scanner rules and GitHub protections are
unchanged; no allowlist, suppression, or bypass was added. The published source
contains neither the original contiguous value nor the matching Slack literal.

## Recovery and scope

Before changing refs, a separate private recovery folder outside this repository
received a verified `original-history.bundle`, a full Git-metadata copy and an
`original-refs.json` manifest. It preserves all 16 original commits, branches,
three annotated tags, original signatures and private Codex refs. The exact
private backup path is supplied locally, not published. Do not push that backup.
Complete old/new mappings are also retained privately beside the backup.

Destination GitHub main was fetched and verified at
`77bddd3289e2c99e0a2d6df09fbd4180a30c2ad8`. The flagged upstream commit was not
reachable from that destination's published history; no remote tags existed.
The published LICENSE commit, its signature and ancestry are preserved exactly.
This changes our local copy of upstream ancestry, not the original Sakana remote.

A checked Git-plumbing plan recreated 15 of 16 commit objects, preserving parent
ordering, merges, authors, committers, timestamps and messages. Every historical
tree comparison differs only at the affected checkpoint test file. All unrelated
source, native application behavior and release contents remain byte-identical.
No `.research-platform` database, experiment, report, artifact or budget ledger
was rewritten. A final tip-only formatting cleanup fixes existing Ruff formatting
in that test file; its AST is unchanged. That formatting is not spread through
the historical rewrite.

Two invalidated upstream merge signatures were removed from the cleaned copies:
`e49408e937115081f68d90838a79483f4f1c1d35` and
`df8313889a004f8a44a472e19a833cd547bb828a`. They cannot remain valid after parent
changes. Their original signed objects remain in the private recovery copy. No
new verified signature is claimed. The destination's published LICENSE signature
is untouched. Historical documentation/scientific records retain their original
commit references; the mapping below explains their cleaned equivalents.

Private local Codex tree snapshots and reflogs are preserved, but are not branches
or release refs selected for publication. Publication uses explicit main/tag
refspecs only, never `--mirror`, `--all` or backup refs. Unreachable old objects
are not erased, and the backup is never pushed.

## Commit mapping

The mapped Phase 2 head is `9ace757b61e79bc96381fdf9718c095bb310991a`. A subsequent publication-audit
commit records this report and the AST-identical current-tip formatting; the
final pushed hash is verified separately after a successful push.

| Original commit | Cleaned commit |
| --- | --- |
| `2b8aa39285c35aaca3b0e06dd121061ef8a2d854` | `5ea47ee3ed4fe8b626e9c5f16c599bb494a58da6` |
| `7ac627e6e9ece605525ea869e62f60acdd415531` | `958bee5801110c8ac4ec0fe81babd39d1a19b0c0` |
| `8236a6f71e4f754986fcae5a8af4c89620f53541` | `644293e0ca2bdf98dfb8b6eb8277ca9786571799` |
| `9ed986dea4f55cbd99680cb5c2a20e0abc247f2b` | `7bcf7ff1824150a88d6acf4942686d808895a114` |
| `7eca5af83b66691477a687aff8fde318e30c3999` | `fa53d96477b2a781c177303d251fac444299616e` |
| `e49408e937115081f68d90838a79483f4f1c1d35` | `a827d8741907cbf24b603a7ff8a866686af4915d` |
| `322f7a8717849211b145d78fceaa0df901de947d` | `09b8bf03418ce20eadda6bf92f3428d98c90cbea` |
| `df8313889a004f8a44a472e19a833cd547bb828a` | `6910a08b07e9a068334b0de76dbbc878258487fd` |
| `04074f1235fb19560ea49849bc5b0b206366270a` | `62da1b216e57c36305a56d9f51f22c558c8fa9cb` |
| `77bddd3289e2c99e0a2d6df09fbd4180a30c2ad8` | `77bddd3289e2c99e0a2d6df09fbd4180a30c2ad8` |
| `acc38271ca56fad7189a498784e3f7ada59a16ec` | `6ee4b464e2129ebe2eb1bb121b26f0895502e9a1` |
| `66713dbc456c9a3705a11350eebe28a3fe94c98a` | `5155367f2ea666654b3199f15df7ffa7fa1ea149` |
| `fffd4c92dd78ef7a3c45e61fffa5f920e8b765de` | `3cd4150406f7f37437e71c805e13c3bbe4786e33` |
| `3a2eecef142a74394e5e093136c521af98750f6b` | `f3011bc185454edf1c60ab64a3506c25acbac339` |
| `e8b9e27531fa4f15ee6f07fa1585dfeac0861742` | `f324e399fe8b8ecbdcdd203c052a16b2c0b71acc` |
| `717f5512ce2ab8932e5e5535153244ac81045412` | `9ace757b61e79bc96381fdf9718c095bb310991a` |

## Release tags

All three tags remain annotated, with identical names, tagger identity/date and
description bytes. Only their target object changes. Original tag objects stay
in the external recovery copy; no existing remote tag is overwritten.

| Tag | Original target | Cleaned target |
| --- | --- | --- |
| `reseon-native-v1.0.0` | `66713dbc456c9a3705a11350eebe28a3fe94c98a` | `5155367f2ea666654b3199f15df7ffa7fa1ea149` |
| `reseon-native-v1.1.0` | `fffd4c92dd78ef7a3c45e61fffa5f920e8b765de` | `3cd4150406f7f37437e71c805e13c3bbe4786e33` |
| `reseon-native-v1.2.1` | `3a2eecef142a74394e5e093136c521af98750f6b` | `f3011bc185454edf1c60ab64a3506c25acbac339` |

No extra release tag or GitHub Release is invented. Old release provenance in
retained research records remains valid through the recovery copy and mapping.

## Verification and publication gates

Verified after the historical rewrite and AST-identical tip formatting:

| Check | Result |
| --- | --- |
| Checkpoint / bounded-process / task-gate / repair / revision suites | 194 passed |
| Native platform / CLI / Inspector | 347 passed; four genuine Docker cases excluded |
| Frontend Vitest | 21 passed |
| Ruff lint / formatting | Pass; affected checkpoint and existing platform scope |
| Linux-target mypy | Pass; 37 platform/backend sources |
| TypeScript / build / Prettier | Pass; existing large-bundle warning remains |
| Git full integrity / historical source and metadata comparison | Pass |
| Main + three annotated release tags | Original Slack literal: 0; Slack pattern: 0; unreviewed/configured credential hits: 0 |
| Other credential-like literals | 16 reviewed synthetic matches across reachable blob versions; unchanged fixture values |
| Research preservation | Both database snapshots unchanged; all 121 artifact files verified |

The Git-object audit reads every reachable blob, commit and annotated tag for the
four explicit publication refs. It excludes private Codex snapshot refs, reflogs,
recovery bundles and unreachable original objects, which are never pushed.
The mapped historical snapshot had 13 such fixture matches; the final tip's
AST-identical formatted checkpoint blob repeats three of them, for 16 total
matches across distinct reachable blob versions. None is a Slack-pattern match.
Original commit/tag metadata comparison validates parent mapping and exact
author/committer/message/tagger/description preservation, except the two explicitly
removed invalid signatures. The final publication follow-up commit is audited
again before push.

Affected-suite command (WSL native Python, from the existing repository):

```bash
/home/sonusunny/.local/share/agsci-mission1-venv/bin/python -m pytest tests/checkpoints tests/runtime/test_bounded_process.py tests/task_drafting/test_task_gate.py tests/task_drafting/test_repair_context.py tests/revision/test_pipeline_revision.py -q --tb=short
```

The full native suite uses the established offline selection documented in the
Phase 2 readiness report. No genuine experiment/provider execution is included.

- Full affected checkpoint and redaction suites passed after canary replacement:
  194 tests, including the complete post-rewrite rerun.
- Full native platform/CLI/Inspector and frontend checks use offline providers;
  real Docker research cases remain excluded. No historical budget is used.
- Ruff lint/format, Linux-target mypy, Git integrity, exact source/metadata/tag
  preservation and a full intended-ref secret audit are required before push.
- The original Slack value and Slack pattern must be absent from every blob,
  commit and annotated tag reachable from main and the three release tags.
- Compare the read-only research/ledger snapshots and all 121 artifact files to
  the retained baseline; no reset, refund or experiment rerun is permitted.
- No established secret scanner is installed in Windows/WSL. The local full-blob
  audit, configured-value comparison and manual fixture review are used; GitHub
  push protection remains the independent mandatory publication gate.
- Windows's previously observed SQLAlchemy Application Control issue is not
  bypassed or repaired by this work; Linux provides the Python regression checks.

Publish only with a normal atomic push after confirming remote main is still an
ancestor and remote tag names are absent or already identical. If GitHub flags
another value, stop to classify it; do not bypass protection. Fetch/verify branch
and annotated/peeled tag hashes afterward. Until that succeeds this document
records verified preparation, not a claim of successful publication.
