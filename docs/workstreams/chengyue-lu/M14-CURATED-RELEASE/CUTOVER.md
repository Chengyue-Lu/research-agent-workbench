# M14-005 governance activation and main hard-gate cutover

Owner: 路诚钺 (`Chengyue-Lu`). R2 review is cross-owner; authority is Issue #57,
ADR-0021 and the [named preparation decision](FIRST_RELEASE_DECISION.md).
This slice implements source-owned live PR governance and proposes active curated
topology. It does not apply GitHub protection changes or authorize a release merge/tag.

## Verified input and implementation

PR #117 was independently approved at `cc0eb0e`, normally squash-merged to
`develop@331809fc7d8fc0a72bb9bc72f59363495e2917c8`. Its actual protected
[push CI 36806326706](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36806326706)
and clean exact-source live attestation passed. Rebuilt Draft
[PR #116](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116) candidate
`ef29d7e6ac49fcab3ddd0bf75487517dcc85d6bf` has 297 files, parent
`b1d5a5a5850e0e7541e4c460f15384cd45357ab2`, policy 1.4.0 and manifest SHA-256
`dd4071266db6d322b2f98fd1d033461ae3765864b41365a65cfdb1be8d181600`.
[Hosted run 36810996919](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36810996919)
passed both Python versions. Independent run/job/check/App, artifact digest/size,
receipt identity and merge-ref workflow/checker blob checks passed. Four rulesets
and both effective rule views remained unchanged. Governance with fresh expectations
had only the dormant error; missing expectations failed closed. These are cutover
review inputs, not final release authority.

The proposed source policy activates strict curated topology and rejects direct
develop-to-main in the same policy/code change. `release_install.py` requires the
live PR number and calls `release_governance.py` after its fresh in-process preflight,
before public checks/builds. The helper authenticates PR/ref/repository identity,
derives the external governance facts from live source CI and independent pins,
executes full R2 governance using source-owned Task/workstream evidence, and reobserves
PR inputs after install. Body `edited` triggers both jobs; no job-level skip exists.
Append-only policy 1.5.0 adds the helper, retaining every old policy object.
Saved JSON cannot enter this in-process workflow path.

## Order after independent R2 acceptance

1. Normally integrate this develop PR with exact-head checks/review. Observe its
   actual protected source CI and clean-source live attestation. Rebuild #116 from
   that accepted source with policy 1.5.0/current main, update independent pins and
   verify source-owned public/install/governance and actual dual-Python hosted jobs.
   Old `ef29d7e`/1.4.0 evidence does not cover the new source.
2. Independently audit candidate manifest/tree/parent, PR merge-ref workflow/checker
   blobs, actual hosted run/check/App identities and artifact digests. Obtain R2
   readiness/cutover acceptance against exact candidate/source/parent. Keep #116
   Draft while these review inputs are incomplete.
3. From a clean accepted source run read-only `release_ruleset_cutover.py` with
   source/current-main/run and the four IDs below. Retain full raw ruleset and
   effective-rule readbacks. The payload replaces only main hard contexts with
   `release preflight (3.11)` and `release preflight (3.13)`, both App 15368. Preserve
   no hard bypass, strict, merge method, Code Owner/stale/last-push review,
   conversation resolution and force/delete guards.
4. Immediately before writing, independently regenerate the plan/readbacks and
   require exact accepted prestate/payload hashes, source/main/candidate/pins and
   unchanged live CI attempt/PR inputs. A named maintainer authorizes this one
   update. Apply `cutover.json` via **one PUT to existing main hard ruleset**; do
   not delete/disable a layer or split the required-context replacement.
5. Re-read all four full rulesets, both effective-rule views and branch flags.
   Main hard equals the reviewed after-payload; other layers equal their before
   state. Verify App/context identities and current candidate checks. Independently
   replay direct develop-to-main: active policy rejects it, and both required
   release jobs execute their head guard and fail instead of skipping.
6. Failed/ambiguous writes or drift stop release work. Reconcile actual raw state
   before retrying. Restore the accepted before-payload in one update only with a
   named rollback decision, then re-read full/effective state. No automatic retry,
   reduced gate or merge follows an ambiguous result.
7. Obtain separate final exact-candidate R2 review and named release merge approval.
   Merge commit, tag/artifact/hash and Task completion follow the
   [release rules](../../../DEVELOP_TO_MAIN_RELEASE.md).

| Branch | Hard ruleset | Review ruleset | Preserved method |
|---|---|---|---|
| develop | 23305447 | 23192001 | squash |
| main | 23305460 | 23192054 | merge |

The preparer remains read-only (`applied=false`). Source policy activation before
remote cutover leaves main's old required checks intact, so generated release is
blocked. Required release jobs reject direct develop before checkout when the
swap occurs. First-main workflow green cannot authenticate itself: independent
source/blob/run verification and the existing main review layer remain mandatory.
