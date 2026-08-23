# 开发协作指南

状态：Stable contributor rules
更新：2026-08-23

## 1. 实名维护边界

工作流名称描述技术范围，不能代替责任人的姓名。Task、ADR、PR、Handoff 和阻塞项必须写明实际负责人。

| 责任人 | 稳定身份 | 负责维护 | 不负责维护 |
|---|---|---|---|
| 路诚钺 | GitHub `Chengyue-Lu` | Method/Core 语义；Mode/Action/Method Resolution；能力词汇；Skill Need、评估、准入和退役；Research State/Claim/Method Trace 规则；受控读取及相关 fixtures/docs | Provider SDK、认证、HTTP transport、模型槽实现、API session loop、live API conformance 与 API 专用测试 |
| 黄毅 | GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`（同一账户） | Provider Adapter、模型能力协商、隔离 API session、Task-to-API 编译、执行关闭事务、真实账户/模型 conformance 与 API 测试 | 代替研究者批准 Claim、单方面改变 Mode/Skill 语义、擅自准入 Skill 或降低 Human Gate |

Agent 不是责任主体。每个 Agent 使用稳定 `actor_id`，并在 Attempt Archive 中绑定具名 `accountable_owner`；模型名、窗口名和临时昵称不能替代人类负责人。

## 2. 开始一个开发 Task

1. 读取根目录 `AGENTS.md`、本文件和 [`TASKS.md`](TASKS.md)；
2. 确认基线提交、负责人、原子边界、允许读取集、写入范围、输出和停止条件；
3. 只读取 Task 指向的模块、计划、Profile、Skill 与输入，不从全仓扫描恢复上下文；
4. R0/R1 普通单 PR 默认以 PR body 与 Git 记录留痕；只有 Task policy、委派、R2、跨 PR、外部副作用、
   压缩或争议触发时，才在 `work/<task-id>/<attempt-id>/` 建立 Task Archive；
5. 完成时提交必要的验证证据；跨窗口、跨 Agent 或跨 PR 时再写 Compact Handoff 和 `WORKLOG.md`。

实时工作项只在 [`TASKS.md`](TASKS.md) 更新；依赖和阶段 Gate 只在 [`ROADMAP.md`](ROADMAP.md) 维护；实现覆盖只在 [`STATUS.md`](STATUS.md) 汇总。

## 3. 留存与克制读取

- 受控研究执行、正式委派或显式 Task policy 触发 Archive 时，Agent 间可见传递与可观察事件按
  Attempt policy 归档；普通开发分支不为了过程形式生成低信息密度记录；
- 不保存隐藏推理、密钥和认证头；受政策限制的删减必须留下 omission 记录；
- 主 Agent 默认只读取 Task、当前索引、风险和 Handoff，排查时再按 ID 拉取原文；
- 不可变大工件使用路径和哈希引用；进入上下文但没有稳定来源的瞬时结果必须脱敏持久化；
- Worklog 是被触发后的导航摘要，不替代消息与事件档案。

## 4. Handoff 分级

- `H0`：无跨 Agent 传递；普通开发只需保存必要输出与检查，正式 Task 可按 policy 增加 Worklog。
- `H1`：普通委派；主 Agent 接收 Compact Handoff，完整消息流留在 Archive。
- `H2`：压缩、Evidence/Claim/Decision 提升、外部副作用、长等待、争议或显式策略触发时，增加 Manifest/Audit，并按需增加 Snapshot 与 Receipt。

分级改变回传主上下文和审查强度；一旦正式 Archive 被触发，其留存要求不因执行便利而降低。

## 5. 共享接口与分支

共享接口包括 Task、Method Resolution、Resolved Capability Snapshot、兼容期 Assignment、Handoff、Receipt、Trace、Capability / Data Policy 和错误/停止状态。

- 核心对象身份、路由语义、人类权威或运行时所有权变化必须先有 ADR；
- 共享 Schema 变更必须说明 owner、语义版本、迁移影响、消费方和合并顺序；
- 同一时间只有明确 owner 修改同一共享 Schema、CLI 区域或 Registry 索引；
- 并行 Task 声明互斥写入路径，无法隔离时串行；
- `main` 和 `develop` 禁止直接 push、force push 与删除；所有改动经过 PR 与必需 CI，跨 owner
  审查由风险等级和敏感路径触发；
- 功能/文档分支以 `develop` 为集成基线，PR 目标为 `develop` 并 squash merge；开发期间 stale base
  只产生 warning，实际冲突或共享契约不兼容仍阻断合并；
- 一个完整 workstream 在 `develop` 完成集成验证后，只通过同仓库 `develop → main` PR 发布，
  该发布使用 merge commit 形成清晰边界；`main` 不接受其他来源分支；
- 创建、审查与合并 release PR 时必须遵守独立的 [`develop` → `main` 发布合并规范](DEVELOP_TO_MAIN_RELEASE.md)；
- 紧急变更仍走 `feature → develop → main`，不得绕过 CI 或 authority gate；可以压缩普通过程文档，
  并在安全恢复后补齐被明确推迟的记录；
- [`docs/workstreams/`](workstreams/README.md) 按风险和复杂度触发，不再是每个 PR 的必需附件；
- Handoff 给出基线提交、修改路径、验证证据、未证明内容和下一动作。

执行便利性与方法、权限或数据边界冲突时，采用更严格边界并请求人类决定；任何一侧不得替另一侧静默定义 fallback。

### 5.1 Hard authority, adaptive workflow

治理约束的是“什么可以成为共享项目真值”，而不是隔离分支内必须采用哪种普通开发过程。
`declared_risk` 与 changed paths 推导出的 `minimum_risk` 共同决定：

```text
effective_risk = max(declared_risk, minimum_risk)
```

低报会自动升级；只有绕过升级后要求、越权修改 Task 或破坏硬不变量时才失败。

| 风险 | 典型表面 | 最低治理 |
|---|---|---|
| `R0` Routine | owner 内实现、bugfix、测试、refactor、非规范文档 | PR + CI；跨 owner review 可选 |
| `R1` Shared Contract | Schema、Registry、公共模型/CLI、兼容迁移 | PR + CI + cross-owner review；workstream 可选 |
| `R2` Authority / Safety | Method/Claim/Gate、权限、数据边界、Runtime authority、架构、治理、安全 | PR + CI + cross-owner + authority basis + adversarial evidence + workstream/Risk Ledger |

`.github/governance-policy.json` 保存 owner、状态机与最低风险路径。治理器输出 `INFO / WARNING /
ERROR`；只有 `ERROR` 使 CI 失败，并必须解释推导风险、原因和补救要求。

### 5.2 PR 类型与 TASKS 授权

| PR class | base | 允许的任务治理变化 | 合并方式 |
|---|---|---|---|
| `feature` | `develop` | implementation/bugfix/refactor/test/docs/status/completion；可合法置 `DONE`，不能改 Task 定义/依赖/验收 | squash |
| `task-definition` | `develop` | 仅文档；可新增或调整声明的未完成 Task，不能同时置 `DONE` | squash |
| `release` | `main` | 只能来自同仓库 exact `develop`；不重新授权新的任务重定义 | merge commit |

Task 状态机允许 `PARKED → READY → IN_PROGRESS → DONE`、`READY/IN_PROGRESS → BLOCKED`、
`BLOCKED → READY/IN_PROGRESS/DONE`，以及小任务 `READY → DONE`。进入 `READY` 或 `IN_PROGRESS`
时，head snapshot 中列明的 Task 依赖必须全部 `DONE`。同一 feature PR 可以完成当前 Task 并激活
依赖已满足的后继 Task；所有变化 ID 都必须在 PR 中声明。`DONE` 行是终态且定义不可变。

同一 Stage feature PR 也可以原子完成一条已声明的依赖链，包括把后继 Task 从 `PARKED` 直接置为
`DONE`。治理器按 head snapshot 的 dependency DAG 拓扑验证顺序：每个依赖必须已在 base 中 `DONE`，
或在同一 PR 的完成集合中先行闭合；每个进入 `DONE` 的 Task 必须在 Verification evidence 中有具名
证据。Task 定义、依赖和验收不得随实现 PR 改写，依赖缺失或未闭合仍然阻断。该机制只消除人为的
状态推进 PR，不放松完成证据或 `DONE` 不可变性。

R0 maintenance 可以填写 `Task ID(s): none`，前提是 `TASKS.md` 不变；R1/R2 必须有正式 Task 或
Audit ID。feature 置 `DONE` 只代表机器确认结构资格、证据字段和 CI，完成判断仍由具名 owner 承担。
不再创建独立 `task-closeout` PR。

PR 模板不再人工复制 Git 已知的 base SHA，也不要求填写 reviewer。Cross-owner review 由有效风险、
CODEOWNERS 和 ruleset 决定。

已经进入 `develop` 的版本化 Registry 文档按 identity append-only：Mode Action
`action_id + version`、Research Mode `mode_id + version`、Decision Authority Matrix
`matrix_id + version`、Research Mode Migration `migration_id + migration_version` 均不得同版本改写、
移除或换路径。语义变化发布新版本，旧 identity 必须继续保留并可验证。

### 5.3 Workstream、History 与远端门禁

- R0 不要求 workstream；单 PR R1 可以省略并产生 warning；
- R2、跨多个 PR/owner/subsystem、migration、private/external evidence、Architecture Hold 或长期实验
  必须建立 workstream；
- R2 workstream 必须包含 Risk Ledger；普通 PR 的 residual risk section 足够；
- History 只为重要 workstream、迁移、治理/架构决定、release milestone 或关键失败建立，不按每个
  Task 自动制造 closeout 文档；
- CODEOWNERS 不使用全局 `*`，只覆盖共享契约与 authority-sensitive 路径；
- `develop` ruleset 的全局 approval count 为 0，但敏感路径要求 Code Owner review；`main` release
  继续至少 1 approval。两者都要求治理与 Python 3.11/3.13 checks、conversation resolution，并禁止
  direct/force/delete。

仓库内的治理检查负责验证来源拓扑、PR 元数据和 TASKS diff；GitHub ruleset 负责阻止直推、要求
Code Owner 审查和必需 checks。两者都配置完成才构成有效保护。

## 6. 变更检查清单

- 变更属于 stable、status、planning、compatibility 还是 history 表面？
- 是否改了对象含义、版本、消费者或迁移要求？
- 责任人、必要 Task/Archive 与风险触发的证据是否充分，而非机械齐全？
- 示例是否代表当前推荐路径，而不是旧工件回放？
- 确定性测试是否覆盖新增不变量与错误路径？
- 文档链接、示例、Schema/Registry 验证和完整测试是否通过？
- 是否明确未证明科学正确性、真实 Provider 兼容性或机制净收益？

实现协议见[implementation 索引](implementation/README.md)，架构决定见[ADR 索引](decisions/README.md)，历史材料见[历史与审计](history/README.md)。
