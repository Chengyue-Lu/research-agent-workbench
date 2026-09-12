# Import-bound lexical path shadowing repair

TEST-PERF-002 revision 27; Chengyue-Lu; R2; source `b1c9a82d1b500b07f9d485c4ba44e84a5da07433`; base `1cb0c19c1182aac368cd61afee111249a86818bb`.

Cross-owner review 5184637057 identified a missed document reader. In a real temporary
Git repository, a function-local imported ROOT points to docs while the outer fixed ROOT
points to the repository root. The same consumer passes with good document contents and
fails after the document becomes bad. Accepted 11c3b57 selects it; reviewed 09d7611 omits it
without an analysis error. The old-head reproduction and reviewer text are preserved.

ImportFrom now binds each name/alias in its lexical scope; Import binds its alias or the
first dotted-name component. A nearer import prevents fallback to an outer fixed root.
Unresolved imported roots retain conservative dependencies. Unambiguous Path imports still
support fixed-root inference. The ordered behavioral producer, successful Schema self-check
cache, existing quality floors and mandatory negative acceptance remain intact.

The 15 PR commits rebased without conflicts onto current develop@1cb0c19, which contains
merged documentation PR68. This repair then adds three regression scenarios: real Git-bound
good/bad readers with direct/aliased imports; import/from/alias/dotted/nested/async/class
scope cases; and controls for unrelated scopes and known local Path constructors.

Local verification: 41 dependency tests PASS; broader focused checks 195 PASS. Dependency
analyzer line/branch coverage is 100/100 (413 statements, 266 branches). All three complete
Git snapshot graph comparisons preserve existing edges. Historical PR68's whole plan remains
equal, with 10 modules, coverage none and both smokes false. These are selection and targeted
coverage proofs, not a current-head hosted full or repository-coverage claim.

The frozen source plan requires full behavior and impact plus repository coverage. Final
archived-head hosted CI, independent pinned selection witness and cross-owner acceptance
remain pending at archive sealing. No merge or release occurred. The same-tree merge identity
cost remains a separate Issue48 follow-up; current exact-target rules are unchanged.

The recorder was created before implementation and restored from its live pickle. Native
event/message export gaps remain explicit. Earlier sealed Attempts are unchanged.
