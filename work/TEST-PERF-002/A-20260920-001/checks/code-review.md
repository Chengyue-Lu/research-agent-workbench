# Independent review: CI domain model 2A

Reviewer profile: CI diagnostic correctness reviewer; skills=[]; accountable owner Chengyue-Lu.
Scope: read-only inspection of the four new files and their invoked accepted helpers. No source edits, commits, GitHub changes, or test-suite executions.
Observed worktree: ci-domain-model; inventory baseline declared as 171d4654f88e926f239cdf25bc8168109b81f391. Source files were still untracked during review.

## Assessment

The diagnostic authority boundary is correctly explicit: declarations reject execution_authority=true and nonempty pilots; reports preserve accepted execution fields and remain ineligible for activation. Overlapping routing uses a union, and missing historical consumer records are visible. No P1 execution-authority bypass was found in this slice. Three P2 issues should be closed before treating the diagnostic as a reliable evidence producer.

## Findings

### P2: Bind the governance helper actually executed during plan verification

Location: .github/scripts/ci_domain_audit.py:143-145.

producer_sources hashes the domain auditor, contract shadow helper, input classifier, planner and dependency analyzer, but omits check_pr_governance.py. The executed chain ci_contract_shadow.verify_observed_plan -> planner.make_plan -> risk_at dynamically loads that local file (plan_ci.py:272-287). The existing contract-shadow report explicitly includes its hash (ci_contract_shadow.py:160-162). A report cannot fully identify the local implementation used for verification while this executed helper is omitted. Add its exact observed source hash to producer_sources and a regression asserting the complete intended producer inventory. The observed plan's Git binding identifies repository objects, not the separately loaded local helper bytes.

### P2: Refuse to overwrite input evidence with the diagnostic report

Location: .github/scripts/ci_domain_audit.py:157-168, especially line 168.

main reads all inputs and then writes --output without checking whether it resolves to --plan, --model or --receipt. An accidental equal path successfully destroys the original evidence/model by replacing it with a domain report. ci_contract_shadow.py:188 already protects its plan input. Resolve paths and reject input/output aliases before processing; test that original bytes remain unchanged for each input collision. Symlink aliases should compare resolved paths; existing hardlink aliases may be checked with samefile where available.

### P2: Report a Gitlink as unknown without dereferencing its foreign commit

Location: .github/scripts/ci_domain_audit.py:126-131.

The code reads every changed path using planner.read_at before classifying its Git mode. dependencies.snapshot includes entries with mode 160000 and type commit. A Gitlink's referenced object is normally not present in the superproject object database, so git show <commit>:<path> can fail and abort report generation. That prevents the promised mode/unknown diagnosis for a supported conservative boundary. Use ls-tree metadata first; preserve snapshot, mode, type and object ID for non-blob entries and explicitly record content as unavailable/not-applicable rather than reading a foreign commit. Add an isolated Gitlink addition/type-change case whose foreign target is absent, plus a symlink case to preserve separate behavior. The accepted execution plan must remain unchanged.

## Non-blocking completeness notes

- receipt_observation:100 defaults absent duration_seconds to 0 and then publishes per-module cost. Since missing evidence must remain distinguishable from a measured zero, expose missing-duration IDs/cost completeness and sum only supplied valid durations. No savings claim is currently made, so this is not an authority bypass.
- inputs[].versions currently preserves only mode and SHA256 (line 131). Explicit snapshot labels and Git object IDs would make additions/deletions/mode changes directly auditable and also support the non-blob fix above.
- The documentation says routing patterns use exact paths or * / ** (DOMAIN_MODEL.md:15), while fnmatchcase also accepts ? and lets * cross path separators. Either define the intended fnmatch semantics explicitly or restrict the accepted grammar; do not silently introduce a separate future exclusion-glob interpretation.

## Scope and confidence

This is a static code review, not proof of passing historical replays or coverage. Four current tests cover authority injection, overlapping routing, partial outcome validation and one real Git archive/executable case. They do not yet cover the three findings above. Current source also correctly leaves candidate selected/skipped, actual coverage/smoke comparison and independent exclusion witness unimplemented; these remain 2B/2C obligations rather than defects in the limited 2A scope.

## Final disposition after repair review

Rechecked only the corrected producer bindings, CLI output/input protection, non-blob Git handling, receipt-duration handling, snapshot labels and corresponding regression additions.

- CLOSED: ci_domain_audit.py:153-156 now binds seven producer files, including the dynamically executed governance helper and the imported consumer-contract helper. The Git regression asserts the governance entry is present.
- CLOSED: ci_domain_audit.py:177-181 rejects resolved path equality and existing hardlink aliases for plan, model and receipt before reading or writing. The regression verifies plan overwrite is rejected and original bytes survive.
- CLOSED: ci_domain_audit.py:131-141 reads only blob objects. Non-blob entries preserve snapshot/mode/type/object ID and explicitly carry unavailable content/null SHA256. The regression adds a foreign Gitlink whose target is absent and checks it remains an unknown input rather than aborting.
- RESOLVED OPTIONAL NOTES: missing case durations now have explicit IDs and case_cost_complete=false; per-module sums include only supplied durations. Each changed version now has an explicit snapshot label and Git object identity.

No remaining blocking finding in this bounded 2A delta review. This disposition is based on code inspection, not an independent rerun of root's focused tests or historical replays. The separate 2B/2C activation, execution evidence and performance gates remain unchanged. Pattern semantics was a non-blocking documentation note in the initial review, outside this requested repair delta.
Reviewed ci_domain_audit.py SHA256: 285924bcf37f14a7912e453fb212c5d5c5ebfc82f6c608f695ebbe6fdc4cf17f
Reviewed test_ci_domain_audit.py SHA256: eb722cd6d475390ba31d936782745fc5100b730e47e2cc8e5f83de53623c16bd
