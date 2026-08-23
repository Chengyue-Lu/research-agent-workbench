# RWB Harness 机制采纳矩阵

状态：研究建议；不修改实时任务、公共 Schema 或已接受架构。

## `COVERED_BY_EXISTING`

以下原则已被 RWB 接受，不重复发明接口：

- 文件权威、五个 plane 与 Execution 不拥有 Method/Claim/Human Gate；
- 不建立全局 Supervisor、固定研究 DAG 或第二套科研状态数据库；
- no-Skill/direct-tool 是正式规范路径；
- Runtime termination、Attempt/Receipt、contract satisfaction、scientific acceptance 分层；
- explicit model slot、无 silent Provider fallback；
- recovery 产生新 Attempt，而不是续写旧 Attempt；
- validator 只证明结构与机器检查，不宣布科学正确。

## `ADAPT_PROPOSAL`

以下机制值得转译为 RWB 语义，但必须等待 M8-003 后的 consumer seam 或独立 ADR：

| 机制 | 来源启发 | RWB 转译边界 |
|---|---|---|
| version/schema handshake | Codex App Server、OpenCode Server | Host 报告实际协议与能力；缺失或不兼容显式失败，不进入 Core 私有协议 |
| Host lifecycle | Codex、Pi RPC、OpenCode | 可替换 adapter 的 launch/send/wait/cancel/collect 候选；不让 Host 改写 Method |
| sanitized request snapshot | DeepSeek session log、RWB Trace | 保存可审计 projection 与 capture-gap；不承诺 provider wire-byte replay |
| Capability Snapshot v2 | DeepSeek capability seam、Codex Schema | 与 Task/Method/Tool/Provider/Model hash-bind；字段须由真实 consumer 驱动 |
| native event normalization | Codex/OpenCode/Cline | 缺失事件记 capture-gap；UI stream 不自动等于完整 Trace |
| permission monotonicity | OpenCode child deny、Cline read-only child | parent∩child∩Task∩Host；logical admission 与 OS enforcement 分栏 |
| derived context view | Pi/Cline compaction、RWB file authority | context 是可重建投影，不成为第二真值数据库 |
| effect receipt | Pi effect sandwich、RWB Receipt | unknown effect 不自动重放；实际副作用与授权分开记录 |

## `DEFER`

- TeamExecutionPort 的生产实现、durable mailbox 与 child task board；
- native Codex launch/collect、Pi/OpenCode/Cline/DeepSeek Host Adapter；
- background Agent、workflow engine、插件市场和 UI 集成；
- salvage recovery、长期 thread continuity、自动 critic/retry；
- Router、并行团队拓扑和跨 Runtime migration。

延后不是否定价值，而是缺少 M8-003 后稳定 consumer、真实科研案例或独立 Task/ADR。

## `REJECT`

- 全局 Supervisor、第二真值数据库、固定研究 DAG 或全局消息总线；
- 为 no-Skill 路径创建 dummy active Skill 或空 Assignment；
- prompt-only permission 被描述为机器强制；
- implicit Skill/Tool/Agent activation 与 silent fallback/router；
- unknown-effect 自动重放、默认 full-history fork；
- 用 team consensus、Runtime success 或 Trace 完整性替代科学正确性；
- 未固定来源、许可证和版本就推广上游机制；
- 把任一外部 Harness 整体嵌入 RWB Core。

## `NEEDS_CODE_VALIDATION`

- PR #20 的 redaction round-trip、完整 Trace validation 与 path containment；
- native Host event coverage 和 capture-gap；
- write scope 的机器 enforcement；
- model-pool 声明与 adapter 实际能力的一致性；
- no-Skill/tool-only/Skill 三条正式 execution/archive fixture；
- Codex 以外 Host 的只读握手与版本不兼容行为。

## PR #20 差异

| PR #20 原方向 | 调整后判断 | 原因 |
|---|---|---|
| model-visible/logged | `PARTIAL` | EventSink 可空、持久化前脱敏、native Host 未接入 |
| request snapshot/reconstruction | `PARTIAL + NEEDS_CODE_VALIDATION` | 只重建最后一个 provider-neutral 请求；无 redaction/path-escape fixture |
| capability seam | `PARTIAL` | Runtime snapshot 粗、引用可选、无 document Schema |
| permission binding | `PARTIAL` | 有逻辑交集与 preflight，但非通用 OS sandbox |
| recovery/fork | `PARTIAL` | 仅 safe-paused file-only preflight，不覆盖 crash/incomplete/native child |
| global Supervisor | `REJECT` | 与项目边界冲突 |
| portable delegation contract | `PROPOSED ADAPT / DEFER` | 与拒绝 Supervisor 不是同一判断，但不在近期关键路径 |

PR #20 修订只能在本工作流经 develop 验收后吸收这些差异；不得把完整研究包并入 PR #20。
