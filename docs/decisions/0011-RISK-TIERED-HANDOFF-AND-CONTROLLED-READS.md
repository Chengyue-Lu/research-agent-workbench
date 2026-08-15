# ADR-0011：按风险分级 Handoff 与受控内容读取

状态：Accepted（文档策略；Schema/自动强制待真实演练后决定）

日期：2026-08-14

后续说明：ADR-0012 保留本 ADR 的 H0/H1/H2 与受控读取决定，但将 Worklog 明确降为摘要，并要求全部跨 Agent 可见传递进入按需读取的 Attempt Archive。

## 背景

当前设计已经能表达 Handoff Packet、Transfer Manifest/Audit、Context Snapshot 和 Execution Receipt，但尚未经过真实多 Agent 工作量测。若所有子任务都固定生成完整链路，可能把大量 token、时间和人工注意力消耗在重复校核上。另一方面，仅限制写入范围不能阻止 Agent 扫描不相关文档；“仓库可访问”不能等价为“任务应读取”。

## 决定

### 1. Handoff 分三级

| 等级 | 适用情况 | 必需内容 |
|---|---|---|
| H0 同上下文收尾 | 没有委派和跨上下文转移 | 工作留痕、正式输出、验证结果；不创建形式化 Handoff |
| H1 Compact Handoff | 默认的普通子 Agent 返回 | 一个 Handoff Packet：状态、输出引用、验证、限制/冲突/未完成、建议下一动作 |
| H2 Audited Handoff | 风险或恢复触发 | H1 + Transfer Manifest/Audit；按需要增加 Context Snapshot、Execution Receipt 和独立语义抽样 |

以下任一条件触发 H2：子上下文发生压缩；结果将提升为关键 Evidence/Claim/Decision；存在外部副作用；Handoff 被质疑或存在摘要失真风险；任务跨越较长等待/会话销毁；Task/Project Protocol 明确要求；机器检查发现负面区段或关键条目无法映射。

H2 不是“更高级所以默认更好”。如果完整链路连续多次没有改变接受、返工、降级或 Human Gate 决定，应删减字段或缩小触发条件。

### 2. 内容读取默认拒绝，逐级扩大

每个 Agent 可以无条件读取当前 Task Packet、仓库级 `AGENTS.md`、选定 Agent Profile、冻结的 Skill Assignment、被选择 Skill 的入口和 Task 明确引用的输入。除此之外：

1. 可以为定位依赖进行文件名、目录名、大小、版本和哈希等元数据发现；
2. 不默认读取未声明文件的正文，不递归加载 `docs/`、`examples/`、候选 Skill、历史 Handoff 或其他 Agent 工作目录；
3. 需要新正文时，先记录原因，由实名 Task owner 扩大允许读取集或新增输入引用；
4. 临时越界读取不得因“已经看过”而自动成为正式输入，必须补录来源与版本；
5. Skill 引用只能沿本次已选择 Skill 的显式 references 逐级读取，不能借 Skill 发现扫描其他 Skill。

在 Schema 增加专门 `read_scope` 前，现有 `input_refs`、选定 Skill package、目标模块路径和 Task 说明共同构成内容读取允许集。实现侧不得把这一过渡表示解释为全仓库读取授权。

### 3. Worklog 记录决定，Attempt Archive 保存实际传递

Agent 在目标 Task 工作目录中维护简短 Worklog，至少记录：基线、目标、已采用/拒绝的关键决定、正文读取范围的扩大、修改路径、重要命令及结果、未完成项。无需记录每一次普通文件打开、每轮自省或完整 Chain-of-Thought。跨 Agent 实际可见的 Assignment、澄清、范围变化、Handoff 和 review 由 Attempt Archive 逐条留存。

Handoff 从正式工件、Trace 和 Worklog 中提取，不复制全过程到主上下文。Worklog 用于导航，完整消息通过索引按需回放；二者都不是新的全局状态数据库。

## 后果

- 普通任务的返回面明显缩小；高风险任务仍保留可审计链路。
- Agent 不能因为拥有工作区权限就自由读取所有材料。
- 实名 Task owner 需要更认真地给出入口和目标路径。
- 真实演练前只能把“流程可能更轻”视为设计假设，必须测量 Handoff 字符量、工件数、审阅时间、遗漏、回查和返工。

## 未采用方案

- 所有任务强制完整 Manifest/Audit/Receipt：在没有真实收益证据时控制成本过高。
- 只依靠 Agent 自觉不乱读：无法审计，也不能跨模型稳定复现。
- 记录每次读取与完整推理：产生 trace 洪流并增加敏感信息暴露。
- 允许任意读取、只限制写入：不能保护上下文预算和任务隔离。
