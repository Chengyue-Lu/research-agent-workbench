# GOV-V2-STAGE-CLOSURE

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 风险：R2 authority / governance
- Audit ID：`GOV-V2-STAGE-CLOSURE`
- 基线：`develop`
- 分支：`agent/governance-v2-stage-closure`

## 目标

本阶段补齐 authority-sensitive 路径的 R2 自动分类，把已发布 identity 的不可变约束从 Mode Action
扩展到 Research Mode、Decision Authority Matrix 与 Research Mode Migration，并允许同一 Stage PR
在不改写 Task 定义的前提下按 dependency DAG 原子完成已声明 Task 链。

## 边界

本阶段只修改治理 policy、治理检查、对应测试和开发规范；不实现研究运行时、Capability binding、
Provider/Adapter、Recovery 或多 Agent 调度。仍保留 Governance v2 的轻量原则：不要求人工 base SHA、
reviewer 字段、所有 PR 的 workstream、task-closeout PR、stale-base ERROR 或全局 CODEOWNERS wildcard。

## 验收

- authority 协议、Registry、Schema 与实现说明自动达到 R2；实现文档和 STATUS 至少 R1；
- 四类 published identity 同版本改写失败，新版本追加通过；
- 已声明且定义未修改的依赖链可在一个 Stage PR 中拓扑闭合，每个 DONE Task 有具名证据；
- 缺失依赖、未声明变化、DONE 改写和证据缺失继续失败；
- 治理单元测试与仓库完整测试通过。

风险控制见 [RISK_LEDGER.md](RISK_LEDGER.md)，验证结果见 [VALIDATION.md](VALIDATION.md)。
