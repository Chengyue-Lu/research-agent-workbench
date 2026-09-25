# M14-005 trusted release preflight

PR #98 accepted this source-owned entry point for release-only checks. It joins the
[live source observer](SOURCE_CI.md) to the accepted deterministic exporter/checker.
M14-005 remains READY and the release topology remains dormant.

Run from the clean, exact accepted develop source after fetching origin. Supply the source,
current main parent, policy/release versions, source CI run, candidate commit and independently
reviewed manifest SHA-256 explicitly. The candidate manifest cannot supply these trust inputs.

```text
python .github/scripts/release_preflight.py --repository OWNER/REPO --source SOURCE_SHA --parent MAIN_SHA --policy-version POLICY_VERSION --release-version VERSION --run-id SOURCE_CI_RUN --candidate CANDIDATE_SHA --manifest-sha256 MANIFEST_SHA256 --output NEW_AUDIT_PATH.json
```

The entry point binds its checker dependency bytes to the accepted source, authenticates fresh
protected develop/main tips, and obtains live source-CI evidence. It projects twice from Git blobs
into independent temporary directories outside the source checkout, checks the independent manifest
pin, and validates the candidate's exact parent, complete tree and prospective merge result.
Candidate code is never checked out or executed. Protected refs and the source-CI observation must
still agree after the checks; drift or a concurrent CI rerun invalidates the attempt.

The caller-owned audit file is created only after all checks pass and cannot overwrite an existing
file. It reports `merge_eligible: false`. Reusing that file does not perform fresh verification or
grant release authority. Fresh branch-protection flags are preliminary observations; actual cutover
still requires the full hard/review ruleset and effective-rule readback.

Tests combine real Git projection/candidate fixtures with controlled live-observer responses; the
source-CI suite separately exercises the authenticated API contract. These deterministic tests do not
claim that a real release candidate or integrated-source preflight has been accepted.

## Diagnostic first-main workflow preparation

The next develop-side slice adds `.github/workflows/release.yml` and the source-owned
`.github/scripts/release_public.py` to append-only surface policy `1.3.0`. The workflow
only responds to a `release/v*` pull request targeting `main` and uses externally
maintained repository variable pins for the exact source, main parent, policy version,
source-CI run and independent manifest SHA-256. Unset pins fail before checkout. It
checks out the pinned develop source, fetches the candidate **as Git data**, runs the
accepted preflight, then checks public links, internal paths and build inputs without
executing candidate code. Both receipts have `merge_eligible: false`.

This workflow is named `release preflight (diagnostic)` and is not a required status
check. The first candidate may supply the workflow file in its PR merge ref; therefore
its own result cannot authenticate its bytes or grant release authority. A reviewer
must independently run source-owned preflight from a clean accepted develop checkout,
verify the projected workflow and validator blobs against the frozen source, and check
the actual GitHub run and effective rules. GitHub documents that `pull_request`
workflows run from the PR merge commit, while `workflow_dispatch` requires the file
on the default branch ([event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[manual-run reference](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)).
The first-main hosted trigger and protected ruleset transition remain unproven until
the separate R2 cutover; the current dormant topology and main hard gates still block
release merging.

## Following slices

The source API repair was accepted in PR #97. Its real protected develop
[push run 35814704926](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35814704926)
and clean exact-source online `attest` passed; the [historical observation pins](SOURCE_CI_ACCEPTANCE.json)
are audit evidence only. The remaining slices are:

1. Obtain R2 review of the diagnostic workflow, first-main trust boundary, candidate public checker
   and exact append-only policy include. Hosted first-main behavior still needs a real observed run.
2. Add dual-Python checkout-outside clean-install and no-Skill/Registry/Projection evidence to the
   release-only workflow. Only then prepare and review atomic topology activation and direct-develop-path closure.
3. Freeze the release source/current main parent after readiness, generate the real release candidate,
   and obtain the separate final release PR/tag/artifact decision.

This implementation slice creates no release branch or tag and changes no remote protection settings.
The small API repair's review waiver does not apply to this subsequent R2 change.
