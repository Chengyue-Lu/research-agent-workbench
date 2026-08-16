# 开发协作指南

状态：当前协作入口

日期：2026-08-16

## 1. 实名维护边界

工作流名称描述技术范围，不能代替责任人的姓名。Task、ADR、PR、Handoff 和阻塞项必须写明实际负责人。

| 责任人 | 稳定身份 | 负责维护 | 不负责维护 |
|---|---|---|---|
| 路诚钺 | GitHub `Chengyue-Lu` | Research Mode 语义、组合与准入；能力词汇；Skill 发现、选择、评估、准入和退役；Resolver 选择理由；受控读取；Handoff/Agent Trace 的方法与评估规则；相关 fixtures 和文档 | Provider SDK、认证、HTTP transport、模型槽实现、API session loop、live API conformance 和 API 专用测试 |
| 黄毅 | GitHub 身份由本人登记 | Provider Adapter、模型能力协商、模型槽、隔离 API session、并行与工具调用、Task-to-API 编译、执行关闭事务、真实账户/模型 conformance 和 API 测试 | 代替研究者批准 Claim、单方面改变 Mode/Skill 语义、擅自准入 Skill 或降低 Human Gate |

共享接口包括 Task Packet、Resolved Task、Skill Assignment、Handoff Packet、Execution Receipt、Agent Trace Envelope、Capability/Data Policy 和错误/停止状态。共享接口变更必须由路诚钺与黄毅共同确认 owner、迁移影响和合并顺序；不能用“本侧”“同伴侧”作为审批主体。

Agent 不是责任主体。每个运行中的 Agent 使用稳定 `actor_id`，并在 Attempt Archive 中绑定 `accountable_owner: 路诚钺 | 黄毅 | <其他实名>`。模型名、窗口名或临时 Agent 昵称不能替代人类负责人。

## 2. 当前开发节点

路诚钺当前维护分支为 `agent/mode-skill-selection-baseline`，目标节点是 `K-MS-1 Mode–Skill Selection Baseline`：

1. 为现有 Mode 建立 trigger、non-trigger、组合与歧义 fixtures；
2. 建立 Task → Mode → capability → deterministic/no-Skill/Skill 的可解释选择矩阵；
3. 审核三个 accepted Skills 的适用边界；
4. 对一个 triage candidate 作证据化去留决定；
5. 在相同 fixture 上比较 H0/H1/H2 和读取成本；
6. 使用完整 Attempt Archive 留存 Agent 间实际传递内容，但只将紧凑 Handoff 加载回主上下文。

达到上述节点后暂停评审，不批量新增 Mode/Skill，也不在此分支修改 API 实现。详细验收见 [Mode–Skill 实施计划](implementation/MODE_SKILL_WORKSTREAM_PLAN.md)，状态以[任务清单](TASKS.md)为准。

黄毅的 API 工作流已在离线 fake-local Gate 中完成 `K-API-2` 的 evidence/H2 与 simulation/H1 双合同路径：冻结 Task/Profile/Skill/输入和 Model Assignment，只通过受控 Tool Registry 构建工具，持久化五种终态，自动生成诚实声明 capture gap 的 Trace，以 Main State 最后提交，并在 H1/H2 fresh Python 子进程中恢复。`M3-007`、`M3-008` 和 `M6-006` 已完成；`M6-003` 仍为 `IN_PROGRESS`，真实 Provider Gate 尚未通过。离线通过不等于真实 Provider 或科研正确性证据，也不构成路诚钺工作流的完成证据。

## 3. 开始一个开发 Task

1. 读取根目录 `AGENTS.md`、本文件和 `TASKS.md`。
2. 只读取 Task 指向的模块、专项计划、Profile、Skill 与输入；不要从全仓库扫描恢复上下文。
3. 在目标路径创建 `work/<task-id>/<attempt-id>/`，写入 Task、actor 映射、允许读取集、写入范围和输出契约。
4. 所有跨 Agent 发送内容先进入 `messages/` 再发送；收到的可见内容在继续处理前归档。所有运行时可观察的文件读取、工具调用、命令、外部动作和结果进入 event/tool trace。
5. 每个 Agent 只读取自己的 Assignment、允许内容和显式引用的历史消息。`INDEX.yaml` 可以用于发现，但消息正文不是默认上下文。
6. 完成时写 Handoff、验证证据和紧凑 `WORKLOG.md`；Worklog 是导航摘要，不是完整 Trace 的替代品。

完整目录与消息信封见[工件与溯源](modules/07-ARTIFACTS_AND_PROVENANCE.md)，H0/H1/H2 规则见[Task 与 Handoff](modules/05-TASK_AND_HANDOFF.md)。

当前自动 API recorder 已覆盖 Assignment/Handoff、Provider/工具边界、受控读取结果和 closeout revision；它不自动观察启动前的所有文件读取、shell 命令或平台消息。调用方必须捕获这些事件，或在不可得时以明确的 capture gap 关闭，不能仅因 INDEX 结构有效就宣称 Trace `complete`。

## 4. 完整留存与克制读取

“留存”与“读取”是两个独立策略：

- 默认留存所有 Agent 间可见传递：Assignment、澄清、范围扩大、进度、Handoff、review、拒绝/接受和确认；
- 默认留存所有可观察的工具/命令调用及结果、正文读取路径与哈希、文件写入修订、正式/中间输出、检查结果、失败、取消和安全暂停；不可变文件已经有路径和哈希时不重复复制正文；
- Attempt 内的过程文件采用追加或新 revision，不能因“最终没采用”而静默覆盖/删除；确需删除时保存 tombstone、旧哈希与原因；
- 不留存隐藏 Chain-of-Thought、密钥、认证头或因法律/数据政策禁止保存的内容；发生删减时必须留下 redaction/omission 记录；
- 主 Agent 默认只读取 Task、当前状态索引和 Handoff；排查或评估时再按 message ID 拉取原文；
- 大输出只传工件引用时，Trace 保存当时实际发送的引用和哈希，不重复复制整份工件；瞬时工具结果若没有稳定来源，则保存脱敏后的原始结果；
- 完整 Trace 的保留期限与是否进入 Git 由 Project Protocol 决定。敏感或大型运行档案默认留在项目工作区，不直接提交公共仓库。

这样既能在优化、争议和故障排查时重放过程，也不会把所有历史消息重新灌入主 Agent 上下文。

## 5. Handoff 分级

- `H0`：无跨 Agent 传递；仍保存 Task、输出、检查和 Worklog。
- `H1`：普通跨 Agent 任务；主 Agent接收 Compact Handoff，但完整消息流继续归档。
- `H2`：压缩、关键 Evidence/Claim/Decision promotion、外部副作用、长等待/会话销毁、摘要争议或 Task 明确要求时，在 H1 之上增加 Manifest/Audit，并按需增加 Snapshot、Receipt 与语义抽样。

H1/H2 的差异是回传主上下文和审查强度，不是“是否保存过程”。任何等级都不能丢弃已经发生的 Agent 间传递。

## 6. 分支、写入与交付

- `main` 只保存双方确认的稳定文档、接口与已验收实现。
- 路诚钺的 Mode–Skill 工作使用 `agent/mode-skill-*`；黄毅的 API 工作使用独立、可识别的分支，并在 PR 中写明姓名与范围。
- 同一时间只有明确的接口 owner 修改共享 Schema、`cli.py` 或同一 Registry 索引。
- 并行 Task 必须声明互斥写入路径；无法隔离的修改串行完成。
- Handoff 必须给出基线提交、实际修改路径、验证证据、未证明内容和唯一下一动作。

若 API 执行便利性与 Mode/Skill 方法边界冲突，采用更严格边界并请求人工决定。黄毅维护的执行层不能因 Provider 限制静默删除 Skill 要求；路诚钺维护的方法层也不能要求执行层绕过预算、数据或工具限制。

## 7. 当前已知缺口

- Agent Trace Envelope/Index/Event Schema、validator/CLI 和 API 自动捕获已离线通过；不可得过程必须保持显式 gap，不得伪装 complete。Trace 语义、最小字段和 Mode/Skill 评估消费方式仍由双方共同维护。
- 真实 OpenAI Gate 仍未执行；当前机器没有 `OPENAI_API_KEY` 和 `RWB_WORKER_MODEL`，所以只能记为 pending/not-run，不能从离线 fixture 推断真实兼容。
- 尚无真实运行数据证明 H1/H2 的净收益；不能把消息数量、Trace 完整度或审计工件数量当作质量本身。
- 当前只有两个正式 Mode、三个 accepted Skills，且真实 with/without 证据不足。
- 黄毅的 GitHub 身份尚未登记在本文件；登记后应替换占位说明，不应猜测账号。
