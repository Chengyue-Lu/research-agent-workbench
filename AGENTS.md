# Repository guidance

## Project boundary

- This repository builds a human-governed research workbench, not an autonomous research lab.
- Keep file contracts and provider-neutral isolated API sessions as the portable execution baseline.
- Reuse native agent, skill, permission, thread, and tool capabilities through optional adapters; do not make Codex, OpenCode, or another platform a core dependency.
- Do not introduce a global Supervisor, continuity database, message bus, or fixed research DAG without an accepted ADR backed by a demonstrated failure.
- Keep the common research kernel small. Method-specific rules belong in Research Mode Packs or Skills.
- 路诚钺 (`Chengyue-Lu`) owns mode semantics, capability vocabulary, Skill selection/evaluation/admission, trace policy, and related fixtures. 黄毅 owns provider adapters, API sessions, live conformance, and API-specific tests. Workstream labels never replace the accountable person's name.

## Agent use

- Do not spawn subagents by default. Delegate only when the user explicitly asks, or when an accepted Task Packet allows delegation and the work is bounded and independent.
- A delegated task must declare an Agent Profile, required Skills, input references, write scope, output contract, budget, and stop conditions.
- Keep the main agent focused on requirements, decisions, risks, indexes, and the next action. Do not load raw logs, full corpora, or long exploratory notes into the main context.
- Persist formal outputs before returning a handoff. Chat summaries are not authoritative artifacts.
- Persist every visible inter-agent transmission in the Task Attempt Archive: assignments, clarifications, scope changes, progress messages, handoffs, reviews, acknowledgements, failures, and cancellations. Write outgoing content before dispatch when the runtime permits; archive received content before acting on it.
- Append runtime-observable file/content reads, tool or shell calls, external actions, results, and file revisions to the Attempt event ledger. Reference immutable content by path and hash; preserve transient results that entered agent context. Never capture secrets or hidden reasoning.
- Treat content reads as scoped access, not as a consequence of workspace visibility. Read the task, repository guidance, selected profile/Skill, declared inputs, and target module first; use filename/metadata discovery before requesting additional file content.
- Do not recursively read unrelated docs, examples, candidate Skills, historical handoffs, or another agent's work directory. If new content is necessary, record why and have the named human Task owner extend the allowed read set.
- Keep a compact work log in the Task write scope for baseline, material decisions, read-scope expansions, changed paths, important checks, and remaining work. The work log is a navigation summary, not a substitute for the message/archive trace. Do not log every file open or hidden reasoning.
- Use a Compact Handoff by default. Require the full Manifest/Audit/Receipt chain only when risk, compaction, external side effects, promotion, dispute, or explicit Task policy triggers it.

## Change discipline

- Start from `docs/README.md` and `docs/DEVELOPMENT.md`; read `docs/ARCHITECTURE.md` and only the relevant module plan before changing a core contract.
- Record a new ADR for changes to core object identity, skill routing semantics, human decision boundaries, or runtime ownership.
- Use explicit file paths when staging changes. Preserve unrelated user work.
- Documentation and schemas must use portable repository-relative paths; do not commit machine-specific absolute paths.

## Verification

- Validate internal Markdown links after documentation changes.
- When implementation begins, prefer deterministic schema, hash, reference, and output checks before LLM-based review.
- Register every new deterministic check or risk code in `src/research_workbench/contracts/risk_codes.py` and cover it with a corresponding test.
- A passing validator means structural validity only; never label it scientific correctness.

## Documentation Surface Discipline

- Stable surfaces (`README`, Charter, Architecture, Modules, Development) describe the accepted system positively and do not own live milestones, implementation snapshots, or migration diaries.
- `docs/STATUS.md` is the authority for current maturity and implementation coverage; `docs/TASKS.md` owns live item status; `docs/ROADMAP.md` owns dependency direction and gates.
- Compatibility behavior, including historical replay, belongs under `docs/compatibility/` and must never appear as the default happy path.
- ADRs, workstreams, audit inputs, migration records, and the detailed devlog preserve how and why the system changed; keep them discoverable but outside first-contact navigation.
- Canonical examples must use current supported and recommended semantics. Historical fixtures must be clearly labeled and linked from compatibility or history surfaces.
- Documentation tests should enforce ownership and leakage boundaries with narrow structural checks, not broad bans on ordinary words.
