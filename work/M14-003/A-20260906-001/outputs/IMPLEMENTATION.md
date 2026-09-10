# M14-003 portable Runtime resource closure

- Owner: Chengyue-Lu; main agent only, H0; no Skill binding or delegation.
- Authority: user requested continued development in PR #60, following the predefined M14-001 -> M14-003 dependency in ADR-0021 / Task acceptance.
- Baseline: `0b2d56f48abdfbc7c52478c6a46afdee801bf2bb`; implementation: `bd76a4ca17eb6bc1b9cfb25c756067b535357674`.
- Build hook and strict RuntimeResourceManifest generate one pinned catalog from explicit public resource classes. Schema/default catalog loading is independent of project and integration roots. Schema validation consumes hash-checked bytes.
- Installed-runtime checks cover Schema/index/hash/identity/reference closure. Conditional Skill manifests/assets map into a controlled installed namespace and reconstruct exact package hashes. Production Projection index remains empty; repository publication authority stays separate.
- Resource regressions: 12/12; exact governance/docs: 125/125; repository: 183/0/0; full: {'errors': 0, 'failed': 0, 'passed': 919, 'skipped': 3}; coverage-quality: {'errors': 0, 'failed': 0, 'passed': 858, 'skipped': 3}; global line 91.95%; resource checker 100.00% line / 98.00% branch.
- Python 3.11.16 and 3.13.15 each installed direct and sdist-rebuilt wheels outside checkout. All 8 normal/poison cases passed; all 120 Runtime assets match, including 72 Schemas and 4 Modes. Package corruption is rejected.
- A parallel verification run exposed live editable resources being replaced by a build. The smoke now uses an isolated build-source copy; corrected runs pass. That failed run is retained in `checks/resource-build-race.log`.
- Phase C reuses the pinned SchemaCatalog through document and Method Trace validation. Its 18 regression methods pass, including actual subprocess denial of Runtime manifest/catalog reads under the unchanged input boundary. Pre-fix failed full/coverage outcomes are preserved in `checks/phase-c-before-fix.json`.
- All 33 final implementation/policy paths are pinned in `checks/verification.json`. Full/coverage ran on `bd76a4ca17eb6bc1b9cfb25c756067b535357674`. Policy-only `0f8828d8d93adb56b5f5c930c126835765b119ff` declares the two automatically excluded type-checking import lines, with unchanged product bytes and passing focused tests plus coverage Gate reevaluation. The initial declaration failure is retained in `checks/coverage-gate-before-declaration.log`; final-head hosted CI and cross-owner review remain integration gates.
- Native capture gaps are explicit. Git and PR #60 own subsequent publication receipts.
- Next: publish the implementation and archive in PR #60 for cross-owner review. M14-004 remains PARKED and must compose public docs plus the new build inputs in a new surface policy version. M14-005 remains BLOCKED and owns readiness/cutover.
- Release topology stays dormant; no real release branch, tag, merge or Skill admission occurred.
