---
name: claim-preserving-rewrite
description: Revise scientific or technical prose for clarity, concision, and natural flow while preserving claims, quantities, citations, polarity, uncertainty, scope, and evidence strength. Use only when the source claims are already fixed and the requested task is wording-level revision. Do not use for fact-checking, summarization, translation, new argument generation, statistical interpretation, or changing conclusions.
---

# Claim-Preserving Rewrite

Improve expression without changing the scientific payload. Treat every factual or interpretive change as out of scope.

## Workflow

1. Read the source and the requested style boundary. Refuse to infer missing facts or repair scientific content silently.
2. Inventory protected quantities, units, citations, entities, polarity, uncertainty, comparison groups, scope qualifiers, and evidence-strength terms. For fragile terms, create a JSON lock using [claim-lock-contract.md](references/claim-lock-contract.md).
3. Rewrite only wording and sentence structure. Keep negative, null, conflicting, and limitation statements visible.
4. Run `python scripts/check_claim_preservation.py <source> <revision> [--lock <lock.json>]`.
5. If the checker reports drift, restore the source meaning or return the unresolved conflict; do not weaken the gate.
6. Return the revision plus a short disclosure of unresolved semantic risks. State that the deterministic pass does not establish scientific equivalence.

## Hard boundaries

- Do not add causal language, certainty, generality, novelty, or statistical significance.
- Do not remove negation, caveats, counterevidence, null findings, or population/time/condition limits.
- Do not alter numbers, units, identifiers, citation locators, URLs, or DOI strings.
- Do not replace a disputed technical term unless the task provides an approved mapping.
- Do not browse, upload text, call an external model, or write outside the task scope.
- Stop for human review when preserving meaning conflicts with the requested style.

This is a candidate Skill in a non-discoverable lab path. It is not accepted for production dispatch.
