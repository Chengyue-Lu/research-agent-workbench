# Repository guidance

## Project boundary

- This repository builds a human-governed research workbench, not an autonomous research lab.
- Prefer native agent, skill, permission, thread, and tool capabilities over a custom orchestration runtime.
- Do not introduce a global Supervisor, continuity database, message bus, or fixed research DAG without an accepted ADR backed by a demonstrated failure.
- Keep the common research kernel small. Method-specific rules belong in Research Mode Packs or Skills.

## Agent use

- Do not spawn subagents by default. Delegate only when the user explicitly asks, or when an accepted Task Packet allows delegation and the work is bounded and independent.
- A delegated task must declare an Agent Profile, required Skills, input references, write scope, output contract, budget, and stop conditions.
- Keep the main agent focused on requirements, decisions, risks, indexes, and the next action. Do not load raw logs, full corpora, or long exploratory notes into the main context.
- Persist formal outputs before returning a handoff. Chat summaries are not authoritative artifacts.

## Change discipline

- Read `docs/ARCHITECTURE.md` and the relevant module plan before changing a core contract.
- Record a new ADR for changes to core object identity, skill routing semantics, human decision boundaries, or runtime ownership.
- Use explicit file paths when staging changes. Preserve unrelated user work.
- Documentation and schemas must use portable repository-relative paths; do not commit machine-specific absolute paths.

## Verification

- Validate internal Markdown links after documentation changes.
- When implementation begins, prefer deterministic schema, hash, reference, and output checks before LLM-based review.
- A passing validator means structural validity only; never label it scientific correctness.
