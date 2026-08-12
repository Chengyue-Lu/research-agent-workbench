# 测试与评估策略

## 1. 原则

- 先测试契约与引用，再测试模型行为；
- deterministic tests 与 Agent evals 分开；
- 结构 PASS 不代表科学正确；
- 测试失败、负结果和平台漂移均保留；
- 测试本身不能演化成庞大控制面。

## 2. 测试层级

### Unit

- ID/revision/hash；
- Schema 解析；
- Claim ceiling；
- Skill 过滤与冲突；
- write scope；
- stale propagation；
- Main State 构造。

### Contract

- Canonical Profile → Codex config；
- Skill Manifest → `SKILL.md` metadata；
- Task → Resolved Task；
- Handoff → promotion eligibility；
- Runtime capability snapshot；
- 工具 Adapter 输入/输出。

### Integration

- 初始化示例项目；
- evidence-scout 完成 Evidence Handoff；
- simulation-auditor 完成 V&V Handoff；
- 主 Agent读取两个 Handoff；
- checkpoint → 新会话恢复；
- input 修改 → stale 阻断。

### Skill Evals

每个 Skill 至少覆盖：正确触发、不应触发、缺工具、恶意来源、输出缺字段、版本回归、上下文过量、越权请求。

### Human Evaluation

研究者评估：错误/遗漏、限制保留、引用可用性、决策负担、恢复信心和是否愿意继续使用。

## 3. 故障注入

首批必须注入：

- 修改输入 hash；
- 删除必需输出；
- Skill version drift；
- 两个 Task write scope 重叠；
- Handoff 隐去反证；
- Runtime capability 缺少工具；
- 主会话在 checkpoint 前后终止；
- 外部来源携带提示注入文字；
- reviewer 给出与原 Agent 一致但无新证据的“共识”；
- trace 中出现敏感字段。

M3 首批已自动化的故障注入包括：主上下文原始材料、隐藏决定、子 Agent 压缩但未固化 Handoff、伪造 Context assessment、checkpoint digest 篡改、高 coordination ratio、超并发、重复 review、敏感/外部/full trace。摘要语义失真和真实运行中的 secret redaction 仍需后续定向案例，不用结构测试冒充完成。

## 4. 黄金样例

黄金样例不追求唯一语言输出，固定的是：

- 输入与来源；
- 必需/禁止的事实关系；
- 可接受 Claim ceiling；
- 应触发的风险；
- 必需工件和引用；
- 人类决定点。

避免把模型措辞快照当作稳定测试。

## 5. 平台测试

Codex Adapter 每次目标版本变化后检查：

- 项目 Agent 配置是否被发现；
- required Skill 是否可显式调用；
- sandbox/permission 是否符合交集；
- 子 Agent是否返回结果并可定位线程；
- 写范围是否被遵守；
- 大输出是否写文件而非污染主上下文。

若平台行为无法可靠自动断言，保留最小手工检查清单，并记录日期和版本。

## 6. 发布门槛

M1/M2 期间发布只要求结构、契约和示例可重复。只有 M5 后才允许宣称对科研质量或效率有帮助；在此之前文案使用“设计目标”“候选机制”“初步验证”。

## 7. 测试删减

每个里程碑删除：

- 不再对应当前行为的实现快照；
- 与上游平台重复且无额外保证的测试；
- 无法改变决策的指标测试；
- 只证明测试框架自身的多层自检。
