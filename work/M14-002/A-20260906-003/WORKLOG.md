# M14-002 append-only deletion review fix

- Baseline: `3331a0666ebd4c0220d5c8bdfff7351c3e4fbb65`; owner: Chengyue-Lu; H0 main agent, no delegation or Skill binding.
- Review basis: `review.md`, transcribed from the user-provided screenshot.
- Each commit's actual policy retains the union of all parent version identities. Immutable blobs are cached; retention is checked at every DAG commit, including merges omitted by path-limited history.
- Regressions cover `[1,2] -> [2] -> [1,2]`, a later unrelated commit, and a merge matching one parent that drops the other parent's version before restoration. Both project and check reject these histories.
- Existing non-prefix merge-union and new-maximum append fixtures remain valid.
- Before-fix evidence: two new methods, three failures and zero errors. After-fix release tests: 37/37; governance/docs: 122/122; repository: 183/0/0; checker line 98.99% / branch 96.97%.
- Exact tested file hashes are in `checks/verification.json`. Final-head hosted CI and cross-owner review remain integration gates.
- Read scope: M14 release implementation, tests, governance/docs and Trace support. The user's screenshot supplies the additional review input.
- Native capture gaps are explicit. This archive is safe-paused before publication; Git/PR provide subsequent receipts.
- Next action: commit and push this scoped fix to PR #60, update review evidence and retain the cross-owner review request.
- Boundaries: dormant release topology; M14-003/004 stay PARKED and M14-005 BLOCKED; no real release branch, tag or merge.
