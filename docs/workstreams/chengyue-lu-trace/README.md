# 路诚钺 Agent Trace 基线分支计划

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 分支：`agent/m3-008-trace-baseline`
- 基线：2026-08-19 最新 `main`
- 状态：M3-008 实现与本地验收
- 目标节点：`M3-008 Provider-neutral Trace Baseline`

本目录只描述路诚钺负责的 Trace 语义、确定性检查和 Mode/Skill 评估前置，不建立 API/Adapter
执行计划。逐项状态仍以 [`docs/TASKS.md`](../../TASKS.md) 为准。

## 1. 本节点交付

1. 冻结 `TRACE.yaml` Envelope、`INDEX.yaml` 和 `events.jsonl` 的 `0.1.0` Schema；
2. 实现 `rwb trace validate`，检查身份、顺序、哈希、actor owner、消息收发、读取/写入/Tool/
   外部动作边界、捕获声明、瞬时结果和过程文件 revision；
3. 提供一个不调用模型的手工 H1 fixture；
4. 用反例测试固定“记录存在但不可信”的失败条件；
5. 更新开发入口、使用指南、模块文档、任务表和 Changelog。

## 2. 明确边界

- 不实现 Provider SDK、认证、HTTP transport、模型选择、session loop 或 Adapter；
- 不对真实运行做 API/live conformance，不读取凭据；
- 不保存或推断隐藏 Chain-of-Thought；
- 不把 Trace 完整度、事件数量或校验通过当作科研正确性；
- 不启动 M7-005/006/014 的真实比较，也不为零 active Skill 补包；
- 共享 Schema 若被执行端消费后需要修改，必须先说明迁移与双方 owner。

## 3. 验收与停止点

本节点只有在正向 fixture、反例测试、全仓库回归、示例/Registry 校验和 `git diff --check`
均通过时完成。完成后停止当前分支；下一 Task 由人类选择，默认建议先做 M7-006 的极小样本
H0/H1/H2 成本对照，因为它能直接检验 Trace/Handoff 是否制造了超过任务价值的协调负担。

若执行端尚不能输出完整 Trace，允许生成显式 `capture-gap`，但不得用手工补全冒充自动捕获，
也不得据此宣称某种 Agent/Skill 机制成本更低。
