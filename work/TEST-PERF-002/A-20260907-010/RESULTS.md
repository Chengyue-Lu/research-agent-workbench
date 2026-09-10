# TEST-PERF-002 proposed M14 consumer contract, revision 12

The PR66 implementation at `aa7f0da293baaedada9c3df49e75431f82d556b9` extends the existing base-side consumer-contract path validation to `.github/scripts/*.py`. A real Git regression proves that adding a contract on the candidate side cannot authorize an exclusion; only a later candidate whose base contains that contract can use it. New consumers and changed imports still restore the required closure. The two cross-owner P1 fixes and independent witness regressions remain included.

## Local validation

- Focused planner/checker/dependency/witness tests: **102/102 PASS**, 285.719 seconds.
- Critical line/branch: dependency helper **100/100**, planner **99.7758/98.6842**, checker **99.2308/97.5**, witness **100/100**.
- All five executable subjects changed by the complete PR relative to `develop@b8a38a1` have **100/100 changed statement/outgoing branch** preflight coverage. Required positive/negative IDs pass.
- Documentation and coverage-policy checks: **30/30 PASS** in both the CI worktree and the isolated M14 contract tree. No threshold, exclusion or existing test was removed.

## Proposed M14 base and measured selection

The isolated M14 branch proposes a consumer contract at `8f8b56f64633185c4bfbe30ad7928a935272d702`. It declares the standalone release-surface checker, its complete 38-test module, and the existing six shared impact-policy acceptance methods. Package and repository smoke are not obligations of this specific unchanged-import leaf contract. The release checker retains its critical inventory, whole-file 95/90, changed 100/100 and all mapped positive/negative evidence.

The contract and its review boundary are documented in `docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/CI_IMPACT_CONTRACT.md` on that isolated branch. The policy fingerprint binds the proposed base inventory. **This experiment assumes that contract has been reviewed and accepted as base authority; this record does not accept it on the reviewer's behalf.** The ordinary current PR cannot use its own policy edit to narrow itself.

| Observation | Result |
|---|---|
| Base | `8f8b56f64633185c4bfbe30ad7928a935272d702` |
| Equivalent digest candidate | `ba138d2ece69f1d5fc49328fa6a5cb9b3fcfa915` |
| Selected inventory | **44 / 1040**, 996 excluded (**95.77% fewer tests**) |
| Plan | R2; behavioral focused; coverage impact; package false; repository false |
| Actual impact run | **44/44 PASS**, **141.704 seconds** on local Python 3.11.16 |
| Critical release checker | **98.9933% line / 96.9697% branch** |
| Changed statement/outgoing branch | **100/100** |
| Real impact gate | PASS, repository coverage proved = false |
| Actual constant-zero candidate | `1097a2a15b76ee6ededb1ad416230dc1326f3cb2` |
| Same selected negative run | 44 methods executed; exit 1; three expected assertions fail across the vector/export methods; no runtime errors |

The final coverage run uses the same collection source roots as the workflow, retaining exclusion-set equality. An earlier scripts-only collector passed behavior but failed that equality; it was replaced by the properly configured run, with no policy relaxation.

These are local selected-work and correctness results. There is no matched hosted full-suite timing comparison, and no claim that arbitrary unreviewed modules now receive the same reduction. Without the accepted M14 base contract, the earlier conservative graph still selected almost the whole suite. The broader Markdown/reference precision observation in revision 11 remains distinct.

## Integration and review

The official M4 and M14 PR branches remain unchanged. The proposed contract and independent hash assertions are on `test/m14-ci-acceptance`, ready for cross-owner review and later adoption into the M14 line. Intentional mutants remain local and must not merge.

The final PR66 head after this archive still changes selection authority and therefore needs current dual-Python full behavioral CI, its independent impact/repository coverage obligations, governance and the pinned witness. The witness root remains `1b543393ae71b9032359b739170d66ec0be08772`; any receipt for `1683a50` is historical for this new candidate. Cross-owner acceptance remains required. No merge, release, tag, protection or new M14 milestone was performed.
