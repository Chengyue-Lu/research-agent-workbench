# First candidate and governance correction evidence

- Accepted source: `cebae4b3d9116d750b5573afce77a3e0bfd2b12f`; protected
  [push CI run 36791544994](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36791544994)
  SUCCESS; clean-source live attestation PASS.
- Candidate: `release/v0.1.0@4d7df013277124b1721f3a5d93f2f15d64d3f2e5`,
  parent `b1d5a5a5850e0e7541e4c460f15384cd45357ab2`, tree
  `5eba0a5e3af1026991cd479ef355e319956262be`, 297 paths, manifest SHA-256
  `57cd04184fb17210f504c946a1e46213857870e46343ec3b75e0a77c724d1677`.
- Source-owned double projection, exact candidate/preflight/prospective merge tree,
  public checker and local Python 3.13.15 direct-wheel/sdist-wheel installation PASS.
  Source-owned receipts say `merge_eligible: false`.
- [Draft PR #116](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116)
  first-main [hosted run 36797275971](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36797275971)
  SUCCESS for release preflight (3.11) and (3.13). The workflow and four checker
  script blobs match frozen source and PR merge ref; downloaded job artifacts match
  the API digests and candidate identity. No release authority follows from a
  candidate-supplied workflow.
- All four active rulesets, both effective-rule views and read-only source-owned
  cutover prestate matched. Proposed payload SHA-256
  `230a4c5ab7e5b534ca3ad098386b5e260b449bbb9d6d899588c7abe2ed118237`;
  `applied: false`, `merge_eligible: false`. Fresh readback is required for any cutover.
- Independent current-governance replay added `TASK-READ` and `WORKSTREAM-EVIDENCE`
  because the candidate excludes those documents. The proposed correction reads
  them from prerequisite-validated source. An actual PR #116 replay with valid
  external expectations then reports only `TOPOLOGY-RELEASE-DORMANT`. Missing
  expectations keep explicit release errors and never grant eligibility.
- Local Python 3.11 release/governance focused run: 158/158 PASS before the final
  added empty-source regression; all 97 final governance/branch tests PASS.
  Documentation links: 10/10 PASS. Repository validation: 186/0/0. The new
  Attempt Trace has no BLOCK and retains a capture-gap warning.
- The governance correction's exact-head hosted CI and cross-owner R2 review
  remain required before it is an accepted source. No ruleset, main, tag or final
  release-PR merge action occurred in this attempt.
