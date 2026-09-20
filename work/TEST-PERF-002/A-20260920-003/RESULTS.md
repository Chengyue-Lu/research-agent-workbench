# Complete accepted and candidate consumer observations

TEST-PERF-002 / Issue #87; owner Chengyue-Lu; risk R2; 2026-09-20.
Base `171d4654f88e926f239cdf25bc8168109b81f391`; implementation `9239c2f53ece159fa7ac035e0552491909d78856`; continuation of Draft PR #92.

## Actual local pair

The existing workstream Markdown control is target `9724a4ee36889b327b33ba1ebb066a6e02521404`.
Its actual accepted plan requires 325 cases in 13 modules, C empty, and neither smoke.
The former two Kernel controls are absent from that accepted B and save no execution.
The new proposal excludes only 73 PlannerTests under 19 unchanged source/config/fixture
pins and an explicit docs/workstreams change scope. Those tests generate Markdown
inside temporary Git fixtures; actual document consumers remain selected.

| Same-driver execution | Cases | Runner wall |
| --- | --- | --- |
| Complete accepted plan | 325 PASS | 323.008 s |
| Filtered candidate | 252 PASS | 59.492 s |

Observed difference: 263.516 s (81.58%).
Both runs use the same driver source, environment and exact Git target, with fresh
processes and expected-order receipts. This is one local pair, not a repeated hosted
critical-path result, and does not authorize activation. The initial raw-checkout
failure (322 PASS + 3 missing-generated-resource errors) and the first different-driver
pair (325/252 PASS, 323.833/63.072 s) remain preserved with their original limitations.

## Quality and lifecycle

The paired comparator retains C and smoke requirements, separately evaluates the
existing impact/repository checkers, and binds artifacts to plan/target/run/receipt.
A real subprocess regression covers every source line/branch in both schedules but
fails after a case moves into a restarted class fixture. The failure stays blocking.
Different drivers remain a timing confound; missing/failed/skipped proof stays inconclusive.
Required coverage observations for broad real candidate plans remain future work: this
real docs pair has coverage_scope=none and cannot establish repository coverage.

- Python 3.11 related regression: 51 PASS, 40.326 s; Python 3.13 focused: 10 PASS, 8.494 s.
- ci_consumer_shadow: 205/205 statements, 84/84 branches; ci_shadow_pair: 118/118 statements,
  38/38 branches. Zero new exclusions. Independent review/recheck: 7 PASS.
- A real planner-source mutant fails an existing PlannerTests case. Such executable
  edits retain accepted tests through the pilot guard and old source pins.
- Hosted previous #92 head b8b21b7 passed all Gates: B1418/C1392, coverage19m51s,
  global94.3169%, all59 critical files95/90, repository186/0/0, package8probesPASS.
  Its sole FULL/repository unknown-input reason was domain-model.json. No cross-PR
  speedup is inferred from this baseline.
- Trace has no BLOCK and retains capture-gap warnings.

[Pair summary](checks/paired-summary.json), [first pair](checks/first-pair-summary.json),
[validation and raw hashes](checks/validation.json), [hosted baseline](checks/PR92_HOSTED_BASELINE.md),
[consumer audit](checks/planner-consumer-review.md), [code recheck](checks/paired-code-recheck.md),
[raw evidence ZIP](checks/raw-evidence.zip).

The ZIP preserves execution drivers, native receipts, independent inventories, environment
captures, failed setup evidence, relevant executable mutant, full hosted artifacts and
source/checker hashes. Frozen scripts inside it are historical experiment artifacts.
Independent exclusion witness, full input/environment review and at least three controlled
hosted pairs remain prerequisites for 2C. Existing quality floors and integration fresh
baselines remain unchanged; no merge or production reduction occurred.
