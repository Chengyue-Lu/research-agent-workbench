# GOV-V2-STAGE-CLOSURE

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 风险：R2 authority / governance
- Audit ID：`GOV-V2-STAGE-CLOSURE`
- 基线：`develop`
- 分支：`agent/governance-v2-stage-closure`

## 目标

本阶段补齐 authority-sensitive 路径的 R2 自动分类，把已发布 identity 的不可变约束从 Mode Action
扩展到 Research Mode、Decision Authority Matrix 与 Research Mode Migration，并允许同一 Stage PR
在不改写 Task 定义的前提下按 dependency DAG 原子完成已声明 Task 链。`PARKED -> DONE` 仅限 R2，
且必须从本次由 `READY`、`IN_PROGRESS` 或 `BLOCKED` 进入 `DONE` 的 anchor Task 沿依赖边可达。

## 边界

本阶段只修改治理 policy、治理检查、对应测试和开发规范；不实现研究运行时、Capability binding、
Provider/Adapter、Recovery 或多 Agent 调度。仍保留 Governance v2 的轻量原则：不要求人工 base SHA、
reviewer 字段、所有 PR 的 workstream、task-closeout PR、stale-base ERROR 或全局 CODEOWNERS wildcard。

## 验收

- authority 协议、Registry、Schema 与实现说明自动达到 R2；实现文档和 STATUS 至少 R1；
- 四类 published identity 由 policy 声明；每个 PR 无条件比较 base/head 全集，删除、迁出、重定位或
  同版本改写失败，保留旧 identity 后追加新版本通过；
- R2 中已声明且定义未修改的完成集合，必须包含至少一个非 PARKED anchor；所有 PARKED 完成均从
  anchor 沿 completion DAG 可达，每个 DONE Task 有具名证据；
- R0/R1 的 PARKED 直达 DONE、独立或断连 PARKED 完成、缺失 anchor、依赖、声明、逐 Task 证据及
  循环 DAG 均失败；
- 治理单元测试与仓库完整测试通过。

风险控制见 [RISK_LEDGER.md](RISK_LEDGER.md)，验证结果见 [VALIDATION.md](VALIDATION.md)。
