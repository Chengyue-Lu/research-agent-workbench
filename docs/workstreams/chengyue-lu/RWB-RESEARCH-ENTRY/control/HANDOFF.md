# ENTRY-A Compact Handoff

2026-10-07。Human accountable owner：路诚钺；运行/Provider领域由黄毅负责正式review。Agent Profile：bounded role/intake/guide implementation worker；required-Skills=[]。分支 `codex/research-entry-integration`，base `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。本地隔离实现，不称 develop 接受、live 资格或科学正确性。通信与命令见 [COMMUNICATIONS](COMMUNICATIONS.md)。未 commit/push/安装/再委派，未改其他代理文件、原Schema/Registry或共享状态。

## Public 接口与 Root 接合

- `entry.roles.build_role_request(root, *, role, task: TaskPacket|Mapping, profile: AgentProfile|Mapping, model, input_refs=(), tools=(), max_output_tokens=1024, instructions=None, context=None, data_policy=None) -> ModelRequest`。必载 intake/main/child/handoff/guide baseline，独立 system+user messages；不继承 chat。main 使用 Root 给定 decision/delegations/summary/limitations/next_actions JSON 格式，0..N 由 main 提出、由 caller 校验执行。instructions/context 进入显式 caller 数据；可承接实际 child results，没有额外磁盘扫描。请求 metadata 记录 baseline/input snapshot SHA256。
- `entry.roles.read_pinned_inputs(root, references) -> tuple[dict,...]`。只读指定 root 内 exact FileReference、同 bytes hash/revision/UTF-8快照；不递归发现或追随refs。支持每文件1MiB、总4MiB的有界文本；binary/image路径未支持。输入缺失/越根/hash/revision漂移拒绝。
- `entry.roles.document_bytes(document) -> bytes`。稳定 JSON serialization，用于实际发布bytes与pins。
- `entry.intake.compile_control_draft(root, *, response: str|Mapping, protocol_ceiling: Mapping, task_ceiling: Mapping, schema_catalog=None) -> ControlDraft`。内部输出 `{protocol,task,method?,requirements?,unknowns}`；ceilings须由caller提供人类给定的合法完整Protocol/Task，不能以模型输出自证授权。现有Schema验证两侧；不扩大权限/范围/预算/并发/深度/数据边界，不删Human gates/停止检查/required outputs，不改人类identity/goal/revision。Method task hash由compiler按将要发布的Task bytes重算；mode ID与versioned Mode ref保持现有表示兼容，完整Action/Registry closure由下游负责。
- `ControlDraft` 的 protocol/task/method/requirements/unknowns及ceilings深度只读；`.as_mapping() -> dict`。草稿不等于批准或运行资格。
- `entry.intake.persist_control_draft(root, *, directory: str, draft: ControlDraft) -> tuple[FileReference,...]`。发布前复核pins/Schema/ceilings；拒绝root逃逸/已有目录；仅新目录独占写 `project-protocol.json`、`task.json`、可选 `method.json`/`requirement-N.json`，`draft.json`明确 `status=draft`、`qualification=schema-validated-control-draft` 与unknown/限制。返回实际bytes的refs；不自动产生approved或runtime-execution。局部I/O失败保留现场，不称事务/CAS/自动重试。
- `entry.guide.build_guide_request(root, *, question, main_state_ref: FileReference|Mapping, approved_refs=(), model, max_output_tokens=1024, data_policy=None) -> ModelRequest`。独立 MainState/获准必要refs，MainState Schema/parser检查；不跟随机器refs、不接受generic主chat/context、不装Tool、无main messaging/Trace/state writer。默认 local_only；远程data policy须caller显式给定并另行授权。
- `entry.guide.ask_guide(root, *, providers: ProviderRegistry, provider_name, question, main_state_ref, approved_refs=(), model, max_output_tokens=1024, data_policy=None) -> ModelResponse`。仅调用注入provider的一次generate，经现有Registry require检查；不读Key、无history/sink/Tool handler，意外ToolCall也不执行，原response携带usage/unknown。Provider异常原样传播供caller记失败/unknown；无paid retry。Provider自身安全、预算/timeout和live资格不由此helper认证。

## 已验证与限制

最终离线定向验证：角色8 PASS、intake7 PASS、Guide3 PASS，共18。测试使用临时项目和 injected offline Provider；所有API/生产Tool/Key/账操作0。实际覆盖baseline/schema进入请求、fresh上下文、existing dataclass消费、pin/extra-input/scope/预算/Skill阻断、不可变draft、exact发布hash、Method→Task pin、既有Mode ID/version ref、模型扩权/删gate/改revision拒绝、可选Requirement及egress拒绝、Guide不跟ref/旧chat、unexpected ToolCall不执行及usage unknown保留。

首轮角色测试 fixture 遗漏原Schema的 `model_policy.class`，3 ERROR；修正fixture并定向重跑，最后8 PASS。intake首轮5 PASS、增边界6 PASS、最后既有Mode表示7 PASS；Guide初轮3 PASS，随后代码未改。失败如实保留在通信记录，不称产品failure或隐藏为一次通过。

仍未做：真正模型需求编译/研究规划器；required Skill实际加载（非空required_skills明确阻断）；完整Method/Mode/Requirement/Registry/Capability/Snapshot/Bundle/View/Host qualification；Tool execution、Native Adapter、live Provider/科研验证；自动恢复、M12/Topic5、Human approval、production Skill admission、Guide自动回main、事务/CAS。Role helper是请求装配，不能单独替代既有Runtime admission；Root/ENTRY runtime组接 exact frozen View、预算和实际结果。普通控制draft所含字符串的科学/方法适用性仍须语义审阅。

## Frozen 文件 SHA256

| 文件 | SHA256 |
|---|---|
| src/research_workbench/entry/roles.py | 083D2B619053FCCE77DF0B9896FC5EEBA407E82D5FABCE86E9F7A4BC417B017D |
| src/research_workbench/entry/intake.py | B76021EE66FD39E579AB05533F546B639AFB07CEEFB98317F48FF35DD978FBCF |
| src/research_workbench/entry/guide.py | 8BFCF458ACFAF6900E421EA0CACD10E6DA783267080BA7652B7B7E7487E8B4C9 |
| tests/test_entry_roles.py | BDAD0C1FFE161B19624B3F39080FEFEAC0B769D716564652C5542F2BB932A5A6 |
| tests/test_entry_intake.py | 46285080EEA141F953522682518DA7FD1997E6BC8121A6DBEBF7DC603E015700 |
| tests/test_entry_guide.py | 2A3C6C7B23F5919C0FD5F1A379AD33E66B1FDC971D12934AB26C64805211D583 |

Next：Root消费以上API并完成Driver/CLI/运行接合与集成测试、分支记录/PR；primary PROJECT_MEMORY仅由Root写最新own-row。此子任务交付后停止，不延伸规划器或权限体系。
