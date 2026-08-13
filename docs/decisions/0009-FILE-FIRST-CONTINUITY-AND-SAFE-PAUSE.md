# ADR-0009：复用现有工件建立文件式连续性与安全暂停

状态：Accepted

日期：2026-08-13

## 背景

本轮提供的 CCRML/Infra 讨论纪要提出 Atomic Work Unit、动态 Context Budget、`SAFE_PAUSE`、机器证据优先、最小 ResumePacket、Fresh Session Continuity Check，以及后置 Failure Memory/图检索。其问题判断与本项目一致，但若直接新增 `ExecutionContract`、`ResultEnvelope`、`current_resume.json` 和 `continuity.sqlite`，会与已有 Task Packet、Attempt、Handoff、Execution Receipt、Context Snapshot 和 Main State 形成平行真值。

外部项目也说明了边界：`ai-memory` 是一个带服务、hooks、SQLite/FTS 与原始会话采集的完整跨 CLI 记忆平台；Graphiti 需要图数据库与 LLM/embedding 管线；LangGraph 的持久化中断依赖自身 checkpointer/runtime。这些机制值得参考，但当前引入会扩大运行时与真值所有权。

## 决策

1. `Task Packet` 同时承担 AWU 与 ExecutionContract：新增 `atomic_boundary`、`completion_checks` 和 `safe_pause_conditions`，不创建重复对象。
2. `Attempt + Handoff + Execution Receipt` 承担 ResultEnvelope：显式支持 `stage-completed`、`safe-paused` 和 `waiting`，Runtime 结束不再被等同于 Task 完成。
3. `Context Snapshot` 新增同单位的动态预算估计：仅当 `remaining >= next_atomic_cost + closeout_cost + safety_margin` 时允许启动下一原子工作单元；固定百分比仍只是代理指标。
4. `Main State` 继续承担最小 ResumePacket：新增 `continuity_status`、哈希锁定的 `machine_state_refs` 和可选 `git_head`。`resume-check` 先核对文件哈希、协议、checkpoint digest、Git 基线和下一动作，再允许恢复。
5. Receipt 的 `status: completed` 只表示执行生命周期结束。只有显式 `completion_claim: contract-satisfied` 才声明 Task 合同已满足，并且必须由可解释的机器验证工件支持；其确定性报告为 `fail` 时声明被阻断。这样机器证据优先，同时保留执行完成但结果失败的实验和负对照。
6. 首版保持文件优先、原子发布和无常驻服务。YAML 先写入并刷盘同目录临时文件，再以排他硬链接发布到最终路径；文件系统不支持该语义时安全失败，不回退为直接写最终文件。SQLite、FTS、向量与图层只有在文件式基准出现可复现失败且对照实验证明收益后才进入新 ADR。
7. Continuity 是现有真值的投影与恢复入口，不拥有科学接受权，也不存完整聊天或 Chain-of-Thought。

## 后果

优点：会议提出的关键安全语义进入现有内核而不增加第四套状态系统；跨模型/平台仍只需读写稳定文件；恢复冲突和虚假完成可确定性检测。

代价：当前没有自动跨窗口启动、历史检索数据库或 Failure Memory；上下文成本仍可能是估计值。Git HEAD 只锁定提交，不代表未提交工作树，因此 checkpoint 应在明确提交边界创建，机器引用哈希仍需独立核对。真实 API fresh session 的恢复样本与对照基准仍需后续采集。

## 暂缓项

- `continuity.sqlite`、常驻 CCRML 服务与生命周期 hooks；
- FTS、embedding、Graphiti/A-MEM 式图检索；
- 自建窗口/CLI 调度器；
- 未经实测写死的百分比和 AWU 成本模型；
- 从完整 transcript 自动抽取并升级长期事实。
