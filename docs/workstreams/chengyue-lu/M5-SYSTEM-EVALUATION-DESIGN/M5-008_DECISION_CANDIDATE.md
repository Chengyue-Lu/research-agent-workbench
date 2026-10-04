# M5-008 首轮案例与进入决定候选

2026-10-04。与[准备包](M5-008_PREPARATION_PACKET.md)共同审查。原 Task 仍 BLOCKED；
本文件是具体可选输入，不是 accepted dossier/Protocol、Skill admission 或 Pilot execution grant。
用户已建立推进到 M5-008 run-set 验收、M5-004 前停止的目标；本候选将涉及人类的决定与可离线工作分开。

## 1. 需要人类决定的内容

| 决定 | 已备候选/事实 | 谁决定及什么时候 |
|---|---|---|
| 案例/输出/读取范围 | 下述独立工程案例与有限格式；也可用人类提供的研究案例 | 路诚钺在观察输出前选择并冻结 public/private dossier、oracle、rubric 与选择理由 |
| A4 candidate/Evaluation 与准入 | 生产 Projection 为空；旧文献提取/仿真 Skill 均 legacy，handoff Skill deprecated | 路诚钺选择 exact candidate/evaluation；完整重评/生命周期与具名 admission 不由目标授权或 Agent 代填 |
| 四臂专项执行 | run inventory/配置/预算候选须最终绑定实际实现；原 Flash 部件授权与1744累计保留 | 路诚钺接受 exact Pilot dossier/Protocol/source/config 与 API/数据/Tool/窗口；黄毅复核实际接口与 applicability |
| 审查与收口 | blind→具名 review/freeze→reveal→metrics→全部 run-set/失败审计 | 真实 reviewer 提交判断；路诚钺/黄毅接受 exact 实现/配置/run set，才提议 DONE |

用户已明确选择首轮采用独立工程案例，允许按有限 document/evidence check 方向准备；这项类型选择
不构成下述 exact cards/oracle/source/config 的最终 freeze。A4 仍待选择先准备文献提取 Skill 重评候选，
或指定已有 candidate/Evaluation。选择准备重评不等于重新准入；未获选前只读取索引 metadata，不展开 Skill 源码。

## 2. 独立工程案例候选

候选身份 `pilot-document-check-001`；四个 claims、三个 source cards，一个 case × replicate 的
四臂 block。以下是本次构造的工程 vignette，不是已有论文、真实观测或正式科研评价。
这些共同公共数据不包含任何私有评分 anchors 或 arm/Skill/Runtime 控制。
实际实现按已有 M6 正向白名单构造 provider payload；本文件的设计说明不整体发送给 Provider。

| 公共 Source ID | 共同输入事实 |
|---|---|
| S01 | 一个测试批次的三个数值为12、18、24，单位均为同一任意工程单位 |
| S02 | 该 vignette 的允许范围是闭区间10到30；没有额外精度或分布假设 |
| S03 | 这些资料不包含方法A/B的对照试验，也不包含采用某方法后的质量变化观测 |

| Claim ID | 待判断的公共命题 |
|---|---|
| C01 | S01三个数值的算术平均数为18 |
| C02 | S01中的数值24超出S02的允许范围 |
| C03 | 方法A已被证明能提高研究结果质量 |
| C04 | S01的三个数值完全相同 |

共同指令候选：只依据上述 cards 为每个 Claim 给出 `supported`、`contradicted` 或
`insufficient`，引用必要的 Source ID；按准备包的 `bounded-evidence-verdict-v1` 输出恰好四项，
没有额外正文。Tool/Method 选择不写入共同指令；A1 Tool 为零，其他 arm 按各自冻结路径和 actual
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

推荐先由人类判断文献提取路径是否值得重评。获选后才读取 exact manifest/source/Need/Evaluation/
Lifecycle，核对触发边界、净增量、许可证、脚本/网络、成功与失败、上下文成本、source/package
pins 和正式 Need；不足时记录缺口或停止，不为了四臂验收临时造一个“必需 Skill”。
新版本或重新准入、不可变 Release/provenance、发布 Projection、Supply/Resolver→View 与
actual consumption 仍按现有完整 Gate。人类也可直接给出另一份 exact candidate/Evaluation 作为输入。

## 4. 运行清单候选与尚待数值冻结

| Block/slot | Case/replicate | 路径 | 当前身份与状态 |
|---|---|---|---|
| 一个完整四臂 block / A1 | pilot-document-check-001 / 1 | fresh M6 plain session | 只是清单行；未分配实际 Attempt/session，无调用 |
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

本次已形成公共 vignette、私有评分候选、四臂 inventory 骨架、Skill资格索引事实以及 Provider
source delta 核对。原 source66 到本候选基线的 Provider/M11/Harness/Schema 产品 delta 仍只包含
`profile_conformance.py` 与 `conformance_journal.py` 两个已合入修复；这不认证尚未实现的 M11 live
Driver 或新 config/Host/Tool，applicability 仍 pending。

接下来独立整理 exact input/授权/applicability 的可核对形式与反例要求，选中路径后做受限重评材料。
正式实现与进入仍遵守原 Task/Gate：需要的 exact 输入缺失就保留 BLOCKED；不能将目标、
通用“继续”、CI、Agent构造的 dossier 或外部窗口接手当作 Human admission/执行/评分决定。
最终完成 M5-008 全部 accepted run set 与具名验收后停止；M5-004 仍由自身依赖和 case Gate 控制。

M12 已由用户委托现有「RWB开发 (1)」窗口独立接手，先核对 Phase C semantic closeout 和 Topic5
R2 activation 输入；M12的准备不成为本Pilot新增依赖，不随委托自动将 RESERVED 改为实现任务。
