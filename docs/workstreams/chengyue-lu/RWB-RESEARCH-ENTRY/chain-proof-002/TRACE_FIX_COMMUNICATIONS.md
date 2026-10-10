# CHAIN-DEV4-014 Visible Communications

日期 2026-10-08（Asia/Shanghai）；对应 [Handoff](TRACE_FIX_HANDOFF.md)。这里只留可见任务与运行观察，不保存隐藏推理或 secrets。

## 输入 Task Packet

来自主准备窗口 `RWB M5-008 续接`，thread `01a1064a-eaef-7da0-aebd-962910ff42b8`。以下仅将消息中的机器绝对 checkout 地址规范为 CODEWT 标签；目录定位原文由发送窗口保留，产品/文档引用使用仓库相对路径。

> Task Packet CHAIN-DEV4-014。继续在 CODEWT 配合，Agent Profile worker，required Skills=[]。你不是唯一工作者，不撤销其他编辑。Root实际Attempt11 Tool handler invoked1但Trace结果写入FileNotFoundError：trace绝对目录216字符，当前operationid结果文件路径276字符；tool-events目录存在。允许读取 src/research_workbench/observability/trace.py 的 _record_tool/_create_exclusive 与Tool引用校验、tests/test_trace*.py文件名及相关Tool用例。唯一产品写 scope trace.py +相关最小trace测试；报告写 chain-proof-002/TRACE_FIX_HANDOFF.md、TRACE_FIX_COMMUNICATIONS.md。修复采用短、可冲突避免的结果文件名，例如事件序号+operation_id SHA前12hex，保留实际operation_id原样在event，结果引用/hash仍由实际文件产生；不变Schema/权限/原件，不改全局_safe_id。用极长/不安全operation_id测试文件名有界、两调用不同文件、原id事件保留、Trace引用可验证。禁止执行产品/测试/API/生产Tool、Key/账、Git；Root负责测试，静态syntax/AST可做。8分钟预算，最小修复及handoff落盘即停止，发现需要核心语义变更则给缺口停止。

## 对用户的可见进展

> 我会按 CHAIN-DEV4-014 补齐 Tool 结果文件名的长度问题，保留事件中的原始 operation_id，并添加最小回归用例。只做静态检查；测试由主窗口执行，交接落盘后停止。

> 已确认结果文件名直接拼入了 operation_id，既可能超长，也可能在不同 ID 清洗后重名。我会改为“事件序号 + ID 的短哈希”；完整 ID 继续保存在事件中，结果引用和哈希仍从实际文件生成。

> 修复与两项回归用例已写好：覆盖超长且含不安全字符的 ID、清洗后重名的不同 ID，以及重复 ID 的多次结果。两份 Python 文件的 AST 与内存编译通过；回归尚未执行，我正在保存源码哈希和交接。

## 可观察检查

00:18:41+08:00 开始本片段。00:20:37+08:00 两份 owned Python AST/内存 compile 通过，未 import 项目或执行测试。文件名发现报告输出尚不存在的 rg 返回无匹配，不是 syntax 检查失败。产品只改结果路径一处，不改 `_create_exclusive` 或 validator；回归复用已有 TestCase。源码 pins 见 Handoff；交接前检查 Markdown 目标与 hashes。

## 发主准备窗口的完成通知

目标仍为上述主准备窗口；2026-10-08 00:22:16+08:00 在交接落盘并复核两份 source pins、AST/内存 compile 及 4 个 Markdown 文件目标后发送，工具返回成功。本片段至此停止，未执行产品/测试/API/生产 Tool。

> CHAIN-DEV4-014 已完成最小修复并按预算停止。trace._record_tool 的结果文件名改为事件序号 + operation_id SHA-256 前 12 hex；原非敏感 operation_id 原样留在 event，沿用既有脱敏与 O_EXCL，result_ref/hash 仍取实际文件，未动全局 _safe_id/Schema/权限/旧原件。trace.py SHA-256 31c60dcd8ed61d8d6437f5001c9072f8c4a234197db487ed1f919d51c465bed5；tests/test_agent_trace.py SHA-256 11a930d9be9b955f626db5722c66ed0d9241fa1feb0f4632a91e6209756491c4。新增两个回归：long unsafe ID 的文件名有界、原 ID 与实际文件/hash/index引用保留；不同 ID 清洗重名及重复 ID 三次调用的结果文件互不覆盖、引用可验证。仅 AST/内存 compile 和 Markdown file target/hash 静态检查；未执行测试/产品/API/生产Tool/Key/账/Git。Root 下一步运行两项新测试和 Agent Trace 相关 suite，确认结果后重冻 Source，再决定新 Attempt；Attempt11 原失败不改判。交接：docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/TRACE_FIX_HANDOFF.md、TRACE_FIX_COMMUNICATIONS.md。
