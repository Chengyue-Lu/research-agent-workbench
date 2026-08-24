# ADR-0019：将 Skill Evolution 作为可选 Maintainer 外环

状态：Proposed — pending R2 cross-owner review

日期：2026-08-25

## 背景

Phase B 已建立 `Capability Requirement → Capability Supply Report → Capability Resolution →
Resolved Capability Snapshot` 的结构契约，也建立了 Skill Need、Candidate/Evaluation 引用、Human
Admission 与 Lifecycle 的维护者侧演化基础。PR #33 明确把这些结果限定为 structural foundation；现有
checked-in fixture 仍是 `structural-replay`，不证明 Runtime consumer、真实 Provider 或 Skill 科研增量。

当前 repository validator 与 `load_validated_capability_snapshot()` 会从 `registry/`、`examples/` 递归收集
文档，并执行包含 Method→Skill Need、Lifecycle 和 Phase B Gate 在内的完整闭包。这适合仓库维护和历史
重放，但若把它当成 Runtime API，会使普通执行依赖 Skill Evolution 的内部对象，并让 no-Skill、direct
Tool 与 Adapter/Provider 路径承担不必要的 Skill 依赖。

同时，Runtime 遇到 capability gap 或执行失败，并不等于已经证明存在一个可复用、值得评测和准入的
Skill Need。若 Runtime 可以把失败自动升级为 Need、Candidate 或新版本，它就同时取得执行与演化权威，
破坏 Human Admission、权限边界和运行中 Snapshot 的可复现性。

## 决定

### 1. Capability-first Runtime 与可选 Maintainer Evolution 分成两个环

```text
Capability-first inner loop
Research Control / Capability Resolver
  Task / Method
    → Capability Requirement
    → explicitly supplied Capability Supply Report(s)
    → compare / qualify / resolve / select
    → Capability Resolution
    → frozen Resolved Capability Snapshot
    → Resolved Execution View

Execution Host / Runtime consumer
  exact frozen Snapshot + Resolved Execution View
    → Execution
    → actual facts / Trace / Receipt
    → bounded Capability Diagnostic or re-resolution request

Maintainer evolution outer loop
Maintainer triage
  → Skill Need
  → Candidate
  → Trial / Evaluation
  → named Human Admission
  → Lifecycle
  → immutable Release
  → SkillReleaseProjection
  → Capability Supply Report
```

Capability-first 内环必须能在 Skill Need、Candidate、Trial、Evaluation、Admission 和完整 Lifecycle 全部
缺席时闭合。no-Skill、direct Tool、procedure 与 Adapter/Provider 是一等供给路径，不创建占位 Skill 或
Skill Assignment。Capability Resolver 是唯一 Supply selection owner；Execution Host 不拥有第二套选择、
replanning、fallback 或 rebinding authority。

### 2. 两个环只通过两个有界单向端口连接

**Maintainer → Runtime：`SkillReleaseProjection`**

它是从已准入、不可变 Release 确定性派生的只读发布投影，不是第二套可写 Registry。未来最小字段类别为：

- exact Skill ID/version 与 release identity；
- content/package digest；
- declared capabilities、I/O、依赖与 compatibility；
- permission、data-egress 与 side-effect ceiling；
- 对指定用途和 scope 的 runtime eligibility；
- 最小 Release 与 named Human Admission provenance。

投影明确排除 Need 正文、Candidate、Trial/Evaluation 结果、评分指标、审议过程与完整 Lifecycle 历史。
Runtime-side catalog 可以从投影构造 Skill 类型的候选 Capability Supply Report；是否选择该 Report 仍由
Capability Resolver 决定。Execution Host 只消费冻结 Snapshot 与 Resolved Execution View，不直接解析
Lifecycle。`SkillReleaseProjection` 只属于 Skill-bearing Runtime Extension，不是 no-Skill、direct Tool、
procedure 或 Adapter/Provider Core 的全局输入。

**Runtime → Maintainer：`CapabilityDiagnostic`**

Runtime 可以产生有界事实，例如 Task/Mode/Action/Requirement、Snapshot/Release 引用、失败类别、脱敏
symptom/checker reference 与 privacy/consent 状态。Diagnostic 默认只保存在本地，不自动上传，不是 Skill Need，也不能触发
Candidate、Trial、Promotion、Release 或安装。只有具名 Maintainer 完成单独 triage 后，才可按正式发布
流程提出或修订 Skill Need。

### 3. 权威边界

| 参与方 | 可以 | 不可以 |
|---|---|---|
| Research Control / Capability Resolver | 接收显式候选 Supply Reports；在既有 ceilings 内 compare、qualify、resolve、select；生成新的 Resolution 与 Snapshot revision，供上游 View producer 按 frozen selection 生成 Resolved Execution View | 自动排序或 fallback；创建 Need/Candidate；扩大 permission/data-egress/side-effect ceiling；把 ambiguous 伪装为 selection |
| Execution Host / Runtime consumer | 消费 exact frozen Snapshot 与 Resolved Execution View；执行已冻结调用；报告 actual facts；记录 Trace、Receipt、bounded Diagnostic 或 re-resolution request；在不改变 Capability/Supply binding 时进行非语义执行调度 | 自行重新选择 Supply；把 Supply A 静默替换成 Supply B；在当前 Snapshot/View 内 rebind；automatic fallback；以“局部重规划”修改冻结执行输入；创建 Need/Candidate；执行 admission/promotion；改写 Release/Lifecycle；扩大权限或修改当前 Task/Method/Claim/Gate/Snapshot |
| Maintainer Evolution | 维护 Need；隔离地 trial/evaluate Candidate；由具名人类决定 admission；发布不可变 Release 与投影 | 控制当前执行；回写运行中的 Task/Method/Claim/Gate/Snapshot；以 eligibility 或 metadata 授予权限 |
| Release metadata | 声明 supply capability、依赖、compatibility 和权限/副作用上限 | 取代 Task/Profile/DataPolicy/Host authority，或把 ceiling 解释为 grant |

`Capability Gap != Skill Need`。gap、blocked 或 execution failure 最多形成 Diagnostic；不存在自动 Need 创建
或自动演化路径。

### 4. Snapshot 与执行授权分离

`runtime-execution` Snapshot 只表示供给闭包具备进入 Topic 4 继续准入的结构资格。它不是最终 Provider
binding、permission grant 或 execution authorization。`Resolved Execution View` 仍须冻结 exact
Provider/Adapter/Model/Runtime/Host、external pin、freshness，以及 Task、Profile、可选 Skill、DataPolicy
与 Host policy 的权限交集。

供给、Release 或 Registry 变化不能静默改变运行中的 Snapshot。Execution Host 检测到当前供给失败或
变化时，只能报告 bounded Diagnostic / re-resolution request；需要替换供给时必须走完整上游流程：

```text
Execution detects failure/change
  → bounded Diagnostic / re-resolution request
  → Research Control / Capability Resolver
  → new Capability Resolution
  → new Snapshot revision
  → new Resolved Execution View
  → Execution Host
```

当前 Snapshot/View 内不存在 Supply 替换、rebinding 或 automatic fallback seam。

### 5. 两种验证边界

- `maintainer-full`：保留当前 repository-wide Need/Lifecycle/Gate 闭包、发布身份检查和历史重放；v0.1
  Method→Need closure 属于此 profile。
- `runtime-bundle`：未来只接受显式 closure manifest 和最小传递闭包；禁止把目录作为隐式输入、禁止
  `rglob(registry, examples)`、禁止导入 Need/Candidate/Evaluation/Lifecycle validator，并允许零 Skill；
  Release Projection 只在 manifest 明确请求 Skill-bearing extension 时出现。

现有 `load_validated_capability_snapshot()` 归类为 `maintainer-full` 的仓库结构验证 helper，不是最终
`runtime-bundle` API。Issue #35 只冻结这两个 profile 的语义与验收，不在本 ADR 中新增 Schema 或代码。

### 6. 兼容边界

- Method Resolution v0.1、既有 `skill_need_refs`、Skill Need Registry 和 Lifecycle v2 原字节保持不变；
- 它们继续用于 `maintainer-full`、发布审计与历史重放；
- Runtime bundle Core 通过 Capability Requirement、Supply Report 与 Snapshot 闭合，不递归解引用 Method
  的 Skill Need；只有 Skill-bearing extension 额外消费发布投影；
- 既有 Skill Supply→Lifecycle 引用只形成 Maintainer 侧结构资格，不能成为新的 Runtime 依赖。

## 后果

优点：

- Runtime 可以独立部署 no-Skill/direct Tool/Adapter 路径；
- Topic 4 Core 只依赖 Runtime Bundle/Profile 与已接受的 supply-neutral 契约，不被 Skill 发布机制阻塞；
- Skill 治理历史不再进入普通执行读取面，减小上下文、隐私和供应链暴露；
- 发布身份、hash 与最小 provenance 仍可审计；
- 执行失败与产品演化之间保留具名人类 triage，避免自批准和在线语义漂移。

代价：

- Topic 4 需要新增 Runtime bundle/profile 和 supply-neutral execution binding；
- Skill 新绑定需要独立的 Release Projection publisher 才能启用；
- `maintainer-full` 与 `runtime-bundle` 必须分别测试，不能继续用一个全仓 loader 冒充两个消费者。

## 实施顺序

1. ADR-0019 与相关稳定/实现文档完成 R2 cross-owner acceptance；
2. 实现 Runtime Bundle/Profile；这是 Topic 4 Core 的 Issue #35 前置；
3. Runtime Bundle/Profile 稳定后，Topic 4 Core 可以为 no-Skill、direct Tool、procedure 与
   Adapter/Provider 实现 supply-neutral Resolved Execution View，不等待 Skill 发布机制；
4. Skill Release Projection/Publisher 作为独立 Skill Runtime Extension 实现，可与 Topic 4 Core 并行；
5. 只有 Projection contract 已接受且 exact-pin validation 可用后，才启用 Skill-bearing Runtime binding；
   Projection 缺失或不匹配时只对 Skill new-binding fail closed，禁止回退读取完整 Lifecycle；
6. Capability Diagnostic/feedback bridge 等待 Failure/Trace 与 privacy 语义稳定，保持 PARKED，不阻塞
   Topic 4 Core。

## 非目标

本 ADR 不新增或修改 Method Resolution、Skill Need、Lifecycle、Capability Snapshot Schema，也不实现
Release service、中央 Registry、数据库、telemetry、provider/model routing、automatic fallback、自动安装/
升级、Candidate 生成或本地自学习。

## Informative evidence

以下材料只作为设计类比，不引入外部项目 ontology，也不替代本项目的 Authority Matrix：

- [Kubernetes controller pattern](https://kubernetes.io/docs/concepts/architecture/controller/) 将不同 desired/current state 交给有界控制环，支持避免单体、互相纠缠的 controller；
- [Open Policy Agent](https://www.openpolicyagent.org/docs) 区分 policy decision 与 enforcement，支持“发布声明不能自行授予执行权限”的边界；
- [OCI Content Descriptors](https://github.com/opencontainers/image-spec/blob/main/descriptor.md?plain=1) 与 [TUF metadata roles](https://theupdateframework.io/docs/metadata/) 展示 digest-pinned content identity 和 snapshot/target metadata 的消费模式；
- USENIX Security 2019 的 [in-toto](https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias) 支持用最小、可验证 provenance 连接维护链与消费者；
- NeurIPS 2023 的 [Toolformer](https://papers.nips.cc/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html) 说明工具选择可以作为模型执行能力独立研究；本文仅据此采用 capability-first 接口，不从论文推导 Skill admission 权威。

检索日期：2026-08-25。外部材料为非规范证据；规范结论只来自本 ADR、项目契约与具名 R2 审查。

## 接受条件

- 路诚钺确认 Capability/Skill、Need/Evaluation/Admission 语义及保留权威；
- 黄毅确认 Runtime 读取面、Provider/Adapter/API 责任和 Topic 4 接口未被 Maintainer 外环侵入；
- 两位 owner 均确认 eligibility、Snapshot 和 Release metadata 不构成执行授权；
- 两位 owner 均确认 Capability Resolver 是唯一 Supply selection owner，Execution Host 不能在冻结输入内
  重新选择、rebind 或 fallback；
- 两位 owner 均确认 Skill Release Projection 只 Gate Skill-bearing path，不 Gate Topic 4 Core；
- 对抗性证据证明 Runtime 概念主链可在 Evolution 对象完全缺席时闭合。
