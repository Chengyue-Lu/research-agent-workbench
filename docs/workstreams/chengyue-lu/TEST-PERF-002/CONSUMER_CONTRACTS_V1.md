# Consumer input and invocation records

TEST-PERF-002 / Issue #48 / Draft PR #85; owner Chengyue-Lu; R2.

This P2 slice registers four review records in the existing
[`tests/ci_impact_policy.yaml`](../../../../tests/ci_impact_policy.yaml). Policy version 2
adds `consumer_contracts`; version 1 remains readable. Unsupported versions and mismatched
shapes are rejected. No parallel selection policy or new exclusion rule is introduced.

## Inspected boundaries

| Contract | Actual source behavior | Review boundary still needed |
| --- | --- | --- |
| CLI Git HEAD observation | `_context_checkpoint` and `_context_resume_check` run `git -C root rev-parse HEAD`; neither observed command requests a Python script | Executable lookup, Git environment, each invocation root, other CLI reads/imports and alternate paths |
| Validation document instances | `load_and_validate(paths)` reads each caller-supplied path once, hashes and parses those bytes, then dispatches semantic validation | Per-caller input instances, indirect refs, directory membership and fixture lifecycle; retain actual cross-document work |
| Schema catalog | `_load` reads every `*.schema.json` in the versioned directory; the default constructor also initializes RuntimeResources | This whole-catalog/manifest integrity work is an actual dependency. Partitioning it requires a separate behavior-preserving change |
| Capability root scan | The candidate and supplied document roots are resolved inside the project; directory roots are recursively scanned before validation | Exact root membership, additions/deletions, parsed-byte hash identity and runtime qualification |

The CLI observations refine the earlier opaque-execution diagnosis. A subprocess call
does not necessarily execute changed repository code. It can still consume Git metadata
and environment, and static imports remain real paths; the observed command alone cannot
authorize removing the CLI consumer. Likewise, a document instance reaching a reader is
not proof that every invocation of that reader receives the changed instance.

## Record and report semantics

Each record has a named owner, consumer, entrypoints, input/output descriptions, invariants,
positive/negative test IDs, explicitly declared file pins and unresolved obligations.
The four initial records pin nine files. These are declared source/test dependencies,
not a claim that all helper, environment or dynamic resource inputs have been enumerated.

[`ci_consumer_contracts.py`](../../../../.github/scripts/ci_consumer_contracts.py) checks
strict shape, portable pin paths, digests, regular Git modes, entrypoints and test identifiers.
It reports call syntax with its lexical owner and source line. This is not arbitrary Python
execution or a general capability resolver. Changed bytes, deleted files, mode changes,
unparseable source and missing evidence identifiers are visible as drift.

Shadow schema 3 separately reports `base-recorded`, `candidate-proposed`, `candidate-revised`
and `candidate-removed`. A revision is checked against the original base definition and pins;
the candidate cannot repair its own failed pin by replacing the declaration. The records
are read from exact base/head Git objects, including when worktree bytes differ. All six
producer source hashes are bound into the report.

Matching pins do not establish complete input closure or prove that a referenced test ran.
Every record/check retains `execution_authority=false`, and every report remains ineligible
for activation. Descriptive input strings are review material, not interpreted path allowlists.
The accepted selector, groups, worker minimum, aggregate and pinned witness retain their
existing execution obligations. This slice does not yet reduce the 91/92 selection for #84.

## Verification and monitored intake

Validation covers malformed declarations, authority injection, source/test/input drift,
deleted/mode-changed pins, missing identifiers and candidate rewrite/removal. A real Git
regression refreshes a changed consumer's candidate pin and verifies that the original base
pin still fails; uncommitted bytes cannot repair it. Existing failing-document-consumer
and weaker-plan rejection tests remain required.

The eleven declared business test IDs are also executed separately. Passing those examples
establishes their observed behavior, not complete invocation closure or permission to skip
other cases. Historical planner/report comparisons retain exact Git/metadata bindings and
compare full execution fields; they do not stand in for twelve full behavioral runs.

M5-007's separate task **RWB开发 (3)** completed this development turn, and PR #86
(`feature/m5-007-harness-preflight`) passed full CI at `b53a391ece3a4be7207c00c636dc9e1570e71473`.
It is now the thirteenth immutable historical sample. Its base is
`0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`; hosted merge target is
`8e7857369894e934ad6c5277f2a3ea2c68201bb8`. The head-target replay preserves the hosted
execution fields and every original selection field; it does not reuse a merge-target plan ID.
CI green, H1/H2 closure, whole M5-007 completion and human acceptance remain separate.
Intake fetched Git objects without modifying that development branch.

The current M5 plan selects 93/94 modules. All 29 behavioral FULL reasons are unclassified
archive files; the Schema additions independently retain actual catalog/install validation.
Raw graph diagnostics select 93/94 for archive seeds, 91/94 for business Python, 91/94 for
test Python, 93/94 for schemas and 48/94 for ordinary documents. These are seed-category
diagnostics, before full planner metadata/contract filtering, not substitute execution plans.
The reference records flag M5's changed `validation/documents.py` and `test_schemas.py` pins.
Thus fixing classification alone would not close the remaining consumer fan-out.

## Next activation requirements

1. Bind concrete invocation inputs, helper/environment changes and added/deleted membership.
2. Preserve real catalog/registry work and enumerate alternative consumer paths.
3. Supply real failing-consumer and precision examples for each proposed exclusion.
4. Extend an independently accepted witness before allowing records to reduce obligations.

No quality threshold, coverage exclusion, existing behavioral test or release boundary is
weakened. Current raw checks and Trace are retained in
[A-20260916-009](../../../../work/TEST-PERF-002/A-20260916-009/RESULTS.md).
