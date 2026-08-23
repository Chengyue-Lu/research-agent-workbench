# GOV-V2-001 Risk-based Development Governance

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 审查：R2，必须由另一位 accountable owner 作 authority review
- Audit ID：`GOV-V2-001`
- 基线：`develop@5991cafdb7f536cd7b871508de9055d02b558728`
- 分支：`governance/v2-risk-based-merge-boundary`
- 状态：implementation；未审查、未合并、远端 ruleset 未修改

## 目标与非目标

目标是在不削弱共享真值硬边界的前提下，把仓库开发治理改为风险比例化：三种 PR class、三种风险、
三种 Finding；删除独立 closeout、人工 base SHA 和全局 CODEOWNERS；实现 Task 状态机、依赖闭合、
风险自动升级、条件 workstream/Risk Ledger 与可解释输出。

本分支不修改研究对象运行时语义，不替代 Method/Claim/Human Gate authority，也不在政策合并前
写远端 ruleset。PR #25 的历史事实不重写；PR #26 的 Action 契约阻塞项在其原分支独立修复。

## 输入与边界

- `GOV-V2-SPEC-20260823`：2026-08-23 获取的私有治理规格，SHA-256
  `6bdcc987236e51af1f7dc01906588d5a5ca987b90e779991e731bfc21ff293bf`；原文不提交；
- PR #25 已合并的治理代码、文档与 rollout 记录；
- 当前 `.github`、`docs/DEVELOPMENT.md`、workstream/history 约定和 governance tests。

写入限于治理 policy/script/template/CODEOWNERS、对应测试、ADR、开发治理文档和本 workstream。
GitHub ruleset 是合并后的外部 rollout，不由未接受分支抢先改变。

## 证据与停止条件

- [风险台账](RISK_LEDGER.md)
- [验证记录](VALIDATION.md)
- [远端 rollout](ROLLOUT.md)
- [ADR-0018](../../../decisions/0018-RISK-BASED-DEVELOPMENT-GOVERNANCE.md)

停止条件：规定的 R0/R1/R2、Task、dependency、topology、warning、template 与 CODEOWNERS 正反矩阵
通过；文档不再把旧 closeout/全局 review 作为当前政策；形成跨分支 handoff。未经 R2 审查不合并，
未经合并和 required-check 可用性验证不修改远端 ruleset。
