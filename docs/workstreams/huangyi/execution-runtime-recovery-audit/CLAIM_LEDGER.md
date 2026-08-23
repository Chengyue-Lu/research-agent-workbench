# 主张台账

状态：`AUDIT-EXEC-RUNTIME-001` 的审计台账。`fact` 只表示证据所支持的有限事实，不表示该项
已进入 Stable Architecture；`proposal` 必须经过目标 SSOT 的正常审查才能生效。

严重度与可能性采用 `低 / 中 / 高 / 严重` 和 `低 / 中 / 高`。PR #23 项只适用于固定的
`b1d5a5a..57b3d24` 候选差异，不能外推为 `main` 已有行为。

| ID | 类型 | scope | 主张及限定 | 固定证据 | 置信度 | 严重度 × 可能性 | 处置 | 目标 SSOT | owner / reviewer |
|---|---|---|---|---|---|---|---|---|---|
| ERR-SCOPE-001 | fact | audit | 原稿“4/5”是个人导航中的 Runtime 域与 Execution/Recovery 域，不是 TASKS M4/M5。 | `SRC-HUANGYI-DRAFT`、`SRC-CHATGPT-SHARE` | 高 | 中 × 高 | 统一更名为 `execution-runtime-recovery`。 | 本 workstream | 黄毅 / 路诚钺 |
| ERR-AUTH-001 | fact | main | Runtime 只能执行已批准 Task/Method/Capability/Policy；不能批准 Claim、Method、权限放宽或 Human Gate。这里是既有不变量，不是新缺陷。 | `SRC-CANONICAL-MAIN`：ADR-0016 | 高 | 严重 × 中 | 保留为回归约束。 | ADR-0016 | 黄毅 / 路诚钺 |
| ERR-BASE-001 | fact | main | ADR-0010 已完成 API-first isolated baseline 选择；外部框架调查不能重开 Gate F。 | `SRC-CANONICAL-MAIN`：ADR-0010 | 高 | 高 × 中 | 调查只提供机制证据。 | ADR-0010 | 黄毅 / 路诚钺 |
| ERR-STATE-001 | fact | main/future | Session termination、Attempt/Receipt、Task contract satisfaction 与 Research acceptance 是四个不同状态面；Runtime `COMPLETE` 不足以证明 Task 完成。 | `SRC-CANONICAL-MAIN`：ARCHITECTURE、ADR-0016 | 高 | 严重 × 高 | 保持分层；增加对抗回归。 | Architecture/Schema/tests | 黄毅 / 路诚钺 |
| ERR-ASSIGN-001 | fact | main | Receipt/archive/K-API-2 路径仍对 Skill Assignment 有硬耦合；这是真实但有限的实现缺口，不代表所有 Attempt/Handoff 都必需 Skill。 | `SRC-CANONICAL-MAIN`：代码、schema、测试 | 高 | 高 × 中 | M8-003 后设计条件引用；旧 v0.1.0 只读兼容。 | 新 Task + Schema/ADR | 黄毅 / 路诚钺 |
| ERR-EGRESS-001 | fact | main/PR23 | Model Session 会把 Tool Result 送入后续 Provider 请求；当前边界没有按每次出口同时核对 source、classification、destination、authorization、transformation 和 retention。 | `SRC-CANONICAL-MAIN`：`session.py`；`SRC-PR23`：runner/compiler | 高 | 严重 × 高 | 缺少显式 resolved egress policy 时默认 BLOCK；首次请求及每次 Tool Result 回注前检查。 | Execution Boundary Contract + tests | 黄毅 / 路诚钺 |
| ERR-PERSIST-001 | fact | PR23 | PR #23 的独立 transcript 保存完整 request/response；本地工具正文可能同时进入 provider request 与持久化记录。 | `SRC-PR23`：runner/closeout | 高 | 严重 × 高 | hard-block；洁净实现只保存最小、已授权、可追溯内容。 | 替代 K-API-2 | 黄毅 / 路诚钺 |
| ERR-REDACT-001 | fact | PR23 | PR #23 在没有扫描证据时生成“未发现敏感数据/未 redaction”的结论；`credential-free` 不能推出 `safe-to-persist`。 | `SRC-PR23`：closeout | 高 | 严重 × 高 | 禁止未知写成 false；记录扫描状态、转换和 retention。 | Trace/Receipt/archive tests | 黄毅 / 路诚钺 |
| ERR-TRACE-001 | fact | PR23 | PR #23 建立第二套 transcript，未通过 M3-008 `SessionEventSink` 形成同一 Trace 事件链。 | `SRC-PR23`：runner/closeout；`SRC-CANONICAL-MAIN`：Trace surface | 高 | 高 × 高 | hard-block；替代实现接回统一 Trace，model-api/native-agent 满足同一最低事件集。 | M3-008 + 替代 K-API-2 | 黄毅 / 路诚钺 |
| ERR-PERM-001 | fact | PR23 | PR #23 没有在副作用前完整交叉执行 read-only、effective permission、allowed roots、Task write scope 与 Attempt 输出目录。 | `SRC-PR23`：compiler/runner | 高 | 严重 × 高 | hard-block；文件创建前进行 preventive check。 | Execution policy + tests | 黄毅 / 路诚钺 |
| ERR-HANDOFF-001 | fact | PR23 | PR #23 会把模型自由文本 summary 自动升级为 Handoff fact，破坏 fact/inference/proposal 分层。 | `SRC-PR23`：closeout | 高 | 高 × 高 | hard-block；无稳定来源时只保留 summary。 | Handoff contract + tests | 黄毅 / 路诚钺 |
| ERR-MODEL-001 | fact + proposal | PR23/future | PR #23 没有在 Receipt 中结构化记录 requested/observed model。未来策略建议普通执行漂移告警，evaluation/benchmark 漂移阻断。 | `SRC-PR23`；`SRC-HUANGYI-DRAFT` | 中高 | 高 × 中 | 先补 observed 字段与可验证规则；策略由契约审查批准。 | Receipt Schema + policy | 黄毅 / 路诚钺 |
| ERR-RECOVERY-001 | fact | main/PR23 | context-limit 结束态是 `incomplete`，现有恢复只接受 `safe-paused`；PR #23 的 `--from-state` 只固定 immutable input，并非 recovery。 | `SRC-CANONICAL-MAIN`：ADR-0009、`recovery.py`；`SRC-PR23` | 高 | 高 × 高 | 分开命名和测试 base-state pin、resume-check、salvage recovery。 | Recovery contract + tests | 黄毅 / 路诚钺 |
| ERR-ENFORCE-001 | inference | main/future | 现有约束混合 preventive、detective、advisory 与未知状态；统一写成“已强制”会夸大保障。 | `SRC-CANONICAL-MAIN`、`SRC-HUANGYI-DRAFT` | 中高 | 高 × 高 | 建立 enforcement matrix；逐项以负面测试证明。 | 独立 Task/ADR/tests | 黄毅 / 路诚钺 |
| ERR-NATIVE-001 | proposal | future | native-agent 的隐藏平台状态、delegation 与回放边界可能弱于 model-api；尚无证据证明当前代码存在该 bug。 | `SRC-CHATGPT-SHARE`、`SRC-HUANGYI-DRAFT` | 中 | 高 × 中 | 仅作为 conformance 场景和外部调查维度。 | Future evaluation | 黄毅 / 路诚钺 |
| ERR-REPLAY-001 | fact | main/future | audit replay 是依据工件重建决策链，不等于模型逐比特重放。 | `SRC-CANONICAL-MAIN`：ADR-0009 | 高 | 中 × 高 | 保留术语边界；禁止把 provenance 验证描述成 bitwise replay。 | ADR/tests/docs | 黄毅 / 路诚钺 |
| ERR-FRAMEWORK-001 | proposal | future | Persona 侵占 Method、双 Router、隐式 Skill/Tool、自动 critic/retry 与隐藏会话状态是未来集成风险，不是当前 bug。 | `SRC-CHATGPT-SHARE`、`SRC-HUANGYI-DRAFT` | 中 | 高 × 中 | 进入机制调查与 conformance catalog；不照搬框架。 | Future evaluation | 黄毅 / 路诚钺 |
| ERR-HOLD-001 | proposal | future | 匿名 user 提出暂缓扩建，GPT 给出 Architecture Hold；共享页不能证明发言身份或双方决议。 | `SRC-CHATGPT-SHARE`、`SRC-MEETING-MINUTES` | 高（来源）/ 低（归因） | 高 × 中 | 采用“只暂停扩张和 Execution 重接入”的候选解释，待双方批准。 | ADR/TASKS（若批准） | 黄毅 / 路诚钺 |
| ERR-TASKS-001 | fact | PR23 | PR #23 修改 M6-003/M6-004 状态和验收边界；候选分支无权单方面重定义项目需求。 | `SRC-PR23`：TASKS blob 与 base diff | 高 | 严重 × 高 | PR #23 do-not-merge；替代分支不得继承这些状态。 | GitHub PR + TASKS governance | 黄毅 / 路诚钺 |
| ERR-ORDER-001 | fact + human decision source | current planning | main/develop 共同基线的下一主线是 M8-002，随后 M8-003；审计与机制调查可并行但不应成为其前置。 | `SRC-CANONICAL-MAIN`：TASKS；`SRC-MEETING-MINUTES` | 高 | 高 × 高 | 本审计不改主线；保持独立 PR。 | TASKS | 黄毅 / 路诚钺 |
| ERR-MECH-001 | proposal | future | hash pin、原子 closeout、file-only verification 和 provenance 有可借鉴价值，但不能连同 PR #23 的任务状态、风险目录或证据包继承。 | `SRC-PR23`、`SRC-MEETING-MINUTES` | 高 | 高 × 高 | 仅从最新 `develop` 洁净重写并重新测试。 | 替代 K-API-2 | 黄毅 / 路诚钺 |

## 台账使用规则

- `fact + proposal` 的事实部分与建议部分分别审查；建议不能借事实置信度自动生效。
- 新证据不得覆盖旧 revision；新增 source ID 并记录适用 commit。
- `Disposition` 进入 ADR、Schema、TASKS 或代码后，在本表补充目标 revision；此前都不是正式验收。
- 严重度高不等于优先于 M8；当前顺序仍由 [`TASKS.md`](../../../TASKS.md) 决定。
