# ADR-0010：纯 API 隔离执行成为可移植基线

状态：Accepted

日期：2026-08-13

2026-08-14 维护说明：本 ADR 的架构决定继续有效；`K-API-2` 及 API 实现/测试由黄毅负责，不再是路诚钺当前 Mode–Skill 节点。

2026-08-20 维护说明：路诚钺当前节点已变为 Method/Core formalization。执行层未来消费冻结的
Method Resolution 与 Capability Snapshot，但本 ADR 的 API-first isolated baseline 不因此失效。

## 背景

ADR-0001 在项目早期选择“原生 Agent 运行时优先”，目的是避免重新实现 Codex、Claude Code 等平台已经提供的线程、子 Agent、权限和 Skill 能力。后续实现证明，科研契约、文件式连续性和 Provider-neutral Model Port 可以独立于这些平台存在；同时，项目未来使用的平台尚未确定，若继续把真实垂直切片绑定到 Codex 或 OpenCode，会使平台选择提前成为核心依赖。

实际可长期依赖的最低执行条件不是某个平台，而是：存在一个可调用的模型 API、一次全新隔离上下文、明确的 Task/Skill/权限/预算，以及执行后可写入的正式工件。该边界也更适合验证跨 Provider 行为和控制子任务上下文。

模型选择的实际规模预计很小：一个高能力主模型、一个或少数平价工作模型，以及按图像、文件等独特能力设置的少量专用模型。为此建设价格数据库、评分 Router 或自动模型竞赛，收益不足且会增加漂移与校核成本。

## 决策

1. 将“文件契约 + 纯 API 隔离会话”作为首要可移植执行基线。每个子任务创建新的 API 会话，只加载 Task Packet、冻结的 Skill Assignment、必要输入引用、工具定义和输出契约。
2. 主 Agent 默认使用显式 `primary` 模型槽；普通子任务默认由 Profile 指向 `worker` 槽；需要多模态等独特能力时，由 Task 或人类显式指定一个 `specialist` 槽。
3. 模型池只支持 `explicit-slot-only`：不打分、不自动排名、不静默降级、不跨 Provider fallback。一个槽固定一个 Provider Adapter、一个由本地环境提供的模型 ID、能力声明和可选 reasoning effort。
4. API 会话执行器必须限制模型轮次、工具调用数、单轮并行调用数、工具副作用类别、工具结果大小、单轮输出、累计 token/可得成本和 wall time。硬预算不可测时停止或 `safe-paused`，不得假装仍受控。
5. Provider response/conversation ID 不作为权威状态。工具循环可以在一次 Attempt 内重放规范消息，但会话结束后只保留正式工件、Handoff、Context Snapshot 和 Execution Receipt。
6. Codex、OpenCode、Claude Code 等保留为可选 Runtime Adapter、交互外壳或人工兜底入口。它们可以承载同一 Task，但不得成为科研内核、Skill Registry、连续性或模型选择的所有者。
7. 若平台路径执行，仍必须固定同一模型槽并在 Receipt 中核对实际 Provider/Model，防止平台继承或二次路由。
8. 本 ADR 取代 ADR-0001 中“真实执行首先依赖原生平台”的优先级；ADR-0001 关于不建设通用 Supervisor、固定 DAG 和会话数据库的限制继续有效。

## 当前关键节点

`K-API-1` 定义为：

- 显式模型池能够在不隐式读取环境的情况下验证，并只按调用者给出的槽位绑定一个模型；
- provider-neutral API runner 能在全新上下文中完成受限文本/客户端工具循环；
- 模型、数据政策或预算不满足时在本地阻断或安全暂停；
- 离线测试证明没有自动 fallback、工具越界和工具结果静默截断。

该节点只是执行缝合点，不是产品交付点。它不要求真实科研 Task、GUI、平台 Adapter 或公开发布。

## 下一关键节点

`K-API-2` 是一次完整的 Task-to-API 文件闭环：将一个已解析 Task 和 Skill Assignment 编译为隔离 API 子会话，产生 Attempt、研究工件、Transfer Manifest、Handoff、Execution Receipt 和 Main State；删除临时会话后，新主会话只凭文件恢复到正确下一动作。真实 API 调用只在已授权的 Windows 用户上下文执行。

## 后果

优点：执行基线不绑定平台；上下文隔离可直接测试；模型成本策略保持简单；平台可以后来比较而不是预先决定。

代价：Workbench 必须维护一个小型有界工具循环和工件桥接；不同 Provider 的工具与停止语义仍需薄 Adapter；API 方式无法自动获得平台 UI、人工审批和会话导航能力。

## 不做

- 不建设通用 Supervisor、长期会话服务、消息总线或数据库记忆；
- 不建立实时价格抓取、模型评分器或 LLM Router；
- 不因为 OpenAI-compatible 就跳过 Provider 合同与 live conformance；
- 不要求一次接入所有平台或所有模型；
- 不让低价模型的结果自动通过 Claim/Human Gate。
