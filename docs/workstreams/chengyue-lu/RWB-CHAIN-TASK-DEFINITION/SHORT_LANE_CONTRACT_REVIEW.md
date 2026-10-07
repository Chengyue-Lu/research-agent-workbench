# Short lane contract review

Task: `AUDIT-RWB-DOCS-005` · 2026-10-08 · bounded contract explorer · required Skills: none.

This is a source review for the PR141 documentation design. It does not implement a router, a short writer, an API invocation, or a MainState updater. Existing behavior and design recommendations are separated below. The audited code belongs to the `research-entry-integration` checkout; these persisted review artifacts belong to the `research-chain-task-definition` checkout. A checkout result is not a merge or admission claim.

## Compact findings

1. A short local edit need not create or revise a research ProjectProtocol. ProjectProtocol is not an imported Runtime Bundle kind. A **bare Task alone**, however, cannot enter the existing Runtime Core: it still needs a Method, an exact Action/Capability slice, a Requirement, eligible Supply and conformance evidence, Resolution, Snapshot, and the separate frozen execution inputs. No-Skill removes the Skill extension, not these control contracts.
2. Existing `compile_control_draft` requires Protocol and Task ceilings and validates a Protocol. Consequently, a pre-Protocol short lane cannot simply call that compiler with Protocol omitted. Such a lane is a documentation design target; no existing router or short writer is established by this review.
3. Independent Guide is a distinct direct `ProviderRegistry`/`ModelRequest` consumer. It does not use Runtime Bundle, Resolved View, `ApiRoleBindingFactory`, or `IsolatedApiSessionRunner`. Its remote-provider/data-policy authorization is explicitly the caller's responsibility. It returns the response and usage and performs no Tool execution or state writes.
4. A no-Mode local operation must retain a real Action and capability demand. The reviewed factory accepts an explicit `action_ref` or `planning_action_id` and matches that selector to one actual Method Action; it does not manufacture a ResearchMode name. A missing capability, Supply, evidence, or matching Action is a gap/blocked admission condition, not a reason to invent a research method for paragraph ordering.
5. Unifying the conversation entry does not unify authority. Preserve the current authorization, pinned inputs, capability/observed-binding facts, and execution limits. Assess MainState impact after execution; any state update remains a separate accepted operation. This assessment/updater is a proposed semantic requirement, not verified existing behavior.

## 1. Minimum Task and runtime controls

The Task schema requires the following fields even for a one-paragraph operation: `schema_version`, `task_id`, `goal`, `question_refs`, `active_modes`, `required_capabilities`, `required_skills`, `forbidden_skills`, `agent_profile`, `input_refs`, `write_scope`, `required_outputs`, `permissions`, `delegation`, `budget`, `atomic_boundary`, `completion_checks`, `safe_pause_conditions`, `stop_conditions`, and `stale_if`. A revision is optional in the schema. The output and write-scope arrays must contain at least one item; a budget must contain at least one allowed limit; completion, safe-pause, and stop conditions must each contain at least one item. Delegation may be disabled, with any supplied depth/parallel values constrained to zero. Evidence: `schemas/v0.1.0/task-packet.schema.json:7–12,29–37,53–92,107–125`.

`active_modes`, `question_refs`, `required_skills`, and `forbidden_skills` reference the shared string-array definition without a field-level minimum in the Task schema (`:19–23`). This is evidence against a Task-level mandatory ResearchMode or Skill selection. The shared definition and Method schema were outside this delegated read set, so this review does not independently prove that every proposed empty-array/no-Mode document is schema-valid. The intake compiler only constrains selected Method modes to the supplied Protocol modes; it does not construct a research-mode name (`src/research_workbench/entry/intake.py:197–209`).

The existing Runtime Bundle does not import `project_protocol` (`src/research_workbench/execution/runtime_bundle.py:25–35`). Its loader nevertheless requires exactly one of each:

| Control object | Required existing behavior | Locator |
| --- | --- | --- |
| Task | Exact Task identity/revision and complete capability demand | `runtime_bundle.py:201–219,242–254,417–440` |
| Method | Status `proceed`; Task reference; exact selected Action; no-Skill disposition for non-Skill Supply | `runtime_bundle.py:256–261,325–340,444–478` |
| Capability Requirement | The selected Requirement must belong to the actual Method's capability demand | `runtime_bundle.py:417–440,461–478` |
| Supply, Resolution, Snapshot | One deterministic eligible selected Supply, `satisfied` Resolution, and matching lineage | `runtime_bundle.py:367–413,490–545` |
| Conformance evidence | Supply evidence references/identities must equal the declared evidence closure; fixture evidence cannot qualify runtime execution | `runtime_bundle.py:548–575,688–707` |
| Manifest and pins | Allowlisted kinds, per-document schema/hash checks, exact import graph and reachable closure | `runtime_bundle.py:615–670,709–735` |

All `runtime_bundle.py` locators in this table refer to `src/research_workbench/execution/runtime_bundle.py`. Core uses `action-capability-slice`; the manifest binds the Action, Requirement, full Task demand, and one closed capability. `task_completion` must remain `false`: a slice receipt does not announce whole-Task completion (`:444–486`). The Bundle itself is a pinned closure and **not execution authorization** (`:1–5`).

The reviewed factory additionally requires Task/Profile/Method/Requirement pins, real Supply and typed conformance pins, explicit data and host policies, an independent observed binding, an output contract, and an Action/planning selector. It freezes Bundle and View through existing execution-input freezing; it does not run Host, Provider, or Tool. Evidence: `docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/runtime/api_factory.py:68–116,217–238,248–278,299–311`. Factory input-pin reads check hashes and schemas (`:128–137`), Task permissions must fit the Profile (`:153–160`), and its per-role archive must fit both Task write scope and allowed roots (`:183–194`).

For a paragraph-ordering task, keep an honest local transformation Action, a bounded input and output contract, actual capability demand, and explicit local-write permission where a consumer writes the result. No-Skill is supported by the reviewed factory and zero-Skill Core (`api_factory.py:153–155,213–216,273`; `runtime_bundle.py:325–340`). The factory accepts exactly one arbitrary nonempty explicit Action/planning selector (`api_factory.py:94–110`) and then checks an exact existing Method Action match (`:174–182`). These checks do not require a ResearchMode naming convention. They also do not establish an already implemented paragraph-writer capability.

There is a material execution limit: this factory currently supports only read-only ClientTools (`api_factory.py:112–116`). Although the session layer recognizes `local-write` and `external-write` side-effect classes (`src/research_workbench/adapters/models/session.py:82–85`), those classes alone do not grant a Task permission or prove a safe writer exists. A paragraph-write consumer and its filesystem boundary still need design/admission. The absence of a matching Action, real Supply, or evidence must be recorded as a gap, not concealed by a fabricated Mode (`api_factory.py:104–105,174–182,226–234`).

## 2. Existing Guide consumer

`build_guide_request` accepts a nonempty question, explicit model, positive output-token limit, one pinned MainState reference, and explicitly approved additional references. It reads only those snapshots, validates MainState, defaults to `local_only=True`, refuses provider-server tools, and declares `tools=()`; it records hashes for the baseline and input snapshot in request metadata. Evidence: `src/research_workbench/entry/guide.py:20–50`.

`ask_guide` builds this request and directly calls `providers.require(provider_name, request).generate(request)` (`guide.py:54–68`). Its docstring states that the call has no sinks or writers, that unexpected ToolCalls are not executed, and that remote-provider/data-policy authorization is separate (`:60–63`). `ApiRoleBindingFactory` rejects roles outside `main`, `child`, and `handoff` and explicitly says it does not implement intake or independent Guide (`api_factory.py:148–150`).

The Guide therefore reuses the provider-neutral model port, ProviderRegistry, DataPolicy, pinned-input reader, and MainState validation. It bypasses the Runtime Bundle/View/Host and isolated-session consumer paths. It exposes a token cap and returns provider usage; it does not itself establish a session wall-time limit, total-token/cost ceiling, execution receipt, or state-impact assessment. Returning usage does not imply zero cost or complete cost reporting. ProviderRegistry internals and the Guide caller's authorization were not read here.

## 3. Minimum reuse for the unified entry design

Treat pre-Protocol routing as a bounded classification/proposal over the user-authorized request and allowed input references. The lane choice conveys intent; it does not itself grant read/write/network permission, choose an unobserved runtime, or approve spending. Reuse the existing model-port/DataPolicy boundary for advisory calls. For local execution, reuse Task/Profile permission ceilings, actual Method/Requirement and capability selection, pinned execution inputs, and the Bundle → View → Host boundary. Optional API sessions remain adapter behavior.

The existing intake compiler provides useful ceiling rules, but its current surface is Protocol-bound. It fixes human Task identity/goal/Profile, preserves required Human gates and conditions, does not expand permission/write/delegation/budget/input boundaries, and leaves required Skills optional under the ceiling (`src/research_workbench/entry/intake.py:101–183`). Publishing its output remains a draft; Human approval and runtime admission are separate and full runtime closure is not claimed (`:215–248`). A pre-Protocol local-lane compiler should reuse these bounded-control rules without silently manufacturing or revising a research ProjectProtocol. That compiler is future work.

For an optional isolated-session adapter, retain the existing explicit provider/model, declared-tool/handler equality, side-effect classes, per-turn output limit, model-turn/tool/time limits, and usage availability checks. Evidence: `src/research_workbench/adapters/models/session.py:49–85,147–198,212–241,315–358,898–912`. Its usage/cost checks occur after responses; they are observed-budget checks, not a proof that a call can never incur a cost above a threshold. A missing provider-reported cost is unknown; with a cost ceiling it causes a pause (`:907–911`). Tool invocation is the accounting boundary even when a handler fails (`:379–394`). Keep declared capabilities and independent observed Provider/Adapter/Model/Runtime/Host facts distinct (`api_factory.py:217–238,248–251`); do not infer actual execution from a selected View alone.

After a short operation, report the artifact result and assess whether it changes project decisions, plans, accepted claims/evidence, sources of truth, open questions, or the next action. A text reorder may yield “no MainState change”; a newly revealed blocker or changed decision may require an explicit MainState update proposal. Execution success and a capability-slice receipt do not authorize state promotion. No code establishing this impact assessment was in the read set, so it is a design recommendation only.

## 4. Semantic and ADR boundaries

No new CoreRole, global Supervisor, message bus, or fixed research DAG is required by the reviewed controls. Keep short local modification a bounded entry/consumer path. Reusing existing object meanings and ceiling rules is an implementation choice inside those boundaries.

Repository guidance requires an ADR for changes to core object identity, Skill routing semantics, human decision boundaries, or runtime ownership (`AGENTS.md`, Change discipline). An implementation crosses that boundary if it redefines Task or Method identity, treats a lane choice as authorization, weakens accepted gates, auto-selects/adopts Skills, grants execution or MainState-promotion authority to the router, or replaces the established runtime owner. Requiring automatic MainState mutation after every local edit would change the human/state-promotion boundary; an advisory impact assessment with the existing accepted update process need not do so. Whether the proposed pre-Protocol compiler needs an ADR depends on the final semantics, not its filename.

## Read domain, uncertainty, and handoff

Actual source content reviewed: primary `AGENTS.md`; Task schema `1–129`; intake `60–248`; Guide `1–68`; Runtime Bundle `1–64,190–276,320–758`; session `40–216,212–241,242–337,339–358,375–395,809–851,898–912`; the sole approved factory `68–200,211–278,299–312`. Metadata/keyword discovery was limited to the declared source trees, then the exact factory path supplied by the coordinator. Whole-file source hashes and line-count metadata were obtained; source content outside the listed semantic ranges was not used for conclusions. No Keys, account/billing files, API originals, unrelated histories, tests, live Provider/Tool executions, Git mutations, configuration changes, schema changes, or product code changes were performed.

Unverified: shared schema definitions; complete Method/no-Mode schema validity; Host/View implementation; a currently available paragraph-edit Supply; all upstream authorization/cost behavior; semantic correctness of a text edit; any implementation of unified routing, a short writer, or MainState impact/updating. This is a contract review, not execution or conformance evidence.

Source SHA-256 values pin the inspected versions:

| Source | SHA-256 |
| --- | --- |
| `schemas/v0.1.0/task-packet.schema.json` | `d2ebc01795522103d09465c8af0c54f025f26b69ed41abac08793d4a75a7d24f` |
| `src/research_workbench/entry/intake.py` | `b76021ee66fd39e579ab05533f546b639afb07ceefb98317f48ff35dd978fbcf` |
| `src/research_workbench/entry/guide.py` | `8bfcf458acfaf6900e421ea0cacd10e6da783267080ba7652b7b7e7487e8b4c9` |
| `src/research_workbench/execution/runtime_bundle.py` | `f9a5b38d50772c354a69de230533ea05a37c1daadb8bfa5a43313632a87005a5` |
| `src/research_workbench/adapters/models/session.py` | `0f705d19759be7a43ccd8b8312ae62c9a50b36e666cf0536a0d00d1d91a58ba9` |
| `docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/runtime/api_factory.py` | `14448a39c4d7c67d42df11eb5a1f0b7c2e8beb372ddb3375099ed3eb03feae84` |

The scoped Task Packet, visible messages, runtime-observable review events, and read-scope extension are recorded in [SHORT_LANE_CONTRACT_COMMUNICATIONS.md](SHORT_LANE_CONTRACT_COMMUNICATIONS.md). Coordinator next action: integrate these qualified constraints into PR141's documentation; separately confirm the no-Mode schema/accepted semantics through the coordinator's allowed inputs. The coordinator owns shared `PROJECT_MEMORY.md` updates because this task's write scope is limited to the two review artifacts.
