# 项目章程

版本：0.6

状态：实施基线

日期：2026-08-20

## 1. 使命

帮助研究者以较低认知负担调用不断变化的 AI 检索、分析、推导、编程和校核能力，同时让研究
方法、证据关系、失败经验与关键决定保持可理解、可迁移、可验证，并由人对科学解释和最终结论
负责。

长期定位：

> A versioned, method-aware research control plane for continuously evolving AI agents.

## 2. 要解决的问题

现有平台已经能创建 Agent、接入模型和工具。RWB 解决的是平台本身不稳定保存的科研边界：

- 不同研究活动如何采用不同方法，又不被统一流水线固化；
- 如何从 Mode/Action 推导最小机制，而不是按名称加载 Skill bundle；
- 如何让 Research State、Evidence/Claim provenance 和失败历史跨 Model/Runtime 延续；
- 如何限制主 Agent 上下文，同时让正式交付经压缩或换窗后仍可恢复；
- 如何区分机器结构验证、目标语义复核与人类科学判断；
- 如何让 Skill、Tool、Protocol 和 Strategy 可演化但不能自动越权；
- 如何用 baseline 证明复杂机制的净价值，而不是用 Agent/Schema/Trace 数量代替进展。

## 3. 产品目标

1. 建立小而稳定的 Integrity Kernel 与科研对象基础；
2. 正式表达 `Mode → Action → Method Obligation → Method Resolution`；
3. 将 Mode、Protocol Profile、Research Strategy、Skill 和 Tool 保持正交；
4. 建立 Capability Requirement 与冻结 Snapshot，使实现可替换而边界不漂移；
5. 建立跨 session/runtime 的 Research State、Failure 和 Frontier；
6. 建立文件优先的 Task、Handoff、Artifact、Trace、版本、迁移和 provenance；
7. 用确定性校验、风险触发复核和少量 Human Gate 管理决策权；
8. 用四类简单 baseline 评估 Mode、Skill、Strategy 和多 Agent 的增量；
9. 以纯 API fresh session 作为可移植执行兜底，并允许可选平台 Adapter；
10. 建立受治理的外部候选发现、审计、trial、评测、退役和历史重放。

## 4. 长线原则

- Research semantics and history outlive models, runtimes, tools and skills；
- 越靠近 Integrity/Research State 的对象越稳定，越靠近 Execution 越可替换；
- 执行层不拥有 Mode、Claim、Skill Need 或权限放宽的解释权；
- 学科差异优先由 Mode/Protocol/Capability 表达，不扩大公共内核；
- 主 Agent 保持在目标、冲突、风险、索引和下一动作；
- 外部 Skill/Tool 发现不等于准入，自动生成永远只进入 candidate；
- 没有增量价值时允许 no-Skill、单 Agent、direct strategy 或删除控制机制。

## 5. 非目标

- 不自治决定选题价值、伦理边界、异常排除、主要 Claim 或发表策略；
- 不以端到端自动完成课题或论文作为核心成功条件；
- 不建立长期模拟课题组职位的 Agent 社会、全局 Supervisor 或固定研究 DAG；
- 不复制平台线程、worktree、权限、模型和工具调度；
- 不建设 Tool marketplace、大而全 scientific environment 或 Provider 数量竞赛；
- 不保存隐藏 Chain-of-Thought，不把长期聊天或报告集合当 Research State；
- 不一次形式化所有学科的 Evidence composition；
- 不以 Star、Agent、Skill、Schema、消息或 Trace 数量衡量成熟度。

## 6. 核心成功标准

在至少两个方法差异明显的真实案例中同时达到：

- 新 Runtime 能从冻结文件状态构建正确的下一 Atomic Task，无需旧会话；
- 关键 Claim 可定位到 Evidence/Run/推导、Method Resolution 与人类决定；
- Unknown、Contradiction、Failure 和 revisit condition 不因换模型或 promotion 丢失；
- Tool/Skill replacement 不要求修改 Method contract；
- 主 Agent 不读取完整语料、聊天或事件账本即可协调；
- Handoff/Trace 增加的审计成本确实降低遗漏、失真或返工；
- 框架协调与校核成本不长期超过任务总成本三分之一；
- 至少删除或简化一项真实数据证明无价值的控制机制。

## 7. 决策权

| 决策 | 默认责任主体 |
|---|---|
| 研究问题、价值、伦理与发布 | 人类研究者 |
| 方法承诺、关键假设和主要 Claim | 人类研究者；Agent 可提出候选 |
| Mode/Action/Mechanism 建议 | Agent 提议；Resolver 校验；歧义时 Human Gate |
| Method/Core 语义、Mode 准入与 Skill Need | 路诚钺维护；关键改变由人批准 |
| Skill/Tool candidate、评测、准入与退役 | 路诚钺维护证据链；promotion 按风险由人批准 |
| Provider/API/Runtime 实现与 live 测试 | 黄毅；共享接口变更共同确认 |
| 数据、来源或权限放宽 | 只能由明确 Human Decision 批准 |
| 结构、引用、hash、版本与边界检查 | 确定性 Validator |
| 异常数据排除和科学解释 | 人类研究者 |

实名维护细节只在 [`DEVELOPMENT.md`](DEVELOPMENT.md) 更新。

## 8. 当前阶段

M0–M7 已形成最小契约、Mode-first 离线选择基线、Skill 历史/lifecycle、上下文治理与 API execution
seam；它们是迁移基础，不是最终信息架构。

当前全局下一节点是 `K-METHOD-1 Method Core Formalization`：先把 Mode Action 与 Method
Resolution 变成正式对象，再完成 Mode v0.2 和 Decision Authority。M3-008 可观察 Trace 基线可按
独立分支推进；Method-aware Trace 是其后的独立节点。上述契约稳定前不扩 accepted Skill、正式
Mode、Provider 或真实多 Agent 试验。

阶段依赖见 [`ROADMAP.md`](ROADMAP.md)，实时状态见 [`TASKS.md`](TASKS.md)。
