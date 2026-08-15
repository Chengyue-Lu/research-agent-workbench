# Research Agent Workbench

一个由研究者主导、按研究活动组合、以证据和可复现性为中心的 AI 科研辅助框架。

本项目不是“自动课题组”，也不试图重新实现 Codex、Claude Code 或其他平台已有的子 Agent 调度。它提供的是平台之上的轻量科研契约层：把研究问题、研究模式、Agent 边界、Skill 选择、工件、证据、交接与人工决策组织成可审查、可替换的结构。

## 当前状态

状态：`K-API-2 Offline Minimal File Loop Gate Passed`（仍停在 `M6-004` 授权门前）

当前仓库已完成 M1 的核心本地契约、M2 的离线 Agent—Skill 切片和 M3 的首批文件式连续性，并通过 `K-API-2` 的最小离线节点评审：`EVID-001` 的冻结合同、选定 Skill 和显式 `worker` 槽可编译为 fresh API session；fake-local Provider 可走 completed/tool-failed/safe-paused/incomplete/stale-input 路径；commit-last closeout 最后发布 Main State；删除内存 transcript 后可由 fresh Python subprocess 以 Main State 为入口，在 Protocol 与哈希锁定的项目文件树中恢复。该 PASS 不包含真实 API、真实 Windows 槽、真实主 Agent 会话、科学正确性或多 Agent 净收益；未经维护者明确授权，不得自动进入 `M6-004`。

## 核心判断

- 主 Agent 是决策工作区，不是长期存储，也不是所有工作的执行者。
- 子 Agent 只接收窄任务；其过程可以被压缩，但正式工件和交接契约不能丢失。
- Agent Profile、Skill、Research Mode 和 Tool 是四个不同概念，必须在单次 Task Packet 中显式组合。
- 不同子 Agent 应按任务加载不同 Skill；关键任务不能只依赖模型的隐式 Skill 匹配。
- 研究差异按实验、仿真、推导、观察统计、证据综合等“研究模式”表达，不按学科建立全局固定流程。
- 确定性校验优先于第二个 Agent；Agent 复核只针对明确风险；关键科学判断保留给人。
- 纯 API fresh session 是可移植执行基线；平台原生 Agent/线程是可选便利层，不另造通用 Supervisor。
- 模型只按 `primary`、`worker` 和少量 `specialist` 槽显式绑定，不建设复杂自动 Router。

## 架构入口

- [零基础使用指南与发布就绪度](docs/GETTING_STARTED.md)
- [项目章程](docs/PROJECT_CHARTER.md)
- [总体架构](docs/ARCHITECTURE.md)
- [完整实施计划](docs/implementation/IMPLEMENTATION_PLAN.md)
- [任务清单](docs/TASKS.md)
- [恢复点与下一步](docs/NEXT_STEPS.md)
- [当前开发 Handoff](docs/CURRENT_HANDOFF.md)
- [Changelog](CHANGELOG.md)
- [模块文档索引](docs/modules/README.md)
- [迁移方案](docs/implementation/MIGRATION_PLAN.md)
- [Skill 候选准入流程](docs/implementation/SKILL_CANDIDATE_PIPELINE.md)
- [Skill 双臂评估协议](docs/implementation/SKILL_EVALUATION_PROTOCOL.md)
- [模型 API 中立端口 ADR](docs/decisions/0003-PROVIDER-NEUTRAL-MODEL-PORT.md)
- [多提供商模型 API 实施计划](docs/implementation/PROVIDER_ADAPTER_PLAN.md)
- [薄 Adapter 与凭据边界 ADR](docs/decisions/0007-THIN-PROVIDER-ADAPTERS.md)
- [API-first 隔离执行 ADR](docs/decisions/0010-API-FIRST-ISOLATED-EXECUTION.md)
- [上下文与执行收据 ADR](docs/decisions/0006-CONTEXT-AND-EXECUTION-RECEIPTS.md)
- [Handoff Transfer Audit ADR](docs/decisions/0008-HANDOFF-TRANSFER-AUDIT.md)
- [文件式连续性与 SAFE_PAUSE ADR](docs/decisions/0009-FILE-FIRST-CONTINUITY-AND-SAFE-PAUSE.md)
- [CCRML 会议吸收与差距审计](docs/references/CCRML_MEETING_ADOPTION.md)

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

`validate` 会检查 Schema、实际文件、SHA-256 与 Registry 引用等机器可判定条件，但不代表科学正确性。`handoff audit-transfer` 的 `structurally-ready` 只表示条目和引用覆盖，不表示语义等价；关键风险或 Task policy 会要求独立人工抽查。`task resolve` 和 `runtime codex render` 不启动 Agent。`skills audit-archive` 不解压、不执行、不联网；`skills eval assess` 不自动准入候选。`context assess` 的字符/回合是压力代理；只有同单位的 `remaining >= next atomic + closeout + safety margin` 才支持继续一个 AWU。外部 Skill 的 `discovered`、`triage`、`reference` 和 `quarantine` 均不等于已安装或已准入。

`K-API-2` 当前没有新增 CLI 命令；最窄入口是 Python API `research_workbench.execution.run_task_api_attempt`，可复现用法和 fake-local fixtures 见 `tests/test_k_api_2_pipeline.py`。单轮 tool-call fan-out 有上限，但 handler 当前串行；token/成本和 wall-time 是调用边界/响应后 guard，不能取消 in-flight 调用。`completed` 证明结构、引用、哈希与文件 closeout 合同成立，但通用路径尚未强制证明 Provider 一定调用了 `document-read`。

## 第一条验证路线

首个离线契约切片已验证两个能力差异明显的子 Agent 配置：

1. `evidence-scout` + `literature-evidence-extraction` Skill：源材料只读、任务区受限写的检索、证据定位和引用交接。
2. `simulation-auditor` + `simulation-vv` Skill：读取模型与运行工件，检查版本、参数、收敛和敏感性。

两者共享最小科研内核与 Task/Handoff 契约，但使用不同的输入、权限、Skill、输出和质量检查。离线证据见 [双 Skill 契约切片](examples/vertical-slice/SLICE_REPORT.md)。evidence 的 fake-local API 文件闭环现已通过，但仍只证明合成输入下的绑定、隔离、关闭和文件恢复；simulation、平台路径和真实案例对照须等 K-API-2 节点评审后另行授权。

## 近期交付边界

当前近期交付边界：

- 最小 Schema 与确定性验证器；
- 一个本地 CLI；
- 纯 API 隔离会话内核与显式模型槽；
- `EVID-001` 的可信编译、严格输出验证、commit-last closeout 与防重放 intent；
- 可选的 Codex Runtime Adapter 映射；
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
