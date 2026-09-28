# M14-005 candidate-install diagnostic attempt

Owner: Chengyue-Lu. Baseline: accepted `develop@39cf61e9fc728a2a6c1494b7a641a011dd6bf114`.
This R2 slice extends the dormant release-only diagnostic. It does not create a release
branch, activate topology, change remote protection, merge to main or publish a tag.

The accepted source's protected push CI run `36446927798` completed successfully;
clean exact-source live `attest` passed and is retained in `tool-events/source-attestation.json`.
The new workflow calls one source-owned diagnostic per Python version. It binds live
source CI, independent source/main/candidate/manifest inputs and public build closure,
then builds a verified projection outside checkout. Direct wheel and sdist-derived wheel
are each installed into fresh environments for no-Skill Runtime/Registry/Projection,
Quickstart and scaffold checks. The result is diagnostic and never merge authority.

Local 3.11 and 3.13 actual portable smoke results are retained separately. They are
source package checks, not real first-main candidate observations. The first-main
hosted trigger, ruleset cutover, source/main freeze, real candidate and release decision
remain future M14-005 gates. Verification details are in `outputs/VERIFICATION.md`.

The visible tool-call stream was not captured exhaustively. The indexed Trace therefore
records a capture gap and retains the decisive exact-result files. No hidden reasoning,
credential or authentication token is archived.
