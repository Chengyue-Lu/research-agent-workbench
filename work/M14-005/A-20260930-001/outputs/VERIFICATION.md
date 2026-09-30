# M14-005 cutover preparation verification

- Integration base: `develop@318904977c0492322e1bffe3e28532bc712e321b`; PR #108 merged
  at 2026-09-30T03:02:24Z with reviewed-head tree `396df62cf658ad2fd3ab9b1bb282df47bfcd369f`.
- Protected develop push: [CI run 36662594652](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36662594652)
  completed successfully, including governance, both Python tests, coverage-quality,
  repository validation and both package routes. Clean exact-source live `attest` PASS;
  caller-owned receipt is retained under `tool-events/source-attestation.json`.
- Current main parent observed: `b1d5a5a5850e0e7541e4c460f15384cd45357ab2`.
  All four active hard/review rulesets and both effective-rule views matched the
  source-owned read-only preparer. The proposed main-hard cutover payload SHA-256 was
  `230a4c5ab7e5b534ca3ad098386b5e260b449bbb9d6d899588c7abe2ed118237`.
  The payload was not applied; these observations are not a release freeze.
- Targeted release/cutover, documentation and coverage-policy tests: 45/45 PASS on
  Python 3.13. New cutover script isolated coverage: 100/101 statements and 15/16
  branches (98% combined report), above the critical 95/90 minimum.
- A local all-module coverage-quality run was interrupted after prolonged Windows
  execution without a final result; it is not acceptance evidence. Hosted exact-head
  full and coverage-quality CI remain required for this PR.
- Negative cases include unexpected bypass/scope/check App/review changes, missing
  source CI, effective-rule mismatch, branch drift, source-CI rerun and output overwrite.
- Remaining acceptance: exact-head full/coverage/governance/repository/package CI and
  independent R2 review of this PR. Real first-main hosted checks and ruleset mutation
  have not been attempted.
