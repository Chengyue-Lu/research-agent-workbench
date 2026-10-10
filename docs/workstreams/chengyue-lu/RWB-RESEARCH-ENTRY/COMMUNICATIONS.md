# 协作与交付索引

本轮所有可见子任务指派、接口消息、重要错误及交付保存在各组COMMUNICATIONS/HANDOFF与review文件。这里保存Root协调索引，不记录隐藏推理、认证信息或科研原始材料。Agent交付表示限定候选与验证范围，不代签具名owner或Human决定。

## 两个新窗口

| 名称 | thread ID | 有界职责 / 输出 |
|---|---|---|
| RWB M12接合规划 | `01a1168d-0d4d-7000-bd71-85d57fbfbf46` / local | continuity-planning profile，required-Skills=[]，20分钟4轮；只写 [m12/PLAN](m12/PLAN.md)、[通信](m12/COMMUNICATIONS.md)，planning完成后停止 |
| RWB前端接合规划 | `01a1168d-35d4-7091-9969-ed532368eb51` / local | frontend-product/intake-planning profile，required-Skills=[]，20分钟4轮；只写 [frontend/PLAN](frontend/PLAN.md)、[通信](frontend/COMMUNICATIONS.md)，planning完成后停止 |

授权：用户明确要求同时开两个新窗口考虑M12和前端。共享输入、scope、输出、预算、停止与禁止项目动作见 [TASK_PACKET](TASK_PACKET.md)；两窗不开发、执行测试、读Key、运行API/生产Tool或写primary memory。原PR137仅是有明确pin的M12参考，不续改或接受它。

## 代码代理与后续任务

| Agent / 子Task | Ownership | 通信/交付 |
|---|---|---|
| control_modules_266 / ENTRY-A | entry/roles,intake,guide及其3个tests | [通信](control/COMMUNICATIONS.md)、[HANDOFF](control/HANDOFF.md)；18限定offline PASS |
| runtime_modules_267 / ENTRY-B | entry/driver及所属tests | [通信](runtime/COMMUNICATIONS.md)、[HANDOFF](runtime/HANDOFF.md)；9限定offline PASS |
| review_report_253 / ENTRY-C | entry/binding及所属tests | [通信](binding/COMMUNICATIONS.md)、[HANDOFF](binding/HANDOFF.md)；15限定offline PASS |
| runtime_modules_267 / ENTRY-REVIEW | 只读Root workflow/state/executor/直接tests，独占review原报告 | [RUNTIME_REVIEW](review/RUNTIME_REVIEW.md)；四项实质发现与实际反例已保留 |
| control_modules_266 / ENTRY-FIX-01 | workflow/state和两个直接tests；不碰Root executor/CLI | [HANDOFF_FIX](control/HANDOFF_FIX.md)；预算10分钟2轮，Task postcall预算、fixed-report一致性与plain anchor兼容，workflow13/state3 PASS |
| review_report_253 / ENTRY-JOINT-CONTROL | 只新建test_entry_control_chain及HANDOFF_JOINT，追加自身通信 | [HANDOFF_JOINT](binding/HANDOFF_JOINT.md)；10分钟2轮，实际producer pins贯穿下游，1 PASS |
| runtime_modules_267 / ENTRY-REVIEW-FIX | 只复查原R1～R4，独占修复验证报告 | 8分钟2轮；明确首次19PASS仍漏原R2 driver-exception零占位分支，Root补guard/反例，最后只复核该缺口 |

所有派发明确不是唯一参与者、互斥scope、required-Skills=[]、不撤销他人修改；0 paid/API/生产Tool/Key/账/安装/commit/push（Root单独管理安装与Git）。Role/Control/Driver/冻结组接口约束的Root来回原文由对应通信保留。Root追加的修复任务要求 actual观察先保留再拒绝；state消费值须与pin报告全部一致；完整control-chain测试要求实际新producer输出进入下游且不得以旧view或validator mock替代。

## 交付检查方法

已读本轮Task Packet及各Compact Handoff，使用 `handoff-integrity` 的范围/输出/锁定/限制核对原则。其 `check_handoff.py` 的输入是正式TaskPacket/HandoffPacket数据契约；本轮Task明确使用development Compact Markdown，未伪造正式Packet或Skill锁去套用该checker。对这些交付检查owned文件、公布SHA、relative引用、输出、测试与remaining；保留original findings和unknown。没有追加独立Human sampling来替代当前PR正式review。

最终代码/测试/文档hash见DELIVERY_MANIFEST。原始可见消息中的机器路径只在本地archive保留，公开文档采用仓库相对路径/checkout变量；定位归一化不改变接口、结果或限制。归一化前后hash与范围由manifest记录，不能把发布版SHA冒充原交付SHA。
