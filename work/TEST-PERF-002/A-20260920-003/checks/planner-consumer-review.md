# PlannerTests invocation-boundary audit

Owner: Chengyue-Lu. Profile: CI consumer independence reviewer; skills=[]. Base: 09c6cb1c82680233c369014e0831874b6702d3b7. Scope: existing regular workstream Markdown modifications only, with unchanged pinned source/config/fixture inputs. This is a diagnostic proposal, not an accepted exclusion witness.

## Conclusion

All 73 test methods in PlannerTests operate on a shared generated temporary seed plus a fresh per-test clone, or on literal/in-memory inputs. They also consume 19 exact real-checkout source/config/fixture files listed and SHA256-pinned in proposal.json. None of the inspected invocation paths reads the current checkout's workstream Markdown bytes. README.md, docs/TASKS.md, docs/ARCHITECTURE.md and workstream paths referenced by these tests are synthetic files written into their temporary repositories, rather than copied real documents.

It is justified to propose the 73 IDs as behaviorally unrelated to a modified existing workstream Markdown instance, under the explicit unchanged-input and environment assumptions. This does not prove an environment/lifecycle-independent skip: prior imported module state, Git/Python configuration, test discovery and candidate execution still require their own evidence. Do not treat the pins as complete production safe-exclusion authority.

## Exact source and input boundary

- tests/test_ci_plan.py:19-21 establishes the actual checkout ROOT and imports plan_ci.
- Lines 39-68 create a temporary seed. Actual reads are planner.POLICY, all eight TRUST_FILES and pyproject.toml. Test stubs, provider leaves, consumer.py and the four Markdown examples are generated from literals. Lines 74-82 clone only that seed for each test with --no-hardlinks.
- Lines 90-93 bind make_plan to self.repo and synthetic base/head/target. Other event/Git operations likewise use self.repo. All fixture mutations stay inside those clones.
- Lines 109-137 and 1388-1405 read pr68-paths.json and pr65.json from the real checkout; their document/content changes are then materialized in the fixture, not followed as paths into the real checkout.
- Lines 778-815 are the important wider boundary: two tests copy the actual claim_trace/release_projection implementation, their proof test and one proof helper into the fixture. These six files and tests/__init__.py must be pinned even though no workstream Markdown is consumed. The copied test source is inspected by the fixture planner; the real business test suite is not executed by these two helpers.
- plan_ci.py imports ci_dependencies; risk_at dynamically imports the actual check_pr_governance.py and its import-time governance-policy.json. The invoked parse_metadata / infer_minimum_risk / resolve_effective_risk path processes fixture changed-path strings and policy data. It does not invoke governance's separate workstream/TASKS Git readers.
- test_ci_plan.py:486-515,1150-1215 imports the real tests.run_unittest_suite and patches its ROOT/TESTS/SOURCE to the fixture, protecting/restoring module and path state where those runner APIs load synthetic tests. Lines 1217-1306 execute the runner copied into the fixture in child Python processes. The runner and tests package initializer are real pinned inputs.

The 19 exact pins, also used as input_patterns, are:

1. .github/governance-policy.json
2. .github/scripts/check_pr_governance.py
3. .github/scripts/ci_checks.py
4. .github/scripts/ci_dependencies.py
5. .github/scripts/plan_ci.py
6. pyproject.toml
7. src/research_workbench/artifacts/claim_trace.py
8. src/research_workbench/capability/release_projection.py
9. tests/__init__.py
10. tests/ci_impact_policy.yaml
11. tests/coverage_policy.yaml
12. tests/fixtures/ci/pr65.json
13. tests/fixtures/ci/pr68-paths.json
14. tests/run_unittest_suite.py
15. tests/test_artifacts_promotion.py
16. tests/test_ci_plan.py
17. tests/test_claim_trace.py
18. tests/test_skill_evaluation.py
19. tests/test_skill_release_projection.py

These are the observed real repository byte reads/import roots for this invocation family, not a claim that only these inputs can affect execution under arbitrary external state. Changing any executable/helper/config/fixture input also leaves the current Markdown pilot and therefore retains the accepted tests independently of the pin check.

## Environment and alternative paths still requiring closure

- Bind Python interpreter/minor version, PyYAML, standard library, dependency set, Git executable/version, filesystem case/newline/symlink behavior and temporary-directory behavior. Some runner assertions intentionally distinguish Python 3.11 from 3.13.
- Git global/system/template/hook configuration, GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE overrides, user config and executable lookup are external inputs. They cannot be inferred from the 19 repository pins.
- PYTHONPATH, sitecustomize/.pth behavior, preloaded plan_ci/tests/runner module origins and earlier test side effects may change imports. The fixed entrypoint must resolve those modules to this exact checkout; a normal same-process full suite is not equivalent to an arbitrarily preloaded interpreter.
- GitHub event/output/summary environment is partially patched by individual tests; the fixture subprocesses inherit remaining environment. Keep the surrounding invocation stable and record how it is isolated.
- Fresh class seed and per-test cleanup/order remain real costs and lifecycle boundaries. Removing the whole PlannerTests family changes setup/teardown work; do not infer exact wall-time reduction by summing only case durations.
- A future source/helper/initializer edit that starts reading a real workstream file would invalidate these pins. New test methods change test_ci_plan.py and the exact ID inventory. Changes to directory membership, executable mode, resource files or alternate invocation topology stay outside the initial existing-Markdown pilot.
- The declaration's assumptions are deliberately visible and execution_authority remains false. Its empty consumer.unknowns field means no additional repository-input ambiguity was found for this narrow inspected rule; it does not clear the comparator's global input/environment/exclusion-witness blockers.

## Real counterexample performed

A disposable sparse clone under this assessment directory was detached at the exact base; no official branch was changed. Baseline ran the existing test tests.test_ci_plan.PlannerTests.test_docs_fast_plan_is_explainable_and_replayable successfully. Then the actual cloned planner source assignment was changed from the ordinary conditional behavioral selection to behavioral = 'full'. No mocks were introduced.

The same existing test failed with AssertionError: 'fast' != 'full' at tests/test_ci_plan.py:98. This establishes a concrete relevant executable mutation that these proposed-to-skip cases must retain when planner input changes. It does not prove all 73 cases necessary for that one mutation or replace the unrelated real-doc control being executed by the main task.

Artifacts:

- proposal.json: exact 73 canonical IDs, 19 base pins, explicit invocation and assumptions.
- inventory.json: independent AST enumeration and exact base/pin inventory.
- counterexample.json: baseline returncode 0, mutant returncode 1, mutation/source hash, interpreter and Git version.
- baseline.stderr.txt and mutant.stderr.txt: original subprocess results.
- audit_and_probe.py: reproduction script. The clone uses shared immutable objects with the source repository; mutation remains local and uncommitted in the disposable clone.

Observed single-test wall times were approximately 2.328 s baseline and 1.875 s failing mutant. They are execution records, not a speed comparison. The main task's complete accepted 13-module run is the appropriate source for the 73-case cost and unrelated document precision observation.

## Disposition

Provide this proposal to the diagnostic comparator for the narrow existing-workstream-Markdown control. Keep accepted CI execution intact. Input/environment/lifecycle closure, independent exclusion witness, candidate replay and paired performance remain unclosed; no activation or release authority is granted.
