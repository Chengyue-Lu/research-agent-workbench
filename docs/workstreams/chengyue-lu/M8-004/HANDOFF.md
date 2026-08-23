# M8-004 stacked implementation handoff

## 当前定位

- 分支：`agent/m8-004-mode-v02-migration`；
- parent：PR #30 head `732390a284974208ded0588411af87ecf27482ff`；
- shared base：本开发段建立时的 `develop@51c8607`；
- 状态：实现、文档与本地验证完成；未创建面向 `develop` 的 PR；
- 合并门槛：PR #30 必须先完成审查并进入 `develop`。

接手者应以远端分支 tip 作为完整交付 head，不要从工作流文档复制一个过期短 hash。

## 已形成的接口

1. Research Mode Schema 同时接受互斥且 fail-closed 的 v0.1/v0.2 形状；
2. v0.1 Mode、Action v1 与历史 Method Resolution 保留原路径和解释；
3. v0.2 Mode 使用八个 `action-id@2.0.0` 引用，不再推荐 Skill；
4. Action Registry append-only 增加 16 个 v2 文档，并精确拥有 `mode-id@0.2.0`；
5. 两个 migration record 固定 source/target/action ref、仓库路径、raw-byte SHA-256 与实现版本；
6. 显式迁移函数与 validator 对未知版本、hash/path/ref 漂移、字段遗漏、映射重复或不闭合均阻断。

实现说明见 [`RESEARCH_MODE_MIGRATION.md`](../../../implementation/RESEARCH_MODE_MIGRATION.md)，验证数字见
[`VALIDATION.md`](VALIDATION.md)，风险与非目标见 [`RISK_LEDGER.md`](RISK_LEDGER.md)。

## 不得误读为已完成的内容

- 共享 `docs/TASKS.md` 中的 M8-004 未被此堆叠分支激活或完成；
- 历史 Method Resolution 未迁移到 v0.2；
- 没有 Capability、Skill、Tool、Model、Provider、API 或 Runtime binding；
- 没有 Decision Authority、Resolved Execution View、Method Trace 或 M8-005 实现；
- 结构迁移通过不等于真实研究质量或成本净收益得到证明。

## 依赖落地后的续接顺序

1. 获取 PR #30 合并后的最新 `develop`，核验它确实包含本分支 parent；
2. 阅读届时的 `docs/TASKS.md`、Governance 与分支规范，形成合法的 M8-004 Task 状态变化；不得照抄
   当前堆叠开发状态；
3. 将本分支提交 rebase/cherry-pick 到新基线，解决共享文档漂移时优先保留新基线权威；
4. 重新生成所有受影响 raw-byte hashes，并运行完整 repository validation、308+ tests、coverage、
   Python matrix、wheel 与 clean-install smoke；
5. 以 R2 边界创建一个面向 `develop` 的正式 PR，获取跨负责人审查后才可合并；
6. 真实 forward case 与迁移历史 Resolution 若仍有价值，分别立项，不塞回 M8-004。

若 PR #30 被修改后合并而不是以当前 head 原样落地，先比较契约差异；不要机械重放本分支。
