# 路诚钺维护工作流

责任人：路诚钺（GitHub `Chengyue-Lu`）。工作流目录只描述技术范围，不能替代具名责任。

当前进行中或仍待具名语义决定的工作流：

- [`POST-INTEGRATION-DOCS-ALIGNMENT/`](POST-INTEGRATION-DOCS-ALIGNMENT/README.md)：以当前
  `develop` 实现和治理事实校正文档真值、Runtime 传递关系与 derived navigation；不重定义系统契约。
- [`PHASE-C-RESEARCH-STATE/`](PHASE-C-RESEARCH-STATE/README.md)：M10 bounded machine implementation
  已集成；Human semantic review 与 R2/Phase C closeout 仍 pending，Topic 5 未获实现权限。
- [`M11-SKILL-RUNTIME-EXTENSION/`](M11-SKILL-RUNTIME-EXTENSION/README.md)：M11-005/006 的
  runtime-minimal projection publication 与统一 Skill Supply mapping；本分支实现待 exact-head CI 与
  cross-owner R2 review，生产 index 仍为空且不改变 zero-Skill Core。

已集成、保留审计记录的工作流：

- [`M11-SKILL-RUNTIME-ACTIVATION/`](M11-SKILL-RUNTIME-ACTIVATION/README.md)：PR #52 独立恢复
  M11-005 为 READY 的历史 activation 记录；后续完成状态以 TASKS 与 extension workstream 为准。
- [`CI-PERFORMANCE-MAINTENANCE/`](CI-PERFORMANCE-MAINTENANCE/README.md)：PR #47 的 CI 去重与
  hosted-runner wall-time 基线；当前质量 topology 由 TEST-QUALITY-001 扩展。
- [`TEST-QUALITY-001/`](TEST-QUALITY-001/README.md)：PR #49 的分层测试、Coverage Policy v2、critical
  branch 与 duration evidence。
- [`M11-EXECUTION-REINTEGRATION/`](M11-EXECUTION-REINTEGRATION/README.md)：M11-001～004 的
  module-level Execution Reintegration 实施与 R2 验证；可选 M11-005/006 由独立 extension workstream 维护。
- [`ISSUE-41-M-SERIES-NORMALIZATION/`](ISSUE-41-M-SERIES-NORMALIZATION/README.md)：PR #42 的
  M-series Task 规范化审计；内部状态矩阵是历史快照，当前真值只在 TASKS。
- [`ISSUE-35-RUNTIME-EVOLUTION-BOUNDARY/`](ISSUE-35-RUNTIME-EVOLUTION-BOUNDARY/README.md)：R2 Skill Evolution 可选 Maintainer 外环与 Runtime 消费边界。
- [`PHASE-B-EVOLUTION/`](PHASE-B-EVOLUTION/README.md)：Phase B 的 Capability Requirement、Skill Need、lifecycle、Protocol 与共享 Snapshot 演化基础。
- [`GOV-V2-001/`](GOV-V2-001/)：R2 风险比例化开发治理与共享真值边界；外部 Admin rollout 状态仍由其 rollout 记录单独说明。
- [`GOV-V2-STAGE-CLOSURE/`](GOV-V2-STAGE-CLOSURE/)：R2 路径补全、通用 published identity 与 Stage 原子依赖闭合。

- [`M8-002/`](M8-002/README.md)：将两个正式 Research Mode 的 Mode Action 正式化为一等契约。
- [`M8-003/`](M8-003/README.md)：将 Action-to-mechanism 决定正式化为版本化 Method Resolution。
- [`M8-004/`](M8-004/README.md)：在不覆盖 v0.1 的前提下建立 Research Mode v0.2 最小迁移 seam。
- [`M8-005/`](M8-005/README.md)：冻结 Decision Authority Matrix 与非授权性的 Authority Rule Eligibility。
