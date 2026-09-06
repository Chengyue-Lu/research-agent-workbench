# Claim evidence localization

M4-003 adds a read-only consumer of the existing Claim, Evidence, source
admission and Promotion Receipt contracts. Contract owner: Chengyue Lu;
implementation: Huang Yi. The `claim_evidence_map` v0.1.0 input is additive:
it does not migrate Research Objects or alter Claim authority.

## Input and command

```text
rwb claim trace objects/claim.yaml --evidence-map checks/claim-map.yaml --root .
```

The map contains `schema_version: 0.1.0`,
`document_kind: claim_evidence_map`, the exact `claim_ref` FileRef,
`evidence_refs` (Evidence document FileRefs), and `source_bindings`.
Each binding joins an existing `source_ref` ObjectRef to an `artifact_ref`
FileRef and a `provenance_ref` FileRef. Every file path is relative to `--root`.
The Claim argument must identify the map's pinned Claim file.

ObjectRef identity/revision and optional `content_hash` semantics remain
unchanged. FileRef SHA-256 checks the actual captured bytes separately. A
source identity that has no standalone research-object representation can
be explicitly joined to raw or produced bytes through this map; this is a
declared binding, not identity attestation or a new source-object ontology.

`rwb validate` also recognizes the map and checks its reference closure;
`--structure-only` retains its usual Schema-only meaning. Without
`--evidence-map`, the existing Claim field view remains available and reports
`localization_status: not-requested`; it does not claim verified localization.

## Consumer checks

- Load only explicit evidence files and the provenance required by the
  Claim's declared support/counterevidence. Missing, wrong-type, unversioned,
  ambiguous, wrong-revision and hash-drifted references prevent a complete
  localization result. No latest-revision fallback or workspace search.
- The map's Evidence identity/revision set must equal the union of the Claim's
  support and counterevidence references. Its source-binding set must equal the
  sources referenced by those Evidence. Extra entries prevent completion;
  every declared binding's artifact/provenance is checked once, including
  invalid or unused bindings. Shared failure results are cached too.
- A raw source uses its exact `<raw-path>.admission.yaml`, with valid Schema,
  acquisition fields, matching admitted path and captured byte hash. An inbox
  reference is rejected. Unreferenced derivative graphs are not expanded.
- A promoted source must match an exact target/source pair in the pinned
  Promotion Receipt and its pinned promotion record. Captured source bytes
  must equal the target pin. The consumer verifies that record's declared
  disposition; it does not reconstruct the entire historical validation chain.
- The receipt must be at `runs/promotions/<promotion_id>/receipt.json`.
  Its record and cited work source must be strictly inside the record's exact
  `work/<task>/<attempt>` workspace. Promotion targets stay within `objects/`,
  `runs/` or `deliverables/candidates/`. These paths retain M4-002's resolved
  path checks, so a filesystem alias cannot stand in for the declared path.
- A retained source may be cited through the same receipt's source set and
  record's `retain-in-work` entry. Its negative-result flag and reason remain
  visible, and its artifact stays inside the declared workspace; it is never
  labeled promoted merely because it has provenance.
- Each limitation retains its text and points to the Claim FileRef plus
  `/limitations/<index>`. The current `limitations: string[]` contract does
  not contain separate source citations; no such citations are invented.

The result exposes support and counterevidence separately, exact Evidence and
artifact locations, original locators/quality flags, provenance and unresolved
edges. `complete` describes structural localization of the declared relations.
An empty relation list remains empty, not proof that no other evidence exists.
The consumer does not parse arbitrary scientific locator text or judge whether
the declared statement correctly interprets the cited material.

`claim_acceptance` and `scientific_correctness` are always false. Optional
Protocol ceiling checking remains active, and a localized Claim can still
fail that ceiling. No Claim status, Human Decision or artifact is written.

## Cost and verification

The read set caches captured bytes/digests, parsed documents and shared source
provenance for one invocation. It uses the existing `LoadedDocuments` index
to avoid a second filesystem read. No promotion checker, validation host or
scientific program is executed. A five-file shared-source fixture verifies
five file opens from the project working directory.

`tests/test_claim_trace.py` covers the normal CLI, generic validator, live-byte
and identity drift, invalid/missing provenance, limits, counterevidence and
read cost. Its integration case consumes a real M4-002 promotion and retained
negative output, then checks altered receipt/record/target references without
repeating the promotion pipeline for each mutation. This bounded synthetic
evidence does not establish scientific correctness or M5 research benefit.
