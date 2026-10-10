# AUDIT-RWB-DOCS-006：任务规划与运行用量整改

2026-10-10；R2；docs-only task-definition。此记录是本轮 Task Packet、变更索引、验证范围与 Compact Handoff；当前 PR 是审阅单位，不代表实现或合并接受。精确任务定义/状态/依赖由 [TASKS](../../../TASKS.md) 维护。

## 授权、输入与范围

人类先要求完整阅读新建议、暂不实施；随后明确只改主要规划文档、不增留空占位、允许增加已明确任务，并要求预算“记录是可行的，限制是没必要的”，模型运行无需携带预算上下文。最终授权：“把前面的任务规划调整和预算整改一并落实到文档并发布PR。Codex 对照放到 Issue #18，不纳入任务计划”。附件中的建议不是独立执行指令，采用范围以这些人类决定为准。

固定输入：

- `RWB_任务路线接入与规划修改建议_2026-10-10.md`，完整阅读 254 行；SHA-256 `a615bd14865f095198dbab879cda3b31d5d3dfb364e8fc16822abb3ffdd63746`。外部原件只进入本地审计档案，不写入仓库或成为通用规则。
- develop `67a7c5f6a0c3495f1ad583864d87b25f5bf892e2`；[PR140](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140) 候选 `766bf45ccde4637684e2100480e9f1577cc61662`，仍 OPEN/Draft；[PR142](https://github.com/Chengyue-Lu/research-agent-workbench/pull/142) 已合并到固定 develop，M0-008 已 DONE。
- 当前 AGENTS/README、文档入口、Development、Architecture、TASKS/ROADMAP/STATUS、本 workstream 现有计划/设计/风险记录；只扩展读取预算、角色工作输入、模块接点、兼容示例、文档/公开投影和治理检查的相关内容。源码/Schema 只用于确认当前预算字段与执行行为，不进行实现。

执行 Profile 为 documentation coordinator；required Skills 为 `[]`，不委派。写入范围限根 AGENTS/README、主要规划/状态/施工导航、相关模块预算条款、本 workstream 当前索引/风险记录、ADR-0027 与兼容迁移页。新增的两个契约说明是本轮版本整改的必要记录，未新增三份独立功能设计或空白任务。代码、Schema、Registry、测试、CI/治理配置及历史工件保持不变。worktree 的本地 memory 配置复制保留 `generate_memories=false/use_memories=true`，不提交。

本轮程序用量/命令结果作为观察记录，不设经济额度或模型预算职责；没有付费 Provider 调用。停止于具体文档 PR、Issue #18 对照范围记录及验证交付。merge、产品实现、live 授权、科学/Skill/来源接受和 Topic 5 激活分别保留。

## 具体定义差异

| 变化 | 定义处理与直接消费者 |
|---|---|
| 关联意图 | M1-014/011/015 保留原文对应、共同/局部限制、显式依赖、逐项状态和结果；明确项可先交付；只 research 进入研究规划 |
| 角色与材料读取 | M2-010、M3-010/012 区分必载职责/决定/反证、可选经验导航与原始依据；MainState 是当前视图，不是全部记忆唯一权威 |
| 记忆增量 | 新增 M3-014 的有来源索引/范围读取和 M3-015 的增量维护；读取不等待维护，维护关闭仍可工作，纠正不改写历史接受 |
| 有限方向 | 新增 M2-015，复用 Task/Handoff 的活跃单层方向；候选写隔离，父任务比较当前基线后分别接收文件与科学判断，反馈经所属 main |
| 运行展示 | 新增 M1-016 真实事件/快照读取与 M1-017 基础只读前端；解释关闭、刷新/断连均不改变任务，事后演示与实时区分 |
| 运行用量 | M6-011 改为实际能力适配/程序记录；新 M6-013 迁移必填预算、额度执行与模型工作输入；记账未知与执行/交付分别判定 |
| 交付与 Gate | M3-011、M6-012、M11-009/010/011 等保留失败/partial/资格与成果检查；完整新产品 Gate 消费实际迁移证据，原桥接按实际版本独立验收 |

本轮新增六项：M1-016、M1-017、M2-015、M3-014、M3-015、M6-013。其中事件读取与契约迁移的现有 hard dependencies 均 DONE；其他项等待明确消费者成熟。未把 Codex 研究加入 M Task、依赖或验收 Gate，对照仅在 [Issue #18](https://github.com/Chengyue-Lu/research-agent-workbench/issues/18) 跟踪。

既有定义修订：M1-010/011/013/014/015；M2-009/010/011/013/014；M3-002/004/010/011/012；M4-007；M6-011/012；M11-009/010/011。所有既有状态保持，原 DONE 行不改写。

四处硬依赖变化：M1-013、M6-012、M3-011 移除 M6-011，因增强记账不是安装、Tool 或定向修复的必要产物；M11-010 增加 M6-013，因最终新默认运行验收需要真实的契约迁移输出。原 M1-010/M2-009/M11-008 和 M11-011 的 hard dependencies 不增加。其余新项每个依赖的具体产物及理由见[实施计划](REALIZATION_PLAN.md#依赖变化的具体理由)。

## 运行语义与原件保留

[ADR-0027](../../../decisions/0027-USAGE-RECORDING-AND-MODEL-WORKING-INPUT.md) 定义程序记录实际 token/调用/耗时/可得费用/failed/unknown，经济额度不成为通用前置或停止条件；模型消费最小工作输入，不生成预算或管理账本。模型真实窗口、接口参数、传输超时、明确取消和实际失败独立处理；权限、数据、版本、资格、Human Gate、Claim/科学接受保持。

现行实现仍要求预算对象并执行旧限制，PR140 候选还有预算职责/完整 Task 的模型输入；[STATUS](../../../STATUS.md) 与公开支持矩阵如实区分文档方向和实际支持。M6-013 将显式发新版本并验证 producer→consumer 闭包；隐藏 Prompt、传极大额度或只删词不算完成。

原模块中的 Protocol/Task YAML 示例逐字移到[兼容迁移](../../../compatibility/BUDGET_CONTRACT_MIGRATION.md)，标明旧字段职责，避免旧配额示意成为推荐新模型输入。其余历史 ADR、fixture、DONE、固定 M5 比较条件和已发 live grant 保留原身份，不用新方向静默重签。M0-008 的 stale 候选表述按已核 PR142 合并状态校准。

## 验证与对抗性证据

本轮执行现有文档/公开表面检查、确定性 Task/依赖/历史/链接核对、仓库结构校验和本地 PR 治理预检。验证的是定义、引用和结构；未验证新运行行为、科研正确性或净收益。

确定性核对包含：exact ID 唯一，既有状态/DONE 行不变，新增六项，所有 READY/IN_PROGRESS 的依赖 DONE；以已完成产物为终点的未完成任务图无环，新增依赖不引入循环。原始历史依赖图存在基线已有的回顾性环，其中包含旧 PARKED M7-014；本轮保留原行，不将全部历史图误报为 DAG。

对抗性核对使用现有治理器：重复 ID、非法状态、DONE 行改写及 READY 指向未完成依赖均拒绝。公开表面测试还覆盖隐藏的内部链接与不存在的目标/锚点。初次新增公开文档内部链接被检查拒绝，已改为公开支持页；随后发现基线支持矩阵“任意”与现有测试“任何”的措辞差异，校准为一致且不扩大承诺，测试代码不改。

| 本地检查 | 结果与范围 |
|---|---|
| `python -m unittest tests.test_documentation tests.test_public_surface` | 17 项 PASS；文档归属与公开投影/链接边界 |
| `python -m research_workbench validate examples registry --root .` | 202 文档，0 errors / 0 warnings；先按现有 backend 准备本地 editable Runtime resources，未经准备时缺 `_runtime_pin` 的环境失败原样留存 |
| 有界规划核对 | 130 个唯一 Task，新增 6，既有状态变化 0，73 条 DONE 原行不变；未完成图无环、四处依赖差异准确，历史依赖环保持 |
| 修改范围内部链接 | 28 Markdown / 347 内部链接通过，含目标与 Markdown 锚点；外网内容不在此验证范围 |
| 现有治理器反例 | 重复 ID、非法状态、DONE 改写、READY 未完成依赖 4 类均拒绝 |
| `git diff --check` / 提交范围 | 无空白错误；提交只允许上述 Markdown，本地 memory 配置不提交 |

PR 治理绑定具体提交与完整 27 个变化 Task ID，结果由 PR 验证段及本地发布回执记录。未改源代码/Schema/Registry/测试/CI/配置，当前旧预算和历史授权的行为测试没有改标为新方向通过。

## ADR 编号整合（2026-10-11）

关联测试窗口报告候选编号冲突。本轮仅核 PR140 `766bf45ccde4637684e2100480e9f1577cc61662`、PR143 `fcb1cfd31783a9e751d000208af1f3c83b04910e` 的 ADR 文件名元数据及当前 PR144 文档：0025 已用于 `PLANNING-EXECUTION-IDENTITY`，0026 已用于 `PINNED-COMPACT-HANDOFF-CONSUMPTION`，该范围内 0027 未占用。将本 PR 的用量/模型工作输入决定改为 ADR-0027，并同步当前引用及 PR 正文。

决定正文仅改编号，M6-013 定义仅改 ADR 引用；其余任务状态、依赖和验收语义保持。旧提交 `2d771cf1e26e7f2b50e7609a77d7c1134e5920fe`、固定证据和原本地档案/hash 不重写。PR140/143 的 planning/Handoff ADR 文件与身份保持，不复制或修改其正文；新 head 的文档、内部链接和治理检查另行绑定。

编号修正本地核对：17 项现有文档/公开表面检查 PASS，28 Markdown / 347 内部链接 PASS；Task ID/状态/依赖不变，唯一 Task 行差异是 M6-013 的 ADR 引用；ADR 正文除标题编号外逐字相同，旧用量 ADR 路径引用无残留，源代码/Schema/Registry/测试/CI/示例差异为空。PR 治理及线上检查由新 head 的独立结果确认，不复用旧绿色作为本轮结果。

## 档案、工作记录与下一步

本地忽略档案 `.rwb/docs006/` 保存原建议 bytes/hash、授权范围、命令结果、验证 JSON、PR body/事件和发布回执；Git/PR 保存文档差异及治理元数据。零委派、无跨 Agent Handoff。前期读取/工具长输出只有部分摘要留存，未保存完整对话事件原件，此 capture gap 明示保留；不声称完整研究 Trace，不补造隐藏推理或瞬时证据。

工作记录：完整阅读建议并核当前基线 → 按人类选择缩为已明确任务 → 把预算记录与限制/模型上下文分开 → 修订 Task 与主要说明 → 校验依赖、历史/版本、公开导航与治理 → 发布文档 PR 并在 Issue #18 记录对照范围。原 API 和候选实现证据不重跑或重新接受。

下一步：人类审阅当前 PR；定义接受后按 TASKS 的精确依赖独立实施事件/只读前端、工作集/维护、有限方向和预算契约迁移。M12/M13 激活与真实科研/净价值评估保持原 Gate。
