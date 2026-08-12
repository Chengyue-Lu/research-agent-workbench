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
| CTX-STALE | 使用旧 revision | BLOCK |
| SKILL-CONFLICT | Skills 指令或契约冲突 | BLOCK |
| SKILL-PERMISSION-ESCALATION | Skill 越权 | BLOCK |
| SKILL-CONTEXT-FLOOD | Skill 过多/过长 | 拆 Task |
| CONSENSUS-CORRELATED | 多 Agent 同源错误被当共识 | 改用异质证据/工具或人类复核 |
| COORD-INTERFACE | 协调接口多于有效工作 | 简化流程 |
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
| CLAIM-OVERREACH | Claim 超出 Evidence/Mode ceiling | 降级或 Human Gate |
| SOURCE-QUALITY | 来源质量或定位不足 | 标记限制，定向检索 |
| HANDOFF-OMITS-NEGATIVE | 失败/反证未传递 | BLOCK promotion |
| DELEGATION-FANOUT | 递归/并发膨胀 | 停止新委派，合并任务树 |
| TOOL-OUTPUT-POISONING | 工具输出被当作高优先级指令 | 按不可信数据处理 |
| TRACE-SENSITIVE-DATA | trace 泄漏数据/密钥 | 脱敏或关闭相关 tracing |

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
