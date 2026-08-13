# CCRML 讨论吸收与差距审计

来源：用户于 2026-08-13 提供、位于工作区外部的本地讨论纪要《会议智能纪要_CCRML与AI课题组Infra重构_结构化完整版》。该文件用于设计参考，不复制进仓库，也不作为机器真值。

外部机制核验：[`akitaonrails/ai-memory`](https://github.com/akitaonrails/ai-memory) 实际是一套含服务、hooks、SQLite/FTS 与跨 CLI handoff 的完整平台；[Graphiti](https://github.com/getzep/graphiti) 是依赖图存储和模型管线的时态图框架；[LangGraph](https://github.com/langchain-ai/langgraph) 的 durable execution/interrupt 属于其 runtime/checkpointer。它们因此只作为机制参考，不直接进入首版依赖。

| 讨论概念 | 当前项目对应物 | 本轮决定 |
|---|---|---|
| Atomic Work Unit / ExecutionContract | Task Packet | 合并：补原子边界、完成检查和安全暂停条件 |
| ResultEnvelope | Attempt + Handoff + Execution Receipt | 合并：补阶段完成、安全暂停、等待状态 |
| Context Budget Controller | Context Snapshot | 采纳：加入下一 AWU、收尾和安全余量比较 |
| ResumePacket / `current_resume.json` | Main State | 合并：补 Continuity 状态、机器引用和 Git 基线 |
| Fresh Session Continuity Check | `rwb context resume-check` | 扩展：校验哈希、Git、协议、digest 与下一动作 |
| Machine Evidence > LLM Summary | Deterministic report + Receipt assessor | 强化：失败报告阻断显式 `contract-satisfied` 宣称，但不抹掉已完成的负对照执行 |
| Stable Failure Memory | Attempt.failure / 风险与测试证据 | 暂缓：先定义准入和失效语义，再决定是否新增工件 |
| `continuity.sqlite` | 无 | 暂缓：文件闭环先做故障注入与 benchmark |
| Hybrid/Graph retrieval | 无 | PARKED：只能是 Index，不能成为 Truth |
| 自动多 CLI rollover | 平台原生线程/会话 | 不自建：只输出可验证恢复工件 |

## 已实现的会议故障场景

- 下一 AWU 成本超过剩余预算：触发 rollover，不启动新单元；
- 收尾余量自身不足：触发 block，要求最小安全暂停；
- `SAFE_PAUSE`：Attempt、Handoff、Receipt、Context Snapshot 与 Main State 可一致恢复；
- Git HEAD 冲突：`resume-check` 输出 `RESUME-CONFLICT-GIT`；
- Receipt 显式宣称 `contract-satisfied` 但机器报告失败：`RECEIPT-VALIDATION-FAILED` 获胜；
- checkpoint 内容被修改：规范化 digest 拒绝恢复；
- checkpoint 发布失败：最终路径不暴露半文件，临时文件被清理；
- Handoff 压缩：Transfer Manifest/Audit 校验关键传递条目。

## 尚未证明

- 原生新会话能否只凭 Main State 一次恢复到正确动作；
- 跨 Codex、Claude Code 与其他 CLI 的一致可用性；
- AWU 成本估计误差及最合适的 reserve；
- 稳定 Failure Memory 是否减少重复失败；
- 文件查询何时变慢到值得引入 SQLite/FTS；
- 连续性机制相对人工 Markdown Handoff 的 token、时间和错误收益。
