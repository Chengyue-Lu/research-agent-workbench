# M5-008 definition Attempt

Attempt ID：M5-008-DEFINITION-001；kind：task-definition；risk：R2。
Accountable owner：Chengyue-Lu；agent actor：codex-primary；delegation：none。
本记录描述 Task 定义工作，不是 M5-008 live execution Attempt 或 Gate 接受。

## 授权与范围

Human 请求新增 “M5-008 — Live Evaluation Pilot Gate”，用真实 API、真实 Provider/Tool execution、
完整四臂 transport 验证 M5-007 Harness 的 live 工程运行，不产生 confirmatory net-benefit conclusion；
将其作为 M5-004 前置，修改 Task 并提交 PR。该请求仅授权本次文档与 PR 工作。

基线：`0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`，branch：`docs/m5-008-live-pilot-gate`。
主 develop checkout 保持原 HEAD 和 clean，工作在独立 worktree。

- 读取集：AGENTS、DEVELOPMENT、TASKS、ROADMAP、STATUS、M-series map、ADR-0020、M5 workstream
  与 Protocol、Issue55 / PR86，以及用于现行文档/Task 检查的 governance/CI scripts 和 tests。
- 写入集：上述 M5 规划文档及本 Attempt；Task 行仅新增 M5-008，修订未完成 M5-004 的依赖与 pilot 隔离验收。
- 输出：[Live Pilot Gate](../../M5-008_LIVE_PILOT_GATE.md)、同步任务图、风险与 task-definition/R2 PR。
- 停止条件：运行真实 API/Tool、改变 DONE Task、越过 admission 或实现 Harness 均超出本次授权。

## Evidence 与 capture 边界

PR84 已接受 M6-008 DONE/M5-007 READY；读取的 PR86 head 为
`b53a391ece3a4be7207c00c636dc9e1570e71473`，只提议 H1/H2，不构成完整 M5-007 接受。
输入正文的 immutable 来源为上述 base 中的仓库文件；PR86 观察仅用于确认当前范围，不将其 CI
移用为本分支证据。

本 Attempt 为延迟、部分 capture：早期读取、工具返回与 compaction 前事件未完整落盘，明确保留
capture gap；不重建缺失时间、原始消息或工具结果，不声称 native Trace v0.1 完整性或通过其校验。
后续本地检查的命令、输出和候选文件 hash 保存于本目录的验证工件；最终提交的 hosted CI 与 review
保留在 PR，绑定各自 exact head。Git 保存每次变更字节；没有 inter-agent transmission。
不保存隐藏推理、密钥、认证头或未授权的私有研究数据。
