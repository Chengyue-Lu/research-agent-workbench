# 主子结果消费的预算桥接

M2-009 implementation slice / M11-008 direct consumer；新分支基于 PR140 的 `766bf45`。原 PR140 未合并，本候选不等待其 review 开展实现；合并和接受仍分别由人类决定。

main 已经提出 child Tasks，不代表这些工作能全部执行并交回。原先逐次调用才核预算，可能执行了 child，最后发现父 Agent 没有接收结果的剩余调用。本轮把已提出的整组工作及父消费会话一起核验，并在嵌套过程中保留祖先和后续同级任务的预算。没有子任务时沿用原路径；子数量继续由 main 决定。

只为已经明确的首个 child Session 与 fresh parent Session 预留容量，使用各自的现有 Session 上限。未来是否继续委派仍由后续实际结果决定。规划预留不会成为付费事实或 unknown hold；发生调用后才记 actual，失败或未知保留原事实。

本轮范围与正反消费要求见 [Task Packet](TASK_PACKET.md)。实际测试模块、输入、输出及未验证项见 [验收记录](VERIFICATION.md)。M1-010/M2-009/M11-008 保持 IN_PROGRESS，后续材料接入、研究对象消费者和角色/Skill 工程仍按原 Task 推进。
