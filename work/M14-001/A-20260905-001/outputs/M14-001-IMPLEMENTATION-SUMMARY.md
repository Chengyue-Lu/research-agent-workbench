# M14-001 implementation summary

- implementation commit: `e560dbc`
- stacked baseline: PR #58 head `12d05dd130c718dd179e011292f9ada9f97bdf74`
- branch: `feature/m14-release-foundation`

M14-001 adds a strict declarative, dormant curated-release topology and keeps every `release/vMAJOR.MINOR.PATCH -> main` candidate fail closed until M14-005. Structural topology matching is explicitly not release authorization.

The checker now separates and validates:

- strict branch syntax, same-repository identity, release class, and automatic R2 risk;
- protected-caller source repository/ref/SHA and exact required-CI attestations;
- exact current-main parent, merge base, root parent, and merge-free release history;
- raw `RELEASE_MANIFEST.json` byte hash against an external expectation;
- immutable dormant activation state that cannot be weakened through policy data.

PR body, branch name, manifest claims, and ordinary process environment cannot manufacture trusted expectations. Exact same-repository `develop -> main` remains the only executable release topology.

M14-002 through M14-005 remain outside this implementation: no allowlist, manifest Schema, exporter, projection/tree comparison, package/runtime-resource boundary, public documentation projection, real release branch, authenticated GitHub observation, readiness cutover, merge, or tag was created.

Local evidence on the tested implementation tree:

- focused governance/documentation: `122/122` pass;
- full behavioral suite: `811` total, `810` pass, `1` Windows privilege skip, no failures/errors;
- coverage-quality: `750` total, `749` pass, `1` Windows privilege skip, no failures/errors;
- global line coverage `91.53%`;
- governance checker `97.31%` line / `96.58%` branch;
- repository validation `183/0/0`;
- package smoke: wheel build/install, `63` installed Schemas, installed validation `183/0/0`, and empty-CWD import pass.

Hosted Python 3.11/3.13, exact PR-event governance, and cross-owner R2 review remain pending until PR #58 merges and this branch is rebased onto the then-current `develop`.

The accompanying Attempt Archive is encoded as Agent Trace v0.1 with `safe-paused` / `frozen` / `gapped` status. Reconstructed or compacted transfers and missing early tool/event streams remain explicit capture-gap warnings and are not promoted into completion evidence.
