# Repository guidance

## Project boundary

- This repository builds a human-governed research workbench, not an autonomous research lab.
- Keep file contracts and the provider-neutral Runtime Bundle → Resolved Execution View → Thin Host boundary as the portable execution baseline. Isolated API sessions are optional Adapter implementations, not a core prerequisite.
- Reuse native agent, skill, permission, thread, and tool capabilities through optional adapters; do not make Codex, OpenCode, or another platform a core dependency.
- Do not introduce a global Supervisor, continuity database, message bus, or fixed research DAG without an accepted ADR backed by a demonstrated failure.
- Keep the common research kernel small. Method-specific rules belong in Research Mode Packs or Skills.
- 路诚钺 (`Chengyue-Lu`) owns mode semantics, capability vocabulary, Skill selection/evaluation/admission, trace policy, and related fixtures. 黄毅 owns provider adapters, API sessions, live conformance, and API-specific tests. Workstream labels never replace the accountable person's name.

## Agent use

- Do not spawn subagents by default. Delegate only when the user explicitly asks, or when an accepted Task Packet allows delegation and the work is bounded and independent.
- A delegated task must declare an Agent Profile, a required-Skills list that may be empty, input references, write scope, output contract, budget, and stop conditions. A Skill binding is optional unless the accepted Task/Method path explicitly requires one.
- Keep the main agent focused on requirements, decisions, risks, indexes, and the next action. Do not load raw logs, full corpora, or long exploratory notes into the main context.
- Persist formal outputs before returning a handoff. Chat summaries are not authoritative artifacts.
- Use the PR body and Git history as the minimum development record for ordinary R0/R1 changes. Create a formal Task Attempt Archive only when an accepted Task Packet, delegation, R2 risk, external effects, compaction, dispute, or a multi-PR workstream requires it.
- When a Task Attempt Archive is required, persist every visible inter-agent transmission and runtime-observable event defined by the Task policy. Reference immutable content by path and hash; preserve transient results that entered agent context. Never capture secrets or hidden reasoning.
- Treat content reads as scoped access, not as a consequence of workspace visibility. Read the task, repository guidance, selected profile/Skill, declared inputs, and target module first; use filename/metadata discovery before requesting additional file content.
- Do not recursively read unrelated docs, examples, candidate Skills, historical handoffs, or another agent's work directory. If new content is necessary, record why and have the named human Task owner extend the allowed read set.
- Keep a compact work log when a formal archive or multi-session handoff is triggered. It is a navigation summary, not a substitute for required message/event evidence. Do not log every file open or hidden reasoning.
- Use a Compact Handoff by default. Require the full Manifest/Audit/Receipt chain only when risk, compaction, external side effects, promotion, dispute, or explicit Task policy triggers it.

## Change discipline

- Governance constrains what may enter shared project truth, not ordinary implementation choices inside an isolated branch. Apply the R0/R1/R2 merge-boundary policy in `docs/DEVELOPMENT.md`.
- Start from `docs/README.md` and `docs/DEVELOPMENT.md`; read `docs/ARCHITECTURE.md` and only the relevant module plan before changing a core contract.
- Record a new ADR for changes to core object identity, skill routing semantics, human decision boundaries, or runtime ownership.
- Use explicit file paths when staging changes. Preserve unrelated user work.
- Documentation and schemas must use portable repository-relative paths; do not commit machine-specific absolute paths.

## Verification

- Validate internal Markdown links after documentation changes.
- When implementation begins, prefer deterministic schema, hash, reference, and output checks before LLM-based review.
- A passing validator means structural validity only; never label it scientific correctness.

## Documentation Surface Discipline

- Stable surfaces (`README`, Charter, Architecture, Modules, Development) describe the accepted system positively and do not own live milestones, implementation snapshots, or migration diaries.
- `docs/STATUS.md` is the authority for current maturity and implementation coverage; `docs/TASKS.md` owns live item status; `docs/ROADMAP.md` owns dependency direction and gates.
- Compatibility behavior, including historical replay, belongs under `docs/compatibility/` and must never appear as the default happy path.
- ADRs, workstreams, audit inputs, migration records, and the detailed devlog preserve how and why the system changed; keep them discoverable but outside first-contact navigation.
- Canonical examples must use current supported and recommended semantics. Historical fixtures must be clearly labeled and linked from compatibility or history surfaces.
- Documentation tests should enforce ownership and leakage boundaries with narrow structural checks, not broad bans on ordinary words.
