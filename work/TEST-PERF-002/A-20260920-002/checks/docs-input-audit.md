# Markdown invocation pilot: real consumer audit and failure probes

Accountable owner: Chengyue-Lu. Agent profile: CI consumer auditor; required Skills: [].
Source snapshot: `09c6cb1c82680233c369014e0831874b6702d3b7` from the isolated
`ci-consumer-shadow` worktree. Date: 2026-09-20. Execution authority: **false**.

## Finding

A bounded modified-existing-Markdown pilot is practical, but retaining only
`DocumentationTests` is insufficient. An actual README navigation fault passed all ten
documentation methods and failed the existing public-surface navigation method.
Several public-surface methods that look fixture-only also consume other real public
pages through `self.files`; an actual GETTING_STARTED leak made them fail.

Initial candidate should retain the accepted `documentation` group plus the full
`test_public_surface` module for this pilot. The group's existing `test_pr_governance`
obligation is retained; this audit does not replace the actual PR governance job.
The demonstrated unrelated candidate exclusions are the two in-memory Kernel tests.
Other business exclusions require separate invocation closure and actual observations.

## Proposed pilot boundary

For the first shadow experiment, use exact modified-existing regular Markdown paths:

- `README.md`
- `docs/README.md`
- `docs/GETTING_STARTED.md`
- `docs/workstreams/chengyue-lu/TEST-PERF-002/DOMAIN_MODEL.md`

Require exact base/head/target and a diff consisting only of content modifications to
these existing regular `100644` entries. Preserve both old/new bytes and tree identity.
Any addition, deletion, rename, type/mode change, malformed/opaque input, executable
content, changed consumer/helper/policy/runner/environment, or other path leaves this
pilot and retains the accepted plan. An exact path match is an experiment eligibility
check, not an exclusion witness; arbitrary `docs/**/*.md` is not yet qualified.

This boundary excludes all archive-wide claims. In particular, duplicate ADR numbers
require directory membership changes and belong to an add/rename conservative control,
not the three modified-existing-file success probes below.

## Actual input closure

| Consumer | Actual inputs and behavior | Consequence |
| --- | --- | --- |
| `DocumentationTests.test_internal_markdown_links_resolve` | ROOT README plus every `docs/**/*.md`; parses inline Markdown targets and checks filesystem existence, including non-Markdown files/directories | Keep for every pilot edit; document membership and link-target existence matter |
| `test_public_projection_documentation_and_build_closure` | `selected_files(ROOT)` invokes real `git ls-files --cached --others --exclude-standard -z`; reads last release policy includes and every selected file; runs public documentation and runtime build-input closure | Bind Git index/untracked/ignore state, release policy, helper bytes, selected inventory, public pages and runtime catalogs; no filename-only closure |
| `test_first_contact_surfaces_do_not_own_internal_milestones` | ROOT README, PROJECT_CHARTER, ARCHITECTURE, GETTING_STARTED bytes | Keep when any first-contact page changes |
| `test_getting_started_uses_recommended_not_replay_path` | GETTING_STARTED bytes; checks forbidden replay-default token | Keep for GETTING_STARTED changes |
| `test_stable_examples_do_not_use_retired_skill_packages` | Three explicit module docs | These bytes are outside this exact pilot; retaining the cheap whole module is simpler initially |
| `test_document_surface_authorities_exist` | Explicit docs/index/CI-file existence | Content-only pilot does not alter those memberships; retain whole module |
| Recovery audit methods (three) | Six named Huang Yi audit docs, with additional content checks on RECOVERY_GATE_PROPOSAL | Outside pilot; retain whole module, do not label general workstream docs fixture-only |
| `test_adr_numbers_are_unique` | `docs/decisions/[0-9][0-9][0-9][0-9]-*.md` names | Add/delete/rename needs separate proof; content-only does not change numbered membership |
| `PublicSurfaceTests.setUpClass` | Full `selected_files(ROOT)` snapshot | Every class method receives real public files; replacing README in a dictionary leaves other real pages intact |
| `test_public_navigation_and_support_have_one_source` | Each PUBLIC_PAGES entry, real support matrix tokens, real release-projection index | ROOT support navigation is a distinct actual obligation missed by documentation-only candidate |

Shared code/input bindings include `tests/__init__.py`, `tests/test_documentation.py`,
`tests/test_public_surface.py`, `tests/public_surface_helpers.py`, latest release policy,
Git behavior and environment, MarkdownIt/linkify dependencies, Python and OS. Public helper
also interprets runtime-resources/catalog JSON when checking build inputs. No attempt was
made to replace these reads with mocks or a fixed file dictionary.

The graph of all actual business invocations is not proved closed by this audit. Generic
runtime APIs can accept caller-selected Markdown as input; a repository path's suffix does
not exclude those callers. Existing accepted dependency/witness obligations remain active.

## Concrete cross-consumers outside the initial allowlist

Scoped source search identified these actual exceptions:

- `tests/test_trace_risk_codes.py::TraceRiskCodeTests.test_registry_exactly_matches_canonical_module_vocabulary`
  reads `docs/modules/07-ARTIFACTS_AND_PROVENANCE.md` and compares its warning vocabulary
  with production `TRACE_RISK_CODES`. Keep this consumer for that document.
- `tests/test_pr_governance.py` reads
  `docs/workstreams/huangyi/execution-runtime-recovery-audit/GITHUB_GOVERNANCE_ROLLOUT.md`
  in `test_pr25_rollout_is_retained_and_marked_superseded`. The real governance CLI also
  reads exact Git TASKS/workstream blobs; its checks must remain independent of unit-test selection.
- `tests/test_m5_trace_export.py` imports an executable `export_capture.py` from a
  `docs/workstreams/.../attempts/` directory. This is outside the Markdown pilot and
  demonstrates why archive directory placement is not a runtime exemption.
- `tests/test_release_surface.py::ReleaseSurfaceTests.test_real_policy_schema_and_no_broad_runtime_or_internal_surface`
  reads actual release policy, tracked path membership and governance policy. Its other
  methods use a synthetic Git seed, but the whole module cannot be called fixture-only.

For README/public documentation changes, package/public-install consequences also remain
separate from coverage. No executable or coverage authority changes in these probes, but
this audit does not independently authorize either smoke job to skip.

## Real failure probes

Producer: [run_probes.py](docs-probes/run_probes.py).
Machine summary: [summary.json](docs-probes/summary.json).
The producer clones the frozen source into `docs-probes/snapshot` with its own Git metadata,
checks out the exact base, commits each one-file mutation as a detached local probe,
and restores that detached snapshot to the base. No official branch or primary worktree is changed.
The snapshot is retained with its object database; probe commits are not pushed.

Command used:

```powershell
& 'D:\lcy\develop\_assessments\rwb-ci-schema-parse-20260917\venv311\Scripts\python.exe' `
  'D:\lcy\develop\_assessments\rwb-ci-consumer-shadow-20260920\docs-probes\run_probes.py'
```

Each case executes the unchanged real modules `tests.test_documentation` (10 methods),
`tests.test_public_surface` (13 methods), and `tests.test_kernel` (2 methods) in a fresh process.
Imports are checked to resolve inside the isolated snapshot. The custom result subclass only
records standard unittest events/times; it neither changes assertions nor mocks any consumer.

| Case | Exact target | Actual result | Observed process wall |
| --- | --- | --- | ---: |
| Baseline | `09c6cb1c82680233c369014e0831874b6702d3b7` | 25 PASS | 1.003 s |
| Broken link appended to `docs/README.md` | `de0682dd582b6ce43356e8117d892489fa4be9b6` | 24 PASS / 1 failed method: `test_internal_markdown_links_resolve` | 1.083 s |
| ROOT README support navigation replaced by another valid page | `09a33b612cd559d74b45bbffd907d603e4fa70de` | 24 PASS / 1 failed method: `test_public_navigation_and_support_have_one_source`; DocumentationTests all PASS | 1.008 s |
| Existing internal STATUS link appended to public GETTING_STARTED | `1307bdb9f66fbe79fc583c65d062b0a7015db72c` | 19 PASS / 6 failed parent methods; 10 unittest failure events including subtests | 1.006 s |
| Neutral sentence appended to workstream DOMAIN_MODEL | `9724a4ee36889b327b33ba1ebb066a6e02521404` | 25 PASS | 1.025 s |

All cases have zero import/runtime errors. Both Kernel methods pass in every case.
Raw test IDs/statuses, target, selected dependency versions, Python/OS, per-test times and full
failure tracebacks are in the case JSON receipts; stdout/stderr are retained separately.
Before/after file hashes, producer/input hashes, actual diff status and Git version are in summary.json.

The public leak's six failed parent methods are:

1. `DocumentationTests.test_public_projection_documentation_and_build_closure`
2. `PublicSurfaceTests.test_autolink_syntax_in_code_remains_literal`
3. `PublicSurfaceTests.test_markdown_reference_html_and_unicode_anchor_resolve`
4. `PublicSurfaceTests.test_rendered_public_entity_and_reference_destinations_resolve`
5. `PublicSurfaceTests.test_selected_source_has_closed_docs_and_build_inputs`
6. `PublicSurfaceTests.test_user_project_attempt_paths_are_not_repository_archive_links`

Items 2–4 and 6 retain the changed GETTING_STARTED bytes when replacing only README in
their test dictionaries. Their observed failures directly refute a blanket “fixture test” skip.

## Candidate retain/skip decisions for comparator

Retain existing `documentation` group (`test_documentation`, `test_pr_governance`) and
add/retain `test_public_surface` for pilot public-page changes. For this first cheap probe
set, retaining both complete documentation/public modules is a clear conservative choice.
Match raw unittest IDs by module/class/method; subtest failure must mark the parent test as
failed rather than treating it as a separate selected-test identity.

Tentative unrelated skips, demonstrated only in the observed 25-test subset:

- `test_kernel.KernelObjectTests.test_revision_is_part_of_object_reference`
- `test_kernel.KernelObjectTests.test_claim_keeps_support_and_counterevidence_separate`

These methods construct production kernel objects from literals and make in-memory assertions;
their inspected implementations contain no filesystem, Git, environment or doc input calls.
The actual source/module initialization and toolchain must remain unchanged. Their repeated
PASS results are a precision control, not proof that every unobserved business test can skip.

The governance `PullRequestBodyTests` methods operate on literal PR-body fixtures, but this
audit did not execute them in the probes and does not propose dropping their accepted group.
Likewise synthetic release fixture methods need method/seed/policy closure before exclusion.

## Limitations and evidence handling

- These are three different real consumer invariants tested by isolated mutations, not three
  naturally occurring PR histories. They seed the corpus; they do not satisfy broad activation.
- The 25 observed tests are not accepted-full behavioral B, coverage C, or a coverage producer.
  No coverage threshold, coverage scope, smoke obligation or aggregate rule was exercised/relaxed.
- Timings characterize this small local probe invocation. They are not a measurement of the
  37-minute job, not paired hosted savings, and not a full-suite speedup claim.
- No add/delete/rename experiment ran; this remains an explicit excluded pilot class. All
  tested changes are `M` on existing Markdown; unknown membership continues conservative execution.
- First-run raw files are preserved under `docs-probes/first-run`. Their custom receipt marked
  a parent method PASS when only subtests failed, although raw unittest failures were correct.
  The producer was corrected to aggregate failed subtests, and all five cases reran. Consume
  the top-level case receipts, which include the corrected parent status.
- Only the local assessment report/probe folder was written. No primary/official branch,
  CI authority, policy, production source, test method or GitHub resource was edited.

Visible parent decision: write scope was extended from this report to `docs-probes/**` to
permit the disposable copies, producer and logs. Parent was informed of the missing public
navigation consumer, non-fixture public-page dependence, actual trace/governance doc consumers,
and corrected subtest receipts. The next step is independent candidate-versus-observed
comparison with explicit partial-observation scope and activation blockers.
