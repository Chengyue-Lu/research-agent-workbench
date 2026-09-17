# M5-007 integration after PR85

Task: M5-007; owner: Chengyue-Lu; risk: R2; delegation: none.
Human authorized merging PR85, PR86 and PR88 in order and rebasing these branches.
This integration record does not alter the Task definition or claim complete M5-007 acceptance.

PR85 merged as `348d6257ddd28637c9d06abe177fc685ac4368b6`.
PR86 rebased from `b53a391ece3a4be7207c00c636dc9e1570e71473` to
`18b85aa6dbb8fbcf242af3ecebffe34dbdb87400`; all three patches compared equal in `git range-diff`.
The new base added explicit diagnostic consumer pins for files changed by the already-reviewed Harness work.

[CI 35199914370](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35199914370)
then reported 1 failure among 1,383 Python 3.13 tests: the live consumer-record consistency test found the
old `validation/documents.py` hash. Inspection of all four records also found the `tests/test_schemas.py` pin.
Both files had only added the two Harness record kinds. The remaining old-head coverage work was cancelled
after preserving this diagnostic failure; that cancelled run is not acceptance evidence.

| Pinned file | Accepted-base SHA-256 | Harness SHA-256 |
|---|---|---|
| `src/research_workbench/validation/documents.py` | `16cd9bb7d61820a9582e614daeecb8c2bee969534bb1b8a67795bb9a305361df` | `087e1c72a55bca42667d05d9dae4b9e005a2a3299ad91763c3d3987745d37abb` |
| `tests/test_schemas.py` | `d0fc0c73d4d2bbb05ee38e161e9f7ad40c7880f6ade46ff73828cfe35d834ecc` | `63fed5380ff7fe925a0edfee15d005a3c51637088f5ae918933dddf17bbd41ff` |

The repair proposes these two exact Git-byte pins in `tests/ci_impact_policy.yaml`. Record identities,
inputs/outputs, invariants, unresolved obligations, evidence test IDs and `execution_authority=false`
remain unchanged. The source, test assertions, selector, thresholds and exclusions are unchanged.
Shadow review still uses the accepted base record: candidate revision cannot clear the old pin's head drift
or authorize an exclusion. Existing consumer-contract and shadow negative tests exercise that boundary.

Verification includes the existing consumer-contract, shadow, planner, validation and Schema suites;
the final exact-head results and new hosted full/coverage/package/governance evidence are retained on PR86.
The original H1/H2 archive remains byte-identical. This is a partial integration record: visible source and
CI results have immutable Git/GitHub references, while local command capture is incomplete. No missing
messages, original timestamps, secrets or hidden reasoning are reconstructed.
