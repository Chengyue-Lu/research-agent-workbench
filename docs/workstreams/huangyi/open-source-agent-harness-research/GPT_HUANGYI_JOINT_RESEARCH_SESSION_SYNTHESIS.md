# GPT 建议：开源 Agent Harness、受控 Peer 通信与方法感知搜索联合调研

> 文档性质：GPT 建议（GPT 与黄毅的联合调研会话整理）
> 状态：Working Paper；不是 TASKS、ADR、Stable Architecture 或双方正式决议
> 提出与讨论：黄毅、GPT
> Owner：黄毅（`let778750-cpu` / `huangyi855`）
> Reviewer：路诚钺（`Chengyue-Lu`）
> 证据截止：2026-08-24

## 0. 文档用途、权威边界与阅读方式

本文不是聊天逐字稿，而是对本轮调研会话中问题、反证、候选设计、风险、外部证据、
评测假设和会话内选择的结构化恢复。原始对话中的自然语言可能混合提问、推测和建议，
本文不依赖措辞相似性来推断项目决定。

本文使用以下标签：

| 标签 | 含义 | 能否直接改变 RWB |
|---|---|---|
| `FACT` | 由固定上游源码、正式论文或当前 RWB 文件/代码直接支持 | 否；仍须服从证据所属表面的权威范围 |
| `INFERENCE` | 基于一项或多项事实作出的解释 | 否 |
| `PROPOSAL` | 黄毅提出或 GPT 整理的候选方向 | 否；需要独立 Task/ADR、实现和评测 |
| `CAPTURE_GAP` | 当前证据不足、身份不明、版本未固定或尚未实测 | 否；不得按“默认支持”处理 |

权威顺序继续遵守项目现有规则：accepted ADR/Stable docs 决定规范语义，
[`TASKS.md`](../../../TASKS.md) 决定实时状态，main 代码与测试决定实际行为；本文件、GPT
建议、外部项目文档和候选 PR 均不能改写这些真值。

本文只覆盖开源 Harness、Agent Team 通信、上下文/记忆、AnySearch 和联合科研检索假设。
PR #23、develop 治理及 Execution/Runtime 恢复审计只作为约束背景，不在此重复其正文。

## 1. RWB 当前约束与本调研的位置

### 1.1 已接受边界

- `FACT`：RWB 是人类治理的研究控制面、契约层与证据链，不是自主科研实验室，也不是
  通用 coding-agent Supervisor。见 [`PROJECT_CHARTER.md`](../../../PROJECT_CHARTER.md)。
- `FACT`：文件工件是跨会话权威；Runtime、会话数据库和 conversation memory 只能作为
  执行载体或可重建投影。
- `FACT`：原生子 Agent 是有界执行能力，不应反向成为全局 Supervisor、固定科研 DAG、
  第二真值数据库或全局消息总线。
- `FACT`：no-Skill 与 direct-tool 是一级路径；只有从真实 Method action 观察到重复、稳定、
  非平凡的语义缺口并证明净增量，才产生 Skill Need。
- `FACT`：Execution 只能消费冻结的 Task、Method、Capability、权限和数据出口约束，不能批准
  Claim、扩大权限或替代 Human Gate。
- `FACT`：当前全局下一任务是 M8-002；之后才是 M8-003 Method Resolution 和
  Method→Capability→Execution bridge。见 [`ROADMAP.md`](../../../ROADMAP.md) 和
  [`TASKS.md`](../../../TASKS.md)。

### 1.2 Architecture Hold 的准确解释

- `FACT`：本工作流本身没有解除 Architecture Hold，也没有获得 Runtime/Team/Search 生产接入授权。
- `PROPOSAL`：本轮沿用的窄范围解释是暂停新 Runtime、Router、自动 fallback、自由 Mesh、
  长期 memory 和复杂恢复等功能扩张；继续 M8、安全修复、Trace、测试、hash/ref、archive、
  file-only verification 和只读外部机制调查。
- `CAPTURE_GAP`：该措辞不等于新的正式 ADR；如需改变项目级 Gate，仍须由两位维护者确认。

### 1.3 本调研的角色

- `FACT`：黄毅在当前工作流中的职责是架构调研、证据核验和小规模只读验证；这不修改
  [`DEVELOPMENT.md`](../../../DEVELOPMENT.md) 的稳定责任表。
- `INFERENCE`：开源 Harness 调研的价值不是选定一个外部框架，而是把可借鉴机制、不可越过
  的 RWB 边界、真实实现缺口和可证伪试验条件分开。
- `PROPOSAL`：Agent Team 通信和 Agent 搜索均作为 M8-003 后的候选研究方向；二者可以在同一
  研究 PR 中联合讨论，但必须保持独立 claim ledger、证据和验收 Gate。

## 2. 黄毅提出的原始问题与前提修正

### 2.1 原始假设

黄毅在本轮会话中提出了两组有研究价值的问题：

1. 高质量 Harness/Agent 工具是否通常采用“主 Agent 结构化派发，子 Agent 完成后只回传主
   Agent”的 Star 拓扑，子 Agent 之间没有联系？
2. 如果 RWB 允许子 Agent 直接联系，能否提升团队效率、质量和性能，并形成创新？这样做会否
   污染主/子 Agent 上下文、加重幻觉和错误传播？
3. AnySearch 是否代表一种值得吸收的 Agent 搜索机制？它的垂直搜索、动态能力发现、并行
   查询和全文提取能否与 RWB 的科研检索、Agent Team 和 memory/context 设计结合？

### 2.2 核验后的修正

- `FACT`：部分成熟产品仍以父→子→父为主，但 DeepSeek 实验 Agent Team、Codex
  MultiAgentV2、Cline SDK Team 和 AutoGen 已存在 peer/direct/broadcast 等通信。因此“高质量
  Agent Team 普遍没有子 Agent 间通信”不是事实。
- `FACT`：允许 peer messaging 已有公开实现；“子 Agent 可以互相发消息”本身不是创新。
- `INFERENCE`：真正可能具有 RWB 差异化价值的是“受科研证据、权限、预算、可恢复审计和
  Human Gate 约束的 peer consultation”，不是自由聊天或全互联 Mesh。
- `FACT`：AnySearch 的开源仓库主要包含 Agent-facing `SKILL.md` 和四套薄 CLI；索引、跨源
  融合、排序、重排与数据源选择位于托管后端，没有在该仓库开源。
- `INFERENCE`：AnySearch 可被称为“开源 Agent 搜索调用与路由工作流”，不能称为“已开源并
  验证的搜索算法”。
- `FACT`：AnySearch 的 batch 是 1–5 个独立 REST 请求的并发执行，不等于 query decomposition、
  依赖规划、融合、去重或全局停止策略。
- `PROPOSAL`：更有辩护力的联合假设是“Method-grounded、Provider-neutral、provenance-first、
  data-egress-controlled 的多 Agent 科研检索协议”。

## 3. 开源 Agent Team 通信机制核验

### 3.1 固定观察矩阵

| 项目/表面 | `FACT`：已核验拓扑 | 上下文与持久化 | 重要限制 |
|---|---|---|---|
| DeepSeek Harness Subagent | 严格直接父→子→父 | 子 Agent 独立 Session；父级 inbox/FIFO | 稳定子系统不支持 sibling peer |
| DeepSeek Agent Team | 任意成员可向指定 teammate 发消息 | queued/delivered mailbox、MessageId 去重、任务 revision/CAS | 明确为实验性；write scope 仍有 advisory 成分 |
| Codex MultiAgentV2 | 同一 root tree 内可向 sibling、ancestor、descendant 发送 | spawn 可选择 none/full/last-N context；send 与 wake/follow-up 分离 | 未核验到 durable ACK、去重或 broadcast 契约 |
| OpenCode TaskTool | 父级调度 child，可多层嵌套 | child 是带 `parentID` 的 Session，可续接 | 未发现第一方 peer mailbox；共享 cwd/文件是潜在旁路 |
| Pi subagent example | 父级单发、并行或 chain | 每个子进程上下文隔离；chain 只传受控 previous result | 官方示例扩展，不是稳定 Team 协议 |
| Cline 产品 Subagents | 子 Agent 只读探索后回父 | 独立上下文；限制写文件、浏览器、MCP 和递归 spawn | 产品表面是实验性父子模式 |
| Cline SDK AgentTeamsRuntime | 指定 teammate 直发并支持 team broadcast | mailbox 可 export/hydrate，含 id/from/to/task/time/readAt | `readAt` 不等于 transport ACK；未见幂等去重契约 |
| AutoGen Core | direct message 与 topic publish/subscribe | Runtime 负责投递与 handler | 是通用多 Agent 框架，不能与 coding Harness 成熟度混为一类 |
| AgentScope | 以唯一成员名直发或广播；支持 InMemory/Redis message bus | Inbox middleware 在推理前把消息注入目标上下文 | destructive read 可能在崩溃窗口丢消息；没有应用级 ACK/dedup |
| LangGraph | 节点通过 typed state、`Send`、`Command` 和 reducer 交换 | checkpoint 保存图状态，不是 Agent mailbox | 节点 retry 可能从节点开头重跑；副作用必须另做幂等 |
| MetaGPT | Environment publish/subscribe 到 Role 私有队列 | Role 把观察到的消息写入 memory | 广播容易扩大上下文和错误相关；无可靠语义 ACK |
| CrewAI | manager/Agent 按 role 同步委派 Task 并接收返回 | Task/context 作为调用输入，结果作为字符串返回 | 主要是父子 delegation；未发现第一方 peer mailbox |
| Ruflo | mesh/hierarchical/centralized/hybrid、direct/broadcast、consensus 与跨机 federation 均有代码表面 | 进程内队列、Agent scope、working/episodic/semantic memory 及可选 SQLite | 当前子包仍为 alpha；默认消息与审计并不持久，安全/恢复语义不能按 README 宣传推定 |

关键固定来源：

- [DeepSeek Subagent](https://github.com/deepseek-ai/deepseek-harness/blob/b150a551b8d465e31e418e1b2eaf5e79bbb7d28e/docs/subsystems/subagent.md)
  与 [Agent Team](https://github.com/deepseek-ai/deepseek-harness/blob/b150a551b8d465e31e418e1b2eaf5e79bbb7d28e/docs/subsystems/agent-team.md)；
- [Codex message tool](https://github.com/openai/codex/blob/343074d4207d572809bd8cea15f4be1d09d98e0b/codex-rs/core/src/tools/handlers/multi_agents_v2/message_tool.rs)
  与 [agent control](https://github.com/openai/codex/blob/343074d4207d572809bd8cea15f4be1d09d98e0b/codex-rs/core/src/agent/control.rs)；
- [OpenCode TaskTool](https://github.com/anomalyco/opencode/blob/3a31c4ea801915c0b050df4b3842997ea62b6e93/packages/opencode/src/tool/task.ts)；
- [Pi subagent example](https://github.com/earendil-works/pi/blob/c49906ec77788625aacbdc53ebca6fbe65bd20f5/packages/coding-agent/examples/extensions/subagent/index.ts)；
- [Cline product subagents](https://github.com/cline/cline/blob/1de61b178aec844e0aa362474274ccbf6acf9403/docs/features/subagents.mdx)、
  [team runtime](https://github.com/cline/cline/blob/1de61b178aec844e0aa362474274ccbf6acf9403/sdk/packages/core/src/extensions/tools/team/multi-agent.ts)
  与 [team tools](https://github.com/cline/cline/blob/1de61b178aec844e0aa362474274ccbf6acf9403/sdk/packages/core/src/extensions/tools/team/team-tools.ts)；
- [AutoGen communication](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/message-and-communication.html)。
- [AgentScope TeamSay](https://github.com/agentscope-ai/agentscope/blob/da00849f2c3db60b16edaf2371ae1d863f341ae2/src/agentscope/app/_tool/_team_say.py)
  与 [Inbox middleware](https://github.com/agentscope-ai/agentscope/blob/da00849f2c3db60b16edaf2371ae1d863f341ae2/src/agentscope/app/middleware/_inbox_middleware.py)；
- [LangGraph types](https://github.com/langchain-ai/langgraph/blob/f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f/libs/langgraph/langgraph/types.py)、
  [MetaGPT Environment](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/environment/base_env.py)
  与 [CrewAI delegation](https://github.com/crewAIInc/crewAI/blob/f4731f5025f861c78e3af0487cc80bf5e7c64782/lib/crewai/src/crewai/tools/agent_tools/base_agent_tools.py)。

### 3.2 正确结论

- `FACT`：父子 Star、顺序 chain、受控 peer、全局 broadcast、topic/pub-sub 都真实存在；不存在一个
  可概括全部优质 Harness 的唯一拓扑。
- `INFERENCE`：编码 Harness 更常优先父子隔离，因为权限、写冲突和生命周期更容易收敛；通用
  multi-agent framework 更常暴露 direct/pub-sub，但其科研证据治理通常不如 RWB 所需严格。
- `CAPTURE_GAP`：未提供 peer tool 不证明子 Agent 绝对无法联系；共享文件、cwd、数据库或外部工具
  可能构成未受控旁路。
- `INFERENCE`：应比较机制和语义，而不是按项目名整体复制。

### 3.3 “通信”必须拆成多个协议层

- `FACT`：模型通常只生成 token、role message、tool call 或 structured output；Agent identity、寻址、
  队列、唤醒、ACK、重试、TTL、权限和 mailbox ownership 由 Harness/Runtime 实现。
- `FACT`：长上下文不等于 memory，structured output 不等于消息已投递，Session/Thread 持久化也不
  等于 mailbox 可恢复。
- `PROPOSAL`：RWB 的 conformance 研究至少分别观察以下九层，不能只记录 `send_message=true`：

| 层 | 最小问题 |
|---|---|
| Transport | in-process queue、subprocess JSONL、RPC、Redis/DB mailbox 还是文件引用？ |
| Addressing | parent/child、稳定 Agent ID、direct、broadcast、topic 还是 graph edge？ |
| Payload | 自由文本、Task packet、Tool result、typed envelope 还是 SourceRef/hash？ |
| Context admission | 全历史、last-N、隔离 child、shared transcript 还是按需引用？ |
| Delivery | created、queued、durable、delivered、consumed、expired、failed 如何区分？ |
| Semantic disposition | needs-verification、adopted、rejected、conflicted、stale 如何记录？ |
| Recovery | 顺序、去重、幂等 retry、cancel、cold resume 和副作用如何处理？ |
| Governance | sender 身份、权限不传播、数据出口、敏感度与 Human Gate 如何约束？ |
| Observability | message ID、hash、时间、reply、capture gap 和 Trace 是否完整？ |

- `INFERENCE`：多数 Harness 实现了 Transport、Addressing 和 Context 中的一部分，却没有同时提供
  可靠传输、科研语义验收和权限治理。Transport ACK 永远不能替代 Evidence/Claim admission。

### 3.4 开放权重强模型不是 Agent-Team Transport

- `FACT`：截至 2026-08-23，没有一个可把 general、coding、tool-use、agentic、中文科研、成本和
  许可证合并为单一名次的权威榜单。[Open Agent Leaderboard](https://huggingface.co/blog/ibm-research/open-agent-leaderboard)
  也明确把“模型 + Agent/Harness”作为评测对象。
- `FACT`：[BFCL V4](https://gorilla.cs.berkeley.edu/leaderboard) 页面最后更新时间为 2026-04-12，
  不能用来给此后发布的 Qwen3.8、Kimi K3、GLM-5.2 或 DeepSeek V4 排当前工具调用名次。
- `INFERENCE`：本文只能建立多维候选池，不能写“当前开源模型第一名/前五名”。厂商模型卡中的
  Agent/coding 分数若使用不同 Claude Code、Codex、OpenCode、OpenHands 或自建 scaffold，也不能
  归因给模型单体。

| 候选 | 固定版本 | `FACT`：公开能力/许可证边界 | RWB 候选槽与主要风险 |
|---|---|---|---|
| DeepSeek V4 Pro / Flash | `b5968e9190ef...` / `60d8d70770c6...` | MIT 权重；官方卡报告长上下文、代码和 agentic 能力 | Pro 可进入 primary 竞争臂，Flash 可进入 worker；部署、Provider/parser 和厂商 benchmark 需独立核验 |
| Qwen3.8 2.4T / 27B | `207bd685a7e3...` / `1d4bf0f2ff60...` | 大模型使用自定义许可，27B 为 Apache-2.0；官方提供 tool parser 与长上下文配置 | 2.4T 可作远端 primary，27B 可作中文/多模态 worker；parser 是 Serving 语法，不是消息协议 |
| Kimi K3 | `a590ce090cb0...` | 自定义 Kimi K3 License；官方卡报告 1M、多模态、代码与科研能力 | 可作长文/科研候选；多轮 Tool 调用要求完整 assistant reasoning/tool history 回注，与 RWB Trace/DataPolicy 有冲突 |
| GLM-5.2 | `b4734de4facf...` | MIT 权重；官方提供 function calling、structured output 与长上下文 | 中文 primary 候选；总体权重和 KV/Serving 成本很高，不能按 activated parameters 估算全部成本 |
| MiniMax M3 | `f0e1c1e04d40...` | 自定义许可；长上下文、多模态和 Provider verifier | specialist/Provider conformance 候选；第三方 Serving 可能改变 tool schema 与语言遵循 |
| gpt-oss-120b | `b5c939de8f75...` | Apache-2.0；128K、Harmony/tool calling/structured output | 可复现实验基线，不应称当前 frontier；中文科研 Evidence 忠实度须实测 |
| Llama 4 | `73d14711bcc7...` | 自定义 Community License；长上下文和 function-call 格式 | 生态/负面对照；官方支持语言未列中文，不适合作为 RWB 中文主候选 |

- `PROPOSAL`：所有模型必须在同一 RWB Harness、Task、Method、source corpus、Tool、权限、预算、
  reasoning effort 和 retry 条件下比较；Receipt 同时冻结 weight SHA、requested/observed model、
  Provider、Serving/parser、量化和 Harness commit。
- `PROPOSAL`：同质团队与异质 lead/worker/verifier 都要实验；通信前先冻结独立结论，并记录共享
  模型、Provider、parser、检索后端和来源造成的 error-correlation domain。
- `PROPOSAL`：模型如要求保留 reasoning history，只能在一个 Attempt 的 Provider 协议处理中短暂
  使用；Archive/Trace/Receipt 不得持久化隐藏 Chain-of-Thought，也不能绕过数据出口授权。

### 3.5 Ruflo 固定版本审计：机制覆盖广，但不能整体移植

本轮新增核验对象为 [Ruflo `main@3c99b1c84a25948c42a163253bac6effed5fbbbb`](https://github.com/ruvnet/ruflo/tree/3c99b1c84a25948c42a163253bac6effed5fbbbb)，
获取时间为 2026-08-24。根包版本为 `3.38.19`，仓库根许可证为 MIT；被重点检查的
`@claude-flow/swarm@3.0.0-alpha.7`、`@claude-flow/memory@3.0.0-alpha.23` 和
`@claude-flow/plugin-agent-federation@1.0.0-alpha.18` 仍是 alpha 表面。因此本文把它当作机制样本，
不把 `main` 快照、README 能力表或项目自身 benchmark 宣传提升为稳定产品事实。

| 表面 | `FACT`：固定源码直接证明 | 对本研究的边界 |
|---|---|---|
| Topology | [TopologyManager](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/topology-manager.ts) 支持 mesh、hierarchical、centralized、hybrid，并会自动 rebalance | 这进一步证明“动态/多拓扑”已有先行实现，不是 RWB 可单独主张的创新；其随机连边也不是科研 Method 约束 |
| Swarm MessageBus | [MessageBus](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/message-bus.ts) 有 direct/broadcast、优先队列、TTL、显式 ACK 接口和有界 callback retry | 这是进程内 transport；没有科研 disposition、Evidence admission 或跨 Attempt 权威语义 |
| Codex Harness inbox | [Contract](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/codex/src/harness/contract.ts#L96-L112) 定义 issuer/audience、correlation/causation、sequence、expiry、content digest 和 receipt；[reference inbox](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/codex/src/harness/in-memory-inbox-reference.ts#L42-L151) 实现精确重试幂等、冲突隔离、cursor、定向接收与 ACK | 这些是明确的先行技术；但实现自述 unsigned、non-durable、`referenceOnly`，不能证明 enforce transport 或 crash recovery |
| Consensus transport | [Local/Federation transport](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/consensus/transport.ts) 分离本地与跨机传输，并提供可选 Ed25519、sequence、correlation 和 timeout | Raft/PBFT/Gossip 解决节点协议一致性，不证明被投票内容为科学事实，也不能批准 RWB Claim |
| Federation | [Federation envelope](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/plugin-agent-federation/src/domain/entities/federation-envelope.ts) 与 [PolicyEngine](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/plugin-agent-federation/src/application/policy-engine.ts) 定义 source/target/session/type、PII、trust、claims、rate limit 和消息类型 | 可借鉴“身份、策略和 payload 分开”，但不能把 trust score、PII regex 或 transport signature 等同于数据出口授权和内容可信 |
| Memory | [Agent scope](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/memory/src/agent-memory-scope.ts) 区分 project/local/user；[TieredMemoryStore](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/memory/src/tiered-memory.ts) 区分 working/episodic/semantic，并可记录 temporal validity、supersedes 和 durable/volatile | scope 与 tier 是存储/可见性机制，不是 Evidence/Claim 等级；RWB 仍以文件工件为权威 |
| `claims` | [包入口](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/claims/src/index.ts) 明确管理 GitHub issue/work ownership、handoff 和 review | 它不是 RWB 的科研命题 Claim；名称相同但语义不同，禁止直接映射 |

#### 3.5.1 已由源码证实的实现限制

- `FACT`：Ruflo 至少存在三套不能混称的通信面：`ruflo-swarm` 插件说明 Task/TeamCreate/SendMessage
  是 Claude Code 宿主原生工具；`@claude-flow/swarm` 另有进程内 MessageBus；consensus 又使用默认
  LocalTransport 或可注入 FederationTransport。静态审计没有证明三者形成同一套可靠 Agent-Team transport。
- `FACT`：TopologyManager/coordinator 保存和重平衡 topology 状态，但 task assignment/broadcast 直接
  调 MessageBus；固定路径没有按 topology edge 做发送准入。因此 mesh/hierarchical 等名称不能证明
  运行时通信边、权限或 Method 依赖已被强制。
- `FACT`：`MessageBusConfig.enablePersistence` 存在，但固定提交的 MessageBus 没有持久化实现；shutdown
  会清空 queue、subscription 与 pending ACK。队列满时移除最低优先项而不形成 durable failure record。
- `FACT`：ACK timeout 只更新统计和发事件，不触发重投；只有 callback 抛错才 retry。源码还明确标注
  broadcast callback 失败时会重入无人消费的 `broadcast` 队列，后续 retry/failed 可能静默丢失；异步
  callback rejection 也没有在该路径被 await。故它最多证明可观察 ACK 与有界同步 callback retry。
- `FACT`：[FederationTransport](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/consensus/federation-transport.ts)
  的 request/reply correlation 与签名校验具有参考价值，但 pending、sequence 和 last-seen state 都在内存；
  broadcast 使用 `allSettled` 并吞掉单 peer 失败，不能当作 durable all-recipient delivery。
- `FACT`：固定提交的 federation 默认 `authorizationMode` 为 `legacy`；没有 transport 时，
  `sendToNode` 只记录 “in-process noop” 后正常返回，使上游 RoutingResult 仍可能显示 success。
- `FACT`：[FederationBudget](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/plugin-agent-federation/src/domain/value-objects/federation-budget.ts#L162-L210)
  会计算 `nextHopCount` 和 `remaining`，但固定调用路径只把 hop 写入 audit metadata；实际
  [coordinator 调用](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/plugin-agent-federation/src/application/federation-coordinator.ts#L324-L360)
  仍传原 payload，envelope 也没有 budget/hop 字段。因此注释中的预算意图不能升级为跨 hop 强制事实。
- `FACT`：入站 dispatcher 能核验 peer、状态、签名和可选 policy，但没有使用 envelope 的 nonce、
  `isExpired()` 或 envelopeId 建立重放/去重 Gate；默认插件 audit persistence 只是进程内数组。
- `FACT`：coordinator 的普通 `sendMessage` 会执行 policy 与 hop/budget 检查；`broadcastMessage` 则直接进入
  routing broadcast。二者不是同一 enforcement path，不能宣称所有出站方式已有一致治理。
- `FACT`：[agent spawn/execute](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/cli/src/mcp-tools/agent-tools.ts)
  将注册与执行分开；spawn 只建立 registry/swarm 记录，另一个 `agent_execute` 路径才发 Provider 请求，
  且固定实现是单次 system+user 调用。注册 N 个 Agent 不等于 N 个已运行、可使用工具并可靠互联的 worker。
- `FACT`：[session tools](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/cli/src/mcp-tools/session-tools.ts)
  保存/恢复 legacy JSON 并 best-effort 导入 memory；没有 RWB 所要求的 canonical digest、Protocol revision、
  Git baseline、Attempt identity、side-effect reconciliation 或 resume-check。因此它是 state rehydration，
  不是执行恢复或可重放研究 Attempt。
- `FACT`：[authorization propagator](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/security/src/authorization/propagator.ts)
  源码自述当前文件尚无调用点；legacy scope 为通配/无限边界，server auth 也只检查标识与凭据非空。
  ADR/组件存在不能证明消息 dispatcher 已经执行递减授权。
- `CAPTURE_GAP`：[observability skill](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/plugins/ruflo-observability/skills/observe-trace/SKILL.md)
  从 memory rows 查询并重建视图；本轮未发现每次 send/tool call 都接入 canonical execution-boundary sink
  的端到端证明，不能据此宣称 full distributed Trace。
- `FACT`：[RetrievalGuard](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/memory/src/agentdb-retrieval-guard.ts)
  默认关闭；非 strict 模式只标记可疑 memory，仍允许其进入结果。`LearningBridge` 会因条目被访问而提高
  confidence，后台学习也可从 success/partial trajectory 自动抽取 pattern。
- `FACT`：仓库中的 multi-agent 结果文件明确标为
  [mock、synthetic deterministic Bernoulli、无 LLM 调用](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/docs/benchmarks/multi-agent/multiagent-mock-2026-06-22T17-02-43-846Z.json#L1-L98)。README 的 routing accuracy、跨框架倍数和 throughput target
  因而只能记录为项目宣传或目标，不能作为 Ruflo 在 RWB 科研任务上的独立性能事实。
- `INFERENCE`：这些缺口不证明 Ruflo “没有价值”，但证明 README 的 zero-trust、self-learning、
  recovery、audit 或性能词不能代替 end-to-end 对抗验证。GitHub Issue 也只能证明缺陷被报告，不能推断频率。

#### 3.5.2 对 RWB 的新增启发

- `PROPOSAL`：把系统严格拆成三个平面：`Collaboration Transport` 只负责可靠送达，`Context/Memory
  Projection` 只负责可重建视图，`Research Acceptance` 才能接纳 Evidence/Claim。三者不能因使用同一
  数据库或同一 Agent 自动合并。
- `PROPOSAL`：回执至少再拆成三层：`IngressReceipt` 只证明接收、去重、hash 与 expiry；
  `SemanticDisposition` 记录 incorporated/rejected/conflict/needs-human/stale；
  `ResearchPromotionDecision` 继续由 Evidence/Claim Gate 决定。前一层成功不能推导后一层成功。
- `PROPOSAL`：借鉴 temporal validity、`supersedes`、durable/volatile honesty，但把它落到稳定文件引用、
  Evidence/Claim lifecycle 或可重建索引；不增加 AgentDB 式第二科研真值库。
- `REJECT`：访问次数、Agent 投票、trajectory success 或 topology consensus 不得提高科研置信度；这会把
  检索流行度和错误复用变成自强化反馈。
- `PROPOSAL`：未来 Peer Envelope 应同时携带 immutable SourceRef/hash 与 correlation domain；共享 memory
  只能返回候选引用，不向所有 Agent 注入可变全文，也不能转移 Method、权限或 Human Gate。
- `INFERENCE`：Ruflo 最有价值的反面教材是“接口名存在不等于语义闭环存在”。RWB conformance 必须分别
  验证 declared、wired、enforced、durable、recoverable 和 evidence-admissible，不能只数 MCP tools。
- `DEFER`：跨机器 federation、共识协议、自动拓扑、自学习 memory、全局 Router 和大规模 swarm 均超出
  RWB 当前 evidence-synthesis/simulation 小团队范围；Architecture Hold 下不接入、不安装、不运行 live spike。

## 4. Peer 通信的潜在收益与风险

### 4.1 可能收益

- `INFERENCE`：存在跨子任务依赖时，直接询问负责相邻证据的 Agent 可能减少主 Agent 的摘要
  中转和等待。
- `INFERENCE`：peer 可以在提交最终 handoff 前发现证据冲突、版本漂移或重复劳动。
- `INFERENCE`：主 Agent 不必加载所有原始结果，只接收 conflict index、source refs 和最终
  disposition，可降低中央上下文压力。
- `INFERENCE`：异质模型、不同检索 Provider 或不同证据来源可能提供互补错误分布。
- `INFERENCE`：受控链式通信适合长文档分片或存在明确依赖的检索任务。

这些收益都是条件性的；它们不是“消息越多越好”的证明。

### 4.2 质量与幻觉风险

- `FACT`：同质 Agent、相同 prompt、相同检索结果和相同模型会产生相关错误，多个 Agent 的一致
  不能被视为独立证据。
- `INFERENCE`：错误摘要被 peer 复用后会形成引用循环、虚假共识和“多数即事实”。
- `INFERENCE`：在看到同伴答案后再独立思考，会引入 anchoring、从众和 semantic reversal。
- `INFERENCE`：自由聊天会把事实、推断、建议和未验证问题混合，降低主 Agent 对不确定性的
  可见性。
- `INFERENCE`：广播相同大段 Tool Result 会扩大上下文、重复 token、延迟、费用和 prompt
  injection 攻击面。
- `INFERENCE`：同伴消息如果携带工具建议或权限假设，可能造成 authority laundering；消息不能
  转移 Task、Method、权限或 Human Gate 权威。

### 4.3 系统与恢复风险

- `INFERENCE`：并发 peer 写入会产生重复消息、乱序、丢失、重放和 write race。
- `INFERENCE`：只有“已读”而没有 queued/delivered/ACK/disposition，恢复后无法判断是否需要重发。
- `INFERENCE`：transport ACK 只证明消息到达，不能证明目标接受、验证或采用了语义。
- `INFERENCE`：跨 Attempt 消息若没有 owner、Task scope、input hash 和 TTL，会在 resume 后变成 stale
  authority。
- `FACT`：RWB 当前 Trace/Receipt 已有 sender、receiver、in-reply-to 和 coordination 汇总等可用
  基础，但尚无完整 peer scope、cross-Attempt mailbox ownership、幂等、ACK 或 semantic disposition
  协议。
- `PROPOSAL`：在上述缺口解决前，不实现自由 peer mesh 或生产 TeamExecutionPort。

## 5. CCF-A 主会论文的正反证据

本文把 ACL、ICML、NeurIPS、SIGIR 等 CCF-A 正式主会论文作为核心；Findings、workshop、
benchmark track 和其他高质量来源只能显式标为补充。

| 来源 | `FACT`：直接观察 | 对 RWB 的限定 |
|---|---|---|
| [Beyond Frameworks, ACL 2025](https://aclanthology.org/2025.acl-long.1037/) | 中央治理、有序交互和 Instructor summary 常有较好的质量—token 权衡；去中心 P2P 可显著增加上下文 | 只覆盖论文设定中的任务与模型，不能证明中央拓扑永远最好 |
| [Chain of Agents, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/ee71a4b14ec26710b39ee6be113d7750-Abstract-Conference.html) | 顺序 worker 通信有助于跨分片依赖；把全部中间内容给 manager 可能退化 | 支持 bounded chain，不支持自由 Mesh |
| [Multiagent Debate, ICML 2024](https://proceedings.mlr.press/v235/du24e.html) | 多 Agent 辩论在部分推理与事实性任务上改善结果 | 是正证据，不代表稳定优于简单基线 |
| [Should we be going MAD?, ICML 2024](https://proceedings.mlr.press/v235/smit24a.html) | debate 不稳定优于 self-consistency/ensemble，且更依赖调参 | 必须保留独立并行+确定性聚合作为基线 |
| [Multi-LLM Debate, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/32e07a110c6c6acf1afbf2bf82b614ad-Abstract-Conference.html) | 同质 Agent 和共同误解可形成 echo chamber；质量/差异性剪枝有帮助 | Agent 数量不等于证据独立性 |
| [Debate or Vote, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/934252acd87f254d5d4672fbde283bd2-Abstract-Conference.html) | 多数投票在多组实验中常优于去中心辩论，更多轮次可能退化 | 收益可能来自独立采样与聚合，而不是交流本身 |
| [ReConcile, ACL 2024](https://aclanthology.org/2024.acl-long.381/) | 异质模型讨论可能互补；同模型实例容易维持共同错误 | Provider/模型/来源独立性必须进入评测 |
| [GPTSwarm, ICML 2024](https://proceedings.mlr.press/v235/zhuge24a.html) | 将 Agent/操作抽象为可优化计算图，边代表信息流 | 自动图优化不提供权限、数据出口、Trace 或科学正确性 |
| [AgentDropout, ACL 2025](https://aclanthology.org/2025.acl-long.1170/) | 动态删除冗余 Agent/边可在其任务上降低 token 并提高得分 | 只支持“通信应可裁剪”，不证明动态 Router 可直接生产化 |
| [GUARDIAN, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/0bc795afae289ed465a65a3b4b1f4eb7-Abstract-Conference.html) | 将多轮消息建成时序图以检测幻觉和错误传播 | 检测式模型不能替代预防性权限、来源验证和 Human Gate |
| [Dynamic Communication Topologies, ACL 2026](https://aclanthology.org/2026.acl-long.1764/) | 任务自适应稀疏拓扑可在论文设定中权衡准确、成本与鲁棒性 | 动态拓扑已有公开先行工作，不能把“动态连边”本身声称为 RWB 创新 |
| [SILO-BENCH, ACL 2026](https://aclanthology.org/2026.acl-long.1354/) | 大量通信不保证形成有效分布式计算，复杂任务/大团队可能崩溃 | 大规模 benchmark 不能直接外推到 RWB 当前最多两个并行子 Agent |
| [Conjunctive Prompt Attacks, ACL 2026](https://aclanthology.org/2026.acl-long.1577/) | 分散在用户输入和远端 Agent 模板中的无害片段可经路由组合成攻击 | 安全检查必须覆盖跨消息组合，不能只逐条扫描 |

综合判断：

- `FACT`：论文同时存在正证据和反证；不存在“peer communication 必然提高正确率”的结论。
- `INFERENCE`：RWB 应采用中央治理、稀疏、任务依赖、证据绑定的通信，而不是默认 Star 或默认 Mesh。
- `INFERENCE`：通信拓扑需要按任务动态选择，并与 single-agent、independent ensemble、Star、chain
  和 free mesh 做同预算消融。
- `FACT`：CommNet、DIAL/RIAL、TarMAC 等 CCF-A MARL 论文早已研究广播、有限带宽、何时发送、
  发给谁和信息瓶颈；但其潜在向量、共享 reward 和封闭仿真环境只构成间接证据，不能代替 RWB 的
  自然语言语义、权限、来源与科研接纳协议。

## 6. 候选创新一：Controlled Peer Evidence Exchange

### 6.1 候选定义

`PROPOSAL`：RWB 可以研究 `Controlled Peer Evidence Exchange`（受控同伴证据交换），其目标不是
让子 Agent 自由对话，而是在主 Agent 保留治理权的情况下，允许针对显式依赖进行一跳、带来源、
可恢复的咨询。

最小原则：

1. **中央治理**：主 Agent 决定 Task 分解、允许边、预算、停止和结果处置。
2. **commit-before-contact**：Agent 在看到同伴结论前先冻结自己的初始结果或 digest，用于检测
   从众和 semantic reversal。
3. **证据绑定**：消息引用 SourceRef、artifact ref 和 SHA-256，不复制完整正文作为权威。
4. **语义分栏**：只允许 `FACT / INFERENCE / PROPOSAL / QUESTION / CONFLICT` 等明确类型。
5. **一跳与无广播默认**：只有主 Agent 授权的 dependency edge 可发；禁止递归 relay 和默认 broadcast。
6. **预算**：每条边有 message、token、round、hop、deadline 和 context budget。
7. **不转移权威**：peer 消息不能修改 Method、Task、权限、Claim ceiling 或 Human Gate。
8. **双层确认**：transport ACK 与 semantic disposition 分离；后者至少区分 adopted、rejected、
   needs-verification、conflict、stale。
9. **幂等与恢复**：message ID、sender/receiver、Task/Attempt、input hash、TTL、dedup key 和 parent
   message 都可重建。
10. **最小主上下文**：主 Agent 读取 conflict index、source refs 和最终 handoff，不加载完整通信图。

### 6.2 候选消息字段

这些字段是研究提案，不是本文件新增的公共 Schema：

```text
message_id
task_ref / attempt_ref
sender / receiver
message_type
purpose / dependency_ref
source_refs[] / content_hashes[]
classification / data_egress_decision
independent_commit_ref
ttl / hop / round / token_budget
sent_at / queued_at / delivered_at / ack_at
in_reply_to / dedup_key
semantic_disposition
capture_gap
```

### 6.3 不能声称的内容

- `CAPTURE_GAP`：尚未证明 RWB 的科研任务会因 peer exchange 获得重复净增量。
- `CAPTURE_GAP`：尚未决定 mailbox 是 Attempt 内单 writer、追加日志还是独立 artifact。
- `CAPTURE_GAP`：尚未证明多 Runtime、跨 Provider 情况下 ACK、取消和权限收窄的一致语义。
- `PROPOSAL`：以上问题必须由 M8-003 后的独立 Task/ADR 和对抗测试决定。

### 6.4 与 RWB 当前应用范围的适配裁决

- `FACT`：RWB 首版正式 Mode 只有 `evidence-synthesis` 与 `simulation`；当前协议示例限制
  `max_parallel_subagents: 2`、`max_delegation_depth: 1`、协调成本 WARN 阈值为 0.33。见
  [`02-PROTOCOL_AND_MODES.md`](../../../modules/02-PROTOCOL_AND_MODES.md) 和
  [`10-OBSERVABILITY_EVALUATION_COST.md`](../../../modules/10-OBSERVABILITY_EVALUATION_COST.md)。
- `FACT`：[`03-AGENT_RUNTIME.md`](../../../modules/03-AGENT_RUNTIME.md) 只在存在真正独立通道、
  主上下文污染、不同工具边界、独立复核或长任务隔离时允许委派；紧耦合写入和协调成本高于执行
  成本时默认不委派。

| 阶段 | 本轮裁决 |
|---|---|
| `NOW` | 保持父→子→父默认拓扑；只在 working paper/fixture 中研究 delivery lifecycle、模型消息忠实度和同预算消融；不新增 Runtime、Router、Team、公共 Schema 或生产 mailbox |
| `LATER` | M8-003 后，只有真实 Evidence/Simulation Task 证明主 Agent 中转成为瓶颈，才由独立 Task/ADR 评估一跳 Peer Evidence Exchange |
| `REJECT` | 全局 shared transcript、自由 sibling chat、无界 broadcast、多跳 gossip、动态自动 Router、递归 team、共享写路径和 peer 直接修改 Main State/Method/Evidence/Claim |

当前最贴近产品范围的两个 use case 是：

1. `evidence-synthesis`：检索 Agent 先独立冻结 Source/Evidence 候选；只有覆盖缺口、反证或 locator
   冲突时，交换 `EvidenceRequest / EvidenceResponse / ConflictNotice` 与 SourceRef/hash。AnySearch
   title/snippet 仍先进入 Source Inbox，不得经 peer 消息升级为 Evidence。
2. `simulation`：执行 Agent 提交 Run manifest、输入、环境和输出 hash；独立审计 Agent 可发
   `VerificationRequest / ConflictNotice`，但不能批准误差阈值、模型假设、外部有效性或 Claim。

`INFERENCE`：普通独立检索、代码扫描、Schema/格式检查更适合隔离并行后由主 Agent 聚合；为这些
任务启用 peer chat 的协调、上下文、安全和恢复成本大概率高于收益。

## 7. AnySearch v3.1.0 静态审计

### 7.1 来源和真实开源边界

- `FACT`：固定基线是 [AnySearch v3.1.0](https://github.com/anysearch-ai/anysearch-skill/tree/4d6cef918e9338c9deef43b81ac0f7e22606825f)，
  commit `4d6cef918e9338c9deef43b81ac0f7e22606825f`，客户端仓库许可证为
  [Apache-2.0](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/LICENSE)。
- `FACT`：开源内容包括 `SKILL.md`、Python/Node/PowerShell/Bash CLI、共享生成块、测试和 CI。
- `FACT`：CLI 调用托管的 `/v1/search`、`/v1/sub-domains` 和 `/v1/extract`；开源仓库不包含索引、
  source routing、融合、去重和 rerank 后端。
- `FACT`：仓库 [SECURITY.md](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/SECURITY.md)
  的适用范围不能替代托管 API 的独立安全审计。
- `INFERENCE`：Apache-2.0 只覆盖仓库代码，不能自动证明托管服务条款、底层搜索数据许可证、
  隐私行为或长期 SLA。

### 7.2 已证实能力

| 机制 | `FACT`：v3.1.0 行为 | 可借鉴性 |
|---|---|---|
| general search | 向 `/v1/search` 发送自然语言 query | 外部 Tool Provider 基础能力 |
| vertical search | 通过 tag 与结构化 params 路由 | 参数 Schema 优于模型自由猜测 |
| `get_sub_domains` | 动态返回 domain/tag/required params | 可转译为 capability discovery，但须冻结 hash |
| hybrid | Skill 建议 general + N vertical | 只是 provider heuristic，非已验证最优策略 |
| batch | 1–5 个请求并发，保持输入顺序，允许逐项失败 | bounded fan-out、partial failure 值得借鉴 |
| extract | HTML/XHTML/text/JSON/Markdown；外部内容标不可信 | 适合 source discovery/inbox，不等于 Evidence |
| cross-runtime | 四套 CLI 和共享生成/contract test | 可借鉴统一接口和跨 Runtime contract test |

### 7.3 查询规划不是搜索算法

- `FACT`：[SKILL.md](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/SKILL.md)
  规定垂直优先、不确定时 hybrid、“coverage beats guessing”。
- `FACT`：CLI 只做参数解析、转换和请求；它不理解 Research Question、Claim 类型、Protocol、来源
  边界，也不生成可审计 Search Plan。
- `INFERENCE`：这些规则属于 provider-specific Search Strategy 候选，不能反向定义 RWB Method。
- `INFERENCE`：固定 vertical/hybrid fan-out 会增加查询数、配额、相关错误、上下文和来源偏差，
  并可能在“无合适 vertical”的任务上劣于 general 或 abstain。

### 7.4 Provenance 和 Evidence 缺口

- `FACT`：CLI 的搜索 Markdown 主要保留 title、URL、snippet/content、结果数和耗时。
- `FACT`：成功响应的 request ID、底层 provider/source ID、排名分数、抓取版本、canonical DOI、
  结果 hash 和排序理由没有形成 RWB 可恢复的 provenance。
- `FACT`：客户端按 API 返回顺序展示；没有客户端排序或去重实现。
- `FACT`：extract 支持的正文格式不含 PDF、DOC/DOCX、图片和其他二进制。
- `INFERENCE`：学术搜索中，返回 DOI、URL、摘要或 snippet 只能用于发现候选来源，不能证明已读取
  原文、定位支持段落或满足 Claim。
- `INFERENCE`：AnySearch backend rank 不能成为 RWB Evidence Strength 或 Claim ceiling。
- `CAPTURE_GAP`：未公开完整、固定的数据源目录、index snapshot、ranking revision、source fusion
  依据和 freshness 定义。

### 7.5 版本、失败和恢复缺口

- `FACT`：`SKILL.md` 与 release 标为 `3.1.0`，但固定
  [Python CLI](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/scripts/anysearch_cli.py)
  和 Node CLI 的 `X-Anysearch-Client` 仍为 `skill/3.0.1`。
- `FACT`：单请求 timeout 为 30 秒；客户端没有自动 retry/backoff、整体 deadline、取消、circuit
  breaker、查询去重或可恢复缓存。
- `FACT`：batch 可返回 partial failure，但成功进程状态不能单独证明所有 item 成功。
- `FACT`：文档建议在 session 中缓存 `get_sub_domains`，客户端并未实现可审计缓存。
- `INFERENCE`：RWB 未来必须分别记录 declared Skill/adapter version、observed client version、
  capability schema hash 和 backend capture gap，不能相信一个版本字符串。
- `INFERENCE`：动态 sub-domain 目录只能成为时间和 hash 绑定的 Capability Snapshot；Attempt 开始后
  不得静默漂移。

### 7.6 数据出口、凭据和提示注入

- `FACT`：即使匿名调用，query 和 extract URL 也会发送到远端服务；匿名不等于不外传。
- `FACT`：API Key 可经 CLI 参数、`.env` 或环境变量提供；`--api_key` 可能进入命令历史、进程参数
  或 Trace。
- `FACT`：`ANYSEARCH_API_BASE_URL` 可修改目的端；未经 allowlist 时可能把 query 或 Bearer Key 发往
  错误端点。
- `FACT`：Skill/Provider 宣称 zero retention/no tracking；[Provider 隐私政策](https://www.anysearch.com/legal?type=privacy)
  同时描述不含完整 query content 的 API call logs。两者不应被简化为“绝对不记录任何信息”。
- `FACT`：extract 正文有 untrusted warning，但 title/snippet 搜索输出没有同等级标记。
- `INFERENCE`：所有 title、URL、snippet、metadata 和正文都应视为不可信数据；自然语言警告不是
  enforceable security boundary。
- `PROPOSAL`：RWB 不允许 Agent 自动注册账号、自动保存 Key、使用 CLI 参数传 Key，或在缺少数据
  出口策略时调用远端搜索。
- `PROPOSAL`：首次验证只做固定版本静态审计；不调用 AnySearch API、不安装 Skill、不创建账号、
  不使用 API Key。

### 7.7 上游测试能证明什么

- `FACT`：[contract tests](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/scripts/test_cli.py)
  和 [CI](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/.github/workflows/ci.yml)
  覆盖 REST 字段转换、并发、顺序、partial failure、错误 request ID 和跨 Runtime 一致性。
- `FACT`：这些是本地 HTTP contract tests，不是 relevance、recall、source diversity、citation
  correctness 或科研 Evidence 质量 benchmark。
- `CAPTURE_GAP`：未找到上游公开、固定、可复现的 AnySearch 质量评测，不能将“significantly
  better”等 Provider 措辞升级为事实。

## 8. AnySearch 在 RWB 中的分层定性

| AnySearch 组成 | `INFERENCE`：RWB 定性 | 当前处置 |
|---|---|---|
| 托管 API | 外部 Tool Provider 候选 | `DEFER` 生产接入，仅保留研究证据 |
| 四套 CLI | Tool Adapter 参考 | `ADAPT` 其 contract discipline，不复制四套实现 |
| `get_sub_domains` | Provider Capability Report | `ADAPT` 为 hash-bound Resolved Capability Snapshot |
| general/vertical/hybrid | Research/Search Strategy 候选 | M8-003 后与 direct baseline 比较 |
| 平台探测、参数和凭据说明 | Tool Capability Card / adapter documentation | 不构成 Skill Need |
| AnySearch Skill 整体 | 外部 untrusted candidate | 不安装、不注册、不成为 accepted Skill |

关键边界：

- `FACT`：RWB 已有 provider-neutral
  [`literature-search` Tool Capability Card](../../chengyue-lu-mode-skill/TOOL_CAPABILITY_CARDS.md)；
  普通 API/MCP/CLI 调用和参数映射优先属于 Tool/adapter，而不是 Skill。
- `PROPOSAL`：已冻结 query plan 时，应允许 tool-only + no-Skill；需要设计搜索计划时，M8-003 可
  产生 `NEED-ES-SEARCH-PLAN` 候选；能力或数据边界不足时必须 blocked/Human Gate。
- `PROPOSAL`：不创建 `anysearch-search` accepted Skill，不为 no-Skill 路径伪造 Assignment。
- `CAPTURE_GAP`：是否存在非平凡、跨任务、重复的搜索策略语义缺口，只能由真实困难任务和 Trace
  证明。

## 9. Agent 搜索研究的论文证据

### 9.1 自适应搜索而非固定 fan-out

| 来源 | `FACT`：主要结论 | 限制 |
|---|---|---|
| [Sources of Evidence for Vertical Selection, SIGIR 2009](https://www.cs.cmu.edu/~jaime/ArguelloSIGIR09.pdf) | vertical selection 应结合 query、query log 和代表性 corpus，并包含“无合适 vertical” | 传统聚合搜索环境，不证明 AnySearch 动态目录质量 |
| [PaSa, ACL 2025](https://aclanthology.org/2025.acl-long.572/) | 多查询、论文阅读和引用追踪可提高复杂学术检索召回 | 领域、样本和 ground truth 有限制，不可外推通用 Web |
| [Q-DREAM, ACL 2025](https://aclanthology.org/2025.acl-long.871/) | 显式问题分解、依赖建模和动态检索有助于 multi-hop QA | 不等于固定并发 batch |
| [ChainRAG, ACL 2025](https://aclanthology.org/2025.acl-long.1089/) | 一次性分解可能丢实体；渐进检索/改写可缓解 lost-in-retrieval | 增加轮次、时延和成本 |
| [DeepDiver, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/180d4373aca26bd86bf45fc50d1a709f-Abstract-Conference.html) | 困难任务可受益于动态提高搜索强度 | over-search、输出长度和调用成本同步上升 |
| [Context Interference, ACL 2026](https://aclanthology.org/2026.acl-long.160/) | 最新检索文档可能成为主要上下文干扰源；筛选可改善可靠性与效率 | 依赖任务和额外 refiner |

综合判断：

- `FACT`：高质量论文支持 task-adaptive planning、query rewriting、停止和上下文筛选。
- `FACT`：没有直接证据支持“几乎所有非百科查询默认 vertical；不确定就固定 general+N vertical”
  作为普适规则。
- `INFERENCE`：AnySearch current heuristic 应作为实验臂，而不是 RWB 默认 Method。

### 9.2 Citation、检索污染和安全

- `FACT`：[CiteEval, ACL 2025](https://aclanthology.org/2025.acl-long.1574/) 表明引用评价不能只看
  二元 entailment，还需考虑完整上下文、可信度、冗余和缺失证据。
- `FACT`：[AgentDojo, NeurIPS 2024 Datasets & Benchmarks](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html)
  证明外部工具返回的不可信文本能形成现实 prompt-injection 测试面；它是 benchmark track，
  不是主会机制论文。
- `FACT`：[ReliabilityRAG, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/41457d56a2fdd20b4c072190290a549b-Abstract-Conference.html)
  研究检索语料污染与可靠性信号，支持对来源可信度进行独立治理。
- `INFERENCE`：搜索排名、多个 Agent 一致和高置信摘要都不能替代原始来源验证。
- `PROPOSAL`：RWB 必须把 Search Observation、Source Artifact、Evidence、Claim 和 Human Decision
  分层，并保留拒绝与反证。

## 10. 候选创新二：Method-aware Auditable Search Strategy

### 10.1 目标语义

`PROPOSAL`：未来 Search Strategy Contract 不绑定 AnySearch，至少表达：

```text
task / mode_action / method refs and hashes
search purpose / question decomposition / dependency graph
source, date, language, region and primary-source boundaries
abstain / general / vertical / hybrid alternatives and rationale
provider capability snapshot ref/hash
query, result, time, cost, context and fan-out budgets
data classification / destination / authorization / transformation
operation IDs / query hashes / provider / HTTPS endpoint
adapter, client and observed capability versions
request IDs / timestamps / raw and normalized response refs/hashes
partial / timeout / truncation / drift / capture gap
source-admission disposition / stop condition
```

### 10.2 分层数据流

`PROPOSAL`：搜索链路固定为：

```text
Research Question / Method Action
  → Search Plan
  → Resolved Capability Snapshot
  → egress authorization
  → Provider operations
  → untrusted Retrieval Observations
  → Source Inbox
  → provenance/hash/locator/license/quality admission
  → atomic Evidence
  → Claim relation and counterevidence
  → Human Decision
```

边界说明：

- Search result、snippet 和 rank 只负责发现，不负责科学接纳。
- Source Artifact 保存原文/固定字节；Context View 只加载当前任务需要的片段。
- Provider 可替换而不修改 Method contract。
- 无合适 Provider、无授权数据出口或无法取得原始全文时，应 blocked/Human Gate，不得 silent fallback。
- Runtime completed、Tool success、source selected、Evidence accepted 和 Claim satisfied 是不同状态。

## 11. 联合候选创新：Peer-assisted Scientific Retrieval

### 11.1 候选组合

`PROPOSAL`：把受控 peer exchange 与方法感知搜索结合：

1. Method Resolution 先产生 Search Plan 与来源/预算/停止约束。
2. Capability Resolution 冻结一个或多个 Provider 的能力、版本、endpoint 和数据出口策略。
3. 主 Agent 按互补 source class、subquestion 或 counterevidence obligation 派发检索任务。
4. 子 Agent 在接触同伴前先冻结独立结果。
5. Agent 之间只交换 SourceRef、hash、最小摘要、冲突和尚缺证据，不交换完整页面或权限指令。
6. 完整原文进入 Archive；按需 Context View 进入具体 verifier/selector。
7. 主 Agent 或独立 verifier 处理冲突、来源独立性和 admission，不按 Agent 多数票自动形成事实。
8. Evidence/Claim/Human Gate 与 Runtime/Team completion 保持分离。

### 11.2 为什么可能有价值

- `INFERENCE`：在 multi-hop、跨文献引用链或反证检索中，受控 peer 可以减少主 Agent 反复中转。
- `INFERENCE`：source-ref-only 通信可能在保留可追溯性的同时降低中央上下文占用。
- `INFERENCE`：不同 Provider/来源类别的独立 Agent 可能降低单一检索排名造成的系统偏差。
- `INFERENCE`：显式 conflict message 可让遗漏反证更早进入 Human/verification 路径。

### 11.3 为什么也可能失败

- `INFERENCE`：如果所有 Agent 使用同一 AnySearch 后端与同一 ranking，它们不是独立证据，反而
  会放大 source-selection bias。
- `INFERENCE`：peer exchange 可能把 poisoned snippet、错误 DOI 或 stale capability catalog 传播给
  全队。
- `INFERENCE`：过多分解和 hybrid fan-out 会增加重复来源、成本、延迟和 context interference。
- `INFERENCE`：source-ref-only 也可能过度压缩，丢掉 limitation、否定词和适用条件。
- `CAPTURE_GAP`：尚未在 RWB 真实 evidence-synthesis 案例中证明组合机制优于简单 baseline。

因此，“允许子 Agent 通信”和“接入 AnySearch”都不是创新结论；真正的候选贡献是可审计约束、
科研证据分层和经消融证明的净增量。

## 12. Memory 与 Context 的联合设计判断

### 12.1 不应建立的对象

- `REJECT`：把完整聊天记录当长期 memory 或科研真值。
- `REJECT`：全局共享 context、全局 message bus、每个 Agent 自动加载完整搜索结果。
- `REJECT`：用 vector store 相似度或 Provider rank 自动覆盖 Evidence/Claim authority。
- `REJECT`：把 peer consensus 写回 Method、Task 或权限。

### 12.2 建议的分层

`PROPOSAL`：

| 层 | 保存内容 | 进入模型上下文的规则 |
|---|---|---|
| Archive | 原始响应、网页/论文、Trace、消息、hash、版本 | 默认不整包加载 |
| Source Inbox | 未接纳候选来源和最小 provenance | selector/verifier 按需读取 |
| Research State | Evidence、Claim、Unknown、Contradiction、Decision | 是跨 Runtime 的研究语义权威 |
| Context View | 当前 Task 所需片段和摘要 | 可重建、带来源、有限预算 |
| Peer Envelope | SourceRef、hash、冲突、请求与 disposition | 一跳、最小化、不可转移权威 |
| Main Conflict Index | 尚未解决的冲突、遗漏、阻断和 Human Gate | 主 Agent 的默认团队视图 |

### 12.3 上下文污染控制

- 独立结论先于交流；保存 before/after delta。
- 原始证据不可变；摘要保留来源、版本、locator、遗漏和 confidence。
- 新检索结果先过 relevance/source admission，再进入 Context View。
- 相同 Provider、相同网页或派生摘要要做 correlation/dedup 标记。
- 超过预算时停止 fan-out、降级为 source refs 或 Human review，而不是继续压缩到语义反转。
- 所有外部文本按 data 处理，不继承工具、网络、权限或写入能力。

### 12.4 Ruflo 对 Memory admission 的补充

- `FACT`：Ruflo 的 per-Agent scope、working/episodic/semantic tier、temporal validity、`supersedes`
  以及 durable/volatile 状态，证明隔离、时效和存储诚实性可以被显式表达。
- `FACT`：其跨 Agent transfer 按类别、条数和 `minConfidence` 选择条目，但被选择只表示进入候选
  memory，不证明来源可靠或科研命题为真。
- `FACT`：CLI memory 的 namespace/`owner_id` 字段不等于调用者 ACL；省略 namespace 的搜索可以跨
  namespace，普通读取也不自动因 `expires_at` 排除内容，过期清理需要显式执行。加密落盘是 opt-in。
- `FACT`：per-Agent COW branch 是可借鉴的 opt-in seam，但依赖缺失时可降级，固定 `agent_execute`
  路径也未把该 branch 自动注入 Provider context；它尚不能证明端到端 context isolation。
- `FACT`：`LearningBridge` 会因访问提高 confidence，并可把活动 trajectory 以成功 reward 收尾；
  这形成“被多次取用 → 更高分 → 更容易再次被取用”的自强化可能性。
- `INFERENCE`：scope/tier 解决“谁能看到、保存多久”，不解决“谁有权采信”。RWB 的 memory
  confidence 不能由访问次数、Agent 自报成功或 consensus 提高；namespace 也不能代替 principal-bound ACL。
- `PROPOSAL`：只借鉴 temporal validity、`supersedes` 和 Attempt-local 隔离；长期 memory 保持为
  可从稳定文件重建的索引。promotion 必须经过 machine verification、Evidence Gate 或 Human Gate。

## 13. 采纳矩阵

### `ADOPT`

- 动态能力发现后再执行；
- bounded batch、稳定输出顺序和逐项 partial failure；
- 外部搜索内容统一标记 untrusted；
- explicit fallback 与无 silent Provider switch；
- peer 独立提交、SourceRef/hash、冲突上报和最小 context；
- transport ACK、semantic disposition 和恢复语义分离；
- temporal validity、`supersedes` 与 durable/volatile 状态诚实记录；
- 同预算 baseline 和失败结果都进入评测。

### `ADAPT`

- AnySearch `get_sub_domains` → hash-bound Resolved Capability Snapshot；
- general/vertical/hybrid → Method-aware Search Strategy 的实验候选；
- Agent Team mailbox → Attempt/Task scoped、one-hop Peer Evidence Exchange；
- complete page/result → Archive + normalized Source Inbox + on-demand Context View；
- provider request/result → data-egress、Trace 和 provenance events；
- heterogeneous Agent → 以模型、Provider、source independence 显式衡量，而非只数 Agent。
- Ruflo typed envelope/digest/cursor → Evidence/Simulation 专用消息类型，并增加 semantic disposition；
- per-Agent memory/COW seam → Attempt-local derived cache 或 Source Inbox，不成为第二科研真值库。

### `REJECT`

- 把 AnySearch 称为开源搜索算法或默认搜索引擎；
- Provider 默认决定 RWB Method；
- 固定 vertical-first、无限 hybrid、自由 Mesh 或默认 broadcast；
- 自动 Provider fallback、账号注册、Key 保存或权限放宽；
- 把 Tool Result 全量回注所有 Agent 和 transcript；
- search rank、Agent 共识、Runtime success 自动升级为 Evidence/Fact/Claim；
- dummy Skill、空 Assignment 或为了接入 Provider 创建虚假 Skill Need；
- 全局 Supervisor、长期 conversation memory、第二科研数据库或全局消息总线。
- access/popularity 自动提高 confidence、Agent 自报 success 自动 promote memory；
- consensus/vote 决定科研 Claim、noop-as-success 或“未抛异常即 delivered”。

### `DEFER`

- 生产 Search Port、TeamExecutionPort 和 native Host 集成；
- AnySearch live API spike、质量/延迟/SLA 结论；
- cache、retry、circuit breaker 和 salvage recovery 契约；
- 多 Provider 选择器、动态 Team topology 和自动 debate/critic；
- accepted Skill、正式 Schema、Registry 或 ADR 变更；
- M8-003 前的 Method→Search/Team production bridge。
- Ruflo federation、Raft/PBFT、dynamic router、AgentDB/SONA 和直接 Runtime 依赖。

### `CAPTURE_GAP`

- RWB 真实科研案例中的 peer communication 净收益；
- AnySearch 后端数据源、routing、fusion、dedup、rerank 和 ranking revision；
- Provider 隐私、保留、驻留和删除行为的独立审计；
- live catalog 漂移、实际 request ID、响应 metadata 和 source provenance；
- peer mailbox 的 durable ACK、幂等、cancel、cross-Attempt ownership；
- source-ref-only 摘要对 semantic reversal 和 limitation loss 的真实影响；
- 不同模型/Provider/语言/地域和领域中的外推稳定性。
- Ruflo 的 durable delivery、端到端 replay defense、跨 hop 预算、cross-Attempt recovery；
- Ruflo topology enforcement、per-Agent memory ACL、COW context wiring 与 canonical Trace sink；
- Ruflo 在真实 RWB evidence-synthesis/simulation 任务上的质量、成本和安全净收益。

## 14. 可证伪假设与实验设计

### 14.1 Peer communication 假设

- `H-PC-1`：跨子任务依赖明显时，bounded peer consultation 相对 Star 降低主 Agent 中转和遗漏。
- `H-PC-2`：独立提交+source-bound exchange 相对自由聊天降低 false consensus 和 semantic reversal。
- `H-PC-3`：无依赖的独立分片中，peer communication 不增加质量，反而增加成本；正确策略应 abstain。
- `H-PC-4`：同模型/同 Provider Agent 的一致不能提升 evidence independence。
- `H-PC-5`：one-hop、TTL、budget 和 conflict index 能限制消息爆炸并支持恢复。

### 14.2 Search 假设

- `H-S-1`：相同预算下，Method-aware selective routing 在专业/长尾任务上提高 primary-source
  admission yield 或 Claim coverage。
- `H-S-2`：adaptive multi-query 只在 multi-hop 等困难层改善 recall；固定 fan-out 在简单或歧义
  任务上损害 precision、context、安全或成本。
- `H-S-3`：provenance + source admission 降低 unsupported claim、错误引用和注入成功率。
- `H-S-4`：同一 Search Strategy Contract 更换 Provider 后仍可执行，AnySearch 不应成为不可替代依赖。
- `H-S-5`：固定 Capability Catalog 版本/hash 可以发现 sub-domain drift 和 replay mismatch。
- `H-S-6`：无搜索必要或无合适 vertical 时，abstain/general 优于强制 vertical。

### 14.3 联合假设

- `H-J-1`：不同 source class/Provider 的独立检索 Agent + controlled peer conflicts，比同源多 Agent
  提高 counterevidence recall。
- `H-J-2`：SourceRef-only exchange + on-demand Context View，比全文广播减少 token/context interference，
  且不显著降低 citation completeness。
- `H-J-3`：poisoned snippet 不会经 peer 消息获得更高 authority；系统能追踪并隔离传播路径。
- `H-J-4`：主 Agent 只读 conflict index 和 final handoff，仍能恢复关键决定而无需重放完整消息图。

### 14.4 Ruflo/Memory 假设

- `H-M-1`：immutable artifact refs 与 reviewer-admitted scoped summary，相对共享可变向量 memory，
  降低错误记忆扩散、陈旧事实复用和恢复歧义。
- `H-M-2`：memory access frequency 与事实有效性不具有可依赖的正相关；access-boost 会增加污染驻留时间。
- `H-RF-1`：对 declared/wired/enforced/durable/recoverable/evidence-admissible 分层做负面测试，
  能发现仅靠接口、配置字段或未抛异常无法发现的 false-success。
- `H-RF-2`：三层 receipt 相对单一 ACK 提高 crash-after-accept、stale message 和未处置冲突的可检测性。

## 15. 对照实验与指标

### 15.1 Team topology 实验臂

1. 单强 Agent；
2. 独立 scouts + deterministic aggregate/vote；
3. Star：所有 child 只与主 Agent 通信；
4. bounded chain：仅显式依赖顺序传递；
5. selective peer refs：受控一跳 SourceRef/Conflict；
6. free mesh：作为负面对照，不作为生产候选。

### 15.2 模型与 Harness 实验臂

1. 同一强模型承担 lead/worker/verifier；测量同质错误与虚假共识；
2. 强 primary + 较小 worker；测量成本、消息忠实度与主 Agent 修正距离；
3. 异质 lead/worker/verifier，使用 Latin-square 轮换角色，避免把角色优势误写成模型优势；
4. 同一权重、不同 Provider/parser；测量 tool schema、参数顺序、语言和 structured message 漂移；
5. 同一模型、不同 Harness topology；区分模型收益与通信/上下文实现收益。

所有实验先比较中文科研 Evidence/反证/Unknown、RWB Schema/Trace/Registry 代码任务、分级长上下文、
Tool 拒绝/缺参/结果回注，以及 FACT/INFERENCE/PROPOSAL/CONFLICT 与 SourceRef/hash 的语义保真。

### 15.3 Search 实验臂

1. `A0` no-search / abstain；
2. `A1` direct generic search，不加载 Skill；
3. `A2` AnySearch general；
4. `A3` 调用者预选 vertical；
5. `A4` AnySearch current vertical/hybrid heuristic；
6. `A5` RWB Method-aware adaptive routing；
7. `A6` 固定 1–5 路 batch fan-out 负面对照。

在真正 live 试验前，AnySearch 只作为设计中的实验臂，不产生性能结论。

### 15.4 Memory 与 transport 实验臂

1. `M0`：无跨会话 memory；
2. `M1`：immutable artifact refs，按需读取；
3. `M2`：带 provenance、validity 和 reviewer disposition 的 scoped summary；
4. `M3`：未经 admission 的共享向量 memory，作为污染对照；
5. `M4`：access-boost 与 Agent 自报 success 的自动学习，作为自强化负面对照；
6. `R0`：单 ACK；`R1`：IngressReceipt + SemanticDisposition + ResearchPromotionDecision。

故障注入包括 exact duplicate、同 ID 异 content、expired/out-of-order、wrong audience、queue overflow、
ACK timeout、accepted 后 crash、第二 hop 预算丢失、高访问频率错误 memory 和自报成功后的错误 promote。

### 15.5 任务分层

- 无依赖的独立分片；
- 明确跨分片依赖；
- 互相冲突的证据；
- 简单事实、时效/长尾、专业域、跨域歧义；
- multi-hop、科学论文/原始 PDF、引用链和反证；
- Provider failure、capability drift、context limit；
- malicious title/snippet、prompt injection、stale hash、重复/丢失/乱序消息；
- 未授权数据出口、越权 tool suggestion 和 summary semantic reversal。

### 15.6 冻结变量

- 相同 Task、Method、source/date/language boundary；
- 相同模型或明示异质配置；
- 相同 Provider 可见能力；
- 相同 tool、permission、data-egress 和 side-effect policy；
- 相同 query/result/time/cost/context/token budget；
- 相同 stop condition、Human Gate 和评测 rubric；
- 并发与串行使用同一 query set，避免把低 latency 误写成高 quality。

### 15.7 指标

| 维度 | 指标候选 |
|---|---|
| 检索 | Recall@k、nDCG@k、MRR、precision、重复率、primary-source ratio、freshness error |
| 科研质量 | Task contract success、Claim coverage、unsupported claim、counterevidence omission、citation precision/completeness |
| Agent 协调 | false consensus、semantic reversal、conflict resolution、重复劳动、主 Agent 中转量、Human correction distance |
| 上下文 | raw bytes、context token、summary loss、source-ref recall、compaction/reopen 次数 |
| 效率 | calls、fan-out、quota/cost、p50/p95 latency、wall time、rework、传输字节 |
| 安全 | injection success、poisoned-source adoption、unauthorized tool/egress、credential exposure |
| 审计 | request/message ID、raw/normalized hash、Trace coverage、ACK/disposition、provider/version/catalog drift |

Memory/transport 额外记录 poisoned-memory adoption、stale recall、source recovery、duplicate/replay
quarantine、最终 disposition 完整度与 crash 后 cursor 恢复率；不得只报告搜索命中或消息吞吐。

### 15.8 晋升标准

`PROPOSAL`：只有在预注册困难分层上，候选机制相对更简单 baseline 获得重复质量净增量、无安全/
治理回退、成本在预算内，并且 reviewer 可以凭文件重建关键决定，才进入独立 Task/ADR。单次成功、
Provider 宣传、Agent 多数票或 CI 通过均不构成晋升。

## 16. 与 M8、no-Skill 和未来接口的关系

- `FACT`：M8-002 继续只正式化 Mode Action；本调研不修改 Action 语义或成为前置条件。
- `PROPOSAL`：M8-003 后，Method Resolution 才可正式表达 Search Plan/Capability Requirement/Skill Need、
  Human Gate、split、blocked 与 rejected alternatives。
- `PROPOSAL`：已冻结 query plan 的普通搜索保持 tool-only + no-Skill；只有重复、非平凡的规划缺口才
  能形成 candidate Skill Need。
- `PROPOSAL`：Peer Evidence Exchange 和 Search Strategy Contract 均先作为 conformance/evaluation
  文档，不在当前研究 PR 新增公共 Schema。
- `FACT`：新 Runtime/Team/Search 不能反向修改 Method、Claim、权限或 Human Gate。
- `PROPOSAL`：M8-003 后若真实 Task 证明需要，分别建立独立 Task/ADR；不能借本 working paper 直接
  进入生产实现。

## 17. 本轮会话内已锁定的选择

以下只表示黄毅与 GPT 本轮调研的范围选择，不代表路诚钺批准或项目 SSOT 已更新：

1. `FACT`：`huangyi855` 与 `let778750-cpu` 属于黄毅同一 GitHub 账号；主名为后者。
2. `FACT`：所有调研和验证产物只存放在黄毅的 open-source-agent-harness-research 工作流中。
3. `FACT`：原始 GPT 稿和原始验证输出不作为项目真值；提交只保留来源、hash、脱敏 fixture 和结论。
4. `FACT`：受控 Agent 通信研究与 AnySearch 搜索研究合入同一个第二阶段研究 PR，但使用独立目录、
   claim ledger 和验收 Gate。
5. `FACT`：AnySearch 首次仅做固定版本静态审计，不调用 API、不注册账号、不使用 API Key。
6. `FACT`：本研究不修改 TASKS、ADR、稳定 Schema、Registry、Runtime 或 M8 顺序，不阻断 M8。
7. `FACT`：Peer communication 与 AnySearch 都只能称候选创新/研究假设，未经消融不得宣称成立。
8. `FACT`：黄毅随后明确授权将本文件更新、提交并推送到
   `codex/open-source-agent-harness-research` 对应的 `develop` 研究 PR；提交 Working Paper 不表示
   路诚钺已经批准其中的 Proposal，也不改变 TASKS/ADR/Stable Architecture。
9. `FACT`：Ruflo 首轮仅对固定提交执行静态源码、测试与文档审计；未安装 npm 包、未调用模型、
   未运行 federation 或性能 benchmark。本地上游副本只作为被忽略的原始核验材料，不进入提交。

## 18. 仍待确认与后续停止条件

### 18.1 需要双方维护者决定

- 是否接受本研究问题进入正式 Evaluation Task；
- peer communication 是否需要新的 envelope/Trace 事件，还是可复用既有 Handoff/Trace；
- Search Plan、Capability Snapshot 与 Retrieval Observation 的正式对象边界；
- 数据出口 enforcement、Provider allowlist、secret source 和 retention vocabulary；
- live search、真实科研案例及人工 relevance/citation 标注的授权范围；
- 哪些结果可以形成 Tool Card delta，哪些构成真正 Skill Need。

### 18.2 立即停止条件

- 需要 API Key、真实邮箱、账号注册或保存凭据；
- 需要发送私密、未发布或未获授权的 query/URL；
- 外部 Runtime/Provider 试图隐式激活 Agent、Skill、Tool 或 fallback；
- 需要修改 TASKS/ADR/Stable docs 才能把研究结论写成事实；
- 无法固定源码版本、许可证、endpoint、能力 Schema 或输出路径；
- 原始 Tool Result、搜索正文或 peer 消息将未经 admission 直接升级为 Evidence/Claim；
- 评测不能冻结预算或不能区分通信收益、模型收益和 Provider 收益。
- 需要把 Ruflo、其 federation/AgentDB/SONA 或移动版本引用直接接入 Runtime 才能继续论证。

## 19. 来源导航

### 19.1 RWB 内部来源

以下六项由独立的 PR #28 工作流交付。为使本 GPT/黄毅调研 PR 直接基于 `develop`、不继承
GLM 分支历史，这里固定引用 PR #28 的 clean head `39a5c78`；这些链接只提供关联研究背景，
不表示其内容属于本 PR 的 diff 或已进入 `develop`。

- [父工作流 README](https://github.com/Chengyue-Lu/research-agent-workbench/blob/39a5c78a0c1d5b00c89cc6e1971de5f233e0b8b4/docs/workstreams/huangyi/open-source-agent-harness-research/README.md)
- [来源清单](https://github.com/Chengyue-Lu/research-agent-workbench/blob/39a5c78a0c1d5b00c89cc6e1971de5f233e0b8b4/docs/workstreams/huangyi/open-source-agent-harness-research/SOURCE_MANIFEST.md)
- [主张台账](https://github.com/Chengyue-Lu/research-agent-workbench/blob/39a5c78a0c1d5b00c89cc6e1971de5f233e0b8b4/docs/workstreams/huangyi/open-source-agent-harness-research/CLAIM_LEDGER.md)
- [采纳矩阵](https://github.com/Chengyue-Lu/research-agent-workbench/blob/39a5c78a0c1d5b00c89cc6e1971de5f233e0b8b4/docs/workstreams/huangyi/open-source-agent-harness-research/ADOPTION_MATRIX.md)
- [Conformance 计划](https://github.com/Chengyue-Lu/research-agent-workbench/blob/39a5c78a0c1d5b00c89cc6e1971de5f233e0b8b4/docs/workstreams/huangyi/open-source-agent-harness-research/CONFORMANCE_PLAN.md)
- [综合分析](https://github.com/Chengyue-Lu/research-agent-workbench/blob/39a5c78a0c1d5b00c89cc6e1971de5f233e0b8b4/docs/workstreams/huangyi/open-source-agent-harness-research/SYNTHESIS.md)
- [项目章程](../../../PROJECT_CHARTER.md)
- [架构](../../../ARCHITECTURE.md)
- [路线图](../../../ROADMAP.md)
- [任务真值](../../../TASKS.md)
- [ADR-0013：Mode-derived Skill Need](../../../decisions/0013-MODE-FIRST-SKILL-DERIVATION.md)
- [ADR-0016：Method-aware Research Control Plane](../../../decisions/0016-METHOD-AWARE-RESEARCH-CONTROL-PLANE.md)

### 19.2 Harness 与 Agent Team 来源

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/tree/b150a551b8d465e31e418e1b2eaf5e79bbb7d28e)
- [Codex](https://github.com/openai/codex/tree/343074d4207d572809bd8cea15f4be1d09d98e0b)
- [OpenCode](https://github.com/anomalyco/opencode/tree/3a31c4ea801915c0b050df4b3842997ea62b6e93)
- [Pi](https://github.com/earendil-works/pi/tree/c49906ec77788625aacbdc53ebca6fbe65bd20f5)
- [Cline](https://github.com/cline/cline/tree/1de61b178aec844e0aa362474274ccbf6acf9403)
- [AutoGen communication](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/message-and-communication.html)
- [AgentScope](https://github.com/agentscope-ai/agentscope/tree/da00849f2c3db60b16edaf2371ae1d863f341ae2)
- [LangGraph](https://github.com/langchain-ai/langgraph/tree/f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f)
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f)
- [CrewAI](https://github.com/crewAIInc/crewAI/tree/f4731f5025f861c78e3af0487cc80bf5e7c64782)
- [Ruflo 固定提交](https://github.com/ruvnet/ruflo/tree/3c99b1c84a25948c42a163253bac6effed5fbbbb)
- [Ruflo MIT License](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/LICENSE)
- [Ruflo Codex Harness contract](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/codex/src/harness/contract.ts#L96-L112)
  与 [reference inbox](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/codex/src/harness/in-memory-inbox-reference.ts#L42-L151)
- [Ruflo Swarm MessageBus](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/message-bus.ts)
  与 [Consensus Transport](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/consensus/transport.ts)
- [Ruflo Swarm host-tool boundary](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/plugins/ruflo-swarm/README.md)
  与 [Unified Coordinator](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/swarm/src/unified-coordinator.ts)
- [Ruflo Federation plugin](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/plugin-agent-federation/src/plugin.ts)
  与 [Coordinator](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/plugin-agent-federation/src/application/federation-coordinator.ts)
- [Ruflo Agent Memory Scope](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/memory/src/agent-memory-scope.ts)
  与 [Tiered Memory](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/memory/src/tiered-memory.ts)
- [Ruflo Agent Tools](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/cli/src/mcp-tools/agent-tools.ts)、
  [Session Tools](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/cli/src/mcp-tools/session-tools.ts)
  与 [Authorization Propagator](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/security/src/authorization/propagator.ts)
- [Ruflo `claims` 包](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/v3/%40claude-flow/claims/src/index.ts)
- [Ruflo mock multi-agent benchmark](https://github.com/ruvnet/ruflo/blob/3c99b1c84a25948c42a163253bac6effed5fbbbb/docs/benchmarks/multi-agent/multiagent-mock-2026-06-22T17-02-43-846Z.json#L1-L98)

### 19.3 开放权重模型与排行榜来源

- [Open Agent Leaderboard](https://huggingface.co/blog/ibm-research/open-agent-leaderboard)
- [BFCL V4](https://gorilla.cs.berkeley.edu/leaderboard)
- [DeepSeek V4 Pro `b5968e9190ef611bbf34a7229255be88a0e937c1`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/tree/b5968e9190ef611bbf34a7229255be88a0e937c1)
  与 [Flash `60d8d70770c6776ff598c94bb586a859a38244f1`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/tree/60d8d70770c6776ff598c94bb586a859a38244f1)
- [Qwen3.8 2.4T `207bd685a7e3696cfaff12ded7c6a7ea0f88c996`](https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B/tree/207bd685a7e3696cfaff12ded7c6a7ea0f88c996)
  与 [27B `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`](https://huggingface.co/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0)
- [Kimi K3 `a590ce090cb049c93a33dfe8c208ec652aa20503`](https://github.com/MoonshotAI/Kimi-K3/blob/a590ce090cb049c93a33dfe8c208ec652aa20503/README.md)
- [GLM-5.2 `b4734de4facf877f85769a911abafc5283eab3d9`](https://huggingface.co/zai-org/GLM-5.2/tree/b4734de4facf877f85769a911abafc5283eab3d9)
- [MiniMax M3 `f0e1c1e04d40177e4673a22097036854f536e9c0`](https://huggingface.co/MiniMaxAI/MiniMax-M3/tree/f0e1c1e04d40177e4673a22097036854f536e9c0)
- [Llama 4 model card `73d14711bcc77c16df3470856949c3764056b617`](https://github.com/meta-llama/llama-models/blob/73d14711bcc77c16df3470856949c3764056b617/models/llama4/MODEL_CARD.md)
- [gpt-oss-120b `b5c939de8f754692c1647ca79fbf85e8c1e70f8a`](https://huggingface.co/openai/gpt-oss-120b/tree/b5c939de8f754692c1647ca79fbf85e8c1e70f8a)

### 19.4 AnySearch 来源

- [v3.1.0 release](https://github.com/anysearch-ai/anysearch-skill/releases/tag/v3.1.0)
- [固定 commit](https://github.com/anysearch-ai/anysearch-skill/tree/4d6cef918e9338c9deef43b81ac0f7e22606825f)
- [SKILL.md](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/SKILL.md)
- [Python CLI](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/scripts/anysearch_cli.py)
- [Contract tests](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/scripts/test_cli.py)
- [CI](https://github.com/anysearch-ai/anysearch-skill/blob/4d6cef918e9338c9deef43b81ac0f7e22606825f/.github/workflows/ci.yml)
- [Provider API 文档](https://www.anysearch.com/docs)
- [Provider 隐私政策](https://www.anysearch.com/legal?type=privacy)

### 19.5 学术核心来源

- [CCF 人工智能目录](https://www.ccf.org.cn/Academic_Evaluation/AI/)
- [Beyond Frameworks, ACL 2025](https://aclanthology.org/2025.acl-long.1037/)
- [Chain of Agents, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/ee71a4b14ec26710b39ee6be113d7750-Abstract-Conference.html)
- [Multiagent Debate, ICML 2024](https://proceedings.mlr.press/v235/du24e.html)
- [Should we be going MAD?, ICML 2024](https://proceedings.mlr.press/v235/smit24a.html)
- [Multi-LLM Debate, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/32e07a110c6c6acf1afbf2bf82b614ad-Abstract-Conference.html)
- [Debate or Vote, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/934252acd87f254d5d4672fbde283bd2-Abstract-Conference.html)
- [ReConcile, ACL 2024](https://aclanthology.org/2024.acl-long.381/)
- [GPTSwarm, ICML 2024](https://proceedings.mlr.press/v235/zhuge24a.html)
- [AgentDropout, ACL 2025](https://aclanthology.org/2025.acl-long.1170/)
- [GUARDIAN, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/0bc795afae289ed465a65a3b4b1f4eb7-Abstract-Conference.html)
- [Dynamic Communication Topologies, ACL 2026](https://aclanthology.org/2026.acl-long.1764/)
- [SILO-BENCH, ACL 2026](https://aclanthology.org/2026.acl-long.1354/)
- [Conjunctive Prompt Attacks, ACL 2026](https://aclanthology.org/2026.acl-long.1577/)
- [DIAL/RIAL, NeurIPS 2016](https://proceedings.neurips.cc/paper/2016/hash/c7635bfd99248a2cdef8249ef7bfbef4-Abstract.html)
- [CommNet, NeurIPS 2016](https://proceedings.neurips.cc/paper/2016/hash/55b1927fdafef39c48e5b73b5d61ea60-Abstract.html)
- [TarMAC, ICML 2019](https://proceedings.mlr.press/v97/das19a.html)
- [PaSa, ACL 2025](https://aclanthology.org/2025.acl-long.572/)
- [Q-DREAM, ACL 2025](https://aclanthology.org/2025.acl-long.871/)
- [ChainRAG, ACL 2025](https://aclanthology.org/2025.acl-long.1089/)
- [DeepDiver, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/180d4373aca26bd86bf45fc50d1a709f-Abstract-Conference.html)
- [Context Interference, ACL 2026](https://aclanthology.org/2026.acl-long.160/)
- [CiteEval, ACL 2025](https://aclanthology.org/2025.acl-long.1574/)
- [ReliabilityRAG, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/41457d56a2fdd20b4c072190290a549b-Abstract-Conference.html)

## 20. 最终综合判断

1. `FACT`：Agent Team 既有 Star 也有 peer/broadcast；“子 Agent 普遍不能互相通信”是过度概括。
2. `FACT`：论文对多 Agent 通信给出互相制衡的正反证据；交流不是稳定增益来源。
3. `FACT`：在已核验的开放权重模型卡/API 中，未发现模型级 Agent-Team transport；Harness/Runtime
   才拥有 identity、addressing、delivery、wake、ACK/recovery 和权限语义。
4. `PROPOSAL`：RWB 值得研究中央治理、稀疏一跳、证据绑定、可恢复的 peer consultation；“允许
   sibling 发消息”与“动态拓扑”已有公开先行工作，不能单独作为创新主张。
5. `FACT`：Ruflo 进一步证明 typed envelope、TTL、ACK、digest、cursor、幂等、per-Agent memory、
   federation 与 consensus 均已有先行实现；但其固定提交也存在 non-durable reference、noop-success、
   预算未贯穿 envelope、默认 legacy 授权和 memory 自强化等实现边界。
6. `PROPOSAL`：RWB 的差异化候选不是另一个通用 MessageBus，而是 Method-derived、证据绑定、
   先独立后通信、三层 receipt、可拒绝且可恢复的稀疏 Peer Evidence Exchange。
7. `FACT`：AnySearch 开源的是调用/路由工作流和 CLI，不是搜索后端算法；其质量和隐私仍有
   capture gaps。
8. `PROPOSAL`：可借鉴 capability discovery、bounded batch、partial failure、untrusted-data 和
   explicit fallback，但必须由 Method、预算、数据出口和 Evidence Gate 重新约束。
9. `PROPOSAL`：通信、记忆和搜索三条研究线组合后的候选贡献，是方法感知、Provider 可替换、
   memory-admission-aware、Evidence-bound、
   peer-assisted 且可审计的科研检索协议。
10. `CAPTURE_GAP`：在真实任务、同预算消融和对抗测试完成前，它只能是 GPT 与黄毅联合调研形成的
   working hypothesis，不能宣称为项目已接受创新。

---

编制说明：本文依据本轮 GPT 与黄毅的联合调研会话、固定上游源码、项目现有工作流材料和列出的
论文来源整理。本文不保存原始聊天正文，不包含隐藏推理，不替代具名人类审查与正式项目决策。
