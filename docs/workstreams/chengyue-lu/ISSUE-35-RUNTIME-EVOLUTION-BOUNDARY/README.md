# ISSUE-35 Runtime / Evolution Boundary

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人审查：黄毅（GitHub `let778750-cpu`）
- Audit ID：`ISSUE-35`
- 风险：R2 authority / Runtime ownership / Skill admission
- 基线：`develop@aeca805e4dbb43b356c7f6da8c1262c9f6220569`
- 目标 base：`develop`
- 工作分支：`codex/issue-35-runtime-evolution-boundary`
- 状态：docs-only 实现与本地确定性验证已完成；等待 R2 cross-owner acceptance
- 对应讨论：[Issue #35](https://github.com/Chengyue-Lu/research-agent-workbench/issues/35)
- 前置集成：[PR #33](https://github.com/Chengyue-Lu/research-agent-workbench/pull/33)

## 1. 风险触发与目标

PR #33 已把 Phase B 收口为 structural foundation，但现有 repository-wide consumer 仍会递归加载
`registry/`、`examples/` 并执行 Skill Need/Lifecycle/Gate 完整闭包。若把它当成 Topic 4 Runtime API，
Runtime 就会依赖 Skill Evolution 内部对象，no-Skill/direct Tool 也无法获得真正的最小部署闭包。

本 R2 workstream 冻结：Capability-first Runtime 内环、可选 Maintainer Evolution 外环、两个单向端口、
发布投影、consumer profiles 和双方 authority ceiling。实现结论由
[ADR-0019](../../../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md) 承载。

## 2. 审计基线

PR #33 最终 head `4d86c4b6d1c2acf94e87a833bfe38ba57a15ffbc` 与合并后的 `develop@aeca805`
具有相同 tree `de6ff063baa4667cd1cc383810cbf44656eeb85f`。本 workstream 不回滚或重开 PR #33，
只以前向 ADR 限定其 Runtime 解释范围。

| Compatibility Gate | `aeca805` 现状 | 本 workstream 决定 |
|---|---|---|
| Runtime 不依赖 Evolution | 未满足 | 定义独立 `runtime-bundle` profile |
| consumer 不递归扫描整仓 | 未满足 | future Runtime 只接受显式 closure manifest |
| no-Skill/direct Tool 零 Skill | 仅 structural replay | Topic 4 必须提供 supply-neutral Execution View |
| Skill Runtime 不解析完整 Lifecycle | 未满足 | 只消费 `SkillReleaseProjection` |
| gap/failure 不自动创建 Skill Need | 已满足 | 提升为 authority invariant |

这些结果不否定 PR #33 的 structural foundation，也不把 Issue #35 扩成 Runtime 重写。

## 3. 读写范围

允许读取：

- repository guidance、Development、Architecture、Roadmap；
- Skill System、Method/Capability/Need/Lifecycle implementation contracts；
- ADR-0013/0016、Phase B workstream、PR #33 最终差量；
- Issue #35 指向的 primary external references。

允许写入：

- `docs/ARCHITECTURE.md`、`docs/ROADMAP.md`；
- ADR、相关 module/implementation contract；
- 本 workstream、owner index 与 Phase B 的前向澄清注记。

禁止写入：

- `src/`、`schemas/`、`registry/`、`examples/`、fixtures 与 tests；
- `docs/TASKS.md`、`docs/STATUS.md`、M9 完成状态；
- 黄毅的 workstream 或任何其他本地 clone/worktree。

## 4. 决定产物

- ADR-0019：双环、单向端口、authority matrix、兼容边界与实施顺序；
- Stable Architecture / Skill System：Capability-first Runtime 的正向系统模型；
- Method/Capability/Need/Lifecycle contracts：`maintainer-full` 与 future `runtime-bundle` 的读取边界；
- Roadmap Topic 4 Gate：最小闭包、零 Skill、release projection 与 frozen-view 要求；
- [Authority Basis](AUTHORITY_BASIS.md)、[Risk Ledger](RISK_LEDGER.md)与[Validation](VALIDATION.md)。

## 5. 外部证据使用边界

ADR 的 Kubernetes、OPA、OCI、TUF、in-toto 与 Toolformer 链接均为 2026-08-25 检索的 primary source，
只提供设计类比。未复制外部对象、术语或代码，也不以外部项目证明本项目的 authority 结论。规范真值
仍来自本仓库 ADR、契约及具名跨负责人审查。

## 6. 非目标与未证明内容

本 workstream 不实现或证明：

- Release Projection Schema/publisher、Runtime profile/consumer 或 Resolved Execution View；
- live Provider、真实账户/模型、API session 或 end-to-end execution；
- Skill 科研净增量、Trial/Evaluation/Human Decision 系统；
- telemetry、中央 Registry、数据库、自动安装/升级、routing/fallback 或本地自学习；
- PR #33 最终 GitHub CI/reviewDecision 的独立复核。

## 7. 接受与停止条件

本分支只完成 docs-only R2 设计。以下条件满足前不得合并 Stable 文档：

1. 文档链接、governance tests、完整 Python tests、repository validation 与 diff checks 通过；
2. 路诚钺确认 Capability/Skill/Need/Evaluation/Admission 权威；
3. 黄毅确认 Runtime 读取面与 Provider/Adapter/API 责任未被 Evolution 侵入；
4. 两位 owner 接受 [Authority Basis](AUTHORITY_BASIS.md)及对抗性证据；
5. ADR-0019 从 `Proposed` 改为 `Accepted` 后，黄毅再次确认最终 diff。

停止于文档边界；后续代码拆为 Runtime Bundle/Profile、Skill Release Projection/Publisher 和 Topic 4
Resolved Execution Integration 三个有依赖顺序的实现任务。Capability Diagnostic/feedback bridge 保持
PARKED，等待 Phase C Failure/Trace 与 privacy 语义稳定。

## 8. 下一动作

提交 R2 cross-owner review；在具名接受前保持 ADR-0019 为 `Proposed`，不在本 workstream 开始后续
代码实现。
