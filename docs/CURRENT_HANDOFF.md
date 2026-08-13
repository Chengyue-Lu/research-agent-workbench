# 当前开发 Handoff

状态：`K-API-1` 已完成，`K-API-2` 是唯一下一关键节点

更新日期：2026-08-13

权威分支：合并后的 `main`

这份文件用于让没有既往聊天上下文的人或 AI 直接恢复开发。聊天摘要、平台线程和临时 transcript 都不是项目状态的权威来源。

## 1. 恢复结论

当前仓库可以由新的开发者或 AI 直接接手。离线依赖、确定性验证、任务与 Skill 绑定、Provider 薄适配器、文件式连续性和隔离 API session kernel 均已进入仓库；接手者不需要访问原讨论记录，也不需要先选择 Codex、OpenCode、Claude Code 或其他 Agent 平台。

但当前只到技术基础节点，尚不能宣称：

- Task 已能自动执行成完整 API 子会话；
- 真实 Provider/Model 已通过本机 conformance；
- 多 Agent 路径比单 Agent 更有效；
- 生成内容具有科学正确性；
- 项目已达到公开发布条件。

## 2. 接手时先读取

按以下顺序读取，避免把全部仓库加载进主上下文：

1. `AGENTS.md`：不可违反的仓库边界；
2. `docs/decisions/0010-API-FIRST-ISOLATED-EXECUTION.md`：当前执行方向；
3. `docs/TASKS.md`：任务状态和唯一关键路径；
4. `docs/NEXT_STEPS.md`：`K-API-2` 的停止条件；
5. `docs/modules/03-AGENT_RUNTIME.md` 和 `docs/modules/09-ADAPTERS_AND_INTEGRATIONS.md`；
6. `examples/task-evidence.yaml` 及对应 Profile、Skill Assignment 和 Main State；
7. 只有修改具体契约时，再读取其 Schema、ADR 和测试。

不要用旧聊天记录补全仓库没有表达的状态。若本文与已接受 ADR 冲突，以较新的 ADR 和机器验证结果为准。

## 3. 已冻结的架构边界

- 文件契约是权威状态；会话历史不是。
- 纯 API fresh session 是可移植执行基线；平台原生 Agent/线程只是可选 Adapter 或人工入口。
- 模型池只保留 `primary`、`worker` 和少量显式 `specialist` 槽。
- 不实现模型评分、价格抓取、LLM Router、静默升级或跨 Provider fallback。
- 主 Agent 只维护目标、任务图、决策、风险、工件索引和下一动作，不接收全部原始材料与工具日志。
- 子 Agent 只获得 Task、选定 Skill、必要输入、有效权限、输出合同、预算和停止条件。
- 子会话可压缩或删除，但必须先写出正式工件、Handoff、Receipt 和可恢复状态。
- 不建立全局 Supervisor、固定科研 DAG、消息总线或连续性数据库，除非真实失败证据支持新的 ADR。
- 学科差异通过 Research Mode Pack、Skill 和 Tool 组合表达，不固化为一条全局科研流程。

## 4. 当前代码状态

已经实现：

- 版本化科研对象、Task、Attempt、Handoff、Context Snapshot、Execution Receipt 和 Transfer Audit Schema；
- Agent Profile、Skill Registry、确定性 Skill Assignment 和作用域权限交集；
- OpenAI Responses、Anthropic Messages、Gemini `generateContent` 非流式薄 Adapter；
- `explicit-slot-only` Model Pool，模型 ID 由调用者显式注入；
- fresh `IsolatedApiSessionRunner`，具有轮次、工具、并行、输出、token/可得成本和 wall-time 边界；
- data policy、能力和预算的调用前阻断；
- `SAFE_PAUSE`、文件 checkpoint、恢复冲突检查及机器证据优先；
- 可选 Codex 配置映射，但没有平台 launch/collect 依赖。

尚未实现：

- Task/Skill Assignment 到 `ModelRequest` 的正式编译器；
- API session 结束到 Attempt、Research Artifact、Manifest、Handoff、Receipt 和 Main State 的原子关闭流程；
- 删除临时 transcript 后的端到端新主会话恢复测试；
- 实际启用 `primary`/`worker` 槽的真实 Windows 调用证据；
- 多模态 specialist 的真实 Adapter 能力。示例中的该槽默认禁用，只是未来占位。

## 5. 唯一下一节点：K-API-2

目标：把 `EVID-001` 的 Task、Profile、Skill Assignment 和显式 `worker` 槽编译到一个全新 API session。会话完成或安全暂停后，必须形成：

1. Attempt；
2. 正式 Research Artifacts；
3. Transfer Manifest 与 Audit；
4. Handoff；
5. Context Snapshot；
6. Execution Receipt；
7. 更新后的 Main State。

随后删除内存 transcript，启动新的主会话并运行恢复检查。只有新会话仅凭文件即可得到唯一正确的下一动作，且不会重复已完成副作用时，才算到达 `K-API-2`。

到达该节点后立即暂停评审。不要顺手扩展 GUI、数据库、多模态、streaming、server tools、新 Provider 或平台 Adapter。

## 6. 可同步开展的工作

多名开发者或 AI 应使用独立分支和不重叠写入范围。建议分为：

| 轨道 | 工作 | 独占写入范围 | 交付给集成者的内容 |
|---|---|---|---|
| K2-A 编译边界 | 定义 Task/Assignment/Profile/Model Slot 到 session 输入与 limits 的纯函数 | 新的 `src/research_workbench/execution/` 编译文件及对应单元测试 | 输入输出类型、失败码、最小上下文证明 |
| K2-B 连续性 fixtures | 准备 completed、tool-failed、safe-paused、stale-input 四条无网络 fixtures | 新的 `examples/api-execution/` 和专用测试文件 | 可重放 fixture、预期状态与哈希 |
| K2-C 关闭事务设计 | 评审 Attempt 到 Main State 的写入顺序、临时路径和崩溃恢复点 | 先只写设计/测试；接口冻结后再写独立 closeout 文件 | 原子性测试和部分写入失败矩阵 |
| K2-D 独立审计 | 检查主上下文泄漏、权限扩大、重复副作用和完成过度宣称 | 测试与审计报告，不修改生产接口 | 阻断项及最小复现 |

同步规则：

- K2-A 的内部输入/输出合同先由一名集成者冻结；其他轨道不得各自发明第二套 session 状态。
- 不允许两个轨道同时修改 Schema、`cli.py` 或同一 Registry 文件；这三类修改由集成者串行吸收。
- fixtures 可以并行准备，但不得把 fixture 成功写成真实 API 或科学价值证据。
- 每次 Handoff 都要给出基线提交、实际修改路径、验证命令、未完成项和下一动作。

## 7. 已知风险和预警

- 编译器最容易误把主 Agent 全历史、未选 Skill 或原始大材料注入子会话。
- 多文件关闭若没有 stage/validate/publish 边界，崩溃后可能出现部分完成状态。
- 工具产生外部副作用后再发现预算不足，会导致恢复时重复执行；副作用必须有幂等键或显式人工确认边界。
- 部分 Provider 不返回完整 token 或成本数据；配置硬预算时必须失败或安全暂停，不能假定为零。
- Provider 返回的实际模型与显式槽位不一致时必须记录并阻断完成宣称。
- Handoff 结构完整只表示可审计，不表示语义无损或科学正确。
- 并行 Agent 会增加合并和校核成本；无法声明独立写入范围的任务不应并行化。
- 真实凭据仅在获准的真实 Windows 用户上下文使用，不写入仓库、不输出值、不在隔离环境迁移令牌。

## 8. 本地恢复与验证

```powershell
git clone https://github.com/Chengyue-Lu/research-agent-workbench.git
Set-Location research-agent-workbench
git checkout main
python -m pip install -e .
rwb validate examples registry --root .
rwb models probe --config registry/models/pool.example.yaml --json
python -m unittest discover -s tests -v
```

`models probe` 默认不读取环境值。只有使用者显式增加环境检查或执行真实 conformance 时，才允许在已授权的本机上下文检查配置是否存在；任何报告都不得保存凭据值。

本 Handoff 写入时的验证基线：

- 全量单元与合同测试：135 项通过；
- 示例与 Registry：`validated=53 errors=0 warnings=0`；
- `git diff --check`：通过；
- 未执行真实 API 调用。

## 9. 接手者完成一次工作的最小回传

新的开发者或 AI 至少应回传：

- 基线提交与工作分支；
- 负责的 Task ID 和独占写入范围；
- 修改过的正式文件；
- 执行过的验证及原始结果位置；
- 未证明的内容和剩余风险；
- 是否达到 `K-API-2`，以及唯一下一动作。

缺少以上任一项时，不应把聊天中的“已完成”同步回 Main State。
