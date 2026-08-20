# 架构演进路线图

状态：方向与依赖基线；不记录逐项实时状态

日期：2026-08-20

逐项状态和唯一下一任务只在 [`TASKS.md`](TASKS.md) 更新。本文件说明依赖顺序、阶段 Gate 与
停止条件，不是工期承诺，也不是研究项目必须遵循的固定流程。

## 1. 总体顺序

| Phase | 目标 | 主要产物 | 启动条件 |
|---|---|---|---|
| A — Core Formalization | 把 Mode-first 方法论变成正式语义 | Mode Action、Method Resolution、Mode v0.2、Decision Authority | ADR-0013/0016 |
| B — Evolution Foundation | 支持可迁移、可评测的能力演化 | Skill Need、Lifecycle v2、Migration、Protocol、Capability Snapshot | Phase A 稳定接口 |
| C — Research State & Verification | 保存跨 Runtime 的研究意义 | State/Frontier、Failure、Evidence–Claim relation、Method Trace | A；部分依赖 B |
| D — Evaluation Loop | 证明新增机制的净增量 | Evaluation Manifest、baseline harness、method/skill metrics | A 后尽早启动 |
| E — Strategy & Governed Evolution | 有界吸收新策略和外部候选 | Strategy interface、candidate pipeline、merge/prune/promotion | B+C+D |
| F — Execution Reintegration | 让 Runtime 消费冻结科研契约 | resolved execution、Capability binding、Trace/Receipt integration | A+C 与 Capability contract |

Phase 不是一条科研 DAG。它只表示框架接口的构建依赖；真实 Task 仍按 Mode/Action 选择路径。

## 2. Phase A：Core Formalization

1. 把两个正式 Mode 的 Action Catalog 转成版本化、可引用文档；
2. 新增 provider-neutral `Method Resolution`；
3. 将八个既有 routing fixture 无损转换为正式 Resolution fixture；
4. 建立 Research Mode v0.2，移除直接 Skill recommendation；
5. 冻结 Mode/Action/Mechanism/Skill/Tool/Claim/permission 的 Decision Authority；
6. 明确稳定 Core invariants 与 replaceable implementation boundary。

停止 Gate：

- `Task → Method Resolution → Execution` 成为明确接口；
- no-Skill、tool-only、Human Gate、split、blocked 都能正式表达；
- 新 Mode 不再隐式携带 Skill；
- 在 Gate 通过前不新增 accepted Skill 或正式 Mode。

## 3. Phase B：Evolution Foundation

- Skill Need 成为版本化对象，绑定 direct/no-Skill baseline 与预期增量；
- lifecycle 扩展到 trial、superseded、retired，并以 Evaluation evidence 驱动 promotion；
- 建立不覆盖原文档的 migration chain，先演示 Mode v0.1 → v0.2；
- Protocol Profile 独立表达 PRISMA、V&V 或项目方法标准；
- Method Plane 请求 Capability Requirement，执行前冻结 provider/adapter/version/hash/permission/
  data-egress/side-effect Snapshot。

停止 Gate：Tool Provider 可替换而不修改 Method contract；旧研究对象仍可解释和重放。

## 4. Phase C：Research State 与 Verification

最小起步对象为 Question、Evidence、Claim、Unknown、Contradiction、Assumption、Decision、Attempt、
Failure 和 Frontier item。Failure 至少记录 learned result 与 revisit condition。

Method Trace 在 M3-008 可观察执行 Trace 之上增加：Mode proposed/resolved、Action selected、Mechanism
selected/rejected、Capability resolved、Human Gate、Evidence change、Claim promotion/rejection、safe
pause、failure 与 reopen condition。

不一次建设统一知识图谱。先用 evidence-synthesis 与 simulation 两个真实案例证明 compact index、
跨 Runtime 恢复和 reviewer-facing verification 有用。

## 5. Phase D：Evaluation Loop

正式比较至少包含：

1. Plain Agent；
2. Plain Agent + Tool；
3. Mode + no-Skill/direct-tool；
4. Mode + candidate Skill。

Evaluation Manifest 冻结 Task、Model、Host、Tool/Capability Snapshot、预算与上下文。指标优先包括
method violation、Claim overreach、provenance error、counterevidence omission、human correction
distance、rework、context、cost 和 completion time。确定性评分与盲化人工样本分层；单次成功不
构成 promotion。

## 6. Phase E/F 边界

第一版 Strategy 只需 `direct` 加至多一个实验策略，且 direct 永远保留为基线。外部发现、自动
生成、repair/merge/prune 只作用于 candidate。

Execution reintegration 不授权 Runtime 定义 Mode、Claim、Skill fallback 或权限放宽。接入前必须
解决 from-state predecessor、严格 completion marker、Evidence source binding、Tool side-effect
accounting、deadline/cancellation 和 current-main fixture 再生等已知问题。

## 7. 不在近期关键路径

- 新增大量正式 Mode 或 accepted Skill；
- 通用多 Agent Supervisor、团队拓扑或全局 DAG；
- Tool marketplace 或内建大规模科学工具库；
- 长期 conversation memory；
- 更多 Provider 接线；
- 自动修改 Core；
- 没有真实消费者的数据库、消息总线或 distributed runtime。

## 8. 长期成功判据

- 更换 Model/Runtime/Tool/Skill 后，Research State 与 Method contract 仍可复用；
- 旧对象跨版本迁移和历史 Attempt 解释可复现；
- Method violation、Claim overreach、provenance error 和重复失败率下降；
- Skill measured increment 能相对简单基线说明；
- Trace 能让 reviewer 重建关键决定而无需加载完整历史；
- 至少一项复杂控制因无增量而被删除或简化。
