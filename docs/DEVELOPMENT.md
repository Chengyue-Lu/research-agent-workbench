# 开发协作指南

状态：Stable contributor rules

## 1. 按任务与证据组织开发

开发不按固定人员分配模块，也不以指定另一人的审核或签字为启动前提。Task、风险、允许范围与验收证据决定实施边界；并行工作声明互斥写入路径，共享修改无法隔离时串行。

Human、Research Control/Resolver、Runtime 与 Tool 的功能权限保持契约边界。开发授权不代替人类接受、权限放宽或发布决定。`actor_id`、授权身份与 `accountable_owner` 是运行追溯字段，不是开发人员分工，本规则不改对应 Schema。

依据见 [ADR-0023](decisions/0023-DEVELOPMENT-WITHOUT-PERSON-ASSIGNMENTS.md)。机器政策、模板及远端审核同步由 M0-008 单独实施，本文件不自报配置或 ruleset 已修改；历史 ADR、DONE Task 和接受记录保留原事实。

## 2. 开始一个开发 Task

1. 读取根目录 `AGENTS.md`、本文件和 [TASKS](TASKS.md)。
2. 选择 exact M Task，核状态、hard dependencies、风险、Phase/Topic、允许读取集、写入范围、输出和停止条件。
3. 读取 Task 指向的模块、计划、Profile、Skill 与输入；新内容按现有授权判断，不从全仓递归恢复上下文。
4. 普通单 PR R0/R1 默认 PR body 与 Git 留痕；Task policy、委派、R2、跨 PR、外部副作用、压缩或争议触发 Task Attempt Archive。
5. 提交适用验证证据；跨窗口、Agent 或 PR 时提供 Compact Handoff 与必要 Worklog。

TASKS 唯一维护定义、状态与依赖；[施工图](M_SERIES_IMPLEMENTATION_MAP.md)导航，[ROADMAP](ROADMAP.md)维护方向/Gate，[STATUS](STATUS.md)维护成熟度。Phase/Topic/family 不是施工身份；近期工作没有 exact Task 时先走 docs-only task-definition。

## 3. 留存、读取与 Handoff

- 正式 Archive 被触发后，按 Task policy 保存可见传递、可观察事件与获准输入；不保存隐藏推理、密钥或认证头，必要删减保留 omission/capture gap。
- main 先消费 Task、索引、风险与 Compact Handoff，再按 ID 读必要原件；大工件用 path/hash 引用，瞬时结果脱敏持久化。
- Worklog 是导航，不替代消息与事件；普通开发不机械制造低信息密度档案。
- H0 无跨 Agent 传递；H1 普通委派使用 Compact Handoff；H2 在压缩、提升、外部副作用、长等待、争议或 Task policy 触发时补 Manifest/Audit，按需 Snapshot/Receipt。分级不降低已触发的留存要求。

## 4. 共享接口与分支

共享接口包括 Task、Method、Snapshot、兼容期 Assignment、Handoff、Receipt、Trace、Capability、Data Policy 和停止状态。

- 核心对象身份、路由语义、人类决定边界或 Runtime 权威变化先有 ADR；Schema 变化说明版本、迁移、消费者和合并顺序。
- 同一共享 Schema/CLI/Registry 区域互斥写入；保留其他窗口编辑。
- 功能/task-definition PR 进入 develop 并 squash merge；开发期 stale base 为 warning，实际冲突或共享契约不兼容仍阻断。
- main/develop 保持必需 PR、CI、conversation resolution 和合法合并方式，禁止 direct push、force push 与删除。
- 内容从 frozen develop source 完整生成同仓库 release/vX.Y.Z → main，以 exact current main 为父提交并 merge commit；active curated topology 拒绝 direct develop → main，release 不回并 develop。
- 每次发布按 [发行规范](DEVELOP_TO_MAIN_RELEASE.md)核来源、工件、远端门禁与人类发布决定；紧急变更仍保持拓扑和硬门禁。

M Task 是 implementation/acceptance identity，PR 是 integration/review unit，无需1:1。强耦合预定义 DAG 可原子集成；PR 列 exact IDs、每项变化、独立 slice/commit/evidence 与拓扑顺序，不能用 Phase/Topic/family/工作包代替验收身份。

## 5. 风险与共享真值

治理约束进入共享项目真值的条件，授权范围内的普通实现过程可自主安排。

```text
effective_risk = max(declared_risk, minimum_risk_from_changed_paths)
```

| 风险 | 典型表面 | 最低证据 |
|---|---|---|
| R0 Routine | bugfix、测试、refactor、非规范文档 | PR + CI |
| R1 Shared Contract | Schema、Registry、公共模型/CLI、兼容迁移 | PR + CI + 契约/消费者与迁移审查；workstream 可选 |
| R2 Authority / Safety | Method/Claim/Gate、权限、数据、Runtime 权威、架构、治理、安全 | PR + CI + 风险审查、authority basis、adversarial evidence、workstream/Risk Ledger |

审查按风险组织，不要求固定两个人或特定账户组合。治理器从 policy 推导最低风险并报告 INFO/WARNING/ERROR；机器人员政策同步前按实际检查结果处理，不能用 PR 自述字段消除失败。

### 5.1 PR 类型与任务状态

| PR class | base / merge | 允许的任务变化 |
|---|---|---|
| feature | develop / squash | 实现、修复、测试、文档、合法状态/完成；不能改定义/依赖/验收 |
| task-definition | develop / squash | 仅文档；新增或调整声明的未完成 Task，不能同时置 DONE |
| release | main / merge commit | 同仓库生成式 release branch，绑定 frozen develop/current main，不重新授权 Task |

状态机：PARKED→READY→IN_PROGRESS→DONE，READY/IN_PROGRESS→BLOCKED，BLOCKED→READY/IN_PROGRESS/DONE，小任务 READY→DONE。READY/IN_PROGRESS 的 head Task deps 全部 DONE；原 DONE 行终态且定义不可变。所有变化 ID 在 PR 声明，完成判断依据实际证据，CI 资格不等于科学正确性。

强耦合 feature PR 可原子完成预定义 DAG，包括符合条件的 PARKED→DONE：定义在 base、至少一个 base READY 入口、外部 deps 在 base DONE、内部无环且入口可达、成员全部声明且各有独立 slice/commit/evidence、依赖拓扑先闭合、风险取最大。此 completion 必须 R2；断连、缺证据、外部 deps 未满足或定义改写均阻断，不合并 Task identity。

R0 maintenance 可填 Task IDs none，前提 TASKS 不变；R1/R2 有正式 Task 或 Audit ID，不机械另建 task-closeout PR。普通 PR 不手填 Git 已知 base SHA，不以 reviewer 字段分配人员。M0-008 同步前的模板身份字段仅用于当前机器元数据，不赋予模块独占权。

已进入 develop 的 Action、Mode、Authority Matrix 和 Migration identity append-only：不得同版本改写、删除或换路径；语义变化发新版本并保留旧版验证/迁移。

### 5.2 Workstream、History 与远端规则

- R0 不要求 workstream；单 PR R1 可省略并产生 warning；R2、跨 PR/subsystem、migration、private/external evidence、Architecture Hold 或长期实验建立 workstream，R2 带 Risk Ledger。
- History 留存重要变化、接受和失败，不按每个 Task 自动造 closeout。
- 硬门禁层保持 PR、合并方式、规定 checks、latest-base、conversation 与 force/delete 保护；审核设置与硬门禁分别处理。
- 远端审核调整在线核对实际 rulesets，M0-008 保存修改前后证据；本文件不声称原 Code Owner/approval 已取消。审核便利不能绕过 CI、来源、权限或发布 Gate。

### 5.3 人类审阅与合并

人类据当前 diff、验证证据和剩余风险决定是否合并，无指定另一人参与、暂无空闲确认或补签前置。Agent 整理审阅包并执行明确授权的操作，开发指令本身不授权 merge/release。

合并前核 exact base/head、冲突、required checks、conversation 与实际 ruleset。失败/缺失检查、实质性 changes-requested、阻断或冲突不能忽略；base/head 或证据变化后重核，最终保存 merge 身份。每次 main 发布另需 source/parent、manifest/projection/tree、安装工件和人类发布决定。

旧 [ADR-0022](decisions/0022-SINGLE-PR-MAINTAINER-REVIEW-EXCEPTION.md)与例外记录解释历史操作；现行人员规则以 ADR-0023 为准，不通过改写旧接受事实同步机器政策。

## 6. 验证与提交

develop 日常 PR 按稳定组件和直接消费者执行检查，业务测试用 Python3.11。文档运行文档检查；安装/构建/依赖变化附实际安装检查，依赖变化加另一支持版本 smoke。新增行为保留公共入口，修复保留故障反例与正常路径；新增/删除/重命名/未知路径进入检查计划，不自动扩大全仓。

风险等级不等价测试或 coverage 范围；组件 coverage 用于诊断，不以统一百分比阻断。错误行为、结果身份和缺适用检查仍阻断；全仓、多版本 checkpoint 按明确范围执行。CI 兼容与回退见 [组件 CI 迁移](workstreams/chengyue-lu/TEST-PERF-002/COMPONENT_CI_MIGRATION.md)。

提交前核文档归属、契约/版本/迁移影响、Task/Archive 与风险证据、推荐示例、适用正反检查和内部链接。结构/工程通过不证明科学正确性、其他 Provider 兼容或净价值。

接口见 [implementation](implementation/README.md)，决定见 [ADR](decisions/README.md)，历史见 [history](history/README.md)。
