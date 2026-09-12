# M14-004 final Quickstart integration

- Owner: Chengyue-Lu; cross-owner R2 acceptance remains required.
- Base: `451644064f558601d5778b9b115390f882f4d260`, the accepted M1-009 merge from PR #74.
- Implementation: `3591043fb870582ae674e1ac9ce994a0bc9675b3`.
- Attempt: [A-20260912-001](../../../../work/M14-004/A-20260912-001/WORKLOG.md).

## Scope and acceptance

PR #69 accepted the public navigation, evidence vocabulary, support matrix, versioned build-input surface
and development-side link checks. This slice completes Getting Started using the accepted scaffold:
installed Runtime checks → no-Skill initialization and input validation → offline-demo initialization →
manifest/hash evidence location → explicit Run reconstruction → report validation.

README links to the canonical steps; Supported Features keeps the single support/evidence matrix.
The example remains a synthetic integer recurrence with a retained zero-net-change result.
Initialization writes reference files; only the explicit reconstruction command creates current execution evidence.
No Runtime, Method, Claim, Provider or release authority semantics change.

The link checker now distinguishes generated user Attempt paths in prose/commands from repository archive
links. Relative, encoded, reference-style and external archive links are still rejected, even if the target
file exists. Existing excluded-file selection, internal navigation, source-byte and build-input rules remain.

## Verification

The local acceptance experiment uses a temporary Git fixture and exact implementation Git blobs, then
exports policy `1.1.0` twice. The fixture's source-CI assertion is synthetic; it is not a release attestation
or a freeze of the real release source. Both 257-file trees are byte-identical, public links/build inputs close,
and every selected product source and Schema preserves its source bytes.

The accepted portable-package harness builds direct wheel and sdist-to-wheel from that projected source.
It executes the guide's 12 `rwb` commands and one project-directory change using each installed interpreter,
under isolated and poisoned-CWD/PYTHONPATH setups. The retained evidence binds the exact guide hash,
command list, Runtime closure and result counts. The corruption/fallback negative probe remains enabled.

The local matrix passed all eight installations: Python 3.11.16/3.13.15 × direct/sdist-wheel × isolated/poisoned.
Each ran all 12 CLI commands successfully, produced a `matched` executed report and retained the negative result.
Both routes contain identical Runtime assets (132 resources, 84 Schemas, 4 Modes, 0 Projections).
Documentation/public-surface/governance focused checks passed 103 tests; repository validation returned 186/0/0.
Current-candidate hosted results are recorded separately in the PR Verification evidence.
The documented route requires no manual Registry/Profile/Skill copying, Provider credentials or generated-file
edits. This deterministic walkthrough records configuration/correction counts; it does not measure human
completion time, general usability or scientific net benefit.

## Completion proposal and remaining gates

M14-004: READY → DONE, with its original identity, dependencies, owner and acceptance unchanged.
Current-candidate CI and cross-owner R2 review must accept this proposal before integration.

M14-005 remains BLOCKED. Its remaining readiness decisions include M0-007 license, actual GitHub remote
protection and a named Human release decision. This slice does not configure protections, activate release
topology, create a release branch/tag or perform a release. The primary local `develop` checkout stays unchanged.
