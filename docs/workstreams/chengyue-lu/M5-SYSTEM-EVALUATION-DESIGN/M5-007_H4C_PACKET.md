# M5-007 H4c：measurement association 与配对分析输入

日期：2026-09-27。Task / Evaluation owner：路诚钺。Execution 接口复核：黄毅。风险：R2。
进入基线：`develop@97d3b3d3141419b34ad47e0f42d9f01d0dfbd535`。
准备分支：`feature/m5-007-harness-analysis`。跟踪：[Issue55](https://github.com/Chengyue-Lu/research-agent-workbench/issues/55)。
状态：实施准备完成，H4c 代码与契约尚未实现；本包细化已接受 M5-007，不改 Task 定义或验收。

## 1. 进入依据和首个交付

PR86/89/90 已接受 H1–H4a；PR96 的 H4b 已合入且实际 protected push CI SUCCESS。
exact source、合并与审核方式见 [进入记录](attempts/M5-007-H4C-ENTRY-001/README.md)。
M5-007 保持 IN_PROGRESS；H4c 完成后进入 H5 的持久化全链证明和整体接受。

首个 implementation slice 先闭合 measurement → run/case/phase/replicate/arm/Attempt/slice →
方法及观察/冻结 review 来源，再交付从这些记录独立重建的配对分析输入。两者构成 H4c 候选的
完整交付；单独注册新 Schema 或通过 measurement 结构验证不足以收口 H4c。

初始候选消费现有 H3/H4a/H4b 输出。旧 H3 没有整臂外层时间或完整成本的项目保持 unavailable；
本轮不以增加运行时采集作为关联层的 hard dependency。确需新观察方法时，另作独立版本化的
评价侧 sidecar，按 [H4 总包](M5-007_H4_PACKET.md) 验收，不能原位改写旧记录。

## 2. 当前接口与新增关联责任

| 已有接口 / 输入 | 已证明内容 | H4c 必须补齐 |
|---|---|---|
| `system_protocol.validate_measurement(inputs, document, expected_protocol_ref=...)` | 13 个固定 metric、四种 status、unit/range、evidence bytes hash；estimated 命名方法 | evidence 属于哪个真实 run/Attempt、方法是否重建同一数值、case/arm/replicate 是否一致；不能只相信 `case_id` 或同名文件 |
| `harness_evidence.validate_harness_evidence` | H3 独立 replay、完整 slots/slices/retries、actual 与 frozen qualification/overlay 比较 | 关联每条 measurement 的目标、分母、scope 和真实 lifecycle；阻止 planned View 冒充观察 |
| H4b `validate_review_reveal` 及其 freeze/package/mapping 链 | 完整具名冻结、可信顺序、exact refs、source-to-projection pins | Human 来源只取这组冻结输入，不能自行评分或复用被替换的 review/map |
| `overlap.validate_overlap` / `comparability.validate_comparability(stage="analysis-input")` | 两侧 closure、freeze 时序、eligibility 和预注册 comparison ceiling | 在分析入口重载并重算；外部目标 case/freeze/pins 仍由调用方给定，结合 actual closure 后再配对 |
| `EvaluationInputs.read/read_bytes/recheck` 与 validator identity | 受控读取、外层 pins、源码/Schema 身份、读后漂移拒绝 | 新关联与分析记录纳入同样的重建和身份检查；待验记录不能自行缩短闭包或提供 authority |

拟议公开实现位于 `evaluation/harness_analysis.py`，提供 metric evidence 的编译/独立验证和
analysis input 的编译/独立验证。具体 record kinds、版本化 Schema 和函数签名在实施提交中固定。
外部 context 至少包含完整 Harness/Review/Freeze contexts、exact execution/evidence/reveal refs、
measurement refs、方法与观察来源 pins，以及既有 admission/projection/Human verifier。
缺少外部权威不能以默认 True 或记录中的自报批准补齐。

association 必须绑定现有 `evaluation_measurement@1.0.0`，保持该已发布文档不变。每个关联明确
measurement ref、metric/status/unit、run/case/phase/replicate/arm、Attempt 集合及适用 slice、
method identity/version/pin、观察或冻结 review refs。核对所有关联键与来源，不用作者给出的 run
标签代替独立重建。method 不能只是一段解释文本：measured 要有可验证的数值/范围/分母来源；
若没有已验收的计量方法，不能从任意 JSON 数字或 synthetic integer 是否正确推导科研指标。

## 3. Measurement 完整性

沿用固定 13 项：`method-violation`、`claim-overreach`、`provenance-error`、
`counterevidence-omission`、`human-correction-distance`、`omission-rate`、`rework-count`、
`lookup-count`、`h2-distortion-rate`、`cascade-rate`、`context-loaded`、`cost`、`completion-time`。
每个计划评价单元对每项指标显式给出 measured、estimated、unavailable 或 not-applicable。
缺项、重复 association、不同 case/replicate/Attempt 的来源混用均拒绝。

- measured 需重建方法、计量范围、单位、分母和 observation 来源；estimated 需固定 estimation
  method 及证据。unavailable/not-applicable 为 null 且有原因，不能补零。
- Human 指标消费冻结审查；合成审查只作 synthetic 序列证据，不产生真实 Human 结论。
  无法支持某个固定指标的现有 rubric 保持该指标 unavailable。
- count 必须整数，ratio 需明确分子/分母及 [0,1] 范围。characters 与 tokens 不互换；币种和
  计量口径不兼容时不隐式汇总或换算，不把 Provider 的 tokens 自动解释为全部 loaded context。
- cost 闭包包含 preparation、supervision、review、correction、recovery 和所有失败/retry。
  局部 API usage/价格仅证明其局部范围，不把缺失人工成本改为零或完整总成本。
- completion-time 需要同一 Attempt 的 Harness 外层可信开始/结束观察。Host 区间、dispatch
  deadline、各 slice 耗时之和和 review 接收时间均不是完整整臂 wall time 的替代。

## 4. Analysis input 的独立重建

1. 验证 H4a/H4b 完整闭包及外部 selected refs，再逐项重建 association 和 method/source pins；
   所有失败、retry、blocked、stopped、not-started 都进入明确的记录集合。
2. 在分析入口再次重算 overlap、资格/overlay、pairwise 和 actual identity。phase=confirmatory
   本身不产生 primary eligibility；admission-overlap、unknown、unresolved 和 pilot 均不得进入
   held-out primary。synthetic purpose 的确认性资格始终 false。
3. 以 case/phase/replicate 和同一 metric/unit 配对。必须和冻结 plan 的 slots/block 集合一致；
   缺失和不完整 block 显式诊断，不能静默删掉失败 arm 后声称完整确认性计划。Attempt 聚合和
   terminal selection 只用冻结 Protocol 已明确的规则，不能事后挑成功或最佳 retry。
4. 保存 Protocol 原样的 `case-replicate-paired-difference`、逐指标差异/区间输入、
   `case-cluster-bootstrap`、confidence level、resamples、seed、
   `report-by-status-no-imputation` 和 secondary descriptive rule。本切片闭合可重建输入，
   不另选统计参数、不据合成数据宣称科学收益。
5. 保持 `A4 − A2` 的跨 transport primary 和 `A2 − A1` Tool 条件增量；`A4 − A3` 只在
   exact-skill-only 时作 Skill conditional increment，skill-bearing-package 降为 bundled
   effect，not-comparable 保持 unavailable。实际漂移不得静默改写预注册解释。

Research Integrity 不被效率抵消；不产生单一加权总分、自动 scoring/promotion/pruning 或
Claim/Task/Human 决定。H4c 的 synthetic 分析输入仍受 M5-008/004/005 原 Gate 限制。

## 5. 写入面、首批正反证据和接受

写入限定为新 evaluation analysis 模块、必要版本化 association/analysis Schema、相应
tests/fixtures、document-kind/validation/catalog/coverage 集成和本 workstream/implementation/STATUS。
CLI 只有在确需暴露完整外部 context 时增加；不改变 M5-003 vocabulary、Runtime、Supply selection
或已发布 H3/H4a/H4b 契约。通用测试组织维护候选 `1b97af2` 独立交付 CI 线，不作为本切片依赖。

| 验收主题 | 正例 | 必须拒绝或保留缺失的反例 |
|---|---|---|
| 关联与计量方法 | 同一真实 run/Attempt 和 pin 下的可重建 measured/estimated，以及有原因的 null status | unrelated evidence、换 case/arm/replicate/Attempt、伪造数值/分母、重复/缺 metric、无 method、单位错配 |
| 成本/时间/生命周期 | 所有 Attempts 和失败保留；无外层时间/人工成本时 unavailable | 删失败 retry、择优聚合、缺值补零、Host/slice 区间冒充外层时间、不兼容币种混加 |
| Review 与完整配对 | 同一 freeze/reveal 及 exact expected set，完整四臂 pairing；缺项以诊断保留 | review/map/reveal 替换、提前揭盲、不完整 block 被标为确认性、pilot/overlap/unknown 升级 |
| 当前 comparison/actual | analysis-input 独立重算，按既有 ceiling 输出解释 | 预注册 exact comparison drift、actual Projection/Supply 漂移、作者自报 eligibility 或 package effect 冒充 pure Skill |
| 独立 replay / 身份 | 新进程从持久化 records 重建，无 Provider/Tool/Host/checker 执行 | 依赖原会话、网络/执行端口调用、hash/validator/Schema 漂移、authorization 中输入改变 |

新增 Schema/源码会改变现有全 catalog/保守源码身份。实施测试必须在 exact candidate 上重新生成
synthetic Protocol/assessment/H3/H4a/H4b inputs；旧 archives 保持原字节与原 validator 身份，
不能为迁就新闭包回填 hashes 或改写旧证据。

实施开始前在独立 Attempt 固定 Task snapshot、输入 pins、Agent Profile、Skills（可为空）、
预算、停止条件与可观察事件捕获。scoped 正反 tests/冷 replay、现行 critical/changed coverage、
repository/package/governance 与当前 policy 选择的 hosted CI 按各自身份验收；请求黄毅 R2
cross-owner review。H4c 接受后再进入 H5，不因本准备包或 scoped PASS 将 M5-007 置 DONE。

若必须更改固定指标/Protocol、Task acceptance、权威或执行 ownership 才能继续，保留具体
最小失败证据并转 Task/ADR review；不得以缺测量数据为由放宽现有 Gate。
