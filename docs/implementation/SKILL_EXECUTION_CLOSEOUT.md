# Skill execution closeout 1.0.0

M11-007 为 projection-backed Skill execution 提供 Host report、实际消费事实与独立文件 replay。
执行继续使用同一个 `execute_frozen_view()`；调用方显式选择 `skill-execution@1.0.0` closeout contract。
该选项只确定事实与报告契约，Driver 绑定、Supply selection 和执行入口仍遵循既有 View/Host 边界。

## 契约版本

以下新对象使用 Schema 格式 `0.1.0` 和必填的 `contract_version: 1.0.0`。对象 kind 与版本共同分派；
未知版本、混入旧 Core 对象或新增 authority 字段均拒绝。已有 Core 与 legacy Schema 文件保持不变。

| kind | 作用 |
|---|---|
| `skill_execution_consumption` | 实际读取的 Supply / Projection identity、path、SHA-256，及 Skill identity/hash、唯一 Skill component |
| `skill_execution_host_report` | 原 Host 生命周期、actual binding、Provider/Tool facts 与上述实际消费记录 |
| `skill_execution_trace_fact` | `actual-skill-execution-binding` typed fact，在 use boundary 持久化上述记录及实际 binding |
| `skill_execution_receipt` | exact Bundle / Snapshot / Resolution / View / Host / Trace / Artifact / Validation refs，以及 requested/actual 消费事实 |

Schema 路径为 `schemas/v0.1.0/skill-execution-*.schema.json`。Core 仍使用
`build_generic_execution_receipt()` / `validate_generic_execution_receipt()`，Skill 扩展使用
`build_skill_execution_receipt()` / `validate_skill_execution_receipt()`。

## 执行侧事实来源

已绑定 Driver 在消费边界调用 `read_skill_execution_inputs()`，传入实际消费的 exact Supply pin。
reader 按同一次字节读取验证 Supply 及其 Projection，重算 identity/component 一致性，并返回不可变的
`ObservedSkillInputs`。执行消费该对象的 `supply` / `projection`，避免重新打开路径引入不同字节。
reader 不发现候选、不重新选择 Supply，也不读取 Projection 所描述的 Maintainer 历史路径。

消费前调用 `record_skill_execution_use()`，写入两个 hash-pinned content-read 事件、typed fact 文件和
该文件的创建事件。随后执行 bounded operation，将同一观测的 `consumption` 放入
`ExecutionDriverResult.actual_skill_consumption`。实际 Provider/Tool 事件继续使用现有 Trace recorder。

Host 负责检测完成结果与 selected View 的一致性，并保留返回的真实事实；closeout 只消费已经 frozen
的 Trace。Replay 核对 exact 输入读取、fact 文件 hash 与事件先后，拒绝在 Provider/Tool 调用后补写
消费事实。Host report 与 typed fact 的实际 binding / Supply / consumption 必须一致，并能由输入文件重算。

## 生命周期与 replay

| 生命周期 | Receipt 资格与结果 |
|---|---|
| completed | actual binding / Supply / Projection / component 与 selected View 相同；输出与 Validation subject closed set 完整；仅 `action-capability-slice-only` |
| post-call-failed | 保留独立 Trace 与文件佐证的 actual drift、输出和 Host diagnostic；completion 为 `none` |
| preflight-blocked | Driver 未执行，无 actual consumption/binding、Provider/Tool 调用或实际执行 fact；completion 为 `none` |
| driver exception / incomplete capture | 保留 Host diagnostic 与可得事实；拒绝 Receipt eligibility |

所有 Receipt 均为 `task_completion=false`。Replay 的输入仅为 Receipt path、外部 SHA-256、project root
和 Schema root；它从 Receipt 自身 refs 重新加载并验证 Bundle、Snapshot/Resolution、View 和全部执行
证据，不需要原始 Python 对象、Agent 会话或 Provider/Tool。Receipt 自报的字段必须与重建结果完全相同。

`requested_skill_consumption` 表达已冻结选择；`actual_skill_consumption` 与 `actual_binding` 表达可重放的
执行事实。M5 consumer 在评价侧将实际结果与 M5-006 overlay 比较。失败 replay 可以保留不相等的实际
事实，不因此成为成功 A4 样本或 overlay equality 证明。

## 验证与接受

`tests/test_skill_execution_closeout.py` 的合成链使用真实 Bundle / View / Host、消费时 Trace、输出与
实际执行的 deterministic subject checker，再构建 Receipt 并在 fresh process 中独立 replay。
覆盖 Provider/Adapter/Model/Runtime/Host 漂移、Supply/Projection 漂移、Tool component、缺失或延迟事实、
重签两份自报记录、Artifact/Validation subject 缺项以及版本混用等反例。Core 与 legacy 回放另有现有回归。

测试证明有界执行事实与文件契约闭合。Gate B 的具名实现接受和审查仍以
[Gate record](../workstreams/chengyue-lu/M11-SKILL-CLOSEOUT-GATE/GATE.md) 为准；真实 Provider readiness、
生产 Skill admission 与科研净增量分别由既有 Task/Gate 决定。
