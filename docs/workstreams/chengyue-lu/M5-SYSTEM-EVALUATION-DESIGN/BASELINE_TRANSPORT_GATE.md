# M5 Baseline Transport Architecture Gate

Gate：`M5-BASELINE-TRANSPORT-ARCHITECTURE-GATE`

结果：本记录进入 `develop` 且承载它的 exact-head R2 PR 获两位 owner 审查并合并时为 `SATISFIED`；
在 feature branch / 未合并 PR 中为 `PENDING (not satisfied)`

责任人：

- Evaluation / estimand：路诚钺（GitHub `Chengyue-Lu`）
- Execution transport / closeout：黄毅（GitHub `let778750-cpu`）

## 1. Exact decision pin

| Field | Value |
|---|---|
| Decision identity | `PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND@1.0.0` |
| Path | `docs/decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md` |
| Raw SHA-256 | `64edd73c44bc77f326a90c51e0a8cbf5fd28c4bbf1a5e18aca7f50250ce21a12` |
| Audit base | `dd2454b5595e33a12aa058529358d46d311a08c4` |
| Integration PR | [PR #56](https://github.com/Chengyue-Lu/research-agent-workbench/pull/56) |
| Review / merge evidence | exact-head cross-owner review 与 merge event；PR 未合并前 Gate 为 `PENDING (not satisfied)` |

首次发布前的 review 修订会使旧 hash、CI 与 review 失效，本记录必须更新为新的 exact bytes 并重新审查；
该 identity 首次进入 `develop` 后，任何语义变化必须发布新 Decision version 与新 Gate record，旧版本继续保留，
不得只更新 hash 以掩盖已发布语义变化。

## 2. Frozen arm mapping

```text
A1 plain-agent          → M6 isolated session + M6-008 baseline closeout
A2 plain-agent-tool     → M6 isolated session + exact Tool + M6-008 baseline closeout
A3 mode-no-skill        → M11 Core no-Skill/direct-Tool path
A4 mode-candidate-skill → M11 projection-backed Skill path
```

A1/A2 exact-pin 完整 Task 作为实验身份，但只将独立版本、`additionalProperties=false` 的正向白名单
`provider_visible_payload` 交给 Provider；完整 Task、actor/permission/budget/pin 保留在不可见的
`transport_enforcement_metadata`。`active_modes`、`agent_profile`、Task `required_capabilities`、
Mode/Action/Method/Capability Requirement/Resolution/Snapshot control、Skill/private-oracle 与未知 Task 字段
默认不可见；A2 唯一例外是 exact-pinned Tool definition/interface 及调用结果。Snapshot/Method ref 只作
evaluator-side provenance。A3/A4 保持 M11 exact Mode/Method contract。

checked-in M5-003 A2/A3 Snapshot 均为 `structural-replay`、`execution_input=false`，只可用于 synthetic
contract test。M5-004 正式 A2/A3 必须使用 `runtime-execution`、`execution_input=true` 且 implementation、
availability、boundary 与 typed conformance 全部闭合的 exact Snapshot；versioned/hash-pinned
`ArmExecutionQualificationRecord@1.0.0` 必须 exact-pin Manifest/arm、Task、Requirement、frozen/runtime
Resolution/Snapshot、Supply/component/implementation/interface，A3 还须闭合 exact Mode/Action/Method，且
permission/data-egress/side-effect ceiling 只能等价或收窄；否则 BLOCK。M5-006 拥有 shared contract/validator，
M6-008 在 M5-006 DONE 后只产生 A2 record。Capability Resolver 是 A3 runtime Resolution/Snapshot 的唯一
producer/selector；M11 只验证并消费 exact Snapshot，M5-007 引用两端对象组装 A3 record并对两类 record
独立重算。

## 3. Estimand and claim ceiling

- primary：`A4 − A2`，只解释为完整 RWB/M11 package 相对 tool-enabled simpler Agent/M6 baseline 的
  system-level difference；其中包含 transport difference；
- secondary：`A2 − A1` 为同 M6 transport 的 Tool increment；`A4 − A3` 只有在 versioned/hash-pinned
  `A3A4PairwiseComparabilityRecord` 证明 Mode/Action/Method、non-Skill Capability/Supply、Tool/procedure、
  provider-visible interface 与相关 boundaries exact-equal、唯一 delta 为 admitted Skill extension 时，才可称
  Skill conditional increment；否则降级为 Skill-bearing package / bundled effect 或 unavailable；
- `A3 − A2` 只能解释为 Mode/Method **加 transport** 的组合差异，不能称 pure Mode effect；
- `A4 − A1` 是完整栈支持性 contrast，不替代 primary；
- 所有结果都受 exact case/Task/model/provider/host/budget/context/data boundary 限定，不产生一般科研增益、
  production readiness、promotion、Claim 或 Human acceptance 结论。

## 4. Preserved invariants

- M5-003 v0.1 Schema、fixture、arm identity 与 read boundary 不变；其 structural fixture 不获得 live eligibility；
- A1/A2 不创建 dummy Method、dummy Snapshot 或 Skill Assignment；
- A2 不从 Tool Snapshot 的 Method provenance 获得 treatment control；
- Capability Resolver 仍是 A3/A4 唯一 Supply selector；
- M5-006 只冻结 shared qualification 与 pairwise comparability contract；M6-008 不拥有 A3/M11，M5-007
  不拥有 Supply selection 或 estimand 重写 authority；
- M6/M11 均不 fallback、reselect、rebind 或静默切换 transport；
- Decision、Trace、Receipt 与 Harness 不产生 permission、Task completion、Claim、Human、admission、promotion、
  pruning 或 Topic 5 authority。

## 5. Implementation dependency introduced by the decision

Gate A 对 M5 只解锁 Protocol，并不证明 baseline transport 已实现；同一 accepted task-definition 另行创建
Execution-owned `M6-008` 实现入口，负责：

- 正向白名单的 A1/A2 treatment-visible envelope 与 enforcement metadata 分离；
- 正式 A2 runtime-execution Tool qualification record 与 treatment non-substitution；
- 每次 provider request/Tool invocation use-boundary pin reload/TOCTOU 阻断、transport trusted clock 与
  preventive/detective 分离；
- exact Provider/Adapter/Model/Runtime/Host/Tool actual facts及其 typed Trace 独立佐证；
- completed/post-call-failed/preflight-blocked Trace/Artifact/Validation/Receipt replay；
- 永久固定 `task_completion=false`，且不复用 mandatory Skill Assignment。

因此本 Decision 的 DAG delta 为（M6-008 完整 dependency/acceptance 仍以 `TASKS.md` 为准）：

```text
ADR-0020 accepted
  └─ M5-006 READY
       └─ M6-008 PARKED → READY after M5-006 DONE
          (also depends M5-003 + M6-002 + M6-006 + M11-004)

M5-006 + M6-008 + M11-004 + M11-006
+ M5-SKILL-CLOSEOUT-REPLAY-GATE
  → M5-007 BLOCKED until every dependency is satisfied
```

Gate B、M5-001/002、M4 provenance、M6-004 live conformance 与 `A4-RUNTIME-ADMISSION-GATE` 均不被
本记录解除。Issue #55 在 Gate A 合入后仍保持 OPEN。

## 6. Adversarial review checklist

| Attempted shortcut | Required result |
|---|---|
| 将 raw Task 的 `active_modes` / Method control 发送给 A1/A2 | BLOCK |
| `agent_profile`、未知 Task 字段或 enforcement metadata 进入 provider payload | BLOCK |
| 以 dummy Method/Snapshot 让 A1/A2 进入 M11 | BLOCK |
| A1 暴露 Tool；A2 替换 frozen Tool | BLOCK |
| 正式 A2 使用 `structural-replay` / `execution_input=false` / fixture-only Tool | BLOCK |
| 正式 A3 使用 `structural-replay` / `execution_input=false` / fixture-only Supply | BLOCK |
| A2/A3 qualification 改变 Task/Requirement/Supply/component/implementation/interface、相关 A3 Mode/Action/Method，或放宽任一 ceiling | BLOCK |
| M6-008 或 M11 产生/选择 A3 Resolution/Snapshot，或替 Capability Resolver 选择 A3 Supply | BLOCK |
| A3/A4 除 admitted Skill extension 外还有 Method、non-Skill Supply、Tool/procedure、interface 或 boundary 差异，却报告 pure Skill increment | BLOCK |
| A3/A4 pairwise record 为 `skill-bearing-package` | 只允许 bundled/package interpretation |
| A3/A4 pairwise record 为 `not-comparable` | secondary contrast unavailable |
| 只在 session 初始 preflight 重验 pins、实际 Tool use 前不重验 | BLOCK |
| Driver 自报 elapsed/actual binding 取代 trusted clock 或 Trace fact | BLOCK |
| 以 legacy Skill Assignment/Receipt 冒充 baseline closeout | BLOCK |
| 把 Gate A/ADR 当成 `M6-008` 实现证据 | BLOCK |
| 把 `A3 − A2` 报告为 pure Mode effect | BLOCK |
| 缺 `M6-008` 或 Gate B 时启动 M5-007 | BLOCK |
| 仅按 ADR 的合法双传输边界启动 M5-006 Protocol 设计 | PASS |
