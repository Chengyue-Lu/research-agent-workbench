# 模块 09：运行时与工具适配

## 1. 目标

将平台中立的 Project Protocol、Agent Profile、Skill Assignment、Task 和 Handoff 映射到具体 Agent 平台与科研工具。Adapter 只能执行映射，不能改变科研状态或批准 Gate。

## 2. Runtime Adapter 接口

```text
capabilities() -> RuntimeCapabilitySnapshot
resolve_agent(profile_ref) -> RuntimeAgentConfig
resolve_skills(skill_assignment) -> RuntimeSkillBinding
launch(resolved_task) -> RuntimeExecutionRef
collect(execution_ref) -> HandoffCandidate
cancel(execution_ref) -> CancellationResult
```

Adapter 必须暴露：

- 支持的 Agent、Skill、权限、工具和并发能力；
- 平台版本和配置快照；
- 哪些约束可由平台强制，哪些只能通过提示/验证；
- 原始会话标识与正式 Task/Attempt 的映射；
- 失败与取消语义。

## 3. Codex Adapter（首版）

映射建议：

| 平台中立对象 | Codex 表面 |
|---|---|
| Repo guidance | `AGENTS.md` |
| Agent Profile | `.codex/agents/<name>.toml` |
| Skill | `.agents/skills/<name>/SKILL.md` |
| Skill metadata | Registry manifest + Skill frontmatter |
| Skill Assignment | Task Prompt 显式调用 + lock 文件 |
| Task execution | 原生 subagent thread |
| Permission ceiling | custom agent config 与会话权限交集 |
| Handoff | 子 Agent返回 + 仓库工件 |
| Rollover | Main State + 新主线程/会话 |

官方能力允许项目级自定义 Agent 设置模型、推理、sandbox、MCP 和 Skill 配置；仓库级 Skill 通过渐进披露加载。首版利用这些能力，不包裹一个长期驻留的自建调度进程。

## 4. 其他 Runtime

Claude Code 等平台以后以独立 Adapter 接入。Canonical manifests 保持不变，Adapter 负责翻译对应的 Agent/Skill 配置与显式调用方式。

不得为了“跨平台统一”只保留所有平台的最小公分母。Adapter 应报告 capability gap；上层可以选择降级、换平台或请求人工决定。

## 5. Tool Adapter

Tool Adapter 提供数据或动作，Skill 提供工作流程：

- 文献：Zotero、Crossref、OpenAlex、PaperQA2；
- 数据/实验：DVC 或 MLflow（二选一起步）；
- 报告：Quarto/Jupyter；
- 推导：CAS/证明助手；
- 仿真/统计：项目已有 CLI 或 Python/R；
- 外部资料：Web Search、浏览器、受控 API。

首版不同时接入所有工具。只有首个案例需要且可替换的最小适配器进入实现。

## 6. 权限模型

有效权限是以下交集：

```text
Runtime session permission
∩ Agent Profile permission ceiling
∩ Task Packet permission
∩ Skill permission ceiling
∩ Project data boundary
```

任一层缺失不按最宽权限推断。Skill 缺少工具时返回 capability gap；不自动安装、不自动登录、不自动扩大网络或文件权限。

## 7. 平台漂移

运行前记录 `RuntimeCapabilitySnapshot`：

- runtime 名称与版本；
- Agent 配置发现路径；
- Skill 发现/显式调用能力；
- 并发和递归限制；
- sandbox/approval 语义；
- 工具/MCP 可用性；
- 已知限制。

版本变化后运行 Adapter contract tests。平台新增原生能力时优先删掉重复代码，而不是保留兼容层。

## 8. 安全边界

- Adapter 不签署 Human Gate；
- Tool 输出视为不可信数据；
- 凭据由平台/环境管理，不写入 Task、Handoff、trace 或仓库；
- 外部写动作需要 Project Protocol 与 Task 双重授权；
- 安装依赖、插件或 Skill 属于供应链变化，需要明确任务或人工批准；
- Runtime 会话日志不能成为唯一证据。

## 9. 验收条件

- Codex Adapter 能把两个 Profile 和两个 Skill 映射到原生配置；
- Adapter 不保存自己的权威项目状态；
- capability gap 可以清晰报告；
- 平台升级后可通过 contract test 发现关键行为漂移；
- 替换 Tool Adapter 不修改科研内核；
- 所有外部写动作可追溯到授权 Task。
