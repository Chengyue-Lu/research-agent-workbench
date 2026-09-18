# M5-007 H3 integration after PR86

Task: M5-007; owner: Chengyue-Lu; interface reviewer: let778750-cpu; risk: R2; delegation: none.
On 2026-09-17 the user authorized rebasing PR89 onto the latest develop after PR86 and other PRs merged,
then marking PR89 ready for review. The authorized scope is integration and PR readiness.

## Inputs and integration

- Original H3 head: `87f13fb87fd51cb4423e78f817e40b1248c6b6cd`.
- Original parent boundary: `b53a391ece3a4be7207c00c636dc9e1570e71473`.
- Accepted develop / PR86 merge: `51dc3ab477f21f18ac3829bf553b5b779d49a4fe`.
- Rebased H3 implementation: `560bf2d`; only the H3 commit was replayed.
- Conflicts in STATUS and WORKLOG were resolved by retaining the accepted M5-008 Gate definition and
  both historical logs, while describing accepted H1/H2 and H3 awaiting review.

The source, schemas, H3 fixtures/tests, Trace regression and original H3 Attempt archive compare
byte-identical to the original head. TASKS matches the accepted develop snapshot. M5-007 remains
IN_PROGRESS; H4/H5 and the M5-008 live engineering Gate retain their existing scope and dependencies.

The accepted CI consumer record pins `tests/test_schemas.py`. H3 adds its execution record kind to that
test, so the proposed pin changes from
`63fed5380ff7fe925a0edfee15d005a3c51637088f5ae918933dddf17bbd41ff` to
`6b0d006c06debc32b94c470375bec696977a14cf47dac3161c2fa5ed65dc820b`.
All other pins, record identities, assertions, thresholds and selection obligations remain unchanged.
The accepted-base record remains the shadow review authority; the candidate cannot clear its own drift.

## Verification and evidence boundary

The [original H3 CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35136554641)
and governance completed successfully on the original head. New exact-head focused, documentation,
Schema, consumer-contract, repository and package results are recorded in the
[PR89 verification section](https://github.com/Chengyue-Lu/research-agent-workbench/pull/89), alongside
the new hosted full/coverage/governance runs. Original evidence is historical and remains frozen.

This is a partial integration record backed by immutable Git and GitHub references. Local tool capture
is incomplete; absent messages and original event timestamps are not reconstructed. No secrets or hidden
reasoning are retained. CI proves the checked implementation properties; R2 acceptance remains with
the named owners.
