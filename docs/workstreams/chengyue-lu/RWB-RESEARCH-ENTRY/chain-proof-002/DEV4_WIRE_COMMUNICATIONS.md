# CHAIN-DEV4-008 Visible Communications

2026-10-07；按本 Packet 保存本片段可见指派、进展、发现和交接；不保存隐藏推理、Key 或运行响应。对应 [Handoff](DEV4_WIRE_HANDOFF.md)。

## Root 指派

> 执行新有界 CHAIN-DEV4-008，Packet 已落盘同 chain-proof-002/DEV4_WIRE_TASK_PACKET.md。Root 已实测 pure codec 缺口 FAIL，ConfiguredProvider 有另层 preflight 但 encoder 漏 Profile limits；请仅将 _Profile 保留已有 validated implementation.limits 不可变 mapping，并向 pure preflight ProviderCapabilities 传 limits。只 wire_codecs.py 及对应 handoff/communications，5 分钟 1 轮，只 AST/compile，Root 跑全部测试。API 第一 Attempt 已闭账：intake 真实成功 7388 token，Root Supply 枚举错误停止后层，累计 63002 held 0；没有运行中的 API，修复后新 Source 重冻。不要再改 007 test，保留当前准确回归。你不独自在代码库，其他内容不动。完成即停并给 source hash。

## 对用户的可见进展

> 我会先读 CHAIN-DEV4-008 的 Packet，只补 wire encoder 保留并传递 Profile limits 的接点，保留 007 的回归用例。完成静态检查和交接后停止，测试与新 Source 重冻由 Root 负责。

> 已确认纯 encoder 在构造 preflight 参数时丢失了 Profile limits。我正在补上不可变保存与传递，并保留现有的 256→257 拒绝回归；行为验证仍由主窗口执行。

> 补上 limits 传递后，又确认下游的 base.preflight 没有检查这些限额，所以仅此补丁还不能证明 256→257 会被拒绝。我已把这个具体缺口通知主窗口，会在交接中明确记录；下一步需由主窗口补齐检查并复测。

## 15:47:39 UTC 发主准备窗口

目标：RWB M5-008 续接；thread `01a1064a-eaef-7da0-aebd-962910ff42b8`；已返回成功。

> CHAIN-DEV4-008：已在 wire_codecs 的 _Profile 复制为 MappingProxyType 并保留 limits，pure snapshot 传 limits，007 test 未动。窄读 base.preflight 完整函数发现它根本不读取 snapshot.limits，只检查 max_output_tokens > 0，因此 Packet 的两处 wire 传递补丁单独仍不足以拒绝 256→257。我保持 ownership 只改 wire；请 Root 决定自己补 preflight 的 limit checks，或将本 Packet 追加为 wire 本地 admission checks。预算余约 2 分钟；我先完成静态 handoff 并明确未决，不会声称回归通过。

## 最终交接通知

同一主准备窗口；15:48:42 UTC 工具返回发送成功。该次检查确认 AST/内存 compile、source hash、未改 regression hash 和 7 个 Markdown 文件目标通过；没有执行产品或测试。通知内容如下。

> CHAIN-DEV4-008 已完成静态候选并停止：wire_codecs._Profile 复制/不可变保留已有 implementation.limits，并向 pure ProviderCapabilities snapshot 传 limits；source SHA-256 a8d4e090a678b3b7895914fce261f61c2c7e6959fc0913f740ef1c478d15c77d。AST/内存 compile 通过；007 test 保持 hash 59d1d8e42168258aebdff62607977134542254f95226f804688436e43c576983。关键未决：base.preflight 不读取 snapshot.limits，因此本补丁仅完成传递，仍不能宣称 256→257 回归通过。Root 需补限额检查并实测后新 Source 重冻。交接 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/DEV4_WIRE_HANDOFF.md、DEV4_WIRE_COMMUNICATIONS.md。未测试/API/Tool/Key/账/安装/Git/primary memory；Root 所报前 Attempt 关闭数据未由我读取核实。
