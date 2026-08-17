# Project-internal Handoff Direct Baselines

这些 baseline 不加载新的 project-internal Skill。Task 中原有的 Mode-derived Skill 可以继续存在；
比较对象只是“是否额外需要交接 Skill”。

## Baseline H1：Schema + compact closeout

1. 只读取 Task、正式输出索引、验证结果和 Worklog；不回读完整 Trace。
2. 从 Task 的 required outputs 与 stop conditions 确认状态。
3. 将可定位结果分为 facts、inferences 和 recommendations。
4. 单独检查 limitations、conflicts、unresolved 与 human decision；没有时显式写空数组。
5. 每个会改变下一动作的结论必须能沿 artifact/validation ref 回查。
6. 只给一个最小下一动作；范围或权限缺口返回 blocked，不给隐式 fallback。
7. 运行 Handoff Schema 与 Task/Handoff relationship checks。
8. 主 Agent 默认只读取 Handoff；有争议时再按 ref 扩大读取集。

这是普通 H1 的默认方案。它不是 Skill prompt，也不要求 Transfer Manifest/Audit。

## Baseline H2：H1 + deterministic transfer coverage

仅在 H2 trigger 成立时增加：

1. 在压缩或销毁 Task Context 前，从正式工件声明必须跨上下文保留的稳定条目；
2. 为每个条目固定 kind、criticality、source ref/hash、locator 和 required flag；
3. 将条目映射到 Handoff 的具体 JSON Pointer；
4. 运行 `rwb handoff audit-transfer`，检查 hash、locator、section、required item 与 negative section；
5. Task policy、critical item 或风险 kind 要求时，进行有界独立人工抽样；
6. 未做人类抽样只能称为 `structurally-ready`，不能称为语义等价；
7. 审计没有改变接受、返工或 Gate 决定时，缩小 H2 trigger，而不是增加常驻 reviewer。

## Baseline 停止条件

- Template/checker 已让真实遗漏和返工降到可接受范围：保持 `no-Skill`；
- 问题可由 Task policy、criticality 或 Human sample 修复：修订契约，不创建 Skill；
- 只有跨 Task 重复出现、且需要语义取舍的遗漏仍存在：才进入 compact Skill trial。
