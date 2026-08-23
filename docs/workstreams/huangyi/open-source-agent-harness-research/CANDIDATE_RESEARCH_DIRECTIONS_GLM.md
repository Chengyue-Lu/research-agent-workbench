# 候选研究方向调研笔记：Agent 间通信与证据级检索

> 整理：**GLM 建**（GLM 与黄毅的联合调研会话，2026-08-23）
>
> 状态：Working paper；**GLM 辅助调研笔记，不是 Stable Architecture、ADR、TASKS 验收或
> Runtime 实施授权**。本文档不改任何任务状态，不解除 Architecture Hold。
>
> - 责任人：黄毅（GitHub 主名 `let778750-cpu`，昵称 `huangyi855`）
> - 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
> - 归属 workstream：[RESEARCH-HARNESS-001](README.md)
> - 证据截止：2026-08-23（外部检索与仓库核查均于当日完成）
> - 纪律声明：遵循 PR #25 治理基线与[本 workstream 隐私边界](README.md)——本文只保存
>   最小脱敏结论，不粘贴私有对话原文，不写机器绝对路径。

## 0. 背景与会话脉络

本笔记沉淀一次联合调研会话的完整产出。会话从项目治理现状出发，最终收敛出两个候选研究
方向。脉络如下（均为会话内已核实内容，详见各节）：

1. **项目治理分析**：8-22 会议纪要、`docs/TASKS.md`、PR #20/#23/#24 的交叉核对；确认
   PR #23 hard-block 的实质是共享真值被实现分支改写，主线为 M8-002 → M8-003。
2. **4/5 部分 Architecture Hold**：执行恢复风险审计（外部 LLM 会话整理稿，已在
   [execution-runtime-recovery-audit](../execution-runtime-recovery-audit/README.md)
   workstream 落地）提出 I1–I12 边界不变量与恢复 Gate。
3. **治理落地核查**：确认 develop 治理基线（PR #25）、PR #24 与 #23 解耦、
   RESEARCH-HARNESS-001 调研分支及其 Codex 只读验证均已成立。
4. **三个候选研究方向**（本文主体）：
   - 议题一：子 Agent 互联（peer communication）的外部核查与 RWB 定位；
   - 议题二：anysearch-skill 的解剖与「证据级检索」提案；
   - 议题三：Agent 间通信机制的分类学核查、RWB 需求映射与应用范围界定。

**与主线的从属关系**：`docs/TASKS.md` 的全局唯一下一任务仍是 M8-002；两提案均为
M8-003 之后的候选研究问题，本笔记仅登记，不启动实现。

结论类型标注沿用本 workstream 惯例：`FACT`（外部或仓库可核验）、`INFERENCE`（基于事实
的推断）、`PROPOSAL`（候选提案，待共同裁定）、`CAPTURE_GAP`（已知未知）。

---

## 1. 议题一：子 Agent 互联（peer communication）

### 1.1 起始假设与核查结论

**假设**（会话提出）：高质量开源 harness/agent 工具的 agent team 模式是主 agent 派发
结构化任务给子 agent，子 agent 完成验证后反馈结果给主 agent；子 agent 之间不存在联系。

**核查结论（INFERENCE）**：在本次列出的 production-facing coding harness 样本中，该假设大体
成立；研究框架与协议样本则包含 peer、群聊、handoff 和共享状态等其他拓扑。该有限样本不能代表
整个生产生态。

#### 本次 production-facing harness 样本：星型 orchestrator-worker 较常见（FACT + INFERENCE）

| 系统 | 拓扑 | 子 agent 间直接联系 | 依据 |
|---|---|---|---|
| Claude Code subagents | 主 agent 派发 → 隔离上下文执行 → 回传主会话 | 否 | [官方文档](https://code.claude.com/docs/en/sub-agents) |
| OpenAI Codex（CLI/云 agent teams） | Task 工具派发 | 否 | 本 workstream [SYNTHESIS.md](SYNTHESIS.md) |
| DeepSeek Harness | 父子 subagent，消息仅 depth-1 父↔子；深层次经父转发；另有 durable mailbox | 否（靠共享工作区文件间接传递） | 运行时一手观察 |
| Cline（squad） | 主 agent + 只读 subagent | 否 | 本 workstream SYNTHESIS.md |
| Anthropic 多 agent 研究系统 | lead 并行派 3–5 个 subagent | 半例外：不直接对话，但写入**共享 markdown 记忆文件**供 lead 读取（经共享工件的间接可见性） | [Anthropic 工程博客](https://www.anthropic.com/engineering/multi-agent-research-system) |

这些公开材料中支持星型设计的工程理由包括：上下文隔离与预算可控；权限边界清晰；
确定性与可调试性；成本（Anthropic 实测多 agent 消耗约 **15 倍** token，编排模型选择贡献
大部分性能方差）；以及 [Cognition《Don't Build Multi-Agents》](https://cognition.ai/blog/dont-build-multi-agents)
两条原则——上下文要共享、动作携带隐含决策。

#### 研究框架：peer 机制早已存在且被系统研究（FACT）

| 框架/协议 | peer 机制 | 出处 |
|---|---|---|
| AutoGen GroupChat | 群聊广播，Manager 选发言人，全员可见 | [AutoGen 0.2 文档](https://microsoft.github.io/autogen/0.2/docs/tutorial/conversation-patterns/) |
| Magentic-One | 双账本编排；**专门 Executor agent 运行并验证 Coder 的代码**（受编排的 agent 间验证） | [arXiv 2411.04468](https://ar5iv.labs.arxiv.org/html/2411.04468v1) |
| LangGraph | supervisor / **network（任意互发）** / hierarchical 三拓扑 | [教程](https://www.kinde.com/learn/ai-for-software-engineering/ai-agents/hierarchical-agent-teams-with-langgraphsupervisor/) |
| MetaGPT | SOP 流水线 + **发布/订阅消息池**（交换结构化文档而非自由聊天） | [ICLR 2024 Oral](https://m.thepaper.cn/newsDetail_forward_26261080) |
| CAMEL | 双 agent 角色扮演直接对话 | [NeurIPS 2023](https://dev.neurips.cc/virtual/2023/poster/72905) |
| OpenAI Agents SDK | **handoffs**：agent 间直接移交控制权 | [官方文档](https://github.com/openai/openai-agents-python/blob/cdde4d65/docs/handoffs.md) |
| AWS Bedrock 多 agent | 显式 `SUPERVISOR / PEER / COLLABORATOR` 等模式 | [AWS 文档](https://pypi.org/project/aws-cdk.aws-bedrock-alpha/2.260.0a0/) |
| A2A 协议 | Google 捐赠 Linux 基金会的跨厂商 agent 间通信标准 | [公告](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents) |

**推论（INFERENCE）**：「让子 agent 互相联系」本身不构成创新点——已撞上被充分研究的
领域；RWB 的机会在于给这个领域补上它缺的治理维度（见 1.4）。

### 1.2 上下文与幻觉风险的文献证据（FACT，均经检索核实）

1. **消息洪水与冗余**：[Cut the Crap（ICLR 2025）](https://mlanthology.org/iclr/2025/zhang2025iclr-cut/)
   实测多 agent 通信管道存在大量冗余 token，剪除后成本大降性能不降；
   [GPTSwarm（ICML 2024 Oral）](https://icml.cc/virtual/2024/oral/35447)学习到的最优
   拓扑常常稀疏——并非连得越多越好。
2. **长上下文稀释**：[Lost in the Middle（TACL 2023）](https://arxiv.org/abs/2307.03172)
   ——peer 消息灌入子 agent 上下文直接稀释核心任务注意力；Anthropic 的对策是 compaction
   与结构化笔记（[context engineering](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)）而非广播。
3. **摘要压缩=未声明语义变换**：星型的信息损失发生在综合点（subagent→lead 的压缩），
   mesh 的损失发生在传输中——两种拓扑都逃不掉，只是位置不同。
4. **错误/幻觉传播**：[MAST: Why Do Multi-Agent LLM Systems Fail?（NeurIPS 2025）](https://mlanthology.org/neurips/2025/cemri2025neurips-multiagent/) 将
   **inter-agent misalignment 与 error propagation** 列为核心失败类别——协作本身引入的
   失败大于单 agent 错误；[Hallucination Cascade](https://arxiv.org/html/2606.07937v1)
   与 IEEE [幻觉滚雪球缓解](https://ieeexplore.ieee.org/document/11366934)直接研究
   一个 agent 的幻觉成为下一个 agent 输入事实的级联放大；
   [Chain of Agents（Google，NeurIPS 2024）](https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/)
   显示顺序链式传话信息逐段退化。
5. **Debate 是双刃剑**：[Multiagent Debate（ICML 2023）](https://www.semanticscholar.org/paper/4780d0a027c5c5a8e01d7cf697f6296880ffc945)
   证明辩论能纠错提分；[ChatEval（ICLR 2024）](https://researchportal.hkust.edu.hk/en/publications/chateval-towards-better-llm-based-evaluators-through-multi-agent-deb)
   发现通信拓扑设计决定成败；[ReConcile（ACL 2024）](https://aclanthology.org/2024.acl-long.381/)
   表明异构模型圆桌优于同构（回音室）；Exchange-of-Thought（EMNLP 2023）要求置信度
   加权以抑制「自信的错误少数派说服正确多数派」。
6. **拓扑效果任务依赖**：[Multi-Agent Design（Google）](https://research.google/pubs/multi-agent-design-optimizing-agents-with-better-prompts-and-topologies/)
   无普适最优拓扑；[DyLAN](https://arxiv.org/abs/2310.02170) 最优团队随任务漂移；
   [More Agents Is All You Need（TMLR）](https://arxiv.org/abs/2402.05120)提示部分
   「多 agent 收益」只是采样+投票的测试时计算收益。

**小结（INFERENCE）**：自由聊天式互联会增加冗余、稀释和错误传播风险；结构化、受验证、带
置信度与证据绑定的有限互联可能在特定任务下降低这些风险。是否产生净收益仍需同任务对照。

### 1.3 RWB 现状映射（INFERENCE，基于仓库事实）

**RWB 已有「三套弱 peer 链接」（pull 式），比 Anthropic 共享记忆文件更严格：**

| 已有机制 | 仓库依据 | 提供的 peer 能力 |
|---|---|---|
| Attempt Archive + 受控读取 | ADR-0011 §2、ADR-0012 | 子 agent 可按 ID 回放其他 agent 的归档消息与工件（记录原因 → owner 扩大读取集 → 补录来源），**读别人的工作不需要聊天** |
| 引用完整性 | M1-005（REF-HASH-MISMATCH、revision、stale） | 任何跨 agent 引用哈希钉定，peer 引用漂移被机器拦截 |
| H1/H2 Handoff 分级 + 语义抽样 | ADR-0011 §1；HANDOFF-LOSSY / CTX-SUMMARY-DISTORTION 等风险码 | 跨上下文传递已有风险分级、负面区段检查、摘要失真人工抽样 |

准确表述：**RWB 只有拉（pull），没有推（push）**。缺两个东西：① 子 agent 向 peer 发起
请求/澄清的合法语音行为（question speech act）；② 不经 coordinator 的寻址式交付
（addressed peer handoff）。

**星型不是缺陷而是权威结构**：谁有权决定「agent B 现在需要 agent A 的结果」？现行答案
唯一——coordinator 派发（Assignment）+ Method Resolution（ADR-0016 §3）。允许子 agent
自行建通信信道 = 未经 Resolution 的隐式 binding，直接冲突于 I2（frozen binding 不得
静默替换）与 I3（未声明参与者不得参与）——[RECOVERY_GATE_PROPOSAL]
(../execution-runtime-recovery-audit/RECOVERY_GATE_PROPOSAL.md) 中挡住外部框架
auto-routing 的不变量，同样适用于我们自己想加的 peer 通道。

### 1.4 候选提案：Communication as Evidence（PROPOSAL）

**候选空白（INFERENCE）**：本次有限检索尚未发现同时提供「证据级、可审计、带预算与人类门控」
通信契约的框架；已观察系统只覆盖其中部分维度。该判断不是穷尽性新颖性检索，需要后续系统综述
和逐实现核查。

**提案要点**：每条 inter-agent 消息是 hash 钉定的 evidence-grade artifact——

- `message_type` 白名单枚举（evidence-claim / question / refutation / status），禁自由聊天；
- source/target `actor_id`；claim 必须挂冻结输入哈希（无引用不得生成新 claim）；
- 置信度声明；AWU 预算记账；redaction 分级；同级进入 Attempt Archive；
- H2 语义抽样人审适用于 peer 消息提升为关键 Evidence/Claim 的场合。

**候选风险码（PROPOSAL，须走 PR #25 共同裁定通道，不得单方登记）**：
`INTER-AGENT-UNVERIFIED`、`COMMS-CASCADE-SUSPECT`、`ECHO-CONSENSUS-NO-EVIDENCE`。
文献风险 → 机制映射：级联→cascade 检测；回音室→交换前先独立作答+异构性要求；
冗余→消息类型白名单+预算；失真→抽样人审。

**验收语言**：不用「效率/性能」，用既有指标——遗漏率、返工率、回查率、级联率、
H2 抽样失真率（复用 M5-003 单 Agent/轻量/多 Agent 对照与 M7-014 框架）。
**meta 定位（PROPOSAL）**：RWB 的 Trace/Attempt/Receipt 可作为测量「互联 vs 隔离对研究质量
影响」的候选仪器；“peer 直连何时值得”是可检验研究问题。其新颖性、测量有效性和发表价值均
尚未建立。

### 1.5 纪律与前提（PROPOSAL 的执行边界）

- Architecture Hold 期间零代码；仅登记候选研究问题（本笔记即是）。
- M8-003 冻结路由权威后，peer handoff 寻址语义（链路建立由 Resolution 输出或 Human Gate
  批准）才有定义锚点——对应 4/5 审计 Gate A。
- 实现排入恢复顺序 Phase 6（先证明单 Agent/单 Attempt/单 Runtime 闭环，再多 Agent）。
- 所有权：peer 通信语义归 Method Plane（路诚钺），数据出口判定归 M6/I4（黄毅）——
  **必须共写 ADR**，不能单方推进。
- peer 消息跨 agent 上下文传递时触发 I4 DATA-EGRESS 判定（source/classification/
  destination/authorization/redaction）。

---

## 2. 议题二：anysearch-skill 与证据级检索

### 2.1 项目定性（FACT，经仓库逐文件核查）

[anysearch-ai/anysearch-skill@4d6cef9](https://github.com/anysearch-ai/anysearch-skill/tree/4d6cef918e9338c9deef43b81ac0f7e22606825f)（2026-04
创建，5.9k stars / 353 forks，Apache-2.0 仅覆盖客户端代码，168KB）**不是学术意义上的
agent 搜索机制研究**——仓库无 benchmark/eval/实验文档，只有 CLI 测试与代码生成器。真实
身份：面向 Claude Code/OpenCode/Cursor/OpenClaw 生态的生产级搜索 skill，商业 API
（api.anysearch.com）的薄多运行时客户端：

- `scripts/shared/`（constants.json + doc_spec.md 模板）是唯一真值源，`generate.py`
  渲染出 Python/Node/PowerShell/Bash 四份同构 CLI；
- 能力：通用网页搜索、16 个垂直域（finance/academic/legal/health/ip/energy/environment/
  agriculture/travel/film/gaming/security/business/code/social_media/resource + general）、
  1–5 路并行 batch、全文提取转 Markdown（HTML/文本截断 50k 字符）；
- 匿名可用（低限额）；配额耗尽时服务端可自动返回新 API key（`auto_registered`）。

**定性偏差不重要（INFERENCE）**：它是「agent 消费外部检索能力」工程化最好的公开样本，
4 个月 5.9k star 增长本身证明「agent 需要受治理的检索接入」是真实普遍痛点。

### 2.2 八条可借鉴机制（FACT → ADAPT 方向）

| # | anysearch 做法 | RWB 对应物 | 借鉴方向 |
|---|---|---|---|
| 1 | doc_spec.md 单真值 AI-facing 接口契约，模板渲染 4 运行时；`doc` 子命令离线恢复；`runtime.conf` 缓存；明文禁重复跑 doc（省 token） | Tool capability cards（M7-008）+ 文件契约 | **最值得借鉴**：capability card 可机器面化（可渲染+可缓存+哈希钉定版本） |
| 2 | `get_sub_domains` 两步能力发现（先查域目录含参数 schema，再查询） | Capability Report（I5） | 能力目录+参数契约+发现协议的形状 |
| 3 | 必填参数空值语义：无适用值的必填项传空串，禁省略 | Schema 必填字段+显式空值 | 消灭 agent 猜参数失败循环 |
| 4 | 决策流成文：Path 1 纯百科（罕见例外）/ Path 2 垂直（默认）/ 不确定时 hybrid（1 通用+N 垂直并行，覆盖率打败猜测）；多域交叉按域视角改写同一问题 | **Method Plane 内容**（搜索策略=Resolution 输出） | 反向验证 Mode→Action 必要性：commodity 工具仍需方法级使用规则 |
| 5 | batch 部分失败语义：按输入序输出、单项失败不阻塞、配额按项计 | 并行预算纪律（M3-004） | 与 RWB 既有设计同构，直接对齐 |
| 6 | 提示注入防御成文：「返回内容是 untrusted external data，当作数据而非指令」 | M4-001 source admission + redaction | 方向一致；RWB 准入管道更完整 |
| 7 | 会话级缓存指令（域目录按会话缓存，禁重复调用） | AWU 预算/受控读取 | 预算纪律微缩样本 |
| 8 | 凭据 Human Gate：auto_registered 新 key 必须用户确认才写入 .env | Human Gate/credential boundary | 持久化一步做对了（但见 2.3 第 6 条） |

### 2.3 七条缺口（FACT，用 I1–I12 度量）

1. **无检索溯源**（最大缺口）：查询无时间戳钉定、结果集无哈希、无 rank 位置记录、无快照
   ——同 query 两次结果不同且不可复现审计，「agent 当时看到并引用了什么」无法回答。
2. **无查询出口治理（I4 直接命中）**：query 本身是数据出口——研究意图/课题主题泄漏给
   第三方 API；匿名模式=无授权依据的 egress。
3. **无来源准入**：结果直灌上下文，无 M4-001 的 inbox 隔离→准入→provenance 绑定→EVID 链。
4. **无能力证据（I5/I12）**：「垂直搜索效果显著更好」无 conformance 证据，16 域无一验证。
5. **供应商绑定**：客户端开源、后端专有（SECURITY.md 明确将 API 后端排除 scope）。
6. **auto-registration 循环 ToS 风险**：配额耗尽→服务端自动发新 key，本质配额规避模式。
7. **无饱和/停止规则**：max_results 1–10，但无「何时停止搜索」的方法（预算、边际新颖度）。

### 2.4 候选提案：Evidence-grade Retrieval（PROPOSAL）

对 RWB 而言不是「接入一个搜索工具」，而是补上 commodity 搜索 API ↔ Evidence Plane 之间
缺失的治理层。四个待验证构件：

1. **Retrieval Manifest**：每次搜索产出哈希钉定工件——精确请求（query/params/endpoint/
   zone/language）、时间戳、响应全文哈希、逐结果（URL+标题+摘要）哈希与 rank 位——
   检索可审计回放。把 INDEX.yaml 文化延伸到检索环；本次样本未证明该组合具有新颖性。
2. **Query Egress Policy**：I4 用于出站查询——研究问题敏感度分级、目标服务白名单、
   查询最小化/改写脱敏。本次样本对查询侧 egress 治理覆盖不足，但不能据此断言业界空白。
3. **Source Admission Gate**：M4-001 具体化——域注册表、可信度分级、准入 Decision 带
   provenance，准入后才可产生 EVID。
4. **搜索策略入 Method Plane**：把 Path1/2/hybrid 决策流升格为 evidence-synthesis Mode
   的「evidence acquisition」action：机制选项（通用/垂直/人工供源）、失败模式（零结果/
   冲突/付费墙）、工件（带 manifest 的 source batch）、停止条件（预算+饱和度）、Gate
   （准入审查）——**M8-002 Mode Action contract 的天然真实用例**。

**与议题一的闭环（INFERENCE）**：检索 fan-out（多 evidence-scout 并行搜索）恰是不需要
agent 间消息通道的协作场景——协调媒介是 source batch 工件（哈希+准入状态），汇合点在
Source Admission 而非会话。再次印证 file-first 哲学。

### 2.5 落地路径与反方观点（PROPOSAL）

**路径**（严格沿治理，不越 Hold、不偏主线）：

1. 现在（零代码）：按 M7-009 管道登记 anysearch 为外部候选——快照哈希、许可记录
   （Apache-2.0 客户端/专有后端，服务依赖风险写入 dossier）、人工 Decision（不安装、
   不执行）；本节可作 dossier 底稿。同时起草 search-web Tool capability card（M7-008
   八字段：数据出口/权限/副作用/预算/失败/验证/fallback/owner）。
2. 契约窗口：M4-001（READY）开工时把 Source Admission + Retrieval Manifest 纳入验收；
   I4 从 proposal→accepted 裁定时纳入 Query Egress Policy（共同裁定通道）。
3. 实现窗口：M8-003 冻结后，evidence acquisition 作为 Mode action 推导 Skill Need；
   真实搜索 Adapter（anysearch 一号候选，另配 arXiv/Crossref/通用引擎做 provider-neutral
   对照）等 Method Resolution + I4 就绪再接。检索线是 capability/tool 契约线，不是
   runtime 扩建线，**Hold 不受阻**；但真实 egress 接线必须等 I4。

**反方观点（必须随 dossier 保留）**：① 商业服务薄客户端，数据政策/存续未知，不能成为
研究基础设施单点；② auto-registration 的 ToS 伦理问题；③ 匿名出口不满足 RWB 授权语义；
④ **最大风险是失焦**——全局唯一下一任务仍是 M8-002，检索线正确姿势是「登记候选+写卡片」，
不是开工实现。

---

## 3. 议题三：Agent 间通信机制分类学与 RWB 需求映射

### 3.1 起始问题与分析方法

**问题**（会话提出）：不同 agent 之间的通信方式究竟是如何实现的？——覆盖 harness/agent
工具、开源排名靠前的大模型生态、以及 CCF-A 顶会中关于 agent team 通信的研究。

**方法**：先把任何系统的 agent 通信拆成五个正交维度（FACT，分析框架），再把核查过的
全部系统放进网格，最后用 RWB 的五平面架构（ADR-0016）、I1–I12 不变量与真实任务场景
反推：RWB 需要什么、不需要什么、边界在哪。本节结论为议题一提案的第三次证据夯实。

### 3.2 通信五维分类学（FACT）

| 维度 | 取值谱系 |
|---|---|
| 传输介质 | 进程内函数调用 → 消息队列 → 黑板/共享池 → 群聊广播 → 共享文件/git → 开放协议（HTTP/JSON-RPC）→ **编排脚本（代码即拓扑）→ 持久化状态机工作流**（后两层经 ruflo 核查补入，见 3.7） |
| 寻址方式 | 角色名 / agent 实例 ID / topic 订阅 / 图的边 / 中心路由器指定 |
| 同步性 | 同步调用（阻塞等结果）/ 异步邮箱（投递后继续） |
| 负载格式 | 自由自然语言 / 半结构化文本 / 结构化 JSON / 工件+哈希 |
| 可见性 | 点对点（仅收发方）/ 广播（全员）/ 共享状态（公共区可读） |
| **拓扑载体**（ruflo 补入） | 数据结构（LangGraph 图）/ 持久化定义（MCP workflow）/ **代码（git 内编排脚本）** / 隐式（LLM 发言人选择）/ 无（星型） |

**关键观察（INFERENCE）**：五个维度中，前四个已被各系统充分探索（见 3.3），**第五维
（可见性）与「治理」整体缺席**——没有任何系统对消息做来源、授权、预算、证据绑定。

### 3.3 七个介质层级的逐系统核查（FACT）

#### 生产级 harness（三种私有实现 + 一种文件媒介）

| 工具 | 介质/模式 | 机制细节 |
|---|---|---|
| Claude Code | 进程内同步调用 | `Task` 工具启动子 agent（独立上下文+权限），结果一次性文本回传；子 agent 另有跨会话持久 memory 目录（文件媒介）；无 peer 信道 |
| OpenAI Codex | 进程内同步调用 | 主 agent `Task` 派发结构化 prompt，共享 worktree 作间接媒介；agent teams 中 peer 不直连 |
| DeepSeek Harness | 进程内调用 + durable mailbox + 共享工作区 | 父子 `send_message` 仅 depth-1；后台 job 异步完成投递通知（异步邮箱）；深层后代经父转发；共享工作区=长时记忆与事实上的 peer 媒介 |
| Anthropic 多 agent 研究系统 | 文件即信道 | subagent 发现写共享 markdown 记忆文件，lead 读取综合——刻意不用消息直连 |
| OpenAI Agents SDK | 进程内调用（两种） | ① handoffs：agent→agent 直接移交对话控制权（调用栈转移）；② agents-as-tools：agent 作为另一 agent 的工具被调用 |

#### 研究框架（四种结构性不同的实现）

| 框架 | 介质/模式 | 关键细节 |
|---|---|---|
| AutoGen GroupChat | 群聊广播 + 中心发言人选择 | Manager 每轮选发言者（LLM/轮转/随机/手动，0.4 支持 Selector 与 FSM 图控制）；全部消息进共享上下文全员可见——可见性最大、token 成本最大 |
| LangGraph | 显式图 + state channel | supervisor / network（任意互发，边即线路）/ hierarchical 三拓扑；消息写 state channel，图的边决定谁看到什么——通信拓扑本身成为一等编程对象 |
| MetaGPT | 发布/订阅消息池 | Environment 共享池；消息带 role 与 cause_by（发布者类型作 routing key）；负载是结构化「文档」而非自由聊天——黑板模式的工程化 |
| CrewAI | 任务管道 + 黑板 + 委派工具 | 前 task 输出注入下一 agent context；delegation 工具直接委派；共享 memory（短期跨任务+实体记忆）作黑板 |
| Magentic-One | 集中双账本 | Orchestrator 维护 task ledger + progress ledger；agent 间经账本间接协调；专职 Executor 验证 Coder 代码——状态机而非消息网络 |
| AgentScope（阿里） | Msg 对象 + Pipeline/MsgHub | 显式 Msg 传递；Pipeline=顺序管道；MsgHub=广播（全员收全部 Msg）——同框架提供点对点与广播两种原语 |
| llama-agents（LlamaIndex） | 外置消息队列 | 生产取向：agent 作为服务订阅消息队列，控制/消息平面分离，可接 SQS 等外部队列——唯一把传输介质做成可插拔的 |
| XAgent / ChatDev | 单线程循环 / chat chain 对话链 | XAgent：outer+inner 双层单线程派发 ToolAgent；ChatDev：角色对按 SOP 两两自然语言对话，phase 间传产物——把「对话」本身当通信协议 |

#### 协议层（跨边界标准化）

- **MCP**：agent↔工具的资源/工具/prompt 交换标准——工具结果回灌上下文的事实信道，即
  I4 指出的 DATA-EGRESS 路径；
- **A2A**（Linux 基金会）：agent↔agent 的 HTTP/JSON-RPC 标准，Agent Card 自描述发现 +
  任务委托——跨信任边界通信；与进程内通信是两个世界。

### 3.4 开源模型生态样本：模型层与通信框架分离的倾向（FACT + INFERENCE）

| 模型（厂商） | 官方 agent 通信设施 | 现状 |
|---|---|---|
| DeepSeek | 无官方框架 | 通信层由第三方建（本 harness 的父子+mailbox+共享工作区；AutoGen/CrewAI 接为 provider） |
| Qwen（阿里） | AgentScope + Qwen-Agent | 本次样本中的显著例外：提供 Msg/Pipeline/MsgHub，但不能据此作全生态完备度排名 |
| GLM（智谱） | AutoGLM（端侧单 agent） | 无官方多 agent 通信框架；生态借道 THUNLP 系（ChatDev/XAgent/AgentVerse 常以 GLM 为主力模型）——模型与框架分离 |
| Kimi K2（月之暗面） | kimi-cli / provider 抽象 | 无官方多 agent 框架 |
| Llama（Meta） | 无 | 由 llama-agents（消息队列）/LangGraph 承接 |
| gpt-oss（OpenAI） | Codex 生态承接 | 结构化子代理 |

**判断（INFERENCE）**：本次检索到的开源模型厂商样本呈现一种倾向：**模型层专注单体
agentic 能力（工具调用可靠性、长上下文、指令跟随），通信层交给框架/协议生态**。这支持
RWB 继续保持 provider-neutral（ADR-0003/M1-008），但不能据此推断所有厂商的内部路线或
宣称通信治理存在确定的市场空白。

### 3.5 顶会研究的收敛结论（FACT）

详见第 1.2 节文献表与第 6 节参考文献；此处只列与介质选择直接相关的五条：

1. 负载要结构化（MetaGPT 文档 > 自由聊天）；
2. 拓扑即性能，但最优拓扑任务依赖且往往**稀疏**（GPTSwarm / Cut the Crap / DeepMind
   稀疏通信拓扑报告）；
3. 先独立作答再交换防回音（ChatEval / ReConcile）；
4. 协作本身引入新失败模式：misalignment 与 error propagation（MAST / Chain of Agents）；
5. 通信量本身是可优化成本（Cut the Crap / SafeSieve 渐进剪枝）。

### 3.6 RWB 需求映射（INFERENCE，本节核心）

#### 3.6.1 RWB 真实需要的通信场景（从仓库任务提取，非想象）

| 场景 | 仓库依据 | 当前实现 | 缺口 |
|---|---|---|---|
| 委派与回传 | M3-003（H1/H2 Handoff）、ADR-0011 | Handoff 契约 + Transfer Manifest/Audit | 已覆盖（治理最完整的部分） |
| 证据/检索 fan-out | M3-004（并行预算、review loop）、M7-011 | 多 evidence-scout 并行、预算硬边界 | 汇合点在主上下文——综合失真风险（议题二的 Source Admission 即解法） |
| 审查循环 | M3-004 review loop、M2-002 reviewer profile | reviewer 质疑经 coordinator 中转 | peer 提问语音行为缺失（议题一 1.3 的「推」） |
| 恢复与交接 | M3-001/006（SAFE_PAUSE、fresh-process recovery）、ADR-0009 | 文件权威 checkpoint + 新 Attempt | 已覆盖（文件介质天然异步） |
| 跨 owner 协作 | DEVELOPMENT.md 责任表、共享 seam 变更 | PR 治理 + architecture review | 已覆盖（人类层通信，PR #25 机器化） |

**结论**：RWB 需要的不是「更多通信」，而是**两类受控推送**——peer 提问（question）与
审查质疑（refutation）；其余场景文件介质已是正确答案。

#### 3.6.2 五维 × RWB 治理映射（逐维判定）

| 维度 | 系统生态现状 | RWB 立场（依据） |
|---|---|---|
| 介质 | 七层并存，无治理 | **不新增介质层**：文件+归档（第七层的治理化版本）是原生选择（ADR-0009 file-first、ADR-0012 文件权威 Trace）；Assignment inbox 天然等价「队列」；新增总线/进程信道违反 I9（无隐藏长期权威） |
| 寻址 | 角色名/实例 ID/topic/边 | `actor_id` + `accountable_owner` 实名绑定（ADR-0012）——比全部七层都强；寻址权限归 Method Resolution（M8-003 后），禁止运行时私寻址 |
| 同步性 | 同步调用为主 | Attempt 语义天然异步：新 Attempt 不覆写历史（ADR-0009）；对账本式（Magentic-One）与队列式（llama-agents）的借鉴止于「投递后继续」的语义，不引入常驻服务 |
| 负载 | 从自由文本到结构化 JSON | RWB 已是结构化极端（Task packet/Handoff/EVID/Schema+哈希）——与 MetaGPT/顶会结论 1 同向；peer 推送负载必须复用同一契约体系（议题一提案），不得引入自由聊天 |
| 可见性 | 点对点/广播/共享状态三选 | **RWB 独有优势**：受控读取（ADR-0011 §2）已实现细粒度可见性（默认拒绝正文、扩域留痕、按 ID 回放）——七层介质无一具备；peer 推送的可可见性也应由同一机制管辖 |

#### 3.6.3 应用范围界定（需要 / 拒绝 / 延后）

**需要（Hold 后按恢复顺序进入）**：
- 受控 peer 提问与审查质疑（evidence-grade，议题一提案）；
- 证据 fan-out 的工件汇合（Source Admission，议题二提案）——**不需要消息通道**，工件
  即协调媒介，两提案在此闭环。

**拒绝（与治理边界冲突）**：
- 自由群聊/广播（AutoGen GroupChat/MsgHub 模式）：全员可见=可见性失控，且违反
  Cut the Crap/回音室证据；
- LLM 自动发言人选择（routing authority 冲突：I1/I2，须由 Resolution 或 Human Gate 决定）；
- 可学习拓扑（GPTSwarm）：拓扑=Method 决策，交给端到端优化等于放弃解释权——可作
  **离线研究对象**（M5-003 对照），不得进运行时；
- 隐藏共享状态（framework checkpoint DB、runtime memory）：I9 直接禁止。

**延后（等真实消费者）**：
- 跨主体 A2A（等 RWB 有对外 agent 交互的真实需求；届时 Agent Card 类发现机制须过
  source admission）；
- 外置消息队列（llama-agents 式）：等单机文件介质出现实测吞吐瓶颈再评估，且须保
  文件权威回放。

#### 3.6.4 与议题一/二的衔接（修订后的创新点表述）

七个介质层级 × 五个维度的有限样本核查支持一个候选方向：通信介质已有大量实现，而 provenance、
预算、准入和 Human Gate 的组合治理在本次样本中覆盖不足。它不能证明“全谱系”或“无人做”。
具体到 RWB，可进一步检验三个候选贡献：

1. **分类学候选**：带治理维度的 agent 通信分类学（第五维可见性 + provenance/预算/
   准入三治理轴）；
2. **机制贡献**：Communication as Evidence（议题一）——把第五维做实；
3. **实证候选**：用 M5-003 对照测「何种研究任务下受控推送优于纯拉取」——回应拓扑收益的
   任务依赖性；本次检索尚未找到充分的科研工作流对照证据，见第 5 节 CAPTURE_GAP。

### 3.7 增补：ruflo（ruvnet/ruflo）核查与分类学修订（FACT + INFERENCE）

#### 3.7.1 项目定性：两副面孔的 mega-harness

[ruvnet/ruflo@d065b15](https://github.com/ruvnet/ruflo/tree/d065b15927c6ba7318623e8af123e7980e4c6681)
（MIT，TypeScript，`claude-flow` 后继，自称 "The original agent meta-harness"）：
33 个原生 Claude Code 插件 + 21 个 npm 插件的市场化 harness 生态，覆盖 swarm 协调、
记忆、自学习、MCP server、联邦通信。按本 workstream 证据纪律分层核查：

| 面孔 | 证据（FACT） |
|---|---|
| 营销面（标 CLAIM，未逐项验证实现） | "100+ Agents"、"零信任联邦 Comms Layer"、"SONA 神经模式 self-learning"、"swarm consensus"（README 主张） |
| 工程面（可验证硬货） | ① 33 个插件全部有 ADR-0001 契约 + smoke 测试 + namespace 协调声明（ADR-0001 原文："This ADR completes the plugin-contract retrofit across the entire ruflo plugin family"）；② [ADR-0002](https://github.com/ruvnet/ruflo/blob/d065b15927c6ba7318623e8af123e7980e4c6681/plugins/ruflo-workflows/docs/adrs/0002-native-workflow-orchestration.md) 诚实记录 tradeoff（"Negative: two surfaces means contributors must pick the right one"）；③ 性能主张带测量与边界（向量记忆标注 "ANN wins above the crossover, **ties/loses at small N**" + 自有 audit 链接）；④ ADR 作者署名 `coder (Claude Code)`——agent 作者身份显式声明 |

**判断（INFERENCE）**：其「插件契约化 + smoke-as-contract + 诚实负面前提」的工程面
与 RWB 治理风格同源；mega-harness 规模同时是「功能全开」路线成本的反面教材（见
3.7.4）。

#### 3.7.2 对分类学的修订：介质九层 + 「拓扑载体」维度

ruflo 的核心贡献是把 agent 间协调从「消息问题」重构为「编排问题」，补入两个介质层：

**（a）确定性编排脚本作为介质（ADR-0002）**：`.claude/workflows/*.js` 用四钩子 API
编排子 agent——`agent(prompt, opts)`（`opts.schema` 结构化校验返回）、`parallel(thunks)`
（barrier）、`pipeline(items, ...stages)`（**无 barrier** 逐项流过全部阶段）、
`phase/log`（进度分组）。**拓扑本身是 git 里的代码**——可 review、可 diff、可版本化。

> **一手同构证据**：本调研所用 DeepSeek Harness 的 workflow 工具与这套四钩子 API 形状
> 完全相同（agent+schema / pipeline 无 barrier / parallel 有 barrier / phase）。两个
> 独立 harness 样本出现相同原语集——「编排脚本作为协调介质」是值得继续验证的工程模式。分类学
> 由七层扩为**九层**（+编排脚本、+持久化状态机工作流），并新增「拓扑载体」维度：
> 拓扑=Method 决策，其载体（图/定义/代码/隐式/无）决定可解释性与可审查性——ruflo
> 的「脚本即拓扑」提供了“拓扑可进入代码审查”的工程例子，支持继续评估 RWB 把 routing authority 放
> 进 Resolution；但 ruflo 拓扑仍无证据绑定（脚本管协调不管 provenance）——治理空白依旧。

**（b）声明式持久化状态机（MCP `workflow_*`，ADR-0001）**：`created → running ↔
paused → completed/cancelled` 生命周期 + **approval gates（人工审批暂停点）** + 跨会话
可恢复（`workflows-state` namespace）+ 无状态旁路（`workflow_execute`）。这与 RWB
SAFE_PAUSE、Human Gate 和 M3-001 checkpoint/resume 存在局部工程类比，但 authority、证据与
恢复语义并不等价；它同样区分「长时命人工门控管道」与「一次性确定性 fan-out」两条路径。

#### 3.7.3 对三议题的具体补充

**议题一（peer 通信）四条**：
1. **schema-validated 结构化返回已有 production-facing 实例**（`agent(prompt,{schema})`）——
   为议题一的「白名单消息类型+结构化工件」提供工程可行性样本，但不证明它是通用标准；
2. **fan-out/pipeline 是「无消息通道协作」的极致形态**：barrier(`parallel`) vs 无
   barrier(`pipeline`) 两原语覆盖若干常见 fan-out 场景，agent 间零直接消息——议题二
   「工件即协调媒介」又一例证；**汇合语义（何时 barrier）变成显式编程决定**——
   「汇合点显式化」应进 Communication as Evidence 提案：**barrier 处正是综合失真风险
   点，应触发 H2 抽样**；
3. **重放语义**：`resumeFromRunId` + per-run journal + 未变更 `agent()` 返回缓存 =
   audit replay 的工程实现——与 file-only verify 同向，但 journal 私有（非文件权威），
   I9 的对照样本；
4. **反面印证**：mesh/adaptive + consensus swarm（CLAIM）是自由互联路线的存在证明；
   无反证绑定的 consensus 恰是 `ECHO-CONSENSUS-NO-EVIDENCE` 风险的规模化样本。

**议题二（证据级检索）一条**：ReasoningBank / trajectory learning / HNSW 向量记忆
（CLAIM）指向检索的另一半——**团队记忆的检索**：Evidence Pool 增长后「哪个 agent 曾
验证过什么」本身需要检索；Retrieval Manifest 可延伸为 *Memory Manifest*（团队记忆
条目带 provenance 检索）——提案的自然扩展方向。

**治理层启发（对 RWB 最直接可用）**：

| ruflo 实践 | RWB 对应/启示 |
|---|---|
| 插件级 ADR + smoke-as-contract（33 插件全覆盖） | RWB 的 ADR 纪律可下沉为「每个 capability card 附最小契约测试」——议题二借鉴 1（capability card 机器化）的具体做法 |
| namespace 协调声明（`workflows-state` 归属声明） | ≈ PR 流程的 owned/shared files 声明；Registry namespace 可借鉴显式 claim 机制 |
| ADR 署名 `coder (Claude Code)` | RWB actor_id + accountable_owner 绑定的非正式先例——RWB 正式化并强制实名是明确优势 |
| 33 插件 smoke 契约用一个 fan-out workflow 自审 | 与 test_pr_governance 审自己 PR 同型；可扩展为「用 RWB trace 审计 RWB CI」的自证闭环 |
| 双 surface 决策表（MCP vs native） | 「决策表而非替代关系」值得在 future Execution Host seam 文档采用 |

#### 3.7.4 克制面（Adoption Matrix 视角）

该 mega-harness 同时是「功能全开」路线的成本样本：其 README 声称 100+ agent、12 个
自动后台 worker、联邦/神经/自学习大量未验证主张——对照「先证明失败模式」纪律，ruflo
可作为 **REJECT/ADAPT 候选样本库**；它展示了这些机制的公开声明与部分工程表面，但不能证明
全部能力已经实现，也不能证明其他系统没有相应治理。
零信任联邦 comms layer（跨机器/org agent 通信）若真实现，是 A2A 类通信的另一生产
数据点，但按 README 口径无法确认治理深度，标 CLAIM 留待深挖。

## 4. 与主线的相容性声明（INFERENCE）

- M8-002 Mode Action first-class contract 仍是全局唯一下一任务；本文三议题均为
  M8-003 之后的候选，且议题二第 4 构件（搜索策略入 Method Plane）恰是 M8-002 的
  用例素材而非竞争项；议题三不引入任何新提案，只夯实议题一/二的证据与边界。
- 三议题均符合「先证明真实失败模式，再引入机制」的 Adoption Matrix 纪律：
  - 议题一的真实失败模式：coordinator 单点上下文压力与综合失真；peer 请求绕行。
  - 议题二的真实失败模式：检索不可复现审计；查询意图泄漏；来源无准入。
- 与 [ADOPTION_MATRIX.md](ADOPTION_MATRIX.md) / [CONFORMANCE_PLAN.md](CONFORMANCE_PLAN.md)
  的关系：本文两提案待裁定后应进入 adoption 管道（discover → audit → candidate → trial
  → evaluation → shadow → human review → promotion），不跳级。

## 5. 已知缺口（CAPTURE_GAP）

- anysearch 后端（api.anysearch.com）的数据留存/隐私政策未核查（客户端仓库不含）；
- 文献结论的任务依赖性：多数 multi-agent 论文基于问答/推理 benchmark，未在科研工作流
  场景验证——RWB 自测（M5-003）前不能直接引用为普适结论；
- 2.2/2.3 表中关于 anysearch 的行为描述基于 SKILL.md/doc_spec.md/README 声明，未实际
  执行其 CLI（遵循「下载内容未安装、执行或自动准入」的 M7-009 纪律）；
- DeepSeek Harness subagent 语义基于一手使用观察，无公开文档可引，标注为本会话证据；
- 议题三的通信机制描述多数来自官方文档/源码快照而非长期运行经验；AutoGen 0.2→0.4、
  LangGraph 等框架迭代快，快照可能过时（检索于 2026-08-23）；
- 多数本次检索到的 multi-agent 通信论文基于问答/推理 benchmark；本次检索尚未找到充分的
  科研工作流通信对照实验。这是 CAPTURE_GAP，不是对全体文献的空白证明；
- GLM/Kimi/Llama 生态的「无官方通信框架」判断基于公开仓库检索，不排除内部或未发布
  项目；AgentScope 是否代表阿里模型组路线未经官方声明核实；
- ruflo 的 swarm consensus / 联邦 comms / SONA self-learning / ReasoningBank 均为
  README 主张（CLAIM），未读实现源码；「DSH workflow 与 ruflo 四钩子同构」基于一手
  使用观察非源码比对；其向量记忆 benchmark 为其自测数字，未独立复现。

## 6. 参考文献

**议题一（多 agent 通信）**
- [Claude Code — Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic — Context engineering for AI agents](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)
- [Cognition — Don't Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents)
- [AutoGen 0.2 — Conversation Patterns（GroupChat）](https://microsoft.github.io/autogen/0.2/docs/tutorial/conversation-patterns/)
- [Magentic-One（arXiv 2411.04468）](https://ar5iv.labs.arxiv.org/html/2411.04468v1)
- [LangGraph — Hierarchical Agent Teams](https://www.kinde.com/learn/ai-for-software-engineering/ai-agents/hierarchical-agent-teams-with-langgraphsupervisor/)
- [MetaGPT（ICLR 2024 Oral 报道）](https://m.thepaper.cn/newsDetail_forward_26261080)
- [CAMEL（NeurIPS 2023）](https://dev.neurips.cc/virtual/2023/poster/72905)
- [OpenAI Agents SDK — Handoffs](https://github.com/openai/openai-agents-python/blob/cdde4d65/docs/handoffs.md)
- [AWS Bedrock 多 agent 协作模式](https://pypi.org/project/aws-cdk.aws-bedrock-alpha/2.260.0a0/)
- [Linux Foundation — Agent2Agent 协议](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [MAST: Why Do Multi-Agent LLM Systems Fail?（NeurIPS 2025）](https://mlanthology.org/neurips/2025/cemri2025neurips-multiagent/)
- [Hallucination Cascade（arXiv 2606.07937）](https://arxiv.org/html/2606.07937v1)
- [Mitigating LLM Hallucination Snowballing（IEEE）](https://ieeexplore.ieee.org/document/11366934)
- [Chain of Agents（Google Research，NeurIPS 2024）](https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/)
- [Multiagent Debate（ICML 2023）](https://www.semanticscholar.org/paper/4780d0a027c5c5a8e01d7cf697f6296880ffc945)
- [ChatEval（ICLR 2024）](https://researchportal.hkust.edu.hk/en/publications/chateval-towards-better-llm-based-evaluators-through-multi-agent-deb)
- [ReConcile（ACL 2024）](https://aclanthology.org/2024.acl-long.381/)
- [GPTSwarm（ICML 2024 Oral）](https://icml.cc/virtual/2024/oral/35447)
- [Cut the Crap（ICLR 2025）](https://mlanthology.org/iclr/2025/zhang2025iclr-cut/)
- [Lost in the Middle（TACL 2023）](https://arxiv.org/abs/2307.03172)
- [More Agents Is All You Need（TMLR）](https://arxiv.org/abs/2402.05120)
- [DyLAN（arXiv 2310.02170）](https://arxiv.org/abs/2310.02170)
- [Multi-Agent Design（Google Research）](https://research.google/pubs/multi-agent-design-optimizing-agents-with-better-prompts-and-topologies/)

**议题二（检索接入）**
- [anysearch-ai/anysearch-skill@4d6cef9](https://github.com/anysearch-ai/anysearch-skill/tree/4d6cef918e9338c9deef43b81ac0f7e22606825f)（含 SKILL.md、scripts/shared/doc_spec.md、scripts/shared/constants.json、SECURITY.md，2026-08-23 快照核查）

**议题三（通信机制分类学与模型生态）**
- [ruflo@d065b15](https://github.com/ruvnet/ruflo/tree/d065b15927c6ba7318623e8af123e7980e4c6681) ·
  [ADR-0001 workflows 契约](https://github.com/ruvnet/ruflo/blob/d065b15927c6ba7318623e8af123e7980e4c6681/plugins/ruflo-workflows/docs/adrs/0001-workflows-contract.md) ·
  [ADR-0002 原生编排双表面](https://github.com/ruvnet/ruflo/blob/d065b15927c6ba7318623e8af123e7980e4c6681/plugins/ruflo-workflows/docs/adrs/0002-native-workflow-orchestration.md)
- [AgentScope — Pipeline 教程](https://doc.agentscope.io/tutorial/task_pipeline.html) ·
  [MsgHub 消息中心](https://java.agentscope.io/v1/zh/docs/task/msghub.html)
- [llama-agents 官方博客](https://www.llamaindex.ai/blog/introducing-llama-agents-a-powerful-framework-for-building-production-multi-agent-ai-systems) ·
  [SQS 集成 fork](https://github.com/MartinRistov/llama-agents)
- [AutoGen — Selector Group Chat](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html) ·
  [FSM/Graph 发言人控制讨论](https://github.com/microsoft/autogen/discussions/5016)
- [ChatDev（THUNLP，中文 README）](https://raw.githubusercontent.com/haochihlin/ChatDev/main/readme/README-Chinese.md) ·
  [XAgent 源码分析](https://jishuzhan.net/article/2072866873775058945)
- [CrewAI — 跨 agent 输出传递（社区）](https://community.crewai.com/t/how-to-pass-response-from-an-agent-in-a-chain-as-a-parameter-to-exa-tool-that-is-used-by-another-agent/349/6) ·
  [Shared Memory 指南](https://hindsight.vectorize.io/guides/2026/07/17/guide-crewai-shared-memory-across-a-crew)
- [A2A vs MCP 协议对比](https://beam.ai/agentic-insights/agent2agent-vs-mcp-2026-ai-agent-stack)
- [SafeSieve: Progressive Pruning for Multi-Agent Communication](https://www.semanticscholar.org/paper/c98b22964aea62c73cd7e330496b07191425da96)（IJCAI 2025）
- [LLM Agent 反馈机制综述（IJCAI 2025）](https://mlanthology.org/ijcai/2025/liu2025ijcai-survey/) ·
  [群组讨论交互建模（IJCAI 2025）](https://mlanthology.org/ijcai/2025/yang2025ijcai-llm/)
- [DeepMind — Improving Multi-Agent Debate with Sparse Communication Topology](https://multiagents.org/2025_talks/talk_improving_multi_agent_debate_with_sparse_communication_topology.pdf)

**仓库内部**
- [workstream README](README.md) · [SOURCE_MANIFEST.md](SOURCE_MANIFEST.md) ·
  [CLAIM_LEDGER.md](CLAIM_LEDGER.md) · [ADOPTION_MATRIX.md](ADOPTION_MATRIX.md) ·
  [SYNTHESIS.md](SYNTHESIS.md) · [CONFORMANCE_PLAN.md](CONFORMANCE_PLAN.md)
- [RECOVERY_GATE_PROPOSAL.md（I1–I12）](../execution-runtime-recovery-audit/RECOVERY_GATE_PROPOSAL.md)
- [docs/DEVELOPMENT.md](../../../DEVELOPMENT.md) · [docs/TASKS.md](../../../TASKS.md) ·
  [ADR-0011](../../../decisions/0011-RISK-TIERED-HANDOFF-AND-CONTROLLED-READS.md) ·
  [ADR-0016](../../../decisions/0016-METHOD-AWARE-RESEARCH-CONTROL-PLANE.md)
