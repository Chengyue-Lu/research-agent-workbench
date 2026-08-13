# 恢复点与下一步规划

状态：API-first 方向已确认，`K-API-1` 已到达

日期：2026-08-13

## 1. 当前架构判断

系统的优势不是在一个长窗口内反复压缩，而是让主 Agent 只维护大局、决定、风险、工件索引和下一 Atomic Work Unit；每个子任务在独立上下文中执行，结束前把不可丢失内容固化为正式工件与 Handoff。子会话可以关闭或压缩，项目方向不依赖其聊天历史。

执行优先级现调整为：

1. 文件式科研契约和连续性；
2. 纯 API fresh session，作为只依赖模型 API 的可移植基线；
3. Codex、OpenCode、Claude Code 等可选平台 Adapter 或人工新窗口；
4. 只有真实失败证明需要时，才评估更重的运行时。

模型选择保持很小：`primary` 主模型、`worker` 平价模型、按需 `specialist`。模型槽只做显式映射，不建设价格数据库、评分 Router 或自动 fallback。

## 2. 已到达的关键节点：K-API-1

已经具备：

- `explicit-slot-only` Model Pool，默认不读取环境，不自动选择模型；
- Profile 可以声明 `default_slot`，coordinator 使用 `primary`，首批子任务使用 `worker`；
- provider-neutral fresh API session runner；
- 模型轮次、工具调用、单轮并行、工具结果大小、单轮输出、累计 token/可得成本和 wall time 边界；
- data policy、模型/能力缺口在调用前阻断；
- 工具越界、不可测硬预算和超预算进入失败或 `safe-paused`；
- 不使用 Provider response ID 延续权威状态，不跨 Provider/Model 静默 fallback。

该节点仅证明执行内核，不证明真实科研价值，也尚未把 Task 自动转换为 API 请求和正式结果文件。

## 3. 当前唯一构建目标：K-API-2

终点定义：一个已解析 evidence Task 能够进入全新的纯 API 子会话，并在完成或安全暂停后形成完整文件闭环；删除临时 transcript 后，新主会话只凭文件恢复到唯一正确的下一动作。

需要完成的最小链路：

```text
Project Protocol
  + Task Packet
  + Agent Profile
  + Skill Assignment
  + explicit worker slot
        ↓ compile
minimal system/developer instructions
  + bounded input references
  + client-tool allowlist
        ↓ fresh API session
Attempt + Research Artifacts
  + Transfer Manifest
  + Handoff
  + Context Snapshot
  + Execution Receipt
        ↓ validate and close out
Main State → new main session resume-check
```

实施顺序：

1. 定义 Task/Assignment → `ModelRequest` 的最小编译边界，禁止注入主 Agent 全历史和未选 Skill；
2. 把 Task budget、有效权限、工具 allowlist、模型槽和 Project data boundary 合并为一次 session limits；
3. 先用 fake Provider 跑通完成、工具失败、预算暂停和 stale input 四条离线路径；
4. 原子写入 Attempt、Handoff、Transfer Manifest/Audit、Context Snapshot、Execution Receipt 与 Main State；
5. 删除内存 transcript，从新主会话执行 `resume-check`，确认下一动作不重复已完成工作；
6. 仅在上述离线闭环通过后，在真实 Windows 用户上下文对实际启用的 `worker` 槽执行一次受限 evidence 调用。

达到第 5 步即到达 `K-API-2` 并暂停评审。第 6 步是随后真实环境确认，不是本节点的强制条件。

## 4. 本节点明确不做

- 不选择或实现 OpenCode、Codex、Claude Code 的新 Runtime Adapter；
- 不要求 OpenAI、Anthropic、Gemini 三家全部启用，只验证实际选择的模型槽；
- 不实现自动模型排名、价格抓取、LLM Router 或静默升级；
- 不实现 GUI、服务端、数据库、消息总线或长期 Supervisor；
- 不扩展 streaming、多模态或 server tools；
- 不安装 ZIP 候选 Skill；
- 不把离线闭环标为科研正确或可公开发布。

## 5. K-API-2 之后的候选顺序

只有节点评审通过才继续：

1. 对启用的 `primary` 与 `worker` 槽做真实 Windows conformance；
2. 用同一 evidence Task 比较轻量单 Agent 与主/子隔离执行的上下文、质量和成本；
3. 运行 simulation Task，验证不同 Skill 和工具边界；
4. 出现真实图像/文件需求时增加一个 specialist 槽及相应 capability；
5. 团队明确选择某个平台后，再实现该平台的薄 Runtime Adapter 并与 API 基线对照。

## 6. 恢复入口

恢复工作时只需依次读取：

1. `README.md` 的当前边界；
2. `docs/TASKS.md` 的当前唯一关键路径；
3. `docs/decisions/0010-API-FIRST-ISOLATED-EXECUTION.md`；
4. `docs/implementation/PROVIDER_ADAPTER_PLAN.md`；
5. `examples/task-evidence.yaml`、对应 Profile、Skill Assignment 和 Main State；
6. `CHANGELOG.md` 最新条目。

不要从旧聊天记录或某个平台会话重建项目状态。
