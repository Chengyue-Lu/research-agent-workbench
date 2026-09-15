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

## Historical implementation candidate evidence

以下候选已收到 [PR81 review](REVIEW-REPAIR.md)。其 one-stage post-call proof 是修复前的历史证据，
原始归档字节保留；它不再作为当前实现验收证据，也不替换上方 accepted evidence 或 Gate 状态：

- implementation commit：`7b3405189e06210cae6552b0eb7699b049e14d73`，基于
  `develop@0bebafd81f0116a8269c63ac97378038a1eb2a5d`。
- extension identity：`skill-execution@1.0.0`；四种 Schema、validator、producer 与 fixture 的
  repo-relative source path/hash 见
  [vertical proof](../../../../work/M11-007/A-20260915-002/checks/vertical-proof.json)。
- proof SHA-256：`eeb86f824c398885df181e36d9e84c02bc3f3294e491da5649518a4114a6d312`。
  四个 case 分别保留 completed-with-tool、failed-model、failed-projection、preflight-blocked
  的全部输入与输出 pins，并记录 isolated-process replay result。
- [开发 Attempt](../../../../work/M11-007/A-20260915-002/README.md) 为 delayed/gapped
  `safe-paused` archive；运行样例各有独立 use-boundary Trace。
- implementation commit 的 Skill/documentation focused 37 PASS；27 项 Skill 正反验收包含
  缺事实、调用后补写、Host/Trace 联合改写、Projection identity 漂移和 subject closure 反例。
  最终 base/head/CI plan、full/coverage/package/repository/governance 与双方 review pins 留在实现 PR，
  接受后才更新上方 accepted evidence。
