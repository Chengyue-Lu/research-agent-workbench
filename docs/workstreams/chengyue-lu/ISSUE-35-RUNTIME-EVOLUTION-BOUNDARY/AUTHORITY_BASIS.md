# ISSUE-35 Authority Basis

状态：Accepted；cross-owner architecture acceptance 已完成；final-state merge gate 由 PR #36 记录

## 1. 具名责任

| 责任人 | 保留权威 | 必须审查 |
|---|---|---|
| 路诚钺（`Chengyue-Lu`） | Capability/Skill vocabulary、Skill Need、Evaluation expectation、Admission、Lifecycle/Release semantics | Runtime 不得由 gap 自动产生 Need，不得以执行便利改变 Method/Claim/Gate/permission |
| 黄毅（`let778750-cpu`） | Provider/Adapter、API session、Runtime bundle/consumer、live conformance 与 API-specific tests | Maintainer 外环不得进入 Runtime 读取面或控制当前 execution；projection 必须足以实现 fail-closed binding |

Agent、Runtime、validator、PR 作者或模型都不是 authority holder。

## 2. 权限矩阵

| Actor / object | 可读 | 可写或决定 | 明确禁止 |
|---|---|---|---|
| Research Control / Capability Resolver | Task/Method refs、Requirement、显式候选 Supply Reports、既有 ceilings | 作为唯一 Supply selection owner 执行 deterministic compare/qualification/resolution/selection；生成新的 Resolution 与 Snapshot revision | 自动排序或 fallback；把 ambiguous 伪装为 selection；创建 Need；扩大 permission/data-egress/side-effect ceiling |
| Research Control / Resolved Execution View producer | exact Resolution/Snapshot、Task/Profile/DataPolicy/Host policy 与 execution identities | 按 frozen selection 冻结 exact View 和最终收紧交集 | 重新选择或替换 Supply；改变 Resolution；扩大任何 ceiling |
| Execution Host / Runtime consumer | exact frozen Snapshot/Resolved Execution View 与 exact artifacts | 执行已冻结调用；报告 actual facts；写 Trace/Receipt、bounded Diagnostic 或 re-resolution request；不改变 binding 的非语义执行调度 | 自行重新选择 Supply；Supply A→B 静默替换；当前 Snapshot/View 内 rebinding；automatic fallback；通过局部重规划修改 frozen input；读取完整 Evolution Registry；Need/Candidate/Evaluation/Lifecycle/Release mutation；Admission/Promotion；Task/Method/Claim/Gate/permission expansion |
| Maintainer Evolution | Need、Candidate、Trial/Evaluation refs、Admission、Lifecycle、Release | 隔离 trial/evaluation；具名 Human Admission；发布 immutable Release/Projection | 修改运行中的 Task/Method/Claim/Gate/Snapshot；把 eligibility 当成 authorization |
| Release publisher | 已接受 Admission/Lifecycle 与 immutable package | 确定性派生只读 projection | 建立第二套可写真值；省略或改写 package hash；授予权限 |

## 3. 决定规则

1. `Capability Gap != Skill Need`；只有具名 Maintainer triage 可以提出正式 Need。
2. `runtime_eligibility != execution_authority`；Release、Supply 与 Snapshot metadata 只能声明 ceiling。
3. 最终执行权限是 Task、Profile、DataPolicy、Host policy 与供给 ceilings 的收紧交集，任一输入不能单独放宽。
4. no-Skill/direct Tool/procedure/Adapter 路径不得创建 Skill Assignment 或依赖 Evolution Registry。
5. Skill path 只消费 exact version/hash 的发布投影；缺失、stale、mismatch 或 unsupported scope 一律 fail closed。
6. SkillReleaseProjection 只 Gate Skill-bearing path；Topic 4 Core 的 no-Skill/direct Tool/procedure/
   Adapter-Provider 路径不得等待该投影。
7. Supply/Release/Registry 变化必须由唯一 selection owner 产生新的 Resolution/Snapshot/View，不能改变正在
   运行的 frozen input。Execution Host 只能请求 re-resolution，不能原地 rebind 或 fallback。

```text
Execution detects failure/change
  → bounded Diagnostic / re-resolution request
  → Research Control / Capability Resolver
  → new Capability Resolution
  → new Snapshot revision
  → new Resolved Execution View
  → Execution Host
```

## 4. Cross-owner acceptance

路诚钺的接受只覆盖 Method/Capability/Skill 语义，不代替黄毅对 Runtime 可实现性、Provider/API 边界和
读取闭包的判断。黄毅的接受只覆盖 Runtime 侧契约，不授权其改变 Need/Evaluation/Admission 或科学权威。

两位 owner 对上述 ceiling 的 architecture acceptance 已完成；ADR-0019 已从 `Proposed` 收口为
`Accepted`。接受证据为 [PR #36 architecture APPROVE](https://github.com/Chengyue-Lu/research-agent-workbench/pull/36#pullrequestreview-5012526099)，绑定 `c09dd69d9a8f7d1c4f70c93e6909a61e72d52e79`。
本次 final state diff 仍须由黄毅复核，避免状态同步重新引入 Runtime ownership 漂移；该复核不修改上方
authority matrix。
