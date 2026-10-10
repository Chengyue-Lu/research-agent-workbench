# CHAIN-DEV4-020 Compact Handoff

2026-10-08（Asia/Shanghai）；Profile boundedworker；required-Skills=[]；budget 8 分钟。Task Packet、条件限定及 Root 冻结通知保存在 [OUTPUT_PUBLICATION_COMMUNICATIONS.md](OUTPUT_PUBLICATION_COMMUNICATIONS.md)。当前 CODEWT 本地候选，未提交/合入/具名接受；Root 是唯一产品/tests/API/Tool 测试者。

## 问题与职责来源

Root 报告 A14 CLOSED，3 次 API/1 次 Tool：main 观察完整，但因没有文件写 Tool、无法提前证明 report 发布，并将 Supply report ref 与 Tool 名字串不等视为不同供给而 blocked。本代理未读取该运行原件或账；保留其原 blocked/closed 结论。

窄读 [Driver](../../../../../src/research_workbench/entry/driver.py) 确认：`execute_role_slice` 用冻结 View 权限检查输出/archive path、要求 fresh 路径，发生在 Provider 前；`SessionExecutionDriver.execute` 把最终响应写入既定 output_path，生成实际文件 pin、Trace file revision 与 output_contract artifact，后续既有 Host/closeout 检查形成真实 Receipt。发布有真实范围与 I/O 条件，模型没有依据提前宣称成功。

## 最小实现与 hashes

| 文件 | 改动 | SHA-256 |
| --- | --- | --- |
| [executor.py](../../../../../src/research_workbench/entry/executor.py) | builder context 增加从实际 FrozenRoleBinding 生成的 pending 发布记录 | `39c4507cd93607eddd0177e5aff4599fd1f0913088e90a595c48a420d56bfe3f` |
| [roles.py](../../../../../src/research_workbench/entry/roles.py) | `_COMMON` 条件说明 Driver 发布职责，以及 Supply refs/Tool/capability 的类型差异 | `8aefb70782c8b091fe7f75305b6c38f0ee4a4a3971621135a55614f63cf5fbd9` |
| [test_entry_executor.py](../../../../../tests/test_entry_executor.py) | 原 joint 用例断言 context 来自 actual binding/path/contract、pending flags 和 Guide 无该记录 | `fdf6eeaf437c47363f52d06fb5b963ff5c86bc94ef71e4389a5aea3f7b5228c0` |
| [test_entry_roles.py](../../../../../tests/test_entry_roles.py) | 条件 baseline/pending/真实失败边界、无记录和 intake 原 compiler 路径断言 | `3ceb75b0d3cc10c19e9cca6d958962da11574d81d668ce4acd0d30f5c2f40afd` |

`caller_context.driver_output_publication` 是事实性的预定职责 metadata，含 `publisher=SessionExecutionDriver`、`status=pending`、原 binding.output_path/output_contract，以及 `boundaries.permission_grant=false`、`publication_complete=false`。每次由 executor 自己从该次 actual binding 填入，其他 caller_context 数据/actual child results 保留。

只有存在这份 frozen slice 记录时，baseline 才说明模型返回 bounded 观察/控制文本，Driver 尝试按该 path/contract 发布；缺文件写 Tool 本身不阻止模型返回该文本。记录不授予权限、不代表文件已写；没有真实 Receipt 不宣称发布成功，实际权限或 I/O 失败仍停止。无记录就不假定 Driver 发布；Guide 独立只读、intake 自己的 draft compiler 保留。没有修改输出契约、选定/实际 verifier、Schema、权限、Core 或 Runtime ownership。

Supply report ref、Tool 名和 capability identity 属于不同类型；字串差异自身不能推导新权限或失败。模型仍遵守实际执行 constraints，admission 继续由现有实现负责。Root 先前写入的 child 自身 Task/禁止再委派/初始空 child_results 说明原样保留。

这只是补齐既有运行时职责的上下文说明；没有新核心身份/路由/权限语义或 ADR 需求。源码与 baseline 字节改变，旧 Source/Attempt 不重绑；当前 metadata 始终是请求时 pending 状态，实际 Receipt 不反写为请求已完成。

## 静态验证与冻结

2026-10-08 00:39:05+08:00 四份 Python AST/内存 compile 通过；未执行 code object、项目 import 或测试。随后 Root 确认已检查 context/conditional baseline，准备最终全入口回归并要求冻结；收到该通知后没有修改产品/测试，只完成报告、source hash 复核与相对 Markdown 文件目标检查。

Root 回归尚未在本片段报告通过；不把 syntax、Root 目视检查或 pending metadata 视为行为成功。测试代码复用现有 joint fixture 和 role helper，没有复制 actual archive 或变更 fixture 来制造运行结果。

本代理未执行产品/tests/API/Tool、Key/账、预占、安装、Git、primary/global memory 写入。写范围只有上表四文件和本两报告。实际读范围：上述 owned 文件及 FrozenRoleBinding、Driver 当前发布/范围检查/实际 Tool identity 段、Host admission 必要段、primary PROJECT_MEMORY 当前导航。未读 actual archive、API response、private inputs 或其他代理内部产物。

## Root 下一步与 continuity

1. 运行全入口回归，确认 pending context 与实际 binding 对应、Guide/intake 不获 Driver 假定、缺实际权限/非法 output path 仍在原 Driver/Host 门槛拒绝，现有 child baseline 保留。
2. 在测试通过且 fresh source/body/budget 冻结后，进入新实际 Attempt；模型最终文本之后由 Driver 留真实 artifacts/Trace/Host/Receipt，保留 API/Tool 失败与未开始层的准确结论。
3. primary PROJECT_MEMORY 当前入口还停留于 Attempt11 摘要，Root 当前 Packet 已报告 A14，存在时间差；由 Root 更新共享连续性。本片段无写权，不将候选说成 merged/accepted。

Coordinator 建议条目：

> 2026-10-08 · CHAIN-DEV4-020：根据 Root A14 blocked 原因，局部候选在 executor 注入 actual binding 的 pending driver_output_publication(path/contract，permission_grant=false/publication_complete=false)，共享 baseline 只在存在该记录时说明 Driver 发布职责与真实 Receipt 条件；Guide/intake 无记录保持原路径。Supply ref/Tool/capability 类型说明不替代原 admission。输出契约/Schema/权限/Runtime/Core/selected/actual verifier 保留，Root child 修改保留。新增/扩充最小断言，四文件 AST/内存 compile 及交接 hash/link 静态检查；本代理未测试/API/Tool/Key/账/Git。收到 Root 冻结后只写报告，回归尚由 Root 准备。来源 chain-proof-002/OUTPUT_PUBLICATION_HANDOFF.md、OUTPUT_PUBLICATION_COMMUNICATIONS.md，source pins 见交接，本地候选未接受。Next Root 全入口检查、重冻 Source/body 后新 Attempt，A14 原 blocked/closed 不改判。
