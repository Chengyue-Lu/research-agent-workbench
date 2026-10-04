# M5-008 Live Pilot 准备与设计候选

2026-10-04。Evaluation / Task owner：路诚钺；Provider / M6 / M11 接口 owner：黄毅。
风险 R2；本包为离线设计候选，Task 仍 **BLOCKED**，状态与验收以
[TASKS](../../../TASKS.md)和[Live Pilot Gate](M5-008_LIVE_PILOT_GATE.md)为准。
核对基线：`develop@6fa105b720254fae82d2e889385c89292272b2d7`。
跟踪：[Issue #123](https://github.com/Chengyue-Lu/research-agent-workbench/issues/123)。

用户已授权将推进至 M5-008 run-set 验收设为目标、在 M5-004 前停止；不涉及新 Human 决断的工作
直接继续。用户选择独立工程案例、希望先考虑一般化Skill；[决定候选](M5-008_DECISION_CANDIDATE.md)
与[一般化Skill候选包](M5-008_GENERAL_SKILL_CANDIDATE.md)提供可审查输入，
实际准入、专项运行、评分与具名收口仍分别保留，当前没有新执行 grant。

## 1. 进入事实与本次交付

| 条件 | 已核对事实 | 本 Pilot 尚需完成 |
|---|---|---|
| M5-007 | DONE；H1–H5 的 synthetic Harness 已接受 | 保存原 `1.0.0` purpose、Schema、历史档案与回放语义；逐项核对新配置适用性 |
| M6-010 | DONE；[受限完成记录](../M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)接受 source66 / installed002 / native005 的 Windows Python3.11.16 Flash Tool/text/Schema | 新 source/config/model/profile/Host/Tool 的 applicability 尚未冻结、核对；旧报告不能重绑新实现 |
| A4 Runtime admission | UNSATISFIED；当前生产 projection index `entries=[]` | 人类选定 candidate 与 Evaluation，提供真实 accepted Release→Projection→Supply 全链；测试 Projection 不具准入资格 |
| Pilot 专项授权 | UNSATISFIED；已有授权针对 M6 部件合成调用 | 人类接受本 Pilot 的独立 dossier/Protocol、exact 四臂计划、预算、账户/数据/Tool/窗口及审查安排 |

本次交付是版本化 live purpose、有限审查输出、四臂集成与证据闭包的候选，
以及可填入 exact pins 的进入清单。没有新增 API 调用、凭据读取、账本/grant、Skill admission 或 Task 接受。
M6-010 的部件成功证明一个选定 Provider/session；M11 live Driver、四臂集成和 M5 完成仍需本项自身验证。

## 2. 首轮 dossier 与有限输出候选

建议首轮采用独立的有界 document/evidence check 工程案例，最多四个 claim cards、八个公共 source cards。
人类在输出产生前选择案例、冻结 public/private packages、Claim ceiling、选择理由与 oracle/审查 anchors。
案例必须与获准 A4 Skill 的 Method、输入和输出契约相容；不为 A4 添加专属转换 Method 或补写答案。
该规模只是准备建议，尚非批准的样本量、真实输入或执行计划。

所有 arm 使用相同公共任务和输出格式候选 `bounded-evidence-relations-v1`。形状示例：

```json
{
  "format": "bounded-evidence-relations-v1",
  "claims": [
    {
      "claim_id": "C01",
      "verdict": "insufficient",
      "relations": [
        {"source_id": "S01", "relation": "limits", "scope_status": "different"}
      ]
    }
  ]
}
```

示例只表达候选格式，不是模型输出、已批准案例或 Schema。冻结后遵守以下有限规则：

- `claim_id` 和 `source_id` 只能来自该案例冻结的闭集；每个 claim 恰出现一次。
  `verdict` 仅为 `supported`、`contradicted`、`insufficient`；每个source最多两项关系，
  相同source/relation不得重复，整个claim最多为冻结source数量的两倍（八source时至多16项）。
  允许空relations并由人类判断；不能用无引用的确定判定掩盖反证或合法未知。
- `relation`仅为`supports`、`counters`、`limits`、`unknown`；`scope_status`仅为`matched`、
  `different`、`unknown`、`not-applicable`，相对于该claim的声明范围逐来源记录。
  关系是有限审查表达，不自动推导科学正确性；同一source的有限支持可同时带来泛化限制。
- 本地按有界 JSON 精确解析，拒绝重复键、非有限值、未知字段、额外正文/代码围栏、缺项或越界数量。
  不截取前缀、不修正模型答案、不通过重试选择满意结果；原响应、失败与 usage 仍按授权归档。
- M6 的最终完整 ModelResponse 与 M11 的输出工件分别保留原 transport envelope；相同白名单
  projection 只输出上述有限内容。A3/A4 多 slice 情况须在冻结时声明一对一输出义务，不能挑选最佳 slice。
- 非 completed、截断、格式无效或缺失输出标为 `unreviewable`，不填零分。执行生命周期仍保留原值；
  完成传输不自动取得审查/成功 block 资格。有限投影无法闭合时 Gate 仍未通过，不回写历史工件。

公开盲审包包含共同案例说明、固定 rubric、来自私有随机熵的匿名 ID 和有限投影；
不分发 arm/Skill/RWB、运行顺序、路径、Provider identity、Trace、cost/token 或私有映射。
审查人使用获批的私有 anchors，对事实判断、来源归属与 Claim ceiling 分别给出有限判定，
记录不可审查理由；代码只校验格式和闭集，不产生 Human score，不压成单一总分。
全部预注册审查项具名提交并冻结后才能 reveal；质量不佳本身可以是合法 Pilot observation。
有限内容仍可能使 reviewer 猜测 treatment，本包只控制标签/元数据暴露，不宣称完全匿名。

## 3. 版本与 authority 设计候选

建议为新 Protocol/Harness/review/measurement/analysis 族提出 `2.0.0`，purpose 为
`live-engineering-pilot`；最终 kind/version/catalog dispatch 随后续 R2 实现审查。
现有 Protocol@1.0.0 的 purpose 只有 `synthetic-contract-proof` 与 `confirmatory-protocol`，
H3 明确拒绝 live，H4 producer/review Schema 固定 synthetic；不能仅改 phase 或连接真实端口。

新版本应通过明确 kind/version/Schema identity 分派，共用既有计划排列、M6/M11 ports、Resolver
和 Receipt 验证器；保留旧 Schema 文件及对应旧版本验证闭包。旧 H4 identity 包含整个 Schema catalog，
新增 live Schema 后不能冒称旧 identity 未变；历史回放使用原冻结 validator/catalog，新版明确新的身份与缓存边界。
不得把旧 producer 切换 purpose、
放宽旧 Schema、覆盖旧报告，或增加 arm-specific Host dispatcher、selector/fallback/旁路 runner。

以下记录只位于 Evaluation/Maintainer 侧，不进入 plain payload 或 Runtime Bundle：

| 候选输入/记录 | 必须闭合的内容 | 不能取得的权威 |
|---|---|---|
| Pilot authorization | Human actor/决定来源；dossier/Protocol/run inventory、账户 credential reference、source/config、窗口、预算、read/egress/Tool/副作用及 stop 的 exact refs/hashes | 文件中的 approved/status 或 Agent verifier 默认 True 不授予授权 |
| Binding applicability | 接受的 M6-010 原始证据 refs；新 exact implementation/validator/install/config/profile/model/Host/Tool 与差异；每项适用/待重验/不适用及具名核对 | DONE、型号字符串相同或旧 PASS 不认证新 Driver/Host；未知必须阻断 |
| A4 gate/overlay | frozen candidate/evaluation→具名 Human Decision→accepted Release/provenance→Projection→Supply→Resolution→Snapshot→Bundle→View 的逐跳闭包 | Harness 不选择 Supply、不直接读 candidate 到 Runtime、不创造 admission |
| Live execution/evidence | run/block/arm/Attempt/slice、逐 use-boundary 的 actual facts、全部 Receipt/Trace/output refs、失败和预算来源 | 保存的 preflight/planned View 不代替实际事实；`task_completion=false` |
| Review/freeze/reveal/metrics | 相同 evidence/policy/package/private map、全量 Human reviews、可信 received/freeze/reveal times、所有 join 及 measurement 状态 | Pilot 始终 `primary_confirmatory_eligible=false`；不产生科研净收益或 promotion |

执行调用方必须从独立可信来源提供 expected refs、时钟与具名 authority 核验，重载全部输入；
不从待验结果文件提取自己的可信 pins。授权在每个实际 Provider/Tool use boundary 重验。
漂移先停止；已发生调用则保留 post-call failure、usage 和原输出，不能事后降成零调用 block。

## 4. 四臂集成与共享条件

| Arm | 复用路径与应实现/验证的接入 | 必须观察的事实 |
|---|---|---|
| A1 `plain-agent` | M6 baseline envelope→fresh API session→baseline closeout；模型只见既有正向白名单公共 payload，Tool 为空 | 实际 exact Provider/Adapter/model 与一次以上真实响应；不注入完整 Task、Mode/Method/Skill 控制 |
| A2 `plain-agent-tool` | 同一 M6 baseline + exact qualified Tool；A2 qualification 继续由 M6 producer 产生 | 实际 Tool invocation、参数本地验证、返回与后续响应；注册 Tool 不等于调用 |
| A3 `mode-no-skill` | 唯一 Resolver 的 Snapshot/Bundle/View→M11 Core→Provider-backed Driver→Core closeout | frozen Mode/Action/Method、非 Skill Tool/procedure 与实际 binding；Harness 组装/重算 A3 qualification |
| A4 `mode-candidate-skill` | 同一 M11 Host/Driver seam 消费 Resolver-selected admitted Skill Supply→Skill closeout | pre-use actual Supply/Projection consumption 与 post-call binding typed facts；独立 replay 后与 overlay 相等 |

已有 `HarnessPorts`/Driver factory 是接入缝，不是 live Driver 已完成的证据。后续实现必须在既有
M11 View/Host 契约内接入真实 API，消费实际 bytes 并同时记录 Provider/Tool facts；不复制一个 A4 runner。
对 A3/A4 都重验输出/stop obligations 与 ceiling；pairwise 独立重算，当前不同 Method 只能得到
`skill-bearing-package`，不能承诺 pure Skill increment。

每个 block 共用 exact model/profile/Adapter/Host、Task/public inputs、context、输出义务、data policy 与
同义预算；每 arm/retry 使用 fresh Attempt/session，按既有冻结算法排序。M11 多 slice 共享整臂预算。
Harness 外层时钟度量可比 wall time；Provider 内部时间或不能同义化的指标分别标 estimated/unavailable/N/A。

首轮运行建议为一个 case × 一个 replicate × 四 arm，零自动 retry/fallback；只调度 pilot slots。
这是四条工程路径覆盖的最低候选，仍须完成实际批准的整个 run set；失败不能挑选成功臂替代。
任一安全、预算、未知 usage、不可解释 drift 或证据未闭合都停止，保留后续 `not-started` slots。
新的手动修复/复验必须保留旧 Attempt、重新冻结并按授权建立 fresh Attempt，不自动扩大预注册集合。

## 5. 执行前输入清单

下表的待填值不是执行默认值。人类接受与接口复核只在 exact 输入齐全后发生。

| 输入 | 当前候选或来源 | 冻结前必须填写/核对 |
|---|---|---|
| Dossier | 用户已选独立工程案例类型；scope-check cards候选 | exact case/Task/public input/private oracle identities/path/hash、选择理由、读取边界仍待Human冻结 |
| Protocol / source / output | live purpose@2.0.0 与有限格式设计 | accepted source/validator/Schema/install、共享 Task/output/context、Protocol/config/计划 refs；本准备包不接受或实现新 Schema |
| Provider / Windows | 历史 M6-010 为 `deepseek-flash`、`deepseek-responses-nonthinking-v1`、Windows Python3.11.16 | 当前官方 slot/profile/endpoint、实际 Host/Tool/Driver 与安装；fresh applicability 与必要有界复验，不重绑 source66 |
| A4 lineage | 一般化Skill源包/正式Need/独立评价方案候选，生产Projection为空 | exact candidate/Evaluation/Human admission/Release/provenance/Projection/Supply/Resolver/Snapshot/Bundle/View pins；准入决定由路诚钺作出 |
| overlap / pairwise | 已有独立重算规则 | admission 与 Pilot case 两侧 typed oracle/input closure、checked/frozen times、overlay/A2/A3 qualification、pairwise；unresolved 不能因 pilot 标签放行 |
| Tokens / calls / Attempts | 用户累计 input+output ceiling 10,000,000；M6 历史已计1744 | 为 Pilot 明确总/每 arm/每 request 输入输出、调用/Tool/turn/Attempt/retry 上限；不得将原部件十组授权当成四臂许可或重置累计历史 |
| 时间 / stop | 用户 Flash-only、北京18:00后且官方闲时的约束继续保留 | fresh 官方窗口、执行日与截止、request/arm/run/父进程有界超时、停止/取消策略；不无限等待响应 |
| 费用 / 账本 | 用户允许 token ceiling 内账单/币种无法核对不单独阻断；金额 unknown 如实保留 | Pilot 决定明确引用原用户政策；所有成功/失败 usage 交叉核对 durable ledger，unknown usage 保留预占并停止；不造币种/价格/结算结果 |
| Account / data / Tool | 已有本地 credential reference，不读取值 | 账户与执行人、仅向获授权子进程注入的 helper/source/context refs、egress/read/write/Tool/副作用白名单及诊断/归档边界 |
| Human review | blind→全量提交→freeze→reveal | reviewer actor、有限 rubric/private anchors、可信时间、分发/私有访问与外部核验；不得让 Agent 代审或虚构黄毅接受 |
| Named completion | 原 Task 的路诚钺/黄毅职责 | exact source/config/run set、独立冷回放、所有负例与限制；接收计划不等于接受未发生的运行 |

同一 source/config/use boundary 无法闭合时，必要 conformance 复验仍消费原唯一累计账本；
如果现有账本/授权类型不能承载新 Pilot，先定义可审计扩展并关联原全部历史，不另开空账本取得新额度。
已有 API Key 与 token 总上限不授予 A4、数据出站、Tool 权限或四臂执行。

## 6. 开发与验收顺序

| 节点 | 可交付内容 | 进入/完成条件 |
|---|---|---|
| P0 当前准备 | 本设计候选、dossier/output、一般化Skill源包/Need/独立评价方案、Gate 与 exact-pin 清单，更新 Issue123 | docs/refs/候选边界/治理检查；零调用，Task BLOCKED |
| P1 合法进入 | Human 冻结案例/输出、真实 A4 lineage、Pilot 专项决定、M6 binding applicability | 所有原 hard/external conditions 闭合，按 TASKS 状态机提出 READY/IN_PROGRESS；缺 exact 对象继续 BLOCKED，不以未来 SHA/占位批准制造 PASS |
| P2 R2 实现 | 新版本 live-purpose contract；已有 M6/M11 ports 的真实 Driver/facts；有界 review/measurement 与 cold reader | 版本兼容、零调用拒绝与离线正反证据、exact-head 组件/安装验证、跨 owner R2 审查；不消费未授权 API |
| P3 冻结运行 | accepted source/config/Protocol/run inventory 与 inputs，真实四臂执行 | 首次输出前 exact Human authorization 与 use-boundary fresh guards；全部预注册 slots 和失败保留 |
| P4 验收收口 | 新进程只读 replay→blind review/freeze→reveal→metric/analysis joins→逐项 Gate record | 路诚钺与黄毅接受 exact 证据；至少一个完整 block 且全 run set 完成，才提议 M5-008 DONE/关闭123 |

准备期决定只绑定已存在的候选范围，不批准尚未产生的实现。最终执行决定必须绑定 P2 实际产出的
exact source/config/Schema/install；变化后重新核对/冻结，旧设计接受不能自动续期到新实现。

后续必要反例：缺 A4/授权/applicability 为零 Credential/Provider/Tool；hash/config/模型/预算漂移拒绝；
调用后失败与 unknown usage 不丢失；fresh retry 不能复用 Session 或择优；A1 Tool 泄漏、A2 未调用 Tool、
A4 Supply/Projection 或 actual binding substitution 拒绝；有限输出额外正文/未知字段不进入盲审；
提前 reveal、部分冻结集合、改评分/映射及 archive 篡改拒绝；confirmatory 入口拒收全部 Pilot records。
这些是待实现/执行的验证清单，不是本次已运行的测试或 live PASS。

实际 Pilot 的受控 post-call fault injection 须在专项范围内、无外部副作用，并与成功 live arm 分列。
原失败、capture gaps、未知 measurement/账单和不完整 slots 不删除；本包不产生 M5-001/002 case 接受、
M5-004/005 研究结论、Skill promotion/pruning、Topic5 或发行资格。
