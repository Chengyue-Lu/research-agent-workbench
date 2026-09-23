# Reviewed CI authority anchor

Owner: Chengyue-Lu; risk R2; [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).

The accepted impact policy stores diagnostic consumer records beside its production
selection contract. PR #86 and #89 updated those records while preserving the
existing consumer fingerprint. Selecting the latest commit touching the entire
policy file therefore selected a different inventory, failed the fingerprint check,
and disabled all otherwise eligible reviewed leaf boundaries.

The planner now finds the matching anchor within a continuous first-parent policy
history whose production authority remains identical. It validates every policy,
then compares canonical JSON with only `consumer_contracts` removed. Policy identity,
version, surfaces, groups, evidence and fingerprint all remain part of the comparison.
The diagnostic records must still validate and cannot claim execution authority.

Traversal stops at the first changed authority, malformed policy, duplicate key,
missing/non-regular policy, mode change, unavailable object or exhausted 64-revision
bound. An older matching digest behind such a barrier is not accepted. A matching
side-branch ancestor is not substituted for first-parent history. Candidate metadata
does not choose or refresh the base-side anchor.

On the current accepted baseline, `171d465 → 51dc3ab → 348d625` has the same authority
projection, and `348d6257ddd28637c9d06abe177fc685ac4368b6` matches its own fingerprint.
The existing anchor/base/head equality checks still exclude new or changed consumers
from the reviewed set. Existing imports, function-body, proof/helper/fixture drift,
base/head edge union, coverage and smoke guards remain applicable.

## Evidence and limitations

Real Git regressions cover diagnostic metadata plus new/changed opaque consumers,
authority changes followed by restoration, malformed and duplicate JSON, attempted
diagnostic authority, deletion/recreation, mode changes, matching side-branch history,
missing history and the traversal bound. The bound regression uses a small configured
limit in a real repository; production retains 64. Existing proof-drift and candidate
self-authorization regressions are also retained.

The source diff remains selection authority. Its own plan requires complete dual
Python behavior and the independent witness; the recovered boundary cannot reduce
that bootstrap. Coverage thresholds, exclusions and production policy are unchanged.

Current-base provider plans recover the anchor but remain broad because newly added
consumers still propagate the change. This repair establishes the correct review
provenance; it does not establish a measured hosted speedup or approve a new consumer
exclusion. The wider work is tracked in the [follow-up inventory](CI_FOLLOWUP_INVENTORY.md).
