# Resolved Execution View Core

M11-002 将一个已验证的 Runtime Bundle 与显式、hash-pinned 的 Profile、DataPolicy、Host policy 和
Execution Binding 收敛成最终冻结的执行契约：

```text
Runtime Bundle（frozen Supply selection）
  + exact Agent Profile
  + exact DataPolicy
  + exact Host policy
  + exact Provider / Adapter / Model / Runtime / Host binding
  + explicit execution_at
  ↓ deterministic preflight and intersection
Resolved Execution View
```

View producer 是 frozen-selection consumer，不是第二个 Capability Resolver。它不比较候选，不把 Supply A
换成 B，也不执行调用。

## 输入契约

`produce_resolved_execution_view()` 接受一个 `ValidatedRuntimeBundle` 和四个 `PinnedExecutionInput`：

- Agent Profile：identity/version/path/hash 必须与 Task 的 `agent_profile` 一致；
- DataPolicy：声明 permission、data-egress、side-effect、budget ceiling 和有效期；
- Host policy：声明同类 Host ceiling 和有效期；
- Execution Binding：固定 Provider、Adapter、Model、Runtime、Host 的 exact ref/version/config digest，并
  必须保留 Snapshot 已选择的 Supply Report identity。

调用方还必须提供 Runtime Bundle manifest 的 external SHA-256 pin 和显式 `execution_at`。producer 不读取
环境变量、不扫描 Registry，也不使用当前时钟替代该时间点。

```python
from research_workbench.execution import (
    PinnedExecutionInput,
    produce_resolved_execution_view,
)

view = produce_resolved_execution_view(
    bundle,
    agent_profile=PinnedExecutionInput("view/profile.yaml", profile_sha256),
    data_policy=PinnedExecutionInput("view/data-policy.yaml", data_policy_sha256),
    host_policy=PinnedExecutionInput("view/host-policy.yaml", host_policy_sha256),
    execution_binding=PinnedExecutionInput("view/binding.yaml", binding_sha256),
    execution_at="2026-08-26T00:00:00Z",
    view_id="VIEW-001",
    expected_bundle_sha256=bundle_manifest_sha256,
    schema_root="schemas",
)
```

## 确定性收敛

View 精确引用 Runtime Bundle、Task、Method Resolution、Capability Resolution、Snapshot、selected Supply
Report、Profile、两份 policy 与 Execution Binding，并冻结：

- Provider / Adapter / Model / Runtime / Host ref、version、content/config hash；
- Supply availability observation、Supply/DataPolicy/Host policy validity windows；
- Task、Profile、Supply、DataPolicy、Host policy 的最严 permission intersection；
- Supply、DataPolicy、Host policy 的 data-egress 与 side-effect intersection；
- Task、DataPolicy、Host policy 的最小 budget ceilings；
- Task required outputs、completion checks、safe-pause 与 stop constraints。

文件系统和网络采用显式有序 ceiling；write roots 采用路径包含关系求交并保留更窄的可写根。Data egress
取 allowed payload 交集与 forbidden payload 并集；side effects 取 allowlist 交集；budget 对每个已声明维度
取最小值。无法形成合法交集即 fail closed。

## Freshness 与供给资格

`execution_at` 必须同时位于 Supply availability、DataPolicy 和 Host policy 的窗口内。selected Supply 必须
仍为 `available`，且 explicit closure 内的 typed evidence 必须：

- 为 `local-conformance` 或 `live-conformance`；
- `result: pass`；
- implementation identity/version 与 Supply 一致；
- 覆盖当前 Capability Requirement；
- observation scope 与 Supply availability scope 一致。

失败只产生 preflight block。若需更换 Supply，调用方必须回到 Capability Resolution，发布新的
Resolution→Snapshot→View；producer 不做 local fallback。

## Authority boundary

View 是 Host 后续要消费的 final frozen contract，但它自身仍不是 permission grant 或 Human Decision。
`boundaries` 固定声明其不拥有 Supply selection、automatic fallback、permission grant、Method decision、
Claim effect、Human decision 或 execution。effective constraints 只能收紧上游已声明 ceiling，不能创造新
authority。

M11 Core 不依赖 SkillReleaseProjection、Need、Evaluation 或 Lifecycle。M11-005/006 的 Skill extension 只能
增加一种合法 Supply 来源，不能改变该 View 的 supply-neutral 语义。

## 当前停止点

M11-002 只生成并 schema-check View mapping；不写执行文件、不解析凭据、不调用 Provider、不产生 Trace 或
Receipt。M11-003 才实现只消费 exact View 的 Thin Execution Host。
