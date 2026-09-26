# M5-007 H4b rebase after CI integration

Date: 2026-09-26. Owner: 路诚钺 (`Chengyue-Lu`). Execution interface reviewer: 黄毅 (`let778750-cpu`). Risk: R2. Required Skills: []; no delegation.

The user requested another latest-base rebase of Ready PR #96. Intake head was `deffc2e73b763bb97da5f5567e4606e76293faa1`, based on `eb49093d6d89515c3e66bec29ee85e7a95bb9ce7`. After `git fetch origin --prune`, the accepted base is `develop@5bf2227ca9b4d2f63f452e579185e7838028de78`, including PR #99 and #100. The tracked tree was clean apart from the local memory policy configuration, which was preserved by autostash and excluded from the PR.

`git -c rebase.autoStash=true rebase origin/develop` replayed all three H4b commits without conflicts: `58d5e57`, `13dbcd8`, `5d4f07c`. Range-diff is identical for the two documentation commits; the implementation's only patch-context difference is the placement of its negative surface after the new mainline CI surface. No implementation behavior was changed.

[Equivalence results](equivalence.json) and the retained [verification script text](equivalence-check.txt) show 52 original H4b paths unchanged byte-for-byte, excluding the merged coverage policy, and 31 newly accepted baseline paths unchanged byte-for-byte, also excluding that policy. Parsed policy equality after removing only the H4b version/suite/critical/surface additions proves the complete new baseline policy is retained: 44 existing negative surfaces and 62 critical modules remain; the candidate has 45 surfaces and 63 critical modules. Thresholds, exclusions and existing suite/negative definitions are unchanged.

Local validation on the rebased implementation:

- [H4b focused tests](focused.log): 13 PASS, including fresh four-arm evidence and independent reveal replay.
- [CI/document/Schema/coverage-policy contracts](contracts.log): 147 PASS across `test_ci_plan`, `test_ci_contract_shadow`, `test_ci_consumer_contracts`, `test_documentation`, `test_schemas` and `test_coverage_policy`.
- Documentation link checks after adding this archive: 10 PASS.
- Repository validation: 186 checked, 0 errors, 0 warnings; pip dependency check PASS.
- Working-tree and staged whitespace checks: PASS.

Read scope was limited to project guidance/progress, PR #96, its changed surfaces and the two new baseline commits. Write scope is this evidence addendum and PR/Issue/progress metadata. The [first rebase record](../M5-007-H4B-REBASE-001/README.md) and [original attempt](../M5-007-H4B-001/README.md) retain their historical evidence; their coverage/package/Trace results do not become new exact-head results. This addendum retains scoped observable checks and does not claim a complete Agent Trace; the original delayed-capture warning remains explicit.

New exact-head hosted CI and cross-owner approval remain required before merge. H4b stays Ready for review; M5-007 stays IN_PROGRESS, with H4c/H5 and all Human/live/release gates unchanged. No merge is authorized by this rebase request.
