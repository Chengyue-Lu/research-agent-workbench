# Risk Ledger

| ID | 风险 | 控制 | 状态 |
|---|---|---|---|
| REVIEW-001 | 第二人不可用导致永久等待 | 路诚钺确认不可用后可批准单次 exact-head 例外，无默认等待 | 维护者已接受；本 PR 落地 |
| REVIEW-002 | 缺少独立 reviewer 漏掉语义问题 | 具名风险承接、验证/回退记录、恢复后补审；阻断问题先解决 | 保留风险；AI review 不替代人类判断 |
| REVIEW-003 | 审核 bypass 同时绕过 CI 或直接写分支 | hard/review ruleset 分层；hard 无 bypass；review 只指定用户 PR-only | 以 rollout 回读为准 |
| REVIEW-004 | 一次决定用于新 head 或其他 PR | base/head、24 小时、一次使用、撤销和漂移失效；merge 前回读 | 人类流程控制；不宣称 GitHub 自动实施 |
| REVIEW-005 | 机制接受被误当成 PR 合并或发布批准 | 单次决定独立；main 另需 Human release decision 与全部 Gate | 当前没有具体 PR 的例外合并授权 |
| REVIEW-006 | Actor/规则漂移扩大权限，迁移中丢失保护 | 固定 User ID；先创建 hard 层再改 review 层；保留 before/after、失败停止 | 以 rollout 回读为准 |
