# Issue #41 — M-series normalization

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- Issue：[M-series normalization](https://github.com/Chengyue-Lu/research-agent-workbench/issues/41)
- 风险：`R2` task architecture / governance normalization
- PR class：`task-definition`
- 审计基线（历史）：`develop@73dcb03b4d4152f36fef5b2dadb3ae0f11d7de7b`
- 实施分支（历史）：`docs/issue-41-m-series-normalization`
- 状态：PR #42 已以 `6b16129` 合入 `develop`；M0～M10 inventory、M11 task-definition、review
  remediation、M-group reservation 与双图规则均已接受，本目录现为 normalization 审计快照

[`NORMALIZATION_MATRIX.md`](NORMALIZATION_MATRIX.md) 固定的是上述审计基线和当时的 before/after proposal，
其中 `READY/BLOCKED/PARKED` 不是当前状态。实时 Task truth 只读取 [`TASKS.md`](../../../TASKS.md)。

## 1. 目标

本 workstream 只规范实施层词汇与 Task DAG：

```text
Phase = macro maturity / architecture Gate
Topic = architecture responsibility / authority domain
M-group = implementation family / development route
Mxx-yyy = atomic implementation identity, dependency and acceptance
```

完成后，普通开发应能仅通过 `TASKS.md`、当前 Task workstream 和 Task 引用的 accepted contract/ADR
判断允许范围、依赖、责任人、验收与负面边界。`ROADMAP.md` 继续管理 Phase/Topic/Gate，不承担日常任务队列。

## 2. 范围

审计 M0～M10 的每个 Task，并产生：

- normalization matrix；
- `KEEP / REFINE / SPLIT / SUPERSEDE / STATUS-FIX / PARK / ADD-MISSING-TASK` 清单；
- Phase→M 与 Topic→M 映射；
- M12～M14 future family reservation 与 canonical M-series-only construction map；
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

后续 feature 实施保持一 dependency layer 一组独立 implementation/acceptance evidence，但 PR 是
integration/review unit，不要求与 Task 1:1。M11-001→002→003→004 的 Bundle、View、Host、
Trace/Receipt 可在同一强耦合 module workstream 中按 dependency DAG、独立 commit/evidence 和相关
owner review 原子集成。`PARKED → DONE` 的 R2 exception 仍只用于满足 canonical module-level 条件的 DAG。

## 6. 事实基线与合并顺序

本轮只审计 `develop@73dcb03b4d4152f36fef5b2dadb3ae0f11d7de7b` 已合并内容。开放 PR、远端
feature branch、候选 fixture 和其中声称的 Task transition 均不进入 matrix，也不预留 canonical 状态。

最终 PR 前重新同步当时最新 `develop`，但只吸收已经合并的事实；发生 `TASKS.md` 冲突时重新执行全量
状态/依赖检查，而不是用未合并分支补丁预测结果。Issue #41 保持 docs-only `task-definition`，不能与
feature implementation 混合。

## 7. 完成 Gate

- matrix 覆盖 M0～M10 全部现存 Task；
- 所有近期 architecture work 均有明确 M Task，且没有 task-per-concept 膨胀；
- READY 只含 hard dependencies 已 DONE 的 Task；BLOCKED/PARKED 语义不混用；
- 长期 IN_PROGRESS 和 oversized umbrella 均有明确结论；
- DONE identity/definition 不变，split/supersede/refine lineage 可追踪；
- Topic 5 未解冻，Runtime/Method/Capability/Claim/Human authority 未扩大；
- Topic 5 membership 只覆盖改变 Handoff/context/safe-pause/recovery/continuation 语义的 Task；Phase C
  chain 是 activation prerequisite 而非 member，M11-003/004 使用 Trace/Receipt 但也不属于 Topic 5；
- M11-006 由 View/Capability semantic owner 维护，不形成 Skill-specific Runtime seam；
- `TASKS.md` 成为唯一 implementation scheduling truth；
- Phase/Topic architecture map 与 M-series-only construction map 用途分离，reservation 不进入 Task 状态机；
- docs-only governance、链接与 CI 通过，并完成独立 R2 review。

## 8. 当前验证证据

- baseline 79 个 Task 与 matrix 79 个 Task exact-set 一致；新增 M11-001～006 后共 85 个唯一 Task；
- DONE 行相对 baseline 零修改；未知 dependency 为 0；READY dependency violation 为 0；
- `tests.test_documentation` + `tests.test_pr_governance`：76 tests PASS；
- full repository suite：432 tests PASS，3 skipped；
- repository validation：154 documents validated，0 errors，0 warnings；
- `git diff --check`：PASS。

这些结果证明文档闭包、Task DAG 结构和现有仓库回归通过，不替代独立 R2 review，也不证明 M11
implementation、live Provider、Phase C 科学表示或 Topic 5 recovery 已完成。

## 9. PR #42 R2 review remediation

| Review finding | Decision |
|---|---|
| Task 与 PR 粒度 | Task 保持 implementation/acceptance identity；PR 是 integration/review unit。同一强耦合 module/workstream 的预定义 DAG 可按 canonical module-level 条件原子集成，不再专门禁止 M11-001→004 同 PR |
| Topic 5 membership/freeze 歧义 | Phase C chain 只作 activation prerequisite；membership 只按 Handoff/context/safe-pause/recovery/continuation objective；M11-003/004 也明确不属于 Topic 5 |
| M11-006 形成 Skill-specific Runtime seam | owner 改为路诚钺；Task 改成 eligible Skill supply 到统一 View/Capability 语义的映射，Host 无 Skill 特例 |
| M6-004 是否 hard-depend M11-004 | 否；它只依赖 M6-001/002 与 external live authorization，验证 Provider/session 而非 Runtime E2E |
| TASKS owner 总述过时 | 补齐 M4/M5/M10、View/Capability semantics 与 M11 Runtime implementation 的具名分工 |

## 10. Issue #41 latest comment：future M-group reservation 与双图

本轮将施工词汇补成 `Phase → Topic → M-group → Mxx-yyy` 四层，但没有建立第四套 planning truth：

- `ROADMAP.md` / Developer Architecture Map 只解释 Phase、Topic、authority、Gate 与 M-group aggregation；
- `M_SERIES_IMPLEMENTATION_MAP.md` 只用 M-group 展示普通施工路线，并展开已定义的原子 Task DAG；
- `TASKS.md` 仍是状态、exact dependency、owner、scope 与 acceptance 的唯一真值；
- M12 Execution Continuity & Recovery、M13 Strategy & Governed Evolution、M14 Product / Release Closure
  只作 namespace reservation，没有状态或原子 Task；
- reservation 必须经 accepted activation Gate、existing-group insufficiency evidence 与独立 docs-only
  `task-definition` 才能激活；当前不解冻 Topic 5、Strategy、Release，不扩大任何 authority，也不推测 M15+；
- construction map 保留跨 group 的 `M3-009` 历史 identity，不为编号连续而重命名。
