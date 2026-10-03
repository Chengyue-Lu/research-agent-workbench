# M6-010 Flash 真实部件进度

2026-10-03。M6-009 已接受；M6-010 保持 **BLOCKED**。最后一组真实运行通过 Tool shape、
一次纯 client Tool 执行及结果往返文本断言，Schema 请求在发送前因 `deadline-exhausted` 停止。
完整三步 conformance 尚未通过。本文记录可观察执行事实，不是具名 Task/run 接受。

## 基线与执行边界

文档基线为 develop `e0682586a024a8ddfe75bac7221a1a028bfa2dd8`；实际产品安装冻结在
PR128 实现 `c3af91f78918d13149dbadf22697562ddff0c661` / 合入
`3e01158bbf6730bcd3089356e7e307cef4b857dc`，PR129 只完成离线收口。
本次进度不改产品、Task 定义或公开支持能力。

只用官方精确 `deepseek-flash`、Responses nonthinking 和固定合成输入。模型与闲时窗在启动前
按[官方价格与模型页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)核对；本日执行选择
UTC 10:00–12:00（北京时间 18:00–20:00），同时满足用户时间下限和当日官方周末闲时条件。
该窗口不是次日自动授权。凭据由本地辅助链只注入选定子进程，协调者不读取密钥值。

沿用[既定计划](../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)：累计实际成功/失败 input+output
不超过 10,000,000；每 Attempt 最多三次调用、256 output tokens/次、一次无副作用 Tool、
API deadline 120 秒，无自动 retry/fallback。失败停止、离线修复和重新冻结后才另选 fresh Attempt，
initial + 最多两次修复复验。外层原生子树 600 秒及 cooperative 605 秒是进程控制边界，
不延长 API deadline。费用/币种不可得记录 unknown，按用户决策不阻断；未知 token 仍 held-STOP。

## 已运行与保留的失败

| native 启动 | durable Attempt | 已收到响应及用量 | 停止事实 |
|---|---|---|---|
| 001 | 无 | 无报告/账本；Provider 0 仅为启动顺序和文件不变的有界推断，凭据操作 unknown | PS5.1 JSON 数值被解析为 Decimal，入口类型检查拒绝，exit 70 |
| 002 | 1 | 一个 Tool 响应，321 input + 49 output = 370；Tool 1 | 第二个 reservation 在发送前 deadline 停止并 release |
| 003 | 2 | 一个 Tool 响应，321 input + 49 output = 370；Tool 1 | 第二个 reservation 的全局 ordinal 4 被入口 local 1..3 误拒，发送前 release |
| 004 | 3 | Tool 响应及往返文本响应，415 input + 50 output = 465；Tool 1 | Schema 对应全局 ordinal 7 在发送前 deadline 停止并 release |

第四次 native 启动选择的是同一账本的第三组 durable Attempt。没有创建第四组 durable Attempt、
自动重试或回退。最终 Root 激活耗时 159.953 秒，parent 未超时；最后 entry 耗时 152.282 秒，
结果为 `failed / deadline-exhausted`。运行总时长包含初始化、校验、停止和归档，不能视为 API deadline。
Schema 未发出，不能把它写成厂商拒绝或 Schema 兼容失败。

独立复核当前和全部历史报告/持久账本一致：三组 Attempt、七个 reservation slots、
四个 durable intents / HTTP delegate entry observations / responses、25 个历史事件。
全历史 input **1,057**、output **148**、total **1,205**；缓存 input 256 是子集，reasoning 0，
不重复相加。未结算预占 **0**，剩余 token 容量 9,998,795；金额/币种 unknown，不声称账单核对。
`provider_invocations` 的当前生成进入计数、预占槽位数和 HTTP 入口数含义不同，不合并成同一指标。

报告的 `live_qualified=false`、`remote_strict_claim=false` 和外部运行接受限定保持原样。
独立复核 PASS 只证明脱敏报告与累计历史相符，不证明 socket、账户账单、native/dependency 安全、
其他模型或正式 M6-010 完成。M5-008 Pilot、A4 admission、科学评价与发布权威均保持原 Gate。

## 修复与离线测量

启动类型检查已加入 Decimal 的有限数值处理；无凭据原生合成链复验通过。
累计 ordinal 修复只针对预先选定阶段与全局槽位，128 个 AST predicate cases 通过；
production journal + FakeDelegate 回归保留三组失败历史，第四次调用/第四组 Attempt 仍拒绝。

全量 875 个文件的原 32MiB+1 读取改为 stat size+1 完整读取，保持 size、SHA、前后 identity
及全部祖先检查。相同本机测量由 6.938 秒降至 1.188 秒；最终 12 个文件竞争/篡改回归通过。
首次 Windows rename fixture 在 stream 未关闭时失败，修正 fixture 后才通过，原失败保留。

最后失败后的离线候选测量：129 pins / 1,980,128 bytes，固定读取 0.546 秒、sized 读取 0.125 秒；
完整 cold graph verifier 对 80 个模块仍各读取/校验相同 1,192,078 bytes，单次验证内复用 AST
使实际 parse 从 797 次降至 80 次，2.328 秒降至 1.078 秒。没有跨验证缓存、文件/SHA 缓存或
guard PASS 缓存，也没有导入/执行 archived product modules。上述后两项只是离线候选，未进入产品，
不构成完整 runtime 性能结论或下一轮 deadline 可达的证明。

## 下一步条件

1. 完成最小校验开销修复的离线审查和完整 Windows 合成链复验，继续检查每次 use-boundary。
2. 三组计划已耗尽；追加真实运行前明确修订计划与保留全部累计历史的状态处理方案。
   不 reset DB/anchor、不另建空 namespace、不借 token 容量绕过 Attempt cap。
3. 在新的 exact implementation/config/helper/context/output 重新冻结且时间条件满足后，
   才可选择新真实 Attempt；失败即停。只有三步全通过且正式运行接受闭合，才能准备 M6-010 收口。

## 证据索引

[FOLLOWUP-021 Task](attempts/FOLLOWUP-021/TASK.md)、[检查](attempts/FOLLOWUP-021/CHECKS.md)、
[交接](attempts/FOLLOWUP-021/HANDOFF.md)与[风险](RISK_LEDGER.md)保存可发布的事实摘要。
本地私有 archive 的原件未加入公共源码；以下 SHA256 用于核对原件，不认证公共可重放性：

| 本地原件标签 | SHA256 |
|---|---|
| final safe report 1.1.0 | `622034509c520e693cd0ea4e3d8099456f63d7c0b1a6ec4164db75e2f116538c` |
| 独立全历史用量 CHECKS | `94684a7547072595701a12fe95896ce866d5887fef397a87bcd5ea1edd8592bf` |
| final accounting canonical snapshot | `5ba9a21804b3fbbb8fa8719fec8a4b8422d1e809fbf7e96076b5934e3e654e27` |
| 启动所选原始 config 文件字节 | `062947dd957a1ad5cecf23c9d26f84cefcc8a064e865bfc50cb1ae9b8b792719` |
| 实际 profile | `aeb383c278bfb974c6998683ce8d6caab859a60880a76d880142c008585f12f0` |
| 实际 manifest | `38bb83df17c123cdde4c46b1de4a6d3178de28495eca4b9593c95b64cdfd32e7` |
| 实际 source closure | `3f00a47a3fe8ef1a538f790ea4fb15787b9af7cd42a424d3a393333af3ff2269` |

原始 config 文件字节与报告内规范化 configuration 引用分别核对，不混用两种 hash。

所有可见失败回执、选定源码、部分命令/角色交付保留。平台未提供的完整工具事件及更早完整
inter-agent transmissions 存在 capture gap，不重建成虚假完整 Trace，不归档密钥、隐藏思考、
原始 Provider payload 或 Tool 参数。
