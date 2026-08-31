# M11 Skill Runtime Activation

责任人：路诚钺（GitHub `Chengyue-Lu`）

风险：R2

PR 类型：`feature`（docs-only activation）

## 决定

本工作流只执行一个恢复决定：

```text
M11-005 PARKED → READY
M11-006 PARKED → PARKED
```

依据是 ADR-0019 已接受 optional Maintainer → Runtime `SkillReleaseProjection` seam，具名 owner 已决定现在
启动该 optional extension，且 M11-005 的 hard dependency M9-003 已为 DONE。该决定恢复合法施工入口，
不表示 M11-005 已实现、已验收或可以绕过 R2 review。

## 不变量

- 不修改 M11-005/006 identity、dependency 或 acceptance；
- 不把 M11-005 置为 DONE，也不提前激活 M11-006；
- no-Skill/direct Tool Core 不依赖 Skill projection；
- Projection 不授予 Supply selection、permission、execution、Claim 或 Human authority；
- Capability Resolver 继续是唯一 Supply selector；
- 不引入 fallback、re-selection、Skill-specific dispatcher/session 或 Topic 5；
- 不准入真实 Skill，也不把 synthetic fixture 解释为科研净收益。

## 后继集成 Gate

实现 PR 必须基于本决定合入后的最新 `develop`，并按通用 R2 module-level DAG 规则显式声明：

```text
M11-005 READY  → DONE
M11-006 PARKED → DONE
```

后继 M11-006 只有在 M11-005 先行闭合、两个 Task 各有独立 implementation slice/commit/evidence、完整
DAG 从 READY anchor 可达且相关跨 owner review 满足时，才能在同一 module-level PR 中原子完成。本 activation
PR 不预先认可任何既有分支实现。

## 验证与停止点

- `TASKS.md` 是唯一 Task status authority；M-series 与 Developer Architecture Map 只同步派生导航；
- ROADMAP 的 optional extension Gate 与 STATUS 的实现覆盖不因 activation 改写；
- 文档链接、Governance focused tests、repository validation 与 hosted CI 必须通过；
- activation PR 经正常 R2/docs review 合入后停止，再处理实现 PR 的 rebase 与验收。
