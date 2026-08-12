---
name: handoff-integrity
description: Deterministically validate a research subagent Handoff against its Task Packet, frozen inputs, Skill locks, artifact references, required outputs, limitations, and unresolved items. Use before a main agent accepts any formal handoff or promotes artifacts. Do not use as a scientific correctness review, source-weight decision, or substitute for a required Human Gate.
---

# Handoff Integrity

Check whether a bounded task returned a complete, traceable handoff. Prefer deterministic validation before semantic review.

## Workflow

1. Read the Task Packet, Handoff Packet, project root, and Skill Assignment lock. Do not load raw subagent conversation unless a reported gap requires it.
2. Read [handoff-contract.md](references/handoff-contract.md) when interpreting a failed or incomplete handoff.
3. Run `python scripts/check_handoff.py <handoff> --task <task> --root <project-root>`.
4. Block acceptance on missing required outputs, changed input hashes, Skill lock drift, references outside the project root, missing artifacts, or a completed handoff with unresolved mandatory work.
5. Preserve `limitations`, `conflicts`, `unresolved`, and `human_decision_required`; do not summarize them away.
6. Report validation codes and artifact paths. State explicitly that a pass establishes structural integrity only.

## Stop conditions

Stop and return the deterministic failures when the checker blocks. Route method quality, scientific interpretation, and Human Gate decisions to the appropriate reviewer or researcher rather than recursively reviewing the handoff.
