# M6-013 Slice 001：显式版本与 producer→consumer 迁移表

依据 [ADR-0027](../../../decisions/0027-USAGE-RECORDING-AND-MODEL-WORKING-INPUT.md)、[兼容边界](../../../compatibility/BUDGET_CONTRACT_MIGRATION.md)。基线 `76fd3d8`；下列目标版本均为候选工程决定，未正式接受或成为默认。旧版的 schema identity、原件、hash、测试与历史 live grant 解释不变。

## 三类边界

- 经济控制：Task.budget/delegation.sub_budget、Policy.budget_ceiling、View.effective_constraints.budget、Session 总 token/Provider cost cap 与 workflow reserve/held。新通用执行取消其必需性和余额/预占/unknown holds 阻断；未知用量作为独立事实，不能单独否认有效交付。
- 技术与治理：真实模型窗口、接口必需输出参数、传输超时/容量、取消、实际失败、权限/data-egress/side-effect/refs/资格/Human Gate、授权深度/并行保持。旧 max_seconds/max_turns 名称不能自动当成真实技术极限，需要实际接口依据与显式新字段。Protocol 中并行/深度从 budgets 移至治理字段，费用比例指标单独作观察信息。
- 历史 live grant：继续使用原版本/精确授权/模型/窗口/金额或 token 边界，既有账/失败证据保持。产品方向不增加付费授权，不将旧 grant 转换成新无限制执行；本切片没有读实际 grant/账原件。

## 固定源、候选目标与接合

| 生产者 → 消费者 | 当前源版本与耦合 | 候选目标 | 首切片实际状态 / 后续要求 |
| --- | --- | --- | --- |
| Protocol/Task producer、intake `compile_control_draft` → TaskPacket/roles/factory | Schema 0.1.0；Protocol.budgets 与 Task.budget 必填，Task.delegation.sub_budget；compiler `_budget` 检查 | Protocol/Task Schema 0.2.0；保留治理深度/并行及权限/交付；无必需经济字段 | **未写新 Task/Protocol Schema。** intake 仍要求模型输出完整旧 Schema；需新 draft 工作契约和程序装配 v0.2.0，不能仅不提供 budget 或改大数字 |
| Data/Host Policy producer → `produce_resolved_execution_view` | execution-policy Schema 0.1.0 必需 budget_ceiling | execution-policy Schema 0.2.0；其他最严边界不变 | 未实现。先版本分派、精确 policy pins；旧 policy 对新 View 不可默默松绑 |
| Task/Profile/Policy/Snapshot/Binding/Bundle → View producer | resolved-execution-view Schema 0.1.0；`_intersect_budget` 拒绝无 ceiling，effective_constraints.budget 必填 | View Schema 0.2.0；移除经济交集，保持权限/data-egress/side-effect/资格/freshness | 未实现。producer 与 loader/Host 必须同一闭包分派；Bundle manifest Schema 0.1.0 升至 0.2.0 候选，明确允许的新旧文档集合 |
| View/Driver → `execute_frozen_view` / actual report → generic closeout | execution-host-report/generic-execution-receipt Schema 0.1.0；Host `HOST-BUDGET-VIOLATION`，facts complete 影响 closeout | Host/Receipt Schema 0.2.0；usage completeness 独立于 execution/delivery completeness | 未实现。不能改旧 complete 字段解释。需新 usage facts/unknown 表达、实际响应/产物/Trace 与资格检查独立，action-only task_completion 仍 false |
| `FrozenRoleExecutor`/Driver → ApiSession runner / Provider | ApiSessionLimits 是未独立版本化的 Python API；conformance policy/summary 1.0.0；总 token/cost 和未知 tokens 终止 | 并列 `ApiSessionControls` contract_version 2.0.0 候选；必要时 conformance policy 2.0.0，旧 1.0.0 保留 | 未实现。将实际 cancellation/技术容量/真实超时与经济控制拆开，保持 Tool side-effects；unknown usage 只作记录 gap。拒绝用极大限制值伪装改版 |
| workflow/main child proposals → factory/executor → parent observations | WorkflowBudget/RoleInvocation 旧未独立版本化 Python 结构，reserve/held、max_calls；factory 固定 Schema 0.1.0 | workflow controls / invocation contract_version 2.0.0 候选；运行事实独立关联 | 未实现。不能把旧测试的 holds 期望删除或改标；main/child 新输出不产生 budget，由程序装配 exact Task/Method/Supply/View |
| 已验证 Task 0.1.0 + admitted snapshots + 明确 stops → **本投影模块** | 原 Task 仍按自身 v0.1.0 校验；完整控制对象留 caller | **model-working-input Schema 0.2.0**（已落盘候选） | 只产生新数据契约。 source_task.schema_version 明示 0.1.0，未知/候选 Task 0.2.0 目前拒绝；不重新解释旧控制、grant 或 gate |
| 投影 → roles.build_role_request/intake_call/Guide/short/maintenance | 当前 roles 仍序列化完整 Task/context、注入旧控制输出 Schema 和 budget baseline | opt-in model-working-input 0.2.0 请求 + 版本绑定职责 baseline | **未接入。** 先版本选择和门槛，再换装 payload；不得把任意 caller_context 声明已验证。职责 baseline 与 intake/main 输出 Schema 也需新版本 |
| Schema/source → Catalog/RuntimeResources/build/installed API/CI | 默认 SchemaCatalog 0.1.0；目前发行/consumer 映射按原闭包 | opt-in catalog/resources + explicit version dispatch | 只新增 checkout 的独立 Schema，未改默认 Catalog/安装资源/backend/CI。Root 需映射新增直接测试，结合当前 P2 修复串行处理 |

## 可分离契约与精确设计缺口

可以独立证明的边界是**数据投影**：候选 0.2.0 自包含 Schema，无外部 $refs、无完整 Task/Policy/ledger 字段，所有 authority boundaries 固定 false，输出数据不会调用 Core。已有 v0.1.0 文件一字不改；纯函数 rechecks 已提供 UTF-8 text 的 hash 与 Task exact refs，但不读文件、不判 admission 或科学正确性。

无法在本写域发布 Task/Policy/View/Host/Session 的可执行 0.2.0：TaskPacket parser 必取 budget；intake 校验和模型输出 Schema 仍要求它；View 必取/相交 budget；Host 必取并判超限；Session 与 workflow 仍有 usage-unknown/经济终止；factory 和资源选版固定。这些点必须由 Root 串行迁移并给双版本正反证据。在消费者闭包缺失时，只落盘一个删字段的 Task Schema 会制造假兼容，因此本切片没有这样做。

旧 free-form safe_pause/stop 字符串混有 reserve/经济要求。模块不猜测其语义、不删词，而要求 caller 显式给 actual stop 的 kind/condition；旧调用的经济规则仍由旧 caller/Host 执行。新 work baseline 也应版本化；传入旧 budget-management baseline 不会被程序秘密改写。

main 的 actual child/Handoff、profile choices、intake draft schema 和 Guide approved-state 还需要明确的版本化工作槽。当前模块不消费任意 context；不能通过把全 context 放入 necessary_decisions 或原文件默认注入来接通。费用原文在 goal/materials/statement/condition 保留；如果任务明确请求费用记录，该材料仍必须经独立授权与 exact pins 输入。

## 接合顺序和 Root 验证

1. Root 运行本切片独立测试（投影白名单、prose 保留、stale/outside/duplicate、nested extras、实际 stop 类型、Schema/new boundaries、旧 budget 仍必需）。当前仅测试代码与静态语法检查。
2. 冻结 Task/Protocol/Policy/View/Host/Session/version dispatch 的新闭包与显式迁移记录；保留旧 bytes/pins，旧→新不得自动产生新的 permission/grant/execution facts。
3. 串行接模型输入和职责/输出契约，给实际 outbound request 差异与全消费者测试；M6-011 记录增强独立接合，不能把记账缺口升级成通用停止门槛。
4. 最后 opt-in installed resources/CI 和真实适用 Gate。此切片不推断 M6-013 DONE、M11-010 通过或 Source/Human/Skill/live 资格。

