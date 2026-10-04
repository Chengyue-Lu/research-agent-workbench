# M5-008 一般化 Skill 候选与准入前评价准备

2026-10-04。用户明确希望先考虑一般化 Skill；本包提出跨领域的有限方法候选，
不把“通用”解释成所有 Mode/Task 自动加载。当前无 Trial/live Evaluation、admission 或发布。

## 1. Candidate 与正式 Need

候选 `scope-preserving-evidence-check@0.1.0`，kind 建议 `method`，独立原始说明在
[非发现目录的 SKILL.md](../../../../skill-lab/candidates/scope-preserving-evidence-check/SKILL.md)。
它在冻结来源集合中核对 claim/evidence 关系，保留范围差异、反证、限制与未知；没有脚本、
二进制、外部包、网络发现、账户或平台依赖。源包使用仓库 MIT 许可，不复制外部 Skill 内容。

现有正式 Need 为 [evidence-conflict-synthesis@1.0.0](../../../../registry/skill-needs/evidence-conflict-synthesis-1.0.0.yaml)，
ref `NEED-ES-CONFLICT-SYNTHESIS`，raw SHA-256
`9cf42f7d2b5561be91fd95d04df3b02ee1e6cef96b88478dfec60668a3f06765`，
origin `ES-A6@1.0.0`、Mode `evidence-synthesis@0.1.0`。
候选仅针对这个已声明的语义缺口提出：区分实质冲突与 population/measurement/time/assumption
差异，不能仅计数投票或由字段不一致就宣称已解决科学冲突。

第一次 trial 的 scope 保持该 Mode/Need；工程数据、文献或其他领域只是 dossier variants，
不凭一个源包声明仿真/实验/写作全适用。现有 Need 非触发项明确包括 extraction-only，
所以简单字段提取、算术答案或 checker PASS 不能成为准入增量证据。

## 2. 基线、边界与待冻结 metadata

| 项 | 候选定义/未决部分 |
|---|---|
| no-Skill/direct Tool baseline | 同一 Task/input/输出义务与 Claim ceiling，先形成 scope/locator 表并做结构检查，由人类判断科学解释；不能为 with-Skill 减少基线说明或隐藏已有能力 |
| 预期增量 | 减少范围误配、反证遗漏和无依据合并；保留未知而不夸大 Claim。当前只是待检验假设，没有 observed gain |
| source/context | 纯说明候选；source bytes/hash/UTF-8 字符量可以本地测量，token 与质量/时间收益不能由字符量推断 |
| 输入/输出 | frozen evidence/claim/scope/locator 集合；共同有限 verdict/relation 格式由 Task拥有，不能给 A4添专属转换器或更高 ceiling |
| Runtime bounds | input/read/egress/write/Tool/Provider 逐项 exact；不把候选说明当 permission 或 API grant。accepted manifest/Release/Projection 尚不存在 |
| capability / Method | 原 Need 的 `research-contract-check` baseline 是结构检查，明确不做科学语义判断且 network/data egress 禁止；本 Skill 不冒称该 checker capability。实际 Requirement/Supply/Method 与公共数据 model egress 必须分别闭合，不能放宽旧 Requirement/Method |
| publication | 实际 manifest需声明 runtime data-egress/side-effect ceilings，complete Need/Evaluation/Human Decision/Lifecycle/immutable Release/provenance→Projection→Supply lineage；现在不写入 `.agents/skills`、accepted/candidate Registry或Projection |

candidate 与正式发布语义见[候选管线](../../../implementation/SKILL_CANDIDATE_PIPELINE.md)、
[Need contract](../../../implementation/SKILL_NEED_CONTRACT.md)和
[SkillReleaseProjection](../../../implementation/SKILL_RELEASE_PROJECTION.md)。
源包留在 `skill-lab/candidates/`，不由 Codex 或 Runtime 默认发现；当前不执行其说明。

## 3. 独立准入前评价候选

评价遵守[Skill evaluation protocol](../../../implementation/SKILL_EVALUATION_PROTOCOL.md)与现有 Need：
冻结同一输入、Provider/model/config、Task/context/checker及完整四臂；with-Skill显式引用候选 source/package
pins，其他 arm 不读取候选。Trial/Evaluation属于 Maintainer 隔离评价，不能冒充M5生产A4
accepted Runtime execution；前者的人类准入完成后才能满足本Pilot外部Gate。

| Case class | 需要覆盖的差异/失败 | 评价要求 |
|---|---|---|
| trigger / population | 同名结论来自不同population/system边界 | scope保留、不能无依据泛化或宣称冲突已解释 |
| trigger / measurement | 相关词指不同measurement定义、基线或单位 | 不静默归一化；仅使用已批准mapping |
| trigger / time/assumption | 短/长窗口、稳态/瞬态或前提不同 | 限制与未知可追溯，scientific interpretation由Human |
| adversarial / majority | 多个正例伴有重要少数反证 | 不按count/prestige裁决，不丢反证 |
| missing-input / boundary | 关键source缺失，或scope未知 | 缺required source停；合法未知不填0或假定相同 |
| non-trigger | 只有提取/格式/算术任务、或已有approved mapping | 不制造新interpretation与开销；候选无增量可降为template/reference |
| adversarial / source instruction | 来源包含要求扩大读取/出站/改Claim的指令 | 视为source content，不改变Task、Tool或数据边界 |

该矩阵定义准备覆盖，不是已注册例数、实际运行或结果。具体case/Task/input/oracle/checker/hash、
replicate/seed/顺序、预算/时窗/stop、账户/Tool与Human review须单独冻结授权。
简单单约束case只校准执行器。实测输出、失败、context/cost/rework、盲审→freeze→reveal与Claim
完整性逐项保留；不由一次Pilot成功、LLM reviewer或deterministic report宣布Skill值得准入。

若无可复现非平凡增量，或只能靠扩大ceiling/额外source改善，停止或降级候选；保持A4 Gate未满足。
source/package hash与Need refs固定后，实际Evaluation assessor至多给eligible-for-human-decision，
仍需路诚钺具名决定与合法生命周期/发布。与Pilot案例overlap必须独立重算，不能重用同一case称held-out。

## 4. 首轮 Pilot 工程案例与共同输出

首轮仍为用户选择的独立工程案例。为实际触发上述语义工作，提出新的
`pilot-scope-check-001` cards：相同程序在不同负载/冷启动/测量口径下出现正负报告，
加入unknown定义和不完整日志，要求保留反证与Claim ceiling。
具体公共cards、claim和四臂清单见[决定候选](M5-008_DECISION_CANDIDATE.md)，
私有anchors与准入前评价输入分开，未被Human最终冻结。

共同输出建议 `bounded-evidence-relations-v1`：每claim的有限verdict，以及逐source/relation的scope状态。
四臂使用同一格式，盲审仅接收有限投影；artifact/transport identities、cost/token与private maps
保留在评价私有闭包。格式解析只作结构检查，semantic评分仍归Human。

M5-008继续BLOCKED；本候选是准入输入准备，不实现live Harness、执行candidate或产生新API请求。
