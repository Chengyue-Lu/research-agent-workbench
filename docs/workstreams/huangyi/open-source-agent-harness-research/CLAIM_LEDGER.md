# 主张台账

状态：研究证据台账；不修改 TASKS 或 Stable Architecture。

默认 owner：黄毅（`let778750-cpu`）；默认 reviewer：路诚钺（`Chengyue-Lu`）。

类型仅允许 `FACT`、`INFERENCE`、`PROPOSAL`、`CAPTURE_GAP`。`P0` 等严重度词不在本
台账中自动产生项目优先级；PR 候选事实必须显式标为 `candidate-only`。

## 1. Current main / develop

| ID | 类型 | Scope | 主张 | 证据 | 置信度 | 处置 / 目标表面 |
|---|---|---|---|---|---|---|
| `HAR-RWB-F001` | FACT | accepted spec | RWB 是方法感知研究控制与证据链，不是全局 Supervisor；文件是跨会话权威，Execution 只消费冻结契约 | `docs/PROJECT_CHARTER.md:13,39-44`；`docs/ARCHITECTURE.md:9-28,84-86`；ADR-0016 | 高 | `COVERED_BY_EXISTING`；不新建接口 |
| `HAR-RWB-F002` | FACT | accepted spec | no-Skill/direct-tool 已是正式设计路径，但规范存在不等于执行闭环 | Charter:42；Architecture:70；module 05:48-65；Task Schema；`examples/quickstart/task-no-skill.yaml` | 高 | 保持规范；连接 F003 |
| `HAR-RWB-F003` | FACT | implementation | 正式 Schema/CLI/Registry/Receipt/archive 的 no-Skill 路径未闭环 | Registry `active-only` 且 3 项为 legacy/legacy/deprecated；resolver/CLI 拒绝无可选 Skill；Assignment `skill_lock.minItems=1`；Receipt 强制并加载 `skill_assignment_ref` | 高 | `REAL_GAP`；等待 M8-003 consumer seam；禁止 dummy Skill |
| `HAR-RWB-F004` | FACT | implementation | Agent Team 当前只有 policy、metrics 和 native delegation 文档，没有统一 `spawn/send/wait/cancel/collect` 执行 Port | `DelegationPolicy`；Receipt coordination metrics；`adapters/codex.py` 明示不启动 scheduler | 高 | 已知限制，不标 current bug；Team Port 延后 |
| `HAR-RWB-F005` | FACT | API traced path | `run_traced_session` 在网络调用前写 provider-request；capture gap 可 safe-pause；Trace 是单 Attempt/单 writer，Archive marker-last 且可 file-only verify | `session.py:221-285,370-435`；`trace.py:1-6,426-469`；`archive.py:150-468` | 高 | 已有防线，但只适用于该路径 |
| `HAR-RWB-F006` | FACT | cross-runtime | “model-visible 等于 exact logged”不是全局事实：EventSink 可空，Trace 持久化前会脱敏，native Host 尚未接入 | `session.py:140-148`；`trace.py:123-186,508-557` | 高 | PR #20 对应项由 `SATISFIED` 降为 scope-qualified `PARTIAL` |
| `HAR-RWB-F007` | FACT | permissions | Task/Profile/Skill 的 roots/scope 有确定性交集和 preflight，但不是通用 OS/Host sandbox；Codex 子目录 scope 是 advisory | `resolver.py:330-423`；`adapters/codex.py:46-51`；`session.py:41-85,149-169` | 高 | `PARTIAL`；logical admission 不得冒充 machine enforcement |
| `HAR-RWB-F008` | FACT | recovery | 当前 recovery 是 file-only preflight：只接受已 closeout、验证通过的 `safe-paused` Attempt，返回新 ID/目录 seed；不覆盖 crash、incomplete 或 native child resume | `recovery.py:1,65-114,142-266`；context limit 在 `session.py:509-516` 记为 incomplete | 高 | `PARTIAL`；不使用“完整恢复”措辞 |
| `HAR-RWB-F009` | FACT | accepted invariant | runtime completed、contract-satisfied 与 scientific acceptance 已分层 | ADR-0009；`observability/models.py:500-585`；Charter:44 | 高 | `COVERED_BY_EXISTING` |
| `HAR-RWB-F010` | FACT | model | Model Slot 显式选择、无排名和 silent fallback；observed model drift 当前只产生 warning | `pool.py:1-6,181-190`；ADR-0010；`session.py:479-493` | 高 | 普通执行保持 warning；evaluation block 仍是提案 |
| `HAR-RWB-F011` | FACT | capability | `RuntimeCapabilitySnapshot` 字段较粗、引用可选，main 没有 snapshot document Schema | `adapters/runtime.py:12-25`；Attempt/Receipt Schema；`observability/models.py:362-371` | 高 | 有限缺口；v2 字段集不在本 PR 定义 |
| `HAR-RWB-F012` | FACT | release | 根目录无 LICENSE，M0-007 为 BLOCKED，`pyproject.toml` 未声明 license | main 文件树、TASKS、pyproject | 高 | 发布阻塞；不是 Harness 架构决定 |

F003 的限定很重要：底层 `resolve_task(..., ())` 可以形成空锁 Python 对象；问题在于该对象
不能通过正式 Assignment Schema/CLI/Receipt/archive 链。因此不得写成“所有底层代码都
不支持空 Skill”。

## 2. 固定上游机制

| ID | 类型 | Scope | 主张 | 固定来源 | 置信度 | 处置 |
|---|---|---|---|---|---|---|
| `HAR-UP-F001` | FACT | DeepSeek evidence commit | capability seam 区分 definition/provider/consumer；subagent 是可选 capability，team 文档明确实验状态 | `HARNESS-DEEPSEEK-001` 的 architecture/subagent/agent-team 文档 | 中高 | 只提炼 typed capability、mailbox 和显式失败场景；不嵌入整个 runtime |
| `HAR-UP-F002` | FACT | Codex local runtime | App Server 使用 JSONL，要求 initialize→initialized；本机稳定/实验 Schema 分离且实验方法需 capability opt-in | `HARNESS-CODEX-001`；`validation/attempts/A-20260823-CODEX-READONLY-05` | 高 | 作为 Host conformance 证据，不成为 Core 依赖 |
| `HAR-UP-F003` | FACT | OpenCode evidence commit | Server/client 和 session/event 表面可分离；child permission 实现继承 parent deny，但仍不能证明 OS sandbox | `HARNESS-OPENCODE-001` 的 server docs 与 `subagent-permissions.ts` | 中高 | `ADAPT_PROPOSAL`：权限单调收窄与 capture-gap |
| `HAR-UP-F004` | FACT | Pi evidence commit | SDK/RPC 提供最小集成面；durable Harness specification 的多项实现仍返回未实现错误 | `HARNESS-PI-001` 的 SDK、harness spec 和 `agent-harness.ts` | 中高 | 作为 portability canary；不能宣称 durable recovery 已成熟 |
| `HAR-UP-F005` | FACT | Cline evidence commit | SDK 文档分离 loop 与持久 core；产品 subagent 为只读实验能力，plugin squad 不拥有科研方法权威 | `HARNESS-CLINE-001` 的 SDK architecture、subagents 与 squad example | 中高 | 借鉴 queue/compaction/隔离；拒绝 generic orchestration 反向定义 Method |

这些上游事实没有形成同任务 benchmark，也没有证明机制收益。任何“最佳”“最成熟”“第一
顺位”只能写成推断或建议。

## 3. 候选 PR 事实

| ID | 类型 | Scope | 主张 | 置信度 | 处置 |
|---|---|---|---|---|---|
| `HAR-PR20-C001` | FACT | candidate-only | PR #20 未进入 main/develop；reconstruction 只重建最后一个已持久化 provider-neutral `ModelRequest`，不重建 wire bytes、远端状态或全部 Host 请求 | 高 | 保留为候选能力，禁止写成 main 已满足 |
| `HAR-PR20-C002` | FACT | candidate-only | Trace 先脱敏再写，而 provider 收到原请求；候选重建函数从脱敏 body 重建，现有测试无 redaction case | 高 | `NEEDS_CODE_VALIDATION`；增加 redaction round-trip |
| `HAR-PR20-C003` | FACT | candidate-only | reconstruction 函数自身不强制完整 Trace validation/root containment，只校验目标文件和 body hash | 高 | 调用方必须消费 validated result，或函数内部验证完整 Trace；增加 path-escape fixture |
| `HAR-PR20-C004` | FACT | candidate-only | Adoption Matrix 仍含 moving branch 链接，多个 `SATISFIED` 跨越 API/native/team scope | 高 | 固定来源；相关项改 `PARTIAL`；Supervisor 与 portable delegation contract 分开判断 |
| `HAR-M8-C001` | FACT | candidate-only | M8-002 候选只新增 Mode Action contract/registry/validator，不修复 no-Skill execution/archive | 高 | 不抢跑 M8-003；候选 TASKS 状态不是 main 真值 |

## 4. 推断与提案

| ID | 类型 | Scope | 内容 | 置信度 | 处置 |
|---|---|---|---|---|---|
| `HAR-RWB-I001` | INFERENCE | current maturity | current main 不是可执行 Agent-Team harness | 高 | 状态说明，不产生 bug 严重度 |
| `HAR-RWB-I002` | INFERENCE | sequencing | 先闭合单 Agent no-Skill/tool-only golden path，再评估 team，可降低断点复制风险 | 中高 | 与路线同向，但不得抢占 M8-002→M8-003 |
| `HAR-RWB-I003` | INFERENCE | target shape | “研究控制/证据内核 + API reference execution + replaceable Host”大部被 ADR-0010/0016 覆盖；formal Team adapter 是新增假设 | 高 | 前半 `COVERED`，后半 `DEFER` |
| `HAR-P001` | PROPOSAL | post-M8-003 | Resolved Execution View 采用条件 Skill binding；Skill 路径引用真实 Assignment，no-Skill/tool-only 不造假 | 中高 | 独立 Task/ADR；本 PR 不定义公共 Schema |
| `HAR-P002` | PROPOSAL | future Host | 版本握手、Host lifecycle、Capability Snapshot v2、native event/capture-gap | 中 | 先作为 conformance 场景，等待真实消费者 |
| `HAR-P003` | PROPOSAL | future Team | optional TeamExecutionPort、child lifecycle、mailbox | 中 | ROADMAP 明确不在近期关键路径，`DEFER` |
| `HAR-P004` | PROPOSAL | future safety | child permission 单调收窄、outer deadline、child config snapshot、effect sandwich、hash-bound context view | 中 | 对抗 fixture 候选，不宣称 main 已实现 |
| `HAR-P005` | PROPOSAL | research order | Codex→Pi→OpenCode 是调研顺序，不是 Runtime 实施授权 | 中 | M2-006/M6-005 仍 PARKED |

## 5. Capture gaps

| ID | 类型 | 未证明内容 | 处置 |
|---|---|---|---|
| `HAR-G001` | CAPTURE_GAP | 尚未对所有上游机制做逐主张、逐行独立重放 | 未有固定 permalink 的细节不得升级为 FACT |
| `HAR-G002` | CAPTURE_GAP | Open Science 的仓库身份冲突 | 保持 `UNVERIFIED_IDENTITY_MISMATCH` |
| `HAR-G003` | CAPTURE_GAP | 原稿中的通过数、源码行数和测试行数不是本轮 clean-baseline 结果 | 不引用为本轮验收证据 |
| `HAR-G004` | CAPTURE_GAP | 公开 Issue 不证明频率、普遍性或当前版本仍存在 | 只登记 failure-mode signal |
| `HAR-G005` | CAPTURE_GAP | 未做五 Harness 的同任务 benchmark | 不使用“最佳/最成熟”作为事实 |
| `HAR-G006` | CAPTURE_GAP | Codex 探针没有 OS 级网络过滤或全系统写入审计 | 只声明请求集合为零、代理失败保护和采样结果；不声明绝对无外联/外写 |
