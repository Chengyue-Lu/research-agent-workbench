# M5 Skill Closeout Replay Gate

- Gate identity：`M5-SKILL-CLOSEOUT-REPLAY-GATE`（Issue #55 Gate B）。
- 状态：**UNSATISFIED**。
- 实施 identity：`M11-007`，定义候选见 [README](README.md) 与 [TASKS](../../../TASKS.md)。
- Execution acceptance：黄毅（`let778750-cpu`）；Evaluation / Skill identity acceptance：路诚钺（`Chengyue-Lu`）。

## 满足条件

Gate B 仅在 M11-007 按既有 Task definition 验收并合入、且以下证据已被具名双方接受时转为 SATISFIED：

| 必需证据 | 当前值 |
|---|---|
| accepted implementation commit / PR | 尚无 |
| extension / Schema / validator identity、版本、repo-relative path 与 SHA-256 | 尚无 |
| synthetic completed / post-call-failed / preflight-blocked vertical proof 的 exact 输入与输出、独立 replay result pins | 尚无 |
| Core no-Skill/direct Tool、legacy compatibility 与独立 negative evidence 的 test IDs / CI artifacts | 尚无 |
| 验证目标 base/head/target、CI run / plan binding | 尚无 |
| Execution 与 Evaluation owner 的 exact-candidate R2 review | 尚无 |

Gate record 可随 implementation PR 准备与审查；SATISFIED 只在对应实现与审核证据合入后生效。
evidence record 使用其已接受的原始 identity/path/hash，不用日期或作者的 PASS 布尔值代替。
Gate 的 bounded scope 是 Skill-bearing actual facts 与独立 execution closeout；失败 replay 仍须按生命周期
解释，不能变成成功或 overlay equality。Gate 本身不授予生产 Skill admission、M6 baseline readiness、
科研有效性、Task/Claim/Human completion 或发布权限。

M5-007 同时 hard-depend M11-007 与此可审计 Gate，以保留实现身份和 evidence acceptance 两个条件。
M6-008 的独立 baseline Task 仍须 DONE；真实案例/live/admission 则继续约束 M5-004。
