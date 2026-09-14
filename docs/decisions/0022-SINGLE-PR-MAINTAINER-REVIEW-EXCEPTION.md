# ADR-0022：Reviewer 不可用时的单次维护者审核例外

状态：Accepted by named maintainer；通过本 R2 PR 集成。
日期：2026-09-14。
决定人：路诚钺（`Chengyue-Lu`）；Audit ID：`GOV-REVIEW-EXCEPTION-001`。

## 问题与依据

仓库由两位 owner 维护。R1/R2 cross-owner review 与远端 Code Owner requirement 使另一位
reviewer 长期不可用时缺少结束等待的路径；PR 作者不能提交自己的 GitHub approving review。
2026-09-14 路诚钺明确接受 PR 作者以具名维护者身份承担单次例外责任，并指定可人工确认另一
reviewer 暂无空闲、由自己一侧批准。按其允许的选项采用无默认等待时间。

## 决定

- 正常 cross-owner review 保留；另一 reviewer 不可用时，由路诚钺逐 PR、逐 exact base/head
  明确批准 `maintainer exception`，PR 作者可以承担此责任。其他 owner、Agent 或自动计时不获得该权力。
- 无默认等待时间；决定最多有效 24 小时、一次使用，base/head 漂移、撤回或新阻断问题即失效。
- required CI、PR topology、conversation resolution、禁直推/force/delete 及其他 authority/readiness
  Gate 独立保留。已有 substantive changes-requested 先解决，不能转成缺席例外。
- main 审核例外另需具名 Human release decision，不能激活 dormant curated topology 或代替 M14-005 前置条件。
- GitHub 每个分支分为无 bypass 的硬门禁层和审核层。审核层只向用户 `140945476` 授予
  `pull_request` bypass，不扩展到整个 admin 角色；原有审批数、Code Owner 和 stale/last-push 规则保留。
- GitHub 只强制两层技术边界；单次记录、有效期和风险承接由具名人类执行，不宣称原生支持逐 SHA 授权。

## 权衡与验证

例外可解除 reviewer 不可用造成的持续阻塞，但减少第二人的独立判断。通过明确责任、当前候选的
验证/风险/回退记录和事后补审控制这项风险，不将 AI review 记作人类批准。
新增硬门禁须先启用回读，再将现有 ruleset 缩减为审核层并增加指定用户的 PR-only bypass；回读各层
完整配置、effective rules、权限身份与 branch tips。配置失败保留硬门禁并停止下一步。
正式记录见 [workstream](../workstreams/chengyue-lu/GOV-REVIEW-EXCEPTION-001/README.md)。

## 来源

- [GitHub ruleset layering](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub rules REST API：User actor 与 pull_request bypass](https://docs.github.com/en/rest/repos/rules)
- [GitHub review authority](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request)
