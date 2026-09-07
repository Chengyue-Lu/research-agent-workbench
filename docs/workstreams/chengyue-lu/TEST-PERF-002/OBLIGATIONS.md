# CI obligations by affected scope

Owner: Chengyue-Lu; cross-owner: let778750-cpu; Audit ID: TEST-PERF-002; risk: R2.
Accepted base: `97f760c43e95b398c396987f349e2199c567cbc7` (PR #65).

Plan v4 binds exact Git diff, event, base policy and a base/head dependency inventory digest.
Governance risk and each execution obligation have independent reasons. A typical R2 test repair is:

```yaml
risk: R2
behavioral_scope: focused
tests: [test_ci_plan, test_ci_checks]
coverage_scope: none
coverage_obligations: []
package_smoke: false
repository_smoke: false
```

`focused` executes the complete selected test modules, including their behavioral, contract, adversarial
and integration cases, on Python 3.11 and 3.13. The selection is derived from machine facts. Agent requests
can add groups/tests or request full evidence. Workers recompute the minimum; a re-signed artifact cannot
remove tests, dependency facts, acceptance, coverage or smoke obligations. `change_class` remains a checked
FAST/FOCUSED/FULL diagnostic alias. Metadata never supplies code execution evidence.

## Selection and reasons

The analyzer reads immutable blobs in batches, builds imports and package initialization edges, and adds
exact file literals, assembled path expressions and conservative resource-reader/opaque-execution edges.
Dictionary keys such as `tests` are metadata, not directory reads. Opaque expansion starts at changed
executable code rather than cascading through unchanged processors of test/fixture input data. It unions old and
new edges, so deleting an import cannot hide its previous consumers. Base policy contract groups remain
additive. For a reviewed contract, the planner locates the immutable Git commit matching its base-side
fingerprint. Unchanged consumers keep that reviewed boundary; new or changed consumers add their entire
downstream closure. Changed imports disable that boundary for the changed source. Candidate fingerprints
cannot authorize their own exclusions. New/modified tests seed their own module and consumers. All other source domains use the same
reverse closure. Python comments/spacing preserve the AST; docstrings remain semantic. Actual coverage
pragmas are tokenized as comments rather than detected in arbitrary strings.

Selection authority has an explicit behavioral bootstrap: semantic changes to `plan_ci.py`,
`ci_dependencies.py`, `ci_checks.py`, `run_unittest_suite.py` or `ci.yml` require full dual-Python behavior.
The rule follows Python AST or workflow structure changes and does not depend on the dependency selector's
chosen tests. Ordinary comments retain scoped behavior. Coverage and smoke remain separate obligations.
Reflected access through `getattr` to execution namespaces or loader capabilities retains opaque consumers,
including assigned, passed and stored functions; ordinary data-attribute access stays outside that frontier.

The `selection` certificate records graph-selected modules with dependency chains, graph-excluded modules,
opaque consumers, errors, affected paths and inventory digest. Base contract groups and explicit additions
are applied separately in the final `tests` list. Unknown surfaces, malformed dependencies, missing test
consumers and stale bases give concrete fallback reasons. Dynamic execution may keep a broad closure;
its presence is retained for review rather than silently treated as independent.

| Change | Behavioral obligation | Coverage obligation |
|---|---|---|
| Documentation/archive with no executable dependency | documentation lane | none |
| Ordinary test or fixture | affected test/consumer closure | none |
| Consumer fingerprint-only refresh | selection-policy tests | none |
| Bounded source or critical validator | complete affected closure | impact |
| CI selection-authority semantics | full behavioral bootstrap | independently derived impact/repository obligations |
| Source plus independent test edit | union of the two closures | impact |
| Monotonic critical/mapping/suite addition | local acceptance and policy tests | local impact subjects |
| Global coverage authority semantics | affected validator/consumer closure | repository plus any executable impact |
| Unclosed source, unsupported surface, stale base | full fallback | repository plus any executable impact |
| Runtime/build environment or integration/release boundary | full | repository plus any executable impact |

Package smoke follows installation/metadata/resources/public CLI consumers. Repository smoke follows
Schema/Registry/validation consumers. Unknown executable scope enables conservative smokes. Risk alone
and the behavioral full label do not enable either smoke.

## Evidence and quality

Coverage is a canonical set: `[]`, `[impact]`, `[repository]`, `[impact, repository]`. Repository evidence
cannot replace impact evidence. The runner executes the union once by canonical test ID and each required
checker runs independently. Both positive and negative evidence remain mandatory for affected critical
surfaces and the existing Provider contract groups. Ordinary executable changes require their changed
statements and outgoing branches at 100/100; they do not invent critical acceptance mappings.

Critical subjects retain whole-file 95/90. Monotonic local policy additions preserve every old critical
entry, acceptance mapping and suite member, and leave other semantic fields unchanged. They add local
proof without requesting unrelated repository coverage. Other semantic authority changes request repository
proof. Repository baselines retain global 90%, critical 95/90, existing exclusions and negative acceptance.
Physical changed lines map to enclosing executable statements, including decorators and multiline branch
origins. Deleted lines have no candidate coordinates; old consumers remain selected. Mapping failures block.
Impact reports explicitly set `repository_coverage_proved: false`.

Fixed `test (3.11)` / `test (3.13)` aggregates revalidate the plan and require every requested job to succeed.
Only a verified empty coverage set permits a coverage skip. Missing, skipped, cancelled or failed required
coverage remains blocking. Old v1-v3 artifacts cannot satisfy v4 dependency and obligation checks.
Content/governance metadata isolation and obsolete-HEAD cancellation retain their existing boundaries.

## Acceptance and measurement

[PR #65's exact 20-file Git fixture](../../../../tests/fixtures/ci/pr65.json) retains its original blobs and
hashes. Its expected plan now selects affected behavioral tests with no coverage or smoke obligations.
Regression tests cover independent tests, removed consumers/imports, mixed source/tests, ordinary comments,
monotonic local critical additions, genuine global authority changes, opaque execution, artifact reductions,
and required-job failures. Full test discovery retains the behavioral and adversarial inventory.

A one-time full oracle validates the selector revision; subsequent PRs consume their computed obligations.
Integration pushes deterministically re-prove the repository baseline. Selected test counts and local suite
elapsed time are distinct from hosted critical-path and total runner time; compare both hosted measures
on exact heads before claiming a CI speedup. Current evidence is recorded in [VALIDATION.md](VALIDATION.md).
