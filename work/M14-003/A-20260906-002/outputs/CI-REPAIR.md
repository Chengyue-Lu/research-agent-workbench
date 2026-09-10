# M14-003 CI dependency repair

- Owner: Chengyue-Lu; H0; no delegation or Skill binding.
- User authorized diagnosis and repair within PR #60. Baseline `cee51b35380d698ae8e8e4ae254fa649a449787d`; implementation `54a3a1cf4d6a96fbfccba6c7198cafafa525d05e`.
- Python 3.13 CI failed in `test_build_regeneration_is_identical_and_removes_stale_output`: direct `build_backend` import could not find `setuptools`. Its build-system declaration only populated the isolated build environment. The dependent aggregate check also failed.
- A fresh Python 3.13 environment reproduced the same error after the unchanged CI installation command. The test extra now explicitly includes `setuptools>=69`; core dependencies and Runtime/release behavior are unchanged.
- Corrected fresh Python 3.11.16 and 3.13.15 environments each passed all 12 Runtime resource tests. Governance/documentation/Schema/coverage-policy focused checks passed 125/125. Installed package metadata scopes setuptools to the test extra.
- Baseline hosted 3.11 compatibility, coverage, and both package smokes passed. Final-head hosted full CI remains an independent gate; those baseline results are not relabeled as final-head evidence.
- Evidence: `checks/verification.json` and selected redacted test logs. Native capture gaps are explicit; Git and PR #60 retain subsequent publication receipts. Earlier frozen archives are preserved.
- Next: publish this repair in PR #60 and retain cross-owner review. Release gates remain dormant; no merge or release activation.
