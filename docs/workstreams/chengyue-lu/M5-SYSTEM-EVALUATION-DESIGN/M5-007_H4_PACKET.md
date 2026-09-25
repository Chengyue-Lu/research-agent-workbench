# M5-007 H4：评价证据、盲审与分析输入实施包

日期：2026-09-19。Task / Evaluation owner：路诚钺。Execution 接口复核：黄毅。风险：R2。
基线：`develop@171d4654f88e926f239cdf25bc8168109b81f391`（PR89）。
分支：`feature/m5-007-harness-evidence`。跟踪：[Issue55](https://github.com/Chengyue-Lu/research-agent-workbench/issues/55)。

本包是现有 M5-007 的 H4 实施细化。H4a actual evidence 已进入 implementation candidate；
H4b/H4c 待实现，M5-007 保持 IN_PROGRESS。当前候选及本地验证见
[H4a Attempt](attempts/M5-007-H4-001/README.md)。
H1/H2 已由 PR86 接受；H3 与整臂 dispatch deadline 修复已由 PR89 接受并合入。
接受依据及环境检查见 [H4 entry record](attempts/M5-007-H4-ENTRY-001/README.md)。

## 1. 交付顺序

| 节点 | 交付及输出边界 | 进入下一节点的条件 |
|---|---|---|
| H4a 实际证据核对，首个实施提交 | evaluation-side run evidence；每个 case/replicate/arm/Attempt/slice 的冻结资格、独立 replay、实际 binding/Projection/Supply、生命周期与 artifact pins 闭合；包含全部失败/retry/停止 | 完成四臂和三种生命周期的正反回放；拒绝 planned-to-actual 替换、漏 slice、遗漏失败与身份错配 |
| H4b 盲审与揭盲顺序 | 有限格式的匿名 review package、评价侧私有映射、具名 Human Review freeze 与受控 reveal record；严格绑定同一 evidence set | 全部预定 review slots 冻结且外部 Human authority 验证通过，才允许生成 reveal；无缺项、重复、替换或事后改分 |
| H4c metric evidence 与 analysis input | 沿用固定指标及四种 measurement 状态，逐条关联实际 Attempt、review 和观察证据；重新验证 overlap/pairwise 与实际身份，生成配对分析输入 | case/replicate 配对、retry 成本、完整 block 和冻结分析规则可独立重算；不完整或不合格数据不能取得 confirmatory eligibility |

三个节点仍属于 M5-007，可按依赖顺序在同一 H4 分支提交。首个 implementation PR 的范围以实际
交付为准；H5 负责最终持久化完整 vertical proof、必要 CLI/仓库/包集成及 R2 收口。
M5-008 的 live pilot 是后继任务，真实 Provider、账户、案例和 A4 admission 仍有各自 Gate。

## 2. 已核对的接口及其限制

| 接口 | H4 的调用责任 |
|---|---|
| `harness_execution.replay_harness(inputs, result_ref, *, context, admission_verifier)` | 外部提供 exact H3 result 和 HarnessContext；重算 H2、完整计划/日志、M6/M11 Receipt、dispatch deadline 与 retry 顺序。接口不调用执行端口；H4 不接收一个自报 replay PASS 字符串 |
| M6 `verify_baseline_receipt`、M11 Core/Skill receipt validators | 消费重载的实际 Trace/Host/Receipt 与全部 slice，不用计划 View 填 actual binding。H4a 在 Evaluation 层统一证据；两种 transport 的执行契约保持各自语义 |
| `validate_qualification`、`validate_overlay` | 再验 A2/A3 资格与 A4 pre-run lineage；将实际消费的 exact 身份逐项关联到已验证闭包。外部 admission verifier 不能从记录中取出或默认成功 |
| `validate_overlap` | 使用调用方独立提供的 case closure/freeze time 重算两侧身份和哈希交集；原记录的 eligible 字段不直接获得信任 |
| `validate_comparability` 的 `analysis-input` stage | 消费 exact preregistered record，重算冻结比较面并拒绝 drift。该接口没有接收 H3 actual facts；H4 必须另外完成实际证据核对后才 join 比较结果 |
| `system_protocol.validate_measurement` | 复用 metric vocabulary、状态、单位、范围和 evidence hash 校验。它目前只读 evidence bytes，不证明 evidence 属于目标 run/case/arm/Attempt，也不证明数值测量方式；这些关联和方法证据由 H4 追加验证 |
| `EvaluationInputs.read/read_bytes/recheck` | 独立外层 pins、受控读取、读后漂移检测；新 record 的 validator/Schema identity 按现有模式固定并重验 |

当前源码入口为 [evaluation](../../../../src/research_workbench/evaluation/)，共享要求见
[Protocol contract](../../../implementation/SYSTEM_EVALUATION_PROTOCOL.md) 和
[Harness contract](../../../implementation/SYSTEM_EVALUATION_HARNESS.md)。

## 3. H4a：实际证据记录

新增版本化 evaluation-owned record，具体公开名称在实现提交中固定。输入必须包含外部选定的
Protocol、H3 result、plan/preflight、case/freeze context 与 admission verifier。输出同时绑定 run、
case、phase、replicate、arm、retry/Attempt 和 slice identity；保留原始 receipt/trace/host/artifact refs。

- 先独立 replay，再读取其中验证过的 actual facts；对 A3/A4 覆盖该 Task 所有必需 slices。
- completed 要求实际 binding、Supply，以及 A4 实际 Projection/Skill 与其 frozen qualification/overlay
  相同；原始 planned View 只作比较目标，不能作为 actual evidence。
- post-call-failed 保留可被 Trace 佐证的真实 drift 和 diagnostic；这是有效失败记录，不能被重写为
  equality/success。preflight-blocked 保留零调用、无实际消费；没有事实时不能伪造空成功值。
- H3 整臂超时停止仍保留已经完成的 slices 和后续零调用 blocked Receipt。未启动的后续 slots
  单独标识；不能补成运行记录、删掉失败后形成完整 block，或仅挑选成功 retry。
- 对记录层的伪造/哈希漂移直接拒绝；对有效但失败的执行保留证据并阻断其完成/分析资格。
  exact preregistration 后的实际漂移必须阻断相关分析，不静默降级后继续确认性比较。

H4a 本身不需要盲审者或真实 case；使用已接受 H3 synthetic ports 产生的新证据做正反验证。

## 4. H4b：review package 与受控 reveal

盲审包与评价侧私有映射分别存储。reviewer 只得到受控的公共任务说明、匿名输出和预注册 rubric；
不得获得 arm、Skill/RWB 标签、execution identity、cost/tokens、原始 Trace/Receipt 路径或可从公开
plan/seed 直接反推 treatment 的别名。映射使用冻结的私有、不含 treatment 语义的 opaque identities。

先支持有明确字段白名单和 projection 规则的 synthetic artifact 格式；只重命名文件不足以完成
匿名化。输出正文或嵌入元数据可能携带 treatment 标识时，要求可审计的授权匿名化处理，无法闭合
则阻断该 review package。保留私有 source-to-projection pins，不能为去标识悄悄改写评价内容。
任意自由文本的完全盲化不由字符串过滤自动证明。

Human Review 是外部具名输入；验证回调/authority 由授权调用方提供，没有默认成功实现。
review freeze 精确覆盖预定匿名 slots，显式记录不可评价项及原因。全部 blind reviews 必须冻结，
然后才产生绑定该冻结集合的 reveal record。freeze/reveal 的可信观察时间由外部调用上下文提供，
冷回放再次提供 expected pins/time；待验文档不能自选时间或仅凭 `approved=true` 获得权限。
提前 reveal、部分 reviews、改分后继续复用 reveal、映射替换或非具名审查均拒绝。

synthetic Human-review fixture 仅测试序列约束，不能声称是实际 Human 评价或科研结论。

## 5. H4c：measurement 与 analysis input

新增评价层 association 将现有 `evaluation_measurement@1.0.0` 精确绑定到 run/case/replicate/arm/
Attempt（及必要的 slice）、measurement method、观察/审查来源及版本。13 个固定指标逐项提供
measured、estimated、unavailable 或 not-applicable；后两者为 null，不能补零。

- 仅当实际证据能证明计量值、范围、单位、分母和来源时记 measured；estimated 必须命名方法。
  Human 指标只消费冻结 review，不自动评分；同名文件或无关 evidence ref 不能成为测量依据。
- 成本闭包包含 preparation/supervision/review/correction/recovery 和全部失败/retry；币种或 token
  口径不兼容时不做隐式换算。缺失调用数据、价格/用量或人工成本时显式保留缺失状态。
- 跨 transport 的 completion-time 使用 Harness 外层可信观察，不能把 Host 区间或各 slice elapsed
  相加冒充完整整臂耗时。H3 旧记录缺失这类观察时保留 unavailable；需要新增观察时使用独立
  版本化 sidecar 和评价侧观察点绑定同一 Attempt，先验收采集方法，不改写旧 H3 archives。
- analysis 入口重新核对 H4a actual closure、全部 review/reveal/measurement pins、overlap 和
  `analysis-input` pairwise；pilot/admission-overlap 与 held-out primary 分开，缺失或 unresolved
  不升级为 held-out。不完整 block 和 stopped run 可保留诊断记录，不能宣称完成全部确认性计划。
- `A4 − A2` 为含 transport difference 的 primary；`A4 − A3` 的解释上限保持 exact-skill-only /
  skill-bearing-package / not-comparable。case-replicate pairing、逐指标差异及冻结统计参数随分析
  输入保存；Research Integrity 不由效率抵消，不产生单一加权总分、promotion 或 Claim 决定。

本切片交付可信的分析输入闭包；统计结果的科学解释、正式评价运行与 Human disposition 仍属于
原 Task/Gate 定义。synthetic 输入持续带有其 purpose，不转为真实 confirmatory net-benefit evidence。

## 6. 读取、写入与负例矩阵

读取集限本包、Task/Protocol/Manifest、H1–H3、M5 shared validators、M6/M11 相关 public replay
接口、直接 Schema/tests/fixtures、catalog/CLI/coverage/CI 集成点和本 workstream 的风险及证据。
首次实现前在 `attempts/M5-007-H4-001/` 固定 Task snapshot、明确输入 pins、profile/skills（可为空）、
预算、停止条件和可观察事件捕获方式。准备阶段的 Git/检查记录不补写成完整实施 Trace。

| 拟定写入面 | 限定内容与验收 |
|---|---|
| `evaluation/harness_evidence.py` 及对应新 Schema/tests | H4a 冷回放和 actual reconciliation；四臂、完整 slices、真实失败/零调用、漏记录/换 case/换 Attempt/换实际 Projection 反例 |
| `evaluation/harness_review.py` 及对应新 Schema/tests | H4b 匿名包、私有映射、具名 freeze/reveal；标签/路径/元数据泄漏、提前/部分揭盲、映射和评分篡改反例 |
| `evaluation/harness_analysis.py` 及必要的观察 sidecar | H4c metric association、完整配对、重算 overlap/pairwise；无关证据、缺值补零、单位不一致、遗漏失败成本、pilot 混入 primary 和 actual drift 反例 |
| H3 evaluation-side observation 接口（确有需要时） | 只增加外层测量采集，保留已有执行、deadline 和 retry 语义；独立新 record，不改写已冻结 H3 记录；须通过原 H3 全部回归 |
| catalog/document-kind/validation、必要 CLI、coverage inventory | 新契约注册与明确外部上下文；CLI 不隐式补齐 admission/review authority；新增关键模块按现行 coverage 门禁验收 |
| 本 workstream、implementation docs 与 STATUS | 记录实际完成面和证据；Task/ROADMAP 的既有定义与 M5-007 IN_PROGRESS 状态保持 |

首个实施从 H4a 开始：先建立 actual-fact substitution 的失败用例，再实现编译与独立验证，并做
新进程禁用 Provider/Tool/Host/checker 的 replay。H4b/H4c 复用该输出，不绕开它直接消费计划。
H4 各候选要求 scoped tests、当前 coverage policy、repository/package/governance 和 cross-owner review。
H5 才汇总完整 M5-007 acceptance；本包和准备分支不构成 DONE。

若必须改变已发布 treatment、Runtime ownership、Supply selection、admission/Human authority 或
原 Task acceptance 才能继续，保留最小失败证据并进入具名 Task/ADR 处理。缺测量数据不构成
放宽 Gate 的理由，也不阻止先交付 H4a/H4b 的可验证部分。
