# M3-008 File-Authoritative Trace Core

## Scope

The v0.1 Trace Core records one Attempt with one append-only writer. Its
authoritative artifacts are `TASK.yaml`, `ACTORS.yaml`, `INDEX.yaml`,
`events.jsonl`, hash-bound message envelopes, and persisted transient tool
results. Deterministic validation checks schema, identity, sequence, hashes,
declared boundaries, redaction declarations, capture gaps, and false
completion.

The event vocabulary is factual: message capture, content read, tool call,
file revision, external action, Attempt status, and capture gap. A shell
command is a tool call with `tool_name: shell`; it is not a new reasoning or
authority concept.

Public validator results use only the canonical Trace vocabulary in
`docs/modules/07-ARTIFACTS_AND_PROVENANCE.md`. Stable bracketed detail
subcodes distinguish schema, identity, ownership, boundary, and consistency
failure classes without creating a second public risk-code registry.

Every event payload passes through the same credential/hidden-reasoning
sanitizer before append. Event-level `redactions` preserve category, reason,
and field path without retaining the removed value. `result_entered_context`
requires a declared result origin, and transient results additionally require
a hash-checked `result_ref`. In v0.1, entered-context results are always
persisted transient results: event refs, `INDEX.tool_event_refs`, and files in
`tool-events/` must form the same closed set; stable-source provenance is not
part of this contract.

## Explicit non-scope

This module does not resolve Method, Mode, Skill, Claim, or Human-Gate
semantics. It does not change the v0.1 legacy Skill-bound Task contract, and it
does not add Trace references to Attempt or Execution Receipt. Those links and
runtime lifecycle behavior belong to the separately reviewed M6 Execution
Trace Adapter.

The file archive and hashes are authoritative. OpenTelemetry exporters may be
added later as optional projections, never as a second source of truth.

## Validation loop

1. Validate the four JSON Schema fixture pairs.
2. Exercise write-before-use recording and fail-closed sanitization.
3. Inject sequence, hash, actor, path, boundary, capture-gap, and completion
   faults; require deterministic risk codes.
4. Run `rwb trace validate --attempt <Attempt-or-INDEX> --root <project>`.
5. Enforce at least 80% repository line coverage and 90% Trace Core line
   coverage. Critical failure branches remain named fault-injection tests; a
   blended line/branch percentage must not replace those checks.
6. Run registry/examples validation, wheel build, and clean-environment smoke
   testing before merge review.
