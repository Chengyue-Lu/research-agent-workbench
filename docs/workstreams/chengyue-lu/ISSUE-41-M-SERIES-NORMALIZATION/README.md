# Issue #41 — M-series normalization

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- Issue：[M-series normalization](https://github.com/Chengyue-Lu/research-agent-workbench/issues/41)
- 风险：`R2` task architecture / governance normalization
- PR class：`task-definition`
- 基线：`develop@73dcb03b4d4152f36fef5b2dadb3ae0f11d7de7b`
- 分支：`docs/issue-41-m-series-normalization`
- 状态：准备完成；允许开始只读 inventory，canonical Task diff 尚未形成

## 1. 目标

本 workstream 只规范实施层词汇与 Task DAG：

```text
Phase = macro maturity / architecture Gate
Topic = architecture responsibility
M Task = implementation identity, dependency and acceptance
```

完成后，普通开发应能仅通过 `TASKS.md`、当前 Task workstream 和 Task 引用的 accepted contract/ADR
判断允许范围、依赖、责任人、验收与负面边界。`ROADMAP.md` 继续管理 Phase/Topic/Gate，不承担日常任务队列。

## 2. 范围

审计 M0～M10 的每个 Task，并产生：

- normalization matrix；
- `KEEP / REFINE / SPLIT / SUPERSEDE / STATUS-FIX / PARK / ADD-MISSING-TASK` 清单；
- Phase→M 与 Topic→M 映射；
- corrected dependency DAG 与 READY/BLOCKED/PARKED 状态；
- oversized umbrella 与 historical lineage 表；
- 更新后的 `TASKS.md`，以及必要的 ROADMAP/developer navigation 对齐。

重点审计 M3 长期 `IN_PROGRESS`、M5 dependency/status、M6-003 umbrella、M3-009 Phase C 复用，以及
Topic 4 缺失的 Runtime Bundle/Consumer Profile、Resolved Execution View、Thin Execution Host 等实施边界。
这些名称只是审计 candidate，不在准备阶段预先冻结 Task ID 或最终拆法。

## 3. 非目标与 authority ceiling

本 workstream 不修改代码、Schema、Registry、Runtime、Method Resolution、Capability Resolver、Claim、
Human Decision 或 Skill lifecycle，不实施 Phase C、Runtime Bundle、Resolved Execution View、Execution Host、
Recovery 或科学案例。

新增或拆分 Task 只建立 implementation contract，不产生新的 architecture authority。尤其：

- Runtime Task 不获得 supply selection、fallback、Method、Claim 或 Gate authority；
- Recovery Task 不解除 Topic 5 freeze；
- Human Decision Task 不把 Human authority 交给 validator；
- Skill Task 不让 Need 自动产生 Candidate 或 runtime eligibility。

如果拆分必须改变上述权威或 accepted architecture，本 workstream停止，先建立独立 R2 ADR/architecture
decision，接受后再返回 normalization。

## 4. 允许读取与写入面

默认读取：

- `AGENTS.md`、`docs/DEVELOPMENT.md`、`docs/TASKS.md`、`docs/ROADMAP.md`；
- `docs/STATUS.md` 与 developer architecture map，用于识别当前实现覆盖和 Topic owner；
- Task 直接引用的 accepted ADR、implementation contract 和 workstream summary；
- 当前 open PR 的 metadata/path diff，只用于发现并发状态冲突，不把未合并内容当作 canonical truth。

默认写入：

- `docs/TASKS.md`；
- 本目录的 audit matrix、风险台账和 lineage/mapping 输出；
- 必要且最小的 `docs/ROADMAP.md`、`docs/DEVELOPMENT.md` 与导航更新。

禁止修改 `src/`、`schemas/`、`registry/`、`examples/`、测试或其他责任人的 workstream 内容。

## 5. 执行顺序

1. 从当前 `develop` 抽取 M0～M10 inventory，不先改状态；
2. 为每项 Task 填写 current objective/status/dependency/Phase/Topic/atomicity；
3. 单独列出状态矛盾、umbrella scope、缺失近期 Task 与历史 lineage；
4. 先形成 proposal DAG，再检查 READY 的全部 hard dependencies；
5. 检查 Phase/Topic 映射是否只承担导航与 aggregation；
6. 进行一次 task inflation、authority expansion 和 Topic 5 thaw 对抗审计；
7. 重新同步 `develop`，吸收已合并的并发 Task 状态后才生成 canonical `TASKS.md` diff；
8. 运行文档链接、Governance focused tests 与 repository validation；
9. 以 docs-only `task-definition` PR 请求独立 R2/cross-owner review。

## 6. 并发与合并顺序

准备时存在以下并发写入：

| 工作 | 状态 | 与 Issue #41 的重叠 | 处理 |
|---|---|---|---|
| PR #39 / `agent/m4-artifacts-provenance` | open | `TASKS.md`、`STATUS.md` | inventory 可参考；最终 diff 前重新同步，未合并状态不进入 canonical truth |
| `agent/m5-evaluation-baseline` | remote branch，无 open PR | `TASKS.md`、`STATUS.md` 与 M4/M5 workstream | 仅登记冲突风险，不假设其 Task transition 已接受 |
| Phase C task-definition #40 | 已进入当前 `develop` | M10 与 M3-009 | 作为当前 canonical input 审计，不回退其 accepted Task identity |

Issue #41 的最终 PR 不与 feature PR 同时改 Task definition。若并发 feature 先合并，应 rebase/merge 最新
`develop` 并重新计算状态；若 normalization 先进入 review，则相关 feature PR 必须在合并前验证其 Task ID、
状态和 acceptance 仍与 normalization 一致。

## 7. 完成 Gate

- matrix 覆盖 M0～M10 全部现存 Task；
- 所有近期 architecture work 均有明确 M Task，且没有 task-per-concept 膨胀；
- READY 只含 hard dependencies 已 DONE 的 Task；BLOCKED/PARKED 语义不混用；
- 长期 IN_PROGRESS 和 oversized umbrella 均有明确结论；
- DONE identity/definition 不变，split/supersede/refine lineage 可追踪；
- Topic 5 未解冻，Runtime/Method/Capability/Claim/Human authority 未扩大；
- `TASKS.md` 成为唯一 implementation scheduling truth；
- docs-only governance、链接与 CI 通过，并完成独立 R2 review。
