# Definition check outputs

These are human-reviewable documentation records with no runtime or test-data consumer.
Original record bytes remain in commit `fb9242bd0d1ba3b899399fdef9c43a6433b8c50b`; each hash below binds the
committed Git blob, and its text is reproduced in a fenced block.

## Candidate document hashes

Original record: `candidate-files.json`; SHA-256 `5903926e94247ebf3e6a0ed453626969042a2c30caec0906cbe2c166509de424`.

```json
{
  "base": "0d4a1d00a4c32ca9b822df6482a95920e7c21b1b",
  "files": [
    {
      "path": "docs/TASKS.md",
      "sha256": "bfc2a624a87fb4dcc5a88b6bb9786cd719e47ee74f43c2f5a98ab4f6b03be60b"
    },
    {
      "path": "docs/ROADMAP.md",
      "sha256": "2feb13ff964dc011b4974581078bba3e068ad381c73556a57a7ba8109f5fc7fb"
    },
    {
      "path": "docs/M_SERIES_IMPLEMENTATION_MAP.md",
      "sha256": "6d7049f8a3aa1ce7d543bbadd7e191967861925716c18434f55c68e907813bd4"
    },
    {
      "path": "docs/STATUS.md",
      "sha256": "fe244c673c1c838f445a5ea181dcc42ade8edb662ca08358141be2a19a4e834d"
    },
    {
      "path": "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/README.md",
      "sha256": "03c928fd16d86395a4ee45cc620762869d8697ff3aced3ee235cf202879d0f0d"
    },
    {
      "path": "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/RISK_LEDGER.md",
      "sha256": "0b1154911e2945146eedb9e5a40a31631c5047069b74eadd0fb618575286382e"
    },
    {
      "path": "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/WORKLOG.md",
      "sha256": "eb91f6565c8de72ddb580e20a26c96b33c39e4ae2f57b1aa161badd86f9fcd5d"
    },
    {
      "path": "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-008_LIVE_PILOT_GATE.md",
      "sha256": "493792ddc5fbb4fb4a9f112eab54dc85f095c0a2ecbfc35fa7d38fe7ba936040"
    }
  ]
}
```

## Successful documentation check

Original record: `documentation-check.log`; SHA-256 `60cb52842d992255373904851db53be3043cf15c02204280bd04017027a40988`.

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

----------------------------------------------------------------------
Ran 10 tests in 0.280s

OK
```

## Initial environment failure

Original record: `initial-documentation-check.log`; SHA-256 `0ebbf109e2ab8c799625a41bb0608b4ad22fa9856b6b791d4926f0cf59b86812`.

```text
Portable-path redaction: local worktree prefix replaced by <worktree>.
test_adr_numbers_are_unique (tests.test_documentation.DocumentationTests.test_adr_numbers_are_unique) ... ok
test_document_surface_authorities_exist (tests.test_documentation.DocumentationTests.test_document_surface_authorities_exist) ... ok
test_execution_runtime_audit_keeps_private_sources_out_of_git (tests.test_documentation.DocumentationTests.test_execution_runtime_audit_keeps_private_sources_out_of_git) ... ok
test_first_contact_surfaces_do_not_own_internal_milestones (tests.test_documentation.DocumentationTests.test_first_contact_surfaces_do_not_own_internal_milestones) ... ok
test_getting_started_uses_recommended_not_replay_path (tests.test_documentation.DocumentationTests.test_getting_started_uses_recommended_not_replay_path) ... ok
test_internal_markdown_links_resolve (tests.test_documentation.DocumentationTests.test_internal_markdown_links_resolve) ... ok
test_no_skill_path_requires_execution_view_without_assignment (tests.test_documentation.DocumentationTests.test_no_skill_path_requires_execution_view_without_assignment) ... ok
test_public_projection_documentation_and_build_closure (tests.test_documentation.DocumentationTests.test_public_projection_documentation_and_build_closure) ... ERROR
test_recovery_gate_separates_authority_from_implementation_evidence (tests.test_documentation.DocumentationTests.test_recovery_gate_separates_authority_from_implementation_evidence) ... ok
test_stable_examples_do_not_use_retired_skill_packages (tests.test_documentation.DocumentationTests.test_stable_examples_do_not_use_retired_skill_packages) ... ok

======================================================================
ERROR: test_public_projection_documentation_and_build_closure (tests.test_documentation.DocumentationTests.test_public_projection_documentation_and_build_closure)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "<worktree>\tests\test_documentation.py", line 26, in test_public_projection_documentation_and_build_closure
    from tests.public_surface_helpers import build_input_errors, documentation_errors, selected_files
  File "<worktree>\tests\public_surface_helpers.py", line 12, in <module>
    from markdown_it import MarkdownIt
ModuleNotFoundError: No module named 'markdown_it'

----------------------------------------------------------------------
Ran 10 tests in 0.158s

FAILED (errors=1)
```

## Task governance audit

Original record: `task-definition-check.json`; SHA-256 `181c079dff025fadfcfc719bcea86eecb7256975d0f754d6afcc98eb3cc88ed0`.

```json
{
  "base": "0d4a1d00a4c32ca9b822df6482a95920e7c21b1b",
  "kind": "task-definition working-tree audit",
  "source_task_sha256": "53bf11dcdb76a71a911714a2c4dd6406770d065420509515a1e59a1af32f074f",
  "candidate_task_sha256": "bfc2a624a87fb4dcc5a88b6bb9786cd719e47ee74f43c2f5a98ab4f6b03be60b",
  "added": [
    "M5-008"
  ],
  "revised": [
    "M5-004"
  ],
  "unchanged_done_tasks": 68,
  "m5_007_unchanged": true,
  "dependencies_preserved_no_new_cycle": true,
  "governance_task_check": "PASS",
  "negative_probes": {
    "premature_DONE": "rejected",
    "undeclared_M5_004_change": "rejected",
    "implementation_in_task_definition": "rejected",
    "DONE_definition_rewrite": "rejected"
  }
}
```
