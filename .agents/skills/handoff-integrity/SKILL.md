---
name: handoff-integrity
description: Deterministically validate a research subagent Handoff against its Task Packet, frozen inputs, Skill locks, artifact references, Transfer Manifest, required outputs, limitations, and unresolved items. Use before a main agent accepts a formal handoff, trusts a compacted subagent context, or promotes artifacts. Do not use as a scientific correctness review, source-weight decision, or substitute for a required Human Gate.
---

# Handoff Integrity

Check whether a bounded task returned a complete, traceable handoff. Prefer deterministic validation before semantic review.

## Workflow

1. Read the Task Packet, Handoff Packet, project root, and Skill Assignment lock. Do not load raw subagent conversation unless a reported gap requires it.
2. Read [handoff-contract.md](references/handoff-contract.md) when interpreting a failed or incomplete handoff.
3. Run `python scripts/check_handoff.py <handoff> --task <task> --root <project-root> [--audit <transfer-audit>]`.
4. When the Task requires a Transfer Manifest, block missing items, stale source hashes, invalid source/Handoff locators, omitted required items, and unmapped negative sections.
5. Require bounded independent human sampling only when Task policy or declared risk triggers it. Never add recursive reviewer Agents to obtain agreement.
6. Preserve `limitations`, `conflicts`, `unresolved`, and `human_decision_required`; do not summarize them away.
7. Report validation codes and artifact paths. State whether the result is structural-only or reviewed; neither proves scientific correctness.

## Stop conditions

Stop and return the deterministic failures when the checker blocks. Route method quality, scientific interpretation, and Human Gate decisions to the appropriate reviewer or researcher rather than recursively reviewing the handoff.
