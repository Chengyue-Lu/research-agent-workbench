# CHAIN-DEV4-017 Visible Communications

日期 2026-10-08（Asia/Shanghai）；对应 [Handoff](SNAPSHOT_HANDOFF.md)。只存可见任务、进展与检查，不存隐藏推理、Key 或运行原始内容。

## Task Packet 输入

来自主准备窗口 `RWB M5-008 续接`；thread `01a1064a-eaef-7da0-aebd-962910ff42b8`。

> Task Packet CHAIN-DEV4-017。Profile bounded worker，Skills=[]，8分钟。Root Attempt12已CLOSED：5实际HTTP、known20104/held0；main实际Tool两模型循环完成并Receipt，主自选child1，child实际输出blocked，freshmain消费该blocked且停止，Guide未开始。模型理由错误地把提供的hash-pinned inputs.text说成未核验复制、没有本机文件工具所以不能读；真实build_role_request已read_pinned_inputs核Task exactrefs/SHA/UTF8/revision，并把这些同bytes text给模型，actualTrace记录实际contentread。本修复仅clarify baseline事实，不改任何权限Schema/根规则/读集合：_COMMON明确 payload.inputs 是caller按照Task.input_refs真实读取、hash验证的文本快照，可基于该快照完成bounded任务，不要求模型自行另开文件；该快照不授权额外文件、引用追踪或writes，refs列表不等于打开新文件。唯一写 scope entry/roles.py +tests/test_entry_roles.py最小断言 +chain-proof-002/SNAPSHOT_HANDOFF.md/SNAPSHOT_COMMUNICATIONS.md。读范围限上述，roles read_pinned_inputs已有实现、TaskSchema必要部分。新测试证明正确capturedtext/hash及baseline说明，同时stale/refoutside仍原样拒绝；不复制fixture打通、不把caller_context所有数据声明已核验。不要改 caller_context/child结果、权限解释或inputRefs内容；Guide等也仍只获准snapshot。你不是唯一开发者，不撤他人。禁止跑产品/tests/API/Tool、Key/账、Git，Root测试。最小实现静态交接落盘停止，若须新语义则报告停止。

## 对用户的可见进展

> 我会按 CHAIN-DEV4-017 澄清已验证输入快照的使用方式，保留现有读取、哈希和范围检查，并补最小断言。只做静态检查，交接后由主窗口测试。

> 现有代码已读取声明的输入、校验原始字节的 SHA-256，并对同一字节做 UTF-8 解码；指定了 revision 时也会检查。此次只补充这一事实说明，明确其适用范围是 payload.inputs，不扩展到 caller_context。

## 可观察检查

00:27:49+08:00 开始片段；00:29:40+08:00 owned roles/test AST 与内存 compile 均通过。输出文件名发现的 rg 无匹配仅表示报告尚不存在，未当测试失败。只改 `_COMMON` 文本和必要断言；无产品运行、测试执行或项目 import。source pins 见 Handoff；交接前复核 Markdown 目标与 pins。

## 主准备窗口完成通知

同一窗口，2026-10-08 00:31:41+08:00 在确认两 source pins 保持、4 个 Markdown 文件目标通过后发送，工具返回成功。冻结通知后只写报告，无源码编辑、项目 import 或测试执行；片段至此停止。

> CHAIN-DEV4-017 已完成并停止源码编辑。仅 _COMMON 澄清 payload.inputs 的已有实际读取/SHA-256/同 bytes UTF-8/可选 pinned revision 事实，可直接读快照完成 bounded Task；不扩展文件/refs follow/write 权限或任意 caller_context 验证，Guide 原边界保留。read_pinned_inputs/Task refs/权限/Schema/child 结果未改。roles.py SHA-256 229e4e1e60c778cfe117979926b3805e672922d74498544a936d0820e655e2b3；tests/test_entry_roles.py SHA-256 5571000887d9f8317d6ff27dc958c45554f9906b33721669ae6be3f436715881。新增 captured text/hash/metadata/baseline 断言及精确 stale/outside-ref 错误断言。我仅 AST/内存 compile、Markdown targets/hash 静态检查，未产品/tests/API/Tool/Key/账/Git。收到 Root 最新反馈：当前 roles+Guide 13 项 8.942s PASS，Attempt13 source/body 已冻结，body 26634 bytes；这些是 Root 实测报告，本代理未重跑。按指令冻结后无源码编辑，只落盘交接。报告 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/SNAPSHOT_HANDOFF.md、SNAPSHOT_COMMUNICATIONS.md；旧 Attempt12 blocked/freshmain 停止/Guide 未开始结论保持，新 Attempt由 Root 独立实际发送与归档。

## 落盘期间收到 Root 冻结通知

> Root已执行当前Snapshot代码的roles+Guide13项8.942s PASS，并为Attempt13冻结548source/body26634 bytes；准备真实调用。请现在结束代码编辑，只落盘现有handoff/comms/hash并停止，避免冻结后源漂移。你的packet仍不允许测试/API/Key/账/Git。

> 代码编辑已结束。主窗口报告当前 roles＋Guide 的 13 项测试通过，并已冻结 Attempt13 的 source/body；我只补记这条验证反馈和交接，不再修改源码。
