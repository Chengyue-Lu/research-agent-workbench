# Attempt inputs: call sites, membership and Runtime resources

Owner: Chengyue-Lu. TEST-PERF-002 / R2 / [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).
This continues [the checkout experiment](ATTRIBUTE_CONSUMER_PROBE.md) on accepted
`5bf2227ca9b4d2f63f452e579185e7838028de78`. PR101 remains a diagnostic test slice.

## Existing invocations and historical inputs

The source map distinguishes a file's directory from the actual argument passed
to a reader. New tests cannot establish that historical CI read a particular
committed Attempt. Historical sources and current observations keep separate
commit identities in the [Attempt evidence](../../../../work/TEST-PERF-002/A-20260926-002/RESULTS.md).

| Existing surface | Source-grounded input | What remains material |
| --- | --- | --- |
| PR84 at `dfe3165a90ebcef99d107aef8e790bf7abc0c13f` | No literal reference to the named M6-CLOSEOUT-001 Attempt was found in that commit's tests/src/.github | This bounded negative search cannot rule out dynamic or prefix-root readers |
| `DocumentationTests.test_internal_markdown_links_resolve` | README and recursive docs Markdown; linked target existence | Directory membership and link-target existence remain inputs even when target JSON bytes are not parsed |
| PR90 at `b9ad97ebf256351dd5e1540d5e688087394d474d`, `H4TraceExportTests` | Imports the archived `export_capture.py`, copies its bytes, generates temporary spool/trace data | Archived executable source must retain its tests and impact coverage; original committed trace payload is a distinct input question |
| `HarnessEvidenceTests` | `ExecutionFixture` creates a temporary evaluation/execution project | Actual receipt, source, hash, reference and lifecycle validation remains necessary; these tests do not become unnecessary because their data is generated |
| `GenericExecutionCloseoutTests` | Temporary bundles, views, receipts and Trace files | The existing tamper and replay contracts remain part of behavioral proof |

Four unchanged existing tests were executed in separate fresh Python3.11
processes with read-only audit hooks: H4 exporter CLI, its post-seal tamper control,
H4 blocked evidence, and M6 retained-validation tamper replay. All four passed.
The M6 case changes the retained validation artifact, not its Trace ledger.
Both exporter observations include open attempts for archived exporter modules;
the other two contain no source archive open attempts. They retain their original fixture substitutions.
This is current-base observation, not historical hosted execution or an absence
proof. Python audit hooks omit some filesystem/native/child-process activity and
report open attempts before success is known.

Their records use the existing `ci_consumer_shadow.validate_proposal` format:
named invocations and canonical tests, source pins, input patterns, assumptions
and explicit unknowns. `execution_authority=false` and unresolved closure remain.
The records do not modify `ci_impact_policy.yaml` or authorize exclusions.

## The actual Trace input boundary

`validate_attempt_trace(root, attempt)` consumes more than the ledger's Git blob:

1. It resolves the caller's root and Attempt/INDEX entry, then reads INDEX bytes.
2. Task, actors, ledger, message, decision, handoff, output, check and transient
   tool-result references introduce byte/hash and containment dependencies.
3. Message-directory membership and recursive tool-event membership are checked
   for unindexed files. New files can change the result without changing INDEX.
4. Default `SchemaCatalog()` constructs `RuntimeResources()`. This verifies the
   manifest, **every listed resource**, and the actual Runtime directory tree
   before loading the schema catalog. Packaged non-schema resources are part of
   this real constructor boundary too. A schema-only pin list is insufficient.
5. Alternate APIs and invocation roots retain their own behavior. One successful
   call cannot establish another consumer's input closure.

The new [input experiment](../../../../tests/test_ci_attempt_inputs.py) runs the
real reader against disposable Attempts and independent copies of the actual
package. Each default-reader invocation uses a fresh Python process. It preserves
the actual resource validator, schema catalog and hash implementation. Named
regressions cover membership, references, unrelated siblings, alternate entry
points, unchanged-manifest resource drift and restoration. Shared scenario results
are immutable; each assertion keeps an independently selectable unittest identity.

The report separates source pins, explicit members, observed file operations,
process setup and reader duration. An observed read inventory remains diagnostic:
it is not a general contract that authorizes future safe skips.

## Next decision

This slice closes specific causal examples and supplies invocation records. A
production boundary still needs complete old/new consumers, environment/toolchain,
membership and alternate paths, an accepted independent exclusion witness, complete
B/C plus coverage/smoke/lifecycle proof, and the required fresh hosted pairs. Real
whole-Runtime and whole-catalog work stays selected until a separate partition is
implemented and accepted. Global90, critical95/90, changed100/100 and fresh develop
integration retain their current requirements.

[Accepted Git proposal templates](ACCEPTED_CONSUMER_TEMPLATES.md) add declaration
provenance to the existing shadow evaluator. This is one prerequisite for later
independent exclusion evidence; it does not close the remaining input contract.
