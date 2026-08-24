# ISSUE-35 Authority Basis

状态：Proposed；等待路诚钺与黄毅的 R2 cross-owner acceptance

## 1. 具名责任

| 责任人 | 保留权威 | 必须审查 |
|---|---|---|
| 路诚钺（`Chengyue-Lu`） | Capability/Skill vocabulary、Skill Need、Evaluation expectation、Admission、Lifecycle/Release semantics | Runtime 不得由 gap 自动产生 Need，不得以执行便利改变 Method/Claim/Gate/permission |
| 黄毅（`let778750-cpu`） | Provider/Adapter、API session、Runtime bundle/consumer、live conformance 与 API-specific tests | Maintainer 外环不得进入 Runtime 读取面或控制当前 execution；projection 必须足以实现 fail-closed binding |

Agent、Runtime、validator、PR 作者或模型都不是 authority holder。

## 2. 权限矩阵

| Actor / object | 可读 | 可写或决定 | 明确禁止 |
|---|---|---|---|
| Research Runtime | Task/Method refs、Requirement、Supply Reports、Resolution、Snapshot、可选 Release Projection | 冻结边界内选择供给、局部重规划、Trace/Receipt、bounded Diagnostic | Need/Candidate/Evaluation/Lifecycle/Release mutation；Admission/Promotion；Task/Method/Claim/Gate/permission expansion |
| Maintainer Evolution | Need、Candidate、Trial/Evaluation refs、Admission、Lifecycle、Release | 隔离 trial/evaluation；具名 Human Admission；发布 immutable Release/Projection | 修改运行中的 Task/Method/Claim/Gate/Snapshot；把 eligibility 当成 authorization |
| Release publisher | 已接受 Admission/Lifecycle 与 immutable package | 确定性派生只读 projection | 建立第二套可写真值；省略或改写 package hash；授予权限 |
| Capability Resolver | Requirement、显式 Supply Reports、既有 ceilings | deterministic qualification、satisfied/gap/ambiguous/blocked、冻结 selection | 自动 fallback；创建 Need；扩大 permission/data-egress/side-effect ceiling |
| Execution Host | frozen Snapshot/Execution View 与 exact artifacts | 执行已授权调用并报告实际事实 | 读取完整 Evolution Registry；按 active/latest 静默更新；改写冻结 View |

## 3. 决定规则

1. `Capability Gap != Skill Need`；只有具名 Maintainer triage 可以提出正式 Need。
2. `runtime_eligibility != execution_authority`；Release、Supply 与 Snapshot metadata 只能声明 ceiling。
3. 最终执行权限是 Task、Profile、DataPolicy、Host policy 与供给 ceilings 的收紧交集，任一输入不能单独放宽。
4. no-Skill/direct Tool/procedure/Adapter 路径不得创建 Skill Assignment 或依赖 Evolution Registry。
5. Skill path 只消费 exact version/hash 的发布投影；缺失、stale、mismatch 或 unsupported scope 一律 fail closed。
6. Supply/Release/Registry 变化必须产生新的 Resolution/Snapshot/View，不能改变正在运行的 frozen input。

## 4. Cross-owner acceptance

路诚钺的接受只覆盖 Method/Capability/Skill 语义，不代替黄毅对 Runtime 可实现性、Provider/API 边界和
读取闭包的判断。黄毅的接受只覆盖 Runtime 侧契约，不授权其改变 Need/Evaluation/Admission 或科学权威。

ADR-0019 只有在两位 owner 对上述 ceiling 无未解决异议时才能从 `Proposed` 改为 `Accepted`。状态变更
后的最终文档 diff 仍须由黄毅复核，避免接受后再引入 Runtime ownership 漂移。
