# M5-007 H1/H2 实施包

日期：2026-09-16。Task / Evaluation owner：路诚钺。Execution 接口复核：黄毅。实施风险：R2。
基线：`develop@0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`（PR84）。
分支：`feature/m5-007-harness-preflight`。关联：[Issue55](https://github.com/Chengyue-Lu/research-agent-workbench/issues/55)。

本包是已接受 [H1/H2 进入计划](M5-007_ENTRY_PLAN.md) 的实现准备；下述新增文件、接口与测试尚待实现。
M5-007 当前 READY；首次 implementation PR 提出 IN_PROGRESS，H1/H2 完成后继续 H3–H5。

## 1. 入口与交付

已核对 M5-006、M6-008、M11-004/006/007 均 DONE，Gate B SATISFIED。
首个 PR 交付 evaluation-owned 的版本化非执行 Harness plan 与 preflight record，以及从外部 pins
重新加载并验证它们的接口。真实 case、live conformance、production admission 继续由 M5-004 的 Gate 约束。

| 切片 | 输入 | 输出 | 完成判据 |
|---|---|---|---|
| H1 | exact Protocol/Manifest、冻结 case closure、逐 case 公共 payload、调用方给定的计划身份及冻结时间 | 版本化计划；pilot/confirmatory 分组、case × replicate × arm 顺序、独立 Attempt 身份及 retry 规则 | 同输入跨进程产生相同计划；逐项重算而不接受作者覆写；仅含 planned 身份和输入 |
| H2 | H1 plan、A2/A3 frozen/runtime bindings、A4 overlay、overlap、pairwise refs、评价侧 admission verifier | exact plan-bound preflight record，保留派生 eligibility、comparison class 与阻断依据 | 重新加载闭包、验证全部外部绑定并调用既有语义检查；可审计地拒绝或降级不合格输入 |

H1/H2 不调用 Provider、Tool 或 Host 执行入口，不产生 actual facts/Receipt。实际 fresh session、失败后的
retry 触发与全部 Attempt 成本由 H3 实现；预留 retry 身份不能被写成已发生的 Attempt。

## 2. 已核对的复用接口

以下签名与责任在上述基线源码中核对；调用时的外部预期不得从待验证文档自身取值。

| 现有接口 | Harness 的调用责任 |
|---|---|
| `EvaluationInputs(root, schema_root=None)`；`read` / `manifest` / `recheck` | 限定根目录、显式 pin 和受控读取；输出前重验已读取内容，保留缓存后的漂移检测 |
| `validate_protocol(inputs, reference)` | 先验证 Protocol、ADR、Manifest 与 frozen binding；不接受 arm 自带的另一份 Protocol |
| `compile_baseline_plan(document)` | 复用四臂 canonical 编译与 shared-condition digest；它只验证文档结构/语义，外部 reference closure 由 `inputs.manifest(...)` 等加载路径承担；它不编排 case/replicate/retry |
| `produce_a2_qualification(inputs, *, protocol_ref, qualification_id, checked_at, bindings)` | 由 M6 producer 生成 A2 record，随后按固定 Protocol 独立重验；不在 Harness 冒充 M6 producer |
| `validate_qualification(inputs, document, *, expected_protocol_ref)` | A3 组装 `producer=evaluation-harness` 的 record；frozen/runtime Resolution/Snapshot 均来自唯一 Resolver，Harness 不选择 Supply；必须覆盖完整 frozen demand |
| `validate_overlap(inputs, document, *, expected_protocol_ref, expected_case_closure_ref, case_selection_frozen_at)` | 独立提供冻结 case 和时间，重算两侧 case/Task/input/private-oracle closure、身份和哈希交集 |
| `validate_overlay(inputs, document, *, expected_protocol_ref, expected_case_closure_ref, case_selection_frozen_at, admission_verifier)` | 在评价侧验证 exact admission lineage；由授权调用方提供 verifier，记录中的 accepted/eligible 字符串不能代替它 |
| `validate_comparability(inputs, document, *, expected_protocol_ref, expected_case_closure_ref, case_selection_frozen_at, admission_verifier)` | 重载完整 A3 qualification 与各 Bundle/View，再按 A4 exact Task 选择对应比较面；消费重算结果 |
| `compile_baseline_envelope(inputs, *, protocol_ref, task_ref, public_payload_ref, arm_id, envelope_id, accountable_owner, qualification_ref=None)` | H1/H2 复用 M6 的显式 public payload 白名单边界；公共输入与评价侧私有闭包保持分离 |

源码入口：[evaluation](../../../../src/research_workbench/evaluation/)、
[M6 envelope](../../../../src/research_workbench/execution/baseline_envelope.py)。
公开 record verifier `verify_evaluation_record` 的现有 outer-pin 规则继续适用；新接口不复制语义检查。

## 3. H1 实现顺序

1. 从调用方给定的 exact Protocol pin 加载 Manifest、case closure 与公共 payload；验证完整 case/Task
   映射、共享条件和四个 canonical arm，拒绝额外 arm、遗漏、重复或 per-arm override。
2. 消费已有 `case-replicate` / `seeded-permutation-within-block` / `[case_id, replicate]` 约束。
   在新增 plan 契约中明确版本化的排列算法及标准测试向量，固定序列化与 tie-break，禁止依赖进程 hash。
3. 编排 pilot 与 confirmatory blocks；核对 replicates、case count 与 fixed-complete-blocks。
   从显式计划/运行命名空间、case、phase、replicate、arm、retry index 派生互不碰撞的 planned 身份。
   再次执行需要新运行身份；重编译同一计划本身不证明 fresh session。
4. 冻结 max_retries、eligible_failures、retain-all-attempts、include-all-costs 与 drift policy。
   不预先启动 retry，也不把 plan 中的 completed-block 目标计作实际完成。
5. plan 保存在评价侧；treatment 输入单独按白名单产生。private oracle、admission Evaluation/candidate
   closure 和受控解释数据不得被整体序列化进 A1/A2 payload 或传给 Runtime。

## 4. H2 实现顺序

1. 重读 H1 的外部 Protocol/case/time pins；生成 A2 qualification、组装 A3 qualification 并调用共享 validator。
2. 重算 overlap，验证 `Protocol frozen_at <= checked_at <= case_selection_frozen_at`。
   有效但 unresolved 的 assessment 仍不具 primary eligibility；记录结构有效与允许进入目标阶段分开判断。
3. 使用显式 admission verifier 重载 A4 的 candidate→Human Decision→Release→Projection→Supply→Snapshot→Bundle→View
   闭包。synthetic fixture verifier 只在测试注入，不能成为生产默认成功回调。
4. 重算 A3/A4 pairwise class。当前完整 synthetic fixture 的 Method disposition 差异应保持
   `skill-bearing-package`；算法层的 `exact-skill-only` 正例不证明已有可执行的同质四臂实验。
5. 保存 exact plan/validator/input pins 与派生结果。重读 preflight 时重新计算，不能信任自报
   `qualified`、`primary_confirmatory_eligible` 或 comparison class。结果只描述 preflight。

## 5. 拟定写入面与验收矩阵

| 写入面 | 第一版范围 |
|---|---|
| `src/research_workbench/evaluation/harness_plan.py` | plan 编译与重算；具体公开名称随实现确定 |
| `src/research_workbench/evaluation/harness_preflight.py` | A3 record 组装、既有 validators 编排及 preflight 重算 |
| `schemas/v0.1.0/` 的两个独立新 record | plan / preflight；独立 record version、严格 unknown-field 拒绝 |
| Schema catalog / document-kind / validation 接入 | 只注册新契约；CLI 如有必要仅添加非执行入口 |
| `tests/test_evaluation_harness_plan.py`、`tests/test_evaluation_harness_preflight.py` | 新端到端正反例；复用 `system_evaluation_fixtures.py` 与 M6 envelope fixture |
| `tests/coverage_policy.yaml` 与必要 CI inventory | 将新增关键模块及正反测试纳入当前 critical coverage 与选择策略 |
| 本 workstream / implementation docs / TASKS / STATUS | 实现事实、正式 Attempt evidence、风险与 IN_PROGRESS 提案 |

必须覆盖的反例分为六组：

- 外层 pin 替换、读后漂移、missing ref、重复/遗漏 case 或 arm、模型/预算/Task override；
- seed/block/replicate/retry 改写、身份碰撞、pilot eligibility 伪造、提前完成计数；
- plain-arm control/private-oracle 泄漏，任何 Provider/Tool/Host 执行入口被触发；
- structural/fixture-only qualification、Supply 替换、ceiling 放宽、缺失/过期 typed conformance、A3 demand 不完整；
- overlap 身份或内容哈希重合、absent/unknown oracle、freeze 过期、admission callback 缺失/拒绝与 lineage 替换；
- pairwise 自报升级、全局 A3 qualification 不完整、Task 子集错配、预检记录冒充 actual execution。

现有基线测试入口：`test_evaluation_manifest`、`test_system_evaluation_protocol`、`test_evaluation_overlap`、
`test_evaluation_overlay`、`test_evaluation_comparability`、`test_evaluation_contracts`、`test_baseline_envelope`。
进入检查结果见 [工作记录](WORKLOG.md)。这些已有测试验证依赖基线，不是新增 Harness 的验收证据。

## 6. 留痕与停止条件

首次 R2 implementation 开始前建立正式 Task Attempt Archive，固定允许读取集、输出、具名 owner、
预算/停止条件并从当时开始捕获可观察事件；本准备阶段的 Git/Issue/工作记录不得补写成完整实施 Trace。
读取集限本包列出的 Task/计划、M5 contracts/Schema/tests、M6 envelope 与 H2 所需 M11 Bundle/View 接口。

若必须修改已发布 M5-003/006 treatment 或 Runtime 权威、引入第二个 selector、放宽 admission/
overlap 规则才能继续，先持久化最小失败案例，按 Task definition / ADR 流程处理具体缺口。
H1/H2 的 PR 验收要求新增正反例、当前 coverage policy、repository/package/governance 与 cross-owner
接口复核；完成后才进入 H3。完整 M5-007 DONE 仍以 H1–H5 的原 Task 验收为准。
