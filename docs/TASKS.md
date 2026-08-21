# 实施任务清单

状态：`DONE / IN_PROGRESS / READY / BLOCKED / PARKED`

当前责任人：路诚钺维护 Method/Core、Mode/Action、Skill Need/evaluation、Research State/Claim 与
Method Trace 语义；黄毅维护 M6 的 API/Runtime 执行实现与测试。共享接口变更按
[开发协作指南](DEVELOPMENT.md)进行独立架构审查。

## M0：架构与仓库

| ID | 状态 | Owner | 任务 | 验收 |
|---|---|---|---|---|
| M0-001 | DONE | 路诚钺 | 冻结产品定位与非目标 | Project Charter 完成 |
| M0-002 | DONE | 路诚钺 | 确立总体架构与模块边界 | 总架构 + 10 模块文件 |
| M0-003 | DONE | 路诚钺 | 将不同 Agent—Skill 绑定纳入架构 | Resolver、Assignment、预警与验收明确 |
| M0-004 | DONE | 路诚钺 | 建立实施、迁移与测试计划 | 三份实施文档完成 |
| M0-005 | DONE | 路诚钺 | 创建并推送独立 GitHub 仓库 | `main` 可访问，首次提交完成 |
| M0-006 | DONE | 路诚钺 | 建立零基础使用与发布就绪度指南 | 安装、离线 quickstart、真实运行边界、故障处理和分级发布 Gate 可由新用户顺序阅读 |
| M0-007 | BLOCKED | 双方维护者 | 选择项目许可证并核对仓库原创 Skills 的许可状态 | 人类维护者确定发布许可后加入 LICENSE，并消除 `project-original-unlicensed` 发布阻断 |

## M1：契约与 CLI

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M1-001 | DONE | 路诚钺 | 初始化 Python 包、pyproject 和基础 CI | M0 | 已合并 `main`；Python 3.11/3.13 GitHub CI 通过 |
| M1-002 | DONE | 路诚钺 | 实现核心对象模型与 JSON Schema | M1-001 | 7 类对象正反 fixture 通过 Draft 2020-12 Schema |
| M1-003 | DONE | 路诚钺 | 实现 Protocol、Mode、Profile、Skill Manifest | M1-002 | 能力、工具、输出、模式、冲突和 scoped permission 可验证 |
| M1-004 | DONE | 路诚钺 | 实现 Task、Attempt、Handoff、Main State | M1-002 | completed/incomplete Handoff、Attempt 与 checkpoint 示例通过 |
| M1-005 | DONE | 路诚钺 | 实现引用、revision、SHA-256 和 stale 检查 | M1-002 | 修改输入触发 `REF-HASH-MISMATCH`，input lock 不同触发 stale |
| M1-006 | DONE | 路诚钺 | 实现最小 CLI | M1-003..005 | init/validate/resolve/handoff/trace/checkpoint 可用 |
| M1-007 | DONE | 路诚钺 | 建立确定性风险检查 | M1-004..006 | Skill 缺失、越权、写冲突、Claim overreach、stale 注入均阻断 |
| M1-008 | DONE | 共享 | 冻结模型 API 中立端口与能力协商语义 | M1-001 | Capability/Data Policy gap 在调用前阻断，提供商基线可查询 |
| M1-009 | READY | 路诚钺 | 建立外部可复用项目 scaffold 与 `0.x` 兼容政策 | M1-006 | `rwb init` 可生成或选择完整模板；新项目不需手工复制 Registry/Profiles/Skills；Schema/CLI 迁移与废弃规则明确 |

## M2：Agent 与 Skills

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M2-001 | DONE | 路诚钺 | 实现 Skill Registry 与 Resolver | M1 | accepted Registry、最小覆盖、显式选择、冲突、权限交集、版本/哈希锁与确定性 Assignment 已测试 |
| M2-002 | DONE | 路诚钺 | 定义四个 Agent Profiles | M2-001 | coordinator/evidence/simulation/reviewer 的权限、工具、输出和上下文边界可验证 |
| M2-003 | PARKED | 路诚钺 | 创建 literature-evidence-extraction Skill | M2-001 | `0.1.0` 已冻结为 legacy；结构证据保留，不再作为新任务默认 Skill，后续只由 Mode-derived Need + Trace 重新激活 |
| M2-004 | PARKED | 路诚钺 | 创建 simulation-vv Skill | M2-001 | `0.1.0` 已冻结为 legacy 并按 action 拆分；真实数值案例不得继续验证 broad bundle |
| M2-005 | DONE | 路诚钺 | 创建 handoff-integrity 检查 | M1 | 确定性脚本已验证 Task/input/Skill/artifact 交接边界，不宣称科学正确性 |
| M2-006 | PARKED | 共享 | 扩展 Codex Runtime Adapter | M2-002..005 | 已有 Agent/Skill 发现、验证和显式 dispatch 保留；平台 launch/collect 不在当前 Mode–Skill 关键路径 |
| M2-007 | PARKED | 共享 | 执行首个双 Skill 垂直切片 | M7-002..006, M7-008 | 历史离线切片可精确 replay，但两个 broad Skill 均已 legacy；真实执行改由 Need + M3-008 路径重新定义 |
| M2-008 | PARKED | 路诚钺 | 建立外部 Skill 发现、隔离评估与准入 Registry | M1 | 73 条候选和 11 个来源的可追溯库存已形成；停止来源驱动扩张，后续 dossier/trial 只由 Mode-derived Need 与 Trace Gate 激活 |

## M3：上下文与风险

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M3-001 | IN_PROGRESS | 共享 | Main State checkpoint/resume | M1 | 规范化 digest、原子文件发布、Continuity 状态、机器证据哈希、Git 基线、下一动作和约束/决定丢失检查已通过；进程级 kill 矩阵与真实新主会话恢复待演练 |
| M3-002 | IN_PROGRESS | 路诚钺 | context pressure 与 AWU 预算 | M3-001 | 可测/未知指标、动态 next-AWU/closeout/reserve 判定、WARN/rollover/block 和 checkpoint 链已测试；真实运行估计误差待采集 |
| M3-003 | IN_PROGRESS | 路诚钺 | Handoff loss/stale/summary 抽查 | M2 | Transfer Manifest/Audit、负面区段覆盖、风险触发抽查、Context/Receipt 绑定已实现；真实 H1/H2 成本与人工样本仍待执行 |
| M3-004 | IN_PROGRESS | 路诚钺 | review loop/fanout/write race 检查 | M2 | 并发预算、review loop、协调成本与既有 write race 检查已落地；真实停止行为待验证 |
| M3-005 | IN_PROGRESS | 黄毅 | 敏感 trace 策略 | M2 | fail-closed 脱敏器和合成 OpenAI/Anthropic/Gemini 密钥、认证头、hidden reasoning fixture 已落地；待 live 脱敏包扫描后 DONE |
| M3-006 | IN_PROGRESS | 共享 | SAFE_PAUSE 与机器完成权 | M3-001..003 | AWU/完成/暂停条件、stage/safe-pause/waiting、执行结束与 `contract-satisfied` 分离、失败报告覆盖显式完成宣称和可恢复 pause fixture 已实现；真实 Task rollover 待演练 |
| M3-007 | IN_PROGRESS | 共享 | 冻结实名 actor、Attempt Archive 与完整 Agent Trace 规则 | M3-003..006 | ADR-0012、目录、消息信封、写前捕获、capture gap、按需读取和 Worklog 关系一致；负责人明确为路诚钺/黄毅 |
| M3-008 | IN_PROGRESS | 黄毅（路诚钺语义审查） | 实现 Trace Envelope/Index/Event Schema、validator 与手工 fixture | M3-007 | 本地候选已实现四类 v0.1 Schema、单写者 recorder、结构化 validator、CLI、正反 fixture 与 sequence/hash/path 性质测试；完整离线故障矩阵已通过，待 shared Schema 语义审查后 DONE |
| M3-009 | PARKED | 路诚钺 | 在 Execution Trace 之上增加 Method-aware Trace | M3-008, M8-003, M8-005 | 记录 Mode/Action/Mechanism/Capability/Human Gate/Evidence/Claim/Failure 决定；与执行事件分层关联，不复制正文 |

## M4：工件与复现

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M4-001 | READY | 路诚钺 | source admission 与 provenance | M1 | inbox 不可直接引用 |
| M4-002 | READY | 路诚钺 | work → object/run promotion | M1 | 只有校验通过可提升 |
| M4-003 | READY | 路诚钺 | Claim trace 与 counterevidence | M1 | 支持/反证/限制一次定位 |
| M4-004 | READY | 共享 | Run manifest 与复现检查 | M2 | 仿真案例可重建 |
| M4-005 | PARKED | 路诚钺 | DVC 技术 spike | 真实大文件需求 | 无需求则不启动 |

## M5：真实案例与删减

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M5-001 | BLOCKED | 人类维护者 | 选定证据综合真实案例 | 人类提供/批准边界 | 问题、来源、数据边界明确 |
| M5-002 | BLOCKED | 人类维护者 | 选定理论+仿真实际案例 | 人类提供/批准边界 | 模型、参数、Claim ceiling 明确 |
| M5-003 | READY | 路诚钺 | 建立单 Agent/轻量/多 Agent 对照 | M2..M4 | 指标与评估表固定 |
| M5-004 | READY | 共享 | 运行案例并分析净收益 | M5-001..003 | 质量、上下文、成本数据完整 |
| M5-005 | READY | 双方维护者 | 里程碑删减评审 | M5-004 | 至少做出一项保留/删除/停止决定 |

## M6：API Execution（黄毅维护）

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M6-001 | DONE | 黄毅 | OpenAI/Anthropic/Gemini 薄 Model Provider Adapters | M1-008 | 三家薄 Adapter 的 provider-neutral 离线合同与错误归一测试通过 |
| M6-002 | DONE | 黄毅 | 显式模型池与隔离 API session kernel（`K-API-1`） | M6-001 | primary/worker/specialist 槽只可显式绑定；轮次、工具、并行、工具结果、输出、token/成本/time 有硬边界；无自动 fallback；离线测试通过 |
| M6-003 | IN_PROGRESS | 黄毅（共享接口审查） | Task-to-API 文件闭环（`K-API-2`）与 Method/Capability 再集成 | M1-008, M2-001..005, M6-002, M8-003..005 | 本地集成候选已有编译/运行/Trace/closeout/file-only replay；双方 shared-interface review、全量 CI 与 OpenAI live replay 后 DONE |
| M6-004 | IN_PROGRESS | 黄毅 | 选定模型槽的真实 Windows conformance 与公开 EVID/SIM canary | M6-001..003 | 2026-08-19 DeepSeek/Anthropic-compatible AT-API-009 仅作历史 live 诊断；当前契约须完成 OpenAI text/schema/tool 与两条脱敏公开案例 |
| M6-005 | PARKED | 黄毅 | streaming/multimodal/server tools 与平台 Adapter | 真实案例或平台选择 | 没有真实需求不启动 |
| M6-006 | IN_PROGRESS | 黄毅（路诚钺语义审查） | API/平台执行时自动写入 Agent Trace | M3-008, M6-003 | 本地候选已实现 pre-call durability gate、provider-neutral request/response/tool/终态捕获、fail-closed 脱敏、capture-gap 和 marker Gate，且离线故障矩阵已通过；待 shared review 与 live 包扫描后 DONE |

## M7：Mode–Skill 选择与协调成本

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M7-001 | DONE | 路诚钺 | 冻结实名 owner、受控读取与分级 Handoff 文档策略 | M2, M3 | 路诚钺/黄毅职责、ADR-0011/0012、架构图和开发入口一致 |
| M7-002 | DONE | 路诚钺 | 建立现有 Mode 决策卡与边界 fixtures | M1-003 | 八个诊断 case 覆盖 evidence/simulation trigger、no-Mode、candidate Mode、组合拆分与歧义阻断 |
| M7-003 | DONE | 路诚钺 | 建立 Task-to-Mode/action/mechanism 选择矩阵 | M7-002, M7-011, M7-008 | tool-only/no-Skill、Skill Need、拆 Task、capability gap、blocked 和 Human Gate 均有可复验路径；无隐式 Assignment |
| M7-004 | DONE | 路诚钺 | 按 Mode action 重新审计并迁移三个 0.1.0 Skill 原型 | M7-011, M7-008 | 三个冻结包均有 action、direct baseline、manifest/package hash、new-assignment/版本决定与机器夹具；未创建无证据的 `0.2.0` |
| M7-005 | PARKED | 路诚钺 | 独立整理/重写最多两个 Mode-derived Need 并作证据化去留决定 | M7-011, M3-009, M8-003 | 不再从来源 shortlist 直接选择；`claim-preserving-rewrite` Stage 1 保留为历史诊断，新的 trial 等待正式 Need/Method Trace |
| M7-006 | PARKED | 路诚钺 | 建立 H0/H1/H2 与内容读取成本对照 | M3-008, M8-003 | 保留为 Evaluation baseline 输入；Method Resolution 稳定后再用 Attempt Archive 记录遗漏、返工、回查和 capture gap |
| M7-007 | PARKED | 路诚钺 | 新增 experiment/theory/observational/engineering Mode | 真实案例 + Mode 准入卡 | 证明现有 Mode 组合不足后逐个启用 |
| M7-008 | DONE | 路诚钺 | 为已确认 Mode action gap 建立首批 Tool capability cards | M1-008, M7-011 | 五张 Action-driven cards 已明确数据出口、权限、副作用、预算、失败、验证、fallback 与 owner；未实现 API/Adapter |
| M7-009 | DONE | 路诚钺 | 建立多来源 Skill 候选池与机器/人工筛选 Gate | M2-008 | 首批 54 个入口均已固定来源、路径、内容哈希和人工 Decision；一方 19 项为 18 `reference`/1 `rejected`，社区 35 项为 6 `triage`/21 `reference`/8 隔离或排除；下载内容未安装、执行或自动准入 |
| M7-010 | DONE | 路诚钺 | 建立四个来源候选 dossier 并决定是否进入验证 | M7-004, M7-009 | 四份历史 dossier 已完成；Human Decision 选择 0 个来源候选直接重写，转入 ADR-0013 的 Mode-derived Need 路线 |
| M7-011 | DONE | 路诚钺 | 建立两个正式 Mode 的 Action–Failure–Artifact–Gate 与 Skill Need 基线 | M7-002, M7-010 | evidence/simulation 的每个 action 有最小机制；每个 Mode 首批 Need≤2；no-Skill、Tool、Skill Need、blocked、Human Gate 均可出现 |
| M7-012 | DONE | 路诚钺 | 建立 project-internal Skill Need 路线与候选占位 | M7-001, M7-011 | 与 Mode-derived 路线分离；交互、输出、恢复和 Gate 候选先比较 Protocol/template/Tool；未新增 Skill/Registry/Runtime |
| M7-013 | DONE | 路诚钺 | 为两个优先 project-internal Need 建 direct baseline、failure fixture 与 compact dossier | M7-012, M1-004 | H1 omission 与 H2 semantic reversal 均形成可复验诊断；两项结论均为 `hold-no-skill`；未修改自动 Trace/API |
| M7-014 | PARKED | 路诚钺 | 对 project-internal 候选做有 Trace 的困难任务比较 | M7-013, M3-009, M8-003 | 比较 template/tool/compact Skill 的遗漏、回查、返工和上下文成本；无重复语义增量即退役 |
| M7-015 | DONE | 路诚钺 | 分离 Skill 历史解析与新分配 lifecycle | M7-004 | Registry/Resolver 表达 active/legacy/deprecated 与精确版本约束；旧 Assignment 可复验，新路由不能选择 legacy/deprecated |
| M7-016 | DONE | 路诚钺 | 执行 K-MS-1 节点评审并冻结基线 | M7-002..004, M7-008, M7-011..015 | 九项条件逐项 PASS；Decision 接受离线选择/治理基线并 safe stop，不自动进入真实 trial |

## M8：Method Core Formalization

| ID | 状态 | Owner | 任务 | 依赖 | 验收 |
|---|---|---|---|---|---|
| M8-001 | DONE | 路诚钺 | 按第二轮审计重整全局架构文档与路线 | M7-016 | ADR-0016、五平面架构、ROADMAP、审计吸收记录和单一真值导航一致；未验证外部项目或实现新 Schema |
| M8-002 | IN_PROGRESS | 路诚钺（黄毅执行审查） | 将 Mode Action 正式化为一等契约 | M7-011, M8-001 | 集成分支已提供 16 个 stable ID/version/hash Action、Schema/Registry 与正反校验；待共同审查后合入 `main` |
| M8-003 | IN_PROGRESS | 路诚钺 | 建立版本化 Method Resolution | M8-002 | 集成分支已将八个 routing fixture 转为 provider-neutral Resolution，并另有 EVID-001 执行实例；待共享语义审查 |
| M8-004 | IN_PROGRESS | 路诚钺 | 建立最小 migration seam 并迁移 Research Mode v0.1 → v0.2 | M8-002, M8-003 | v0.2、双 Mode action refs 与确定性 v0.1→v0.2 migration 已实现；v0.1 保持可验证，待兼容审查 |
| M8-005 | IN_PROGRESS | 路诚钺（黄毅执行审查） | 冻结 Decision Authority Matrix 并映射 validation/preflight | M8-002, M8-003 | Matrix、越权/Provider 污染/Human Gate 正反检查与 execution preflight 已实现；待双方确认共享风险语义 |
| M8-006 | IN_PROGRESS | 共享 | 冻结 Resolved Capability Snapshot 与 Resolved Execution View | M8-003, M8-005, M6-003 | 集成分支已冻结 Task/Assignment/Method/Snapshot/可选前序状态和执行身份，严格 CLI 离线闭环可 replay；待 shared review 与 live conformance |

## 历史 GitHub Issues

首批 Issues 已在后续实现与架构调整后关闭；本节只保留任务来源追溯，不再作为当前执行入口：

- [#1 M1-001 Bootstrap Python package and CI](https://github.com/Chengyue-Lu/research-agent-workbench/issues/1)
- [#2 M1-002 Implement the minimal research object schemas](https://github.com/Chengyue-Lu/research-agent-workbench/issues/2)
- [#3 M1-003 Implement protocol, mode, agent, and skill manifests](https://github.com/Chengyue-Lu/research-agent-workbench/issues/3)
- [#4 M1-004 Implement task, handoff, main state, and reference integrity](https://github.com/Chengyue-Lu/research-agent-workbench/issues/4)
- [#5 M1-005 Build the minimal CLI and deterministic risk checks](https://github.com/Chengyue-Lu/research-agent-workbench/issues/5)
- [#6 M1-008 Freeze provider-neutral model API port](https://github.com/Chengyue-Lu/research-agent-workbench/issues/6)
- [#7 M2-008 Audit and admit external Skill candidates](https://github.com/Chengyue-Lu/research-agent-workbench/issues/7)（来源驱动扩张已被 Need-first 路线取代）

## 当前下一任务

当前顺序是：对 **M8-002..006 + M6-003 + Trace shared boundary + no-Skill Assignment
seam** 做双方审查 → 在授权 Windows 环境执行 OpenAI text/schema/tool 与两条公开
canary → 扫描脱敏包并重放 `trace validate`/`execute verify`。全量离线、coverage、
wheel/干净 venv 已在本地通过，Python 3.11/3.13 仍待 PR CI 重放。
审查和 live 证据通过前不标 DONE、不直推 `main`。M3-009 与 M7-005/006/014 继续 parked。
