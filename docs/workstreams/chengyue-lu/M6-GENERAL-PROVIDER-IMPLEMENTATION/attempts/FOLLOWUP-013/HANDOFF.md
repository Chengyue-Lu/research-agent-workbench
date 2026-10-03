# FOLLOWUP-013 交接

PR128 审核指出的 P2 已修复：bound 1.1 冷读和发布共同核对当前 Attempt 实际 token 用量与持久
`reported_usage`，并从全部历史完整回执重新计算 known input/output/total。缓存、推理用量保持子集。
删除已知回执或把未知输出改为零不能制造一致报告；writer 在拒绝时不创建输出。

正常 partial、未结算写入失败和最终 accounting 不可得仍保留原观察事实，未知用量继续预占并停止。
当前 durable contract 不提供 verified reconciliation；旧 1.0 继续原结构回放。
内部一致性不认证嵌入账本的外部真实性，也不授予实际运行资格。

新增回归 13/13、已有相关回归 79/79 通过；完整命令、字节身份和原失败见 [CHECKS](CHECKS.md)。
CI 组件登记新测试以及共享 binding/reporting fixture 的直接消费者，避免未来变更漏选。
用户授权修复后合并 PR128；新 head 仍须通过必需检查和实际远端合并条件。

M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE 保持，Task 定义及具名验收状态没有变化。
合并后先重建、冻结新产品安装版与 Windows/helper/config 闭包，再修复联合启动的具体故障并验证。
旧 source 的 Windows synthetic PASS 不被转移到新 source。实际 Flash 的时间、预算、失败留存及
no-retry/fallback 约束继续生效；SDK 评估不增加本次测试的新门槛。
