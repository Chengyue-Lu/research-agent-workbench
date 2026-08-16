# 实施任务清单

状态：`DONE / IN_PROGRESS / READY / BLOCKED / PARKED / EXTERNAL`

当前责任人：路诚钺维护 M2/M7 的 Mode–Skill、读取、Handoff 与 Trace 评估；黄毅维护 M6 的 API 执行实现与测试。共享接口变更按[开发协作指南](DEVELOPMENT.md)由两人共同确认。

## M0：架构与仓库

| ID | 状态 | 任务 | 验收 |
|---|---|---|---|
| M0-001 | DONE | 冻结产品定位与非目标 | Project Charter 完成 |
| M0-002 | DONE | 确立总体架构与模块边界 | 总架构 + 10 模块文件 |
| M0-003 | DONE | 将不同 Agent—Skill 绑定纳入架构 | Resolver、Assignment、预警与验收明确 |
| M0-004 | DONE | 建立实施、迁移与测试计划 | 三份实施文档完成 |
| M0-005 | DONE | 创建并推送独立 GitHub 仓库 | `main` 可访问，首次提交完成 |
| M0-006 | DONE | 建立零基础使用与发布就绪度指南 | 安装、离线 quickstart、真实运行边界、故障处理和分级发布 Gate 可由新用户顺序阅读 |
| M0-007 | BLOCKED | 选择项目许可证并核对仓库原创 Skills 的许可状态 | 人类维护者确定发布许可后加入 LICENSE，并消除 `project-original-unlicensed` 发布阻断 |

## M1：契约与 CLI

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M1-001 | DONE | 初始化 Python 包、pyproject 和基础 CI | M0 | 已合并 `main`；Python 3.11/3.13 GitHub CI 通过 |
| M1-002 | DONE | 实现核心对象模型与 JSON Schema | M1-001 | 7 类对象正反 fixture 通过 Draft 2020-12 Schema |
| M1-003 | DONE | 实现 Protocol、Mode、Profile、Skill Manifest | M1-002 | 能力、工具、输出、模式、冲突和 scoped permission 可验证 |
| M1-004 | DONE | 实现 Task、Attempt、Handoff、Main State | M1-002 | completed/incomplete Handoff、Attempt 与 checkpoint 示例通过 |
| M1-005 | DONE | 实现引用、revision、SHA-256 和 stale 检查 | M1-002 | 修改输入触发 `REF-HASH-MISMATCH`，input lock 不同触发 stale |
| M1-006 | DONE | 实现最小 CLI | M1-003..005 | init/validate/resolve/handoff/trace/checkpoint 可用 |
| M1-007 | DONE | 建立确定性风险检查 | M1-004..006 | Skill 缺失、越权、写冲突、Claim overreach、stale 注入均阻断 |
| M1-008 | DONE | 冻结模型 API 中立端口与能力协商语义 | M1-001 | Capability/Data Policy gap 在调用前阻断，提供商基线可查询 |
| M1-009 | READY | 建立外部可复用项目 scaffold 与 `0.x` 兼容政策 | M1-006 | `rwb init` 可生成或选择完整模板；新项目不需手工复制 Registry/Profiles/Skills；Schema/CLI 迁移与废弃规则明确 |

## M2：Agent 与 Skills

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M2-001 | DONE | 实现 Skill Registry 与 Resolver | M1 | accepted Registry、最小覆盖、显式选择、冲突、权限交集、版本/哈希锁与确定性 Assignment 已测试 |
| M2-002 | DONE | 定义四个 Agent Profiles | M2-001 | coordinator/evidence/simulation/reviewer 的权限、工具、输出和上下文边界可验证 |
| M2-003 | IN_PROGRESS | 创建 literature-evidence-extraction Skill | M2-001 | 结构、正例、stale source 和 dispatch 注入隔离通过；真实 Agent 前向测试待执行 |
| M2-004 | IN_PROGRESS | 创建 simulation-vv Skill | M2-001 | V&V 结构、版本锁和 Claim ceiling 正反例通过；真实数值案例待执行 |
| M2-005 | DONE | 创建 handoff-integrity 检查 | M1 | 确定性脚本已验证 Task/input/Skill/artifact 交接边界，不宣称科学正确性 |
| M2-006 | PARKED | 扩展 Codex Runtime Adapter | M2-002..005 | 已有 Agent/Skill 发现、验证和显式 dispatch 保留；平台 launch/collect 不在当前 Mode–Skill 关键路径 |
| M2-007 | IN_PROGRESS | 执行首个双 Skill 垂直切片 | M7-002..006 | 离线契约切片已证明 Skills 不同；路诚钺先完成 Mode/Skill 选择、读取计划和 H1/H2 成本基线，真实执行证据由黄毅负责的执行工作流提供 |
| M2-008 | IN_PROGRESS | 建立外部 Skill 发现、隔离评估与准入 Registry | M1 | ZIP 审计、18/18 追溯、非发现候选和 provider-neutral 双臂评估契约/CLI 已落地；fixture 会被正确阻断，真实 with/without 与 trial/accepted 仍待完成 |

## M3：上下文与风险

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M3-001 | IN_PROGRESS | Main State checkpoint/resume | M1 | 规范化 digest、原子文件发布、Continuity 状态、机器证据哈希、Git 基线、下一动作和约束/决定丢失检查已通过；进程级 kill 矩阵与真实新主会话恢复待演练 |
| M3-002 | IN_PROGRESS | context pressure 与 AWU 预算 | M3-001 | 可测/未知指标、动态 next-AWU/closeout/reserve 判定、WARN/rollover/block 和 checkpoint 链已测试；真实运行估计误差待采集 |
| M3-003 | IN_PROGRESS | Handoff loss/stale/summary 抽查 | M2 | Transfer Manifest/Audit、负面区段覆盖、风险触发抽查、Context/Receipt 绑定已实现；真实 H1/H2 成本与人工样本仍待执行 |
| M3-004 | IN_PROGRESS | review loop/fanout/write race 检查 | M2 | 并发预算、review loop、协调成本与既有 write race 检查已落地；真实停止行为待验证 |
| M3-005 | IN_PROGRESS | 敏感 trace 策略 | M2 | 外部/完整/敏感 trace 会阻断或警告；真实脱敏器与密钥 fixture 待实现 |
| M3-006 | IN_PROGRESS | SAFE_PAUSE 与机器完成权 | M3-001..003 | AWU/完成/暂停条件、stage/safe-pause/waiting、执行结束与 `contract-satisfied` 分离、失败报告覆盖显式完成宣称和可恢复 pause fixture 已实现；真实 Task rollover 待演练 |
| M3-007 | DONE | 冻结实名 actor、Attempt Archive 与完整 Agent Trace 规则 | M3-003..006 | ADR-0012、目录、消息信封、写前捕获、capture gap、按需读取和 Worklog 关系已冻结；负责人明确为路诚钺/黄毅 |
| M3-008 | DONE | 实现 Trace Envelope/Index/Event Schema、validator 与 fixture | M3-007 | Schema/validator/CLI 与正反 fixture 已能检测 message/event sequence、hash、actor owner、capture gap、未声明删减、越界正文/工具、瞬时结果丢失和过程产物覆盖；不保存 Chain-of-Thought |

## M4：工件与复现

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M4-001 | READY | source admission 与 provenance | M1 | inbox 不可直接引用 |
| M4-002 | READY | work → object/run promotion | M1 | 只有校验通过可提升 |
| M4-003 | READY | Claim trace 与 counterevidence | M1 | 支持/反证/限制一次定位 |
| M4-004 | READY | Run manifest 与复现检查 | M2 | 仿真案例可重建 |
| M4-005 | PARKED | DVC 技术 spike | 真实大文件需求 | 无需求则不启动 |

## M5：真实案例与删减

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M5-001 | BLOCKED | 选定证据综合真实案例 | 人类提供/批准边界 | 问题、来源、数据边界明确 |
| M5-002 | BLOCKED | 选定理论+仿真实际案例 | 人类提供/批准边界 | 模型、参数、Claim ceiling 明确 |
| M5-003 | READY | 建立单 Agent/轻量/多 Agent 对照 | M2..M4 | 指标与评估表固定 |
| M5-004 | READY | 运行案例并分析净收益 | M5-001..003 | 质量、上下文、成本数据完整 |
| M5-005 | READY | 里程碑删减评审 | M5-004 | 至少做出一项保留/删除/停止决定 |

## M6：API Execution（黄毅维护）

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M6-001 | EXTERNAL | OpenAI/Anthropic/Gemini/Zhipu 薄 Model Provider Adapters | M1-008 | 黄毅维护；Zhipu 标准 API 当前仅 text/structured 离线合同通过，tools/live 仍 pending；路诚钺不修改实现或测试 |
| M6-002 | DONE | 显式模型池与隔离 API session kernel（`K-API-1`） | M6-001 | primary/worker/specialist 槽只可显式绑定；轮次、工具、并行、工具结果、输出、token/成本/time 有硬边界；无自动 fallback；离线测试通过 |
| M6-003 | IN_PROGRESS | Task-to-API 文件闭环（`K-API-2`） | M1-008, M2-001..005, M6-002 | evidence/H2 与 simulation/H1 双合同路径已离线通过：受控 Tool Registry、Model Assignment、五终态、commit-last、自动诚实 gapped Trace 与 H1/H2 fresh-process 恢复均有 fake-local 证据；节点仍等待 M6-004 真实 OpenAI Gate，不声称科研正确性 |
| M6-004 | EXTERNAL | 选定模型槽的真实 Windows conformance 与一次 evidence 调用 | M6-001..003 | 待黄毅在授权环境执行并返回脱敏工件；当前机器缺少 `OPENAI_API_KEY` 和 `RWB_WORKER_MODEL`，状态为 pending/not-run，不得伪造通过 |
| M6-005 | PARKED | streaming/multimodal/server tools 与平台 Adapter | 真实案例或平台选择 | 黄毅决定执行端启动条件；没有真实需求不启动 |
| M6-006 | DONE | API/平台执行时自动写入 Agent Trace | M3-008, M6-003 | 执行边界已自动生成 validator-compatible Trace；不可得捕获显式记为 gap 而不伪装 complete，密钥、provider response ID、正文与隐藏推理不入 Trace |

## M7：Mode–Skill 选择与协调成本

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M7-001 | DONE | 冻结实名 owner、受控读取与分级 Handoff 文档策略 | M2, M3 | 路诚钺/黄毅职责、ADR-0011/0012、架构图和开发入口一致 |
| M7-002 | IN_PROGRESS | 建立现有 Mode 决策卡与边界 fixtures | M1-003 | evidence/simulation 具有 trigger、non-trigger、组合、歧义和 no-Mode 样本 |
| M7-003 | READY | 建立 Task-to-Skill 选择矩阵 | M2-001 | 可解释 no-Skill、accepted Skill、拆 Task 和 Human Gate；排除理由可重放 |
| M7-004 | READY | 审计三个 accepted Skills 的 trigger/non-trigger | M7-002..003 | 每个 Skill 有适用、边界、不适用和删除条件 |
| M7-005 | READY | 对一个 triage candidate 作证据化去留决定 | M2-008, M7-003 | 产出 reject/retain-reference/continue-trial，不自动 accepted |
| M7-006 | READY | 建立 H0/H1/H2 与内容读取成本对照 | M3-008, M7-002 | 通过 Attempt Archive 记录消息/工件数、字符、审阅、回查、遗漏、返工、读取扩展和 capture gap |
| M7-007 | PARKED | 新增 experiment/theory/observational/engineering Mode | 真实案例 + Mode 准入卡 | 证明现有 Mode 组合不足后逐个启用 |

## GitHub 执行入口

M1 已建立里程碑与首批可执行 Issues：

- [#1 M1-001 Bootstrap Python package and CI](https://github.com/Chengyue-Lu/research-agent-workbench/issues/1)
- [#2 M1-002 Implement the minimal research object schemas](https://github.com/Chengyue-Lu/research-agent-workbench/issues/2)
- [#3 M1-003 Implement protocol, mode, agent, and skill manifests](https://github.com/Chengyue-Lu/research-agent-workbench/issues/3)
- [#4 M1-004 Implement task, handoff, main state, and reference integrity](https://github.com/Chengyue-Lu/research-agent-workbench/issues/4)
- [#5 M1-005 Build the minimal CLI and deterministic risk checks](https://github.com/Chengyue-Lu/research-agent-workbench/issues/5)
- [#6 M1-008 Freeze provider-neutral model API port](https://github.com/Chengyue-Lu/research-agent-workbench/issues/6)
- [#7 M2-008 Audit and admit external Skill candidates](https://github.com/Chengyue-Lu/research-agent-workbench/issues/7)

## 当前下一任务

路诚钺的 `K-MS-1` 实现不属于当前 API 分支。本分支只保留共享 Task/Handoff/Trace/Receipt 接口；Mode 决策卡、Task-to-Skill 选择、Skill 审计与 Handoff 成本对照仍按 `M7-002..006` 由其独立工作流推进。黄毅不在本分支补写或宣称完成这些工件。

`M6-003` 的 evidence/H2 与 simulation/H1 双合同、受控 Tool Registry、Model Assignment、自动诚实 gapped Trace 与 fresh-process/commit-last 已有离线证据；`M6-006` 因此已完成。`M6-003` 仍为 `IN_PROGRESS`，唯一未跑的 API Gate 是 `M6-004` 真实 OpenAI 调用；当前机器缺少 `OPENAI_API_KEY` 和 `RWB_WORKER_MODEL`，必须保持 `EXTERNAL`/pending。
