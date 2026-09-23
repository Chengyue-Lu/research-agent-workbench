# CI follow-up evidence

Implementation `b1199d28913b4f5b134f0d6cbb54c9f2c9c26596`; accepted base `171d4654f88e926f239cdf25bc8168109b81f391`.

The raw acquisition report below describes its original pre-commit state; source hashes bind it to this implementation. Hosted CI and human acceptance are separate.

# Named diagnostic input regression

Owner: Chengyue-Lu. Task TEST-PERF-002. Skills [].
Commit `b1199d28913b4f5b134f0d6cbb54c9f2c9c26596`, parent `09c6cb1c82680233c369014e0831874b6702d3b7`, branch `feature/ci-domain-model`. Working tree clean.

The prior four tests exercised synthetic models but did not validate the real named JSON. This change adds one five-line test, `DomainModelTests.test_named_repository_model_satisfies_official_validator`, reading `ROOT / audit.MODEL` bytes and using the exact duplicate-key hook and validator used by the production CLI. It does not construct another plan or report. It does not pin domain count, owner text, or a fixed model hash. Existing four methods are AST-identical. DOMAIN_MODEL.md adds five lines describing this actual-input boundary.

No production file or official model byte changed. The named model remains `454443ea5295fe70b2ed9cf83624dc59376aa2f96c7d54b9b4df015e4d40b0c1`. No selector, classification, policy, threshold, smoke or exclusion permission changed, and PR92 was untouched.

## Validation

| Actual interpreter | Suite | Result | Native wall | Process wall |
| --- | --- | --- | ---: | ---: |
| 3.11.16 | 5 domain + 10 documentation | 15 PASS, 0 skip/error | 4.988429 s | 5.113343 s |
| 3.13.15 | 5 domain + 10 documentation | 15 PASS, 0 skip/error | 4.831126 s | 4.945967 s |

Native documentation checks include all internal Markdown links and public build/documentation boundaries. Exact source hashes and commands are in validation.json and each preflight/process record. No full suite or coverage run was needed or claimed for this local check; hosted required CI will run for the updated PR head.

`mutants.py` cloned exact parent into a disposable Git tree and copied only the final test file. It then overwrote the actual `docs/workstreams/chengyue-lu/TEST-PERF-002/domain-model.json` path, without patching ROOT/MODEL, loader, parser or validator, and ran the new method in a fresh real Python process:

- Normal exact bytes: PASS.
- `execution_authority=true`: fails with `cannot grant execution authority`.
- Nonempty pilots: fails with `separately reviewed protocol`.
- Duplicate version key: fails with `duplicate policy key: version`.

Each variant's exact JSON, subprocess argv/cwd/exit, log and hash is retained. The snapshot model was restored afterwards; the formal worktree model remained unchanged throughout. These are actual named-input faults, not synthetic model-only checks. Earlier named-input-audit retains the separate real-CLI controls and the proof that the old four methods missed a corrupted actual file.

Initial authoring evidence (`initial.log` plus its source snapshot) records an incorrect expected duplicate-key error label in a larger CLI harness. The production parser rejected that input correctly. The final minimal test uses the same parser/validator directly and the isolated controls above retain its actual exception. No failure log was overwritten.

Independent reviewer output is REVIEW.md with its separately maintained reviewer-sha256.json. The reviewer inspected the actual path, strict parse/validator calls, old-method preservation and the retained real-path controls; no source was changed by review. Root owns A-20260920-008 archival and PR91 update. This task did not push, change Ready state, create a PR or produce Trace records.

## Retain / exclude

Retain all top-level JSON/logs/scripts/review files, the four `*-model.json` control files, source snapshots and the final two source files by commit. Exclude the disposable **snapshot/** Git clone from the formal archive: its exact parent plus copied final test and all model variants/logs/commands are already preserved. Also exclude __pycache__ and .pyc. No venv was created or modified.

Final changed-source hashes:

```json
{
  "tests/test_ci_domain_audit.py": "22e39bc2072486f4d24d73fc06332150fa21c31521a54be48ffacd51101669ba",
  "docs/workstreams/chengyue-lu/TEST-PERF-002/DOMAIN_MODEL.md": "5c72960545f2e6f0df9528553c71abe867864d8f15bc54ba604f3f4822a7de04"
}
```
