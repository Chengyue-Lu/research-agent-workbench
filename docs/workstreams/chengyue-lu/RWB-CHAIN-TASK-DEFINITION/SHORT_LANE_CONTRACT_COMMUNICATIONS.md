# Short lane contract communications

Task: `AUDIT-RWB-DOCS-005` · date: 2026-10-08 · agent: `short_lane_contract` · coordinator: Root.

This file preserves the scoped delegation and visible inter-agent messages relevant to the review. It uses repository-relative paths and checkout aliases. `CODEWT` means the source `research-entry-integration` checkout; `DOCSWT` means the output `research-chain-task-definition` checkout. The companion [contract review](SHORT_LANE_CONTRACT_REVIEW.md) contains exact evidence locators, source hashes, actual read ranges, findings, and unknowns. No hidden reasoning or credentials are captured.

## Task Packet received

> 只读窄问 Task Packet AUDIT-RWB-DOCS-005。Profile=bounded contract explorer; required-Skills=[]; budget=10分钟/1轮。当前用户授权把统一对话入口的 pre-Protocol 路由、readonly Guide 同级的短程局部修改、执行后是否影响MainState评估并入 docs PR141，禁止本轮实现/API调用。你不独自在仓库，其他人编辑docs，不回退其内容。允许读：primary AGENTS.md 与 CODEWT 下 schemas/v0.1.0/task-packet.schema.json（先文件名定位实际Task schema）、src/research_workbench/entry/intake.py、guide.py、api_factory.py、src/research_workbench/execution/runtime_bundle.py 的Task/Protocol必要条件片段、src/research_workbench/adapters/models/session.py 的最小request约束片段。只用metadata发现路径，勿读Key/账/API原件/无关历史。问题：①一次简单段落重排不需要研究Protocol时，可否通过现有最小Task/no-Mode/no-Skill配置及Bundle/View/Host；到底哪些控制契约仍必需？②readonly Guide现行调用绕过/复用哪个消费者？③设计统一入口时避免绕过权限/费用/工具事实，最小复用建议、需要新语义/ADR的边界。勿把当前实现不存在的router/shortwriter说成已有，给精确文件/line locators。只写 DOCSWT 的 docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/SHORT_LANE_CONTRACT_REVIEW.md + SHORT_LANE_CONTRACT_COMMUNICATIONS.md，公开repo-relative，机器绝对原packet可存ignored .rwb/docs005-communications/contract.md。输出Compact结论、实际读域、未知，无测试/Tool/API/Git/configSchema产品改动。

Stop conditions: missing declared inputs or required scope must be returned to Root; no independent scope extension, product implementation, tests, live API/Tool runs, or Git/config/schema changes. This was an independent bounded source review. No further delegation occurred.

## Visible inter-agent transmissions

1. Agent → Root, metadata issue:

> metadata 定位：Task schema 是 schemas/v0.1.0/task-packet.schema.json；entry/intake.py、guide.py、execution/runtime_bundle.py、adapters/models/session.py 均存在。src/research_workbench 全树文件名没有 api_factory.py 或 factory 文件；我将继续允许片段审查。请提供 api_factory 当前路径或确认可扩展 filename discovery 至仓库全树；当前不读取额外内容。

2. Agent → Root, preliminary contract result:

> 初步有明确边界：Runtime Bundle allowlist 没有 project_protocol（runtime_bundle.py:25–35）；Core 必须各一 Task/Method/Requirement/Supply/Resolution/Snapshot（201–219），no-Skill仍要求 method skill_disposition=no-skill（325–340）与 Action/Capability slice（444–486）。但 entry.compile_control_draft 当前必须 protocol/task/unknowns 及两个 ceiling（101–120）。Guide ask_guide 直接 providers.require(...).generate(...)（guide.py:54–68），无 Bundle/session runner。待 api_factory 路径确认；我会将短程入口写成设计/准入约束，不写成已有路由。

3. Root → Agent, sole-file read-scope extension and interpretation to verify:

> Root metadata已定位：CODEWT docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/runtime/api_factory.py。允许补读此唯一文件Task/Protocol/Method/guide factory相关片段，不扩展其他历史。结论正合目标：短程不必创建/修订研究ProjectProtocol，但内部Task/Method/Requirement与授权/冻结不得绕过；无需新CoreRole或统一Supervisor。请特别核资料既有no-Mode用现有action refs不等于强制ResearchMode命名，缺能力记录gap，不为段落编排造研究方法。

4. Agent → Root, factory result:

> 已补读唯一 api_factory（docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/runtime/api_factory.py）。Factory 用任意显式 action_ref 或 planning_action_id 精确匹配现有 Method Action（94–110、174–182），没有生成或强制 ResearchMode 命名的代码；不实现 intake/Guide（148–150）；只支持 readonly ClientTools（112–116）。短程段落修改可保留 no-Skill Method/单一capability slice，但写回与pre-Protocol compiler/router仍是待设计，不能称factory已支持段落写回。缺Supply/evidence/匹配Action时须记录gap并阻断（104–105、174–182、226–234），不能造研究Mode。将据此落报告。

## Runtime-observable review events

| Order | Operation and observed result | Consequence |
| --- | --- | --- |
| 1 | Read primary `AGENTS.md`; filename discovery in declared schema/entry/execution/model-adapter trees | Task schema and four code sources located; no source-tree `api_factory.py` filename found |
| 2 | Collected source SHA-256/line-count metadata and targeted symbol matches; one combined result was truncated | Narrow numbered semantic excerpts were subsequently read; no conclusion relies on unseen truncated text |
| 3 | Read Task/Guide and intake ceiling/compiler/persistence fragments | Protocol-bound compiler and direct Guide Provider consumer established |
| 4 | Read Runtime Bundle cardinality, Method/no-Skill, slice/closure/pin/lineage fragments | Bare Task insufficient; Protocol absent from imported kinds; no-Skill retains Method/capability closure |
| 5 | Read session request/limit/usage/tool invocation fragments | Tool-handler equality, side-effect checks, observed token/cost limits, usage unknowns established |
| 6 | An output-directory existence probe was run under CODEWT and returned missing; corrected metadata probe used DOCSWT | No CODEWT document was created or modified; DOCSWT directory exists and both assigned output names were absent |
| 7 | Received sole-file factory scope extension; collected factory metadata/hash and read approved related fragments | Explicit existing Action/planning selector, frozen Bundle/View, independent observed binding and readonly-Tool limitation established |
| 8 | Persisted only the two assigned public review artifacts under DOCSWT | Formal findings available before the Compact Handoff |
| 9 | Checked relative Markdown links and scanned both public artifacts for machine-specific absolute paths | Both links resolve; both artifacts use portable paths; no product tests were run |

Each content result entered the agent context through the recorded source ranges; the companion review pins the complete files by SHA-256. The two tool-output truncation warnings were treated as limitations of the transient display, and the required findings were obtained from subsequent bounded numbered reads. No live Provider/ClientTool invocation, test run, product-code/schema/config change, Git mutation, or shared project-memory write occurred. Local shell commands were used only to read sources/metadata and persist/verify the permitted artifacts.

## Handoff record

Delivered artifacts: `SHORT_LANE_CONTRACT_REVIEW.md` and this file. Remaining coordinator checks: no-Mode/shared schema definitions and accepted semantics; paragraph-edit Supply availability; Host/View/writer and MainState-update behavior. These were not independently verified inside this Task Packet. Root retains responsibility for integrating PR141 and writing any shared project-memory entry.

Compact result transmitted to Root: no research ProjectProtocol is imported by Runtime Core; a bare Task does not satisfy Core. Existing Task/Method/Requirement/Supply/Resolution/Snapshot/pins and separate authorization remain necessary. Guide uses a direct Provider consumer. The reviewed factory accepts exact existing Action/planning selectors and readonly ClientTools; short writing/routing and post-execution MainState impact assessment remain design targets. Required follow-up: confirm no-Mode schema/accepted semantics and actual paragraph-write capability before implementation/admission.
