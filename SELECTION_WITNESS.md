# Independent selection witness execution root

This audit branch carries a read-only execution entry for TEST-PERF-002 / PR #66.
Its source is reviewed alongside the implementation PR, but its workflow executes
from a separately chosen immutable commit. It is not a release or integration branch.

The reviewer supplies the witness commit and candidate CI run independently of the
candidate plan. Dispatch the existing `ci.yml` workflow using this audit branch as
the API ref and the independently pinned commit as the `witness_sha` input,
then check the returned run's `head_sha` against the chosen commit using GitHub's API.
Only a receipt from that run, bound to the current PR base/head and plan, is evidence.
Candidate workflow results, candidate-proposed pins and candidate copies of this
script cannot replace this invocation. The workflow checks out its own SHA only.
It does not install the candidate package, restore candidate caches, import candidate
modules, extract the plan archive or use a write token. Candidate commits are fetched
as bare Git data and fixed authority blobs are parsed without execution.

The witness establishes the selection-authority behavioral floor. It does not certify
test execution, coverage or smoke success. Those remain separate exact-head checks.
Ordinary R2 changes do not acquire a FULL floor merely because of risk.

This dispatch is an explicit cross-owner review step. Existing repository required
check settings do not automatically enforce it. Cross-owner acceptance of the fixed
execution root and receipt is required before merging PR #66. Changing automated
trust-root deployment or branch protection remains a separate maintainer action.
