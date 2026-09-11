# System-Level Evaluation Protocol — M5-006

Contract version: `1.0.0`. Evaluation owner: 路诚钺 (`Chengyue-Lu`).
Baseline transport consumer/producer owner: 黄毅 (`let778750-cpu`).

This contract preregisters the system comparison and verifies evaluation inputs. It does not run an arm,
select a Supply, approve a Skill, produce actual execution evidence, or score research for a Human.
The accepted basis is [ADR-0020](../decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md),
whose exact bytes are required by the Protocol schema. Task acceptance remains in [M5-006](../TASKS.md).

## Artifacts and entrypoints

The new records use the existing Schema catalog directory `v0.1.0` and independent record `version: 1.0.0`.
Their `record_kind` is recognized by repository document validation. All top-level records and typed envelopes
reject unknown fields. Existing Evaluation Manifest and Skill Evaluation v0.1 are unchanged.

| Record kind | Purpose | Semantic verifier |
|---|---|---|
| `system_evaluation_protocol` | Exact ADR/Manifest, Mode/Action bytes, frozen implementation/interface declarations and preregistration | `system_protocol.validate_protocol` |
| `evaluation_provider_interface` | Frozen Supply-bound provider-visible interface bytes and declared I/O | `qualification.validate_implementation`, as part of a qualified closure |
| `arm_execution_qualification` | `ArmExecutionQualificationRecord@1.0.0` covering every A2 or A3 frozen Snapshot | `qualification.validate_qualification` |
| `evaluation_case_closure` | Case / formal Task / input / oracle commitments and case-specific checker/Human provenance | `overlap.derive_overlap`, consumed through an assessment |
| `admission_evidence_overlap` | `AdmissionEvidenceOverlapAssessment`, including both comparison closures and derived eligibility | `overlap.validate_overlap` |
| `a4_execution_qualification` | Candidate-origin treatment to admitted pre-run Runtime lineage | `overlay.validate_overlay` |
| `a3_a4_pairwise_comparability` | `A3A4PairwiseComparabilityRecord`, with a bounded interpretation | `comparability.validate_comparability` |
| `evaluation_measurement` | One metric with explicit evidence/measurement status | `system_protocol.validate_measurement` |

The public Python entrypoint is `research_workbench.evaluation.contracts.verify_evaluation_record`.
It requires a repository-relative record path and SHA-256. Child records additionally require an externally
selected Protocol FileReference. Overlap, A4 overlay and pairwise verification also require an externally selected
case closure and freeze time. The case count must match the frozen design and formal comparison Tasks must belong
to the Manifest. An overlay's Task must occur in that selected case closure.
An outer pin must come from the consumer's frozen inputs, not be copied from an untrusted record as approval.

```text
rwb eval verify evaluation/protocol.json --root <evaluation-root> --sha256 <protocol-sha256>

rwb eval verify evaluation/a2-qualification.json --root <evaluation-root> --sha256 <record-sha256> \
  --protocol evaluation/protocol.json --protocol-sha256 <protocol-sha256>

rwb eval verify evaluation/overlap.json --root <evaluation-root> --sha256 <assessment-sha256> \
  --protocol evaluation/protocol.json --protocol-sha256 <protocol-sha256> \
  --case-closure evaluation/cases.json --case-closure-sha256 <case-closure-sha256> \
  --case-selection-frozen-at <frozen-timestamp>
```

These are command shapes; the deterministic test builders supply synthetic files for integration tests.
The CLI has no admission-approval switch. Full A4/pairwise verification requires an authorized Maintainer
to supply the Python API's independent `admission_verifier`; without it, verification fails closed.
`rwb validate --structure-only` remains available for inspecting record shape without claiming qualification.

## Preregistered comparison

The four arm identities remain those of [M5-003](EVALUATION_MANIFEST_CONTRACT.md):

- A1/A2 use M6; A3 uses M11 Core; A4 uses the M11 Skill extension.
- Primary `A4-A2` measures a system package difference including transport.
- `A2-A1` is the within-M6 Tool contrast. `A4-A3` has the pairwise record's interpretation ceiling.
- `A3-A2` includes Mode/Method and transport; `A4-A1` is a supporting full-stack contrast.

The Protocol freezes case-replicate blocks, seed, confirmatory and pilot replicate counts, complete-block stopping,
retry limit and eligible transient failures, fresh Attempts, retention/costing of failures, and drift handling.
The declared stopping block count must equal case count times confirmatory replicates. Pilot observations are
excluded from primary confirmation. A safety stop retains all attempted runs; output quality does not authorize
retrying until a preferred result appears.

Analysis is per-metric paired differences with case-cluster bootstrap intervals; confidence level, resample count
and seed must be explicit before results. Secondary comparisons remain descriptive. A small case set restricts
inference; validation of these parameters is not statistical power or generalizability evidence.
Model/provider/adapter/host/runtime/Task/context/budget/data drift requires blocking and a new Protocol version.
The Protocol freezes the complete execution binding, including versions/hashes, and a time budget in seconds.
The binding's model/slot, adapter, Host and Runtime identities must agree with M5-003; A3/A4 Views must match
that exact binding and the common turn/output/time budget. Context loading and parallel execution limits remain
mandatory consumer checks for M6-008/M5-007, since the current View does not represent a loaded context transcript.

Blind Human reviews hide arm, Skill/RWB labels, execution identity, cost and token information. All blind scores
must freeze before reveal. The decision order is research integrity, quality/correction, then efficiency/cost.
Integrity degradation cannot be offset by efficiency; a weighted aggregate score is outside this contract.
Only the future Harness can enforce the observed ordering of review/reveal and execution events.

## Frozen-to-runtime qualification

The Protocol pins every A2/A3 frozen Snapshot and its implementation/component files and provider interface.
The qualification record binds those declarations to runtime-execution Snapshots. The validator reloads the
selected and unselected candidate closure and reuses the existing Capability Supply comparison validator.
It verifies exact Task, Requirement, Supply/component/implementation identity and I/O; A3 also preserves the
frozen Mode/Action/Method and Core `no-skill` disposition. Permission roots, data egress and side effects can
only remain equivalent or narrow. A structural fixture never becomes executable by changing a record boolean.

M6-008 produces A2 records after this contract is accepted. Capability Resolver produces/selects A3 runtime
Resolution/Snapshot; M11 consumes them. M5-007 assembles and independently recomputes A3 records.
Qualification is evaluated at its recorded timestamp. M6 use-boundary checks and the Harness/Host's trusted
execution clock must recheck current validity before actual calls; historical qualification is not a live permit.

## Held-out assessment

An assessment has three logical sections, without a self-referential raw hash:

1. `admission_case_closure` pins the exact Skill Evaluation, candidate/Skill identity and every admission case.
   The Protocol independently pins this closure before assessment. Rewriting an assessment and its case/provenance
   files cannot replace that frozen source. A Protocol without this pin cannot support overlap verification.
   Its Task and formal input references must agree with that Evaluation; v0.1's opaque Task contracts remain
   unresolved unless formal Task identity can actually be read and checked.
2. `comparison_input_closure` pins the Protocol and proposed/frozen case closure, hashes the admission logical
   section, and records normalized subject sets and a deterministic comparison digest.
3. `assessment_result` pins the validator implementation, `checked_at`, intersections, gaps and derived eligibility.

Only case, Task, formal input and private oracle are disqualifying axes. Same-category identity **or** hash equality
is overlap; case-specific checker/Human provenance is evidence of oracle closure, not a fifth/sixth axis.
Cross-category equal hashes and shared public sources/frameworks do not themselves create these intersections.
Case files bind the declared Task/input/oracle and provenance commitments, preventing an assessment from attaching
a different oracle to an unchanged case. Oracle bytes are hashed only on the authorized evaluation side; records
store references/commitments and never forward private bytes to treatment arms or Runtime.

`resolved`, `absent` and `unknown` are distinct. Missing/unparseable/drifted references, empty input closure,
opaque Task identity, and mismatched case-specific provenance produce unresolved reasons. A coherent unresolved
assessment can be structurally valid while remaining ineligible. Only complete `held-out` closure yields
`primary_confirmatory_eligible=true`; overlap remains pilot/secondary evidence and cannot solely justify pruning.

Verification independently reloads both sides, recomputes subjects/intersections/status/eligibility, verifies
`protocol.frozen_at <= checked_at <= case_selection_frozen_at`, and compares the exact selected case closure pin.
The validator pin conservatively covers the executing package's Python code and Schema catalog, including indirect
loaders/checkers. Consumers cannot substitute a shorter dependency list. A changed implementation requires a fresh
assessment; old assessments/validators remain necessary for historical replay.
Parsed Schema bytes are retained in the invocation's identity and rechecked alongside all referenced inputs.

## A4 pre-run lineage and comparison ceiling

The A4 overlay preserves the frozen candidate/evaluation, binds a named accepted Human Decision, immutable Release
and eligible Lifecycle, and reproduces the exact SkillReleaseProjection. Candidate-to-Release changes require
explicit pinned promotion/build provenance with matching endpoints. The independent admission verifier must verify
the actual evidence, Human decision and any build/promotion mapping; parsed status strings provide no such authority.

Projection-backed Supply must lead through the selected Snapshot and exact Runtime Bundle to a deterministically
recomputed Resolved Execution View. The overlay references the overlap assessment and agrees with its derived
eligibility. It remains a pre-run record: the future Harness separately needs Host actual facts, typed Trace and
replay-valid Skill closeout. The Core closeout's current Skill exclusion is preserved.

Pairwise verification reloads A3 qualification, A4 overlay and both execution surfaces. It compares Task/Method bytes,
Requirement and non-Skill Supply/component multisets, provider-visible interface, binding, effective constraints,
Profile constraints, output/completion requirements and stop/safe-pause conditions.
Only exact equality with one admitted Skill extension can yield `exact-skill-only`. Differences in Method, non-Skill
Supply or relevant boundaries downgrade to `skill-bearing-package`; missing/incompatible shared conditions make the
secondary contrast `not-comparable` / unavailable. Neither changes the primary estimand.

Current M11 Core/Skill Method dispositions differ, so the complete synthetic integration fixture reports a package
effect. The pure exact-equality test proves the comparison algorithm, not the existence of a currently executable
exact-skill-only experiment. Analysis-input records reload their preregistered inputs; a preregistered exact result
cannot silently degrade. The Harness remains responsible for independent post-run actual-fact reconciliation.

## Measurement and evidence boundaries

Measurements retain the M5-003 fixed metric vocabulary. Measured/estimated entries require nonnegative values and
pinned evidence; estimates name their method. Unavailable/not-applicable entries require `value: null` and a reason.
Counts are integral, ratios stay in [0,1], and units must match their metric. A missing token count is never zero.
Cross-transport wall time uses the Harness's outer trusted clock. Cost includes preparation, supervision, review,
correction, recovery and every Attempt; records do not calculate a universal score.

The Protocol does not complete M6-008, Gate B, M5-007, case approvals, live conformance or A4 production admission.
The corresponding dependencies remain in TASKS. Record identity/version and externally pinned bytes are immutable
inputs; revisions use new paths/pins, with prior records retained for replay.
