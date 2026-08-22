# Harness Adoption Matrix（Codex App Server 与 DeepSeek Harness）

状态：Issue #17 adoption spike 结论
基线：main `b1d5a5a`（2026-08-22）
上游一手来源：[openai/codex `codex-rs/app-server/README.md`](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)（main 分支当日版）；[deepseek-ai/deepseek-harness `AGENTS.md`](https://github.com/deepseek-ai/deepseek-harness/blob/master/AGENTS.md)（master 分支当日版，MIT，developer preview）

本页只回答一个问题：这两个上游中哪些机制值得 RWB 以最小改动吸收。判定词汇沿用 Issue #17：`ADOPT`（直接吸收）、`ADAPT`（按 RWB 边界重构后吸收）、`REJECT`（与 RWB 语义或架构边界冲突）、`DEFER`（收益不足或依赖未成熟）。已由 main 现有实现满足的候选记为 `SATISFIED`（附代码证据），不重复迁移。

## RWB 现有基线（判定的对照面）

| 机制 | main 上的位置 |
|---|---|
| 模型 API 缝 | `adapters/models/port.py`：`ModelProvider` Protocol、`ProviderCapabilities`、`Capability`/`DataPolicy`、`CapabilityGap`/`DataPolicyGap`、`ProviderRegistry.require()` |
| 隔离会话循环 | `adapters/models/session.py`：`IsolatedApiSessionRunner`、五种终态（completed / safe-paused / blocked / incomplete / failed）、`ApiSessionLimits`（含 `allowed_tool_side_effects` 冻结绑定） |
| 持久化边界 | `session.py` 的 `SessionEventSink`：`provider-request` 事件在网络调用之前记录（持久化失败阻断发送）；`capture-gap` 事件诚实降级为 `safe-paused` |
| 控制信号分离 | `session.py` 的 `cancel_requested` 回调独立于 `event_sink` 记录流 |
| 文件权威 Trace | `observability/trace.py`：append-only events、hash-bound messages、闭集校验、密钥与隐藏推理的 redaction |
| 恢复生命周期 | `execution/recovery.py`：`prepare_recovery_attempt` 仅在前一 Attempt 通过 file-only replay 后产出 `RecoverySeed`，恢复总是指向新 Attempt |
| 本地 runtime 缝 | `adapters/runtime.py` + `adapters/codex.py`：`RuntimeCapabilitySnapshot` 显式区分 `enforceable_constraints` 与 `advisory_constraints` |

## Adoption Matrix

### 七个优先候选

| # | Upstream | Pattern / Primitive | RWB Target | Decision | Reason | Follow-up |
|---|---|---|---|---|---|---|
| 1 | Codex App Server | Execution Host protocol seam：host 是协议而非库；initialize 握手冻结能力快照；`generate-ts` / `generate-json-schema` 产出与二进制版本绑定的 schema；stable / experimental 表面协商 | Execution / Capability | ADAPT | RWB 是库不是常驻服务（ADR-0001 拒绝自建全局 Supervisor），不引入 JSON-RPC 进程边界；但三点可吸收：(a) 能力快照在会话建立期冻结——`ProviderRegistry.require()` 已同构；(b) schema 可导出且版本绑定——RWB 缺失；(c) enforceable / advisory 约束显式区分——`CodexRuntimeAdapter` 已实现，API session 线可对齐 | Issue：Execution Host seam 显式化（含 trace 事件 schema 导出与版本绑定） |
| 2 | DeepSeek Harness | `Model-visible ⟺ logged`：凡进入模型请求的内容必须可从 session log 重建；新的模型可见输入必须有 session 事件 | Trace | SATISFIED | `session.py` 把 `provider-request` 持久化放在 provider 异常边界之外（"failure must block before network use"）；Trace Core 以 hash-bound envelope 与闭集校验落实同一不变量 | 本页 Spike：request reconstruction 机器验证（把"可重建"从文档声明变成可执行校验） |
| 3 | Codex App Server | Execution Request Snapshot：请求先持久化后发送（rollout JSONL + item 持久化） | Execution / Trace | SATISFIED | `ModelRequest` 为冻结 dataclass；每轮循环以 `replace(bounded_request, messages=tuple(messages))` 生成新快照并整体写入 `provider-request` 事件；本地 runtime 线（`CodexRuntimeAdapter`）只做文件映射不发起请求，该线不适用 | 同上 Spike 一并覆盖 |
| 4 | DeepSeek Harness | Definition → Provider → Consumer capability seam：一个能力缝由 Service Definition / Service Provider / Consumer 三角色完整构成，缺一不拆 | Capability | SATISFIED | `port.py` 同构：`Capability` 枚举（Definition）、`ProviderCapabilities` + `ModelProvider`（Provider）、`required_capabilities(request)` 推导 + `gaps_for` / `data_policy_gaps_for` 消费端闸门（Consumer）。DeepSeek 的"seam 完整性"规则可作为后续 registry 测试启发 | none |
| 5 | Codex App Server | session/event 与 live-control signal 分离：`turn/interrupt`、`turn/steer` 是请求（控制面），`item/*` 是通知（记录面） | Execution | SATISFIED | `cancel_requested` 回调与 `event_sink` 记录流完全分离，控制信号不写入事件流。Codex `turn/steer` 的 in-flight 追加输入在 RWB 中等价于下一轮 `provider-request`（messages 追加后重发），已被快照语义覆盖 | none |
| 6 | Codex App Server | resume / fork / recovery 生命周期：`thread/resume` 按持久化 token 续算；`thread/fork` 以 `lastTurnId` / `beforeTurnId` 定边界；mid-turn fork 记录 interruption 标记 | Research State / Execution | ADAPT（recovery 已实现；turn 级 fork DEFER） | RWB 的恢复语义更严格：`prepare_recovery_attempt` 要求前一 Attempt 通过 file-only replay 才允许 seed，且恢复总是新 Attempt、不改写历史（`RecoverySeed`）。Codex 的 mid-turn fork interruption 标记与 RWB `SAFE_PAUSED` 保留 partial state 同构。turn 粒度 fork 当前无消费者（方法变体重试属 Method plane，未实现） | fork 粒度 DEFER，待 Method plane 出现消费者后重评 |
| 7 | Codex App Server | sandbox / permission / approval 冻结执行绑定：permissionProfile 按 id 选择；approval decision 词汇（accept / acceptForSession / acceptWithExecpolicyAmendment / decline / cancel）；granted 权限 turn 内 sticky | Execution | SATISFIED（执行绑定）+ ADAPT（decision 词汇，转交） | API 线已实现：`ApiSessionLimits.allowed_tool_side_effects` 冻结绑定 + `ClientTool.side_effect` 分级 + write_scope / read_allowlist / tool_allowlist；本地线 `CodexRuntimeAdapter` 已诚实声明 sandbox 不能强制子目录 write scope。Codex 的 approval decision 词汇对 RWB Human Gate 有参考价值，但 Human Gate 属 Method plane（issue 明令不得用普通 approval 代替） | Issue：Human Gate decision 词汇设计（路诚钺 lane） |

### 重点范围其余项

| Upstream | Pattern / Primitive | RWB Target | Decision | Reason | Follow-up |
|---|---|---|---|---|---|
| Codex / DeepSeek | Tool execution pipeline（invocation 记账、输出上限、失败语义） | Execution | SATISFIED | `session.py` 以调用为记账边界（失败与超限仍计一次调用），工具失败只回异常类型，超限结果触发 safe-pause | none |
| Codex / DeepSeek | Session / event log / replay | Trace | SATISFIED | `events.jsonl` append-only + `verify_execution_archive` file-only replay | none |
| Codex | Request reconstruction（从持久化历史重建请求） | Trace | ADAPT | 结构性重建可（`_has_outbound_request` + INDEX 校验）；机器化"从 trace 重建 `ModelRequest` 并验证一致"缺失 | 本页 Spike |
| Codex / DeepSeek | Trace completeness 与 runtime invariants | Trace | SATISFIED | 闭集校验 + 24 个 TRACE-* 风险码 + `capture-gap` 诚实降级 | none |
| Codex | Host protocol / schema versioning（schema 与版本绑定、按连接协商） | Execution | ADAPT | `adapter_version` 字段已存在；缺 schema 导出与版本绑定机制 | 并入候选 1 的 follow-up Issue |
| DeepSeek | Context / compaction（compaction capability + basic provider；compaction 作为 session event） | Research State | DEFER | RWB 以显式 Handoff / Main State 承载跨会话状态（ADR-0009），自动透明压缩与"显式交接可审计"边界冲突。设计约束记录：若未来引入 compaction，必须产出显式 Handoff artifact 且成为模型可见事件（DeepSeek 的做法） | none（设计约束已记录） |

### 低优先级（按 issue 仅记录，不主动迁移）

| Upstream | Pattern | Decision | Reason |
|---|---|---|---|
| 两者 | subagent orchestration / Agent Teams | REJECT | ADR-0001 拒绝自建全局 Supervisor；RWB 的协作原语是 Handoff 而非进程内编排 |
| DeepSeek | workflow engine / background jobs | REJECT | 同上；后台任务不属于可移植核心 |
| 两者 | UI-specific architecture | REJECT | RWB 无 UI 消费者 |

## 本页 Spike：request reconstruction 机器验证

判定依据：候选 2 / 3 的 `SATISFIED` 结论依赖 Trace Core 的结构性校验，"reconstructable"尚无机器证明。Spike 在 `execution` 层新增一个从 Attempt 归档重建最后一个 `provider-request` 的 `ModelRequest` 并与持久化消息哈希比对的函数，配独立测试。这是最小迁移：不新增语义、不改 Trace 格式，只把既有不变量变成可执行断言。实现以独立 PR 交付。

## 上游工程实践（记录，不构成迁移项）

- DeepSeek 的 keyless snapshot 测试（"每个非平凡的模型可见行为变更在同 PR 内附可运行示例的快照"）与 RWB 的合成 conformance 方向一致；RWB 已有 `test_provider_conformance.py`，不重复。
- DeepSeek 的 `resolve(request): Spec` 显式默认化（默认值在 owning implementation 的显式步骤中给出，不藏在 `run()` 内）与 `session.py` 的 `bounded_request = replace(request, max_output_tokens=min(...))` 同构。
- Codex 的 backpressure 有界队列与 `-32001` 可重载错误：RWB 单进程库形态暂无此面；若候选 1 的 host seam 落地则一并考虑。
