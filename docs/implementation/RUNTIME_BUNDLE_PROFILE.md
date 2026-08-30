# Runtime Bundle / Consumer Profile

M11-001 为 Runtime 建立一个显式、hash-pinned、supply-neutral 的读取边界。它回答：

> 对于一个已经由 Research Control / Capability Resolution 冻结的 `runtime-execution`
> Snapshot，Runtime 本次获准读取的 exact document closure 是什么？

它不回答“是否应当执行”、不重新选择 Supply，也不生成 Resolved Execution View。后续 M11-002 才会在
该 closure 之上冻结最终 Host/Provider/Adapter/Model 与 policy intersection。

## Manifest 契约

`runtime_bundle_manifest` 只接受单个文件，并显式固定：

- `entrypoint`：唯一 `resolved_capability_snapshot` 的 path/hash；
- `execution_scope`：唯一 `Action + Capability Requirement` 执行切片，并同时声明 Task 的完整
  capability demand、当前 singleton closed set；`task_completion` 在 M11 Core 中固定为 `false`；
- `documents`：Task、Method Resolution、Capability Requirement、typed conformance evidence、Supply
  Report、Capability Resolution 与 Snapshot 的 exact path/kind/hash；
- `imports`：上述对象之间完整且无额外边的 import graph；
- `skill_extension.enabled: false`：M11 Core 的 zero-Skill 边界；若为 true，必须同时 exact-pin 唯一
  `skill_release_projection`；
- 四项 false authority boundary：manifest 不选择 Supply、不授予执行权或权限、也不拥有 fallback。

Core/extension bundle 都要求 Task、Method、Requirement、Resolution、Snapshot 与 **Resolution 最终选择的** Supply
Report 各一个，conformance evidence 可以有一个或多个。Resolution 可以保留多个候选及其比较事实，但
Runtime closure 不导入未选候选的 Supply Report；否则 manifest 会把 Resolution 历史误当成本次可执行供给。
所选 Supply 必须在候选中恰好出现一次、对应 comparison 恰好出现一次，且全部 comparisons 中只能有这一个
eligible candidate；ambiguity 不能伪装为 `satisfied`。所有传递引用都必须
在 manifest 内声明并 hash 对齐；所有 manifest document 又必须从 entrypoint 可达，因此不能把未选供给或
其他无关文件塞进 closure。

M11 v0.1 不把上述 singleton closure 冒充 whole-Task closure。`Method Resolution.resolution_status` 必须为
`proceed`，`blocked` 与 `split-and-block` 均 fail closed；Task `required_capabilities` 必须严格等于全部
Method Action `capability_requirements` 的并集。`execution_scope.action_ref` 必须精确命中 Method Action，
`requirement_id` 必须属于该 Action，`closed` 必须只含当前 Requirement，而 `required` 必须等于 Task 的完整
capability set。无论当前切片是否恰好覆盖全部 capability，M11 Core 都固定 `task_completion: false`，只报告
capability-slice closure fact。

## Runtime loader

```python
from research_workbench.execution import load_runtime_bundle

bundle = load_runtime_bundle(
    "runtime/manifest.yaml",
    project_root=".",
    schema_root="schemas",
)

snapshot = bundle.documents[bundle.entrypoint_path]
```

返回的 manifest 和 document mapping 是深层只读视图。loader 只读取 manifest 列出的文件，不接受目录，
不递归扫描 `registry/`、`examples/` 或 project root，也不导入 repository-wide validator、Skill Need、
Candidate、Evaluation 或 Lifecycle。未列出的损坏文件不会污染该 bundle；被引用但未声明、hash 漂移、身份
替换、复制的 Supply facts 漂移、selected candidate/comparison 不闭合或 import graph 漂移都会 fail closed。

## 与 maintainer-full 验证的区别

`load_validated_capability_snapshot()` 继续服务仓库维护者：它收集 Registry/examples，并验证 Method、Skill
Evolution 与 Phase B Gate 的完整仓库一致性。`load_runtime_bundle()` 是 Runtime consumer profile，只接受由
producer 预先构造的最小闭包。二者不能互相替代：

| Profile | 输入 | 允许读取 | 用途 |
|---|---|---|---|
| `maintainer-full` | repository roots | Registry、examples 与 Evolution contracts | 发布前、迁移与仓库审计 |
| `runtime-bundle` | 单个 manifest | manifest 中 exact path/hash closure | M11 Runtime consumer 输入 |

## Optional Skill extension

M11-006 没有建立第二个 Runtime loader。`skill_extension.enabled: true` 仍进入同一个
`load_runtime_bundle()`，但 exact closure 额外包含一个从 selected Skill Supply 指向
`SkillReleaseProjection` 的 `supply-projection` edge。manifest projection pin、Supply projection ref、
document kind/path/hash/identity 必须一致。

Skill Supply 的 Release identity/component、required Tool dependency、capability/I/O 与 boundary ceiling
由同一个纯 projection→Supply checker 重放；permission roots、data-egress forbidden set 也必须保持收窄，
不能只比较粗粒度 policy。Method 必须是 `skill-need` 或 `mixed` disposition。反之 non-Skill Supply 必须继续使用
`no-skill`，且不得开启空洞 Skill extension。Runtime 既不读取 projection index，也不读取 Lifecycle、Need、
Evaluation 或 Human deliberation。

Projection missing/stale/mismatch、Supply 超出 ceiling、Method disposition 不符或 extension pin 漂移均在
Driver 调用前 fail closed。Runtime 不选择替代 Skill、不回到 Lifecycle、不 fallback；重新选择仍须回到
Capability Resolver 并发布新的 Resolution→Snapshot→View。

## 明确边界

- 只接受 `qualification: runtime-execution`；Phase B 的 `structural-replay` fixture 不能执行；
- Core（`skill_extension.enabled:false`）只接受 Method `no-skill` 且 Supply 不含 Skill；可选 extension 只接受
  projection-backed Skill Supply 与 Skill-bearing Method disposition；
- Method Resolution 必须为 `proceed`；Capability Resolution/Snapshot 必须为 `satisfied`，且身份、引用与供给复制事实闭合；
- non-fixture availability 与 live typed evidence 是输入资格，但仍不等于最终 permission 或 Human approval；
- manifest 不保存凭据，不执行调用，不实现 fallback、routing、recovery、Trace 或 Receipt；
- Skill extension 不改变 Core 的 zero-Skill 可用性，也不增加 Skill-specific Host/driver/session/fallback。

## 验证证据

`tests/test_runtime_bundle.py` 覆盖：zero-Skill/无 Registry 正路径、多候选 Resolution 只导入 selected Supply、
selected Supply 缺失候选、未声明无关坏文件隔离、目录输入、hash 漂移、未声明传递引用、
`structural-replay`、import graph 漂移、hash-valid identity substitution、Supply fact 漂移、双 eligible
ambiguity、Method blocked/split-and-block、Task/Method capability set 漂移、任何 Task completion 声明、深层只读结果，
以及 Runtime 模块无递归/Evolution imports。M11-006 另覆盖 projection-backed Skill 的同一路径正例、
projection/ref/hash/fact/ceiling/Method drift 负例、View/Host 复用和 Lifecycle callback 不得授权 Runtime。
