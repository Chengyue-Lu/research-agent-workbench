# M6-010 DeepSeek Flash 受限收口

2026-10-04。本 feature 候选将 [M6-010](../../../TASKS.md) 从 BLOCKED 置为 DONE，
完成判断仅接受以下已经运行并保留的 exact Windows / Flash Provider 与 Session 部件证据。
Task 定义、依赖和验收原文保持不变；共享 Task 状态随本 PR 的接受与集成生效。

用户路诚钺直接要求“可以，你来进行M6-010收口，132部分也交给开发2窗口继续执行”，并已明确
授权范围内的后续推进默认审批、实际硬阻断除外。此前的 Flash-only、北京时间 18:00 后及官方
闲时窗、成功失败累计 10,000,000 tokens、最多十组、费用未知可继续的直接决定构成本次
`M6-DEEPSEEK-LIVE-AUTHORIZATION-GATE` 的依据。Provider/Session 维护者仍为黄毅；
该来源记录用户维护者判断，不代填黄毅新的个人 approval 或 reviewer 不可用事实。

原报告永远保持 `live_qualified=false`、`remote_strict_claim=false` 和当时具名接受为 null。
报告 writer / cold reader 不产生 Human acceptance；此处的 Task 完成判断在报告外部，绑定原始
source/config/run，不能通过修改历史报告取得资格。

## Exact 验收对象

| 对象 | 固定身份与边界 |
|---|---|
| 产品源 | `66f24a29335ced059a460d879418e07a6c7e6ea0`，FOLLOWUP-023 installed002 的非 editable Python 3.11.16 Windows 安装 |
| profile | `deepseek-responses-nonthinking-v1`；profile SHA-256 `aeb383c278bfb974c6998683ce8d6caab859a60880a76d880142c008585f12f0` |
| 请求与观察模型 | 均为 `deepseek-flash`；当时官方映射 DeepSeek-V4.1-Flash，观察的别名不证明服务端不可变 build/revision |
| endpoint / 模式 | `https://api.deepseek.com/responses`；`reasoning.effort=none`，真实传输使用 `UrllibTransport` |
| 配置 | candidate SHA `1e5810d24f6366491d27902871c2b2c5e56ece6261dc6a9a1e3d8e50f3efc618`；resolved SHA `1e8de27b6e047bd6c0a7b9eb9f5badd4243c28871c781bb7a1e5a97f07ae3ee2` |
| source binding | manifest1.1 SHA `a77f7d0e7bec8f15347589b97acd43b493742f6967804c31a83878ed7cfcfe4f`；81-module v3 closure SHA `7c07093cc2571f8953b056822705e87d9dc4067481b2f4a49558d12e82dcf2bc` |
| Windows / Credential | actual005 variant003 的七份 source、安装/dependency/runtime/executable、descriptor 与 rendered entry 均按原 refs 固定；genuine bridge 仅向被授权子进程注入本地 Credential reference，未读取/归档密钥值 |
| 固定输入与输出 | 纯合成、单个确定性无副作用 Tool、每次 body ≤4096 bytes；报告及 Session summary 只保留闭集元数据，不保存原始 prompt/response/tool arguments/隐藏思考 |
| 调用与预算 | 每组 ≤3 次调用、一次 Tool、每次 ≤256 output tokens；累计 input+output ≤10,000,000，未知 usage 保留预占并停止；原 baseline3 只由 append-only grant 扩为 effective10 |
| 时间 / 重试 | 原选定 UTC `2026-10-03T13:25:00+00:00`–`15:00:00+00:00`（北京 21:25–23:00）；运行前官方 fresh recheck 和逐发送时间 guard；shared360 / socket180 / parent600 / cooperative605 秒，0 自动 retry/fallback |
| 已接受运行 | native005 / durable Attempt4；本地 calls1..3 对应同一持久历史的 global slots8..10，三步全部完成 |

完整 Windows context/source/helper/计划/授权/输出绑定的原件仍在私有归档。
[公开证据索引](evidence/M6-010_CLOSEOUT_EVIDENCE_INDEX.json)给出 24 份原件的相对定位、
byte size 与 SHA-256；它同时保留独立 review 和本次只读复核结果。原件访问是完整 cold replay
的必要输入，公开索引本身不认证原件 producer、机器时钟、账户或人类身份。

## 原验收条款逐项核对

| M6-010 要求 | 结果与可定位证据 |
|---|---|
| 依赖 M6-009 / M6-002 与具名 live 授权 | 两个 Task 已 DONE；[M6-009 收口](M6-009_COMPLETION.md)和用户直接决定；授权原件的 hash 见公开索引。十组上限包括已经失败的组数，不是可另开十组 |
| exact source/profile/model/config/Host/Tool/report 冻结 | 上表；[FOLLOWUP-023 检查](attempts/FOLLOWUP-023/CHECKS.md)；installed002/packet002、actual variant003 selection/source manifest 和独立 source review 均留存 |
| 北京 18:00 后且官方闲时 | actual005 的 invocation 与 completion 均在当时选定窗口内；原 fresh official recheck、每次发送 guard 和 deadline refs 留存。此事实不授权未来窗口，也不宣称独立认证物理时钟 |
| fixed Tool shape / fresh Session / 本地参数验证 | 第1次 specific Tool 请求得到匹配 shape；本地 validator 后真正执行一次纯 Tool。原 Session summary 记录单 Session 的 specific→结果回传→none 两轮；独立 reviewer 与本次复核一致 |
| text 与 Schema | 第2次往返文本断言通过；第3次独立 Schema 断言通过。Schema 调用属于同组第三个 reservation，Session summary 只描述前两轮，不假称它包含第三阶段 |
| bounded calls / stops / usage | current3 entries、3 responses、Tool1；parent exit0 / 186.422s，entry179.172s；新用量483 input+56 output=539。所有三份 usage 都与对应 durable `reported_usage` 一致 |
| 全部失败、累计预算与未知成本 | 原前三组 failed、1205 tokens、3 个 before-send release、native001 启动拒绝及全部准备失败保留。全历史4 durable Attempts /5 native launches /10 slots /7 responses /40 events /41 checkpoints，1540+204=1744，held0；金额/币种/账单仍 unknown、未结算核对 |
| 零请求阻断、预算停止、source/config drift | [FOLLOWUP-023](attempts/FOLLOWUP-023/CHECKS.md)的 helper 漏图/guard 后 drift/真实 Windows 合成入口和预算上限拒绝；[FOLLOWUP-024](attempts/FOLLOWUP-024/CHECKS.md)的闭账本零凭据/HTTP失败报告与授权原文篡改拒绝。负例使用合成状态，不故意发无效 live 请求 |
| 独立脱敏报告复核 | [原始报告副本](evidence/M6-010_ACTUAL005_REPORT.json) SHA `1f0bef0cbf1bea5f9b1744a8801f62c7aac3e05c86f34b9b9e8b76781cda70d8`。独立 review006 的 exact installed pure reader / SQLite ro+immutable audit PASS；本次重复只读核对 PASS，原40 checkpoints与前三组字节前缀未变 |
| exact 接受与其他 Gate | 只接受上述 Flash Provider/session 事实；M6-004、M11 E2E、A4 Runtime admission、M5 pilot、科学评价和发布仍各有独立验收；M5 状态未改 |

cache384 为 input 子集，reasoning0 为 output 子集，不重复加到1744。持久字段
`provider_invocations=10` 表示历史 reservation slots；实际 delegate entries/responses 为7，
不能把10解释成十个成功远端调用。报告的 unknown cost 依照用户直接决定非阻断，unknown token
仍会停止；没有把“账单不可核对”误当成“token 可未知”。

## 当前 develop 的适用性

[PR #131](https://github.com/Chengyue-Lu/research-agent-workbench/pull/131) 已于 2026-10-04 合入
`ede2bc1d5e3496b4e4c72abb1f39f0a3ce00aedf`；其 tree 与最终 head74 相同。
source66 到该基线的 Provider 产品变化只有两个模块：

- `profile_conformance.py` 将扩限 metadata 的存储异常纳入已有 `accounting-failed` 脱敏报告路径；
- `conformance_journal.py` 将用户授权原文改为 exact-byte/hash 读取；prefix / decision 的 canonical JSON 校验保留。

其余变化为 CI producer/汇总与测试、文档维护。传输、四协议 codec、factory、Session、Tool、body
policy、profile/model 和对应 Schema 没有变化；两个修复的具体故障与正常路径有
[FOLLOWUP-024 离线证据](attempts/FOLLOWUP-024/CHECKS.md)，最终合入候选组件 CI 为594 PASS。
本次仅做文档和既有脱敏证据发布，没有新 Provider 请求、Credential 操作、账本初始化或 grant。

这个 delta 复核使当前工程状态可说明，但不把 source66 报告重绑到新 graph/config。M5 采用
新的 actual source/config/purpose 时仍须逐项复核上述 exact binding 的适用性；无法闭合相同对象
时，重新冻结并在原唯一累计账本上做必要的有界验证。Task DONE 不意味着以后任意 API
配置都可运行，不绕过 A4 Release→Projection→Supply→Resolution→Snapshot→Bundle→View→Host
lineage 或 pilot 专属授权。第三方 SDK/AST 优化都不是本项的新验收依赖。

## 保留的信任边界与后继

原 `caller-attested-gates`、`partial-source-closure`、`input-bound-proof-unverified`、
`windows-run-unaccepted`、`remote-strict-unclaimed` warnings 和平台 capture gap 原样保留。
81-module 源码图及安装/runtime pins 证明选定对象一致性；它们不证明全部 native/compiler/dependency
行为、真实 socket 出站、账户数据控制或 server build。input1,048,576 是按当时官方1M context
作保守预占的执行选择，body 上限和实际 usage 可复核，未宣称独立 tokenizer/计费证明。
本项采用这些披露边界下的合成部件验收，不产生远端 strict、全厂商或科学正确性结论。

develop 的完整 CI `37168512882` 在本次快照中仍运行，Python3.13 compatibility 已失败；
本项冻结的是 Windows Python3.11.16，未把594组件或本地复核当作全量/多版本/coverage通过。
全量诊断和 [PR #132](https://github.com/Chengyue-Lu/research-agent-workbench/pull/132)由开发2
继续负责。后继 M5-008 先形成 live purpose/有限 review projection、真实 A4 admission 与 pilot
专属计划；Provider binding 适用性是其中的实际 Gate，而非自动授权四臂实验。
