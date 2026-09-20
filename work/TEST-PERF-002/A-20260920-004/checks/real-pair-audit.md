# Independent real provider pair artifact audit

Date: 2026-09-20. Owner: Chengyue-Lu. Reviewer: domain_plan_review / CI evidence reviewer. Bounded read-only audit of coverage-pilot/HANDOFF.md, provider-positive/short-temp-pair, retained earlier failure summaries/hashes, and the current offline comparator. No fresh tests, coverage collection, smokes, source changes or Git mutations.

## Disposition

**No material blocker found in the requested evidence slice.** The artifacts support one local Python 3.11 historical provider control pair with zero exclusions. They do not establish current-base reduction, hosted savings, critical 95/90, repository-wide coverage or 2C activation.

## Verified

- **52/52** files in the successful pair artifact manifest match their stored SHA-256. **49/49** preserved files from both earlier attempts match their original outer manifest; the “unchanged” assertions also all remain true. Original summaries retain their coverage-Gate failure and deep-directory package-smoke failure; neither has a candidate run relabeled successful.
- Each independent native execution contains **81 passing B cases**, **34 C evidence cases**, and **C minus B = 0**. Actual execution order equals the fresh expected/inventory B order; canonical membership, count and all checkpoints agree. Zero failures, errors, skips or inconclusive outcomes. Both native C projections contain the expected 34 IDs and report success.
- Re-evaluated both original execution receipts with the current offline `compare_receipt`: **observed-no-missed-failure**, no blockers. This includes native ordered B/C execution-contract checks and runtime aliases. Current `validate_bundle` accepts each original bundle and verifies separate run identity associations, raw coverage/receipt semantic hashes, and smoke membership binding.
- Bundle receipt objects exactly equal the original native JSON; bundle coverage objects exactly equal the original raw coverage JSON, including original keys. The retained driver/orchestrator reads these raw objects into the bundle without path-key transformations. Original file-byte hashes and canonical semantic digests are distinct and correctly retained. This is consistency of supplied artifacts, not independent authentication of their capture chronology.
- The actual `provider_driver.py` SHA is **5a93e5bc31c5e541c0e8a8e9535fb1e24fb953542ecd5ba58969f1957632da0b**, matching both driver records. Full argv differs only in the unique `--role accepted/candidate` value. Environment objects match; each dependency inventory, invocation-context and coverage-config digest matches its retained source file. Run IDs are distinct.
- Both role-specific smoke artifacts match their declared **actual file-byte digest**, run ID and corresponding execution-receipt digest. Both retained repository outputs say **186 validated / 0 errors / 0 warnings**. Both package reports contain the four direct/sdist-wheel × isolated/nonisolated routes, identical runtime resources and `merge_eligible=false`. Every recorded subprocess exit is zero; every corresponding step-log hash matches. Separate commands, receipts and role paths remain visible even when deterministic smoke result bytes match.
- Plan self-digest, report self-digest and both report bundle digests match. Pair report file SHA is **88758a6c784ee2eebb8713510c5d20849e8c528240d5d943811d8d8bbfc1df78**. It preserves observed matching status, zero behavioral/effective exclusions, `execution_authority=false`, `savings_proved=false`, and `activation.eligible=false`.

## Claim boundaries

HANDOFF identifies immutable historical PR85 base **348d6257ddd28637c9d06abe177fc685ac4368b6**, target **51eb115119d3ea7b9639fae86ba94e0f5f0be8ea**, and plan **f8091e8ca27f552f3c30a9c99bf36a74bf614344999c816098294856a9885736**. It explicitly states zero removed tests and treats the 19.179342 s versus 18.632539 s runner difference as noise, not reduction evidence. It separately discloses current-base fingerprint expansion and does not present the historical narrow plan as a repair of that debt.

The first failed guard mutation retains 81 passing cases plus a failed impact check; the earlier positive target retains its failed package smoke. The shortened-TEMP success is a new pair rather than a rewrite of those failures. The earlier 260-character path explanation remains labeled probable/inferred because the historical random directory was cleaned; the report does not claim direct observation of that removed path.

This audit did not rerun the full Git-bound build_report or independent coverage checker, regenerate coverage, execute any test/smoke, or authenticate the host. It verified their retained raw evidence, association checks, native receipt interpretation and logged outcomes within the requested time bound. Wider authenticated collection and 2C exclusion authority remain separate.

Machine-readable checks: `real-pair-checks.json`.
