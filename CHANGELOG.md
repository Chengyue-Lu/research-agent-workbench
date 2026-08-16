# Changelog

本项目遵循“证据先于宣称”：离线契约、fixture 和真实运行结果分开记录。日期按仓库当前开发快照标记。

## 2026-08-16 — M6-004 收尾：只读并行度显式决策与 live completed 终态

### Decision（并行度子决策，登记在 M6-005 范畴）

- 单轮工具 fan-out 上限 `ExecutionPolicy.max_parallel_tool_calls` 默认 1→4，**仅对该轮全部调用为 read-only 工具的回合生效**；含任何副作用工具（或未知名）的回合保持串行上限 1。runner 仍逐个顺序执行（无线程并发），总 fan-out 继续受 `max_tool_calls` 硬上限约束，当前切片工具白名单仅 read-only。
- attempt 身份纳入会话边界：`_attempt_identifier` 增加 `session_limits` 规范化摘要。不同执行边界是不同 Attempt，不得共享关闭批次/完成标记——修复“放宽策略后重跑永远命中已关闭旧批次（幂等跳过、模型不重执行）”的隐性缺口。`examples/api-execution/` 三条链 fixtures 已再生成（attempt id 更新）。

### Added

- session runner 分级并行测试：全 read-only fan-out 在上限内逐个按序执行并继续会话；read-only + local-write 混合回合即使上限 ≥2 也在任何副作用前以 `parallel-tool-budget` 安全暂停（零执行）。
- compiler 测试：attempt id 对会话边界敏感（不同 policy ⇒ 不同 attempt id）。

### Milestone

- `M6-004` live 面收尾：EVID-001 新尝试 `A-2D05287D7252`（经 `--from-state` 链自 safe-paused `A-3F04FD1F0130` 的 Main State）在真实 Windows 会话以 glm-5.3 执行，**status completed、completion_claim contract-satisfied**；11 工件原子落盘（含首个 live Evidence 工件）；check-report pass（EVIDENCE-SCHEMA/SOURCE-HASH/SOURCE-LOCATOR，checker 哈希钉住）；Receipt 记录真实 2 请求、2455 入/4997 出 tokens；幂等重跑 `already-published`（模型不重执行、11 文件哈希复核）；`handoff validate` 与 `context resume-check`（仅凭文件）均通过。
- 诚实边界：Evidence 工件如实自标 `synthetic-fixture/no-citable-evidence/extraction-blocked`（结构完成 ≠ 科学价值）；本次运行 receipt `max_parallel_observed: 0`——决策移除的是上一次尝试确定性触发的 `parallel-tool-budget` 阻断，本次运行本身未发生 fan-out；Attempt Archive 自动捕获仍属 M6-006；live 运行工件按设计留在本地 `work/` 与 `checkpoints/`，不入库。

全量 219 项测试通过；`validate examples registry` = 84/0/0。

## 2026-08-16 — claim-preserving-rewrite checker 跨 locale 输出契约修复

### Fixed

- `check_claim_preservation.py` 入口将 stdout/stderr 钉为 UTF-8：此前 `--json` 报告（`ensure_ascii=False`，含中文 detail）按子进程 locale 编码输出，父进程 `subprocess.run(text=True)` 按宿主 locale 解码；混合环境（如带 `PYTHONIOENCODING=utf-8` 的中文 Windows 会话）下读线程 `UnicodeDecodeError` 使 stdout 丢失，`test_candidate_claim_rewrite.py` 3 项测试崩溃。本机 GBK/GBK 与 CI UTF-8/UTF-8 的通过只是父子 locale 恰好一致。
- `tests/test_candidate_claim_rewrite.py` 全部 3 处 `subprocess.run` 显式 `encoding="utf-8"`，解码不再跟随宿主 locale。
- 哈希钉住链同步再生成：候选包 `package_hash`（`6c05f9f2…`）更新于 `registry/skills/candidates.json`、候选 manifest、`registry/skills/sources.json` 与 `examples/evals/claim-preserving-rewrite/fixture-evaluation.yaml`；`baseline-check.json` 与 `with-skill-check.json` 用修后 checker 重生成（仅 checker 哈希与派生 `report_id` 变化，`checks` 输出逐项一致），两份校验文件的新哈希同步写入 `fixture-evaluation.yaml`。
- 验证：全量测试在干净环境与 `PYTHONIOENCODING=utf-8` 环境均 216/216 通过（修复前后者 213 通过 + 3 失败）；`validate examples registry` = 84/0/0。

## 2026-08-15 — M6-004 live 接线、两处 live-only 集成缺陷修复与真实 evidence 调用

分支：`agent/m6-004-live-provider-wiring`（含 K-API-2 全部提交 + live 接线 + 本日修复，待评审合并）。

### Added

- `rwb execute task` live 路径（3d1b79e）：`--from-environment` / `--provider-config` / `--model-env` 显式接线；模型池绑定模型透传；缺配置、禁用适配器、未知适配器分别以 `EXEC-PROVIDER-NOT-CONFIGURED` / `EXEC-ADAPTER-DISABLED` / `EXEC-ADAPTER-UNKNOWN` fail-closed；离线测试 9 项（装配、键控、阻断、缺模型变量零写入）。
- 真实 conformance 记录：glm-5.3 经 `glm-anthropic-messages`（open.bigmodel.cn Anthropic 兼容端点）text/structured/tools 三项通过（本地 `runs/provider-conformance/glm-rerun-20260815.yaml`，`runs/` 按设计不入库）。

### Fixed

- 结构化输出在 Anthropic 兼容端点的诚实性（54f3d1d）：探针把 JSON Schema 直接嵌入提示词（GLM 端点静默忽略 `output_config`）、解析前剥离一层 markdown code fence、单次调用输出上限 256→1024（thinking 优先模型会耗尽小预算）。
- **live-only 集成缺陷 1**：编译器把 task/assignment/slot 记账信息写入 `ModelRequest.metadata`，而适配器 metadata 契约是 provider 特定的（Anthropic 只传 `user_id`，Gemini 全不传）→ 任何 live 执行在首次网络往返前死于 `UNSUPPORTED`。离线路径（脚本化 provider）不经过适配器序列化，故 214 项离线测试从未暴露。修复：记账字段上移到 `CompiledSession`（`task_id`/`assignment_id`/`slot_id`），wire 请求 metadata 恒空。
- **live-only 集成缺陷 2**：`incomplete` 会话关闭事务必然失败——合成的 `human_decision_required` 条目不在 `_negative_mirror`/manifest 内（`HANDOFF-NEGATIVE-UNMAPPED`），且语义评审 pending 被发布期验证一刀切阻断（`HANDOFF-SEMANTIC-REVIEW-REQUIRED`）。离线四路径未覆盖 incomplete。修复：决策条目纳入 mirror/manifest（schema `kind: human-decision` 早已预留）；发布期验证豁免"评审待完成"（review.pending 是人工门禁的预期状态，结构风险仍阻断）。
- `execute task --json --dry-run` 的 `status` 字段误标 `already-published`（与真 resume 不可区分）→ 细分为 `compiled-not-executed`。
- `examples/task-evidence.yaml` 输出预算 1800→4096：1800 在 live 实测中把 glm-5.3 截断在 `finish_reason=length`（thinking token + 完整 JSON 单轮放不下）；静态 fixtures 与引用哈希同步再生成。

### Milestone

- `M6-004` 到达（live 面）：真实 Windows 用户会话 conformance 通过 + 一次真实 evidence 调用完成（EVID-001 attempt `A-3F04FD1F0130`，glm-5.3 实测 1182 入/783 出 tokens）；会话因模型并行工具调用触发 `parallel-tool-budget` 硬边界安全暂停——设计内终态，原子关闭完整落盘 10 工件 + Main State；确定性幂等（重跑跳过模型执行、10 文件哈希复核）、`context resume-check` 仅凭文件恢复、`handoff validate` 均通过。全量 215 项测试通过；`validate examples registry` = 84/0/0。
- 附带发现：glm-5.3 在该任务上倾向并行发起 read-only 工具调用，当前示例 policy `max_parallel_tool_calls=1` 下任务无法到达 completed；放宽并行度属 M6-005 范畴的显式决策，未在本分支放水。
- 未证明：completed 终态的 live evidence 产物（需并行度决策或模型行为配合）、Attempt Archive 自动捕获（M6-006）、任何科学正确性。

## 2026-08-14 — K-API-2 离线文件闭环（M6-003）

分支：`agent/k-api-2-task-to-api-closure`（基于 `main` @ `6a4c49b`，待评审合并）。

### Added

- `src/research_workbench/execution/` 新工作流包：
  - `compile_session` 纯函数编译边界：Task Packet + Profile + 冻结 Skill Assignment + 显式模型槽 → 一个全新 `ModelRequest`。逐个哈希校验输入与 Skill 正文（`TASK-STALE-INPUT`、`COMPILE-SKILL-DRIFT`），超限直接阻断不截断；每个会话限额标注来源（task-budget 或 policy-default）；类型上无法携带主 Agent 历史或未选 Skill。
  - read-only `document-read` 客户端工具与 `SessionToolLog`：只读声明输入或有效 allowed roots，越界/超限拒绝并留痕。
  - 状态映射表：会话结果 → Attempt/Handoff/Receipt/Main State 一致状态；模型漂移阻断 `contract-satisfied` 宣称；completed 只有在确定性检查（`execution/checks.py`，按哈希钉住）通过时才宣称 `contract-satisfied`。
  - 原子关闭事务：stage/validate/publish 三阶段，11 类文档按固定顺序排他 `os.link` 发布、Main State 严格殿后；完成标记只在发布后验证通过时写入；同一进程内同计划可确定性续跑；跨进程中断由预检以 `EXEC-CLOSEOUT-INCOMPLETE`/`EXEC-BATCH-CLAIMED` fail-closed 阻断（不自动重跑模型，人工处置）；内容分歧以 `EXEC-CLOSEOUT-PATH-CONFLICT` 阻断；发布后用真实 Receipt/Handoff/Transfer 校验器复核。
  - `execute_task` 编排与 `build_provider_registry` 缝隙（真实 Provider 接线显式阻断为 `EXEC-PROVIDER-NOT-CONFIGURED`，属 M6-004）；确定性 attempt id（覆盖 assignment、槽位、模型与任务正文哈希）+ 完成标记让重跑跳过模型执行。
- `rwb execute task` CLI 子命令：显式 `--model-env NAME=VALUE` 注入或 `--from-environment` 实环境读取；`--dry-run` 只编译不执行。
- `examples/api-execution/`：completed / tool-failed / safe-paused 三组可再生静态 fixtures（`regenerate.py` + README 声明离线边界）；stale-input 路径按设计零写入，由 E2E 测试证明。
- 新测试：编译器 17、工具 7、关闭事务 13（含逐步 `os.link` 故障注入矩阵与验证失败不落标记回归）、离线 E2E 16（四路径 + 全新 CLI 会话仅凭文件的 resume-check 证明 + 漂移/预检/幂等/写范围/中断批次防护/独占 claim）、CLI 接线 4、fixtures 一致性 6（含 checker 哈希钉住校验）。
- 评审加固（REQUEST-CHANGES 整改）：`.gitignore` 的 `work/` 锚定到仓库根（此前 fixtures 批次链被静默排除、fresh clone 自检失败）；attempt_id 覆盖任务正文；零输入 evidence 任务编译期阻断；completed 无结构化输出时强制不宣称 contract-satisfied；批次独占 claim 防并发重复执行。

### Milestone

- `K-API-2` 的离线验收到达：已解析 evidence Task 编译进全新 API 子会话，完成或安全暂停后 Attempt、Evidence、确定性检查、Transfer Manifest/Audit、双 Context Snapshot、Assignment、Handoff、Receipt、Main State 全链原子落盘；删除内存会话后新 CLI 会话仅凭文件恢复唯一下一动作。全量 192 项测试通过；`validate examples registry` = 84/0/0。
- 未证明：真实 Provider/模型调用（M6-004）、Attempt Archive 自动捕获（M6-006）、任何科学正确性。

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
