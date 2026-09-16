# H3 scope amendment — Trace path capture

2026-09-17。保留初始 TASK snapshot；实现过程中追加此范围说明。

四臂集成暴露出 Trace credential regex 将 `TASK-MR-ES-FROZEN-001` 的 `SK-…` 子串识别为
credential token，导致 Skill fact 的 project-relative creation event 被脱敏并被独立 closeout 拒绝。
基于用户对完成 H3 开发的授权，写入面补充 `src/research_workbench/observability/trace.py` 的
一处 token-boundary 修复及对应 `tests/test_agent_trace.py` 回归测试。真实独立 `sk-`/`SK-`
密钥、路径中的密钥与嵌套敏感值继续脱敏。测试和 review 需覆盖这一共享辅助函数。

此修复保持 Trace Schema、Skill fact 路径、Runtime ownership 与原有独立 replay 校验。
