<!-- markdownlint-disable -->
# 科研 Agent / AI for Science 外部参考材料与简要评估

> 审计日期：2026-08-19
> 目的：为 Research Agent Workbench（RWB）建立可持续更新的外部参照系。
> 原则：优先使用项目官方仓库、官方技术页和论文；记录“值得借鉴什么”，而不是按 Star 数量排序。

## 1. 使用方式

本文件将外部材料分为六类：

1. 端到端 AI Scientist / Autonomous Research；
2. 科研工作流与 Agent Runtime；
3. 文献、证据与知识综合；
4. Scientific Tool / MCP / Capability 生态；
5. Agent Skill 与 Skill Evolution；
6. Benchmark、Trace 与 Verification。

对 RWB 的评估统一使用四个标签：

- **直接借鉴**：适合转化为 RWB 核心设计原则；
- **适合集成**：不建议自己重造，应作为 Tool / Agent / Runtime Provider；
- **保持差异**：与 RWB 相邻，但 RWB 应明确采取不同设计；
- **持续跟踪**：当前不进入实现，但可能影响后续架构。

---

# 2. 端到端 AI Scientist / Autonomous Research

## 2.1 AI Scientist v2 — Sakana AI

- 来源：<https://github.com/SakanaAI/AI-Scientist-v2>
- 定位：从 hypothesis、experiment、analysis 到 manuscript 的端到端自主科研系统；v2 使用 progressive agentic tree search 与 experiment manager。
- 值得关注：
  - 研究探索可显式表示为树，而不是单线工作流；
  - 开放探索与高成功率之间存在明显 trade-off；
  - 实验执行必须与 sandbox / execution boundary 配套。
- 对 RWB：
  - **直接借鉴**：Research Strategy 可包含 tree-search / branching / prune；
  - **保持差异**：RWB 不应把“端到端自动完成论文”作为核心成功条件；
  - **评价**：高相关，但更适合作为 Strategy/Runtime 参照，而不是总体架构模板。

## 2.2 Agent Laboratory

- 来源：<https://github.com/SamuelSchmidgall/AgentLaboratory>
- 定位：Literature Review → Experimentation → Report Writing 三阶段科研工作流，使用 specialized agents，并支持不同人类参与程度。
- 值得关注：
  - Human feedback 是科研质量的重要控制点；
  - 端到端系统需要可显式插入人工反馈。
- 对 RWB：
  - **直接借鉴**：Human Gate 必须作为科学决策对象，而非普通聊天确认；
  - **保持差异**：不采用固定三阶段全局 DAG；Mode Action 应保持可选。

## 2.3 AI-Researcher — HKUDS

- 来源：<https://github.com/HKUDS/AI-Researcher>
- 定位：围绕 resource collection、idea generation、implementation、experimentation、writing 等科研阶段组织 Agent。
- 对 RWB：
  - **持续跟踪**：观察 end-to-end research automation 的能力上限；
  - **保持差异**：避免重新退化为 Literature Agent / Experiment Agent / Writer Agent 的永久角色体系。

## 2.4 Google AI Co-Scientist

- 来源：<https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/>
- 定位：多 Agent hypothesis generation / reflection / ranking / evolution / meta-review 系统。
- 值得关注：
  - research reasoning strategy 可以是可配置的 deliberation policy；
  - candidate generation、批判、pairwise ranking、evolution 可以分层。
- 对 RWB：
  - **直接借鉴**：未来引入 `Research Strategy`，与 Mode 解耦；
  - **保持差异**：不把 tournament / debate 固化为所有科研任务的默认机制。

## 2.5 AgentRxiv

- 来源：<https://arxiv.org/abs/2503.18102>
- 定位：让 autonomous research laboratories 上传、读取并继续构建其他 Agent 的研究报告，实现 cumulative research。
- 值得关注：跨运行、跨 Agent 的研究资产复用可以产生增量价值。
- 对 RWB：
  - **直接借鉴**：Research State 必须比单次 session / report 生命周期更长；
  - **保持差异**：不以“历史报告集合”作为主要记忆形式，而应积累结构化 Evidence / Claim / Unknown / Failure / Decision。

## 2.6 OR-Agent

- 来源：<https://github.com/qiliuchn/OR-Agent>
- 定位：面向可自动评价问题的结构化 research tree；支持 branching、backtracking、experiment reflection、long-term reflection、checkpoint 与 solution database。
- 值得关注：
  - 失败路径与 local optimum 是研究轨迹的一部分；
  - Research Tree 有助于保存“为什么停止某条方向”。
- 对 RWB：
  - **直接借鉴**：Research State 增加 Attempt / Failure / Revisit Condition / Frontier；
  - **保持差异**：Research Tree 只是 Strategy，不应成为统一科研数据模型。

## 2.7 AutoScientists

- 来源：<https://github.com/mims-harvard/AutoScientists>
- 定位：自组织多 Agent 团队围绕 promising hypotheses 协作、互评，并共享成功和失败，面向长时间计算科研实验。
- 值得关注：
  - decentralized coordination；
  - 共享失败可以减少重复探索；
  - task-specific policy 与 universal orchestration 分离。
- 对 RWB：
  - **持续跟踪**：未来多 Agent / Research Frontier；
  - **直接借鉴**：失败结果应成为可查询研究资产；
  - **保持差异**：不默认多 Agent，不让团队拓扑成为科研方法本身。

## 2.8 Panda — AllenAI

- 来源：<https://github.com/allenai/panda>
- 定位：极简 outer plan-do + inner act-reflect autonomous research agent。
- 值得关注：简单 controller 仍可完成大量科研任务；项目曾主动移除内建 research functions，以避免预置工具反向 bias 研究决策。
- 对 RWB：
  - **直接借鉴**：永久保留 Plain Agent / Tool-only baseline；
  - **保持差异**：复杂 Method Plane 必须通过实验说明自己的增量价值。

## 2.9 autoresearch — Andrej Karpathy

- 来源：<https://github.com/karpathy/autoresearch>
- 定位：修改代码 → 固定预算训练 → 测量指标 → 保留/丢弃 → 重复的极简自动优化循环。
- 对 RWB：
  - **直接借鉴**：当 objective + validator 已充分明确时，Method Resolution 应允许返回 deterministic loop / no-Skill / no-multi-Agent。

---

# 3. 科研工作流与 Agent Runtime

## 3.1 FAROS

- 来源：<https://github.com/OpenNSWM-Lab/FAROS>
- 定位：Blueprint-driven research workflow runtime；核心对象包括 Blueprint、Capability、Profile、Provider，以及 run/event/artifact/memory/verification。
- 与 RWB 的邻近性：**最高**。
- 值得关注：
  - 稳定 runtime boundary；
  - domain modules 与 runtime core 分离；
  - Provider 不等于 LLM；
  - Capability / Provider Registry。
- 对 RWB：
  - **直接借鉴**：定义稳定 Core Surface 与 replaceable implementation boundary；
  - **保持差异**：RWB 不以预定义 Blueprint 为核心，而以 Method Resolution 解释“为什么需要某机制”；
  - **风险**：若 RWB 只做 Blueprint + Capability + Provider + Runtime，将与 FAROS 高度同质化。

## 3.2 Claude Science

- 来源：<https://www.anthropic.com/news/claude-science-ai-workbench>
- 定位：面向科研人员的 AI workbench，整合 tools/packages、compute 和 auditable artifacts。
- 对 RWB：
  - **适合集成/对标产品层**：说明通用科学工作台与工具接入会快速商品化；
  - **保持差异**：RWB 不应把 UI、Tool 数量或单一 Host 作为长期壁垒。

---

# 4. 文献、证据与知识综合

## 4.1 PaperQA2

- 来源：<https://github.com/Future-House/paper-qa>
- 定位：scientific RAG / agentic paper search、evidence gathering、citation-backed answer；支持多 Provider，并在 2025 年从 SemVer 转向 CalVer。
- 关键教训：
  - agent behavior version 与普通 API version 并不完全一致；
  - 旧的 pickled `Docs` state 在重大版本升级后不可兼容；
  - runtime-internal state 不是理想的长期科研资产格式。
- 对 RWB：
  - **适合集成**：literature-search / evidence-retrieval provider；
  - **直接借鉴**：长期 Research State 必须 schema-first，不绑定 Python object；
  - **保持差异**：Evidence admissibility 与 Claim ceiling 仍由 RWB 控制。

## 4.2 OpenScholar

- 来源：<https://arxiv.org/abs/2411.14199>
- 定位：基于大规模开放论文库的 retrieval + scientific synthesis + citation-backed response。
- 对 RWB：
  - **适合集成**：说明 retrieval/synthesis 已经是独立成熟战场；
  - **保持差异**：RWB 不应以“搜索更强”作为核心创新。

## 4.3 STORM / Co-STORM

- 来源：<https://github.com/stanford-oval/storm>
- 定位：通过 multi-perspective question asking、simulated conversation、knowledge curation 与 outline/article generation 支持深度研究和知识整理。
- 值得关注：
  - 高质量 research 的前置步骤是提出高质量问题；
  - Co-STORM 使用动态知识组织与 human collaboration。
- 对 RWB：
  - **直接借鉴**：Research State 应显式维护 Question / Unknown / Contradiction；
  - **保持差异**：报告生成不是核心研究状态。

## 4.4 Elicit Systematic Review

- 来源：
  - <https://elicit.com/blog/systematic-review-for-prisma-2020>
  - <https://elicit.com/blog/evaluating-elicit-slr>
- 定位：将 search、screening、extraction、synthesis 按 systematic review process 工程化，并支持 PRISMA 2020、审计与复现。
- 对 RWB：
  - **直接借鉴**：引入 `Protocol Profile` / `Method Standard`，用于 PRISMA、Cochrane 或领域规范；
  - **保持差异**：Protocol 不等于 Mode，也不应写成 Skill；
  - **核心启示**：scientific rigor 是过程属性，不是最终报告附加的 checklist。

---

# 5. Scientific Tool / MCP / Capability 生态

## 5.1 ToolUniverse

- 来源：<https://github.com/mims-harvard/ToolUniverse>
- 定位：大规模 scientific tool ecosystem，统一描述和调用科学数据库、API、模型与软件包。
- 值得关注：
  - Tool/Capability registry；
  - compact discovery，避免将完整工具宇宙塞入 context；
  - Provider/Tool 与调用协议可独立演化。
- 对 RWB：
  - **直接借鉴**：建立 `Capability Resolver` 与 capability snapshot；
  - **适合集成**：RWB 不需要自己建设千级 Scientific Tool 仓库；
  - **保持差异**：RWB 决定“需要什么能力”，ToolUniverse 解决“哪里有这个能力”。

## 5.2 Biomni

- 来源：<https://github.com/snap-stanford/Biomni>
- 定位：通用 biomedical AI agent，整合 retrieval-augmented planning、代码执行、数据集、数据库和领域工具。
- 值得关注：
  - tool metadata 与 resource retrieval；
  - reproducible environment；
  - 大型科学 capability environment 的实际工程复杂度。
- 对 RWB：
  - **适合集成/参考 Adapter 层**；
  - **直接借鉴**：Tool/Execution 权限必须与科研方法分离；
  - **保持差异**：不要复制大而全的 domain environment。

## 5.3 Paper2Agent

- 来源：<https://arxiv.org/abs/2509.06917>
- 定位：将论文与代码自动转化为 MCP server / research agent，并通过生成测试持续修正。
- 对 RWB：
  - **直接借鉴**：Paper/Repo → Candidate Capability/Skill 自动生成管线；
  - **保持差异**：自动生成只能进入 candidate，不可自动 promotion；
  - **适合作为未来 Source Admission 流程参考**。

## 5.4 Zotero MCP

- 来源：<https://github.com/54yyyu/zotero-mcp>
- 定位：通过 MCP 将本地/云端 Zotero library 暴露给 ChatGPT、Claude 等 Agent。
- 对 RWB：
  - **适合集成**：document-read / literature-library capability；
  - **保持差异**：Zotero 是 Adapter，不应进入 Mode 语义。

## 5.5 paper-search-mcp

- 来源：<https://github.com/openags/paper-search-mcp>
- 定位：将多学术来源 paper search / download 封装为 MCP/CLI/Skill。
- 对 RWB：
  - **适合集成**：作为 `literature-search` capability 的候选 Provider；
  - **保持差异**：query coverage、source boundary、stop rule 仍属于 Mode/Method/Protocol。

---

# 6. Agent Skill 与 Skill Evolution

## 6.1 K-Dense Scientific Agent Skills

- 来源：<https://github.com/K-Dense-AI/scientific-agent-skills>
- 定位：跨 Claude Code、Codex、Cursor 等 host 的大型 scientific skill collection。
- 值得关注：
  - Skill portability；
  - source/version/provenance；
  - 按需安装/加载；
  - security scan。
- 对 RWB：
  - **直接借鉴**：Skill Contract 与 Host Adapter 分离；
  - **保持差异**：不参与“Skill 数量竞赛”；
  - **关键观察**：现有 Skill 生态混合了 Tool docs、API wrapper、method、workflow、output formatting，反证 RWB 的 Need-first 分类具有必要性。

## 6.2 SciVisAgentSkills

- 来源：<https://arxiv.org/abs/2606.05525>
- 定位：针对 scientific visualization 的 skill + benchmark；比较 Skill 在不同 agent harness 下的收益与 token efficiency。
- 对 RWB：
  - **直接借鉴**：Skill 价值应写成 `Need × Host × Model × Tool Snapshot × Baseline × Metric`，而不是全局 `passed`；
  - **直接借鉴**：正式记录 `baseline` 与 `measured_increment`。

## 6.3 CASCADE

- 来源：<https://arxiv.org/abs/2512.23880>
- 定位：通过 continuous learning、web/code extraction、reflection 等机制不断积累 executable skills。
- 对 RWB：
  - **直接借鉴**：Skill 可持续演化，而非只手工维护；
  - **保持差异**：采用 Governed Skill Evolution：发现 → candidate → audit → trial → baseline comparison → human promotion；
  - **不采用**：Agent 直接改 Skill 后立即投入正式科研任务。

## 6.4 SkillFoundry

- 来源：<https://arxiv.org/abs/2604.03964>
- 定位：从 repository/API/script/notebook/document/paper 等异构资源中挖掘并验证 skill，支持 expand/repair/merge/prune。
- 对 RWB：
  - **直接借鉴**：Need dossier 可利用自动化 source mining；
  - **直接借鉴**：Skill library 需要 merge/prune，而非只有 add；
  - **保持差异**：RWB promotion 必须受 Method Need 和历史科学语义约束。

## 6.5 SkillComposer

- 来源：<https://arxiv.org/abs/2606.06079>
- 定位：将 Skill evolution 分为 create / improve / merge，并研究 specificity 与 generalization 的张力。
- 对 RWB：
  - **持续跟踪**：适合作为未来 Skill evolution algorithm；
  - **直接借鉴**：Skill generalization 必须通过跨任务 forward test，而不能只看单任务收益。

## 6.6 Agent Skill Evaluation and Evolution Survey

- 来源：<https://arxiv.org/abs/2606.11435>
- 定位：总结 skill evaluation/evolution 的多种范式和 benchmark 类型。
- 对 RWB：
  - **直接借鉴**：Skill lifecycle 应从 package versioning 升级为 evaluation-driven evolution；
  - **持续跟踪**：用于维护 RWB Skill Evaluation Matrix。

---

# 7. Benchmark、Trace 与 Verification

## 7.1 ScienceAgentBench

- 来源：<https://arxiv.org/abs/2410.05080>
- 定位：从真实同行评议论文提取 102 个科研任务，强调应先严格评估 scientific workflow 的 individual tasks，再谈 end-to-end automation。
- 对 RWB：
  - **直接借鉴**：以 Atomic Task / Method Resolution 为主要评测单元；
  - **直接借鉴**：报告执行结果、正确性与成本，而非只看最终文本质量。

## 7.2 AstaBench

- 来源：<https://arxiv.org/abs/2510.21652>
- 定位：2400+ scientific research problems，强调 controlled tools、cost、agent class 与 confounder control。
- 对 RWB：
  - **直接借鉴**：Evaluation Manifest 必须冻结 model/tool/cost/context 等环境变量；
  - **适合作为外部 benchmark source**。

## 7.3 SciAgentArena

- 来源：<https://arxiv.org/abs/2606.12736>
- 定位：约 200 个现实科研场景，支持 stepwise verification 与 agent-agnostic interactive environment。
- 对 RWB：
  - **直接借鉴**：Stepwise verification；
  - **关键观察**：当前 Agent 对结构明确任务更可靠，对 open-ended exploration / novel insight 仍明显不足，支持 RWB 的 Atomic Task 与 Human Gate 路线。

## 7.4 SciAgentGym

- 来源：<https://arxiv.org/abs/2602.12984>
- 定位：1780 个 domain-specific tools，专门评估 multi-step scientific tool use。
- 对 RWB：
  - **直接借鉴**：Tool-chain horizon 是独立风险维度；
  - **直接借鉴**：长链任务优先拆 Atomic Task，不应假设“更多工具调用=更强 Agent”。

## 7.5 Autonomous Research Agents: Verification Gap Survey

- 来源：<https://arxiv.org/abs/2608.05179>
- 定位：系统审计 autonomous research agents 的 autonomy、artifacts、HITL、novelty verification、execution traces 等。
- 核心意义：科研 Agent 的瓶颈正在从“能不能生成结果”转向“reviewer 能不能验证 Claim”。
- 对 RWB：
  - **直接借鉴**：Trace 必须从 observability 提升为核心科研语义；
  - **直接借鉴**：Evidence–Claim–Trace–Decision 应形成统一闭环。

---

# 8. 本轮外部生态结论

## 8.1 不值得 RWB 正面竞争的领域

- 通用 Agent loop；
- Provider abstraction；
- 多 Agent orchestration；
- 大规模 scientific tool collection；
- 通用 literature retrieval；
- generic paper writing；
- 单一领域大而全 environment。

## 8.2 值得形成 RWB 差异化的领域

1. Method-aware routing；
2. Mode → Action → Method Obligation → Minimal Mechanism；
3. Skill Need resolution；
4. Skill 的 evaluation-driven lifecycle；
5. Evidence–Claim admissibility / composition；
6. Human scientific authority；
7. Long-lived Research State；
8. Failure / Unknown / Contradiction 的持续积累；
9. Cross-runtime reproducible research contract；
10. Reviewer-facing Trace / Verification。

## 8.3 建议长期跟踪的高优先级项目

**Tier A：直接架构参照**

- FAROS
- ToolUniverse
- PaperQA2
- K-Dense Scientific Agent Skills
- CASCADE / SkillFoundry
- AgentRxiv
- AstaBench / SciAgentArena
- Verification Gap survey / follow-up work

**Tier B：策略与未来能力参照**

- Google AI Co-Scientist
- OR-Agent
- AutoScientists
- AI Scientist v2
- STORM / Co-STORM
- Elicit
- Biomni

**Tier C：适合作为 Adapter / Tool Source**

- Zotero MCP
- paper-search-mcp
- Paper2Agent generated MCPs
- 其他 Scientific MCP / CLI / database providers
