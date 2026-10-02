# Definition checks

Docs-only candidate; no Provider product test, full/coverage, new live run or Human approval.

## Task/dependency and source receipt audit

```json
{
  "kind": "docs-only task-definition audit",
  "base": "1c9cef27983e93362be33830f989e124ad3ccc41",
  "source_task_sha256": "8e83f401c56afb9728feedb65ff2463abe0d433c3ab913f9960981660cf6363a",
  "candidate_task_sha256": "a4360a95133b4e0bcbc017bae24528cb0cd94810f6dd632361ebfe43faa69719",
  "added": [
    "M6-009",
    "M6-010"
  ],
  "revised": [
    "M5-004",
    "M5-008"
  ],
  "unchanged_DONE_rows": 70,
  "original_M6_004_unchanged": true,
  "READY_dependencies_DONE": true,
  "no_new_cycle": true,
  "governance_task_check": "PASS",
  "negative_probes": {
    "premature_live_DONE": "rejected",
    "undeclared_M5_004_dependency_change": "rejected",
    "product_implementation_in_definition": "rejected",
    "rewrite_DONE_definition": "rejected",
    "READY_with_BLOCKED_dependency": "rejected"
  },
  "api_calls": 0,
  "official_matrix_receipt_hashes_verified": {
    "FETCH_RECEIPTS.json": "75343eade1b6cf91e1a43ef16b6fff5e94b84184880ca11b3e9d8dbdeaba26e6",
    "REFERENCE_FETCH_RECEIPTS.json": "f02d411a1e78b2185a74bfb8d17d8eb34301bf4acfdedbafca7ac6753010b0b4",
    "SURVEY_FETCH_RECEIPTS.json": "8420291ed64fa04ffb52d9334ba160eaa2723e3f54e0778afac79a5e0b71d2c1"
  },
  "coverage": "11 public providers/gateway + 3 enterprise boundaries; documented only",
  "documentation_tests": "23/23 PASS",
  "independent_review": "initial P2 invocation budget resolved to ADR-0007 total <=3; not human approval"
}
```

## Documentation/public check

Python 3.11; existing tests.test_documentation + tests.test_public_surface. Log SHA-256 `31f59f28a9dcc1caa8e638131f92a59dd9754560146ff4c30cf6943ab782a7cb`.

```text
test_adr_numbers_are_unique (tests.test_documentation.DocumentationTests.test_adr_numbers_are_unique) ... ok
test_document_surface_authorities_exist (tests.test_documentation.DocumentationTests.test_document_surface_authorities_exist) ... ok
test_execution_runtime_audit_keeps_private_sources_out_of_git (tests.test_documentation.DocumentationTests.test_execution_runtime_audit_keeps_private_sources_out_of_git) ... ok
test_first_contact_surfaces_do_not_own_internal_milestones (tests.test_documentation.DocumentationTests.test_first_contact_surfaces_do_not_own_internal_milestones) ... ok
test_getting_started_uses_recommended_not_replay_path (tests.test_documentation.DocumentationTests.test_getting_started_uses_recommended_not_replay_path) ... ok
test_internal_markdown_links_resolve (tests.test_documentation.DocumentationTests.test_internal_markdown_links_resolve) ... ok
test_no_skill_path_requires_execution_view_without_assignment (tests.test_documentation.DocumentationTests.test_no_skill_path_requires_execution_view_without_assignment) ... ok
test_public_projection_documentation_and_build_closure (tests.test_documentation.DocumentationTests.test_public_projection_documentation_and_build_closure) ... ok
test_recovery_gate_separates_authority_from_implementation_evidence (tests.test_documentation.DocumentationTests.test_recovery_gate_separates_authority_from_implementation_evidence) ... ok
test_stable_examples_do_not_use_retired_skill_packages (tests.test_documentation.DocumentationTests.test_stable_examples_do_not_use_retired_skill_packages) ... ok
test_autolink_syntax_in_code_remains_literal (tests.test_public_surface.PublicSurfaceTests.test_autolink_syntax_in_code_remains_literal) ... ok
test_build_input_removal_is_rejected (tests.test_public_surface.PublicSurfaceTests.test_build_input_removal_is_rejected) ... ok
test_excluded_files_are_not_selected (tests.test_public_surface.PublicSurfaceTests.test_excluded_files_are_not_selected) ... ok
test_excluded_links_cannot_hide_in_reference_html_or_encoding (tests.test_public_surface.PublicSurfaceTests.test_excluded_links_cannot_hide_in_reference_html_or_encoding) ... ok
test_markdown_reference_html_and_unicode_anchor_resolve (tests.test_public_surface.PublicSurfaceTests.test_markdown_reference_html_and_unicode_anchor_resolve) ... ok
test_missing_target_and_anchor_are_rejected (tests.test_public_surface.PublicSurfaceTests.test_missing_target_and_anchor_are_rejected) ... ok
test_product_sources_and_schemas_are_complete (tests.test_public_surface.PublicSurfaceTests.test_product_sources_and_schemas_are_complete) ... ok
test_projection_without_license_is_not_build_ready (tests.test_public_surface.PublicSurfaceTests.test_projection_without_license_is_not_build_ready) ... ok
test_public_navigation_and_support_have_one_source (tests.test_public_surface.PublicSurfaceTests.test_public_navigation_and_support_have_one_source) ... ok
test_rendered_entities_and_autolinks_cannot_reach_excluded_files (tests.test_public_surface.PublicSurfaceTests.test_rendered_entities_and_autolinks_cannot_reach_excluded_files) ... ok
test_rendered_public_entity_and_reference_destinations_resolve (tests.test_public_surface.PublicSurfaceTests.test_rendered_public_entity_and_reference_destinations_resolve) ... ok
test_selected_source_has_closed_docs_and_build_inputs (tests.test_public_surface.PublicSurfaceTests.test_selected_source_has_closed_docs_and_build_inputs) ... ok
test_user_project_attempt_paths_are_not_repository_archive_links (tests.test_public_surface.PublicSurfaceTests.test_user_project_attempt_paths_are_not_repository_archive_links) ... ok

----------------------------------------------------------------------
Ran 23 tests in 0.856s

OK

```

## Review resolution

Independent review found 3 shape + 2 Session requests exceeded accepted ADR-0007 item11. Candidate now uses Tool call + Tool-result/text + Schema, total at most 3 calls. Reviewer rechecked that change; official matrix was integrated and receipt hashes checked by coordinator, not retrospectively claimed reviewed by that agent.

## Exact-head governance

Full PR metadata/topology/workstream/published-identity check is recorded against the published candidate commit in the PR/local receipt after commit; this file is not a self-referential exact-head attestation.

## Preparation and budget follow-up

User final API input+output ceiling is 10,000,000 tokens, failed calls included. Bounded independent definition review found no actionable blocker in binding/Session/probe scope and budget semantics; it reviewed a point-in-time uncommitted candidate, not a Human approval or final-head live attestation. Review SHA-256 `1769fec44c92c6187d308ab1295fb023bfaa076c02aa107ed4976b64672f3ab6`.

Separate source-attested endpoint collision probe matched the loaded bytes of six explicitly selected modules to the base Git blobs and again observed different endpoints with equal binding, credential.resolve/send both zero. Receipt SHA-256 `61475a323e002f21d3cfa14323e452945df21f202579299192287d8c3802a139`. This is local preparation evidence, not new product conformance.
# 用户直接接受与费用策略补充

用户直接接受此纯文档定义，并明确余额充足、计费币种/账单不可得不作为测试前置条件。
PLAN、Risk Ledger 和 Handoff 同步该指令；累计输入加输出 10,000,000、未知token停止、
Flash/北京时间18:00后及官方闲时、三调用/无自动retry/fallback保持。
此直接接受不记录为黄毅新的review或reviewer不可用事实，也不代填产品离线或live通过。
