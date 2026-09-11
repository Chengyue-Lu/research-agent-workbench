# Full-suite cost, test necessity and reusable evidence

TEST-PERF-002; Chengyue-Lu; R2; Issue #48 / PR #70.

## Measured bottleneck

The first completed coverage baseline ran 1,074 cases in 2,600.969 seconds. Skill evaluation,
Skill release projection, Claim trace, execution Trace adapter and Host tests accounted for
38.4% of that duration. Test count alone did not explain the cost: the ten selected evaluation
cases consumed 268.983 seconds, while seventy planner cases consumed 84.309 seconds.

Direct profiling used the real
`SkillEvaluationTests.test_complete_live_pair_is_only_eligible_for_human_decision` on Python
3.11.16, without replacing any evaluator, fixture, filesystem operation or assertion.

| Work inside one profiled test | Calls before | Cumulative time before | Calls after | Cumulative time after |
|---|---:|---:|---:|---:|
| `SchemaCatalog` construction | 14 | 42.903 s | 14 | 9.222 s |
| Schema self-validation (`check_schema`) | 1,064 | 35.575 s | 76 | 2.588 s |
| Runtime resource construction | 14 | 4.506 s | 14 | 4.330 s |
| Actual document schema validation | 14 | 0.043 s | 14 | 0.046 s |
| Evaluation fixture construction | 1 | 0.069 s | 1 | 0.039 s |

Cumulative rows overlap and must not be added. Profiling inflates Python execution costs.
An independent, unprofiled three-trial comparison cleared the new cache before every trial:
median 16.840 s before and 6.112 s after, a 63.7% reduction for this exact test. These are local
Windows measurements, not a full hosted-suite speedup claim.

The evaluator constructs a catalog repeatedly while checking protocol, receipts, context,
assignment, profile, check report and decision documents. Every catalog previously checked
the same 76 schema definitions again. Fixture construction was cheap in this measured path;
deleting or merging its negative cases would have targeted the wrong cost.

## Implemented reuse boundary

`validation/schemas.py` now retains successful schema self-checks in a bounded 256-entry
process-local cache keyed by exact schema bytes and checker identity. It caches the fact
that a schema definition is valid. Each catalog still reads current bytes, enforces pinned
Runtime resource integrity where applicable, parses fresh schema objects, builds its own
reference registry and validates every supplied document.

This preserves the existing public behavior. New bytes require a new check even if path,
size and timestamps are unchanged. Invalid schemas are not cached as success. A new checker
has a different key. Returned schema mutation cannot poison later catalogs. Different roots,
renames, removed files, malformed JSON and missing IDs retain fresh inventory/error behavior.
The regression scenarios exercise those boundaries with real schema validation; spies only
count calls and a failing checker proves invalidation. No runtime/behavioral assertion or
coverage threshold was removed.

## Necessity audit of expensive tests

| Read surface | What requires distinct evidence | Disposition |
|---|---|---|
| `test_skill_evaluation.py` | Model identity/configuration, context equality, checker identity, assignment, receipt/report binding, missing usage and human decision binding fail differently | Retain the cases; reuse schema self-checks. The valid paired case proves eligibility, while the human-decision case separately proves decision binding and recorded outcome. |
| `test_execution_host.py` | The long post-call scenario tests binding, supply, egress, side effect, budget, output and write-scope violations with seven distinct diagnostics | Retain all seven counterexamples. Repeated bundle/view construction is a later measurement target; shared mutable fixtures require reset verification. |
| `test_skill_release_projection.py` | Isolated registry/hash/derivation checks and whole-publication external-evidence/human-decision checks have different prerequisites | Retain both layers. Split future maintenance by derivation, publication authority and malformed registry/shape cases, keeping explicit integration tests. |
| `test_claim_trace.py` | Direct evidence localization and a real promotion with retained negative evidence are different paths; the long promotion case checks independent provenance substitutions | Keep the existing unit/integration class separation. A file split can improve selection granularity; it does not itself remove validation work. |
| `test_trace_properties.py` | Generated sequence, path-escape and byte-tamper variants exercise ranges beyond a single fixed example | Retain the property checks. Their repetition is deliberate; separate focused deterministic proof from stress execution through an accepted selection contract, not by deleting generated cases. |

The projection file currently combines helper construction, derivation, authority closure,
schema shape and malformed-input checks. Extraction should first move shared fixture builders
into an explicit helper module, then separate contract test files while keeping their dependency
closure and mandatory acceptance identity mapped. It should follow measured gains from common
initialization, because additional process boundaries can also repeat expensive fixtures.

No redundant whole test has been proven removable in this audit. Repeated schema self-checks
are demonstrated redundant work. A test can be removed or consolidated only after comparing
its preconditions, observable assertions, failure diagnostic and counterexample detection with
the retained scenario; equal line coverage or similar names are insufficient.

## Growth with additional Skills

A new Skill asset should require its own package/contract checks and affected registry
consumers. It should not imply replaying every accepted Skill's entire evaluation workflow.
Changes to a shared evaluator, schema, loader or authority policy have a larger dependency
closure and appropriately require broader behavior.

The schema cache has a stable cost while many Skills share the same definitions: the schema
self-check count grows with distinct schema/checker inputs, not the number of evaluation calls.
The remaining measured catalog cost includes repeated `RuntimeResources` construction. That
constructor validates manifest identity, every resource's bytes and the whole file closure;
its work scales with installed assets. An operation-scoped verified resource/catalog context
is the next candidate, but needs tests for file/manifest/symlink drift and existing constructor
integrity contracts. A process-global cached success for a mutable root would not preserve them.

## Cross-commit CI reuse

The proposed subtraction is feasible when the common part is defined by complete inputs:

`work to execute = required test obligations - valid reusable test evidence`

For a cacheable test unit, the key must cover:

- Its test code, helpers, package initialization, literal/declared resources and transitive
  production dependencies, including removed or newly introduced dependency edges.
- Fixture/registry/schema/configuration inputs and resource inventory where the test scans
  directories or indexes; equal filenames do not establish equality.
- Interpreter/platform, installed dependency/tool versions, test command/flags, controlled
  environment and randomization settings.
- The accepted execution and evidence contract, including measurement configuration for
  any coverage data being reused.

The previous evidence must come from an eligible successful run with verified artifact
integrity. Its origin commit/run remains visible; it must not be relabeled as a fresh execution
at the new HEAD. A trusted verifier derives the current key and assembles the new plan's
evidence. Missing/failed/uncertain evidence executes again; candidate metadata cannot create
its own narrower trusted key.

| Change | Reuse decision |
|---|---|
| An unrelated isolated test/leaf changes; all inputs of another unit are identical | The unchanged unit can be eligible. |
| Test method unchanged but helper, fixture, dependency, schema or runtime pin changes | Invalidate the affected unit. |
| Runner, environment or measurement semantics change | Invalidate units whose execution/evidence contract changes. |
| Network/live service, time-sensitive state or an unresolved dynamic dependency matters | Not automatically cacheable; isolate/control those inputs or execute again. |
| A full suite is requested under the current accepted fresh-execution policy | Execute it; a future reuse contract must be reviewed before changing that policy. |

Coverage reuse additionally needs byte-identical measured source coordinates, compatible
line/branch configuration and complete source accounting. Reuse raw coverage facts and
re-evaluate the current thresholds/negative obligations; do not copy an old percentage or
combine stale coordinates. Integration baselines and explicit fresh runs remain distinct
from cached test evidence.

This is an audited adoption design, not an enabled cross-commit result cache. The currently
implemented execution join reuses results only within the same plan/run. The old `fee47c0`
to `bf6d079` transition changed the runner/workflow, so overlapping test names alone would
not have authorized carrying their old execution receipts forward.

[Pants's test documentation](https://www.pantsbuild.org/stable/docs/python/goals/test) provides
a relevant implementation reference: dependency-aware invalidation, isolated test processes,
controlled environment and the tradeoff between fixture-sharing batches and cache granularity.
[Its CI guidance](https://www.pantsbuild.org/stable/docs/using-pants/using-pants-in-ci) describes
cache reuse and cache-performance reporting. This change borrows those boundaries without
introducing a new build system or replacing RWB's accepted authority checks.
