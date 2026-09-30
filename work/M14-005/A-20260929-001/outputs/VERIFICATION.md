# Verification record

The exact-source online `attest` succeeded for protected `develop@39cf61e9fc728a2a6c1494b7a641a011dd6bf114`
and full/source CI run `36446927798`; `tool-events/source-attestation.json` retains
repository/workflow/run/attempt/job/check binding. It says `merge_eligible: false`.

The source package smoke built direct wheel and sdist→wheel in external temporary
directories and installed each route in fresh environments on Python 3.11.16 and
3.13.15. Both reports show four successful route/isolation probes, identical Runtime
assets, 155 resources, 106 Schemas, zero production Projections, no-Skill Quickstart
and matched bounded offline reconstruction. See `tool-events/portable-source-*.json`.

Final local focused run: 79 tests PASS across release install, public checker,
portable build, trusted preflight, release surface and documentation;
`tool-events/focused.log` retains the command output. Critical
`release_install.py` test coverage is 100% line and 100% branch in
`tool-events/install-coverage.json`; six focused coverage tests passed.
Repository validation returned `validated=186 errors=0 warnings=0`.
Workflow matrix/pin behavior and append-only policy are exercised by the
focused tests. `git diff --check` passed.

An uninstrumented repository-wide coverage-quality run began before the last
implementation changes and was interrupted because its result could no longer
represent the final HEAD. It is not reported as a passing check. The review PR's
exact-head CI must provide the full/coverage/dual-Python hosted evidence.
The local source smoke does not substitute for an actual candidate-bound hosted
first-main check.
