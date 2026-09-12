# Resource dependency precision

Owner: Chengyue-Lu; cross-owner: let778750-cpu; Audit ID: TEST-PERF-002; risk: R2.

PR #68 at `0f6da949c9d89d4d5e0cea9cffad1e85465bb52c` changes documentation and its
Attempt Archive on `develop@11c3b57dfbf8af0dc2587fc421d097e2544941c3`. Its hosted plan
selects 35 behavioral modules, coverage `none`, package smoke and no repository smoke.
The selected modules contain 725 of the 1,096 cases in that base's full 3.11 receipt.

## Confirmed causes

The old graph treats the name `docs/STATUS.md` in a set exclusion assertion as a file
input. It follows the resulting edge through `test_release_surface`, a historical
oracle importing that test, and the `root / "work"` containment guard in Run
reconstruction. The guard is then interpreted as consuming the entire work directory,
reaching the CLI and 23 test modules. The same basename matching also lets a qualified
README reference consume unrelated README files in other directories.

The repair recognizes lexical comparisons and boolean predicates on literal sets or
unambiguous pathlib values. Function-local name lists used exclusively by lexical
predicates are not content inputs. Reads, unknown calls, returned/exported values,
closures, rebinding and global/nonlocal assignments retain conservative references.
Whole path expressions are resolved against fixed `__file__` / pathlib roots and
directory prefixes, normalizing parent segments and retaining ambiguity when a path
leaves the repository root. Their individual filename components no longer create unrelated
basename aliases. Unknown roots and bare filename/helper inputs retain ambiguity.

## Import-bound lexical names

Cross-owner review 5184637057 reproduced a missed reader at `09d7611`: a local
`from project_config import ROOT` was absent from the lexical binding table, so the
reader incorrectly inherited an unrelated module-level fixed ROOT. A real temporary
Git repository confirms that changing `docs/input.md` from `good` to `bad` fails the
consumer while the old candidate selector excludes it; accepted `11c3b57` selects it.

ImportFrom binds each imported name or alias in its enclosing lexical scope. Import
binds its alias, or the first component of a dotted name. These nearer bindings stop
fixed-root inference from falling through to an outer assignment. Imported roots that
cannot be resolved retain the conservative unknown-reader dependency. An unambiguous
`pathlib.Path` import still supports fixed path inference in its actual scope.

Regression scenarios cover real document failures with direct/aliased imports, plain
and dotted imports, async functions, nested closures and class bodies. Controls verify
that sibling imports and class namespaces do not shadow a method's module-level free
variable, and that known local Path constructors retain bounded input selection.
The ordered behavioral producer and Schema self-check reuse remain in place.

## Verification boundary

The committed PR #68 fixture pins its exact changed paths/statuses and tests the
specific false chain alongside an actual document-reading consumer. It does not
duplicate the original document bytes or claim to be a complete repository snapshot.
The separate read-only replay uses the original complete Git base/head snapshots.

The proposed selector reduces that complete-repository plan to 10 modules / 261
baseline test IDs, with coverage `none` and both smokes false. The same baseline's
recorded case durations sum to 74.728 seconds for those IDs, versus 773.460 seconds
for the former selection. These are cost attribution from one existing receipt,
not new hosted timings or a guarantee of future wall time.

The full graph audit removes 432 edges and adds four previously missed fixed
relative inputs. Of the removed edges, 355 enter the Run reconstruction directory
guard, 45 enter governance path-name classification, and 23 enter release path-name
classification. The remaining nine are name/metadata comparisons in tests and the
CI checker. Actual imports, directory scans, old/new graph union, Markdown consumers,
archive execution, helper/fixture proof identities and opaque execution remain.

Other probes intentionally remain conservative: an arbitrary fixture resource reaches
77/78 modules through unresolved readers; raw executable/oracle seeds reach 75/78
through opaque execution. Accepted local contracts still own the narrower executable
edit domain. Remaining CI/runner and ambiguous basename consumers are not removed
merely to achieve a smaller number. This round does not claim universal narrow selection.

The selector repair itself requires the full dual-Python behavioral bootstrap,
changed-line/branch 100/100, critical 95/90, the independently pinned witness and
cross-owner review. Repository global 90%, integration coverage, metadata isolation,
plan-bound fail-closed aggregates and existing negative acceptance are unchanged.
