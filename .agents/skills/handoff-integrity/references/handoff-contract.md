# Handoff acceptance boundary

A Handoff is a compact return boundary, not a transcript. It must identify the Task and Attempt, freeze the same inputs and Skills used for execution, point to formal artifacts, and disclose limitations and unresolved work.

Accept a completed Handoff only when required output contracts are represented by artifacts or a supported structured result, all repository-relative references exist inside the project root, and input and Skill locks match the task attempt. An `incomplete`, `blocked`, `failed`, or `cancelled` Handoff may still be useful, but it must not be promoted as completed work.

Never infer scientific correctness from a schema, hash, or reference pass. Human decisions remain explicit Decision objects.

For compressed task contexts, use a Handoff Transfer Manifest created before the context is discarded. It enumerates task-local transfer obligations and frozen source locators. A Transfer Audit maps those IDs into Handoff sections. Deterministic coverage can expose omissions and stale references, but only bounded independent review can label a paraphrase preserved or distorted. Domain or mode Skills decide which items belong in the manifest; the integrity Skill must not impose one scientific workflow on every discipline.
