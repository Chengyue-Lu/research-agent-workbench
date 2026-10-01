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

[PR #102](https://github.com/Chengyue-Lu/research-agent-workbench/pull/102) accepted
`.github/workflows/release.yml` and the source-owned
`.github/scripts/release_public.py` in append-only surface policy `1.3.0`. The workflow
only responds to a `release/v*` pull request targeting `main` and uses externally
maintained repository variable pins for the exact source, main parent, policy version,
source-CI run and independent manifest SHA-256. Unset pins fail before checkout. It
checks out the pinned develop source, fetches the candidate **as Git data**, runs the
accepted preflight, then checks public links, internal paths and build inputs without
executing candidate code. Both receipts have `merge_eligible: false`.

This workflow was named `release preflight (diagnostic)` in PR #102 and is not a required status
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

## Candidate installed-package diagnostic

PR [#108](https://github.com/Chengyue-Lu/research-agent-workbench/pull/108) appended surface policy `1.4.0` and extended that diagnostic
workflow to Python 3.11 and 3.13. Each matrix run invokes source-owned `release_install.py`,
which performs live source-CI preflight and candidate public checks, verifies its own and
`portable_package_smoke.py` bytes against the accepted
source, reconstructs the exact candidate projection outside checkout and checks the
independent manifest pin and complete Git tree before any build backend executes.

From that projection, the portable smoke builds a direct wheel and an sdist-derived
wheel in temporary directories. It compares packaged Runtime assets and license bytes,
installs both into fresh virtual environments, and runs isolated and poisoned-path
no-Skill Quickstart, Registry, Projection and scaffold/reconstruction probes from empty
project directories. Missing or corrupt packaged resources fail closed. After installation,
the source-owned wrapper reobserves protected refs and the complete CI attempt. Its
receipt embeds the preflight/public/install observations and remains `merge_eligible: false`;
neither this diagnostic nor PR CI replaces an
independent exact-source run on the actual first-main candidate.

## Cutover preparation after PR #108

PR #108 was independently approved and squash-merged as `develop@3189049` with the
same tree as its reviewed head. Its protected push [CI 36662594652](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36662594652)
passed, and a clean exact-source live `attest` of that run passed. These are accepted
source facts, not a release source freeze or a first-main observation.

The next R2 preparation changes the matrix job name to `release preflight (3.11)` /
`release preflight (3.13)` and removes the job-level branch `if`. Every main-bound PR
therefore reaches the first-step same-repository/version/pin guard; a non-release head
fails instead of producing a skipped check that a ruleset could treat as satisfied.
The release topology remains dormant, and main's current required checks are unchanged.

The source-owned `release_ruleset_cutover.py` prepares a **read-only** single-ruleset
payload for the later main hard-gate swap. It requires a clean accepted develop source,
fresh protected source/main refs, live source CI before and after four active hard/review
ruleset and effective-rule readbacks, the exact GitHub Actions App check identities, and
the existing main reviewer/merge rules. It writes the old and proposed payloads with
hashes and `applied: false`; it never updates GitHub. A future writer must independently
reobserve the prestate immediately before the one main-hard-ruleset update and stop on
any drift. The payload and its green tests do not themselves activate release eligibility.
The current readback and non-authorizing payload are retained in the
[cutover preparation Attempt](../../../../work/M14-005/A-20260930-001/INDEX.yaml).

## Following slices

### First candidate diagnostic (2026-10-01)

[PR #115](https://github.com/Chengyue-Lu/research-agent-workbench/pull/115) was
cross-owner approved and merged as `develop@cebae4b3d9116d750b5573afce77a3e0bfd2b12f`.
Its actual protected [push CI run 36791544994](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36791544994)
completed successfully, and a clean exact-source live attestation passed. From that
source and `main@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`, the first
candidate was built on `release/v0.1.0` at
`4d7df013277124b1721f3a5d93f2f15d64d3f2e5`; its manifest SHA-256 is
`57cd04184fb17210f504c946a1e46213857870e46343ec3b75e0a77c724d1677`.
Source-owned double projection, preflight, public check and local Python 3.13 package
installation passed. Draft [PR #116](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116)
triggered actual [first-main hosted run 36797275971](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36797275971):
both Python 3.11 and 3.13 diagnostic checks passed. The workflow and validator blobs
in the PR merge ref match the frozen source, and all four remote rulesets and both
effective-rule views were read without mutation. Every receipt still reports
`merge_eligible: false`; the PR remains a blocked draft.

The independent PR-governance replay exposed a develop-side issue: policy correctly
omits `docs/TASKS.md` and `docs/workstreams/**` from the public candidate, but the
governance checker still read them from its head. This yields `TASK-READ` and
`WORKSTREAM-EVIDENCE` in addition to the expected dormant/missing-expectations errors.
The proposed fix reads declared Task IDs and R2 workstream evidence from the trusted
source only after release prerequisites validate; an untrusted attempt still fails
closed without reading development-only candidate documents. This correction requires
its own develop PR and accepted source CI, followed by rebuilding the candidate and
refreshing external pins before any cutover. The first diagnostic candidate and its
run remain evidence, not the final releasable source.

The source API repair was accepted in PR #97. Its real protected develop
[push run 35814704926](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35814704926)
and clean exact-source online `attest` passed; the [historical observation pins](SOURCE_CI_ACCEPTANCE.json)
are audit evidence only. The remaining slices are:

1. Review and accept the develop-side governance correction; observe its protected push
   CI, then rebuild the candidate from that exact source and refresh the external pins.
2. Repeat source-owned and hosted first-main checks on the rebuilt candidate while
   the old required checks continue to block merging.
3. With R2 review and fresh readiness evidence, activate the governed release topology and
   replace the main hard ruleset's old required contexts in one update; re-read effective
   rules and prove direct `develop -> main` remains blocked. A failed or ambiguous update
   requires fail-closed reconciliation before any release merge.
4. Obtain separate final release-PR merge approval, then close tag/artifact/hash evidence.

This implementation slice creates no release branch or tag and changes no remote protection settings.
The small API repair's review waiver does not apply to this subsequent R2 change.
