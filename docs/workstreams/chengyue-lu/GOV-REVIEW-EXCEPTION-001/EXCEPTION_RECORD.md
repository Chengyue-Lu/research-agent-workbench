# 单次审核例外操作记录

由路诚钺（`Chengyue-Lu`）审阅并明确决定；无需等待计时。此模板本身不构成授权。

```text
Decision: maintainer exception
PR: <URL>
Base SHA: <40-hex>
Head SHA: <40-hex>
Decider: Chengyue-Lu
Review request: <request/time/link>
Reviewer unavailable: <人工确认及原因>
Reviewed evidence: <exact-head CI / diff / verification links>
Open blockers: none（如有，先解决）
Residual risk and acceptance: <具体判断>
Rollback: <revert / repair PR 路径>
Decided at: <UTC timestamp>
Expires at: <最多 24 小时，或更早>
Authorization: 我批准以上 PR 在该 base/head 上使用一次维护者审核例外并合并。
Release decision: <main 必填本次具名发布决定；develop 写 not applicable>
```

执行前读取当前 PR 与 base/head、required checks、冲突、reviews/conversations 和两层 rulesets。
任一 pin/授权/门禁不满足即停止；不要为完成合并删除检查、改设 always bypass 或清空审查记录。
执行时锁定 expected head；核对 base freshness 后立即操作，发生竞态则重新回读。
合并后追加 merge SHA、执行人、时间、实际 base/head、有效规则回读和补审入口。

另一 owner 恢复后补审；补审不是先决等待条件。发现问题走修复或 revert PR，仍通过硬门禁。
