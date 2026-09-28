# M5-007 H5 draft implementation

Date: 2026-09-28. Owner: Chengyue-Lu. Reviewer: let778750-cpu. Risk: R2.
Agent: codex-m5-h5; bounded integration and independent replay; Skills: [].
Scope and capture policy: [TASK](TASK.md). Accepted task boundary: [H5 packet](../../M5-007_H5_PACKET.md).
Entry source: `34a4b05cacbce81459720c3363ef781a55334b42`; develop: `24e1a3eb5d503e56868a10d5222b79ad544e3f86`.
PR104 is not yet R2 accepted. This dependent draft does not mark H5/M5-007 accepted or DONE.

Retain the real local synthetic four-arm chain, one transient failure/fresh retry, the blind
synthetic rubric and complete metric/pairing closure. All 13 metrics remain unavailable/null;
synthetic ratings do not establish research performance or real Human review.

Validation outputs and exact inventory pins will be retained here. The cold replayer consumes
the caller-selected inventory reference and trusted repository helper/validator code. Historical
proof replay requires its pinned source/schema environment; future source drift requires a new
proof, never rewritten historical bytes. Active tests build fresh inputs for their current source.

Capture is partial: intake, early reads, branch creation, patch operations and publication messages
are not a complete native Agent Trace. Logged command evidence does not erase this capture gap.

## Durable proof and replay

[vertical-proof.zip](vertical-proof.zip) preserves 454 original files (1,699,987 uncompressed bytes;
607,567 archive bytes). [proof-refs.json](proof-refs.json) pins the ZIP and the caller-selected
[inventory](proof-inventory.json); the same inventory bytes are inside the ZIP.
Archive SHA-256: `176c47b3ebbc8e71d3cdb27f835d82a8e5af2ac876638d7ca7d0c7601a063b2d`.
Inventory SHA-256: `c794fabd85e79cca382c03465f5cf9b2065c642fd2bcf4eb869fd173bb0c240f`.

Run from the trusted source checkout matching the embedded production/Schema/helper identities.
Verify the ZIP hash with `rwb hash <archive-path>` before extracting to an empty short directory,
then invoke the developer replayer with the original inventory reference. Do not calculate a
new inventory hash from untrusted replacement bytes or execute source files inside the proof.
The ZIP keeps deep Attempt paths portable across Windows checkouts without rewriting records.

```text
python -m zipfile -e <verified-archive-path> <empty-short-directory>
python -m tests.harness_proof replay --root <short-directory> --schemas schemas --inventory-ref '{"path":"proof-inventory.json","sha256":"c794fabd85e79cca382c03465f5cf9b2065c642fd2bcf4eb869fd173bb0c240f"}'
```

[Archived cold replay](evidence/archived-cold-replay.log) passed in 74.891 s: 8 cells / 4 arms,
10 pairs under the frozen Protocol, 8 completed Attempts, 1 post-call failure and 7 planned
not-started retries. The failed cell retains retry indexes 0 and 1 with different Attempt IDs.
All 13 metrics remain unavailable/null, and primary_confirmatory_eligible is false.
Archive verification compared each ZIP member to its original file pin before extraction.

## Validation and remaining acceptance

- [Final chain tests](evidence/focused-final.log): 7 PASS in 424.229 s; original byte drift,
  resigned result/eligibility upgrade, failed-Attempt deletion, source/Schema drift, freeze time,
  and admission/Human/measurement refusal. After this run, the combined Schema/guard case was
  split into independent test methods; [current cold guards](evidence/cold-guards-final.log)
  separately PASS, including DNS, UDP socket creation, subprocess/os.system and proof code.
- [Docs/CI mapping](evidence/docs-ci-final.log): 25 PASS. H5 is registered in the evaluation
  component and all seven direct fixture/helper consumers select its tests.
- [Repository](evidence/repository.log): 186 checked / 0 errors / 0 warnings.
- [Installed smoke](evidence/package-smoke-results.json): 8 steps PASS, 9.922 s. The existing
  isolated wheel environment has [106 identical production modules and 106 identical schemas](evidence/installed-source-equality.log).
  No product source/schema changed in H5; this is an equality-checked reuse, not a new wheel build.
- [Proof-only coverage](evidence/proof-coverage.json) is diagnostic: build plus archived cold
  replay cover 92/98 helper statements and 176/222 analysis statements; negative tests are not
  included in that measurement. H4c's existing 222/222 statements / 52/52 branches remain
  historical scoped evidence on the identical production source, not a new H5 full coverage run.
- [Local candidate governance](evidence/governance-final.log): PASS, effective R2. This is a
  post-freeze check; the original frozen Trace remains unchanged. The first local governance
  import harness lacked its dataclass module registration and failed before invoking the checker;
  that diagnostic is retained separately from the successful check.

The first chain run retained 5 PASS / 2 failed assertions: a hardcoded 6-pair expectation
ignored two frozen secondary contrasts, and one combined forgery expected reconstruction
before the Schema's false-eligibility guard. Final tests derive contrasts from Protocol and
exercise numeric forgery and eligibility separately. The first archive-directory generation
failed at Windows path length 206; its incomplete local spool is preserved outside the archive.
A short-root build passed in 230.578 s; the final ZIP retains those exact successful bytes.
The local logger's first error output also hit legacy console encoding; original bytes survived,
and later native commands use UTF-8. These diagnostics are not acceptance results.

[Input pins](INPUTS.json), verification.json and the gapped Trace bind the retained evidence.
Hosted component CI/governance and H4c/overall R2 acceptance remain pending at draft publication.
No M5-007 DONE, Issue55 closure, live Gate change or merge is authorized by these results.
