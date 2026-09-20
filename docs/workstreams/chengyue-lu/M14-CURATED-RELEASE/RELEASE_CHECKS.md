# M14-005 trusted release preflight

This slice prepares the source-owned entry point for release-only checks. It joins the
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

## Following slices

1. Accept the source API repair and verify its real protected develop push with online `attest`.
2. Review this source-owned composition. Wire a trusted release-only workflow to it, prove the first-main
   bootstrap trust anchor, and add the exact required workflow/public validator includes in a new
   append-only release-policy version. Candidate-controlled workflow code must not provide its own trust.
3. Add candidate public-link/build-input closure and dual-Python clean-install evidence to that workflow.
   Only then prepare and review atomic topology activation and direct-develop-path closure.
4. Freeze the release source/current main parent after readiness, generate the real release candidate,
   and obtain the separate final release PR/tag/artifact decision.

This implementation slice creates no release branch or tag and changes no remote protection settings.
The small API repair's review waiver does not apply to this subsequent R2 change.
