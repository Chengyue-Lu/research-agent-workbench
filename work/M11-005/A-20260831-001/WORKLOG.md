# M11-005 work log

- Base: `develop@97fa2455c983dc65e66a782bac8d272eed32c633` after PR #50.
- Branch: `agent/m11-skill-runtime-extension`.
- Boundary: projection publication only; existing legacy Skill releases remain historical replay and receive no production projection.
- Archive level: H0 implementation record; no subagent delegation or external side effect.
- Implementation: added the projection/index Schemas, empty production index, deterministic external-evidence/Human-decision publisher, runtime-minimal catalog reader, closed repository validator, append-only governance declaration, implementation note and critical coverage inventory.
- Positive evidence: synthetic active Release with complete runtime boundaries and externally resolved evidence/decision produces one deterministic schema-valid projection; the production index loads with zero entries.
- Adversarial evidence: existing legacy Skill, absent evidence, absent Human decision, absent runtime boundaries, index hash drift, capability/provenance/manifest drift and history-field injection all fail closed.
- Focused validation: projection 8/8 after adding malformed/ambiguous index, defensive publisher and closed-registry adversarial matrices; Lifecycle 7/7, catalog 6/6, Schema 3/3 and Governance 67/67 tests passed; repository validation exited 0.
- Hosted run `33333387290` proved dual-Python behavioral, package-smoke, governance and global line 90.91%, while correctly blocking the first head because the new producer/validator modules had insufficient per-file branch evidence. The remediation adds tests only and awaits a new exact-head 95/90 result. Real Skill/Provider efficacy remains out of scope.
