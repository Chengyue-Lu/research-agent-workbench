# ENTRY-JOINT-CONTROL 完整离线接合正例

2026-10-07；Profile=bounded integration tester；required-Skills=[]。实际链路通过，无 core/validator/资格桥接修改。隔离候选结果，不是正式接受或真实 API 验证。

## 测试什么、给了什么、得到了什么

[test_entry_control_chain.py](../../../../../tests/test_entry_control_chain.py) 是一个跨模块正例，只定义本身 TestCase，不 import 其他 TestCase。

输入是既有明确 offline fixture：人类 Protocol/Task ceiling、模型控制提案 JSON、Method/Requirement、typed local-conformance 文件及 Supply，另有明确 Profile/两 policy/ExecutionBinding 和独立 offline Provider 元数据。没有真实 API、Key 或生产 Tool。typed evidence 的 `live` class 是既有离线 fixture 的契约输入；本测试未建立真实来源/live qualification。

| 接入模块 | 这例实际操作 | 下游消费的实际输出及断言 |
| --- | --- | --- |
| 前端控制编译/持久化 | compile_control_draft 在人类 ceiling 下验证提案，再 persist_control_draft | 实际返回 project-protocol.json/task.json/method.json/requirement-1.json FileReferences；Method task hash 精确等于已发布 Task bytes；draft仍为draft，unknown保留 |
| Capability selection | trusted callback重新读 typed 原件，核 hash、evidenceID、implementation/version、capability、evidence class/kind；然后 freeze_capability_selection | 实际生成 Resolution/Snapshot pins，status=satisfied，callback一次；不使用旧fixture Resolution/Snapshot进入下游 |
| Bundle/View freeze | 将前端和 selection 实际返回 pins 重绑7-document、11-import manifest，并调用 freeze_execution_inputs | 新 Bundle/View pins；View.task_ref 指向实际 intake Task；entrypoint指向实际新 Snapshot；闭合只有 research-contract-check slice，task_completion=false |
| 主角色、Session、Host、Trace、Receipt | FrozenRoleExecutor 的 binding_factory 对实际 workflow Task 精确比对；使用新 Bundle/View pins进入 execute_role_slice/SessionExecutionDriver/execute_frozen_view | offline Provider.generate实际调用一次；1main/0child；Session模型回合1、Host completed、Trace和Receipt产出；独立 validate_generic_execution_receipt 再验证通过 |
| workflow消费 | 解析真实 offline响应的 complete/零delegations，汇集实际端口usage与Host/Trace/Receipt refs | stage-completed；reported known_tokens=38、held_tokens=0、model_calls=1；可读 REPORT.md存在；task_completion和human_acceptance均false |
| checkpoint | 使用真实 intake Protocol pin及实际 workflow result发布MainState | accepted_decisions=[]；machine_state_refs含实际Receipt；保留Protocol身份及下一步人类审阅 |
| Guide读取 | build_guide_request只读取这个确切checkpoint | 只有该MainState在approved_inputs，payload含人类审阅下一步；tools为空；文件bytes前后不变；没有发送Guide Provider请求 |

主角色返回明文摘要：“The bounded contract-check execution slice produced retained Host and Trace facts.”限制明确 offline scripted Provider，下一步为人类审阅该切片。usage数字是 fixture端口实际返回的报告值，本例不推算真实 token计费。

## 验证与限制

执行命令：`<worktree-root>/.rwb/entry-venv/Scripts/python.exe -m unittest tests.test_entry_control_chain -v`。首测1/1通过，8.578秒。13:48:54 UTC开始，13:50:35 UTC首测结束；预算10分钟/2轮。没有先失败再放宽契约，没有 monkeypatch validator、伪造 Receipt pass 或旧view替代新producer输出。

这例证明上述模块以真实生产接口和实际返回文件引用接合、冻结/执行/消费/状态发布可达；输入模型提案和 Provider回答仍是显式 offline脚本。未验证自然需求改写质量、intake模型调用、Guide回答质量、付费API、真实来源conformance、生产Tool、科学正确性、整个Task capability闭合或Human Gate接受。dynamic 0..N由其他测试覆盖，本例仅零child。临时工件由TemporaryDirectory管理，源码可重跑；本报告不是生产Attempt归档。

## 交付与Root下一步

| 文件 | SHA-256 |
| --- | --- |
| tests/test_entry_control_chain.py | ca26e5df83c2fe59190d640eac4d136046e564641db20274eba7f1affbe44930 |

通信、读集及调用事实见 [COMMUNICATIONS](COMMUNICATIONS.md)。只新增本测试与本Handoff，追加本通信；未修改旧binding、core、Schema/Registry或现有fixture。Root可将此正例纳入整体回归/PR；真实API及来源资格仍由Root按现有授权与资格边界单窗口推进。

PROJECT_MEMORY own-row建议：`2026-10-07 AUDIT-RWB-ENTRY-001 ENTRY-JOINT-CONTROL：已补前端compile/persist→capability freeze→explicit Bundle/View freeze→FrozenRoleExecutor Session/Host/Trace/Receipt→workflow→checkpoint/Guide request完整离线正例，首测1/1通过；实际producer pins贯穿下游，Task完成/Human接受=false。来源binding/HANDOFF_JOINT与tests/test_entry_control_chain.py；未验证live/API/Guide回答/全Task闭合。下一步Root总体回归与真实资格接入。`
