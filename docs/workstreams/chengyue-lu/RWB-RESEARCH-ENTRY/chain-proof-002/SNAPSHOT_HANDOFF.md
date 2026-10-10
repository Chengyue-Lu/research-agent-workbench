# CHAIN-DEV4-017 Compact Handoff

2026-10-08（Asia/Shanghai）；Profile bounded worker；required-Skills=[]；8 分钟。主准备窗口的本 Task Packet 及可见通信保存于 [SNAPSHOT_COMMUNICATIONS.md](SNAPSHOT_COMMUNICATIONS.md)。当前 CODEWT 局部候选，未提交、合入或具名接受；不代签 Source/live/Human 资格。

## 问题来源与可确认事实

Root 报告 Attempt12 已 CLOSED：5 次实际 HTTP、known 20104/held 0；main Tool 两模型循环及 Receipt 完成，自选 child 1；child 实际 blocked，fresh main 消费该 blocked 后停止，Guide 未开始。Root 将模型拒绝理由定位为误解输入快照：它把 hash-pinned inputs.text 当作未核验复制、并要求本机文件工具。上述运行事实/Trace content-read 由 Root 提供，本代理未读运行原件或账复核。

窄读实现确认 `build_role_request` 先核请求 refs 属于 Task exact read set，再调用 `read_pinned_inputs`；后者对原始文件 bytes 检查 SHA-256、可选 pinned revision、UTF-8 解码，并将这些相同 bytes 的 text 捕获至 payload.inputs。当前缺口是 baseline 未向模型说明这项既有读取事实。

## 最小修改与 source pins

| 文件 | 实现/测试范围 | SHA-256 |
| --- | --- | --- |
| [roles.py](../../../../../src/research_workbench/entry/roles.py) | 仅补 `_COMMON` 对已验证文本快照的说明，供五种现有 role baseline 使用 | `229e4e1e60c778cfe117979926b3805e672922d74498544a936d0820e655e2b3` |
| [test_entry_roles.py](../../../../../tests/test_entry_roles.py) | 新增 snapshot text/hash、metadata pins 与共享 baseline 断言；加强原 stale/outside-ref 拒绝错误断言 | `5571000887d9f8317d6ff27dc958c45554f9906b33721669ae6be3f436715881` |

说明的边界：payload.inputs 中每个 item 是 caller 从 Task.input_refs 实际读取、核 hash、同 bytes 解码和检查可选 revision 后的文本快照。bounded Task 可以使用 inputs[].text，无需为了读取同一快照而再次打开文件或另需本机文件工具。仅 refs 列表不代表额外文件已打开；快照不授予额外文件读取、自动追踪引用或写权限。该验证说明只适用 payload.inputs，不扩展至任意 caller_context。

读取实现、Task refs 内容、读集合、权限解释、Schema、根规则、caller_context 和 actual child results 完全沿用现有代码。Guide 的独立只读、无 Tool/no-follow-ref 等限制保留。没有复制运行 fixture 或把 baseline 说明作为放宽硬条件的依据；这里只澄清既有事实，不需要新的核心语义/ADR。baseline 字节及既有自动计算的 baseline_sha256 将变化；旧 Attempt/Source 不重绑或改判。

## 新测试及静态检查

`test_verified_input_snapshot_and_baseline_explain_existing_read` 复用原测试生成的 source.txt/Task refs，比较 captured text 与真实 UTF-8 bytes、实际 SHA 与 Task pin、用户 payload/baseline metadata hashes；并对现有各 role（包括 Guide）的 baseline 检查快照读取/验证说明与访问边界。原失败 child context 保留在既有测试中。

原 `test_hash_drift_and_extra_inputs_are_rejected` 保留相同数据与调用，只将泛化异常断言加强为 `input hash mismatch` 与 `outside Task exact read set`，避免把其他失败原因误当精确边界拒绝。

2026-10-08 00:29:40+08:00 两份 Python AST/内存 compile 通过；未执行 code object 或项目 import。返回前检查 source hashes 与交接相对 Markdown 文件目标。测试代码未执行，静态通过不证明模型下一次会成功或全链完成。

没有运行产品/tests/API/Tool、Key/账、预占、安装、Git 或 primary/global memory 写入。只修改上述两份源码/测试文件与这两份报告，保留其他工作者更新。

实际读范围：收到的 Packet、owned roles.py（包括 read_pinned_inputs/精确 refs 门槛/共享 baseline）、owned role 测试及 helper、TaskSchema input_refs/revision 必要段，以及 primary PROJECT_MEMORY 当前导航摘要。未读取原始 API 输出、actual Trace、私有输入、fixture corpus 或其他代理产物。

## Root 下一步与连续性

1. 交接落盘期间收到 Root 最新反馈：当前 Snapshot 代码的 roles+Guide 13 项测试 8.942s PASS；已为 Attempt13 冻结 548 source/body 26634 bytes，准备真实调用。上述结果由 Root 实测报告，本代理未重跑或读取测试日志；收到冻结通知后无源码编辑。
2. Root 在已冻结 Source 上继续实测角色正确消费实际快照并归档结果。此次候选不改判 Attempt12 的 child blocked/freshmain 停止/Guide 未开始，也不替代新 Attempt 的真实成功产物与接续检查。
3. 当前 primary PROJECT_MEMORY 摘要仍记到 Attempt11，与本 Packet 更新的 Attempt12 有时间差；Root 核实后写共享连续性摘要。本片段无该文件写权。

Coordinator 建议条目：

> 2026-10-08 · CHAIN-DEV4-017：根据 Root Attempt12 的 child blocked 理由，局部候选在 role 共享 baseline 澄清 payload.inputs 是已有 Task exact refs 的真实读取/原 bytes hash 与 UTF-8 快照，可直接基于快照做 bounded 工作；不授予额外 reads/refs follow/write，不把 caller_context 全部声明已核验。read_pinned_inputs、Task refs、权限/Schema/child 结果保留。新增 snapshot/hash/metadata/baseline 与精确拒绝断言代码；本代理仅 AST/内存 compile、交接 hash/link 静态检查，未运行测试/API/Tool/Key/账/Git。Root 报告 roles+Guide 13 项 8.942s PASS、Attempt13 已 source/body 冻结；冻结后本代理无源码编辑。来源 chain-proof-002/SNAPSHOT_HANDOFF.md、SNAPSHOT_COMMUNICATIONS.md；本地未提交/接受。Next Root 完成新 Attempt 实测与归档，原 Attempt12 blocked 结论保留。
