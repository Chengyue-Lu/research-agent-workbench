# M5-008 有限正文 codec 实现候选

2026-10-04。责任人：路诚钺；风险R2；原Task仍BLOCKED。
本段是隔离分支的实现候选，接受/成熟度以TASKS、STATUS与PR为准；没有实际Pilot运行。

## 1. 位置与进入边界

[bounded_evidence.py](../../../../src/research_workbench/evaluation/bounded_evidence.py)实现
[准备包](M5-008_PREPARATION_PACKET.md)的`bounded-evidence-relations-v1`有限正文。
这是纯结构codec，没有Provider/Tool调用、凭据、文件读写、Supply选择、准入或评分接口。
Candidate Skill不被这个模块加载。actual Receipt/live-purpose记录、blind package、Human freeze/reveal、
测量/账本与M11真实Driver仍须后继集成，不由正文可解析性取得资格。

仓库AGENTS的Change discipline将治理施加在shared truth接受边界，允许隔离分支先作实现候选。
因此准备计划补充P0.5离线实现候选节点；不把待准入/授权转换成已满足，也不改Task定义或状态。
真实执行和共享接受仍遵守[原Pilot Gate](M5-008_LIVE_PILOT_GATE.md)。

## 2. 明确的有限形状

`EvidenceOutputSpec`由调用方的外部冻结输入提供：1–4个claim local IDs（C01–C04），
1–8个source local IDs（S01–S08），均为无重复的不可变tuple。local IDs到实际输入/provenance的
映射由冻结dossier拥有，不由codec生成或验证；alias闭集不能自证source已经admitted。
固定body ceiling为16,384 UTF-8 bytes，JSON容器深度至多5；这是正文契约候选，不是API token预算。

顶层只有format/claims；每claim只有claim_id/verdict/relations；每relation只有source_id/relation/scope_status。
共同枚举及每source最多两项关系、相同source/relation不得重复、总关系数至多2×source数，
与准备包一致。所有必需claim恰出现一次；source须在闭集内，空relations保留给Human判断。
来源可同时支持有限命题并限制泛化，支持与反证不互相消除；checker不自动决定哪种关系科学正确。

只解析完整JSON，拒绝重复键、数字/非有限值、额外正文/围栏、BOM、非法UTF-8、未知字段、越界IDs、
缺/重复claims和超出数量/深度。深度扫描识别quoted strings与escape，独立于解释器recursion limit。
不截取前缀、修复答案、改verdict或重试。canonical projection仅排序有限claims/relations；原正文保留。

## 3. ModelResponse与私有/公开责任

`project_evidence_response()`消费既有provider-neutral ModelResponse。调用方先从独立重放的执行证据
获得lifecycle，重载实际工件和冻结spec；codec自身不认证传入的completed或ModelResponse来自真实调用。
只有completed、FinishReason.COMPLETE、无待调用Tool、单个纯text ContentBlock进入正文解析。
其他生命周期、截断/拒绝/未知finish、多个输出、附带data/mime/reference或无效正文都unreviewable。
保留原response与usage的责任仍属于上游archive/closeout，不能因无投影而丢掉已发生调用或计零成本。

返回的EvidenceProjection是**私有**对象：可用时有有限answer，另有稳定diagnostic和有界正文hash。
`public_value()`只产生availability/answer的正向白名单值，不读取或发布response ID、Provider/model、
warnings、usage、provider_metadata、private path/hash。非完整/无效输出公开answer为null，而不造零分。
正文hash不是完整transport envelope/Artifact hash；上游必须另外保存并exact-pin原工件。

这个值尚非盲审包。后继package必须从私有熵分配opaque ID、覆盖所有slice并在Human审查freeze后reveal。
有限答案仍可能使人猜测treatment；这里没有generic text anonymization或匿名性证明。

## 4. 兼容与证据

原Schema目录、Catalog、H1–H5 producer/source和历史报告不修改；不将这个正文塞进旧integer projection。
独立compatibility用例直接运行旧H4 `_project`：整数继续可投影，本codec的JSON仍拒绝。
没有新增record kind/Schema或重解释旧purpose；未来live记录版本新增时必须显式处理catalog/source身份。

[新增测试](../../../../tests/test_bounded_evidence.py)覆盖闭集/格式/规模、正文与metadata泄漏、
解释器深度差异、非完整finish与所有未完成lifecycle、原usage/正文保留、immutable/canonical值，
以及上述旧H4兼容。刻意保留“结构合法但科学判定可能错”的正例，防止把checker当Human判分。
本地结果和实际hosted CI按各自exact commit记录；22个小用例不冒称整个Harness/live集成验收。
初次depth诊断FAIL保留，随后加显式depth ceiling；capture-gap如实保留。

## 5. 后继交付

先完成同一pure-codec的R2审查与CI证据，继续使独立Skill Evaluation的Task/input/checker/Method/egress
相容性可审查；实际forward证据、Human blind review与具名admission独立于M5 A4。
同时可在隔离分支准备live-purpose、授权/applicability输入与真实M6/M11集成候选，但不能把自报字段当授权。
原外部Gate闭合后才提出Task合法进入，最终actual source/config/Schema/install再冻结，运行全部Pilot run set，
完成cold replay→Human review/freeze→reveal→metric/analysis→具名收口，并在M5-004前停止。
