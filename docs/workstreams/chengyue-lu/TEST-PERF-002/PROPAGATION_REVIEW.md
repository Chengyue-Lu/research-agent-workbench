# Per-input propagation review

TEST-PERF-002 / Issue #87; owner Chengyue-Lu; R2; 2026-09-24.

Shadow schema 4 extends the existing [contract report](CONSUMER_CONTRACTS_V1.md).
The existing input facts, accepted-plan verification and immutable merge-base/head graph
remain its inputs. The execution planner, workers, independent witness and aggregate
do not consume the new fields.

## The missing distinction

An accepted dependency selection retains one deterministic path for each test module.
Two changed archive inputs can independently reach the same resource readers, while
only the first input appears in that retained path. A mixed change can also require
FULL directly through unclassified input obligations and retain opaque execution
through a different source seed. A single displayed path cannot prove an input is
unrelated or identify an exclusive cause of execution cost.

`propagation_review` now keeps three separate observations for every changed input:

- The exact accepted unclassified reasons for behavioral, coverage and smoke obligations.
- Whether the input is a root in the accepted graph and which module witnesses retained it.
- Its isolated ordinary merge-base/head consumer closure, without reviewed overrides, including
  module membership and resource/opaque path witnesses. Non-seeds, including policy
  metadata and unchanged executable semantics, have no isolated closure.

The isolated closures overlap and can exceed the accepted reviewed boundary. Their
module counts must not be summed or interpreted as actual cases, excluded work,
execution minima or speedup. Each isolated module still has one path witness; kinds
are neither exhaustive alternative edges nor exclusive causal contributions. Raw
graph errors remain visible. The accepted plan is not modified.

The original `review_reason` remains a display label for compatibility; new
`fallback_edge_kinds` retains simultaneous resource and opaque kinds on that path.
The report continues to state `execution_authority=false` and `activation.eligible=false`.
No consumer proposal, classification, fingerprint or report can grant an exclusion.
Unclassified reasons are compared with the recomputed minimum in every obligation;
re-signing an altered reason list cannot forge this attribution. Additional non-classification
reasons for conservative escalation remain legal. The explicit graph binding retains
merge-base consumers even when both current branches independently removed a reader.

## Git object facts

Each changed version includes its mode, object type and object ID. Blob bytes carry
a SHA256; gitlinks retain commit identity with `content_available=false` and a null
content hash. Commit text is never substituted for unavailable file content. Existing
mode/type and executable classification remains conservative.

## Acceptance boundary

Regressions cover overlapping archive roots, mixed executable/archive causes, policy
metadata absent from graph seeds, non-blob Git input, immutable plans, invalid plans
and real failing consumers. Python3.11 and3.13 each passed35 related cases; local
coverage for the changed script is151/151 lines and44/44 branches. Coverage-policy
validation passed21 cases. The initial unconfigured3.13 interpreter failed import
before executing tests; its log remains distinct from the configured successful run.

New local reports retain the original PR90 official plan and separately recompute
PR84/65 from their immutable Git pairs. Accepted obligations, smoke and activation
fields are identical between the previous and new report producers. These are
diagnostic replays, not fresh behavioral CI or safe-exclusion acceptance.

| Corpus | Changed inputs | Inputs with direct unknown obligations | Resource witnesses | Opaque witnesses |
|---|---:|---:|---:|---:|
| PR90 | 73 | 51 | 52 | 4 |
| PR84 | 24 | 9 | 9 | 0 |
| PR65 | 20 | 0 | 0 | 0 |

Columns count inputs with observed mechanisms and overlap; they are not runtime cases.
One local fresh-process before/after diagnostic observation took13.656/14.469s,
9.406/9.156s and3.016/3.016s respectively. The additional analysis has a measured cost;
these single observations do not establish a performance distribution or CI speedup.

This slice improves attribution before proposing a stable input boundary. It does not
close input membership, environments, helpers or shared lifecycles; those still need
the [C01–C20 controls](CI_REPLAN_ACCEPTANCE.md), independent witness acceptance and
actual B/C/coverage/smoke paired evidence before production reduction.

Existing reports keep their original schema and producer identity. Schema 4 reports
are new observations; replaying historical Git facts does not renew an old CI receipt.
