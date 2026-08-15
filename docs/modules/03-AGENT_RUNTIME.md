# 模块 03：Agent 运行模型

## 1. 目标

定义主 Agent 与子 Agent 的职责、Agent Profile、委派条件和执行映射。项目保持 API 与平台中立；黄毅维护 API session 及其测试，路诚钺维护进入任何执行路径之前的 Task、Mode、Skill、读取、Trace 和返回边界。

## 2. 主 Agent Charter

主 Agent 负责：

- 维护当前问题、约束、决定、风险和任务索引；
- 判断任务是否值得委派；
- 创建 Task Packet 并请求能力解析；
- 比较 Handoff、处理冲突和识别 Human Gate；
- 控制 Claim 强度、成本和停止时机；
- 在上下文压力前写 Main State 并主动 rollover。
- 给出目标路径和初始内容允许集；需要扩大正文读取范围时负责修订 Task。

主 Agent 不负责：

- 长期阅读和保存大规模原始材料；
- 直接吞入日志、数据集、整本论文或所有 Skill 正文；
- 亲自完成所有检索、编程、仿真和复核；
- 用自然语言摘要替代正式工件；
- 默认建立多轮 Agent 互审。
- 把“能访问工作区”解释为“可以读取全部仓库正文”。

## 3. Agent Profile

Agent Profile 是运行容器配置，不是研究方法。建议字段：

```yaml
agent_profile_id: evidence-scout
version: 0.1.0
purpose: read-heavy evidence discovery and extraction
model_policy:
  class: efficient-read-heavy
  default_slot: worker
  reasoning: medium
permission_ceiling:
  filesystem: worktree-write
  network: search-and-fetch
  external_write: forbidden
  allowed_roots: [work]
allowed_tool_capabilities: [web-search, document-read, citation-resolve]
default_context_policy: isolated-task
delegation:
  allowed: false
output_contracts: [evidence-record, handoff-packet]
```

Profile 不包含完整 Skill 指令，也不固定厂商模型。`default_slot` 只在小型本地模型池中指向 `primary`、`worker` 或一个显式 specialist；Task/人类可以覆盖它，但不能触发自动评分或静默 fallback。

## 4. 首批 Agent Profiles

### coordinator

主 Agent 配置。最小工具集，读取 Main State、Task/Handoff 索引和短摘要。默认不读取 raw materials。

### evidence-scout

源材料只读、任务区受限写的检索密集 Agent。允许搜索、文档阅读、引用解析并写自己的 Task 工件；禁止修改正式 Claim、其他 Task、上传本地敏感材料或生成最终综合结论。路径权限语义见 [ADR-0005](../decisions/0005-SCOPED-WRITE-PERMISSIONS.md)。

### simulation-auditor

受限计算 Agent。允许读取代码、参数、Run 工件，并在任务工作区执行检查；禁止修改基准 Run、改变模型假设或批准误差范围。

### targeted-reviewer

默认只读的专项审查 Agent。必须携带一个具体风险问题和停止条件，不能执行“全面复核一切”。

## 5. 委派准入

只有满足至少一项时才委派：

- 存在两个以上真正独立的读取或分析通道；
- 中间输出会显著污染主上下文；
- 需要与主 Agent 不同的 Skill 或工具边界；
- 高风险结果需要一次独立、定向复核；
- 任务运行时间较长且可以隔离。

以下情况默认不委派：

- 单一、短小、主 Agent 已有全部上下文的任务；
- 需要频繁共享隐式状态的紧耦合写入；
- 子 Agent 产出无法形成独立工件；
- 协调成本可能高于执行成本。

委派后，子 Agent 可以先发现路径、文件名、大小、版本与哈希等元数据；读取允许集之外的正文必须请求扩展并记录原因。普通返回使用 H1 Compact Handoff；只有风险、压缩、外部副作用、promotion、争议或 Task 明确要求时才升级为 H2 审计链。

## 6. 递归委派

默认 `max_delegation_depth: 1`。子 Agent 不得再创建子 Agent，除非 Task Packet 同时声明：

- `delegation.allowed: true`；
- 最大深度、最大并发和子预算；
- 可委派的子问题类型；
- 汇总责任与失败处理。

任何递归委派都必须返回一份合并后的 Handoff，而不是把完整子树抛给主 Agent。

## 7. 首版执行映射

### 纯 API 基线

- coordinator 默认使用 `primary` 槽；其他首批 Profile 默认使用 `worker` 槽；
- 每个子任务建立一个 fresh context，不继承主 Agent 的完整消息历史；
- Task、Skill Assignment、输入引用、输出契约和预算组成唯一启动材料；
- 工具循环在本地受轮次、调用数、结果大小、token/成本和 wall time 限制；
- provider/model 不满足能力或数据政策时阻断，不换槽、不换 Provider；
- 临时 API transcript 不是权威状态，退出前必须固化工件与 Handoff。

### 可选 Codex 映射

- `.codex/agents/*.toml` 保存项目级自定义 Agent Profile；
- Profile 可指定模型、推理强度、sandbox、MCP 和 skill 配置；
- `.agents/skills/*/SKILL.md` 保存仓库级 Skills；
- Task Prompt 显式点名 required Skills，避免只依赖隐式触发；
- 并发、等待、follow-up 和线程生命周期交给 Codex 原生能力；
- 写密集任务默认串行，或分配互不重叠的 write scope。

项目不把 Codex 或其他平台的私有 thread/session ID 写入科研内核，只可作为可选 Run metadata。OpenCode、Claude Code 等以后遵循同一规则；平台是否最终采用不影响 API 基线。

### Task-to-API 关闭事务（K-API-2 离线闭环）

`src/research_workbench/execution/` 已把上述基线缝合成一条可回放链路：

- `compile_session` 是纯函数编译边界：只接收冻结契约对象与项目根，产出最小 system/user 消息、冻结结构化输出 Schema、工具 allowlist 与带来源标注的会话限额；输入与 Skill 正文逐个哈希校验，超限阻断而非截断。
- 会话结果经唯一状态映射表写入 Attempt/Handoff/Receipt/Main State；completed 只有在按哈希钉住的确定性检查通过后才允许 `contract-satisfied` 宣称，模型漂移一律阻断宣称。
- 关闭事务 stage/validate/publish 三阶段：全部文档先落 staging 并通过 Schema 与交叉引用校验，再按固定顺序排他硬链接发布，Main State 严格殿后；完成标记只在发布后验证通过时写入，同进程同计划可续跑，跨进程中断由预检 fail-closed 阻断（不自动重跑模型）；发布后用真实校验器复核。
- `rwb execute task` 是唯一 CLI 入口；真实 Provider 接线保持显式阻断，live 调用属 M6-004。

## 8. 失败处理

| 失败 | 默认动作 |
|---|---|
| Agent 超时 | 写 incomplete Handoff，保留已有工件，不自动无限重试 |
| 输入版本变化 | 标记 `stale_input`，阻止合并 |
| Skill 缺失或版本不符 | `BLOCK`，重新解析能力 |
| 权限不足 | 返回 capability gap，不自动扩大权限 |
| 输出 Schema 不合格 | 一次定向修复；再次失败升级给主 Agent |
| 结果冲突 | 并列保存，主 Agent提出可判别的下一步，不做多数投票 |
| 写入冲突 | 阻止合并，重新划分 write scope |

## 9. 隐藏风险

- Agent Profile 被写成巨大“专家人格”，重新固化学科思维；
- 同模型的多个 Agent 产生相关性错误，伪装成共识；
- Agent 角色名称诱导主 Agent过度信任；
- 平台版本更新改变继承、权限或 Skill 发现行为；
- 平台或网关在 Workbench 已选模型后再次路由，造成 planned/actual 不一致；
- 子 Agent 隐式继承主 Agent 的高价模型，绕过 `worker` 槽；
- 子 Agent 为完成任务私自扩大问题边界；
- 写密集并行造成冲突与难以追责的合并。

应对：Profile 保持短小；正式可信度来自证据和验证，不来自角色名；记录 runtime capability snapshot；并行优先用于只读任务。

## 10. 验收条件

- 两个子 Agent 使用不同 Profile 和 Skills 完成任务；
- 主 Agent 只接收结构化 Handoff 和必要索引；
- 权限由 Profile、Task 和平台三者取交集；
- Skill 缺失时任务失败关闭，而非退化成无声明通用执行；
- 并行写入不允许重叠路径；
- 同一受限 Task 可以通过纯 API fresh session 执行，不依赖特定平台；
- 更换运行时只需实现 Adapter，不修改科研对象；
- 模型槽选择显式，Receipt 能核对实际 Provider/Model，没有自动 fallback。
