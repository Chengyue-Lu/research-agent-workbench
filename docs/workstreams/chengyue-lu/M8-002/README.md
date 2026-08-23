# M8-002 Mode Action 一等契约

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 必需审查人：黄毅（GitHub 主名 `let778750-cpu`）
- Task：`M8-002`
- 状态：feature implementation complete；等待跨负责人审查与独立 task closeout
- 目标 base：`develop`
- 基线 commit：`5991cafdb7f536cd7b871508de9055d02b558728`
- 工作分支：`agent/method-m8-002-mode-action-contract`

## 1. 目标

把既有 `evidence-synthesis` 与 `simulation` Action 基线正式化为：

- 独立、版本化的 `mode_action` 文档；
- 对路径与原始文件字节做 SHA-256 固定的闭集 Registry；
- 可由 Mode、routing fixture 和后续 Method Resolution 稳定引用的一等契约；
- 对 ID、版本、Mode 归属、路径、哈希、missing/orphan/drift 做确定性校验的实现。

## 2. 非目标与停止边界

本工作流不实现或修改：

- Method Resolution、rejected alternatives 或 Capability Resolution；
- Research Mode v0.1 → v0.2 migration；
- Skill Need、Skill/Tool/Agent/Model/Provider/Runtime binding；
- Human Gate decision vocabulary、Method Trace 或 Research State；
- API session、Receipt、Recovery、Execution Host 或数据出口策略。

Action 只回答“哪个原子研究动作需要约束”，不能选择执行机制，也不能批准 Claim 或 Human Gate。

## 3. 输入与读取范围

规范输入：

- `docs/TASKS.md`、`docs/ROADMAP.md`；
- ADR-0013 与 ADR-0016；
- `docs/modules/02-PROTOCOL_AND_MODES.md`；
- 历史 Mode–Skill workstream 中的 Action requirements 与 routing fixtures；
- `examples/mode-skill-routing/mode-action-routing-v1.yaml.txt`。

跨线约束只读取已合入 `develop` 的
[`execution-runtime-recovery` 审计采纳矩阵](../../huangyi/execution-runtime-recovery-audit/ADOPTION.md)，
不读取或继承对方候选 Runtime 分支实现。

## 4. 写入范围与公共契约影响

允许写入：

- `schemas/v0.1.0/mode-action*.schema.json`；
- `registry/modes/actions/**`；
- Mode Action protocol model、document validation 与相应测试；
- routing fixture 的正式 Action 引用；
- 本 workstream、Mode/implementation/status 文档及 M8-002 的非完成态进度。

公共契约新增 `mode_action` 与 `mode_action_registry`。它们是 Method/Core 契约，不改变 Runtime
ownership，也不要求 Execution/Receipt 立即迁移。后续消费者必须显式引用 `action_id@version`；需要
冻结具体内容时同时保存 Registry 中的 `content_hash`。

## 5. 证据与风险

- [风险台账](RISK_LEDGER.md)：记录语义越权、跨线耦合、Registry drift 和治理断层；
- [验证证据](VALIDATION.md)：记录 focused/full tests、文档检查与 Registry 闭集验证；
- 实现合同：[`MODE_ACTION_CONTRACT.md`](../../../implementation/MODE_ACTION_CONTRACT.md)。

测试通过只证明结构、引用与哈希闭合，不证明 Action 对真实研究任务的方法适用性或科学正确性。

## 6. 合并与停止条件

feature PR 以 `develop` 为目标并使用 squash merge。本 PR 不把 M8-002 置为 `DONE`，也不提前启动
M8-003。实现合入 `develop` 并完成集成验证后，另建 `task-closeout` PR 更新 TASKS、Changelog、
验证/历史证据；只有 closeout 合并后 M8-003 才可进入 READY。

停止条件：16 个 Action、Registry、Schema、正式 fixture 引用和确定性负面测试形成闭集；任何需要
修改 Method Resolution、Execution View、Runtime 或 Human Authority 的发现都登记并转交后续 Task，
不在本分支扩张。

合入 `main` 后，在 `docs/history/` 新建具名 M8-002 closeout，原 workstream 路径冻结保留。
