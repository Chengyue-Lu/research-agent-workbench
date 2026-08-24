# Skill lifecycle v2

M9-003 把原先混在候选与 accepted Registry 中的状态拆成五个正交轴：

```text
Skill Need refs
      ↓
Intake state
      ↓（不自动晋级）
Evaluation state ── references only ──> Baseline / Trial / Evaluation Record
      ↓
Admission state ── decision_ref ──> Human Decision
      ↓
Runtime eligibility

Lifecycle disposition = current / superseded / retired / legacy-preserved
```

Lifecycle Record 不保存 actual trial result、evaluation result、benchmark metrics 或分数。它只引用
`baseline_ref`、`trial_ref`、`evaluation_record_ref`、`promotion_evidence_refs` 与 `decision_ref`；Phase D
负责真正的 Evaluation Manifest、metrics 和实验记录。

## 状态轴

- `intake`：记录 source/candidate 是如何进入流程，不产生 evaluation 或 admission；
- `evaluation`：`not-planned / planned / in-progress / evidence-ready / blocked / not-reconstructable`；
- `admission`：`pending / trial / accepted / rejected / legacy-imported`，其中 trial、accepted、rejected 必须
  引用 Human Decision；
- `runtime_eligibility`：`ineligible / trial-only / eligible / historical-replay-only`；
- `lifecycle`：`current / superseded / retired / legacy-preserved`。

`eligible` 不是 admission 的别名。一个 Skill 只有同时满足以下条件，才能成为 M9-005 Skill Supply：

- `record_scope = current`；
- evaluation 为 `evidence-ready`；
- admission 为 Human `accepted` 且有 `decision_ref`；
- runtime eligibility 为 `eligible`；
- lifecycle 为 `current`；
- Supply Report 的 `skill_lifecycle_ref` 与 `runtime_eligibility_ref` 精确匹配。

`trial-only` 只能服务隔离 trial，不能进入普通 Snapshot；superseded / retired 不能保持当前 runtime
eligibility。Lifecycle 本身不授予 permission、Claim 或 Human Gate。

## Legacy migration

[`accepted-v1-to-lifecycle-v2`](../../registry/skills/lifecycle-migrations/accepted-v1-to-lifecycle-v2.yaml)
将三个旧 accepted 条目映射为独立 Lifecycle Record，但不修改
[`accepted.json`](../../registry/skills/accepted.json)：

- `literature-evidence-extraction@0.1.0`：`legacy-preserved`；
- `simulation-vv@0.1.0`：`legacy-preserved`；
- `handoff-integrity@0.1.0`：`retired`，由 Task template 与 Human transfer boundary 取代。

三者均保持 `historical-replay-only`，不会因迁移重新获得 new-binding eligibility。缺失的 baseline、trial、
Evaluation Record 与 Human Decision 不会被补造。

迁移逐项固定旧 entry 的 skill/version、manifest path、content hash、package hash 与 legacy lifecycle，
并固定目标 Lifecycle path/hash；它不固定整个 accepted Registry 的唯一或最新 hash。以后 append 新 accepted
entry 时，旧 migration 仍可重放；已映射 entry 的 identity/hash 被改写则阻断。

## 不可变与验证

`lifecycle_id + lifecycle_version` 与 `migration_id + migration_version` 是发布身份。语义变化必须新增版本，
旧文档继续保留。完整性 index 固定 lifecycle ref、path 与 raw-file hash。Repository validator 还会阻断：

- index/path/hash/identity 漂移或未入索引的 Lifecycle Record；
- legacy source entry 或 migration target 漂移；
- trial admission 缺少 trial ref 或 trial-only eligibility；
- runtime eligibility 绕过 evaluation / Human admission；
- superseded/retired 仍声称 current runtime eligibility；
- Skill Supply 引用不存在、不匹配或非 current 的 lifecycle eligibility。

本轮不重新设计 accepted Skill package、Assignment、benchmark、trial runner、Provider/Runtime 或 Human
Decision provenance。旧 Assignment 的精确历史回放继续由现有 accepted Registry 兼容 seam 负责。
