# M5-008 Conformance 与 Pilot 显式适用关系候选

2026-10-04；隔离 R2 候选，Draft PR136。Evaluation owner：路诚钺；Provider/API applicability owner：黄毅。未形成新的具名接受、共同 live qualification 或 Pilot grant。[ADR candidate](ADR_CANDIDATE_CONFORMANCE_PILOT_APPLICABILITY.md) 仍 Proposed。

M6 报告绑定 `GuardedConformanceTransport`，Pilot 使用 `GuardedPilotTransport`。两者保留各自 manifest；默认 [factory](../../../../src/research_workbench/evaluation/live_verification.py) 继续严格核对同 binding，不能重标 class 或修改历史 report。

## 冻结与冷比较

[reader](../../../../src/research_workbench/evaluation/live_applicability.py) 的辅助关系版本为 `1.0.0`，kind 为 `evaluation_provider_applicability_relation`，purpose 为 `m5-conformance-to-pilot-applicability`。它不是 Core Registry kind 或许可。调用者必须显式提供 `applicability_relation_ref`，且该 ref 必须等于 frozen context 的 `provider_applicability_ref`；文件内容不会自动开启新路径。

关系引用原 qualified report、Conformance manifest 和当前 Pilot manifest，并保存完整 comparison 与固定 limitations。原 report 仍由 M6 cold reader 验证 class、source closure、config、warnings 和 accounting；factory 仍要求 accounting 与独立选择的原 M6 journal snapshot 全等。跨 run 累计预算只走独立 budget checkpoint。

两份 manifest 必须是既有 source-graph 版本，且 adapter class/version、provider identity、credential reference/class、compiler/runtime、model/generation policy 和 transport response limit 一致。profile 与 resolved config 按完整内容相等核对，允许不同 archive 相对路径；当前 Pilot config FileRef 必须与 frozen context 全等。模型/Profile/凭据/runtime 变化须另行资格处理。

comparison 列出两侧 source roots、closure refs、transport identities、共同信任边界，以及 module 并集中每一项原/新 SourceRef 与字节是否相同。新增、删除、内容变化和不同 archive 路径均保留。reader 冷重算整个对象，拒绝遗漏、额外 approval 字段、来源替换及 limitations 删除，不导入 archived Python。

## 具名决定与实际对象

既有 actual Provider observer 核对当前 Pilot manifest 与 Protocol Adapter/Model；独立 runtime observer 核对当前 source commit、Windows context 和 source artifact refs。完整原 report 和完整关系传给可信 Human verifier。

具名 Provider Decision 的 `m5_live_provider_applicability` 除当前 context、Pilot binding 和 runtime observation 摘要外，必须精确绑定关系 FileRef、原 report、原/新 manifest、完整 comparison 摘要和 limitations。旧同 binding Decision 不能接受此关系。Human callback 须验证真实人的接受；accepted/actor/哈希不能提供权限。慢核验后再次核对全部已读取证据字节及当前 loaded Provider，每次实际入口仍由 [use guard](M5-008_LIVE_VERIFICATION_PACKET.md) 重算并检查当前时间、官方窗口和原预占。

## 范围与下一步

比较结果是结构证据，不证明共同 live conformance、远端 fidelity、wrapper instance delegate/callback 来源、失败请求 token 上界、账户/数据权限、Skill 准入或四臂授权。原 report 与 compiler/native 的限定保持。黄毅须评价完整差异及执行证据，再作实际具名适用决定；路诚钺负责 M5 证据/trace 的语义边界。

[离线用例](../../../../tests/test_live_applicability.py) 使用真实临时 archive、cold reader 和实际不同 facade 对象；报告调用、Human、input bound 与 runtime authority 均是 synthetic。临时 Pilot journal 只用于构造 facade，未调用或预占，其初始化 context 早于测试最终关系，不能用于运行许可。测试须绑定 exact source 回执，不是实际接受或 scientific correctness。

actual input proof 仍开放：官方 Responses 资料说明超 context 返回400，但本候选未取得失败请求计费上界保证，未建立公开 encoding 与 hosted API 的完整等价。没有 tokenizer 执行、model GET、付费调用或 Key 读取。可信 current observers、合法 Model slice、实际 Skill Trial/A4 lineage、generic Driver、cold replay、盲审评分和完整 run-set 具名接受仍待分别完成。
