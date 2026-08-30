# SkillReleaseProjection publication contract

M11-005 defines a narrow Maintainer-to-Runtime publication boundary for an already accepted, immutable Skill
Release. It does not admit a Skill and does not expose the complete Skill lifecycle to Runtime.

```text
active accepted Skill Release (exact source/package + manifest bytes)
  + current Lifecycle eligible for new-binding
  + externally resolved baseline/trial/evaluation/promotion evidence
  + externally resolved Human admission decision
        ↓ deterministic publisher
SkillReleaseProjection
```

## Published facts

Each projection fixes:

- `projection_id + projection_version` as its append-only published identity;
- exact Skill ID/version and Release reference;
- manifest path/raw SHA-256, source content hash and package hash;
- capabilities, input/output contracts, Tool dependencies and compatibility;
- permission, data-egress and side-effect ceilings;
- explicit runtime eligibility ref/scopes, including `new-binding`;
- the source Lifecycle path/hash and named Human decision reference.

The projection Schema is allowlisted and cannot contain Need text, Candidate state, Trial/Evaluation results,
metrics, scores, deliberation or full Lifecycle history. Its authority flags are all false: publication cannot select
a Supply, grant execution or permission, own fallback, promote a Claim or satisfy a Human Gate.

## Publisher and integrity index

`build_skill_release_projection()` loads one exact accepted Registry entry and one indexed Lifecycle record. It
requires the accepted entry to be `active`, the Lifecycle to be structurally current/new-binding eligible, and all
referenced evaluation evidence plus the Human decision to be accepted by explicit external resolvers. Lifecycle
state strings alone are insufficient.

Future projectable Skill manifests must include `runtime_boundaries.data_egress_ceiling` and
`runtime_boundaries.side_effect_ceiling`. The field is optional at Schema compatibility level so historical
manifests remain readable, but the publisher rejects any manifest without it. This prevents unknown legacy
behavior from being inferred as a safe Runtime boundary.

`registry/skills/release-projections.json` is the closed integrity index. It may be empty: the current repository has
no active, evidence-complete new-binding Skill. Every future entry must fix projection identity, Release identity,
path and raw-file hash. Repository validation replays the deterministic Release/Lifecycle mapping and rejects
missing, relocated, rewritten or fact-drifted projections.

## Consumer boundary

`SkillReleaseProjectionSet` is the runtime-minimal catalog reader. It reads only its explicit index and indexed
projection files; it does not load Need, Candidate, Evaluation or Lifecycle documents. M11-006 may use an exact
projection to qualify one Skill Supply candidate through the existing Capability Resolver. Projection metadata is
a ceiling and eligibility fact, never a final permission or execution grant.

The zero-Skill/no-Skill/direct Tool Core remains valid with an empty projection index or with no projection input
in a Runtime Bundle.

## What this proves

Synthetic bounded tests prove deterministic mapping, raw-byte identity, closed indexing and fail-closed
evidence/decision/hash/fact behavior. They do not prove scientific benefit, real Provider availability or admission
of any checked-in legacy Skill.
