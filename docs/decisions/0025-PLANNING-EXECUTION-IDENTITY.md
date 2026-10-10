# ADR-0025: Planning execution slice identity

- Status: Candidate
- Date: 2026-10-10
- Scope: Runtime Bundle → Resolved Execution View → Thin Host → execution Receipt

## Context

Method Resolution already admits a Method-local `planning_action_id` alongside the
versioned Mode `action_ref` branch. The package factory planning delta reached the
Runtime Bundle consumer and failed `RUNTIME-BUNDLE-EXECUTION-SLICE-MISMATCH`: its
manifest and downstream selector consumers only represented Action slices. The
demonstrated failure is preserved by the coordinator; it is not a planning pass.
The [planning/Handoff Task Packet](../workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/planning-handoff-004/TASK_PACKET.md)
authorizes extending this identity boundary and independent consumer verification.

## Proposed decision

Extend the `0.1.0` schema allowed set with an explicit discriminator:

| `execution_scope.kind` | Exactly one selector | Identity namespace |
|---|---|---|
| `action-capability-slice` | `action_ref` | Existing versioned Mode Action |
| `planning-capability-slice` | `planning_action_id` | Exact pinned Method Resolution |

The selector branches are mutually exclusive. A planning ID is meaningful only
inside the exact Method Resolution `resolution_id`, `revision` and content hash
already closed by the Bundle's declared documents, Capability Resolution and
Snapshot and exposed as the View's `method_resolution_ref`. The same plain ID in
another Method is a different execution identity. No versioned Action is invented.

Both branches require exactly one matching Method decision, the Method's existing
`resolution_status: proceed`, the exact pinned Requirement, the full Task capability demand and a
singleton closed capability. Existing Task/Method/Requirement/Supply/Resolution/
Snapshot/conformance hash and reference checks remain mandatory. Neither selector
selects a new Supply, grants permission, introduces Skill qualification, accepts a
method or Claim, or declares whole-Task completion.

View deterministically consumes the selected decision's stop and blocked
conditions. Host copies the same scope and reloads/recomputes the exact View and
Bundle before dispatch. Generic and optional Skill Receipt closeout retain this
scope and independently recompute their frozen lineage. A completed Action
receipt uses `action-capability-slice-only`; a completed planning receipt uses
`planning-capability-slice-only`; failed or blocked receipts use `none`.
Skill admission, Projection and Skill identity rules are unchanged.

View and Host report schemas reference the manifest's `execution_scope` definition,
so the discriminator extension applies to all three without duplicating identity.

## Version and replay boundary

This is an explicit compatible allowed-set extension within `0.1.0`, not a rewrite
of an existing Mode/Action/AuthorityMatrix/Migration Registry identity. Release
identity remains pinned by exact source and Runtime Resources manifest hashes;
the schema version alone does not distinguish consumer capability.

New consumers read existing Action payloads and frozen bytes without migration.
Existing Action manifests, Views, Host reports and Receipts are not rewritten or
backfilled. Old consumers reject the new planning kind through their existing
schema/selector checks. Compatibility is therefore directional: this proposal
does not claim old consumers can read new planning artifacts. A planning-capable
release requires rebuilt and verified packaged schema resources.

## Required verification

Exercise the actual factory → Bundle → View → Host → generic Receipt path and a
cold file replay using a schema-valid no-Mode planning Method. Test wrong and
duplicate planning IDs, mixed selectors, opposite-kind selectors, non-proceed
Method resolutions, Method/Requirement/full-demand drift, View/Host/Receipt substitution,
and completion-claim mismatch. These cases must reject before provider dispatch
where applicable. Replay existing Action and Skill closeout cases unchanged.
Structural validity and offline test fixtures do not establish live qualification,
scientific correctness, Human acceptance or completion of the three bridge Tasks.

## Acceptance

This document is a candidate proposal and implementation basis under the bounded
Task Packet. Only the authorized human/coordinator may record its acceptance and
promote verified coverage into the authoritative project status.
