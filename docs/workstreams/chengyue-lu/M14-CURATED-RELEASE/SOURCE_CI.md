# M14-005 source CI preparation

- Owner: 路诚钺 (`Chengyue-Lu`); R2; Task M14-005 is READY in this candidate under the
  [named v0.1.0 preparation decision and fresh protection readback](FIRST_RELEASE_DECISION.md).
- Original integration baseline: `171d4654f88e926f239cdf25bc8168109b81f391` (2026-09-21 rebase).
- M0-007 was accepted in [PR #78](https://github.com/Chengyue-Lu/research-agent-workbench/pull/78).
  [PR #79](https://github.com/Chengyue-Lu/research-agent-workbench/pull/79) accepted the separate hard/review rulesets.
- Scope: the develop-side source-CI producer and live observer. Release-only checks, their policy include,
  topology cutover and the first release remain subsequent slices of the same Task.

## Producer

The `CI` workflow runs `source_governance` only for a push to exact `refs/heads/develop`, checked out at the
push SHA. Its check is named `governance`. On other events the inactive job has a different name, so its
skipped result cannot shadow the independent PR `CI governance` check.

`release_source_ci.py governance` authenticates the repository and retrieves the unique merged PR whose
merge commit equals the pushed source. It requires same-repository head/base, a single source parent,
the PR base equal to that parent, and the reviewed feature tree equal to the integrated source tree.
It then invokes the existing governance checker on the **actual parent → squash-source delta**, using the
current merged PR body. An absent association, non-squash integration, metadata/Task/policy violation or
tree mismatch fails the source check. Running the ordinary PR checker on a push and accepting its no-op
exit is insufficient.

The job publishes `source-governance.json` only after success as an **audit artifact** recording its
governance result. Trust comes from the successful same-source governance job in the authenticated `CI`
run, together with the existing complete integration tests. The PR metadata is a fresh API
observation, not a reconstruction of the body as it existed at merge time; later incompatible body edits
can therefore block a rerun. They must be reconciled explicitly in the accepted PR record.

## Live observer

From an accepted, clean source checkout, fetch current remote history and choose the exact source and
CI run being assessed. The observer requires its own bytes to match the source, the checkout HEAD to
equal that source, and source ancestry in the freshly observed protected develop branch.

```text
python .github/scripts/release_source_ci.py attest --repository OWNER/REPO --source FULL_SOURCE_SHA --run-id CI_RUN_ID --output NEW_CALLER_OWNED_PATH.json
```

The command uses `gh` authentication with read access to repository contents, Actions and Checks. It
always queries `github.com` through fixed read-only API paths. Its observations require:

- exact repository name and numeric identity, including the run's head repository;
- the active `CI` workflow's numeric identity and `.github/workflows/ci.yml` path;
- a successful completed **push** run on `develop`, with the exact source SHA;
- every expected source job from the run's latest attempt, including governance, both Python aggregates,
  both compatibility suites, coverage, documentation, repository validation and both package checks;
- successful, unique jobs bound to that run/attempt/source, and matching check runs from GitHub Actions
  app ID `15368`, in that run's check suite;
- complete pagination, followed by a second run observation that rejects a concurrent rerun/state change.

PR merge rehearsals, dispatch runs, green jobs from another attempt or workflow, duplicate names, skipped
checks and a missing governance producer fail closed. If a partial rerun omits required jobs from the latest
attempt, rerun the complete workflow; evidence from separate attempts is not combined.

The result separates `source_ci` (the existing release-manifest expectations shape) from the audit
`observation` (repository/workflow/attempt/suite/job/check IDs). It reports `merge_eligible: false`.
The future protected release caller must perform this live observation itself and pass the resulting
`source_ci` to the exporter; a saved JSON file, candidate manifest or PR claim cannot substitute for that
call. Authentic source CI alone grants neither release readiness nor release authority.

`attest` does not download, hash or validate `source-governance.json`. That producer receipt is a separate
audit attachment, not an attestation input or an exporter trust token. Downloading it helps inspect the
producer's recorded metadata/delta, but a matching receipt cannot make a rejected live graph valid.
Any future protected caller that uses its contents as a machine input must separately specify and verify
the artifact's run/attempt/source binding, hash and content; that integration is not implemented here.

API contracts: [workflow runs and attempts](https://docs.github.com/en/rest/actions/workflow-runs),
[workflow jobs](https://docs.github.com/en/rest/actions/workflow-jobs),
[check runs](https://docs.github.com/en/rest/checks/runs), and
[commit-associated PRs](https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit).

The transport pins REST API `2022-11-28`, whose supported PR response includes the required
`merge_commit_sha` identity. GitHub [removed that field in `2026-03-10`](https://docs.github.com/en/rest/about-the-rest-api/breaking-changes#version-2026-03-10)
from both associated-PR and PR-detail responses; switching only the header makes the producer reject every
source. The [supported-version schedule](https://docs.github.com/en/rest/about-the-rest-api/api-versions#supported-api-versions)
lists support through 2028-03-10. A future migration must establish an authenticated replacement identity
and exercise the transport and response schema together. Missing identity still fails closed.

## Acceptance and next integration

Deterministic fixtures exercise the actual squash-delta governance checker and separate live-observer
identity/attempt/App rejection cases. The observer is a critical coverage surface with 95/90 thresholds
and independent positive/negative evidence. Existing full integration, package and coverage gates stay active.

An implementation PR could not prove its own post-merge develop push producer: that workflow first ran
after R2 acceptance into develop. The repaired source has now been integrated and its actual protected
push and clean exact-source online `attest` have passed. The [accepted-source audit pins](SOURCE_CI_ACCEPTANCE.json)
retain the source SHA, push run/attempt, workflow and check-suite IDs, required job/check-run IDs and
GitHub Actions App identity. The [original attestation output](SOURCE_CI_ATTESTATION_07083b8.json)
is preserved byte-for-byte with its SHA-256 in that record. These files record a historical live
observation, not a reusable trust token.
The producer receipt was retained separately for audit inspection; `attest` did not consume it. A
previously green develop run without the source-governance job remains a negative control.

Engineering evidence: [Attempt index](../../../../work/M14-005/A-20260915-003/INDEX.yaml) and
[verification](../../../../work/M14-005/A-20260915-003/outputs/VERIFICATION.json). Capture gaps and the rejected
initial archive preflight are retained; final-head hosted CI and review receipts belong to the implementation PR.
The [review correction Attempt](../../../../work/M14-005/A-20260915-004/INDEX.yaml) retains the named READY
decision, fresh protection readback and receipt-semantics correction; prior frozen records retain their original scope.
The [previous rebase Attempt](../../../../work/M14-005/A-20260916-001/INDEX.yaml) retains upstream Gate B/CI planner/M6 integration.
The [current rebase Attempt](../../../../work/M14-005/A-20260921-001/INDEX.yaml) retains the M5/CI baseline,
semantic STATUS/coverage conflict resolution, protection readback and the gated next-step plan.

PR #80 was accepted as `ea7d6c8cb619b392f79be439fc1ee214f6928cd9`. Its first protected push
[35536949452](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35536949452)
exposed the API-version mismatch above. The [contract repair Attempt](../../../../work/M14-005/A-20260921-002/INDEX.yaml)
retains the failing regression, supported live responses and bounded maintainer authorization.
PR #97 accepted the transport repair as source
`07083b8275616d95357c97ee19c674f869f5862e`. Its actual protected-develop
[push run 35814704926](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35814704926)
completed successfully at attempt 1; the accepted source's clean, full-history online `attest` passed.
The audit pins above preserve the source/workflow/run/suite/jobs/App observation without replacing the
fresh live check required of any future release caller.

Next: review the [trusted release preflight](RELEASE_CHECKS.md), then implement the trusted release-only
workflow and first-main bootstrap, the new append-only policy include, candidate public/install checks,
and the separately reviewed atomic topology cutover. The named first-release decision authorizes
implementation/cutover preparation; final release PR and tag require separate approval. M14-005 remains
READY, while release eligibility and topology remain dormant.
