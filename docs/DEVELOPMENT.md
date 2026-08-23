# 开发协作指南

状态：Stable contributor rules
更新：2026-08-23

## 1. 实名维护边界

工作流名称描述技术范围，不能代替责任人的姓名。Task、ADR、PR、Handoff 和阻塞项必须写明实际负责人。

| 责任人 | 稳定身份 | 负责维护 | 不负责维护 |
|---|---|---|---|
| 路诚钺 | GitHub `Chengyue-Lu` | Method/Core 语义；Mode/Action/Method Resolution；能力词汇；Skill Need、评估、准入和退役；Research State/Claim/Method Trace 规则；受控读取及相关 fixtures/docs | Provider SDK、认证、HTTP transport、模型槽实现、API session loop、live API conformance 与 API 专用测试 |
| 黄毅 | GitHub `let778750-cpu` | Provider Adapter、模型能力协商、隔离 API session、Task-to-API 编译、执行关闭事务、真实账户/模型 conformance 与 API 测试 | 代替研究者批准 Claim、单方面改变 Mode/Skill 语义、擅自准入 Skill 或降低 Human Gate |

Agent 不是责任主体。每个 Agent 使用稳定 `actor_id`，并在 Attempt Archive 中绑定具名 `accountable_owner`；模型名、窗口名和临时昵称不能替代人类负责人。

## 2. 开始一个开发 Task

1. 读取根目录 `AGENTS.md`、本文件和 [`TASKS.md`](TASKS.md)；
2. 确认基线提交、负责人、原子边界、允许读取集、写入范围、输出和停止条件；
3. 只读取 Task 指向的模块、计划、Profile、Skill 与输入，不从全仓扫描恢复上下文；
4. 在 `work/<task-id>/<attempt-id>/` 建立 Task Archive；
5. 完成时写 Handoff、验证证据和紧凑 `WORKLOG.md`。

实时工作项只在 [`TASKS.md`](TASKS.md) 更新；依赖和阶段 Gate 只在 [`ROADMAP.md`](ROADMAP.md) 维护；实现覆盖只在 [`STATUS.md`](STATUS.md) 汇总。

## 3. 留存与克制读取

- 所有 Agent 间可见传递先归档：Assignment、澄清、范围变化、进度、Handoff、review、确认、失败和取消；
- 所有可观察的正文读取、工具/命令调用、外部动作、结果和文件修订进入 event / tool trace；
- 不保存隐藏推理、密钥和认证头；受政策限制的删减必须留下 omission 记录；
- 主 Agent 默认只读取 Task、当前索引、风险和 Handoff，排查时再按 ID 拉取原文；
- 不可变大工件使用路径和哈希引用；进入上下文但没有稳定来源的瞬时结果必须脱敏持久化；
- Worklog 是导航摘要，不替代消息与事件档案。

## 4. Handoff 分级

- `H0`：无跨 Agent 传递；仍保存 Task、输出、检查和 Worklog。
- `H1`：普通委派；主 Agent 接收 Compact Handoff，完整消息流留在 Archive。
- `H2`：压缩、Evidence/Claim/Decision 提升、外部副作用、长等待、争议或显式策略触发时，增加 Manifest/Audit，并按需增加 Snapshot 与 Receipt。

分级改变回传主上下文和审查强度，不改变“过程必须留存”的原则。

## 5. 共享接口与分支

共享接口包括 Task、Method Resolution、Resolved Capability Snapshot、兼容期 Assignment、Handoff、Receipt、Trace、Capability / Data Policy 和错误/停止状态。

- 核心对象身份、路由语义、人类权威或运行时所有权变化必须先有 ADR；
- 共享 Schema 变更必须说明 owner、语义版本、迁移影响、消费方和合并顺序；
- 同一时间只有明确 owner 修改同一共享 Schema、CLI 区域或 Registry 索引；
- 并行 Task 声明互斥写入路径，无法隔离时串行；
- `main` 和 `develop` 禁止直接 push、force push 与删除；所有改动经过 PR、必需 CI 和至少一名
  非作者的另一位 accountable owner 审查；
- 功能/文档分支从最新 `develop` 创建或 rebase，PR 目标为 `develop`，并以 squash merge 合入；
- 一个完整 workstream 在 `develop` 完成集成验证后，只通过同仓库 `develop → main` PR 发布，
  该发布使用 merge commit 形成清晰边界；`main` 不接受其他来源分支；
- 不设 hotfix 绕过路径；紧急安全修复同样先进入 `develop` 并通过相同门禁；
- [`docs/workstreams/`](workstreams/README.md) 记录过程与证据，Git branch 隔离代码；同一原子
  workstream 不为每次微调另建分支，但每个独立 workstream 仍使用一个受控分支；
- Handoff 给出基线提交、修改路径、验证证据、未证明内容和下一动作。

执行便利性与方法、权限或数据边界冲突时，采用更严格边界并请求人类决定；任何一侧不得替另一侧静默定义 fallback。

### 5.1 PR 类型与 TASKS 授权

| PR class | base | 允许的任务治理变化 | 合并方式 |
|---|---|---|---|
| `feature` | `develop` | 可更新未完成任务的进度状态；不能改任务/依赖/验收或置 `DONE` | squash |
| `task-definition` | `develop` | 仅文档、需维护者标签；可新增或调整未完成任务，不能同时置 `DONE` | squash |
| `task-closeout` | `develop` | 独立 closeout、需维护者标签；只可把列明任务从非 DONE 置 DONE，并提交验证/history 证据 | squash |
| `release` | `main` | 只能来自同仓库 exact `develop`；不重新授权新的任务重定义 | merge commit |

所有 PR 必须填写 [PR 模板](../.github/pull_request_template.md)中的 Task ID、workstream、base SHA、
契约/权威影响、风险和 clean-checkout 验证。`governance/task-definition` 与
`governance/task-closeout` 标签只表示进入对应审查路径，不能替代另一位 owner 的批准和必需 CI。
已 `DONE` 行不可降级或改义。

仓库内的治理检查负责验证来源拓扑、PR 元数据和 TASKS diff；GitHub ruleset 负责阻止直推、要求
Code Owner 审查和必需 checks。两者都配置完成才构成有效保护。

## 6. 变更检查清单

- 变更属于 stable、status、planning、compatibility 还是 history 表面？
- 是否改了对象含义、版本、消费者或迁移要求？
- Task 与 Archive 是否记录负责人、读写范围和消息？
- 示例是否代表当前推荐路径，而不是旧工件回放？
- 确定性测试是否覆盖新增不变量与错误路径？
- 文档链接、示例、Schema/Registry 验证和完整测试是否通过？
- 是否明确未证明科学正确性、真实 Provider 兼容性或机制净收益？

实现协议见[implementation 索引](implementation/README.md)，架构决定见[ADR 索引](decisions/README.md)，历史材料见[历史与审计](history/README.md)。
