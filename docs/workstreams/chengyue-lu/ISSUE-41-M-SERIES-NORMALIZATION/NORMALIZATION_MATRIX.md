# M-series normalization matrix

状态：inventory skeleton；结论尚未审计，不具有 Task-definition authority。

## 1. Current Task audit

| Task | Current status | Current objective | Phase | Topic(s) | Dependency valid? | Scope atomic? | Proposed action | Evidence / note |
|---|---|---|---|---|---|---|---|---|
| M0～M10 | pending inventory | — | — | — | pending | pending | pending | 每个现存 Task 必须展开为独立行 |

允许的 `Proposed action` 只有：

- `KEEP`
- `REFINE`
- `SPLIT`
- `SUPERSEDE`
- `STATUS-FIX`
- `PARK`
- `ADD-MISSING-TASK`

## 2. Split / supersession lineage

| Old Task | Problem | Proposed successor Task(s) | Historical identity preserved? | Authority unchanged? |
|---|---|---|---|---|
| pending audit | — | — | pending | pending |

## 3. Missing atomic Task proposals

| Candidate work | Why a Task is needed | Independent producer/consumer surface | Proposed dependency | Phase | Topic(s) | Status | Non-goals |
|---|---|---|---|---|---|---|---|
| pending audit | — | — | — | — | — | PARKED until accepted | — |

新 Task ID 只有在 objective、scope、negative acceptance、authority boundary、owner、risk 和 dependency
均明确后才能提出。架构 prose 中出现一个名词，不构成建 Task 的充分理由。

## 4. Phase aggregation

| Phase | Constituent M Tasks | Entry Gate | Closeout Gate | Navigation only? |
|---|---|---|---|---|
| A～F | pending audit | pending | pending | must be yes |

## 5. Topic ownership mapping

| Topic | Canonical responsibility | Related M Tasks | Owner boundary | Duplicate Task? |
|---|---|---|---|---|
| Topic 1～7 | pending audit | pending | pending | must be no |

## 6. State consistency checks

| Check | Expected rule | Finding |
|---|---|---|
| READY dependencies | every hard dependency is DONE | pending |
| BLOCKED | planned work with an unmet hard/external condition | pending |
| PARKED | outside current execution queue | pending |
| IN_PROGRESS | active implementation work exists now | pending |
| DONE | accepted implementation/evidence satisfies unchanged acceptance | pending |
