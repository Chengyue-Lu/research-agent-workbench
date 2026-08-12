# 架构参考与采用边界

日期：2026-08-13

## 官方平台能力

- [Codex Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)：支持专用子 Agent、不同模型/推理配置、原生线程和结果汇总；也明确提示子 Agent消耗更多 token，写密集并行会增加冲突。本项目据此采用“只在窄、独立、噪声密集任务上委派”。
- [Codex Build Skills](https://learn.chatgpt.com/docs/build-skills)：Skill 使用 `SKILL.md` 和可选 scripts/references，通过 name/description 发现并渐进披露。项目据此把 Skill 正文留给具体子 Agent，主 Agent只看 Registry 元数据。
- [OpenAI Agents SDK Handoffs](https://github.com/openai/openai-agents-python/blob/main/docs/handoffs.md)：结构化 handoff input、history filter 和上下文分离说明交接应有明确 Schema；本项目不因此立即引入 SDK。
- [OpenAI Agents SDK Tracing](https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md)：trace 可覆盖模型调用、工具、handoff 和 guardrail；本项目仅将其视为调试/成本观测，不视为科研证据。

## 开源科研与编排项目

- [STORM / Co-STORM](https://github.com/stanford-oval/storm)：多视角提问、知识整理、人机共同探索和动态 mind map 对长程信息探索有价值；但其定位主要是知识整理和报告生成，不能直接替代实验/推导/因果判断。
- [PaperQA2](https://github.com/Future-House/paper-qa)：带文内引用的科学文献 Agentic RAG 可作为 Evidence Skill/Tool Adapter 候选；不把检索答案直接当最终 Claim。
- [LangGraph human-in-the-loop](https://github.com/langchain-ai/langgraphjs/blob/main/docs/docs/agents/human-in-the-loop.md)：checkpoint 与 interrupt 适合需要持久暂停的工作流；首版先用文件 checkpoint，真实需求出现后再考虑图运行时。
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)：可作为未来编程式多 Agent Adapter 候选；旧 AutoGen 已进入维护模式，因此不将其作为新核心依赖。
- [DVC](https://github.com/treeverse/dvc)：数据、pipeline 和 experiment versioning 成熟，真实大文件场景出现时优先接入；首版不重造数据版本工具。

## 采用原则

参考项目提供“可借用的能力”，不提供本项目的科研正确性。任何依赖只有在真实案例中有消费者、能替换、且净收益超过集成成本时才进入实现。
