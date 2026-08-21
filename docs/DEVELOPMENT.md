# 开发协作指南

状态：当前协作入口

日期：2026-08-20

## 1. 实名维护边界

工作流名称描述技术范围，不能代替责任人的姓名。Task、ADR、PR、Handoff 和阻塞项必须写明实际负责人。

| 责任人 | 稳定身份 | 负责维护 | 不负责维护 |
|---|---|---|---|
| 路诚钺 | GitHub `Chengyue-Lu` | Method/Core 语义；Mode/Action/Method Resolution；能力词汇；Skill Need、选择、评估、准入和退役；Research State/Claim/Method Trace 方法规则；受控读取及相关 fixtures/docs | Provider SDK、认证、HTTP transport、模型槽实现、API session loop、live API conformance 和 API 专用测试 |
| 黄毅 | GitHub 身份由本人登记 | Provider Adapter、模型能力协商、模型槽、隔离 API session、并行与工具调用、Task-to-API 编译、执行关闭事务、真实账户/模型 conformance 和 API 测试 | 代替研究者批准 Claim、单方面改变 Mode/Skill 语义、擅自准入 Skill 或降低 Human Gate |

共享接口包括 Task Packet、集成候选 Method Resolution/Resolved Capability Snapshot、兼容期 Resolved Task/Skill
Assignment、Handoff、Execution Receipt、Agent/Method Trace、Capability/Data Policy 和错误/停止状态。
共享 Schema 变更必须单独说明 owner、语义版本、迁移影响、消费方和合并顺序；路诚钺与黄毅共同
确认跨 Method/Execution 边界的修改。不能用“本侧”“同伴侧”作为审批主体。

Agent 不是责任主体。每个运行中的 Agent 使用稳定 `actor_id`，并在 Attempt Archive 中绑定 `accountable_owner: 路诚钺 | 黄毅 | <其他实名>`。模型名、窗口名或临时 Agent 昵称不能替代人类负责人。

## 2. 当前开发节点

`K-MS-1` 已冻结为历史离线选择/治理基线。第二轮审计后，全局进入
`K-METHOD-1 Method Core Formalization`：

1. M8-001 重整稳定架构、文档真值与依赖路线；
2. M8-002 正式化两个现有 Mode 的 Action；
3. M8-003 建立 provider-neutral Method Resolution，并转换八个 routing fixtures；
4. M8-004 通过最小 migration seam 迁移 Research Mode v0.1 → v0.2，删除直接 Skill recommendation；
5. M8-005 冻结 Decision Authority 并接入 validator/preflight；
6. 到达 K-METHOD-1 后再启动统一 Evaluation Manifest、Method Trace 或 Skill trial。

M8-002..006、M6-003 与黄毅侧 M3-008/M6-006 当前只在同一独立集成候选中，不得绕过双方
shared-interface review 直推 `main`。Execution/Archive Trace 与 Method Trace 仍严格分层；`K-MS-1` 的原始计划和 dossier 保持只读历史，不再
作为当前开发入口。阶段依赖见[架构路线图](ROADMAP.md)，实时状态只见[任务清单](TASKS.md)。

## 3. 开始一个开发 Task

1. 读取根目录 `AGENTS.md`、本文件和 `TASKS.md`。
2. 只读取 Task 指向的模块、专项计划、Profile、Skill 与输入；不要从全仓库扫描恢复上下文。
3. 在目标路径创建 `work/<task-id>/<attempt-id>/`，写入 Task、actor 映射、允许读取集、写入范围和输出契约。
4. 所有跨 Agent 发送内容先进入 `messages/` 再发送；收到的可见内容在继续处理前归档。所有运行时可观察的文件读取、工具调用、命令、外部动作和结果进入 event/tool trace。
5. 每个 Agent 只读取自己的 Assignment、允许内容和显式引用的历史消息。`INDEX.yaml` 可以用于发现，但消息正文不是默认上下文。
6. 完成时写 Handoff、验证证据和紧凑 `WORKLOG.md`；Worklog 是导航摘要，不是完整 Trace 的替代品。

完整目录与消息信封见[工件与溯源](modules/07-ARTIFACTS_AND_PROVENANCE.md)，H0/H1/H2 规则见[Task 与 Handoff](modules/05-TASK_AND_HANDOFF.md)。

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
- 路诚钺的 Method/Core 工作使用 `agent/method-*`；历史 `agent/mode-skill-*` 不继续扩张。黄毅的 API 工作使用独立、可识别的分支，并在 PR 中写明姓名与范围。
- 同一时间只有明确的接口 owner 修改共享 Schema、`cli.py` 或同一 Registry 索引。
- 并行 Task 必须声明互斥写入路径；无法隔离的修改串行完成。
- Handoff 必须给出基线提交、实际修改路径、验证证据、未证明内容和唯一下一动作。

若 API 执行便利性与 Mode/Skill 方法边界冲突，采用更严格边界并请求人工决定。黄毅维护的执行层不能因 Provider 限制静默删除 Skill 要求；路诚钺维护的方法层也不能要求执行层绕过预算、数据或工具限制。

## 7. 当前已知缺口

- M3-008 的四类 Execution/Archive Trace Schema、单写者 recorder、validator 与 CLI 已在本地集成候选实现；仍须由路诚钺审查 shared 语义并通过故障矩阵，Method Trace 继续等待 M8-003/005，不能塞回同一事件层假装完成。
- API session 与平台 Adapter 的自动 Trace 写入属于黄毅的执行实现范围；执行端只消费冻结接口，不自定义 Mode/Claim/Skill fallback。
- Mode Action、Method Resolution、Decision Authority 与 Resolved Capability Snapshot 已有集成候选 Schema/validator，但尚未共同审查合入；长期 Research State 仍未实现。
- 尚无真实运行数据证明 H1/H2 的净收益；不能把消息数量、Trace 完整度或审计工件数量当作质量本身。
- 当前只有两个正式 Mode、三个历史 accepted Skill 条目且 active 为零；真实 with/without 证据不足。
- 黄毅的 GitHub 身份尚未登记在本文件；登记后应替换占位说明，不应猜测账号。
