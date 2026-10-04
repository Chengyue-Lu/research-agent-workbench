# Product regression and development-record inputs

Owner: Chengyue-Lu. Scope: test maintenance on develop. The user clarified that permanent development records and internal content do not need recurring product tests; packaged M5, Provider and other product functions remain in scope.

## Implemented boundary

- Remove 21 test methods that only check development prose, intake history or frozen internal exporters/checkers. This includes the all-documents link scan; public links continue through the existing rendered release-document closure and its negative controls.
- Keep the two catalog API tests and provide separate temporary JSON inputs through the real loader. They retain quarantine/trial separation and mode/capability metadata filtering, without reading the development intake corpus.
- Keep both product compatibility replay methods. Remove their old source-ZIP and launcher-history assertions and the frozen checker's negative loop; preserve receipt/input hashes, three old one-stage rejections, blocked acceptance, four repaired outcomes and the positive validation-subject witness.
- Remove the deleted exporter module from component and coverage-quality inventories. Coverage policy 2.3.6 changes that suite entry only. Source root, global 90%, critical 95/90, critical inventory, negative acceptance and exclusions remain identical to the accepted base.

Historical records and frozen fixtures remain in Git. User project archives, runtime trace/closeout validation, release leakage controls and independent release witness tests remain product checks even when their fixture storage uses a work directory.

## Verification

Python 3.11.16: 68 unique relevant methods passed. The initial local run passed 60 controls and reported four missing generated `_runtime_pin` errors. Generate the existing Runtime resource closure, then execute only those four methods; all pass. The two catalog tests and two current-API compatibility replays each execute once separately. The original errors and the earlier helper import failure before test execution are preserved.

AST comparison confirms 21 removals, two catalog fixture rewrites, two replay-method refinements (one renamed), and 132 unchanged retained method bodies across the affected modules. Product source, schema, registry, release authority and historical inputs are unchanged. This local slice collects no coverage and does not prove the repository coverage floor.

Compact delegated-work evidence: [attempt record](../../../../work/TEST-BOUNDARY-001/A-20261004-001/README.md). Pre-compaction transmissions are incomplete; retain the capture-gap warning and do not label the record complete Agent Trace v0.1.

## Cost and remaining work

This change removes irrelevant regression obligations; there is no measured whole-CI speedup claim. The previously measured development-export suite was about 1.7 seconds, while the main cost lies in Provider source checks and Harness execution. Those performance changes have separate owners and candidates. The M5 JSON fixture candidate in PR132 remains independent.

Permanent-record checks are removed by their actual subject, not by blanket exclusion of `work/**`, modules that are not yet public, or product behavior. Explicit compatibility fixture migration may later remove historical storage coupling while preserving the same product cases and independent input evidence.
