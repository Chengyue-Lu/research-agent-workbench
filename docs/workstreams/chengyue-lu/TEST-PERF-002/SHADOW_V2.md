# Shared input facts and affected-source witnesses

TEST-PERF-002 / Issue #48 / Draft PR #85; owner Chengyue-Lu; R2; 2026-09-16.

Subsequent P2 records and shadow schema 3: [consumer contracts](CONSUMER_CONTRACTS_V1.md).
The schema 2 corpus below remains its original producer-bound evidence.

## This slice

The user authorized a larger historical branch corpus and further CI replanning work.
The first shadow report exposed three gaps: one display role discarded simultaneous
authority facts; archived logs and common attributes remained unclassified; selected
test paths did not explain the actual source paths that triggered smoke obligations.

[`ci_input_facts.py`](../../../../.github/scripts/ci_input_facts.py) now describes directory
purpose, executable facts, all authority dimensions, scoped attributes and unresolved
inputs separately. A workflow can carry both selection and coverage authority; a test
helper remains executable test code. The display role does not choose CI obligations.
Archive data still needs content/hash validation and real-reader closure.

The attribute grammar preserves rule order and recognizes relative text/eol/whitespace
rules. Git itself validates a representative precedence case. Macros, filters, export
attributes, escaping, malformed or duplicate attributes and unknown flags stay unresolved.
Script suffixes, shebangs, executable modes, symlinks/gitlinks and mode drift retain their
stronger facts. A directory or extension never grants permission to skip execution.

`ci_dependencies.select()` now retains `witness_version=1` and `affected_witnesses` for
every affected path. These are the paths already traversed by the selector; graph traversal,
selected tests, exclusions, contract rules and obligations are unchanged. The signed plan
and worker recomputation bind the new witnesses. Missing or altered witnesses are rejected.
Each affected source has one deterministic witness, not an enumeration of all alternative
paths. Removing a displayed edge alone cannot establish a safe exclusion.

Shadow schema v2 uses those witnesses for the actual CLI and validation source consumers
that trigger smoke, while retaining accepted group reasons and direct/fallback reasons.
It binds hashes of the report producer, input classifier, planner, dependency selector and
governance checker. Old plans without the new witness format must be replayed with their
original producer or regenerated from exact original Git facts. No implicit format upgrade
or weaker-plan acceptance is provided.

The diagnostic job remains separate from execution outputs and aggregates. This slice
changes the selector's evidence payload and therefore still needs full authority bootstrap
and the independent pinned witness. It has not activated contract-based exclusions.

## Historical corpus

Each case uses immutable base/head Git snapshots and the captured PR metadata; target=head.
The before producer is commit `980bb99947a52a812fb691334e8ad6106171b9d5`, in an isolated
checkout. Historical branches and the primary develop checkout are unchanged.

| PR / surface | Dependency modules | Behavioral / coverage | Unknown input records before → after |
| --- | ---: | --- | ---: |
| #65 test/fingerprint | 4/70 | focused / none | 1 → 0 |
| #68 documentation | 10/78 | focused / none | 9 → 0 |
| #71 M5 protocol | 85/86 | full / impact + repository | 18 → 0 |
| #73 documentation | 10/79 | focused / none | 6 → 0 |
| #74 scaffold | 86/87 | full / impact + repository | 5 → 0 |
| #75 M6 execution | 91/92 | focused / impact | 8 → 3 |
| #77 M14 Quickstart | 86/87 | full / repository | 7 → 0 |
| #78 release readiness | 86/87 | full / impact + repository | 13 → 1 |
| #80 M14 Source CI | 92/93 | full / impact + repository | 22 → 0 |
| #81 M11 closeout | 88/89 | focused / impact + repository | 22 → 0 |
| #82 closeout records | 88/89 | full / repository | 1 → 0 |
| #84 closeout records | 91/92 | full / repository | 0 → 0 |

All 12 comparisons preserve every previous selection field and 16 execution/binding
fields, including exact tests, positive/negative proof, changed coordinates, coverage and
both smokes. Classification gaps decrease from 112 to 4 records across cases (not a unique
file count). The remainder is three transport-proof ZIPs and LICENSE; container contents
and packaging input contracts require explicit treatment. Largest augmented plan is
443,764 bytes, below the existing witness's 4 MiB input limit.

These are planner/report migration checks, not twelve full behavioral runs. Classification
completeness and source witnesses do not establish a safe smaller execution set or hosted
time savings. PR84 still selects 91/92 modules. The earlier real #65 selected execution
remains separately retained in [A-20260916-007](../../../../work/TEST-PERF-002/A-20260916-007/RESULTS.md).

## Correction to the earlier smoke inference

The first report retained a test-level chain through deterministic_runner and CLI/validation
tests. That chain is real, but it did not identify the source paths used by smoke predicates.
The new #80 witnesses show independent causes:

- Package: `release_source_ci.py → cli.py`, with an opaque-execution edge; `__main__.py`
  is then reached by a syntax edge. CLI's execution capability needs an invocation contract.
- Repository: `ci.yml → validation/*` through unbounded resource readers, directly or via
  shared integrity/requirements helpers. Data-instance propagation needs its own contract.

Consequently a runner-only boundary cannot close these obligations. The original frozen
attempt is retained as historical evidence; this source-level correction governs the next
review. Static edges are explanatory witnesses, not proof that every use is necessary.

## Local checks and next activation boundary

- Input/attribute, real Git consumer, witness-tampering and selector scenarios are covered.
- Changed modules: input facts 80/80 statements and 46/46 branches; report 120/120 and 36/36;
  selector 503/503 and 322/322. No coverage exclusions were added.
- Existing planner, checker, coverage-policy, documentation and independent-witness regressions
  are included in this slice's verification. Exact-head preflight and hosted checks are separate.

Next, define base-reviewed CLI execution and validation input-instance contracts, then
implement independently witnessed exclusions against this corpus. Workflow authority,
RuntimeResources' actual whole-catalog validation, dynamic execution and unknown inputs
remain conservative until their individual boundaries have evidence.

Raw matrices, metadata, producer snapshots, checks and Trace:
[A-20260916-008](../../../../work/TEST-PERF-002/A-20260916-008/RESULTS.md).
