# 实施任务清单

状态：`DONE / IN_PROGRESS / READY / BLOCKED / PARKED`

## M0：架构与仓库

| ID | 状态 | 任务 | 验收 |
|---|---|---|---|
| M0-001 | DONE | 冻结产品定位与非目标 | Project Charter 完成 |
| M0-002 | DONE | 确立总体架构与模块边界 | 总架构 + 10 模块文件 |
| M0-003 | DONE | 将不同 Agent—Skill 绑定纳入架构 | Resolver、Assignment、预警与验收明确 |
| M0-004 | DONE | 建立实施、迁移与测试计划 | 三份实施文档完成 |
| M0-005 | DONE | 创建并推送独立 GitHub 仓库 | `main` 可访问，首次提交完成 |

## M1：契约与 CLI

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M1-001 | IN_PROGRESS | 初始化 Python 包、pyproject 和基础 CI | M0 | 功能分支已推送；工作流仅监听 `main`/PR，等待进入 PR 后的 GitHub CI |
| M1-002 | DONE | 实现核心对象模型与 JSON Schema | M1-001 | 7 类对象正反 fixture 通过 Draft 2020-12 Schema |
| M1-003 | DONE | 实现 Protocol、Mode、Profile、Skill Manifest | M1-002 | 能力、工具、输出、模式、冲突和 scoped permission 可验证 |
| M1-004 | DONE | 实现 Task、Attempt、Handoff、Main State | M1-002 | completed/incomplete Handoff、Attempt 与 checkpoint 示例通过 |
| M1-005 | DONE | 实现引用、revision、SHA-256 和 stale 检查 | M1-002 | 修改输入触发 `REF-HASH-MISMATCH`，input lock 不同触发 stale |
| M1-006 | DONE | 实现最小 CLI | M1-003..005 | init/validate/resolve/handoff/trace/checkpoint 可用 |
| M1-007 | DONE | 建立确定性风险检查 | M1-004..006 | Skill 缺失、越权、写冲突、Claim overreach、stale 注入均阻断 |
| M1-008 | DONE | 冻结模型 API 中立端口与能力协商语义 | M1-001 | Capability/Data Policy gap 在调用前阻断，提供商基线可查询 |

## M2：Agent 与 Skills

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M2-001 | DONE | 实现 Skill Registry 与 Resolver | M1 | accepted Registry、最小覆盖、显式选择、冲突、权限交集、版本/哈希锁与确定性 Assignment 已测试 |
| M2-002 | DONE | 定义四个 Agent Profiles | M2-001 | coordinator/evidence/simulation/reviewer 的权限、工具、输出和上下文边界可验证 |
| M2-003 | IN_PROGRESS | 创建 literature-evidence-extraction Skill | M2-001 | 结构、正例、stale source 和 dispatch 注入隔离通过；真实 Agent 前向测试待执行 |
| M2-004 | IN_PROGRESS | 创建 simulation-vv Skill | M2-001 | V&V 结构、版本锁和 Claim ceiling 正反例通过；真实数值案例待执行 |
| M2-005 | DONE | 创建 handoff-integrity 检查 | M1 | 确定性脚本已验证 Task/input/Skill/artifact 交接边界，不宣称科学正确性 |
| M2-006 | IN_PROGRESS | 实现 Codex Runtime Adapter | M2-002..005 | 原生 Agent/Skill 发现、验证和显式 dispatch 已完成；launch/collect 仍使用平台原生会话、待真实演练 |
| M2-007 | IN_PROGRESS | 执行首个双 Skill 垂直切片 | M2-006 | 离线契约切片已证明 Skills 不同且原始资料不进入 dispatch；两次真实原生执行待完成 |
| M2-008 | IN_PROGRESS | 建立外部 Skill 发现、隔离评估与准入 Registry | M1 | ZIP 只读审计器、18/18 入口追溯和非发现派生候选已落地；Claim 表层漂移 fixtures 通过，真实 with/without 与 trial/accepted 仍待完成 |

## M3：上下文与风险

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M3-001 | IN_PROGRESS | Main State checkpoint/resume | M1 | 规范化 digest、前序引用、协议 revision、下一动作和约束/决定丢失检查已通过；真实新主会话恢复待演练 |
| M3-002 | IN_PROGRESS | context pressure 代理指标 | M3-001 | 可测/未知指标、阈值、WARN/rollover/block 和 checkpoint 链已测试；真实运行指标待采集 |
| M3-003 | IN_PROGRESS | Handoff loss/stale/summary 抽查 | M2 | 未固化 Handoff 的子 Agent 压缩会阻断；摘要失真抽查仍待实现 |
| M3-004 | IN_PROGRESS | review loop/fanout/write race 检查 | M2 | 并发预算、review loop、协调成本与既有 write race 检查已落地；真实停止行为待验证 |
| M3-005 | IN_PROGRESS | 敏感 trace 策略 | M2 | 外部/完整/敏感 trace 会阻断或警告；真实脱敏器与密钥 fixture 待实现 |

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

## M6：按真实需求扩展

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M6-001 | IN_PROGRESS | OpenAI/Anthropic/Gemini 薄 Model Provider Adapters | M1-008 | 端口、ToolChoice、本地工具参数校验、HTTPS Transport 与离线合同已通过；有硬预算和脱敏报告的 live runner 已完成，每家一个模型的真实 Windows 执行待完成 |
| M6-002 | READY | 有预算的 client-tool loop runner | M6-001, 真实消费者 | 轮次、调用、并行、工具输出、token/成本/time 均有硬上限；不自动跨提供商 fallback |
| M6-003 | PARKED | streaming/multimodal/server tools | 真实案例需求 | 每项独立 capability、data policy、合同与删除条件，不批量铺开 |

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

当前功能分支已推送，M1 本地功能完成；`M1-001` 等待 PR/main 触发 GitHub CI。M2 的 accepted Registry、四个 Profile、三个仓库级 Skills 和 Codex 原生配置映射已落地。M3 已具备 Context Snapshot、Execution Receipt、checkpoint/resume 和首批故障注入。M6-001 的三家 API Adapter、ToolChoice、本地工具参数校验和脱敏 live conformance runner 已完成；下一步由用户在真实 Windows 授权上下文执行每家一个模型，不在 Codex 沙箱内读取令牌或据此判断认证。之后仍需平台原生子 Agent 各执行一次 evidence/simulation Task，把实际 Handoff、上下文与成本写入同一收据。`M2-008` 已完成首个 ZIP 的 18/18 入口审计，并建立非发现的 `claim-preserving-rewrite` 派生候选及正反 fixtures；下一步是真实 with/without 前向测试、误报分析和继续审查外部来源，不安装原始候选。`M5-001` 和 `M5-002` 保持阻塞，直到人类选择真实案例；不以虚构课题替代真实验证。
