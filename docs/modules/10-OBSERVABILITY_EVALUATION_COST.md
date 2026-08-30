# 模块 10：观测、成本与评估

## 1. 目标

衡量系统是否真正提高研究质量和降低认知负担，而不是只记录“多少 Agent、多少消息、多少流程通过”。观测必须有消费方和保留期限。

## 2. 最小运行记录

每个 Attempt 记录：

- Task、Agent Profile、当前 Action/Capability execution slice，以及适用的 Runtime Bundle/View refs；
- optional Skill Assignment/Skill binding（仅 Skill-bearing path；no-Skill/direct Tool 不伪造）；
- requested binding/selected Supply 与 Host-observed actual binding/actual Supply；
- actor_id 与实名 accountable owner；
- 开始/结束时间、状态、重试原因；
- Agent 间每条可见消息的 ID、类型、发送/接收者、时间、内容哈希和附件引用；
- 可观察的正文读取、工具/命令、文件 revision、外部副作用和状态事件；
- 输入/输出工件引用；
- token/调用/工具执行等平台可获得成本；
- deterministic checks；
- 是否触发 review/Human Gate；
- Handoff 被接受、修改、拒绝或废弃；
- 敏感 trace 是否关闭或脱敏。

不保存隐藏 prompt 或 Chain-of-Thought，也不重复复制已经有不可变路径与哈希的工具输出；但实际发送给另一个 Agent 的可见 payload、运行时可观察的调用元数据，以及进入 Agent 上下文却没有稳定来源的瞬时工具结果必须进入 Attempt Archive。

当前必须区分两类 Receipt。legacy `execution_receipt` 仍要求 Skill Assignment，并保留显式
`completion_claim: contract-satisfied` 的兼容路径；这不表示 generic no-Skill Attempt/Handoff migration
已经完成。M11 `generic_execution_receipt` 则 exact-pin execution slice、View、Host report、Trace、Artifact
和 Validation closed set，固定 Assignment absent、`task_completion: false`；completed 也只声明
`action-capability-slice-only`。post-call failed Receipt 只有在 typed、hash-pinned Trace fact 能独立佐证完整
actual binding/Supply 时才可重放，preflight block 不得伪造 actual facts。

两类 Receipt 的 `model_usage_status` 都必须是 `measured`、`estimated`、`unavailable` 或
`not-applicable`；未知成本不允许伪装成零。任何 execution status 都不自动成为 Task completion、Claim
promotion、Human acceptance 或科学正确性证明。

Execution assessment 检查 Task/Profile/Attempt、一致的 frozen control refs、可选 Assignment、View/Host/
Trace/Receipt closure、输出存在性、Handoff 回指、时间与状态、协调成本、并发上限、review loop、敏感/
外部/full trace，以及真实 Agent/API 执行是否缺少用量。它不把 contract-only fixture 计作模型运行，也
不把 selected Snapshot/View 当成 actual execution fact。

## 3. 质量指标

- 关键 Claim 的 Evidence 覆盖率；
- 引用 locator 可验证率；
- unsupported / overreaching Claim 比例；
- stale result 被错误合并次数；
- 负结果和冲突保留率；
- Run 可复现率；
- 人类纠正的实质错误类型；
- Agent 结果采纳、修改和拒绝比例。

## 4. 上下文指标

- 主 Agent发生非计划压缩的次数；
- checkpoint/rollover 后恢复成功率；
- 下一 AWU 成本估计误差、closeout reserve 命中率与 false-completion rate；
- 新会话 Time-to-First-Correct-Action 与重复工作率；
- Handoff 缺失限制或未完成项比例；
- Transfer Manifest 条目数、必传条目覆盖率和未映射负面区段数；
- 触发语义复核的条目数、实际抽样数及 preserved/distorted/unverifiable 分布；
- 主 Agent回查原始材料/日志频率；
- Pinned State 大小与增长率；
- Skill 正文加载量；
- 因摘要失真导致的返工次数。
- Trace capture gap、延迟归档、未声明删减和越界回读次数。
- event ledger 中越界读取/工具调用、未保存瞬时结果和过程产物覆盖次数。

## 5. 成本指标

模型成本策略不建设连续评分 Router。只比较实际启用的少量槽位：`primary`、`worker` 和按需 specialist。Receipt 同时记录计划槽位对应的请求模型与 Provider 实际返回模型；简单任务是否留在 `worker`，由同类 Task 的完成率、返工、token、时间和人工纠错决定。若 `worker` 未过门槛，由人类或明确规则创建新 Attempt 并改用 `primary`，不自动让两个模型轮流校核。

- 每条最终采用 Evidence 的 token/时间；
- 每条 accepted Claim 的 token/人工时间；
- 协调、汇总、校核占总成本的比例；
- 每个 Skill 的加载成本与采纳率；
- 子 Agent无效产出比例；
- reviewer 改变实际决定的比例；
- Handoff 抽样与失真修复的人工分钟数；
- Human Gate 阅读与等待时间。

协调成本持续超过三分之一时进入 WARN，并优先减少 Agent、Handoff 字段、review 或规则，而不是提高预算。

协调比例优先使用 `coordination_tokens / (coordination_tokens + execution_tokens)`；token 不可得时才使用对应时间比例。两个基准都不可得时产生 unknown 警告，不合成跨单位总分。

Handoff 语义复核不默认扩大为全文复核。只有 Task 明确要求或 Transfer Manifest 出现关键/高风险条目时才计入最小抽样；若抽样成本持续高而并未改变接受、返工或升级决定，应缩减字段或触发条件，而不是常驻一个 reviewer Agent。

Handoff 成本对照按 H0/H1/H2 分组，至少记录工件数、总字符、生成时间、审阅时间、主 Agent 回查次数、限制遗漏与返工。内容读取另记录初始允许集、范围扩展次数、实际使用的新输入和无关读取。目的不是追求零读取或最短 Handoff，而是确认额外控制确实改变了决策或降低了错误。

## 6. 对照评估

M5-003 已将正式 Method/Skill baseline plan 的 canonical treatment vocabulary 固定为四臂：

1. Plain Agent；
2. Plain Agent + Tool；
3. Mode + no-Skill/direct-tool；
4. Mode + candidate Skill。

Evaluation Manifest 顶层只冻结四臂共享的 Task/input、exact Model、Host、budget、context 和 evidence
classes；Tool、Resolved Capability Snapshot、Mode/Method 与 candidate Skill 是 per-arm exact treatment
binding，不能误写成四臂共用同一个 Snapshot：

- `plain-agent` suppress Mode/Method control，且不携带 Tool/Snapshot/Skill binding；
- `plain-agent-tool` suppress Mode/Method control，并 exact-pin Tool Supply Snapshot；
- `mode-no-skill` exact-pin Mode/Method 与 no-Skill/direct-Tool/procedure Snapshot，拒绝任何 Skill Supply；
- `mode-candidate-skill` exact-pin Mode/Method、candidate Skill identity/version/hash 与对应 Skill Evaluation。

四种 treatment 必须各出现一次。`rwb eval plan` 复用 `eval check` 的 exact-reference closure，只产生同一
frozen-condition digest 下的 deterministic `compiled-not-executed` plan；M5-003 不运行真实案例、不保存
trial/result，也不证明 Skill/Method 已有净收益。未来比较可观察 method violation、Claim overreach、
provenance error、反证遗漏、人工纠正距离、返工、时间、token/成本和可恢复性，不能只比较文本“更完整”。
多 Agent/H1/H2 是正交的 coordination 变量，不是旧 arm 名称或默认优胜组。

## 7. Skill 评估

每个 Skill 有独立小型 eval 集：

- 正常触发案例；
- 不应触发案例；
- 缺输入/工具案例；
- 恶意或提示注入来源；
- 输出契约边界；
- 版本升级回归；
- 与相近 Skill 的路由区分。

Skill 的价值由任务成功、错误率、上下文成本和结果采纳率衡量，不以安装次数或描述覆盖范围衡量。

既有 `skill_evaluation` 是独立的 provider-neutral paired same-input evaluation record，不是 M5-003
四臂 Manifest 的替代 treatment vocabulary。baseline 与 with-Skill 必须冻结 Task/input，控制
provider/model/config，分别引用输出、确定性报告、legacy Execution Receipt 与 Context Snapshot，并在
揭示条件前完成人类评分。评估器阻断 fixture-only、案例不足、输入/模型/配置漂移、with-Skill 确定性
失败、上下文不可比和非盲评；它不会自动求总分、批准 Skill、选择 Runtime Supply 或促进 Claim。
平台无法提供 token 时保留 `unavailable` 并产生警告，仍可使用实测字符数与 wall time，但不得宣称
token 节省。实际 trial/evaluation result 属于后续 Evaluation/Trial record，不回写 Skill Need 本体。

## 8. Trace 政策

Trace 分为三个职责层：Execution/Archive Trace 保存实际 Agent 传递、可观察读取/工具/文件事件、
Handoff 和过程产物；Method Trace 保存 Mode/Action/Mechanism/Human Gate/Evidence/Claim 的关键决定；
可选运行遥测记录 token 级、内部调试或平台细节。三者通过引用关联，但都不是科研证据本身。

M11 actual execution binding 必须由 Host facts 和 typed、hash-pinned `execution_trace_fact` 记录；计划中的
Snapshot/View 只能作为 expected binding。M3-009 Method Trace 可以 exact 引用该 fact，或在本 Attempt
没有 authoritative fact 时显式记录 gap，不能用 runtime log、Snapshot 或 Receipt 文本补造 actual facts。

默认策略：

- 核心协作 Trace 对每个跨 Agent Attempt 必须存在；
- 可选遥测只在有明确调试或评估消费方时开启；
- 敏感项目关闭外部 trace 或先脱敏；
- trace 有保留期限；
- 正式事实必须提升为工件；
- 没有调试消费方的可选遥测不保存；
- trace 关闭不能破坏核心可追溯性。

Trace 完整度不是越高越好。禁止通过记录隐藏推理、密钥或无界工具输出追求“全量”；也禁止用 Worklog 摘要替换已经发生的 Agent 间原始传递。

## 9. 反指标异化

- 指标必须关联一个决策；无消费方则删除；
- PASS 数、Agent 数、消息数、Schema 覆盖率不是成功指标；
- Claim coverage 不能鼓励制造低价值 Claim；
- token 降低不能以丢失限制、反证和来源为代价；
- Human Gate 通过率高可能表示 Gate 无价值，而不是质量高；
- 每个里程碑进行一次“删减评审”。

## 10. 验收条件

- 能回答每次结果用了哪个 Agent、输入、Capability Supply 和工具，以及是否使用了 Skill；
- 能比较单 Agent 与多 Agent 的净收益；
- 能识别上下文污染和 review loop 的真实成本；
- trace 不包含不必要的敏感数据；
- 任一跨 Agent Attempt 能检测消息序列缺口并定位到实名责任人；
- 主 Agent 可以只加载 Handoff/索引而不加载完整消息正文；
- 至少一个低价值机制因指标被删除或降级；
- M5-003 plan 能保持四臂 exact closure 且不触发执行；未来真实评估结果才能支持继续、修改或停止项目，
  而不是只支持扩张。
