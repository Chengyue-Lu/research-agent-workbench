# Revision 13: impact precision intake

Task: TEST-PERF-002; owner: Chengyue-Lu; risk: R2; delegation: false.
Scope: prepare the next repair from [Issue #48's latest request](https://github.com/Chengyue-Lu/research-agent-workbench/issues/48#issuecomment-5573581053).

Accepted base is `bdbac11a0c9a17fa221f8cc8bdd522c1bf4f9087` after merged PR #66.
The clean isolated branch `feature/test-perf-002-impact-precision` was created from that commit.
The [implementation sequence and acceptance matrix](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/IMPACT_PRECISION.md)
separates dependency precision, impact proof selection and executable collection.

- Reproduced raw immutable-head probes for claim trace, release surface and release projection:
  each selects 72/75 test modules at M14 head `205559b25f7f0bd276094a4ac53db28354b7284d`.
- Downloaded the actual CI plan and coverage artifacts for run `34131110394`.
  Both behavioral and coverage lists contain the same 74 test modules.
- Executed coverage IDs in that artifact partition into 978 repository policy members and 61 re-added
  tests. The latter took 937.590517 seconds within the 2655.396489-second coverage suite.
  This measures existing cost, not a new performance improvement.
- Hosted coverage job failed despite 1039 passing test outcomes; aggregate failures are retained.
- No source mutation, test-suite run, contract acceptance or hosted experiment took place in this intake.
  Formal M4/M14 branches retain their heads. The previous conditional 44/1040 result is not current-base acceptance.

The [baseline data](checks/baseline.json) includes selected dependency chains, excluded modules,
opaque consumers, exact refs, job timestamps and hashes for original hosted artifacts.
The [request snapshot](checks/issue48-comment.json) preserves the cited comment body as review input.
[Reproduction notes](checks/REPRODUCE.md) explain how these observations were obtained.

This completed intake is not implementation completion. The next turn starts from the three consumer
inventories, retains fail-closed proof obligations, and follows the frozen acceptance matrix.
Native reads and tool events before archive initialization have an explicit capture gap;
the archive does not claim a complete native event export.
Initial trace validation rejected the `completed` Attempt status because of that gap. Its receipt and the
original event remain preserved; a subsequent status correction records `safe-paused` before publication.
