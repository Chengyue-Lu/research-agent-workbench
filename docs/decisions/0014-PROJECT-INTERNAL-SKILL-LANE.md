# ADR-0014：项目内生协议 Skill 与 Mode-derived Skill 并行

状态：Accepted

日期：2026-08-17

## 背景

ADR-0013 要求从 Research Mode 的 action gap 推导科研方法 Skill，但本项目还有一类只服务于
Workbench 自身的重复任务：Agent Assignment、受控读取、Handoff、上下文恢复、Human Gate 材料
准备和 Attempt 收束。它们不属于任何学科，也不改变 Evidence、Claim ceiling 或科研方法。

如果完全不为这类任务留出 Skill 位置，复杂交接中的语义选择可能反复依赖临时提示；如果把所有
内部规范都包装成 Skill，又会重复 Project Protocol、Schema、Tool 和 Runtime 的职责，并让每个
Agent 常驻加载大量治理文字。

## 决定

### 1. 建立独立的 Project-internal Skill Need 来源

Skill Need 有两条互不替代的来源：

- `mode-derived`：来自正式 Research Mode 的 action、failure、artifact 和 Human Gate 缺口；
- `project-internal`：来自本项目跨 Task 复用、且需要非平凡语义判断的协议执行动作。

`project-internal` 是适用范围，不是新的 `kind`。候选最终仍需判断属于 method、integrity、tool
或 output；若现有分类不合适，再通过独立 Schema 决策处理，不能在本 ADR 中顺手扩展 Registry。

### 2. 内部规范不等于内部 Skill

按以下优先级选择最小机制：

1. 稳定且始终生效的权限、读取、留痕和责任规则进入 Project Protocol、Task 或 Agent Profile；
2. 字段、文件名、格式和必填项进入 Output Contract、Schema 或模板；
3. hash、引用、结构、状态转换和可机器判定条件进入确定性 Tool/checker；
4. 只有跨 Task 复用、需要语义取舍、具有清晰 trigger/non-trigger，且相对前三者有待验证增量时，
   才建立 Project-internal Skill Need；
5. 范围扩大、Claim、最终接受、争议和风险豁免继续属于 Human Gate。

因此“Agent 必须留痕”“输出必须满足 Schema”“未获准路径不得读取”本身都不是 Skill。

### 3. 不全局加载，不形成治理 Bundle

- 主 Agent 默认只读取候选元数据、Need ID 和路由结果；
- 子 Agent 只在 Task Assignment 显式要求时加载一个项目内生 Skill；
- 项目内生 Skill 计入现有两个主 Skill加一个 integrity Skill 的总上限，不获得额外配额；
- 不建立默认的“交接 + 输出 + Trace + 恢复”Skill bundle；
- Task/Schema/Tool 足够时必须选择 `no-Skill`；
- Skill 不能授予读取、写入、网络、模型、Tool 或外部副作用权限。

### 4. 与 Mode-derived 路线并行但在路由时合流

两条路线可以并行建立 Need 和 fixture，但只在 Atomic Task 的 Resolver 中合流。Project-internal
Skill 继承上游 Mode、Claim 和数据边界，不得改变或补造 Mode；没有 Research Mode 的维护任务也
可以使用它，但仍须继承 Project/parent constraints。

### 5. 首批只建立占位，不创建 Skill 包

首批占位处理 Handoff 语义压缩、H2 转移覆盖、Task Assignment、受控恢复和 Human Gate Brief。
占位只表达待验证 Need；在 direct protocol/template/tool baseline 和困难案例就绪前，不进入
`.agents/skills`、accepted Registry 或 Runtime Assignment。

## 后果

优点：

- Agent 交互与输出中的语义难点有明确演进位置；
- 稳定规则仍由上层契约强制，不依赖 Skill 是否触发；
- 项目特殊性不会污染通用科研方法 Skill；
- Mode-derived 和 project-internal 两条开发线可并行推进。

代价：

- 同一个交接需求必须先证明模板和 checker 不足；
- 需要额外记录适用范围，避免内部 Skill 被误作可移植公共能力；
- 若候选长期没有真实失败证据，应保持占位或删除，而不是为了完整性实现。

## 边界

本 ADR 不授权：

- 新增或修改任何正式 Skill 包、Registry Schema、Resolver 或 Runtime；
- 把交互留痕、读取控制或输出 Schema 降级为可选 Skill 指令；
- 为所有 Agent 默认加载内部 Skill；
- 修改 Provider/API、平台 Adapter、自动 Trace 捕获或模型路由；
- 将项目内生候选宣称为适用于其他项目的通用 Skill。
