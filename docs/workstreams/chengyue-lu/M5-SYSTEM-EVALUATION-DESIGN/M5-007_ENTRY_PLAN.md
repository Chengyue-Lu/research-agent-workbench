# M5-007 Synthetic Harness 进入计划

更新：2026-09-16。Task / Evaluation owner：路诚钺。Execution 接口复核：黄毅。风险：R2。

## 进入节点

已接受基线为 `develop@0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`。
M6-008 实现已由 PR75 合入，PR84 已接受 M6-008 DONE 与 M5-007 READY。
此计划细化现有 Task，不增加 Task、不改写其目标、依赖或验收。
首个开发分支为 `feature/m5-007-harness-preflight`；具体接口、写入面与负例见 [H1/H2 实施包](M5-007_H1_H2_PACKET.md)。

| 前置 | 已接受依据 | Harness 消费接口 |
|---|---|---|
| M5-006 DONE / Gate A | PR71，ADR-0020 与 [Protocol contract](../../../implementation/SYSTEM_EVALUATION_PROTOCOL.md) | frozen Protocol/Manifest、qualification、overlap、overlay、pairwise validators |
| M6-008 收口 | PR75 与 [M6 closeout](../../huangyi/M6-BASELINE-EXECUTION/CLOSEOUT.md) | A1/A2 allowlisted envelope、fresh isolated session、actual facts 与 baseline replay |
| M11-004/006 DONE | Core Host/Trace/Receipt 与 projection-backed Skill mapping | 唯一 Resolver 产生/选择的 exact Snapshot→Bundle→View；Core closeout |
| M11-007 DONE / Gate B SATISFIED | PR81/82 与 [Gate record](../M11-SKILL-CLOSEOUT-GATE/GATE.md) | versioned Skill closeout、typed use facts、独立 replay |

真实 M5-001/002 dossiers、M6-004 live conformance 与 A4 production admission 不阻塞 synthetic Harness
实现，继续阻塞 M5-004 正式执行。此计划不运行真实模型、不选择真实案例、不声称系统科研收益。

## 首个开发 PR 的明确范围

首先完成下表 H1/H2：新增 evaluation-owned 的版本化 Harness plan / preflight 记录，加载现有 frozen
Protocol/Manifest，确定每个 case × arm × replicate 的独立 Attempt 身份和输入，重算全部资格与 freeze
条件。这个切片只准备执行，不调用 Provider/Tool/Host，不将预检通过写成 actual execution。

先复用 `evaluation/manifest.py::compile_baseline_plan`、`system_protocol.py::validate_protocol`、
`qualification.py::validate_qualification`、`overlap.py::validate_overlap`、`overlay.py::validate_overlay`
和 `comparability.py::validate_comparability`。实现前核对它们的当前签名与调用方责任；不创建第二个
Supply selector，不复制 validator 以绕开 shared contract。H1/H2 合入仍不代表完整 M5-007 DONE。

## 实施切片与验收

下列 H1–H5 为同一 M5-007 的施工顺序，不是新 Task；可分 implementation PR，最终一起收口。

| 切片 | 交付 | 必须出现的正反证据 |
|---|---|---|
| H1 冻结 Harness plan | 从 exact Protocol/Manifest/公开 case refs 确定性编译计划；消费预注册 seed/block/randomization、replicates、retry/stopping/drift 规则；明确评价侧与 treatment 输入 | 同输入同计划；任何 frozen pin 漂移或 arm override 拒绝；每个 replicate/retry 独立 Attempt/session；plain arms 不得收到控制字段或 private oracle |
| H2 评价侧 preflight | A2 加载 M6 producer 已产生的 qualification ref 并独立重验，A3 引用唯一 Resolver 的两端对象组装 record，均独立重算 M5 qualification；A4 overlay/admission lineage、overlap 与 pairwise 从 exact closure 重算 | structural-only/fixture-only binding、替换 Supply、ceiling 放宽、缺 typed conformance、未知/缺失 oracle、过期 freeze 或身份/哈希重叠均按既有规则阻断/降级；重算结果不能由自报 eligible/exact-skill-only 覆盖 |
| H3 四臂 synthetic 执行 | A1/A2 调 M6，A3 调 M11 Core，A4 调 M11 Skill；每臂使用 fresh Attempt，冻结 refs 与 actual lifecycle 分开保存 | 四条路径有实际本地调用与独立 cold replay；completed、post-call-failed、preflight-blocked 区分；失败/retry 保留，不能择优丢弃；禁止 fallback/reselect/rebind |
| H4 评价证据与分析输入 | 统一 evaluation-side run record，独立重放并比较 actual binding 与冻结 plan/qualification/overlay；生成盲审材料、受控 reveal map、metric evidence 与 analysis input | planned View 不能冒充 actual fact；漂移或伪造 replay result 被拒绝；盲审阶段隐藏 arm/Skill/cost/token/RWB 标签；measured/estimated/unavailable/N/A 保持，缺值不填零；Human Review 未完成不能提前 reveal |
| H5 集成收口 | 一套持久化四臂 synthetic vertical proof、正反 replay、Schema/validator/必要 CLI 集成、critical coverage 和 R2 接受 | 分析输入阶段重算 pairwise/overlap 与实际身份；全链哈希漂移/越权/生命周期反例；当前 policy 选择的 CI、repository/package/governance 与双方接口复核通过 |

## 解释与读取边界

- `A4 − A2` 保持含 transport difference 的 primary system-level contrast；`A2 − A1` 是同 transport Tool 条件增量。
- `A4 − A3` 只有 `exact-skill-only` 才允许 Skill conditional increment；`skill-bearing-package` 降级为 bundled effect，`not-comparable` 令该 secondary contrast unavailable。`A3 − A2` 不解释为 pure Mode effect。
- confirmatory freeze 前必须独立提供目标 case/time，校验 `checked_at <= case_selection_frozen_at` 并重算 case/Task/input/private-oracle intersection；unknown/absent/unresolved 不得当 held-out，overlap 不进入 primary confirmatory analysis。
- private oracle、candidate/Evaluation/admission lineage 仅由获得读取授权的评价侧消费；Runtime 只取得选定的 published projection 与执行闭包。禁止直接加载 candidate 目录或向 treatment arms 泄漏 oracle。
- synthetic fixture 只证明本地契约与执行 plumbing，不能被复用为正式 runtime conformance 或 production admission；M5-004 的 real execution 入口必须重新验证其全部外部 Gate。
- 保留 Research Integrity 不可被效率抵消及三层 decision hierarchy；不实现自动 Human scoring、单一 weighted aggregate score、promotion/pruning 或 Claim 接受。

## 文件与交接边界

实现写入 `src/research_workbench/evaluation/` 的独立 Harness 模块、独立版本化 Schema、对应 synthetic
tests/fixtures 与 coverage inventory。必要的 catalog/validation/CLI 集成随实际接口确定。
M5-003 已发布 Manifest/arm/metric set 和 M6/M11 Runtime contracts 保持当前边界；若发现必须改变这些
定义的缺口，先停在具体失败证据和 task-definition/ADR review，不能在 Harness 中加旁路。

PR84 交付的状态、证据绑定和进入计划已接受。首次实现 PR 开始时将 M5-007 置为 IN_PROGRESS；
完成 H1–H5 的整体验收后才提出 DONE。Issue55 继续 OPEN，直到 Harness 的内部重算与分析输入闭包被接受。
