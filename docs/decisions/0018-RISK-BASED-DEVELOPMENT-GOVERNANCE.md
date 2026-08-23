# ADR-0018：基于风险的开发治理与共享真值边界

状态：Proposed — pending R2 cross-owner authority review
日期：2026-08-23

## 背景

上一版仓库治理成功保护了 `develop/main` 拓扑、DONE Task、Task definition 和 owner authority，
但同时把 workstream、base SHA、跨 owner review、Risk Ledger、History 和独立 closeout 强制到每个
PR。机器已经知道的事实被要求人工复制，普通维护与共享契约承担相同流程，导致 AI 开发频繁因
低信息密度元数据和 stale base 重跑。

需要保留 fail-closed 的共享真值边界，同时让隔离分支内的普通实现采用最低充分过程。

## 决策

采用原则：

> **Hard authority, adaptive workflow.** Governance constrains what may become shared project truth,
> not how an agent must perform ordinary work inside an isolated development branch.

1. 保留 `feature → develop → main`、同仓库 release、DONE immutable、Task definition 分权、具名
   owner、CI 与 authority/data/permission/runtime 边界；
2. PR class 只保留 `feature / task-definition / release`；feature 可以在验证与 owner 判断下完成 Task，
   不再建立独立 `task-closeout`；
3. 使用 `R0 / R1 / R2`。治理器从 PR 声明和 changed paths 推导
   `effective_risk = max(declared, inferred)`，低报自动升级而不是因分类失误立即失败；
4. R0 只需 PR+CI；R1 增加 cross-owner review；R2 增加 authority basis、adversarial evidence、
   owner-matched workstream 与 Risk Ledger；
5. PR 元数据不再复制 base SHA 或 reviewer；workstream、Risk Ledger 与 History 按风险和复杂度触发；
6. Task 状态采用显式有限状态机，feature 可以在同一 head snapshot 中完成当前 Task 并激活依赖已
   `DONE` 的后继 Task；DONE 行继续终态不可变；
7. 治理器输出 `INFO / WARNING / ERROR` 及原因/补救要求，只有 ERROR 阻断；stale base 本身降为
   WARNING，真实冲突或共享契约不兼容仍阻断；
8. 策略数据放入 `.github/governance-policy.json`；CODEOWNERS 删除全局 `*`，只覆盖敏感表面；
9. 紧急变更仍走正常拓扑并保留 safety/authority gate，只允许压缩非关键过程材料。

## 权威边界

机器只判断结构资格、路径最低风险、状态转换、引用和证据字段是否存在。它不能证明科学完成、
方法适用或 authority decision 正确。具名 owner 对 Task completion 作判断；R1/R2 的另一位 owner
对共享契约或 authority boundary 作明确审查；GitHub ruleset 执行远端合并保护。

## 后果

- R0 maintenance 可以 `Task ID(s): none`、`Workstream: none`，不等待跨 owner；
- Schema/Registry/public contract 自动至少 R1；治理、架构及已知 Method/Claim/Gate/permission/
  data-policy 表面自动 R2；语义无法仅凭路径判定时，PR 的 authority declaration 与 cross-owner
  review 构成补充，不把路径分类器伪装成完备语义证明；
- R1 使用 CODEOWNERS 的路径覆盖会对同文件内的内部重构产生保守 false positive；在公共与内部
  模块进一步拆分前接受该成本，不能为减少 review 静默降低 shared-contract 保护；
- Governance v2 自身是 R2，只有代码、负面测试、文档、cross-owner authority review 和 ruleset
  rollout 全部闭合后才能成为已生效的共享政策。
