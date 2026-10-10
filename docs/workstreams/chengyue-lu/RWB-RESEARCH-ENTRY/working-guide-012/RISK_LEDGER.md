# 工作 Guide 风险与未完成部分

| 风险/边界 | 本次处理 | 剩余条件 |
| --- | --- | --- |
| work 投影被误当新权限或 Runtime | 所有投影 boundaries 为 false；旧 Task/Profile/DataPolicy/output grant 先验证，新 Schema 明确 opt-in | Task/Policy/View/Host/Session 仍须独立版本迁移与完整 Gate |
| 来源字段或结果类别被当作接受 | reader 同批解析来源闭包；结果只核实际捕获文本与 exact Task pin，contract/scientific 未建立 | 正式 Handoff 继续走既有消费者，科学接受由真实证据及人类决定 |
| 空选择、未选来源和调用前漂移 | 显式空选择阻断旧 fallback；必要决定与反证必须实际捕获；Provider 协商后复验材料与结果 | 文件系统原子性不在此接口保证范围；新读取闭包不得靠可见 ref 自动扩大 |
| 取消或 Provider 错误被重跑掩盖 | 最终复验后的取消 sample 阻止派发；Provider 错误原样抛出、usage/unknown 保留、无自动重试 | 取消回调只报告取消；Adapter 的在途取消、超时语义仍按其真实能力核验 |
| 只读解释污染状态 | 工具列表为空，无 Trace/MainState/主会话写入器，原文件字节在消费后保持一致 | 新 Guide 不替代旧 MainState/stage 专用核验接口；后续状态解释需要明确输入合同 |
| 候选或离线工程证据被当作通用运行 | source/installed 身份、平台 skip、原 CI 失败均分别保留 | main/child/intake、新无额度 Runtime、实际 API 和科研净收益尚未由本切片证明 |

静态审查和实际结果见 [验证记录](VERIFICATION.md)。M1-010/M2-009/M11-008/M6-013 的整项完成不由此表推导。
