# ENTRY-FIX-01 Compact Handoff

2026-10-07；Agent Profile=bounded implementation worker；required-Skills=[]；Human owner路诚钺。隔离分支 `codex/research-entry-integration`，本次只修改 workflow/state 及两个对应tests；Root修改executor/jointtests，未碰这些文件。新增通信附在 [COMMUNICATIONS](COMMUNICATIONS.md)。无API/生产Tool/Key/账/安装/commit/push。

- workflow 在保留实际observation与usage之后、parse_control之前复检 dispatched output cap、node累计output/turns、node真实elapsed及Run全局deadline。Task额度10而actual15、Task时限10而actual20均safe-paused；actual input20/output15、known35和真实调用数仍留在report，不重写为预算数字。
- state canonical比较 `WorkflowResult` 所有已报告字段，只有report_ref以已有same-byte SHA pin单独验证；缺字段或替换next_actions/limitations/observations/summary/disposition/counters/unstarted/authority flags均拒绝。构造checkpoint只取固定报告字段，后续引用与publication复验使用初次捕获的不可变report pin。
- Root追加的plain directory scope兼容按既有 `validation/relationships.py:208–240` 的目录anchor/组件语义实现；plain与`/**`均能覆盖真实子路径，`work/task-other`不能进入`work/task`。未扩展任意glob、绝对路径或上级目录，未改core Schema/权限词汇。

限定测试最终：workflow13 PASS（15.654s），state3 PASS（13.991s），共16；state新增一个参数化测试含11类结果篡改反例。保留原正向0/1/3 children、actual结果消费、首次/后续checkpoint、拒覆盖/漂移等回归；额外确认node turn overrun仍保留usage。首次workflow12 PASS（11.346s）为scope补正前中间版本，最终13 PASS才对应此交付。全程TemporaryDirectory/ScriptedExecutor，未声明live验证。

命令：`& ./.rwb/entry-venv/Scripts/python.exe -I -m unittest discover -s tests -t . -p test_entry_workflow.py -v`；state同命令替换pattern为`test_entry_state.py`。四owned文件的`git diff --check` exit0。

| 文件 | SHA256 |
|---|---|
| src/research_workbench/entry/workflow.py | D2D1F64971DA72DF808D084274156A70B0D640A572467E77F99F913C38979C92 |
| src/research_workbench/entry/state.py | 15FAEBA426AA7D701918C3A8243332C51DC082AFAFDEECF64AB290439233B262 |
| tests/test_entry_workflow.py | E6833E3118C3FD736DA44AFDA1F81149472B5E11C05D415EB7BFDD98E72E2288 |
| tests/test_entry_state.py | 8D5F6B68658290F96DD4EAA139979BAB821E88B2EE97D763B9BD0380B1D992F4 |

Next：Root完成executor/joint adapter验证与全入口集成、PR记录。这里仍是既有应用入口的预算/文件一致性修复，不执行Human acceptance或M12恢复；不声明跨文件CAS/硬中断已超时的Provider调用。本子Task回hash后停止。
