# M8-002 Mode Action 一等契约

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 必需审查人：黄毅（GitHub 主名 `let778750-cpu`）
- Task：`M8-002`
- 状态：implementation complete；已纳入统一 Action-to-Resolution 节点，未合并
- 目标 base：`develop`
- 基线 commit：`5991cafdb7f536cd7b871508de9055d02b558728`
- 活动工作分支：`agent/method-m8-action-resolution-node`
- 历史分支：`agent/method-m8-002-mode-action-contract`（保留引用，不再继续开发）

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

已发布的 `action_id@version` 是 immutable identity；语义、Mode、路径或内容变化必须发布新版本。
Claim effect 复用 canonical Claim strength，Gate 只保存 opaque ID，且 Action 不开放任意 metadata
作为实现绑定或 authority 逃生口。

## 5. 证据与风险

- [风险台账](RISK_LEDGER.md)：记录语义越权、跨线耦合、Registry drift 和治理断层；
- [验证证据](VALIDATION.md)：记录 focused/full tests、文档检查与 Registry 闭集验证；
- 实现合同：[`MODE_ACTION_CONTRACT.md`](../../../implementation/MODE_ACTION_CONTRACT.md)。

测试通过只证明结构、引用与哈希闭合，不证明 Action 对真实研究任务的方法适用性或科学正确性。

## 6. 合并与停止条件

原独立 Draft PR #26 已撤回且未合并。M8-002 与 M8-003 现作为一个连续的 Action-to-Resolution
审查节点维护；节点分支不把当前隔离开发状态直接当成可合并的 TASKS snapshot。Governance v2
生效后，统一节点 PR 必须先形成合法的依赖与状态转换，再以 `develop` 为目标接受 R2 审查。

停止条件：16 个 Action、Registry、Schema、正式 fixture 引用和确定性负面测试形成闭集；任何需要
修改 Method Resolution、Execution View、Runtime 或 Human Authority 的发现都登记并转交后续 Task，
不在本分支扩张。

只有达到当前 History 触发条件时才建立长期 closeout；原 workstream、PR #26 与旧分支均保持可追溯。
