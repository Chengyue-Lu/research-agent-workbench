# 来源与验证范围

本审计固定于 `develop@ab98caf25125e6567d8bb2c8afff02105b54c940`（2026-09-12）。下列文件均可在该提交直接打开，不依赖本机分析稿。验证只能支持本次文档事实与引用，不能替代 Human semantic acceptance。

## 1. Phase C 精确输入

| 输入 | Manifest SHA-256 | 实际 source refs |
|---|---|---:|
| [Case A](../../../../examples/phase-c/m10-003-gate/case-a/source-manifest.json) | `d737238601c0321328d1445dce891a3f40e2f6e41ec8a431f3b3384bff1d01ba` | 13 |
| [Case B](../../../../examples/phase-c/m10-003-gate/case-b/source-manifest.json) | `6b30550de75233d6ab86d3e8d116ef447ded1c37c53e1a3a9610f09a3c2d8865` | 11 |

以文件实际字节计算 SHA-256，与 manifest 的 `source_ref.sha256` 比较，24 项全部匹配；未使用对象内部的示例 `content_hash` 代替实际 pin。具体路径与结果保存在 [SOURCE_INDEX](../../../../work/AUDIT-M12-M13-ENTRY-001/A-20260912-001/SOURCE_INDEX.json)。没有读取 private oracle，没有运行 actor 或重新生成 closure。

语义表逐项引用 [PHASE_C_REVIEW](PHASE_C_REVIEW.md) 中的实际 State、Claim、Decision、Failure、Method Trace。fixture 的 D-PC-A/D-PC-B 不代表真实维护者签字，MTRACE 的 applied 声明也不等于 actual_binding 可用。

## 2. 接受状态和已有实现

- [TASKS](../../../TASKS.md)与 [ROADMAP](../../../ROADMAP.md)：M12/M13 的 reservation、Phase C Human/R2 与独立 Topic 5 进入条件。
- [Phase C workstream](../../chengyue-lu/PHASE-C-RESEARCH-STATE/README.md)、[执行侧验证](../M10-RESEARCH-STATE/VALIDATION.md)、[bounded Gate](../../../implementation/PHASE_C_BOUNDED_GATE.md)：机器完成与待具名语义收口的区别。
- [ADR-0009](../../../decisions/0009-FILE-FIRST-CONTINUITY-AND-SAFE-PAUSE.md)、[recovery.py](../../../../src/research_workbench/execution/recovery.py)、[handoff_transfer.py](../../../../src/research_workbench/context/handoff_transfer.py)：现有文件式恢复检查与交接，不是新 Attempt 执行器。
- [host.py](../../../../src/research_workbench/execution/host.py)与 [generic_closeout.py](../../../../src/research_workbench/execution/generic_closeout.py)：现有 action slice 的执行/闭合边界，仍不授予 Topic 5 authority。
- [ADR-0019](../../../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md)及 TASKS 中 M7/M9：已有可复用演化路径及未激活反馈桥，不需凭“自学习”名称再建相同生命周期。

当前 PR 状态来源：[PR70 接受](https://github.com/Chengyue-Lu/research-agent-workbench/pull/70#pullrequestreview-5186088306)及合并提交、[PR71 本轮复审](https://github.com/Chengyue-Lu/research-agent-workbench/pull/71#pullrequestreview-5186095164)、[PR69](https://github.com/Chengyue-Lu/research-agent-workbench/pull/69)。PR71 的原基线 CI 不证明包含 PR70 的新集成目标通过；本审计不代替其最终检查。

## 3. 本变更的最小检查

仅核对新增文档和 owner 索引的内部链接、上述 24 项字节 pin、diff 空白问题、实际改动范围，以及既有 PR governance。保留一轮独立只读语义复核，重点是误把预检当接续、误把 fixture 当人类接受、重复建立 M7/M9 演化链。

具体结果随本次 [工作记录](../../../../work/AUDIT-M12-M13-ENTRY-001/A-20260912-001/WORKLOG.md)和 PR 验证段提供。TASKS、ROADMAP、源码、Schema、Registry 和 CI 配置没有修改；不执行本地 full、coverage、安装、模型测试或恢复实验。新 PR 的 hosted 检查按已接受工作流执行，不能把其他提交的 CI 成功移记为本提交结果。
