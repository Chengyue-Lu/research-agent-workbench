# Phase A / M8 Core Formalization 收口

- 日期：2026-08-24
- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人审查：黄毅（GitHub `let778750-cpu`）
- Feature PR：[#30 M8 Method Control Stage](https://github.com/Chengyue-Lu/research-agent-workbench/pull/30)
- `develop` 集成提交：`ead1270d0461b870b8030450b4186f8d62f1eeb7`
- `main` release：尚未进行；本记录不把 develop 集成写成正式发布

## 最终范围

Phase A 以 M8-001～005 完成以下 Core contract：

- 两个正式 Mode 的 16 个逻辑 Action、跨 v0.1/v0.2 的 32 个 versioned Action 文档；
- raw-byte hash-pinned Action Registry 与 published identity append-only 治理；
- 八个 synthetic bounded TaskPacket 与八个 Task-bound Method Resolution；
- Research Mode v0.1/v0.2 共存及两个 exact-pin migration record；
- Decision Authority Matrix v1 与九个 Authority Rule Eligibility fixture；
- Task/Mode/Action/Gate/Artifact/stop/block/claim-effect、migration 和 eligibility 的确定性关系验证。

Phase A 的完成只证明 Method/Core 契约、引用、迁移与 authority ceiling 闭合。它不包含 Capability
binding、Resolved Execution View、Assignment/Receipt migration、Method Trace、完整 Human Decision、
Runtime consumer 或真实科研净收益。

## 合并与验证证据

- PR #30 最终 head `fb03bcd9944452b033e1c0ad74cc1db6b8fec34e` 与 `develop@ead1270` tree 相同；
- 黄毅在最新 head 完成跨 owner R2 review，并用 clean develop merge 复核 352 passed、3 skipped；
- GitHub `governance`、`test (3.11)`、`test (3.13)` checks 全部通过；
- 四个 DONE Task 的 workstream 分别保留具名 validation 与 Risk Ledger；
- 这些证据证明结构、引用、哈希、治理和兼容边界，不证明科学正确性。

## 真值变化

- [`TASKS.md`](../TASKS.md)：M8-001～005 均为 DONE；下一阶段转为 M9 / Phase B；
- [`STATUS.md`](../STATUS.md)：记录 Action、Resolution、Mode migration 与 Rule Eligibility 已实现，并列出
  Capability/Execution/Human Decision 限制；
- [`ROADMAP.md`](../ROADMAP.md)：Phase A Gate 收口，Phase B 进入 Evolution Foundation；
- ADR-0013/0015/0016 的稳定语义不因收口改写。

## 后续入口

下一工作段为 [`PHASE-B-EVOLUTION`](../workstreams/chengyue-lu/PHASE-B-EVOLUTION/README.md)，首项
`M9-001` 只正式化需求侧 Capability Requirement。Provider availability、具体 Tool/Skill/Adapter
binding、fallback 与 API/Runtime 继续由后续供给层和黄毅负责的执行线处理。

M8 原始证据继续保留在
[`M8-002`](../workstreams/chengyue-lu/M8-002/README.md)、
[`M8-003`](../workstreams/chengyue-lu/M8-003/README.md)、
[`M8-004`](../workstreams/chengyue-lu/M8-004/README.md)和
[`M8-005`](../workstreams/chengyue-lu/M8-005/README.md)。
