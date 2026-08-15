# Changelog

本项目遵循“证据先于宣称”：离线契约、fixture 和真实运行结果分开记录。日期按仓库当前开发快照标记。

## 2026-08-14 — K-API-2 离线最小文件闭环

### Added

- `research_workbench.execution` 的可信 Task-to-API 边界：Project Protocol、Task、Profile、Skill Assignment 和可选 previous Main State 在 Provider 前按精确字节捕获并做 canonical ref/Schema 校验；执行期漂移阻断 Main State 发布。
- 只编译 Task 冻结输入、Assignment 选定 Skill、显式模型槽、权限/工具/data-policy/budget 交集的 `CompiledApiExecution`；主会话历史、未选 Skill 和原始 source 正文不会被预先注入 prompt。
- 只读、哈希复验的 `document-read`，以及 Evidence source/hash、claim ceiling、locator 和 Transfer statement 的结构化输出校验。
- commit-last closeout：stage/validate、逐文件排他发布、real-tree 复验和 Main State last；completed 生成 Research Artifacts 与 Manifest/Audit，非 completed 不伪造这些科研工件。
- 持久 execution intent、精确 stage plan、已提交 bundle 检查和同 Attempt 并发互斥。完整 validated stage 可续发；执行已开始但 plan 尚未形成时返回结果未知并禁止自动重放。
- fake-local K2 测试覆盖 completed、tool-failed、safe-paused、incomplete、stale/missing input、错误模型、无效/漂移合同、错误 Evidence hash、动态写权限、并发、关键 closeout 崩溃及 Main 提交窗口的输入/Skill/非 Main 文件漂移；fresh Python subprocess 可在无 transcript 时以 Main State 为入口校验项目文件树并执行 `resume-check`。
- Task 输入以执行前捕获的精确字节写入 stage；每个发布文件由 stage plan 哈希锁定，并在发布 Main State 前重新核验真实合同、输入、Skill lock、非 Main 文件与 staged Main State。
- staged/committed 重试绑定规范 Task/Attempt 输出路径与 optional previous Main State identity，并在任何续发写入前重新执行 write-scope/allowed-root 检查。
- 最终离线验证为仓库全量 226 tests passed、K2 专项 92/92 passed（compiler 18、session 16、I/O 6、closeout 11、pipeline 41）、Registry validator 53/0/0；未执行真实 API。独立冻结字节复测由节点评审另行记录。

### Hardened

- Provider Adapter ID 与规范 Provider identity 使用不同命名空间：前者用于 Registry/请求绑定，后者用于 capability/响应核验和 Receipt usage；错误 Provider/模型会在工具前阻断。负值、布尔值或非有限 usage/limit 不能绕过预算 guard。
- `LENGTH`、`PAUSED` 与 `CONTEXT_LIMIT` 明确关闭为 `incomplete`，使用独立下一动作；已提交 Attempt 会从正式 Receipt 核对请求的 Adapter ID/模型，改变绑定不能命中幂等 fast path。
- Skill 指令和 Task document-read 均对同一份捕获字节完成哈希与 UTF-8 解码；content-only Skill lock 不再隐式授权邻近 Markdown。
- repository-relative path 拒绝 Windows drive-relative 形式，动态 artifact 路径按真实 `object_id` 复验 write scope/allowed roots，并拒绝 Windows reserved basenames。
- 工具失败仅持久化本地调用序号、工具名和异常类型，不保存 Provider call/response ID 或异常正文。

### Milestone and limits

- `K-API-2 Offline Minimal File Loop Gate Passed`：2026-08-15 三路只读复审均给出 PASS，未发现阻断性 P0/P1；`M6-004` 仍为待维护者明确授权的真实 Windows 工作。
- closeout 是 Main State last 的崩溃一致协议，不是跨文件事务；崩溃可留下未被权威 Main State 引用的孤立文件。
- `max_parallel_tool_calls` 只是单轮 fan-out 上限，handler 当前串行。token/成本在响应后检查，wall time 在调用前后检查，均不能取消 in-flight 调用。
- 当前只证明 fake-local、合成 source、临时目录和 fresh Python subprocess。没有执行真实 API，也未证明真实 Windows 主/子会话、外部写幂等、科研正确性、Transfer 语义等价或多 Agent 净收益。
- 风险触发的 negative-result/conflict 等候选目前转为失败且不保留内容；mandatory semantic review 与中途 Provider 异常的 partial aggregate 仍未完整支持。

## 2026-08-13 — API-first 隔离执行关键节点

### Changed

- 执行优先级从“Codex 原生运行时优先”调整为“文件契约 + 纯 API fresh session 优先”；Codex、OpenCode、Claude Code 等保留为可选 Runtime Adapter 或人工窗口入口，不预先固化最终平台。
- 模型选择收缩为显式 `primary`、`worker` 和少量 `specialist` 槽，不建设价格数据库、评分 Router 或静默 fallback。
- coordinator 默认指向 `primary`；evidence、simulation 和 targeted review Profile 默认指向 `worker`，高风险任务可由 Task/人类显式覆盖。

### Added

- ADR-0010，冻结 API-first 隔离执行、平台可替换和小型模型池边界。
- `ModelPool`/`ModelSlotConfig`：默认不读取环境，只按调用者指定槽位绑定一个 Provider/Model。
- `IsolatedApiSessionRunner`：单 Attempt 内的 fresh context 工具循环，限制模型轮次、工具调用、单轮 fan-out、工具副作用类别、工具结果、单轮输出、累计 token/可得成本和 wall time；handler 当前串行。
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
