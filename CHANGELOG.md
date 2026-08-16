# Changelog

本项目遵循“证据先于宣称”：离线契约、fixture 和真实运行结果分开记录。日期按仓库当前开发快照标记。

## 2026-08-15 — closeout/pipeline 行为不变重构

### Changed

- `execution/closeout.py`（2463 行）拆分为 `execution/closeout/` 包：`errors`（错误与值类型）、`paths`（路径布局）、`documents`（文档读写与 schema 校验）、`verify`（视图校验与漂移核验）、`builders`（纯文档构造）、`stage`（stage 树与执行 intent）、`publish`（五入口）。公共 API 经包 `__init__.py` 原名重导出，三个下游导入方零改动。
- commit-last 协议的四个世界状态检查点（stage 视图 → outputs 已发布 → hash 校验后 → Main State 发布后重读盘）收敛为 `_ViewCheck`：检查点次数、相对顺序与全部 fault-injection 点名逐一保留，仅消除 9 处 11 关键字参数的搬运样板。
- `pipeline.run_task_api_attempt` 的 6 组失败 closeout 样板收敛为局部 `closeout_terminal` 闭包（11 个不变参数闭合捕获，编译前后阶段差异经显式覆盖）；本地 `_REQUIRED_ACTIONS` 常量改为共享 `TERMINAL_STATUSES`。
- 三个 Provider Adapter 中逐字重复的 `_integer` 上移 `adapters/models/base.py` 一份。

### Scope

- 纯行为保持重构：校验调用次数、错误码、fault 点、公共 API 与全部 227 项测试零变化；未合并任何校验语义。
- `output.py` 与 `context/handoff_transfer.py` 的两个 `_resolve_pointer` 经逐行核对语义不同（空指针返回与数组下标 token 严格度不同，位于不同信任边界），有意保留不合并。
- 验证：每步后执行域/adapter 域门禁测试，最终全量 pytest 通过。

## 2026-08-15 — K-API-2 H2 fake-local 文件关闭切片

### Added

- 新增 Task/Profile/Skill Assignment/显式模型槽到最小 API 请求、限制与精确 `document-read` handler 的纯编译边界；Protocol、合同、Skill、输入和 previous Main State 在 Provider 调用前按精确字节冻结。
- 新增 `completed`、`safe-paused`、`incomplete`、`failed`、`blocked` 五种终态的文件关闭路径；成功路径生成研究工件、Manifest/Audit、Handoff、Snapshots、Receipt 和 Main State，非成功终态不伪造科研工件。
- 新增执行 intent、可验证 stage 续发、排他发布、Main State 最后提交、已提交身份核验和 fresh Python 子进程恢复检查。

### Hardened

- 模型控制的 JSON、locator、object ID、Provider/Model identity、usage、动态输出路径和 contract/input/Skill 漂移均在完成宣称前 fail-closed；同 Attempt 不自动重放未知外部执行。
- Provider Adapter ID 与规范 Provider identity 分离记录；预算文案明确为请求前、调用边界与响应后 guard，不宣称可取消 in-flight 调用。

### Scope

- 当前实现只接受明确要求 Transfer Manifest 的 H2 evidence Task，并用 fake Provider/合成 fixture 验证；普通 H1/risk-tier closeout、完整 Attempt Archive/Agent Trace 自动捕获、真实 Provider/Windows、科研语义等价和科学正确性均未证明。
- 主线已将当前唯一节点调整为 `K-MS-1`。本切片不恢复已归并的旧交接文档，也不授权启动 `M6-004` 或 `M6-006`。

## 2026-08-14 — 实名责任、完整 Agent Trace 与文档归并

### Changed

- 维护责任改为实名：路诚钺负责 Mode/Skill、读取、Handoff/Trace 方法与评估；黄毅负责 API 执行实现、自动 Trace 捕获与测试；工作流名称不再替代审批主体。
- Worklog 降为 Attempt Archive 的导航摘要。所有 Agent 间实际可见传递，以及运行时可观察的读取、工具/命令、文件 revision、结果和状态事件均要求留存。
- 完整留存与上下文加载解耦：主 Agent 默认只读取 `INDEX.yaml` 与 Handoff，排障或评估时才按 message ID 回放原文。
- 原 `CURRENT_HANDOFF.md`、`NEXT_STEPS.md` 和 `WORKSTREAM_OWNERSHIP.md` 合并为 `docs/DEVELOPMENT.md`、`docs/TASKS.md` 与 `docs/README.md`，减少当前状态的重复来源。

### Added

- ADR-0012：实名责任人与可回放 Agent Trace 决策。
- Attempt Archive 目录、actor registry、消息信封、capture-gap、删减和保留规则。
- 总体架构 Mermaid 图中的 Trace 写入、默认只读索引与实名维护关系。

## 2026-08-14 — Mode–Skill 工作流接管与上下文简化

### Changed

- API Adapter、API session、Task-to-API、live conformance 与 API 测试由黄毅维护；路诚钺主线改为 Research Mode、Skill 选择/评估/准入和协调成本。
- 当前下一节点从 `K-API-2` 调整为 `K-MS-1 Mode–Skill Selection Baseline`；API backlog 保留为共享仓库中的 external workstream。
- Handoff 改为 H0/H1/H2 风险分级：普通子 Agent 默认只返回 Compact Handoff，完整 Manifest/Audit/Receipt 只在压缩、高风险、外部副作用、promotion、争议或明确策略下触发。
- Agent 内容读取采用默认拒绝与逐级扩大：允许路径元数据发现，但未声明正文需先扩展 Task 允许集。

### Added

- `docs/WORKSTREAM_OWNERSHIP.md`：曾用于冻结工作流边界，现已归并到 `docs/DEVELOPMENT.md` 并改用实名责任。
- ADR-0011：记录风险分级 Handoff、受控内容读取和简短工作留痕原则。
- `docs/implementation/MODE_SKILL_WORKSTREAM_PLAN.md`：记录当前缺口、候选优先级、`K-MS-1` 验收和分支范围。
- 更新总体架构 Mermaid 图，显示 Mode–Skill 决策、执行工作流、内容允许集、读取扩展和 H1/H2 返回关系。

### Clarified

- 正式 Mode 目前只有 evidence-synthesis 与 simulation；其他模式名称不是待批量补齐的承诺。
- Worklog 记录基线、重要决定、范围变化、修改和验证；Agent 间实际可见传递另由 Attempt Archive 完整保存，仍不记录隐藏推理。
- 流程简化仍是假设；后续必须比较 H1/H2 的工件数、字符、审阅、回查、遗漏和返工。

## 2026-08-13 — API-first 隔离执行关键节点

### Changed

- 执行优先级从“Codex 原生运行时优先”调整为“文件契约 + 纯 API fresh session 优先”；Codex、OpenCode、Claude Code 等保留为可选 Runtime Adapter 或人工窗口入口，不预先固化最终平台。
- 模型选择收缩为显式 `primary`、`worker` 和少量 `specialist` 槽，不建设价格数据库、评分 Router 或静默 fallback。
- coordinator 默认指向 `primary`；evidence、simulation 和 targeted review Profile 默认指向 `worker`，高风险任务可由 Task/人类显式覆盖。

### Added

- ADR-0010，冻结 API-first 隔离执行、平台可替换和小型模型池边界。
- `ModelPool`/`ModelSlotConfig`：默认不读取环境，只按调用者指定槽位绑定一个 Provider/Model。
- `IsolatedApiSessionRunner`：单 Attempt 内的 fresh context 工具循环，限制模型轮次、工具调用、单轮并行、工具副作用类别、工具结果、单轮输出、累计 token/可得成本和 wall time。
- `rwb models probe` 与禁用状态的 `registry/models/pool.example.yaml` 模板。
- 离线测试覆盖显式槽位、禁用/未知槽、工具往返、data policy、预算暂停、工具结果不静默截断和无 Provider fallback。
- `docs/CURRENT_HANDOFF.md`：为无既往会话上下文的开发者或 AI 固化恢复顺序、已证明/未证明边界、`K-API-2` 验收、并行写入范围和风险预警。

### Milestone

- `K-API-1` 已到达：隔离 API 执行缝可离线验证，但尚未形成 Task-to-API 的 Attempt/Handoff/Receipt 文件闭环。
- 下一唯一节点为 `K-API-2`：完成一个 evidence Task 的 fresh API session 文件闭环，并在删除临时 transcript 后由新主会话恢复。该节点不是 GUI、发布或科研交付点。

### Fixed

- 目录包哈希改为按仓库相对 POSIX 路径排序，消除 Windows 与 Linux 对路径大小写排序不同造成的 Skill package drift。
- 显式声明 RFC3339 format validator 依赖，确保干净环境不会静默跳过 JSON Schema 日期时间校验。

## 2026-08-13 — 零基础使用与发布就绪度指南

### Added

- `docs/GETTING_STARTED.md`：从安装、自检、Task/Assignment/dispatch、原生 Agent 接力、Handoff 验收到 SAFE_PAUSE 恢复的完整上手路线。
- 按内部 alpha、外部 pilot、公开 beta 和稳定 `1.0` 分级的发布门槛，明确当前可用范围以及真实原生执行、项目脚手架、许可、兼容性、工件复现和科研价值证据缺口。

### Clarified

- `rwb init` 当前只是最小文件目录初始化器，不复制 Agent Profiles、accepted Skills、Registry 或 Codex 配置。
- `render` 只生成最小派发，不启动 Agent；Workbench 管契约和验证，线程生命周期继续由原生平台负责。

## 2026-08-13 — CCRML 讨论吸收与连续性闭环

### Added

- Task Packet 的原子工作边界、机器完成检查与安全暂停条件；Codex dispatch 会显式携带这些边界。
- Context Snapshot 的动态预算比较：下一 AWU 成本、closeout 成本与安全余量使用同一单位，不再以固定百分比单独决定 rollover。
- `stage-completed`、`safe-paused`、`waiting` 状态，以及包含 Attempt/Handoff/Receipt/Main State 的可恢复 SAFE_PAUSE fixture。
- Main State 的 `continuity_status`、哈希锁定 `machine_state_refs`、可选 Git HEAD 和恢复冲突检查。
- Execution Receipt 区分“执行结束”和显式 `completion_claim: contract-satisfied`；机器 `fail` 会阻断后者，但不会抹掉失败实验或负对照记录。
- YAML 工件先在同目录完整落盘，再以排他硬链接原子发布；注入发布故障不会暴露半文件或残留临时文件。
- CCRML 会议吸收差距表与 ADR-0009，明确复用现有工件并暂缓 SQLite/Graph/额外运行时。

### Not yet proven

- 文件式 SAFE_PAUSE 尚未在真实新原生会话中完成一次端到端恢复。
- 动态 AWU 成本仍为显式测量/估计输入，尚无跨模型校准数据。
- `continuity.sqlite`、Failure Memory 和混合检索的净收益仍无 benchmark 证据，因此未实现。

## 2026-08-13 — 暂停前开发快照

### Added

- 平台中立的 Research Object、Project Protocol、Research Mode、Agent Profile、Skill、Task、Attempt、Handoff、Main State、Context Snapshot 与 Execution Receipt 契约及 CLI。
- Codex 原生 Agent/Skill 映射和 evidence/simulation 双 Skill 离线垂直切片。
- OpenAI Responses、Anthropic Messages、Gemini `generateContent` 薄 Adapter，ToolChoice、本地工具参数复验和默认不读环境、不联网的 live conformance runner。
- 外部 Skill 来源 Registry、只读 ZIP 审计、18/18 入口追溯、隔离候选区及 `claim-preserving-rewrite` 原始候选。
- provider-neutral paired same-input Skill Evaluation、确定性检查报告、盲评/人工准入边界和故意 `not-eligible` 的 fixture。
- Handoff Transfer Manifest/Audit：稳定条目 ID、源工件哈希、Handoff locator、负面区段覆盖、风险触发的人类抽查，以及压缩 Context Snapshot/Receipt 绑定。
- `docs/NEXT_STEPS.md`，记录暂停点、恢复输入、执行顺序和禁止扩张项。

### Changed

- 主 Agent 明确只维护问题、约束、决定、冲突和工件索引；原始材料与长日志留在 Task/Artifact Context。
- Skill Assignment 固定 Skill 内容与包哈希、工具、权限和 Registry digest；不同 Agent 继续使用不同 Skill。
- `literature-evidence-extraction` 在压缩前输出 Transfer Manifest；`handoff-integrity` 可审计结构覆盖和有界语义抽查，不承担科学正确性评审。
- token/成本不可得时记录 `unavailable`，不以 0 代替，也不宣称节省。

### Security and governance

- 外部候选默认不可执行；发现、评估、trial、accepted 分离。
- Provider 凭据延迟读取；文档、报告和测试不保存 token、完整响应、Chain-of-Thought 或无消费方的 trace。
- GitHub/API 令牌不得在 Codex 沙箱读取或导出；真实认证和 live 调用在真实 Windows 用户上下文执行。

### Not yet proven

- 尚未完成三家 Provider 的真实模型 conformance。
- 尚未执行两个真实原生子 Agent 并删除会话后恢复。
- 尚未用真实研究材料验证 Transfer Manifest 是否遗漏关键语义及其维护成本。
- 首个候选 Skill 尚未完成四类真实 paired evaluation，也未准入。
- 尚无真实科研案例证明多 Agent 相对单 Agent 的净收益。

## 2026-08-12 — 初始重构方向

- 将原项目从“全局科研代理/全盘外包”方向收缩为研究者主导、平台优先、模式化组合的轻量契约层。
- 决定不自建通用 Supervisor、不建立单一跨学科流水线，并把上下文、证据、权限、成本和人工 Gate 设为核心边界。
