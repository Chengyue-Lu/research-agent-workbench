# Capability Resolution and Snapshot Core

M9-005 在需求与执行之间固定单向关系：

```text
Capability Requirement
        ↓
Capability Supply Report(s)
        ↓ deterministic comparison at evaluated_at
Capability Resolution
        ↓ satisfied + exact selected report
Resolved Capability Snapshot
        ├─ structural-replay（Phase B fixture）
        └─ runtime-execution（供 Topic 4 继续准入的非 fixture 供给记录）
```

本阶段不建立全局供给 Registry，也不实现 Provider discovery、API session、Runtime consumer、自动
fallback 或模型路由。调用方必须显式提供候选 Report；低层 Provider conformance 不能自动证明高层科研
Capability Requirement。Research Control / Capability Resolver 是唯一 Supply selection owner；Execution
Host 不能在 Snapshot 或 Resolved Execution View 冻结后重新选择供给。

当前 `load_validated_capability_snapshot()` 会递归收集 repository 的 `registry/` 与 `examples/`，并调用
包含 Method→Skill Need、Lifecycle 和 Phase B Gate 在内的完整文档验证。它是 `maintainer-full` 仓库结构
验证 helper，不是最终 Runtime bundle API，也不能因名称中的 `validated` 被解释为执行授权。

## Supply Report

Report 只陈述一个供给的事实：

- exact implementation/component identity、version/hash；Provider/Model/Runtime/Host 的最终绑定由 Topic 4
  上游 Research Control / Resolved Execution View producer 另行冻结，Execution Host 只校验并消费；
- provided capability、supported I/O、produced artifacts、limits 与 known unknowns；
- 所需 permission、data-egress 与 side effects；这些是供给侧事实，不是最终执行授权；
- typed conformance artifact ref；evidence 必须绑定 artifact path/hash、kind/class、ID、implementation
  ref/version、capability、observation scope 与 result，Report 不得自报 evidence `status` 覆盖引用制品；
- scoped availability observation 与 `observed_at`；`valid_until` 可作为 producer metadata，但 Phase B
  不用当前时钟完成 Runtime freshness 准入。

Report 不能选择自己、放宽边界、持有 Method/fallback/Claim/Human Gate authority，不能保存凭据、价格路由
或隐藏 fallback。当前 checked-in 报告全部是 fixture，availability 只属于 `fixture-only`。

## Capability Resolution

Resolver 计算 capability、I/O、artifacts、permission、data-egress、side-effects、typed conformance、
availability 与 Skill runtime eligibility 十类检查。结果只有：

- 一个合格供给：`satisfied`；
- 无合格供给：`gap`；
- 多个合格供给：`ambiguous`，不得自动排序或 fallback；
- permission / egress / side-effect 越界：`blocked`。

Resolution 固定 `qualification` 和 `evaluated_at`。Repository validator 从引用 artifact 的真实 result、
identity、scope 与 capability 重新计算 checks/status/selection；Report 内字段不能覆盖引用证据。Resolution
不创建 Authority eligibility、permission grant 或最终 Runtime binding。

Capability Resolver 的 selection 不能由 Execution Host 再解释。多个合格候选继续是 `ambiguous`，或由
上游具名决定重新提供明确候选；Execution Host 不得自行排序、将 Supply A 换成 Supply B 或把失败解释为
automatic fallback。

## Snapshot 两级资格

所有 Snapshot 固定 exact Task、Method Resolution、Requirement、Resolution、Supply Report、Supply identity、
三类 Supply-side boundary facts 与 conformance refs。Task ref 必须与 Method Resolution 内的 Task
identity/revision/hash 一致。

### structural-replay

当前三条 fixture 全部属于此级：

- `supply_required_permissions`、`supply_data_egress`、`supply_side_effects` 与选中 Report 精确一致；
- 不含 Assignment、Agent Profile、最终 effective permissions、execution boundaries 或 Authority eligibility；
- `boundaries.execution_input: false`。

因此 fixture、no-Skill、尚无规范 Assignment 的 direct Tool 和 Adapter/Provider 不能被 Runtime 消费。它们只
证明 schema、hash、replay 与供给替换边界。

### runtime-execution

Phase B 只定义这一资格词汇与 fail-closed seam。形成该类 Snapshot 至少要求唯一 satisfied runtime
Resolution、非 fixture availability、与高层 Requirement 匹配的 `local-conformance` / `live-conformance`
typed evidence，以及全部 schema、未知字段、path/hash、identity 与 transitive closure 检查通过。

这仍不是最终执行授权。外部 Snapshot pin、执行时 freshness、account/host/region、精确
Provider/Adapter/Model/Runtime、credentials/quota、Task/Profile/Skill/Assignment 权限交集、DataPolicy preflight
和 side-effect enforcement 均由 Topic 4/M6 的上游 Resolved Execution View producer 完成；Execution Host
只校验并消费 exact frozen View。Phase B trusted loader 接受可选 external hash（提供时必须匹配同一批
解析字节），但不要求 `execution_at`。

## Skill Supply Extension

Lifecycle state 与旧 `skill_lifecycle_ref` / `runtime_eligibility_ref` 只服务 Maintainer 结构审计和历史
Resolution replay，不能授权 Runtime new-binding。即使调用方传入一个返回 true 的旧 Lifecycle callback，
`runtime-execution` comparison 仍保持 `skill-runtime-eligibility: unknown`。

M11-005/006 后，Runtime Skill Supply 必须改用 exact `skill_release_projection_ref`：

- ref、document path 与 raw SHA-256 必须命中一个 `SkillReleaseProjection`；
- projection 必须显式 `eligible + new-binding`，且所有 authority boundary 为 false；
- Supply implementation 与唯一 Skill component 必须等于 projection 的 Release identity/version/content hash；
- capability、supported I/O 必须等于 projection；附加 Tool component 只能来自 projection dependencies；
- Supply permissions（包括 optional `allowed_roots`）、data egress 与 side effects 可以进一步收紧，
  但不能超过 projection ceiling；projection 声明的 required Tool dependencies 必须全部成为 Supply
  component，optional Tool 只在实际绑定时出现；
- conformance、availability、limits 与 limitations 仍属于 Supply Report，不由 projection 伪造。

Capability Requirement v0.1 只比较 filesystem/network/external-write permission class；Supply 的 optional
`allowed_roots` 是后续 View 收窄事实。projection-backed Skill 必须显式携带 roots 并先证明其位于 Release
ceiling 内，View 再与 Task/Profile/DataPolicy/Host roots 做同一通用交集。非 Skill 旧 Report 未声明 roots
时仍使用 Task roots，因而 Core 行为不变。

这些检查只决定某一 Skill candidate 是否有资格进入既有 Capability comparison。Capability Resolver 仍是
唯一 selector；Projection 或 Report 都不能创建 permission、execution、fallback、Method、Claim 或 Human
authority。missing/stale/mismatch projection 只让该 candidate fail closed，不改变 Requirement 或其他 Supply。

完整 Lifecycle、Need、Candidate、Trial/Evaluation 与 Human deliberation 不进入 Runtime bundle。现有三个
legacy Skill 均无 production projection；空 projection index 不影响 no-Skill/direct Tool/procedure 与
Adapter/Provider Core。

## Consumer profiles

本契约定义两个不同消费者，不能再由同一个隐式目录扫描承担：

| Profile | 输入与闭包 | 允许读取 | 禁止行为 |
|---|---|---|---|
| `maintainer-full` | repository roots 与完整发布/历史闭包 | Method、Need、Lifecycle、Gate、fixtures | 把结构通过宣称为 Runtime authorization |
| `runtime-bundle` | 显式 closure manifest 与最小传递依赖 | Task/Method ref、Requirement、Reports、Resolution、Snapshot；仅 Skill-bearing extension 可含 Release Projection | 目录输入、`rglob(registry, examples)`、Evolution validator/import、隐式 fallback |

`runtime-bundle` 必须在 Evolution Registry 不存在时支持零 Skill no-Skill/direct Tool 路径。任一无关
Registry 文档损坏不得影响只引用显式 bundle 的执行解析。Profile、closure manifest 和 import-graph test
由后续 Topic 4 Task 实现；Issue #35 不新增 Schema 或 Python API。

## Resolved Execution View boundary

`runtime-execution` Snapshot 仍只是 Topic 4 的合格输入。上游 Research Control / Resolved Execution View
producer 必须另行冻结 external hash pin、execution-time freshness、exact Provider/Adapter/Model/Runtime/Host、
credentials/quota preflight，以及 Task、Profile、DataPolicy、Host policy 与 selected supply ceilings 的权限
交集；仅 Skill-bearing extension 加入可选 Skill/Assignment。Release metadata、Lifecycle eligibility、
Supply Report 和 Snapshot 均只能收紧或声明 ceiling，不能授予权限。Execution Host 只消费该 exact frozen
Snapshot/View，可以进行不改变 Capability/Supply binding 的非语义执行调度，但不能重新选择、rebind、静默
替换或 automatic fallback。

Supply、Release 或 Registry 更新不能改变运行中的 Snapshot。Execution Host 检测失败或变化时只能发出
bounded Diagnostic / re-resolution request；替换供给必须由 Capability Resolver 创建新的 Resolution 与
Snapshot revision，再由上游 View producer 按 frozen selection 创建新的 Resolved Execution View，最后
交给 Execution Host。完整边界见
[ADR-0019](../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md)。

## Replacement fixture

`examples/capability-resolution/` 的 direct Tool、Adapter/Provider，以及 Method `no-Skill` 对应的
`procedure` 三条 synthetic chain 都是 `structural-replay`。A/B replacement 保持 Task、Mode、Action、
Method、Requirement 和三类 Supply boundary facts 不变，只替换 exact Supply/Snapshot。它不证明真实
Provider 可用、Runtime 已实现或科研结果有效。
