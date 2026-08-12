# Research Agent Workbench

一个由研究者主导、按研究活动组合、以证据和可复现性为中心的 AI 科研辅助框架。

本项目不是“自动课题组”，也不试图重新实现 Codex、Claude Code 或其他平台已有的子 Agent 调度。它提供的是平台之上的轻量科研契约层：把研究问题、研究模式、Agent 边界、Skill 选择、工件、证据、交接与人工决策组织成可审查、可替换的结构。

## 当前状态

状态：`M3 Context/Receipt + M6 Provider Adapter Foundation`

当前仓库已完成 M1 的本地实现和 M2 的离线 Agent—Skill 契约切片，并开始实现 M3：提供可恢复 Main State、Context Snapshot、Execution Receipt，以及上下文压力、协调成本、并发、复核循环和敏感 trace 检查。Skill 供应链现具备只读 ZIP 静态审计、18/18 来源入口追溯和非发现候选实验区；首个 `claim-preserving-rewrite` 候选尚未准入。另已实现 OpenAI Responses、Anthropic Messages、Gemini `generateContent` 的非流式薄 Adapter、ToolChoice、本地工具参数校验，以及默认零环境/零网络的 live conformance runner；但尚未用真实账户/模型执行 conformance。项目仍无数据库、Web UI 或自建调度器；真实原生子 Agent 和真实科研案例仍待执行。

## 核心判断

- 主 Agent 是决策工作区，不是长期存储，也不是所有工作的执行者。
- 子 Agent 只接收窄任务；其过程可以被压缩，但正式工件和交接契约不能丢失。
- Agent Profile、Skill、Research Mode 和 Tool 是四个不同概念，必须在单次 Task Packet 中显式组合。
- 不同子 Agent 应按任务加载不同 Skill；关键任务不能只依赖模型的隐式 Skill 匹配。
- 研究差异按实验、仿真、推导、观察统计、证据综合等“研究模式”表达，不按学科建立全局固定流程。
- 确定性校验优先于第二个 Agent；Agent 复核只针对明确风险；关键科学判断保留给人。
- 优先使用平台原生的 Agent、Skill、线程、权限和工具能力，不另造通用 Supervisor。

## 架构入口

- [项目章程](docs/PROJECT_CHARTER.md)
- [总体架构](docs/ARCHITECTURE.md)
- [完整实施计划](docs/implementation/IMPLEMENTATION_PLAN.md)
- [任务清单](docs/TASKS.md)
- [模块文档索引](docs/modules/README.md)
- [迁移方案](docs/implementation/MIGRATION_PLAN.md)
- [Skill 候选准入流程](docs/implementation/SKILL_CANDIDATE_PIPELINE.md)
- [模型 API 中立端口 ADR](docs/decisions/0003-PROVIDER-NEUTRAL-MODEL-PORT.md)
- [多提供商模型 API 实施计划](docs/implementation/PROVIDER_ADAPTER_PLAN.md)
- [薄 Adapter 与凭据边界 ADR](docs/decisions/0007-THIN-PROVIDER-ADAPTERS.md)
- [上下文与执行收据 ADR](docs/decisions/0006-CONTEXT-AND-EXECUTION-RECEIPTS.md)

## 当前可执行入口

```powershell
python -m pip install -e .
rwb validate examples registry
rwb schema list
rwb task resolve examples/task-evidence.yaml `
  --profile registry/agents/evidence-scout.yaml `
  --registry registry/skills/accepted.json
rwb skills accepted --root .
rwb runtime codex validate --root .
rwb runtime codex render examples/task-evidence.yaml `
  --profile registry/agents/evidence-scout.yaml `
  --root .
rwb handoff validate examples/handoff-evidence.yaml `
  --task examples/task-evidence.yaml
rwb claim trace examples/objects/claim/CLAIM-001.yaml `
  --protocol examples/project-protocol.yaml
rwb skills candidates --status triage
rwb skills audit-archive <archive-path> `
  --source-id research-copilot-archive-1.0.0 `
  --expected-sha256 c69471fdec7164595b5d28a613a5421d549472585d8ace0f89b745b801ebe940 `
  --registry registry/skills/candidates.json
rwb providers list
rwb providers probe --config registry/providers/adapters.yaml
rwb providers conformance --adapter openai-responses
rwb context assess --id CTX-001 `
  --protocol examples/project-protocol.yaml --scope main `
  --metric loaded_chars=25000 --output work/CTX-001.yaml
rwb context resume-check examples/main-state.yaml `
  --protocol examples/project-protocol.yaml --root .
rwb execution assess examples/observability/execution-evidence-contract.yaml `
  --protocol examples/project-protocol.yaml --root .
```

`validate` 会检查 Schema、实际文件、SHA-256 与 Registry 引用等机器可判定条件，但不代表科学正确性。`task resolve` 只生成固定的 Profile/Skill/权限执行视图，不启动 Agent；`runtime codex render` 只生成原生 dispatch prompt，也不启动自建运行时。`skills audit-archive` 只在 ZIP 内做有界静态文本扫描，不解压、不执行、不联网，也不保存正文或命中片段。`context assess` 的字符/回合等数据是压力代理，不是假装精确的 token 窗口；缺失指标会明确标为 unknown。外部 Skill 默认不可执行；`discovered`、`triage`、`reference` 和 `quarantine` 均不等于已安装或已准入。

## 第一条验证路线

首个离线契约切片已验证两个能力差异明显的子 Agent 配置：

1. `evidence-scout` + `literature-evidence-extraction` Skill：源材料只读、任务区受限写的检索、证据定位和引用交接。
2. `simulation-auditor` + `simulation-vv` Skill：读取模型与运行工件，检查版本、参数、收敛和敏感性。

两者共享最小科研内核与 Task/Handoff 契约，但使用不同的输入、权限、Skill、输出和质量检查。离线证据见 [双 Skill 契约切片](examples/vertical-slice/SLICE_REPORT.md)。该切片只证明绑定、隔离与校验可重放，不证明多 Agent 更强；后续仍需两个真实原生子 Agent 执行和单 Agent 对照。

## 近期交付边界

当前近期交付边界：

- 最小 Schema 与确定性验证器；
- 一个本地 CLI；
- Codex 优先的 Runtime Adapter；
- 四个 Agent Profile、三个仓库级 Skill 与 accepted Registry；
- 主状态包、Task Packet 和 Handoff Packet；
- Context Snapshot 与 Execution Receipt；
- 无数据库、无常驻 Supervisor、无全局自治 DAG。

## 参考方向

设计借鉴但不复制以下项目的边界：

- [Codex Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)：使用原生子 Agent，将噪声工作移出主线程。
- [Codex Build Skills](https://learn.chatgpt.com/docs/build-skills)：使用可渐进加载的仓库级 Skills。
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)：参考结构化 handoff、guardrail 与 tracing 的职责分离。
- [STORM / Co-STORM](https://github.com/stanford-oval/storm)：参考多视角知识整理与人机协作，但不把文章生成等同于科研闭环。
- [PaperQA2](https://github.com/Future-House/paper-qa)：参考带定位引用的科学文献证据检索。
- [LangGraph](https://github.com/langchain-ai/langgraph)：参考持久执行与人工中断，不在首版引入通用图运行时。
- [DVC](https://github.com/treeverse/dvc)：在确有大数据/实验版本需求时接入，不自行重造数据版本系统。

## 名称说明

`Research Agent Workbench` 是工作名。它强调“研究工作台”而不是“自治科研系统”，以免产品目标被误解为将选题、实验解释和结论责任全盘交给模型。
