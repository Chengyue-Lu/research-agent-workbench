# Research Agent Workbench

一个由研究者主导、按研究活动组合、以证据和可复现性为中心的 AI 科研辅助框架。

本项目不是“自动课题组”，也不试图重新实现 Codex、Claude Code 或其他平台已有的子 Agent 调度。它提供的是平台之上的方法感知科研控制平面：让研究语义、状态、证据、失败与决定长期保存，同时允许 Model、Runtime、Tool、Skill 和执行策略替换。

## 项目阶段

当前为内部技术 alpha：独立集成分支已把 Mode Action、Method Resolution、Mode v0.2、Decision Authority、Resolved Capability Snapshot 与 `K-API-2` strict file loop 串成首个离线闭环；双方审查和 live conformance 前不视为主线稳定能力。逐项状态和唯一下一节点以[任务清单](docs/TASKS.md)为准。

## 核心判断

- 主 Agent 是决策工作区，不是长期存储，也不是所有工作的执行者。
- 子 Agent 只接收窄任务；其过程可以被压缩，但正式工件和交接契约不能丢失。
- Agent Profile、Skill、Research Mode 和 Tool 是四个不同概念，必须在单次 Task Packet 中显式组合。
- Mode、Protocol、Strategy、Skill、Tool 和 Capability 是正交概念；Method Resolution 解释最小机制，Resolved Capability Snapshot 冻结具体执行绑定。
- Research State 的生命周期长于任何 Agent 会话、模型、Runtime、Tool 或 Skill；聊天不是长期事实源。
- 不同子 Agent 应按任务加载不同 Skill；关键任务不能只依赖模型的隐式 Skill 匹配。
- 研究差异按实验、仿真、推导、观察统计、证据综合等“研究模式”表达，不按学科建立全局固定流程。
- 确定性校验优先于第二个 Agent；Agent 复核只针对明确风险；关键科学判断保留给人。
- 纯 API fresh session 是可移植执行基线；平台原生 Agent/线程是可选便利层，不另造通用 Supervisor。
- 模型只按 `primary`、`worker` 和少量 `specialist` 槽显式绑定，不建设复杂自动 Router。
- Agent 对文件内容采用任务级允许集；可以先发现路径元数据，但不能因为拥有工作区权限就递归读取无关文档。
- 普通委派默认只返回 Compact Handoff；完整 Manifest/Audit/Receipt 由风险、压缩、外部副作用或明确策略触发。
- 所有 Agent 间实际传递的可见内容，以及运行时可观察的读取、工具、命令和文件 revision 进入 Attempt Archive；主 Agent 默认只读取索引与 Handoff，完整 Trace 仅在评估或排障时按需回放。

## 文档入口

- [文档导航](docs/README.md)：按使用目的给出最小阅读集，避免遍历全部文档。
- [开发协作指南](docs/DEVELOPMENT.md)：实名责任、当前节点、分支、读取与完整 Trace 规则。
- [项目章程](docs/PROJECT_CHARTER.md)：使命、非目标和人的最终责任。
- [总体架构](docs/ARCHITECTURE.md)：稳定关系、Mermaid 流程与架构不变量。
- [架构路线图](docs/ROADMAP.md)：Method/Core、Research State、Evaluation 与 Execution reintegration 的依赖和停止 Gate。
- [任务清单](docs/TASKS.md)：当前状态的唯一权威入口。
- [零基础使用指南](docs/GETTING_STARTED.md)：安装、离线演练与发布就绪度。
- [Changelog](CHANGELOG.md)：已经落地的变更。

模块、实施计划、ADR 和参考材料均从[文档导航](docs/README.md)按需进入。

## 当前可执行入口

```powershell
python -m pip install -e .
rwb validate examples registry
rwb schema list
rwb task resolve examples/task-evidence.yaml `
  --profile registry/agents/evidence-scout.yaml `
  --registry registry/skills/accepted.json `
  --historical-replay
rwb skills accepted --root .
rwb runtime codex validate --root .
rwb runtime codex render examples/task-evidence.yaml `
  --profile registry/agents/evidence-scout.yaml `
  --root . `
  --historical-replay
rwb handoff validate examples/handoff-evidence.yaml `
  --task examples/task-evidence.yaml
rwb handoff audit-transfer examples/handoff-transfer-audit-evidence.yaml `
  --root .
rwb claim trace examples/objects/claim/CLAIM-001.yaml `
  --protocol examples/project-protocol.yaml
rwb skills candidates --status triage
rwb skills audit-archive <archive-path> `
  --source-id research-copilot-archive-1.0.0 `
  --expected-sha256 c69471fdec7164595b5d28a613a5421d549472585d8ace0f89b745b801ebe940 `
  --registry registry/skills/candidates.json
rwb skills eval assess `
  examples/evals/claim-preserving-rewrite/fixture-evaluation.yaml `
  --root . --registry registry/skills/candidates.json
rwb providers list
rwb providers probe --config registry/providers/adapters.yaml
rwb providers conformance --adapter openai-responses
rwb models probe --config registry/models/pool.example.yaml
rwb context assess --id CTX-001 `
  --protocol examples/project-protocol.yaml --scope main `
  --metric loaded_chars=25000 `
  --context-budget-status estimated --context-budget-unit characters `
  --remaining-context 10000 --next-atomic-cost 4000 `
  --closeout-cost 800 --safety-margin 500 `
  --output work/CTX-001.yaml
rwb context resume-check examples/main-state.yaml `
  --protocol examples/project-protocol.yaml --root .
rwb context resume-check examples/continuity/main-state-safe-pause.yaml `
  --protocol examples/project-protocol.yaml --root .
rwb execution assess examples/observability/execution-evidence-contract.yaml `
  --protocol examples/project-protocol.yaml --root .
```

`task-evidence.yaml` 是锁定 `0.1.0` 原型的历史垂直切片，因此示例显式使用
`--historical-replay`。新 Assignment 默认只接受 accepted Registry 中的 `active` Skill；当前三个
原型均为 legacy/deprecated，不会因仍可回放而进入新任务。

`validate` 会检查 Schema、实际文件、SHA-256 与 Registry 引用等机器可判定条件，但不代表科学正确性。`handoff audit-transfer` 的 `structurally-ready` 只表示条目和引用覆盖，不表示语义等价；关键风险或 Task policy 会要求独立人工抽查。`task resolve` 和 `runtime codex render` 不启动 Agent。`skills audit-archive` 不解压、不执行、不联网；`skills eval assess` 不自动准入候选。`context assess` 的字符/回合是压力代理；只有同单位的 `remaining >= next atomic + closeout + safety margin` 才支持继续一个 AWU。外部 Skill 的 `discovered`、`triage`、`reference` 和 `quarantine` 均不等于已安装或已准入。

## 第一条验证路线

首个离线契约切片已验证两个能力差异明显的子 Agent 配置：

1. `evidence-scout` + `literature-evidence-extraction` Skill：源材料只读、任务区受限写的检索、证据定位和引用交接。
2. `simulation-auditor` + `simulation-vv` Skill：读取模型与运行工件，检查版本、参数、收敛和敏感性。

两者共享最小科研内核与 Task/Handoff 契约，但使用不同的输入、权限、Skill、输出和质量检查。离线证据见 [双 Skill 契约切片](examples/vertical-slice/SLICE_REPORT.md)。该切片现在只作为历史绑定/隔离证据；两个 Skill 均非 active，也不证明多 Agent 更强。新的严格路径与合并边界见[Method-to-Execution 初版闭环](docs/implementation/METHOD_EXECUTION_LOOP.md)。

## 近期交付边界

当前近期交付边界：

- 最小 Schema 与确定性验证器；
- 一个本地 CLI；
- 纯 API 隔离会话内核与显式模型槽；
- 可选的 Codex Runtime Adapter 映射；
- 四个 Agent Profile、三个仓库级 Skill 与 accepted Registry；
- 主状态包、Task Packet 和 Handoff Packet；
- Context Snapshot 与 Execution Receipt；
- 无数据库、无常驻 Supervisor、无全局自治 DAG。

路诚钺的维护范围不包括 Provider Adapter、API session、真实模型 conformance 或 API 测试；实名边界见[开发协作指南](docs/DEVELOPMENT.md)。

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
