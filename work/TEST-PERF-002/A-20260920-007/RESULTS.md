# CI follow-up evidence

Implementation `50be82d05e087228293a9bf96b797bcf0f3ff844`; accepted base `171d4654f88e926f239cdf25bc8168109b81f391`.

The raw acquisition report below describes its original pre-commit state; source hashes bind it to this implementation. Hosted CI and human acceptance are separate.

# EARLY-PROOF implementation handoff

Owner Chengyue-Lu; Task TEST-PERF-002; Skills []. Branch `fix/ci-runner-preflight`.
Final commit **`50be82d05e087228293a9bf96b797bcf0f3ff844`**, direct parent/accepted develop **`171d4654f88e926f239cdf25bc8168109b81f391`**.
Only four authorized files changed. No push, PR, Trace archive or production reduction was performed.

## Behavior and scope

The runner now rejects unsupported ordered coverage producers before B collection, rejects native full-B loader errors/zero cases before fixture execution, and rejects nested repository-C loader errors/zero cases at the original deferred boundary. Invalid loaders retain the original module/ImportError traceback; an empty suite reports `no tests collected`. Explicit B=none remains valid. Normal full/focused/impact work on both supported Pythons remains covered, while the existing ordered producer remains 3.11-only. B's original hierarchy, fixtures and order, delayed C import, receipt projection and all quality policies are unchanged.

Root explicitly extended write scope to the two real worker regressions in test_ci_plan.py: `test_real_workers_preserve_order_and_project_exact_git_plan_evidence` and `test_real_ordered_worker_preserves_class_and_module_fixture_failures`. These retain actual 3.11 order/failure behavior and actual 3.13 ordinary behavior, while asserting 3.13 producer rejection without a raw receipt or sentinel execution. Six new runner scenarios use real disposable modules/loaders and fixture events; their plan/version patches isolate unit entry points, supplemented by those exact-Git subprocess workers.

## Verification phases (do not collapse their hashes)

| Run | Cases | Runner wall seconds | Process wall seconds |
| --- | ---: | ---: | ---: |
| 311 | 96 PASS | 267.489633 | 267.623937 |
| 313 | 96 PASS | 254.018893 | 254.144851 |
| 311-final | 23 PASS | 0.396261 | 0.521418 |
| 313-final | 23 PASS | 0.340545 | 0.450532 |

The first two runs were the complete **23 runner + 73 PlannerTests** combination on the original pending PR92 snapshot `4119f8b2d8e1e64a0afead138d13061e2d89e996`. Source hashes at that phase:

```json
{
  "tests/run_unittest_suite.py": "dae50d536f21499cdaba90b8a1a9a818b6882f909b641e0df03c9f69de585e7a",
  "tests/test_test_runner.py": "f1f01e820076d464f597d40498d5bfbf254e728ba9d696ea331877b3928e0408",
  "tests/test_ci_plan.py": "65b1dbfc795f406ae73626a5fc9bb6fa10a823eb0305289e624670a983ad626e"
}
```

After both complete runs passed, root authorized the review's diagnostic improvement: the two new loader exceptions now append original loader.errors, or an explicit empty message. Existing regression fixtures were strengthened to check the precise ImportError/module and to ensure a nonempty impact suite cannot mask an empty repository suite. The producer-version fixture also declares valid coverage selectors so its removed-guard control reaches the existing late receipt enforcement instead of an unrelated missing field.

Only the 23 runner cases were rerun on both Pythons after that final improvement, as directed. test_ci_plan.py remained byte-identical to the full 96-case runs. The final runner/test source hashes match both final receipts; final source follows below. The old full-run producer scripts, raw logs/receipts/preflight JSON and original tested-source snapshot are retained untouched. We do not describe the earlier full 96 runs as testing the last error-message format.

Three final isolated controls remove exactly one new guard each. Each runs the same six real-module regressions, producing two expected assertion failures. The full-empty control reproduces the old empty-B acceptance; the mixed impact+repository control proves nonempty impact cannot substitute for empty required repository-C. The producer control reaches the old late receipt mismatch after executing behavior. Original earlier mutant observations are also retained, including their less precise fixture failure, and are not substituted for these final controls.

## Independent review and rebase

`INDEPENDENT_REVIEW.md` found no material blocker and recommended retained loader diagnostics. Root arranged a separate final recheck; its report binds the last code and controls. Earlier review files are preserved. The final documentation changes only explain validation phases and independent accepted-base integration.

Initial local commit `b0a80c181519fc85f56ad8a76b5b80b6d540a83d` was rebased with the authorized `git rebase --onto 171d4654f88e926f239cdf25bc8168109b81f391 4119f8b2d8e1e64a0afead138d13061e2d89e996 fix/ci-runner-preflight`, yielding `fef9c35bd54f0c8f7e5a4595664c6c28f26d50d5`; a documentation-only amend yielded final HEAD. There were no conflicts. Fourteen relevant production/test/policy/selector/witness inputs are byte-identical between accepted develop and the initial PR snapshot, as recorded in final-binding.json. Final source/test bytes remain identical to their final focused runs. Full discovery membership differs because PR92 adds three diagnostic modules/tests; this assessment does not claim a final-head full-suite run.

`final_plan.py` recomputes and verifies the exact final-HEAD plan, then loads immutable accepted-base witness bytes and evaluates candidate Git objects without importing candidate code. Plan `33f5fdac52bc0579512b1b5c3d2042cae50029299b9e8c8a89c414aaf70977d4` requires behavioral **full**, coverage **impact+repository**, and both smokes; blocked_reasons is empty. The independent local witness is **PASS**. These are plan/selection checks, not full-suite, coverage, smoke, hosted authentication or merge acceptance. The workstream note has zero Markdown links; `git diff --check` passed.

## Final source pins

| Repository-relative path | SHA256 |
| --- | --- |
| `tests/run_unittest_suite.py` | `36bf86a6325e5465dc624356455e5376702ac6475b515572c405e7a487a607f9` |
| `tests/test_test_runner.py` | `2f7db94d1e790d0169347fe847d92e136cb712034cf776bd4c9ef630ee6a8dfd` |
| `tests/test_ci_plan.py` | `65b1dbfc795f406ae73626a5fc9bb6fa10a823eb0305289e624670a983ad626e` |
| `docs/workstreams/chengyue-lu/TEST-PERF-002/EARLY_PROOF.md` | `73acb453c2b4bdc540d93b45d9688609150fe2a28df9ecbfbd6eed67b5f12739` |

## Raw retention and next owner action

Archive the top-level producer scripts, `*-preflight.json`, `*-receipt.json`, `*-process.json`, all `.log` files, `tested-source-pins.json`, original/final source snapshots, mutant results, original/final mutant source and result.log, final plan/binding/witness, accepted witness source, both review reports and hash files, this report, validation.json and sha256.json. The mutation fixture roots contain only small source copies and logs required to replay the controls; they are not Git clones.

No temporary Git clone or venv exists under this scratch output. Exclude any `__pycache__` and `.pyc` if later created. The persistent `ci-runner-preflight` worktree and shared read-only venvs are not archive inputs; reference the commit and recorded interpreter paths. Native temporary test repositories were removed by their own fixture lifecycle.

Root owns Task Attempt A-20260920-007, push and Draft PR. CI still must execute the exact final target's required plan, complete coverage and smokes, and obtain review. This is early invalid-input rejection; no hosted duration reduction or passing-suite speedup is claimed.
