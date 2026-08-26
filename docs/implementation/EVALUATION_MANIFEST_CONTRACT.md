# Evaluation Manifest Contract (M5-003)

状态：Active implementation contract

更新：2026-08-26

## 1. 目的与边界

M5-003 v0.1 以四个 Phase D treatment mechanism 为唯一 canonical arm vocabulary：
`plain-agent`、`plain-agent-tool`、`mode-no-skill`、`mode-candidate-skill`。旧的
`single-agent / lightweight / multi-agent` 描述 coordination topology，与 treatment 是正交维度，
因此本契约不保留 `arm_map`，也不推导二者映射。未来若评估 topology，必须作为独立变量另行定义。

本契约冻结比较计划，不运行模型、不记录结果、不授权 live execution。实际案例运行属于 M5-004。

## 2. 共享受控条件

`frozen_conditions` 只出现一次并由四臂共同消费，必须 exact freeze：

- 非空且去重的 `task_packet_refs`；
- `model.pool_ref`、`slot_id`、`provider_adapter` 与 exact `model_id`；
- `host_id / platform / runtime`；
- `max_turns / max_output_tokens / max_parallel`；
- context policy、data policy、`max_input_tokens` 与 initial context refs；
- 非空、去重的 evidence classes。

arm schema 采用 `additionalProperties: false`，不能重新声明 Task、Model、Host、budget 或 context。
因此不同 Task set、Model、预算或 context 的 per-arm override 会在 Schema 与语义检查层 fail closed。

## 3. Treatment bindings

- `plain-agent` 不得携带 Tool/Snapshot 或 Skill binding；
- `plain-agent-tool` 与 `mode-no-skill` 必须各自携带至少一个 exact
  `capability_snapshot_refs`；
- `mode-candidate-skill` 必须携带 exact `skill_binding`
  （ID/version/package content hash/source FileReference）及 `skill_evaluation_ref`；
- 引用闭合检查要求 Snapshot 的 Task 落在 frozen Task set，且 candidate binding 四个字段与
  被 pin 的 Skill Evaluation 一致；Model slot/provider adapter 也必须与 pinned pool 条目一致。

四个 treatment 必须各出现一次；缺失、重复和 legacy `arm_map` 均被拒绝。

## 4. Minimal baseline harness

`rwb eval plan <manifest>` 将通过校验的 manifest 编译为 deterministic、non-executing baseline
plan：按 canonical 顺序输出四臂，为每臂附同一 `frozen_conditions_sha256`，并只保留各自 treatment
差异。`rwb eval check` 同时执行 Schema、语义、FileReference pin 和 treatment closure 检查。

该 plan 是可执行前的冻结输入，不是运行器、Execution Receipt 或 Evaluation Record。

## 5. 指标与证据

`metric_set` 必须逐字复现 `FIXED_METRIC_SET` 的 13 项 M5-003 v0.1 comparison vocabulary；
缺失、重复、定义/单位/方向漂移或额外指标均阻断。这个词表只对本版本 manifest 合同生效，
不声明为仓库外或所有未来 Evaluation 的全局指标 ontology。

fixture：`examples/evals/manifests/EVAL-MANIFEST-M5-003-001.yaml`。专项测试覆盖四臂完整性、
Task/Model/budget/context override、Snapshot 缺失、Skill binding/evidence mismatch、baseline plan
确定性、指标漂移与仓库级交叉验证。
