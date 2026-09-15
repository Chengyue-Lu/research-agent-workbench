# GOV-REVIEW-EXCEPTION-001

- 责任人：路诚钺（`Chengyue-Lu`）；风险 R2；Audit ID：`GOV-REVIEW-EXCEPTION-001`。
- 基线：`f7a9715ed35787d3326283c22f834b1514c5c88c`；目标 `develop`；分支 `feature/review-maintainer-exception`。
- 输入：具名维护者 2026-09-14 明确接受单次例外；DEVELOPMENT、发布规范、CODEOWNERS、当前 main/develop rulesets 和 GitHub 官方 rules API。
- 状态：维护者已接受治理决定；实现、远端分层与验证证据通过独立 R2 PR 集成。

## 范围与输出

按 [ADR-0022](../../../decisions/0022-SINGLE-PR-MAINTAINER-REVIEW-EXCEPTION.md) 更新稳定协作规范、
Agent 合并约束、治理器的审核要求说明，以及 main/develop 的硬门禁和审核层配置。
使用既有 Audit ID 路径实施治理维护，canonical `TASKS.md` 不变，不建立产品 Task 或修改 M14 验收。

允许读取仓库治理文档、所列 CI/治理实现与测试、API 身份/规则/PR 回读；允许写入上述文档、治理器要求
文案、本 workstream 与 `work/GOV-REVIEW-EXCEPTION-001/`，以及 exact main/develop rulesets。
PR #78 保持独立；启用机制不授予任何具体 PR 的合并权。Runtime、release architecture、LICENSE、
Skill admission 和 M14-005 状态均不改变，本地 primary develop 保持原 HEAD 和 clean。

## 验证与停止条件

- 文档链接、既有治理/拓扑/Task/published-identity focused tests 和 repository validation；
- ruleset 请求与回读逐字段一致；hard layer 无 bypass，only-review layer 仅指定 User/PR-only；
- 负例拒绝 hard bypass、错误用户、always/exempt、缺 checks、错误 merge method 和审批漂移；
- 未合并任何实际 PR，未向受保护分支做破坏性 push 探测；仅声称已读取配置覆盖的远端保护。

完成条件：规则/文档/验证证据已落地，独立 R2 PR 可审查，main/develop tips 未改变。
合并任何具体 PR 时依[单次决定模板](EXCEPTION_RECORD.md)另行取得明确授权。
风险见 [Risk Ledger](RISK_LEDGER.md)，部署证据见 [远端记录](ROLLOUT.md)。
