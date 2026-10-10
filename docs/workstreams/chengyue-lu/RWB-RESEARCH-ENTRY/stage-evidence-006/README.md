# 执行阶段证据接合

PR140实施切片；exact Task为M2-009与M11-008，状态仍由[TASKS](../../../../TASKS.md)维护。前一轮已验证的planning/正式Handoff链见[原验收记录](../planning-handoff-004/VERIFICATION.md)。本轮先合并的[PR142](https://github.com/Chengyue-Lu/research-agent-workbench/pull/142)仅闭合M0-008治理，不替代本切片验收。

## 解决的问题

实际执行先生成main观察，再执行child、消费正式Handoff，最后写Receipt与checkpoint。模型输出时的“尚未返回”或“等待Driver发布”可能与后续已发生的事实同时保留。扁平限制列表缺少阶段来源，Guide容易把早期观察当作当前执行缺失。

本切片在应用层固定workflow事件日志，生成逐阶段证据，并通过MainState已有machine/index refs接合。每条限制仍保留；新证据区分已派发、已返回、已结构消费和未知，不根据文字猜测风险已关闭。MainState Core Schema和人类接受边界保持。

## Producer 与消费者

| 桥接 | 输入 | 输出和直接消费者 |
| --- | --- | --- |
| workflow阶段来源 | 实际role事件、context/child消费、observations与闭合usage | 最后事件后计算journal pin，写入应用层workflow report；供阶段producer重读 |
| 阶段证据发布 | exact report、journal、actual final Handoff及独立预期事实 | 版本化阶段证据工件；checkpoint显式选择写出并将其pin加入MainState |
| Guide前置核验 | 获准MainState、stage snapshot与单独明确授权的verification refs | 重算阶段派生字段，返回实际source检查范围；缺授权/旧缺pin保留未检查或未知 |
| 模型解释 | 获准快照与前置检查结论 | 只读回答；原始verification文档不进入模型payload，无自动追读、状态写入或main通知 |

检查阶段source记录及派生一致性不等同完整Receipt replay、产物内容质量、模型理解、科学或Human接受。完整Handoff验证仍由producer/checkpoint的原消费者完成；Guide不因可见机器refs而自动取得读取授权。

`publish_workflow_stage_evidence` 使用 actual `result`、外部 `handoff_ref`、目标文件及写域发布 sidecar；`publish_workflow_checkpoint` 通过可选 `stage_evidence_output` 接入。Guide 的 `build_guide_request` / `ask_guide` 增加可选 `stage_evidence_ref` 与 `verification_refs`，stage 的 exact pin 必须同时列在 `approved_refs` 中。核验函数 `assess_workflow_stage_evidence` 返回 checked、not-checked 或 unknown 和明确检查范围；Guide 仅发送七项核验元数据，完整阶段事实在获准快照中，不重复原始结果。

实际结果见[验收记录](VERIFICATION.md)。[Task Packet](TASK_PACKET.md)界定读写、协作及测试范围；旧无 journal pin 的报告保留 unknown，不借新提交改写旧 Attempt。
