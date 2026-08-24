# Skill Need Contract

状态：M9-002 实现契约

`Skill Need` 是版本化的方法需求对象。它回答“为什么直接 Mode/Task/Tool 仍存在可复用的语义判断
缺口，以及将来什么证据足以判断候选是否值得 trial/promotion”。它不是 Skill candidate、Evaluation
Record、Admission Decision、Assignment、Supply Report 或 runtime eligibility。

## 1. 分层边界

```text
Skill Need
  = gap + direct baseline + expected increment
  + evaluation criteria + required evidence classes

Evaluation / Trial Record
  = actual inputs + outputs + metrics + reviews + observed costs

Lifecycle / Admission
  = evidence refs + decision refs + admission/runtime eligibility state
```

Need 的 `boundaries` 将 `records_trial_results`、`records_evaluation_results`、
`records_promotion_evidence`、`records_runtime_eligibility`、`is_candidate` 与 `is_assignment` 固定为
`false`。Schema 使用 `additionalProperties: false`，所以实际结果、Provider/Tool/Skill binding、availability
或 fallback 不能被附加到 Need。

## 2. Maintainer authority 与创建边界

Skill Need 属于 Method/Maintainer evolution，不属于 Research Runtime。Runtime 对 capability gap、blocked
或 execution failure 最多产生 bounded `CapabilityDiagnostic`；Diagnostic 默认本地、不是 Need，也不能
触发 Candidate、Trial、Promotion 或 Release。

创建或修订 Need 必须由具名 Maintainer 完成独立 triage，证明缺口跨任务复用、需要非平凡语义判断，且
no-Skill/direct Tool/Task template/checker 基线不足。没有该判断时保持 capability gap，不为填充 Registry
自动生成 Need。Runtime bundle 不读取 Need 正文或 Registry；v0.1 Method→Need closure 只属于
`maintainer-full` 和历史重放。参见
[ADR-0019](../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md)。

## 3. Identity 与兼容引用

- 发布身份是 `need_id + version`；相同身份的内容、路径或 hash 不可原位改写；
- `need_ref` 是 M8 Method Resolution 已发布的精确引用别名，不是 `active/latest` selector；
- `registry/skill-needs.json` 固定 `need_ref`、`need_id`、`version`、path 与 raw-byte SHA-256；
- 语义变化发布新版本并使用新的精确 `need_ref`，旧对象和旧 Method 继续解析原始 identity；
- 本轮不修改八份 M8 Resolution 的原始字节。

首批对象严格来自现有 Method 引用：

| Need ref | Origin Action | Baseline capability |
|---|---|---|
| `NEED-ES-SEARCH-PLAN` | `ES-A2@1.0.0` | `literature-search` |
| `NEED-ES-CONFLICT-SYNTHESIS` | `ES-A6@1.0.0` | `research-contract-check` |
| `NEED-SIM-CONVERGENCE-STUDY` | `SIM-A3@1.0.0` | `bounded-compute` |

没有 Method 引用的候选不会为了填充 Registry 被创建。

## 4. 需求内容

每个 Need 必须包含：

- trigger 与 non-trigger；
- `semantic_gap`，分别解释缺失判断、失败后果，以及为何 Mode/Task/direct Tool 不足；
- `baseline`，只允许 `mode-plus-no-skill` 或 `mode-plus-direct-tool`，并引用 M9-001 Requirement；
- `expected_increment` 与明确 non-goals；
- 四臂 comparison requirement：Plain、Plain+Capability、Mode+no-Skill、Mode+candidate Skill；
- evaluation criteria、required evidence classes、coverage requirements 与 stop conditions；
- included/excluded domain scope 和已知 variants。

这些字段规定未来评测必须收集什么，不证明任何 candidate 已执行或产生增量。实际 Evaluation Manifest、
metric、Trial Record 与盲评结果属于 Phase D；M9-003 lifecycle 只引用相应 record/decision。

## 5. 确定性闭合

Repository validation 必须阻断：

- Method 引用未知 Need，或存在 Need/Method 引用却缺少完整性 index；
- index 重复 reference、重复 `need_id@version`、重复 path、path/hash/identity 漂移；
- Need 引用未知 Mode、Action 或 Capability Requirement；
- Action hash 不匹配，或 Action 所属 Mode 不在 Need `mode_refs`；
- evaluation criterion 引用未声明的 evidence class；
- published Need 被删除、移动或按相同版本改写。

通过这些检查只证明结构、引用和职责边界闭合，不证明 Skill 的科研净收益。

## 6. 非目标

M9-002 不实现 candidate discovery、trial runner、Evaluation Record、promotion、retirement、runtime
eligibility、Capability Supply Report、Snapshot、Provider/Adapter/API 或 Runtime。即使当前不存在任何
Skill 实现，Method Resolution 仍保持 `proceed`，no-Skill/direct-tool baseline 仍是一等合法路径。
