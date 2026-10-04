# M5-008 首轮案例与进入决定候选

2026-10-04。与[准备包](M5-008_PREPARATION_PACKET.md)共同审查。原 Task 仍 BLOCKED；
本文件是具体可选输入，不是 accepted dossier/Protocol、Skill admission 或 Pilot execution grant。
用户已建立推进到 M5-008 run-set 验收、M5-004 前停止的目标；本候选将涉及人类的决定与可离线工作分开。

## 1. 需要人类决定的内容

| 决定 | 已备候选/事实 | 谁决定及什么时候 |
|---|---|---|
| 案例/输出/读取范围 | 下述独立工程案例与有限格式；也可用人类提供的研究案例 | 路诚钺在观察输出前选择并冻结 public/private dossier、oracle、rubric 与选择理由 |
| A4 candidate/Evaluation 与准入 | 用户希望先考虑一般化 Skill；本次提出 scope-preserving-evidence-check@0.1.0，生产 Projection 仍为空 | 路诚钺选择 exact candidate/evaluation；完整评价/生命周期与具名 admission 不由目标授权或 Agent 代填 |
| 四臂专项执行 | run inventory/配置/预算候选须最终绑定实际实现；原 Flash 部件授权与1744累计保留 | 路诚钺接受 exact Pilot dossier/Protocol/source/config 与 API/数据/Tool/窗口；黄毅复核实际接口与 applicability |
| 审查与收口 | blind→具名 review/freeze→reveal→metrics→全部 run-set/失败审计 | 真实 reviewer 提交判断；路诚钺/黄毅接受 exact 实现/配置/run set，才提议 DONE |

用户已明确选择首轮采用独立工程案例，并希望先考虑一版一般化 Skill。这允许准备下述领域无关的
有限证据核对候选，不构成 exact cards/oracle/source/config 的最终 freeze、实际 Skill admission 或 API grant。
[一般化 Skill 候选包](M5-008_GENERAL_SKILL_CANDIDATE.md)给出正式 Need、源包、评价与发布边界。

## 2. 独立工程案例候选

候选身份 `pilot-scope-check-001`；四个 claims、四个 source cards，一个 case × replicate 的
四臂 block。以下是本次构造的工程 vignette，不是已有论文、真实观测或正式科研评价。
这些共同公共数据不包含任何私有评分 anchors 或 arm/Skill/Runtime 控制。
实际实现按已有 M6 正向白名单构造 provider payload；本文件的设计说明不整体发送给 Provider。

| 公共 Source ID | 共同输入事实 |
|---|---|
| S01 | 报告A：程序P相对基线B，配置E、短任务、warm-start、窗口W1；median elapsed time分别为80ms与100ms，报告称减少20%。没有提供样本量或完整原始日志 |
| S02 | 报告B：程序P相对基线B，配置E、长任务、包含cold-start、窗口W2；median elapsed time分别为105ms与100ms，报告称增加5%。没有提供与W1的配对记录 |
| S03 | 报告C仅写“程序P的efficiency提高20%”；没有说明efficiency的定义、单位、分母、基线、负载、启动状态或时间窗口 |
| S04 | 报告D声明与S01相同的配置E、短任务、warm-start、窗口W1和基线B；median elapsed time分别为110ms与100ms，报告称增加10%。日志只部分保留，未说明差异原因 |

| Claim ID | 待判断的公共命题 |
|---|---|
| C01 | 四份报告都明确记录了P相对B减少median elapsed time |
| C02 | S01和S02记录的是相同负载、启动状态及时间窗口，因而可直接合并成同范围的正负冲突 |
| C03 | 现有资料给出了S03中efficiency的单位、分母和基线，可据此与median elapsed time按已批准的mapping合并 |
| C04 | 现有资料已证明S01与S04是可信的科学冲突，并已解释两者差异的原因 |

共同指令候选：只依据上述 cards 为每个 Claim 给出 `supported`、`contradicted` 或
`insufficient`，保留有关来源的支持、反证、限制或未知及逐来源scope关系；按准备包的
`bounded-evidence-relations-v1` 输出恰好四项，没有额外正文。`supports`只表示该source在声明范围内
提供同方向证据，不自动证明整项Claim；`counters`也不能被其他支持来源抵消。
只有cards中的信息与已有批准mapping可用；缺少定义不能静默归一化，声明scope相同也不认证数据质量。
Tool/Method 选择不写入共同指令；A1 Tool 为零，其他 arm 按各自冻结路径和 actual
qualified interfaces 工作，不因工程案例简单而用 canned result 替代真实调用。

私有 adjudication 候选与有限 rubric 已独立准备在私有归档，包含逐 Claim 允许的判定、引用条件和
非补偿式 overclaim 判断。正式 case/oracle commitments、typed comparison closure、Human 决定和
可信 freeze time 仍待形成；没有把 Agent 产生的答案称为 Human scientific correctness。
冻结前必须核对与所选 Skill、Method/output obligations、admission Evaluation 的相容性与 overlap；
不相容就改候选版本，不能为 A4 补专属转换路径或观察输出后改 oracle。

## 3. A4 选择与当前资格

在当前 source 的 index metadata 中，`literature-evidence-extraction@0.1.0` 和
`simulation-vv@0.1.0` 为 legacy；`handoff-integrity@0.1.0` 为 deprecated。
旧 `accepted.json` 的 admission history 不是生产投影与新 assignment eligibility。
外部 triage/reference candidate index 的条目也不是 accepted Runtime supply。

本次源包 `scope-preserving-evidence-check@0.1.0` 对应现有正式 Need
`evidence-conflict-synthesis@1.0.0`，仅提出在冻结来源中保留scope/反证/未知的待检验增量。
它位于 `skill-lab/candidates/`；没有 manifest/Release/Projection/accepted Supply，不执行默认发现。
独立 Maintainer Trial/Evaluation必须证明相对同一输入和ceiling的no-Skill/direct Tool非平凡增量，
保留non-trigger、失败与上下文成本，经过Human blind review与具名admission。
现有 Need 的baseline checker不做语义判断且禁止network/egress；实际Requirement/Supply/Method
以及公共数据model-egress相容性仍待闭合，不能据本源包放宽旧契约。
新版本或重新准入、不可变 Release/provenance、发布 Projection、Supply/Resolver→View 与
actual consumption 仍按现有完整 Gate。准入前评价输入与本Pilot case分离，独立重算overlap。
此前准备的算术案例 `pilot-document-check-001` 留在私有准备历史；它属于non-trigger控制，
不单独用来证明该Skill的增量或准入资格。所有候选判定仍待Human审核，未形成运行结果。

## 4. 运行清单候选与尚待数值冻结

| Block/slot | Case/replicate | 路径 | 当前身份与状态 |
|---|---|---|---|
| 一个完整四臂 block / A1 | pilot-scope-check-001 / 1 | fresh M6 plain session | 只是清单行；未分配实际 Attempt/session，无调用 |
| 同 block / A2 | 同 case/replicate | fresh M6 + runtime-qualified pure Tool | 同上；Tool identity、shape、实际调用义务待选 |
| 同 block / A3 | 同 case/replicate | Resolver→M11 Core→真实 Driver | 同上；Method、全部必需 slices 与 output obligations 待冻结 |
| 同 block / A4 | 同 case/replicate | Resolver→M11 admitted Skill path→真实 Driver | 同上；无真实 admission/Projection，不能执行 |

实际顺序使用既有 frozen seed/permutation algorithm；列表顺序不代表预注册执行顺序。
建议0自动 retry/fallback；数值 budget 不沿用部件组数作授权。要在冻结完整 Method/slice/input/body
后分别约束 request、arm、run、Tool/turn、Attempt 与父进程 deadline，不能先造一个“可执行”默认值。
全局成功/失败 input+output 上限10,000,000包含原1744；unknown usage保留预占并停止，不能另开
空账本。费用/币种无法核对按原用户政策如实 unknown，不造价格或结算结果。
Flash-only、北京时间18:00后且官方闲时约束保留；执行日/窗口与当时官方 slot 冻结时 fresh 核对。

## 5. 已可独立完成的工作与边界

本次已形成公共scope vignette、私有评分候选、四臂 inventory 骨架、一般化Skill源包/Need/评价方案
与资格索引事实以及 Provider
source delta 核对。原 source66 到本候选基线的 Provider/M11/Harness/Schema 产品 delta 仍只包含
`profile_conformance.py` 与 `conformance_journal.py` 两个已合入修复；这不认证尚未实现的 M11 live
Driver 或新 config/Host/Tool，applicability 仍 pending。

接下来独立整理 exact input/授权/applicability 的可核对形式与反例要求；完成合法的独立评价、
Human准入与Pilot专项输入后，再按原Task进入实现与最终运行冻结。
正式实现与进入仍遵守原 Task/Gate：需要的 exact 输入缺失就保留 BLOCKED；不能将目标、
通用“继续”、CI、Agent构造的 dossier 或外部窗口接手当作 Human admission/执行/评分决定。
最终完成 M5-008 全部 accepted run set 与具名验收后停止；M5-004 仍由自身依赖和 case Gate 控制。

M12 已由用户委托现有「RWB开发 (1)」窗口独立接手，先核对 Phase C semantic closeout 和 Topic5
R2 activation 输入；M12的准备不成为本Pilot新增依赖，不随委托自动将 RESERVED 改为实现任务。
