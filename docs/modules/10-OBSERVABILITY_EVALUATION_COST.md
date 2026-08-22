# 模块 10：观测、成本与评估

## 1. 目标

衡量系统是否真正提高研究质量和降低认知负担，而不是只记录“多少 Agent、多少消息、多少流程通过”。观测必须有消费方和保留期限。

## 2. 最小运行记录

每个 Attempt 记录：

- Task、Agent Profile、Skill Assignment 和 Runtime snapshot；
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

`Execution Receipt` 将上述信息收敛为平台中立文件，并与 Attempt、Agent Profile、Skill Assignment、Context Snapshot 和 Handoff 双向关联。`model_usage_status` 必须是 `measured`、`estimated`、`unavailable` 或 `not-applicable`；未知成本不允许伪装成零。Receipt 的 `status` 是执行生命周期；只有显式的 `completion_claim: contract-satisfied` 才声明结果通过 Task 合同，避免把负对照的“执行完成”误写成“验证通过”。

Execution assessment 检查 Task/Profile/Assignment/Attempt 一致性、输出存在性、Handoff 回指、时间与状态一致性、协调成本比例、并发上限、review loop、敏感/外部/full trace，以及真实 Agent/API 执行是否缺少用量。它不把 contract-only fixture 计作模型运行。

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

正式 Method/Skill 比较采用四种条件：

1. Plain Agent；
2. Plain Agent + Tool；
3. Mode + no-Skill/direct-tool；
4. Mode + candidate Skill。

Evaluation Manifest 必须冻结同一 Task/input、Host、Model、Tool/Resolved Capability Snapshot、budget 和
context。比较 method violation、Claim overreach、provenance error、反证遗漏、人工纠正距离、
返工、时间、token/成本和可恢复性，不能只比较文本“更完整”。多 Agent/H1/H2 是可增加的机制
变量，不是默认优胜组。

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

`skill_evaluation` 契约采用 provider-neutral 的 paired same-input 评估：baseline 与 with-Skill 必须冻结 Task/input，控制 provider/model/config，分别引用输出、确定性报告、Execution Receipt 与 Context Snapshot，并在揭示条件前完成人类评分。评估器阻断 fixture-only、案例不足、输入/模型/配置漂移、with-Skill 确定性失败、上下文不可比和非盲评；它不会自动求总分或批准 Skill。平台无法提供 token 时保留 `unavailable` 并产生警告，仍可使用实测字符数与 wall time，但不得宣称 token 节省。

## 8. Trace 政策

Trace 分为三个职责层：Execution/Archive Trace 保存实际 Agent 传递、可观察读取/工具/文件事件、
Handoff 和过程产物；Method Trace 保存 Mode/Action/Mechanism/Human Gate/Evidence/Claim 的关键决定；
可选运行遥测记录 token 级、内部调试或平台细节。三者通过引用关联，但都不是科研证据本身。

默认策略：

- 核心协作 Trace 对每个跨 Agent Attempt 必须存在；
- 可选遥测只在有明确调试或评估消费方时开启；
- 敏感项目关闭外部 trace 或先脱敏；
- trace 有保留期限；
- 正式事实必须提升为工件；
- 没有调试消费方的可选遥测不保存；
- trace 关闭不能破坏核心可追溯性。

Trace 完整度不是越高越好。禁止通过记录隐藏推理、密钥或无界工具输出追求“全量”；也禁止用 Worklog 摘要替换已经发生的 Agent 间原始传递。

Trace 格式由版本化 JSON Schema 描述（INDEX、ACTORS、event、envelope 四文档 + 共享定义）。
`rwb trace export-schema --out <dir>` 导出与 baseline（当前 `rwb-agent-trace-v0.1`）绑定的
schema bundle：manifest 按 sha256 钉定每个文件并声明各文档治理的物理工件，外部消费者无需
读取工作台源码即可独立机器校验一份 Attempt trace。schema 文档的任何变更必须与 baseline
版本变更同一提交（由测试强制），已导出的 bundle 不会被静默改写。

## 9. 反指标异化

- 指标必须关联一个决策；无消费方则删除；
- PASS 数、Agent 数、消息数、Schema 覆盖率不是成功指标；
- Claim coverage 不能鼓励制造低价值 Claim；
- token 降低不能以丢失限制、反证和来源为代价；
- Human Gate 通过率高可能表示 Gate 无价值，而不是质量高；
- 每个里程碑进行一次“删减评审”。

## 10. 验收条件

- 能回答每次结果用了哪个 Agent/Skill/输入/工具；
- 能比较单 Agent 与多 Agent 的净收益；
- 能识别上下文污染和 review loop 的真实成本；
- trace 不包含不必要的敏感数据；
- 任一跨 Agent Attempt 能检测消息序列缺口并定位到实名责任人；
- 主 Agent 可以只加载 Handoff/索引而不加载完整消息正文；
- 至少一个低价值机制因指标被删除或降级；
- 评估结果能支持继续、修改或停止项目，而不是只支持扩张。
