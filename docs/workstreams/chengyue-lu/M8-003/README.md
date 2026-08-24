# M8-003 Method Resolution

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 必需审查人：黄毅（GitHub 主名 `let778750-cpu`）
- Task：`M8-003`
- 状态：DONE；PR #30 中与 M8-002、M8-004、M8-005 原子闭合，已合入 `develop@ead1270`
- 实际开发基线：M8-002 feature lineage，已同步其 `def0689` contract hardening
- 最终集成提交：`develop@ead1270d0461b870b8030450b4186f8d62f1eeb7`
- 已合并阶段分支：`agent/method-m8-action-resolution-node`
- 历史提交：`1610d87`（原 M8-003 分支已删除，提交由统一分支祖先关系保留）

## 1. 阶段节点

本 workstream 与 M8-002 共同形成：

```text
Mode
→ first-class Action + hash
→ per-Task Method Resolution
→ no-Skill / Tool / Skill Need / Human / blocked / split
```

这是本轮连续开发的审查节点。原 PR #26 已撤回且未合并；M8-002 与 M8-003 的提交历史已正式合流，
后续只在统一活动分支继续节点级整理。

## 2. 目标

- 新增 `method_resolution` Schema 与 Python contract；
- 将八个 routing cases 一一映射为独立 path+hash Resolution；
- 正式记录 Task/Mode/Action、bounded obligations、最小机制、Skill Need、Human Gate、blocked condition、
  rejected alternatives、status 与 limitations；
- 验证 Action/hash、Mode 与 Need/Gate/block 闭集；
- 保持 no-Skill 一级、provider-neutral 和 Human authority。

## 3. 非目标

- 不实现 Mode v0.2 migration、Resolved Execution View 或 Capability binding；
- 不修改 Assignment、Receipt、Trace、Recovery、API session 或 Runtime；
- 不选择具体 Tool、Skill、Agent、Model、Provider、Adapter 或 MCP；
- 不定义 Human Gate decision vocabulary，不写 Method Trace；
- 不把 `proceed` 升级为 Task completed、contract satisfied 或 Claim accepted。

## 4. 读写范围与契约影响

输入限于 M8 TASK/ROADMAP、ADR-0016、M8-002 Action contracts/Registry 和八个 routing fixtures；跨线
只消费 `develop` 已接受的不变量，不读取或继承候选 Runtime 实现。

写入限于 Method Resolution Schema/model/validation、八个 examples、routing 引用、focused tests、本
workstream 与相应 implementation/module/status/TASKS 文档。公共契约新增 per-Task Method Resolution；
没有新的全局 Registry，也不改变 Execution ownership。

## 5. 证据、风险与停止条件

- [风险台账](RISK_LEDGER.md)；
- [验证证据](VALIDATION.md)；
- [实现合同](../../../implementation/METHOD_RESOLUTION_CONTRACT.md)。

停止条件：八个 Resolution 无损覆盖既有边界结果，正反 Schema/relationship tests 和完整仓库验证通过，
并形成 Action-to-Resolution compact handoff。任何需要修改 Execution View、Capability Snapshot、Mode
migration 或 Decision Authority 的发现登记后推迟，不在本分支扩张。

Governance v2 已生效，统一分支以真实 TaskPacket/hash 绑定、Action 继承关系与 supply-side 分层完成
M8-003 验收；PR #30 已通过节点审查并合并。

按 Governance v2，本分支因 Method Resolution authority surface 至少为 R2：正式 PR 必须提供
authority basis、adversarial evidence、cross-owner authority review 与本 workstream/Risk Ledger。
本次 feature 快照按 dependency DAG 与逐 Task 证据把 M8-003 置为 DONE，不再要求独立状态推进 PR。
