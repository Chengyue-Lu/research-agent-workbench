# 模块 08：验证、风险与 Human Gate

## 1. 目标

把机器可确定的问题、需要语义复核的问题和必须由人负责的问题分开。避免默认多 Agent 全量互审，也避免用结构 PASS 冒充科学正确。

## 2. 三层验证

### 第一层：Deterministic Validator

适用：Schema、必填项、内容哈希、引用存在性、版本陈旧、write scope、Skill lock、参数范围、测试、数值阈值、引用 locator。

输出只说明检查结果和规则版本，例如：

```yaml
check_id: CHK-0044
subject_ref: handoffs/EVID-001.yaml
ruleset: handoff-integrity@0.1.0
result: pass
meaning: structurally_valid
not_claimed: scientifically_correct
```

### 第二层：Targeted Agent Review

只在存在明确语义风险时启用，例如“此段总结是否超出引用”“这条 Claim 是否忽略已记录反证”。审查 Agent 只收到问题、相关工件和停止条件，不读取整个项目。

Handoff 传递审计也遵循这一边界：确定性验证器先核对 Transfer Manifest 条目、来源哈希、Handoff JSON Pointer、必传项与负面区段覆盖；只有关键条目、假设、冲突、方法边界、负结果或人工决定等明确风险才要求独立人工抽样。`structurally-ready` 仅表示结构覆盖可解释，不表示摘要与来源语义等价。

### 第三层：Human Gate

处理：方法选择、关键假设、伦理/安全、异常数据排除、因果解释、模型代表性、主要 Claim、不可逆操作和外部发布。

## 3. 预警级别

| 等级 | 含义 | 行为 |
|---|---|---|
| INFO | 状态和趋势 | 记录，不打断 |
| WARN | 可能降低质量/效率 | 建议处置，可继续 |
| BLOCK | 契约、权限、数据或引用已不满足 | 阻止 promotion/执行 |
| HUMAN | 需要责任主体判断 | 暂停相关升级，等待 Decision |

预警不是独立 Agent。它们由 Task 创建、Skill 解析、Handoff、promotion、Claim 升级、checkpoint 和 release 等边界触发。

## 4. 核心风险登记

| 代码 | 问题 | 默认处置 |
|---|---|---|
| CTX-MAIN-PRESSURE | 主上下文过载 | checkpoint / rollover |
| CTX-HANDOFF-LOSS | 子 Agent 交接丢失关键内容 | BLOCK |
| CTX-AUTO-COMPACTION | 主上下文发生非计划压缩 | 写 Main State 并 rollover |
| CTX-HIDDEN-STATE | 决定只存在于聊天/隐式状态 | BLOCK，创建 Decision 工件 |
| CTX-METRICS-UNKNOWN | 压力指标不可获得 | 显式保留 unknown，禁止成本结论 |
| CTX-NEXT-AWU-UNSAFE | 剩余预算不足以覆盖下一原子单元和收尾余量 | 不开启新 AWU，进入 safe pause/rollover |
| CTX-CLOSEOUT-RESERVE-INSUFFICIENT | 连最小收尾余量都无法覆盖 | BLOCK 扩展，立即持久化最小恢复状态 |
| CTX-STALE | 使用旧 revision | BLOCK |
| RESUME-CONFLICT-GIT | Main State 的 Git 基线与当前 HEAD 不同 | BLOCK，先解释或重建恢复状态 |
| RECEIPT-VALIDATION-FAILED | 完成宣称引用的机器验证为失败 | BLOCK；机器证据覆盖自然语言状态 |
| SKILL-CONFLICT | Skills 指令或契约冲突 | BLOCK |
| SKILL-PERMISSION-ESCALATION | Skill 越权 | BLOCK |
| SKILL-CONTEXT-FLOOD | Skill 过多/过长 | 拆 Task |
| SKILL-NAMESPACE-COLLISION | 不同来源使用相同 Skill name，平台不会自动合并 | 以 accepted Registry + 来源哈希解析，等价项交人工选择 |
| REGISTRY-SPLIT-BRAIN | Task、运行时和 Handoff 使用了不同 Registry 快照 | 冻结 registry digest，阻断合并 |
| ASSIGNMENT-HANDOFF-DRIFT | Handoff 只写 Skill ID/version，遗漏实际内容哈希 | 对照 Attempt/Assignment lock；未补齐前不得 promotion |
| CONSENSUS-CORRELATED | 多 Agent 同源错误被当共识 | 改用异质证据/工具或人类复核 |
| COORD-INTERFACE | 协调接口多于有效工作 | 简化流程 |
| TASK-READ-OUTSIDE-SCOPE | Agent 读取未声明正文或未记录范围扩展 | BLOCK 合并，补录/重做 |
| WRITE-RACE | 并行写冲突 | BLOCK / 重新分区 |
| REVIEW-LOOP | 互审无停止条件 | 停止并交给主 Agent/Human |
| GOAL-DRIFT | 子任务偏离当前问题 | 关闭 Task 或新建 Question |
| PROXY-GAMING | 为通过指标牺牲研究价值 | 审计指标消费方，删除指标 |
| HUMAN-FATIGUE | Gate 太多导致机械批准 | 合并/删除低价值 Gate |
| SOURCE-INJECTION | 外部内容携带恶意指令 | 数据/指令隔离，工具限制 |
| DATA-BOUNDARY | 敏感内容可能外传 | BLOCK/HUMAN |
| REPRO-GAP | 缺代码、输入、参数或环境 | 降低 Claim / BLOCK release |
| FRAMEWORK-BYPASS | 使用者经常绕过系统 | 简化所绕过机制 |
| PLATFORM-DRIFT | Runtime/Skill 行为变化 | capability snapshot + 回归测试 |
| ADAPTER-ENFORCEMENT-GAP | 平台 sandbox 只能限制工作区，不能强制 Task 子目录 | scoped-write 校验 + 独立任务目录；不得把提示约束称为平台强制 |
| PROVIDER-SEMANTIC-DRIFT | 不同模型 API 对工具、结构化输出、缓存和停止原因语义不同 | capability negotiation + provider-specific contract tests；不做静默模拟 |
| CLAIM-OVERREACH | Claim 超出 Evidence/Mode ceiling | 降级或 Human Gate |
| SOURCE-QUALITY | 来源质量或定位不足 | 标记限制，定向检索 |
| HANDOFF-OMITS-NEGATIVE | 失败/反证未传递 | BLOCK promotion |
| HANDOFF-AUDIT-COVERAGE | Transfer Manifest 条目没有完整映射到 Handoff | BLOCK promotion |
| HANDOFF-NEGATIVE-UNMAPPED | Handoff 中的限制、冲突、未决项或人工决定没有来源条目 | BLOCK promotion |
| HANDOFF-SEMANTIC-REVIEW-REQUIRED | 关键或高风险条目尚未完成有界独立抽样 | BLOCK promotion，完成最小样本复核。注：发布期 closeout 验证（`execution/closeout.py`）豁免此码——新发布 batch 的 audit 恒为 `review.status=pending`，语义评审是发布后的人工动作；完成标记只证明结构完整，transfer 门禁仍由 `handoff audit-transfer` 把守，两者不对称是有意设计 |
| HANDOFF-SUMMARY-DISTORTION | 抽样发现 Handoff 歪曲或无法验证来源语义 | BLOCK，修订 Handoff 并重新审计 |
| HANDOFF-OVERHEAD | H2 工件持续增加但不改变决策 | 降为 H1 或缩小触发器 |
| DELEGATION-FANOUT | 递归/并发膨胀 | 停止新委派，合并任务树 |
| COORDINATION-COST-HIGH | 协调/汇总/校核占比超过预算 | WARN，优先删 Agent、review 或字段 |
| COST-USAGE-UNKNOWN | 真实模型运行没有可用量数据 | 不得宣称 token/成本收益 |
| TOOL-OUTPUT-POISONING | 工具输出被当作高优先级指令 | 按不可信数据处理 |
| TRACE-SENSITIVE | trace 检测到敏感数据 | BLOCK，脱敏或删除 |
| TRACE-DATA-BOUNDARY | 外部 trace 与本地数据边界冲突 | BLOCK |

## 5. Agent 复核准入

创建 reviewer 前必须回答：

1. 要降低的具体风险是什么？
2. 为什么确定性检查不能解决？
3. reviewer 需要哪些最小输入？
4. 输出将改变什么决定？
5. 停止条件和 token 预算是什么？
6. reviewer 是否与原 Agent 共享同样的模型、Skill 和来源，从而缺乏真正独立性？

若第 4 项没有明确答案，不创建 reviewer。

## 6. Human Gate 设计

Gate 必须包含：

- 决策问题，而非泛泛“是否同意”；
- 可选动作及其影响；
- 相关 Claim/Evidence/Run/风险引用；
- Agent 建议与不确定性；
- 决策人、时间和范围；
- 哪些对象会因决定而生效/失效。

Gate 长期不改变任何结果时应删除或降级。人工批准频率高但阅读时间极短，是 `HUMAN-FATIGUE` 的信号。

## 7. 防止控制面递归增长

任何新增全局检查、Supervisor、Canary、恢复数据库或治理层前必须有：

- 至少一个真实事故或高风险可复现案例；
- 当前简单机制无法解决的证据；
- 明确消费方；
- 预计 token、开发、维护和人工成本；
- 删除/停止条件；
- 先作为局部 Skill、脚本或 Mode 规则试验的结果。

## 8. 验收条件

- 大多数检查由确定性工具完成；
- reviewer 都有具体风险和停止条件；
- Human Gate 数量少且确实改变决定；
- 任何 PASS 均说明其语义边界；
- review loop 可被检测和终止；
- 风险注册表不会因“可能发生”无限扩张，低价值预警可删除。
