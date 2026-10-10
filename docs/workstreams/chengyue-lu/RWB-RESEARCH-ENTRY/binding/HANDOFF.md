# ENTRY-C 控制冻结 caller 交付

2026-10-07；隔离分支候选，基线 `d3c4d23`。Agent Profile：bounded capability-freeze caller worker；required-Skills=[]。完成限定 caller 与自身离线验证，未建立真实来源/API资格或正式接受。

## 实际接口

[binding.py](../../../../../src/research_workbench/entry/binding.py) 提供两个函数，输入全显式，无目录扫描或固定案例。

```python
freeze_capability_selection(
    project_root, *, task, method, requirement, supplies,
    supporting_documents, evidence_check, output_directory,
    resolution_id, snapshot_id, evaluated_at,
    qualification="structural-replay", revision=1,
    projection_eligibility_check=None, schema_root=None,
) -> CapabilityFreezeResult

freeze_execution_inputs(
    project_root, *, manifest,
    agent_profile, data_policy, host_policy, execution_binding,
    output_directory, execution_at, view_id, revision=1, schema_root=None,
) -> ExecutionInputsResult
```

- Task/Method/Requirement/Supply、Profile/policies/binding 输入均为现有 `PinnedExecutionInput(path,sha256)`。path 必须 portable root-relative，拒绝绝对路径、冒号、反斜杠、空/dot/traversal 段和 root 外 symlink；只读确切文件、绑定同次读取的 bytes/hash、检查声明 kind 与完整 Schema。
- supporting_documents 是显式 `kind/path/sha256` references，仅允许 typed capability conformance、provider conformance、SkillReleaseProjection。不得依赖隐含 registry scan。
- evidence_check 保留现有 `(SupplyIdentity, evidence_mapping, requirement_id) -> pass|fail|unknown` 形状，必须由 caller 提供真实可信实现。production 不提供“总是 pass”证据函数。Skill 的 Runtime projection verifier 同样外部提供。
- CapabilityFreezeResult：`status`, `resolution`, `snapshot`, `summary_path`, `assessments`。resolution/snapshot 是现有 PinnedExecutionInput 或 None；summary_path 是 root 相对路径；assessments 保留逐候选十项检查。
- ExecutionInputsResult：`bundle`, `view`, `summary_path`。bundle/view 是现有 PinnedExecutionInput。

## 输出与边界

selection 复用 assess_supply/resolve_status，不排序、不 fallback。完整 SupplyChain 独立重算冻结契约。Task/Method identity、hash 与 capability demand 保持一致；Requirement 必须由该 Method 请求；不修改 Method、不扩大人类范围。

只有唯一合格候选生成 Snapshot。普通 gap/ambiguous/权限 blocked 产生合法 `capability-resolution.json` 与逐项可读 SUMMARY，不产生 Snapshot；多个合格候选不会自选。

Method 未 proceed、缺 trusted verifier、trusted fail/unknown、Runtime Skill 缺 trusted projection verifier：返回 blocked，持久化 SUMMARY，Resolution/Snapshot 为 None。外部 fail/unknown 不能硬写成与 pinned typed 原件不一致的 Resolution；实际检查仍保留在 result/summary。损坏 pin/Schema/交叉引用则 fail closed 抛 EntryBindingError，尚未发布成功输出。

structural Snapshot 明确 execution_input=false。runtime-execution 仅接受 caller 显式要求、非 fixture typed live 证据及可信检查；缺资格保留 blocked/gap。输入证据及既有对象不被改写。此 caller 不代替正式来源 qualification、Skill admission 或最终 Runtime admission。

runtime 接完整现有 manifest：精确 documents/imports、slice closure、entrypoint/Skill extension 和 false authority boundaries。先检查 Schema/外部 pins/SupplyChain，写唯一新目录，再由现有 load_runtime_bundle 校验闭合；由 produce_resolved_execution_view 形成 View；由 load_resolved_execution_view 作确定性重放核对。View 固定 Snapshot Supply，禁止重选；原有 policy/Profile/budget/permission/egress/side-effect/freshness 交集规则保持。

Runtime/View 校验失败保留 candidate `runtime-bundle.json` 与 blocked SUMMARY，抛 EntryBindingError；不返回成功 result。必要时已写 View 也仅为诊断 candidate，需依 SUMMARY 判断整个 freeze 是否完成。目录独占、不覆盖历史目录。跨文件发布没有事务回滚或权限预占；Manifest/View 本身也不授予执行权。Host、Driver、Tool、Provider、trace/closeout 均由 Root 后续集成。

## 验证及原失败

[test_entry_binding.py](../../../../../tests/test_entry_binding.py)：15项通过。命令与初始失败见 [COMMUNICATIONS](COMMUNICATIONS.md)。覆盖结构冻结/不可升级 fixture、显式 Runtime typed 输入、无 verifier/unknown/fail、空候选 gap、多个合格 ambiguous、权限 blocked、非法路径/hash/kind、Task lineage/范围、源文件 mutation、Bundle→View round-trip、禁止重选、缺 import、旧目录不可覆盖。仅确定性 offline fixture，不代表科学正确性、生产 Tool 行为或 live conformance。

第一次测试暴露旧 M11 Runtime fixture 复制 structural comparisons 后更改 qualification，其文案与当前 runtime assessment 重算不同；未改旧 fixture 或放宽校验。新测试由本 producer 先冻结匹配当前规则的 Resolution/Snapshot，再重绑完整 manifest。另一个首测失败是测试 Supply 使用 Schema 禁止的 external_write=true；改为合法更窄 Requirement，从真正 permission assessment 得到 blocked。

| 交付 | SHA-256 |
| --- | --- |
| src/research_workbench/entry/binding.py | c8b5811d9d5eca08affac3292658c989ff3f001aafd14176de9fca3fd0dc991c |
| tests/test_entry_binding.py | 31d24156850735927503b89e9974128d67738f4de36da19c9d2497b54643c80a |

## Root 下一步与 continuity 建议

Root 为实际 RoleInvocation/Task 制作 pins，供应可信 evidence/projection verifier；先 selection，再按返回 refs 显式重绑 manifest documents/imports/entrypoint，随后 freeze_execution_inputs。不得把 fixture 或 lambda-pass 作为真实来源资格。shared CLI/__init__、总体 API/Tool 验证、总体回归与 PR 由 Root 负责。本交付不 merge/commit/push。

PROJECT_MEMORY own-row 建议：`2026-10-07 AUDIT-RWB-ENTRY-001 ENTRY-C：隔离入口 capability-selection / explicit Bundle→View callers 已实现；15个自身 offline tests通过。复用已有 assess_supply/resolve_status与Runtime/View validators；gap/ambiguous/blocked及trusted fail/unknown保留可读记录，structural不可升级。来源为本binding/HANDOFF；尚无live资格或正式接受；下一步Root集成实际Task pins/可信证据并总体回归。`
