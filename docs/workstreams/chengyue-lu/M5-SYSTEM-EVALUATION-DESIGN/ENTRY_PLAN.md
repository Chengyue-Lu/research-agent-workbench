# M5 implementation entry plan — 2026-09-11

状态：开工时的进入评估与实施规划快照；当前实现与验证进展见 [WORKLOG](WORKLOG.md)。本记录本身不构成验收证据。

Evaluation owner：路诚钺（`Chengyue-Lu`）。Execution 接口 owner：黄毅（`let778750-cpu`）。

## 1. 结论与依据

**M5-006 具备立即进入实现的条件。第一个集成节点是完整交付 M5-006 的 R2 feature PR，目标分支为 develop。**
M14 后续、文档维护、M1-009 scaffold 和首次发布均不是这个节点的前置条件。
M5-007 Harness 与 M5-004 真实四臂运行分别受后续执行契约和真实证据 Gate 约束。

本次已执行 `git fetch origin --prune`；主工作区 clean，local/remote develop 均为
`11c3b57dfbf8af0dc2587fc421d097e2544941c3`。
据此建立独立分支 `feature/m5-evaluation-protocol`；本记录为该分支的开工输入。

当前依据按权威与用途区分：

- [TASKS](../../../TASKS.md)：M5-006 的状态、依赖与验收定义；本计划不重定义 Task。
- [Issue #55 最新推进评论](https://github.com/Chengyue-Lu/research-agent-workbench/issues/55#issuecomment-5635303677)：2026-09-11 更新，明确取代正文中过时的 Gate A / M5-006 阻塞状态。
- [ADR-0020](../../../decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md) 与 [Gate A record](BASELINE_TRANSPORT_GATE.md)：固定双传输和 estimand；[PR #56](https://github.com/Chengyue-Lu/research-agent-workbench/pull/56) 已合并，其 merge commit 为当前 develop 祖先。
- [既有设计](README.md)、[Risk Ledger](RISK_LEDGER.md)、[Manifest contract](../../../implementation/EVALUATION_MANIFEST_CONTRACT.md) 与 [模块 10](../../../modules/10-OBSERVABILITY_EVALUATION_COST.md)：提供字段、消费者、测量和解释边界。
- [开发治理](../../../DEVELOPMENT.md)：实现使用 feature PR；任务定义变化另走 task-definition，R2 要求具名 cross-owner review 和对抗证据。

本次实测 ADR raw SHA-256 与 Gate record 相同：
`64edd73c44bc77f326a90c51e0a8cbf5fd28c4bbf1a5e18aca7f50250ce21a12`。

## 2. 进入资格与实际缺口

| 项目 | 当前证据 | 对 M5 进入的影响 |
|---|---|---|
| M5-003 + Gate A | DONE / SATISFIED；accepted ADR pin 已核验 | M5-006 的两个硬依赖均闭合 |
| M4-001～004 | TASKS 主表均为 DONE | 后续真实实验的 provenance / Claim / Run 依赖已闭合 |
| M14-001～003 | TASKS 主表均为 DONE | 使用当前包与资源边界；M14 后续可独立推进 |
| M5-006 的新记录与校验器 | 在当前 src / schemas / tests 中未找到这组新契约；现有 `evaluation/manifest.py` 主要提供 M5-003 冻结计划及引用闭包 | 需要实际 Schema、比较规则、校验器、测试和集成；仅提交协议说明不足以 DONE |
| M6-008 | PARKED，等待 M5-006 DONE | 本分支交付可供其消费的共享契约，baseline transport 实现由 Execution 线承接 |
| M11-004 / M11-006 | DONE；Core closeout 代码仍显式拒绝 Skill Supply | mapping DONE 不能替代 Skill-bearing replay closeout；Gate B 缺口真实存在 |
| M5-007 | BLOCKED | 等待 M5-006、M6-008 和 Gate B；M11-004/006 已满足 |
| 真实 case、M6-004、A4 admission | M5-001/002、M6-004 仍 BLOCKED；production Projection index 为空 | 可准备资料与环境，M5-004/005 继续等待各自验收 |

TASKS 派生索引仍有 M4-004 “候选待合并”等历史文字。本次按主 Task 行、Git 合并状态及最新 Issue 判断；
这些文字由并行文档维护线对齐，不作为新增 M5 blocker。

## 3. 对 Issue 计划的评估

接受 Issue #55 的任务顺序、六类交付与 scope；建议按下面四点落实，避免执行时再次串行等待或混淆责任。

1. **以 M5-006 实现收口作为首个 PR 节点。** 既有 workstream README 中的 task-definition / docs-only 描述属于已接受的设计阶段；本次入口是现有 READY Task 的 R2 feature 实现。六类交付仍属于一个 M5-006，按切片审查，不制造新的 M5 Task。
2. **Gate B 的任务定义应提前并行准备。** Issue 的串行图可用于表达 Harness 的前置条件，但没有把 M6-008 DONE 定义为 Gate B 的现有硬依赖。由 Execution owner 在 M5-006 期间准备独立 docs-only task-definition，明确后继 Task、依赖、正反证据和 owner；具体编号在该流程确定。Gate B 实现何时启动由接受后的定义决定，本计划不自行解锁。
3. **严格区分评价侧与 treatment / Runtime 的读取边界。** TASKS 要求评价侧验证 candidate/evaluation 的 exact 引用，并重算 case / Task / input / oracle commitments。Issue 的“不读取 candidate/private oracle”简述应落实为不直接执行 candidate 包、不向 treatment arms 或 Runtime 暴露 private oracle；授权的评价侧仍须消费所需 identity/hash 闭包。assessment 只保存可验证 commitment，不携带 oracle bytes。
4. **准备可以并行，正式 freeze 有顺序。** case 候选、live 环境、admission 路径的材料准备可并行；confirmatory case/oracle 的正式 hash freeze 应使用已经冻结的 M5-006 held-out、blinding、stopping 语义。M5-007 的 synthetic implementation 不等待真实 case 完成。

## 4. M5-006 的六个实施切片

每个切片具备独立 implementation diff、正反测试和可定位证据。下表是施工顺序，不是六个新 Task。
全部切片及集成验收完成后，才将完整 M5-006 提交为 DONE 候选。

| 切片 | 可审查交付 | 完成证据 |
|---|---|---|
| S1 Protocol core + metrics | 版本化 Protocol 与验证入口；exact ADR pin、四臂映射、primary/secondary、randomization / replicates / pilot / stopping / retry / drift、blind/reveal、measurement status 与三层分析规则 | 正例可校验；缺失预注册参数、estimand 越界、未知值、将 unavailable/N/A 填为 measured zero、单一 weighted score 或完整性退化被效率抵消均被拒绝 |
| S2 A2/A3 execution qualification | `ArmExecutionQualificationRecord@1.0.0` 的 Schema、comparison rule、fail-closed validator；连接 frozen 与 runtime bindings，保持 Task / Requirement / Supply / component / implementation / interface 和相关 A3 Mode / Action / Method，ceiling 只能相同或收窄 | 两臂分别有合规与拒绝证据；structural-replay、execution_input=false、fixture-only、替换对象、typed conformance 缺失、hash drift、ceiling 扩张均阻断；M6/M5 producer ownership 明确 |
| S3 A3/A4 pairwise comparability | 版本化 `A3A4PairwiseComparabilityRecord`；从 exact shared conditions 与非 Skill 表面派生三态及 interpretation ceiling | 三态均有 fixture；Method / non-Skill Supply / interface / boundary 差异不能被声明为 exact-skill-only；预注册 exact-equality 后的漂移被拒绝；当前 Method disposition 不兼容如实降级 |
| S4 admission overlap | `AdmissionEvidenceOverlapAssessment` 三逻辑区、typed resolved/absent/unknown、四类 intersection、validator pin、checked_at 与派生 eligibility；闭包摘要避免循环和 self-hash | 同类别 identity 或 hash 相同均识别；同路径不同 hash、缺 oracle、opaque Task 无 formal identity、过期检查或换 case 均不能 held-out；公共 source / 通用框架不误作禁止性重叠 |
| S5 A4 qualification overlay | 独立版本化 pre-run overlay；保持 frozen candidate/evaluation，连接具名 Human Admission、immutable Release / promotion provenance、Projection → Supply → Resolution → Snapshot → Bundle → View → Host；exact 引用 S4 assessment | lineage 逐跳错绑、丢失、替换、hash drift、选中其他 Supply、status / eligibility 自报与重算不同均阻断；pre-run qualification 不冒充 post-run actual evidence |
| S6 validator / repository / package 集成 | 新契约进入现有 SchemaCatalog、document-kind / validation 路径，提供最小可重复校验入口；合成 fixtures、实施说明、coverage 分类及 R2 证据齐备 | M5-003 旧 Schema / fixture / arm / metric set 保持兼容；新记录可独立重放校验；完整 CI、repository / package smoke、文档链接、治理与 cross-owner review 收口 |

S1 中需要在实现时明确并记录的参数包括：随机化单位与 seed / block 规则、replicate 的 fresh Attempt/session 语义、
pilot 与 confirmatory 数据隔离、重试与 failed Attempt 的计费/纳入规则、停止阈值来源、盲审完成与 reveal 的顺序。
本进入计划不虚构样本量、成功率或已批准真实 case；Protocol freeze 前须使这些规则及所需参数成为可验证输入，
不能留下“实现者自行决定”的占位验收。

估计量继续服从 ADR-0020：primary `A4 − A2` 是含 transport difference 的 system-level difference；
`A2 − A1` 是同 M6 transport 的 Tool 条件增量；`A4 − A3` 仅在 exact-skill-only 时允许 Skill 条件增量解释；
`A3 − A2` 包含 Mode/Method 与 transport 差异。测量成本保留准备、监督、复核、纠错、恢复和失败 Attempt 的实际消耗，
按既有指标与明确测量口径表达；M5-003 的固定指标词表不原位扩张。

## 5. 分支文件边界与协作接口

实现优先放在 `src/research_workbench/evaluation/` 的独立模块、新增版本化 Schema、相应 tests 与合成 evaluation fixtures，
复用现有 FileReference / schema validation / integrity primitives。Schema 目录遵守当前 catalog 约定；记录自身版本不触发全仓 Schema 升版。
只做必要的 `validation/`、CLI 校验入口、coverage policy 与 package-resource 集成。
新增共享校验器应纳入 critical coverage 责任；不能因其尚未在旧表内而降低验证义务。

本分支拥有 Protocol / qualification / comparability / overlap / overlay 的评价契约，不实现 M6 session runner、
M11 Skill closeout、Supply selector、真实 Provider 调用或 Human admission。M5-003 v0.1 与 admission Evaluation v0.1 保持既有语义。
新 M5 工件保持 Maintainer/Evaluation 输入边界；Schema 分发不意味着记录可成为 Runtime input。
沿用 M14-003 已接受的 Runtime resource root / package boundary；public allowlist 与 M14 发布策略由其 owner 维护。

稳定文档与公开文档正在独立 worktree 维护。本分支初期只维护本 workstream 和 M5 实施文档；
到集成节点再对 `TASKS.md` 的 M5-006 状态、必要的 `STATUS.md` 实现覆盖和实施索引作最小差异更新。
任务定义、依赖、验收不在 feature PR 中改写；并行分支先合并时先 fetch/rebase，再验证新的 exact head。

Execution handoff 在 M5-006 验收时至少提供：

- A2 record 的 exact Schema / validator identity、输入/输出、错误语义和 fixture；A3 的 producer/consumer 责任对照。
- S1 的 arm→transport、实际测量口径、失败/重试/时钟约束和 baseline payload 读取边界。
- 从 M5-003 structural binding 到可执行 binding 的合规/拒绝对照，明确资格记录不自动授予执行权限。
- S3/S4/S5 后续由 M5-007 组装或独立重算的接口，以及需要 Execution actual-fact / replay 佐证的字段。

## 6. 后续节点与并行安排

| 节点 | 进入条件与产出 | 责任与并行关系 |
|---|---|---|
| N0：本次进入评估 | 最新基线、Gate pin、代码缺口、切片和文件边界有落盘记录 | 已完成规划；共享 Task 状态仍 READY |
| N1：M5-006 R2 feature PR | S1～S6 完整、exact-head checks 与具名 cross-owner review；接受合并后共享状态成为 DONE | 路诚钺；文档/M14 同期独立推进 |
| N2a：M6-008 baseline transport | 在 M5-006 DONE 后激活并实现 A1/A2 envelope、use-boundary checks、A2 producer、actual facts / replay closeout | 黄毅；M5 owner 提供契约及 fixture 支持 |
| N2b：Gate B | 可先并行准备独立任务定义；接受后按其依赖实现 Skill-bearing generic closeout 并验收 Gate | Execution owner；完成时间须早于 M5-007，具体 Task ID 待正式定义 |
| N3：M5-007 Harness | M5-006、M6-008、M11-004/006 均 DONE 且 Gate B SATISFIED；synthetic four-arm proof、pre/post-run 重算、匿名 review/reveal/analysis 闭合 | 路诚钺；不要求真实 case 已完成 |
| N4：M5-004 真实实验 | M5-001/002 正式冻结并获 Human approval、M6-004 live conformance、A4 admission Gate 及全部 Task 依赖闭合 | 人类批准真实实验边界；保留失败与未知测量 |
| N5：M5-005 disposition | 消费 exact run set、blind review、analysis 与限制 | 由 Human 作 evidence-linked disposition，不自动 promotion / pruning |

外部竞品产品比较属于单独验证计划。借鉴其强简单基线与完整成本核算思想，不将外部产品名称改成 M5 的四臂，
也不把竞品深析或新用户 scaffold 追加为 M5-006 的硬依赖。

## 7. 验证与交接要求

本次仅验证进入依据和规划文档：Git 基线、Gate ADR raw hash、合并 ancestry、目标代码缺口、文档链接与差异完整性。
没有运行新增 M5 实现测试、live Provider 或真实实验，不能沿用旧 M14/M4 的测试数量作为 M5 证据。

开始 R2 实现时建立相应 Task Attempt Archive，保留可见命令结果、验证证据及如实的 capture gaps，
并把新增失效路径对应到现有 Risk Ledger。该 Ledger 的历史设计结论不能代替实现证据。

每个切片先做 focused 正反校验。最终 rebase / 整合后，在同一 exact head 运行完整 Python 3.11/3.13 CI、
coverage、repository validation / smoke、package smoke、documentation 与 governance checks。
按当前 coverage policy，global line ≥90%，critical line ≥95% / branch ≥90%；CI plan 产生的 impact
line / branch 义务为 100% / 100%，按实际 plan 执行并检查新增路径已归类，不以总数通过替代局部证据。
本分支不为了缩短检查而修改 accepted CI authority 或降低阈值。

首个 PR 标记 `feature`、`R2`、`M5-006`，在 body 中用切片映射实现与验证证据，引用 Issue #55、ADR/Gate 和 workstream。
该 PR 只完成 M5-006 时使用 `Refs #55`，不提前关闭仍跟踪 Gate B / M5-007 的 Issue。
cross-owner review 后由人类决定合并；本分支不自行 merge、创建 release branch/tag 或推进真实发布。
