# ENTRY-REVIEW-FIX：原R1–R4限定复查

Profile：targeted reviewer；required-Skills=[]。只读修复的executor/workflow/state、三个直接tests、control/HANDOFF_FIX及原审查报告；只写本文件。没有改原报告、Driver、代码或他人工件，没有API/生产Tool/Key/真实账/安装/commit/push/再委派。原 [RUNTIME_REVIEW](RUNTIME_REVIEW.md) SHA256保持 `bacd275a44a689ee3e7be857b0906c438cce2ededed38d0f8ffe04aed2f26db0`。

**最终限定结论：原R1–R4均已修复并复查，未发现这四项范围内仍未闭合的实质缺口。** 第一次独立19PASS保留；其中R2异常分支经本组反例揭示、Root再补守卫后，本组独立Executor4/4 PASS（10.140s）。workflow/state源码与其第一次通过时的hash保持相同；原审查报告保持原bytes。本结论只对应本文末列exact source/test hashes及离线范围，不表示live、科研接受或新增M12/硬中断资格。

## 第一次限定复查

| 原项 | 已核源码与证据 | 结果 |
|---|---|---|
| R1 Session limits参数 | [executor.py](../../../../../src/research_workbench/entry/executor.py):80–83改用max_model_turns，补max_tool_result_chars=1；真正FrozenRoleExecutor→Driver→Session→Host→receipt→Workflow离线joint test实跑 | 已修复 |
| R2 attempted/unknown账 | executor:104–118从Host provider_invocations读取actual attempts；attempted1/Session received0保留usage None，joint test证明model_calls1/held228、无retry | 主要分支已修；driver-exception未知零占位分支尚未闭合，见下 |
| R3末轮Task预算 | [workflow.py](../../../../../src/research_workbench/entry/workflow.py):303–321在parse_control前复检本次output cap、node累计turns/output和node elapsed，再检Run deadline，actual usage先留档 | 已修复 |
| R4 state消费字段 | [state.py](../../../../../src/research_workbench/entry/state.py):46–55 canonical比对Result全部报告字段，report pin独立捕获；后续构造从report读取而非可变Result。state11类篡改反例和发布/权限/hash回归实跑 | 已修复 |

这不是新的整体架构/科学/live评价。Root报告全新增entry63 PASS/85.197s、control workflow13/state3 PASS；本组独立执行了下列19项限定测试，没有重复全入口矩阵。

## 第一次测试结果

三命令使用Root现有Python环境、`-I -m unittest discover -s tests -t . -p test_entry_<name>.py -v`；互相独立TemporaryDirectory，无安装操作：

- executor：3/3 PASS，11.784s。actual联合调用/receipt、actual发送失败attempt1而received0/unknown hold228、exact Task substitution零Provider dispatch。
- workflow：13/13 PASS，18.548s。包含原output10/actual15被safe-paused且known35保留；Task time10/actual20、Run60被Task deadline阻断；node turn超额；旧动态children/结果消费和跨freshSession预算回归。
- state：3/3 PASS，16.371s。参数化Result字段篡改覆盖11类（含原next_actions反例），无输出文件；原report bytes不改；真实前后checkpoint/no overwrite/hash/scope回归保留。

三个suite exit0。本次联合读有工具截断，随后定向有行号重读workflow290–330、state40–63、executor99–128，必要源码未以截断内容替代。

## 原R2尚存的异常分支（已告知Root）

第一次复查executor:104–116只校验Host attempted是非负int，再对attempted==0直接写input/output0。此前已读Host的driver-exception返回事实不完整的零占位；这不是可以确定未发送的preflight zero。原R2明确要求不能从session=None/fact-incomplete推定零调用零usage，这条还缺守卫。

已执行只mock返回值的有界adapter消费者反例：将 `execute_role_slice` 返回设为 `execution_phase='driver-exception'`、`actual_facts.complete=False`、`capture_gaps=['driver-exception']`、placeholder `provider_invocations=0`、session=None、receipt=None。使用实际FrozenRoleExecutor及既有joint fixture运行workflow。观察结果：

```json
{"status":"safe-paused","model_calls":0,"held_tokens":0,"observation":{"model_calls":0,"input_tokens":0,"output_tokens":0},"summary":"role execution did not complete; retain its failure and stop"}
```

这是显式offline mock消费者反例，假pin路径标作not-published，仅验证异常事实映射；没有真实Provider发送、伪造生产closeout、state提交或扩写test文件。必要补正：不能证明zero dispatch的driver-exception/fact-incomplete+无Session分支抛给workflow unknown路径保留reservation；已知attempted1/received0保持actual count与None；确认preflight zero继续0。补正状态若有后续证据，记录于本文件后续核验段，不能用前面的19PASS覆盖此残余。

## 第一次可复核hash

| 文件 | SHA256 |
|---|---|
| src/research_workbench/entry/executor.py | d601d586f507041c99b654fcda9359cefd5851a130ee623ccd1b39c25f737ab7 |
| src/research_workbench/entry/workflow.py | d2d1f64971da72df808d084274156a70b0d640a572467e77f99f913c38979c92 |
| src/research_workbench/entry/state.py | 15faeba426aa7d701918c3a8243332c51dc082afafdeecf64ab290439233b262 |
| tests/test_entry_executor.py | e4b99d8bb7fdff2478b51199a001e4ed4da95783fb08bc0cc879b3b16ba69f56 |
| tests/test_entry_workflow.py | e6833e3118c3fd736da44afda1f81149472b5e11c05d415eb7bfdd98e72e2288 |
| tests/test_entry_state.py | 8d5f6b68658290f96dd4eaa139979bab821e88b2ee97d763b9bd0380b1d992f4 |
| control/HANDOFF_FIX.md | 31c227d97d5a352244cc88433bd544ba868f7b1f8b0aee695c831eed41589bdf |

## 可见通信原文

Root指派：

> ENTRY-REVIEW-FIX：只复查原R1–R4，预算8分钟2轮；Profile targeted reviewer，required Skills=[]，只读修复的entry/{executor,workflow,state}.py、test_entry_{executor,workflow,state}.py、control/HANDOFF_FIX.md和原报告，独占新 review/FIX_VERIFICATION.md。不改原审查报告、代码、其他工件，不API/Tool/Key/安装/commit/push。Root真正FrozenRoleExecutor joint3PASS（正确limits/Host attempted1、Session received0但unknown hold228）；全新增entry63PASS85.197s，control独立workflow13/state3PASS。请用限定反例/测试核原四点均被修；保留具体未闭合项，没有则明确已复查范围/hash/结果。不要额外扩大架构/科研矩阵。留可见指派/结果后停止。

发Root（原R2 residual）：

> ENTRY-REVIEW-FIX源码R1、R3、R4已见明确修正，当前R2还留原报告已指明的driver-exception分支：executor.py facts读取后只验证attempted是非负int，随后attempted==0直接把input/output置0；但Host driver-exception用不完整_zero_facts(provider_invocations=0,complete=False)占位，不代表确定零发送。session=None+execution_phase=driver-exception仍映射RoleObservation failed,calls0,tokens0，workflow.account会跳过hold。建议明确检测driver-exception或不能证明零发送的fact-incomplete/无Session分支并raise给workflow unknown hold；已知attempted1/received0现有joint反例正确。正在做限定复核，不扩大R1–R4。

发Root（独立测试和反例）：

> 限定19测试实跑：executor3 PASS11.784s/workflow13 PASS18.548s/state3 PASS16.371s。R2残余已用只mock不完整Host返回的counterexample确认：execution_phase=driver-exception、complete=false、placeholder invocations0、session=None =>workflow safe-paused但model_calls0/held_tokens0、tokens0；这不是已知preflight零调用，需unknown hold。其余原R1/R3/R4已由源码+反例测试闭合。尚在8分钟budget；你补这条guard后我可只重跑executor相关复查，报告会明确初次19PASS不覆盖该异常分支。

Root补正指派：

> R2残余已补 executor：attempted==0 且 facts.complete is not True 即raise，由workflow unknown hold保留；已补test_incomplete_host_zero_placeholders_preserve_unknown_reservation（不完整Host占位stub），executor最终4PASS8.566s。请仅核该原缺口并executor复测，更新FIX_VERIFICATION实际范围/结论/hash后停止。之前19PASS未覆盖残余原样记保留。

## 第二次限定复查：R2剩余分支闭合

定向重读最终executor `104–122`、[test_entry_executor.py](../../../../../tests/test_entry_executor.py) `107–118`。新增 `attempted == 0 and facts.get('complete') is not True` 时raise明确错误，解释Host不完整零占位不能证明zero outbound；由workflow已有executor-exception分支保留原reservation。attempted1/received0依旧保持actual1+usage None；fact-complete的确定zero仍0。

本组执行 `python -I -m unittest discover -s tests -t . -p test_entry_executor.py -v`，最终4/4 PASS、10.140s、exit0，四项逐项ok：exact frozen Task substitution、failed actual send attempt1/received0/hold228、incomplete Host zero placeholders（safe-paused、hold228、无虚构零usage observation且保留不完整result）、actual positive joint Role/Session/Host/receipt/Workflow/checkpoint路径。该新增counterexample仍明确offline stub；没有把stub当真实Provider发送或完整closeout。

最终源码/test定位：

| 文件 | 最终SHA256 |
|---|---|
| src/research_workbench/entry/executor.py | 6f1924bbef590df87b3f7539e2e30c3c7f7deafb3b739fd3b9302682e03d7987 |
| tests/test_entry_executor.py | 143e356977fea48b058dbed42c31ea1ea8c5c3c4cb8446ed654792829588809c |
| src/research_workbench/entry/workflow.py | d2d1f64971da72df808d084274156a70b0d640a572467e77f99f913c38979c92 |
| src/research_workbench/entry/state.py | 15faeba426aa7d701918c3a8243332c51dc082afafdeecf64ab290439233b262 |
| tests/test_entry_workflow.py | e6833e3118c3fd736da44afda1f81149472b5e11c05d415eb7bfdd98e72e2288 |
| tests/test_entry_state.py | 8d5f6b68658290f96dd4eaa139979bab821e88b2ee97d763b9bd0380b1d992f4 |

两轮仅原R1–R4及其必要负例/回归；没有追加全仓或科研矩阵，没有改任何产品/test/原报告文件。最终交付相对Markdown链接做存在性检查，文件SHA由最终Compact给Root保留。本组交付后停止；Root负责剩余集成/PR记录和人类审查，不把本限定验证替代具名authority。
