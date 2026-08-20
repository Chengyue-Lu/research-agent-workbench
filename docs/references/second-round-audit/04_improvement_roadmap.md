# Research Agent Workbench — 可能的改进计划表

> 本表是架构优先级计划，不是工期承诺。
> 难度：S / M / L / XL 为相对实现与迁移复杂度。
> 原则：先稳定科研语义，再扩 Evolution / State，最后重新接 Execution。

## 1. 总体路线

| Phase | 目标 | 核心产物 | 优先级 | 相对难度 | 主要依赖 | 是否建议并行 |
|---|---|---|---|---|---|---|
| A — Core Formalization | 让 PR11 从设计文档变成正式系统语义 | Mode v0.2、Mode Action、Method Resolution、Decision Authority | P0 | L | PR11 / ADR-0013 | 部分可并行 |
| B — Evolution Foundation | 建立版本化、可迁移、可评测的演化基础 | Skill Need、Lifecycle、Migration、Protocol、Capability Snapshot | P1 | XL | Phase A | 可分 2–3 条线 |
| C — Research State & Verification | 保存跨 session / runtime / 年份的研究意义 | Research State、Frontier、Claim composition、Method Trace | P1 | XL | A；部分依赖 B | 可部分并行 |
| D — Evaluation Loop | 证明 Mode/Skill/Strategy 是否真的有增量 | baseline harness、evaluation manifest、metrics | P1 | L | A；Skill eval 依赖 B | 建议早启动 |
| E — Strategy & Governed Evolution | 让系统可以吸收外部方法但不失控 | Strategy interface、candidate evolution pipeline | P2 | L/XL | B+C+D | 后置 |
| F — Execution Reintegration | 重接 PR10 类 runtime/live execution | resolved execution contract、Trace/Receipt integration | P2 | XL | A+C；Capability contract | 后置 |

---

# 2. Phase A — Core Formalization

| ID | 工作项 | 输出 | 难度 | 风险 | 完成标准 |
|---|---|---|---|---|---|
| A1 | Mode Action 正式化 | schema + registry + validator | M | Action 定义过度固定 | 两正式 Mode 全部 Action 可机器验证 |
| A2 | Method Resolution | schema + fixtures + resolver contract | L | 抽象过重 | 8 个现有 routing case 无损表达 |
| A3 | Research Mode v0.2 | 去除 direct Skill recommendation | M | backward compatibility | v0.1 可历史读取，v0.2 Need-first |
| A4 | Decision Authority | matrix + validation rules | M | 人工 Gate 过多导致阻塞 | 自动/人工边界有明确 fixture |
| A5 | Core invariants document | stable semantics vs replaceable implementation | S | 文档与代码漂移 | CI/validator 能覆盖核心不变量 |

**Phase A Stop Gate**

在以下条件满足前，不建议新增 accepted Skill 或正式 Mode：

- Method Resolution 已成为 Task → Execution 的正式中间产物；
- 新 Mode 不再隐式携带 Skill；
- no-Skill/tool-only/blocked/Human Gate 均可机器表达。

---

# 3. Phase B — Evolution Foundation

| ID | 工作项 | 输出 | 难度 | 风险 | 完成标准 |
|---|---|---|---|---|---|
| B1 | Skill Need contract | need schema + registry | M | Need 粒度失控 | Need 可映射 baseline 与 candidate |
| B2 | Skill lifecycle v2 | trial/promotion/supersede/retire | L | Registry 兼容 | promotion 有 evidence 链 |
| B3 | Schema migration | migration registry + runner + audit | XL | 迁移造成语义静默变化 | Mode v0.1→v0.2 可复现迁移 |
| B4 | Protocol Profile | PRISMA/V&V 类 profile contract | M/L | 与 Mode 重叠 | Mode/Protocol/Skill 责任不重叠 |
| B5 | Capability Requirement | provider-neutral request | M | 约束表达过度复杂 | 能表达权限/数据出口/副作用 |
| B6 | Capability Snapshot | frozen provider binding | M | Adapter metadata 漂移 | 每次执行能钉住 exact capability |

**Phase B Stop Gate**

- Skill 不能仅凭名称/文档“accepted”；
- old state 可通过显式 migration 继续解释；
- Tool provider 可替换而不修改 Method contract。

---

# 4. Phase C — Research State & Verification

| ID | 工作项 | 输出 | 难度 | 风险 | 完成标准 |
|---|---|---|---|---|---|
| C1 | Research State primitives | Question/Evidence/Claim/Unknown/... | XL | 一次建模过大 | 先覆盖 evidence + simulation 两个真实案例 |
| C2 | Attempt/Failure memory | failure + revisit condition | M | 失败数据噪声 | 新 Agent 能避免重复已知失败 |
| C3 | Research Frontier | open question / contradiction / pending gate index | L | Frontier 无限增长 | 有 compact index 与 archive policy |
| C4 | Evidence–Claim relation | support/contradict/qualify/unknown | L | 语义判定难 | 结构规则与 Human semantic review 分层 |
| C5 | Claim composition | multi-Mode admissibility | XL | 过早形式化科学推理 | 从少量明确 case 开始，不追求全学科统一 |
| C6 | Method-aware Trace | Method + Execution linked trace | XL | Trace 体量与隐私 | reviewer 可重建关键决策路径 |

**Phase C 原则**

不要尝试一次构建“统一科学知识图谱”。先建立足够支撑真实 forward test 的最小 Research State。

---

# 5. Phase D — Evaluation Loop

| ID | 工作项 | 输出 | 难度 | 风险 | 完成标准 |
|---|---|---|---|---|---|
| D1 | Baseline harness | Plain / Tool / Mode / Mode+Skill 四组 | L | benchmark 偏置 | 同一 Task/Model/Tool snapshot 可公平比较 |
| D2 | Evaluation Manifest | model/tool/budget/context pinning | M | 字段过多 | 可复现实验环境 |
| D3 | Method metrics | violation / claim overreach / provenance | L | evaluator 主观 | deterministic + human sample 双层 |
| D4 | Skill metrics | measured increment / cost / context | M | 单一 benchmark 过拟合 | 至少跨两个困难案例 forward test |
| D5 | External benchmark bridge | AstaBench / ScienceAgentBench 等 adapter | M | benchmark 与 RWB Task 不同构 | 不修改 Core 即可接入外部 task suite |

**建议最早开始 D1/D2。** 复杂架构如果没有 baseline，容易把 scaffolding 误认为创新。

---

# 6. Phase E — Strategy & Governed Evolution

| ID | 工作项 | 输出 | 难度 | 风险 | 完成标准 |
|---|---|---|---|---|---|
| E1 | Research Strategy interface | direct/tree/tournament 等统一接口 | L | 过度设计 | 第一版只实现 direct + 1 个实验策略 |
| E2 | External source discovery | repo/paper/skill metadata ingest | M | 来源污染 | discovery 与 admission 严格分离 |
| E3 | Candidate generation | Skill/Tool/Protocol candidate | L | 自动生成低质对象 | 永远只进入 candidate |
| E4 | Governed evolution | audit→trial→eval→shadow→promotion | XL | 自动化越权 | 人工 promotion 与完整 evidence chain |
| E5 | Prune/Merge/Supersede | skill/method library maintenance | L | 历史引用断裂 | old versions 仍可 replay |

---

# 7. Phase F — Execution Reintegration

| ID | 工作项 | 输出 | 难度 | 风险 | 完成标准 |
|---|---|---|---|---|---|
| F1 | Rebase PR10 execution line | clean integration branch | L | hash-derived fixture 大量重生 | clean CI + current main |
| F2 | from-state integrity | validated predecessor chain | M | resume 链断裂 | input preflight + exact predecessor hash/path |
| F3 | completion marker hardening | atomic strict marker | M | replay false positive | partial/truncated marker 不能 suppress run |
| F4 | Evidence provenance binding | source selection contract | M | 多输入错配 | locator+hash 绑定同一 frozen input |
| F5 | Runtime→Trace binding | Receipt + Attempt + Method Trace | L | shared schema 冲突 | Execution 只消费 M3 shared contract |
| F6 | Tool side-effect accounting | attempted/succeeded/delivered | M | 重放副作用 | side-effect call 永不因输出错误“消失” |
| F7 | hard deadline semantics | timeout/cancellation boundary | L/XL | local tools 不可取消 | 明确 hard/soft budget 或实现隔离执行 |

---

# 8. 建议的并行开发组织

在两人/少量贡献者条件下，可按稳定边界拆：

| Workstream | 主要职责 | 不应修改 |
|---|---|---|
| Method/Core | Mode、Action、Method Resolution、Decision Authority | Provider/live runtime |
| Evolution/Registry | Skill Need、lifecycle、migration、protocol | Method semantics 未批准部分 |
| State/Trace | Research State、Claim relation、Trace | Runtime provider behavior |
| Runtime/Adapter | API、Model、Tool execution、Receipt | Claim/Mode/Skill fallback |
| Evaluation | fixtures、baselines、external benchmark bridge | 生产 contract 的静默变更 |

共享 schema 变更必须通过独立 architecture review，避免再次出现 PR10/PR11 式共享文件冲突。

---

# 9. 建议的近期最小提交序列

若希望下一阶段仍保持较小 PR，建议顺序：

| PR | 内容 | 目标 |
|---|---|---|
| PR12 | Mode Action schema + v0.1 formalization | 只把现有 Action 变正式，不改 runtime |
| PR13 | Method Resolution schema + routing fixture conversion | 建立核心中间表示 |
| PR14 | Research Mode v0.2 + remove direct Skill recommendation | 完成 PR11 语义收敛 |
| PR15 | Skill Need schema + Decision Authority | 冻结 Need 与决策权 |
| PR16 | Method Trace envelope / M3-008 | 为 forward test 与 runtime 接入准备 |
| PR17 | Evaluation Manifest + minimal baseline harness | 开始证明增量价值 |
| 后续 | Migration / Protocol / State / Runtime rebase | 按真实案例需要推进 |

以上编号仅为计划占位，实际应以仓库当时 PR 编号为准。

---

# 10. 不建议近期做的内容

| 项目 | 原因 |
|---|---|
| 新增大量正式 Mode | 当前两个 Mode 尚未通过完整 forward validation |
| 扩大 accepted Skill 数量 | Skill Need / evaluation lifecycle 未完成 |
| Tool marketplace | ToolUniverse/MCP 生态更适合作为 Provider |
| 通用 multi-agent supervisor | 已有成熟生态，且易模糊科研方法边界 |
| 长期 conversation memory | Research State 应优先于聊天记忆 |
| 自动修改 Core | 与 governed evolution 原则冲突 |
| 更多 Provider 接线 | 在 Method/Trace contract 未稳定前收益有限 |

---

# 11. 长期成功判据

系统不应仅以 Star、Demo 或单一 benchmark 判断成功。建议长期追踪：

- 旧 Research State 跨版本成功迁移率；
- 更换 Model/Runtime 后任务 contract 重用率；
- Tool/Skill replacement 不修改 Method contract 的比例；
- Method violation rate；
- Claim overreach rate；
- Evidence provenance error；
- Human correction distance；
- 重复失败率；
- Skill measured increment；
- Trace 可复核率；
- 历史 Attempt replay / interpretation 成功率。

最终目标是：

> 新模型、新 Agent、新 Tool 可以不断替换；旧研究意义、失败经验、证据链与决策依据仍然可理解、可迁移、可验证。
