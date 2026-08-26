# Thin Execution Host

M11-003 实现一个 supply-neutral、single-binding、single-attempt 的窄 Host：

```text
exact Runtime Bundle + hash-pinned Resolved Execution View
  ↓ deterministic View recomputation
one pre-bound FrozenExecutionDriver
  ↓ exactly one call
Execution Host Fact Report
```

Host 不接收候选 Driver 列表，不访问模型池，不选择 Provider/Tool，也没有 retry/fallback/recovery loop。

## View consumer

`load_resolved_execution_view()` 要求单个 View 文件、external SHA-256 pin 和已验证 Runtime Bundle。它会：

- schema-check View；
- 校验 View→Runtime Bundle identity/path/hash；
- 从 View 中恢复 Profile、DataPolicy、Host policy、Execution Binding 的 exact pins；
- 调用 M11-002 producer 作确定性重算，并要求结果逐字段相等；
- 返回深层只读 `ValidatedExecutionView`。

因此，即使攻击者重写 View 并同步更新文件 hash，也不能静默修改 Model、Host、policy intersection 或
frozen Supply selection。任何上游 policy/binding 文件漂移也会在重算前被各自 hash pin 阻断。

## Driver port

`FrozenExecutionDriver` 只有两个 surface：

- `binding`：Driver 声明自己实际使用的 Provider/Adapter/Model/Runtime/Host identity；
- `execute(FrozenExecutionRequest)`：接收只读 View 与 bundle documents，返回 `ExecutionDriverResult`。

Host 在调用前要求 Driver binding 与 View 完全一致；不一致则零调用、`blocked`，并输出指向当前
Snapshot/View 的 re-resolution request。调用后仍比较 actual binding，防止 Driver 静默 rebind。

## Boundary enforcement 与 facts

Driver 必须报告：

- turns、output tokens、elapsed seconds、Provider/Tool invocation counts；
- external write、data-egress payload classes、side effects；
- output artifacts 的 contract/path/hash；
- fact capture 是否完整及 capture gaps。

Host 将 actual facts 与 View 的 effective permission、egress、side-effect、budget、write roots、required
outputs 逐项比较。越界、缺失 output、artifact path/hash 漂移或事实捕获缺口均转为 `failed`，不会写成
completion。Driver exception 只产生 content-free `HOST-DRIVER-EXCEPTION` 与 `driver-exception` capture gap；
异常正文不会进入 report，Host 也不会重试。

## Report 不是 Receipt

`execution_host_report` 只说明一次 Host 调用实际发生了什么。其 boundary 固定：

- `actual_facts_only: true`；
- 不拥有 Supply selection、rebinding、automatic fallback；
- 不产生 Method decision、Claim effect 或 Human decision；
- 不实现 Topic 5 recovery。

失败时可包含 bounded Diagnostic。只有 binding 需要变化时才生成 re-resolution request；这不是 Host 自己
执行 re-resolution。M11-004 才把 fact report 连接到通用 Trace/Artifact/Validation/Receipt。

## 当前适用范围

测试使用 bounded local no-Skill procedure Driver，证明接口与边界，不证明任何真实 Provider 账号、模型、
SDK 或网络调用可用。现有 M6 Provider/session 可以在后续通过薄 Driver 适配，但 M11-003 不修改其 SDK、认证
或 live conformance。
