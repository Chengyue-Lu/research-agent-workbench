# CHAIN-API-PREP-005 可见通信与读域

2026-10-07；Profile=bounded implementation worker；required-Skills=[]；15分钟/2轮。机器worktree路径参数归一为本仓库相对路径，其他可见约束保留。不记录秘密或隐藏推理。

## Root授权

> 执行 CHAIN-API-PREP-005。Packet：[PR140 worktree]/docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/API_FACTORY_TASK_PACKET.md。按完整Profile、Skills=[]、读域、ownership、15分钟/2轮与停条件，准备 runtime/api_factory.py 及两份 handoff/communications。你不独自在代码库，不改别人内容。仅静态开发，严禁产品/API/Tool/Key/账测试或fixture伪资格。Root传实际conformance与独立binding observation，factory必须实际产物逐Task冻结。请尽快给最小可审接口。

## 可见消息（顺序）

1. commentary：我先读取 API Factory Task Packet 和现有入口接口，确认逐 Task 冻结所需的输入与独占写域，然后尽快给 Root 最小接口。此次只做静态开发，不运行产品、API 或资格测试。
2. worker → Root：API factory 最小接口拟为 ApiRoleBindingFactory(root, code_root, *, provider, observed_binding, task_pin, profile_pin, method_pin, requirement_pin, supplies, conformance_refs, evidence_check, data_policy_pin, host_policy_pin, timestamp, output_directory, output_contract, ...).__call__(RoleInvocation)->FrozenRoleBinding。初始/回收 main 校 inv.task 与 call_intake 实际 task_pin 完全一致并直接消费原 Method/Requirement pins；child 从真实 parent Method 深拷贝后，仅替换实际 child Task identity/hash，能力/方法越原 slice 则阻断。所有freeze走现有binding两个public函数；不生成 conformance/Source pass，observer来自Root独立观测并在use boundary再回调。确认 ownership 按 Packet 相对本轮目录：chain-proof-002/runtime/api_factory.py + API_FACTORY_{HANDOFF,COMMUNICATIONS}.md。正在核 manifest/import字段后写实现。
3. worker → Root：已核合同：原 research-contract-check Requirement 与 fixture Supply 均禁止 project-context 外传，不能由 factory 放宽来接真实 API；请传 call_intake 实际产物中明确允许当前 public synthetic payload 的 Requirement 和真实非fixture Supply/policies。Driver固定默认 request_payloads=('project-context',)，所以当前 Root 若把该标签分类为 public synthetic，须在所有实际 egress allowlists 明确允许；仅新起标签而不改Driver不能绕过。factory只冻结，不制造pass。child Method暂保持真实parent的capability/机制/义务不变并绑定新Task；child capability集合不同将阻断，需要实际新Method输入。scope将逐Task检查，child输出从其授权write_scope派生，不写parent域冒充child权限。
4. commentary：Factory 已写入独占 runtime 目录，逐 Invocation 调用现有比较冻结与 Bundle/View producer。它直接消费实际 intake pins，并拒绝 fixture 资格和 changed capability demand。原示例 Requirement 禁止外传 `project-context`，我已把这个阻断发给 Root；factory 不会改写该边界来放行 API。
5. Root → worker：Root确认原contractcheck需求禁止外传；已准备隔离候选 entry-api-bridge Requirement，constraints明确allowlisted project-context（本Attempt只public synthetic）/search-and-fetch。Method保留当前Mode但planning_action_id=NEED-ENTRY-API-BRIDGE，不冒充canonical Action接受；capabilities=[entry-api-bridge]。factory当前强制action_ref比对，请接口允许显式 action_ref 或 planning_action_id 唯一选择，Root使用后者；不是固定行动。实际 conformance 会在intake真实完整响应+schema编译成功后，基于该次actual raw pins/known usage及Root结构checks制作，范围仅该候选roundtrip可用，不宣称formal source/live接受；原source qualification=false仍保留。
6. worker → Root：收到，会将 selector 改为 exactly-one of action_ref / planning_action_id，并在实际 Method 中要求唯一匹配、把实际选定标识写入既有 manifest.execution_scope.action_ref（字段是 nonemptyString）。请你核 Runtime lineage consumer 是否已认可 planning_action_id；若它仅匹配 canonical action_ref，factory将让现有 freeze fail closed并留blocked summary，不修改core兼容或伪造canonical Action。当前实际helper接口保留 observed_binding 独立callback；未生成 conformance/source/live pass。
7. Root → worker：Root已核 runtime_bundle.py 455–475：只匹配decision.action_ref，planning_action_id不认可。保留你optional selector可显式让现有freeze拒绝，但本实际Attempt将用单独隔离候选versioned Action ENTRY-A1@0.1.0（Root准备mode-action Schema-valid真实文件/hash），需求entry-api-bridge明确egress；不改core或canonicalAction/Registry，不伪造accepted。初始intake将输出此真实Method。请handoff注明planning selector当前consumer gap，不能当可执行通过；准备完成后停止并给source hash。
8. worker → Root：Factory已实现并完成AST/内存compile（没有执行/import产品）。最终selector接口 exactly-one action_ref=None / planning_action_id=None；你本次传 action_ref='ENTRY-A1@0.1.0' 即可。planning selector保留为fail-closed诊断入口，handoff明确现有Runtime不认可它。初始/回收main使用actual intake pins；child真实Task写新目录并从actual invoked parent Method仅派生新identity/Taskhash，能力集合改变阻断。archives可用 archive_scope(invocation) 显式选Task域；默认父main用output_directory，child在该目录越其scope时改用child首个授权scope。factory.records提供实际bundle/view/method/task refs，不生成conformance或SOURCE接受。正在落盘交接+通讯/source hash，随后停止。

## 实际读域

全文：本Packet、总TASK_PACKET、DEV4_INTAKE_HANDOFF、AGENTS/README；entry executor、driver前275行、workflow RoleInvocation接口及调用/节点消费段；binding公开freeze接口与实现（批读出现输出截断后补读核心165–292段，未据缺失内容判断）；schemas v0.1.0 capability-conformance-evidence/execution-binding/runtime-bundle-manifest/agent-profile/execution-policy；四份Packet限定Task/Method/Requirement/Supply示例。

有界接口：intake/intake_call类与public def索引；configured Provider模型/capabilities/binding_descriptor公开段；provider_binding capture/assert/observe公开段与函数索引。tests/execution_fixtures.py只读取manifest/imports合同字段段157–208，不import，不复制其qualification、时间、假hash或fixture conformance。目录/文件元数据用于发现entry接口、Schema与本写域，没有扩读Key、账、真实运行日志或其他代理域。

写域仅 runtime/api_factory.py 与两份API_FACTORY归档；实现引用现有public producers，未修改src/tests/Schema/Registry/config、Guide或Workflow预算实现。没有再委派、安装、Git mutation、primary/global memory操作。

## 静态可观察结果

两次使用现有隔离Python仅执行标准库 ast.parse 和内存 compile，code object不执行、项目imports=0。第一版297行/尾随空白0；selector修改后AST/内存compile再次PASS，并打印__init__/__call__公开参数。仅检查准备代码语法，不运行prepare/factory/模型/Tool/资格或产品tests。

最终相对Markdown目标/UTF-8/尾空白/source hash检查交付前完成；hash不写入自身通讯文件，发送Root并停止。Planning selector consumer gap来自Root明确path:line消息，不是本worker扩读或测试Runtime的结果。

交付前增加FACTORY记录的实际profile/observer binding/selected Supply/conformance/Resolution/Snapshot pins与summary路径，并保留child重复消费时原始parent Method pin。最后静态AST/内存compile PASS，未执行code object，零产品imports/尾空白；两个Markdown的三个本地链接通过、机器路径0。三份交付SHA256由只读Get-FileHash发送Root，source/交接/通讯均不再修改。
