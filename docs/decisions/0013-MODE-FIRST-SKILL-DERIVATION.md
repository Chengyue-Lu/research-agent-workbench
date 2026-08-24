# ADR-0013：从 Research Mode 派生 Skill 需求

状态：Accepted

日期：2026-08-17

> [ADR-0019](0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md) 澄清：本 ADR 中“产生
> Skill Need”是 Method/Maintainer 控制面的正式需求推导，不是 Research Runtime 在遇到 capability
> gap 或失败时自动创建 Need。Runtime 只消费 Capability-first 执行链与已发布 Skill 投影。

## 背景

首批工作固定并筛选了 73 个外部或本地 Skill 候选，随后为四个社区候选建立了详细 dossier。
这套流程证明了来源、许可、脚本、权限和上下文风险可以有界留痕，但也暴露出一个方向问题：
若先从外部候选出发，项目容易用“社区已经写了什么”反推自身的研究方法和 Skill 边界。

第二批 GLM 采集进一步提供了负证据：20 个新增记录中有 14 个 Tool/MCP Adapter、只有 6 个
Skill；理论方向没有成熟的 proof-assistant Skill，仿真方向没有独立、通用的 V&V Skill。
外部生态的目录结构不能替代本项目对证据、Claim、Artifact 和 Human Gate 的定义。

当前三个 accepted Skill 也主要证明了 Schema、hash、边界 fixture 和确定性 checker 可运行，
尚未通过真实困难任务证明其方法增量。`accepted` 不应被误读为永久核心或科学价值已验证。

## 决定

### 1. Mode-first，不做 Mode-to-Skill 固定绑定

每个正式 Research Mode 先定义：

- 它允许什么证据支持什么强度的 Claim；
- 可能出现哪些原子研究动作和失败模式；
- 每个动作需要什么输入、Artifact、停止条件和 Human Gate；
- 哪些动作是必需，哪些只是某类 Task 的可选动作。

Mode 不携带固定 Skill bundle。一个 Atomic Task 只从 Mode action catalog 选择本次需要的动作，
不能因为激活 Mode 就加载全部 Skill。

### 2. 先判定机制，再产生 Skill Need

每个 action 必须先在以下机制中选择最小充分者：

1. `Mode/Project invariant`：Claim、证据和风险的稳定边界；
2. `Task contract/template`：一次性或项目特定的步骤与输出；
3. `Tool/checker`：确定性读取、检索、计算、格式、Schema、hash 或外部操作；
4. `Skill Need`：跨任务复用、需要语义判断、能写清 trigger/non-trigger 且有潜在增量的方法动作；
5. `Human Gate`：来源权重、模型代表性、可接受误差、伦理、安全和最终解释。
6. `blocked/capability gap`：必需输入、许可、权限、工具能力或批准缺失，不能在边界内继续。

`no-Skill`、`tool-only`、`blocked` 和 `Human Gate` 都是正常结果。只有第 4 类才建立 Skill Need
Spec；不得为填满 Mode 表格而创建 Skill。

### 3. Dossier 以需求为中心，不以来源为中心

后续 dossier 的主键是 `need_id`，而不是某个外部 Skill 名称。每份 Need dossier 汇总：

- Mode/action/failure/artifact/Human Gate；
- no-Skill 和 direct-tool 基线；
- 多个外部 Skill、官方方法、论文规范和真实失败案例暴露的共同约束；
- 学科、求解器、数据和工具变体；
- 互相冲突的建议、许可与不可复制部分；
- 一个项目原创 compact contract 是否值得进入 trial。

外部 Skill Registry 改作来源和模式参考库。外部内容不能因名称匹配而成为项目 Skill，也不能
从一个来源直接“润色移植”。只有 Need Spec 冻结后才允许按多个来源独立综合。

### 4. 重新审视现有 accepted Skills

- `handoff-integrity@0.1.0` 的确定性部分迁移目标仍是 Tool/Trace/H2 模板；
- `literature-evidence-extraction@0.1.0` 与 `simulation-vv@0.1.0` 作为首轮原型冻结，不继续
  原地扩写；是否拆分、重写或退役由 Mode action map 决定；
- 历史 Assignment 保持原版本和 hash 可解析；任何变更创建新版本或显式 deprecation，不能
  静默改义；
- 在新的 Mode-derived trial 通过困难任务前，不新增 accepted Skill。

### 5. 当前实施顺序

1. 只处理正式 `evidence-synthesis` 与 `simulation` 两个 Mode；
2. 建立两者的 Action–Failure–Artifact–Gate 矩阵；
3. 产生少量、排序后的 Skill Need Specs 与 Tool gaps；
4. 再建立 Task-to-Mode-to-action-to-mechanism 路由 fixtures；
5. Mode 需求确认后才修订现有 Skill、建立 Tool cards 或选择外部参考；
6. 真实 forward test 仍等待 M3-008 Trace validator。

`experiment`、`theory`、`observational-statistics` 和 `engineering-validation` 继续保持候选分类；
只有真实案例证明现有 Mode/组合不足时才申请准入。

## 后果

优点：

- Skill 分类由项目的方法需要驱动，不再被外部仓库目录牵引；
- 不同研究形态可以拥有不同 action catalog，而无需一条全局科研 DAG；
- Tool、短 Task contract 和 Human Gate 可替代大量低价值 Skill；
- 同一需求可比较多个来源并提取共识、分歧和学科变体；
- 主 Agent 只维护 Mode、Need、风险和索引，不加载候选全文。

代价：

- 现有 accepted 名称和候选 shortlist 不能直接成为开发清单；
- 需要先完成 Mode action 分解，短期内可能没有新的 Skill 包；
- 某些动作会得到“当前无需 Skill”或“缺真实案例”的空结果。

## 边界

本 ADR 不授权：

- 新增正式 Mode；
- 修改 Provider/API/Runtime、模型路由或真实 conformance；
- 安装、执行、注册 GLM 采集到的外部 Skill/MCP；
- 删除历史 dossier、Registry 记录、Skill 版本或 Attempt Archive；
- 在没有 Trace 和困难任务证据时宣称 Skill 有增量价值。

## 不采用

- 每个 Mode 固定绑定一组 Skills：会制造隐式大角色和上下文洪泛。
- 继续从候选池挑“最完整”的 Skill：会把外部实现的边界当作项目需求。
- 为每个研究阶段预建一个 Skill：把可选 action 固化为全局流程。
- 立即删除三个 accepted Skill：会破坏历史锁定与现有 fixtures，且没有完成迁移。
