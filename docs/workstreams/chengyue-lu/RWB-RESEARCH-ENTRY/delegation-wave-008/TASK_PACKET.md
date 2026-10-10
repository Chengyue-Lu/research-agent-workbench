# Delegation wave admission implementation packet

2026-10-10; M2-009 implementation slice / M11-008 direct bridge validation; R2. Parent candidate PR140 at `766bf45ccde4637684e2100480e9f1577cc61662`; new branch `codex/research-entry-continuation`. Human authorized continuation and a new PR without waiting for PR140 review. PR140 remains unmerged. Task definitions, dependencies and IN_PROGRESS states remain unchanged.

## Problem and intended consumer

The main model selects 0..N child Tasks. Existing whole-wave validation checks permissions, depth, identity and output conflicts, while calls/tokens are only checked per invocation. It can start children when the parent has no remaining turn, or let earlier child sessions consume the capacity required for siblings and the fresh parent consumer. This slice protects the explicit result-consumption bridge before starting work.

Use the existing bounded Session upper limits to reserve only already proposed child first sessions and the fresh parent consumption session. Carry pending sibling and ancestor-consumption reservations through nested waves. Do not require entire child Task maxima or predict unproposed descendants. Release pending reservation at its own dispatch boundary; it is planning capacity, not actual usage or unknown hold. Actual calls, usage, failed and unknown remain separately accounted. Main retains delegation decisions; Runtime retains exact frozen selection consumption.

## Bounded development packet

Profile: worker; required Skills: []. Allowed inputs: repository AGENTS/README, DEVELOPMENT/ARCHITECTURE, exact M2-009/M11-008 rows, modules 03/05, `entry/workflow.py`, `entry/executor.py`, `entry/factory.py`, `entry/handoff.py`, `entry/stage.py`; `tests/test_entry_workflow.py`, `test_entry_bridge_flow.py`, `entry_factory_support.py`, `entry_chain_support.py` and named direct helpers after metadata inspection. Read-only scoping report in private `entry-continuation-008/RUNTIME_SCOPING.md` is a proposal, not acceptance.

Product write scope: `src/research_workbench/entry/workflow.py`; new regression `tests/test_entry_wave.py`. Root owns new `tests/test_entry_wave_bridge.py`, CI component mapping/tests, readable evidence, workstream index/Risk Ledger, STATUS candidate navigation, PR/Git, canonical project own-row and all actual runtime tests. Root updates only the old workflow `test_task_budget_does_not_reset_for_main_result_consumption` expectation: the intended parent-turn preflight now stops before the child instead of after it, with retained main usage and child unstarted. Workers are not alone; preserve others' changes and adjust to current interfaces. Any necessary direct dependency beyond these paths must first be named for scope review. No Schema/Registry/Skill changes, protected config, existing immutable evidence, M12/Topic 5, global memory, credential or production ledger writes.

Budget: one bounded implementation/review pass with compact persisted handoff; no worker runtime tests, API calls, production Tools or Git mutations. Root performs deterministic source/installed consumers. Paid testing, if necessary, remains under existing per-request source/config/history/official idle and cumulative-token conditions; this packet does not weaken them.

## Direct-consumer scope extension after actual failure

The first installed nested consumer reached the real factory and failed before the grandchild Method could be frozen. The retained factory exception and reconstructed Schema errors identify repeated inherited `limitations`: the existing factory appended the same warning at each generation, while the unchanged Method Schema requires unique strings. Root additionally owns the two-line deduplication in `src/research_workbench/entry/factory.py`, preserving order, every inherited limitation and the same warning. The existing nested bridge regression must assert preserved limitations, distinct Task pins and actual grandchild/fresh-parent consumption. No core contract or authority change is needed. The first test replay also omitted the final workflow report pin; Root corrects that exact expected observation without relaxing the consumer. First failures and the stopped partial source run remain retained, not counted as passes.

## Required behavior and evidence

- Parent has an available turn, output and current deadline before admitting any child.
- All proposed first child sessions plus parent consumption fit remaining calls/tokens after every pending ancestor/sibling reservation.
- First child and nested child cannot consume future reserved slices; per-invocation upper limits remain enforced.
- Insufficient capacity, cancellation or elapsed deadline before the wave means zero child sends, all proposed children marked unstarted, prior main/intake actual usage preserved, no fabricated unknown holds.
- Unknown or actually failed current execution preserves its applicable fullhold and later operations are unstarted; no paid retry/fallback.
- Normal 0-child, flat multiple-child and nested wave paths consume actual formal Handoff in fresh parent requests. No fixed child number or new event kind is introduced; stage/Handoff consumers remain compatible.

Output: source patch; source-pinned offline regressions; installed package actual caller/factory/Host/Receipt/Handoff consumers for normal and stopped cases; readable producer→consumer inputs/results table; honest remaining Task limits. Structural validity does not imply scientific or Human/Skill/source acceptance.

Stop on core ownership/selection/Human boundary change, absent necessary input, unresolved actual test failure or a change outside this slice. Persist visible transmissions and scoped findings in private `entry-continuation-008`; return a compact file/hash handoff. No merge or release is authorized by continuation.
