# Development-record regression boundary

Human scope: omit checks of permanent RWB development records and internal frozen scripts; retain shipped M5/Provider features and product behavior. Isolated branch: test/product-doc-ci-boundary-20261004, accepted base ede2bc1d5e3496b4e4c72abb1f39f0a3ce00aedf. PR132 remains a separate M5 fixture performance candidate.

Inputs: repository AGENTS/README, docs/README/DEVELOPMENT, release-surface policy/include, affected tests, ci_components mapping, coverage policy, product catalog parser/schema, and the read-only test-boundary report. Historical records are not altered or removed. Product replay and independent release witness tests remain.

Delegation: Agent Profile test-only fixture boundary implementer; required Skills []; slow_provider_test_design owns tests/test_catalog.py and catalog-implementation outputs only. Migrate two generic parser/filter tests to minimal temporary inputs, remove four intake-history assertions, execute the retained two methods once in existing Python3.11. Stop on unsupported fixture schema rather than mock the parser. Root owns remaining selected tests and stale manifest entries. Final independent review is read-only. Budget: bounded relevant reads and tests, no global rerun, dependency installation or real API call.

Root validation: exact AST removed/retained IDs; unchanged product source/resource/policy authority fields; public rendering/build closure and existing link/leak negative controls; retained governance, mapping and coverage fail-closed controls; bounded real AgentTrace controls. New exact-head component plan and governance before a separate Draft PR. No merge/Ready change in this slice.

Visible handoffs and results are captured locally in messages.jsonl. Some pre-compaction event payloads are unavailable; retain a capture-gap warning, do not claim complete Agent Trace v0.1. Raw failures and prior performance evidence retain their original identity. No coverage-efficiency estimate follows from method deletion alone.
