# Thin Execution Host

M11-003 实现一个 supply-neutral、single-binding、single-attempt 的窄 Host：

```text
hash-pinned Resolved Execution View（内部绑定 exact Runtime Bundle）
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
- 返回深层只读 `ValidatedExecutionView`，其中保留这次重算使用的 exact `ValidatedRuntimeBundle`。

因此，即使攻击者重写 View 并同步更新文件 hash，也不能静默修改 Model、Host、policy intersection 或
frozen Supply selection。任何上游 policy/binding 文件漂移也会在重算前被各自 hash pin 阻断。执行 API
不再接受第二个可替换 Bundle 参数；在 Driver 调用前，Host 会按 View 绑定的 manifest pin 重载 manifest 与
全部 document，并与已验证 Bundle 比较，从而在可控文件边界内阻断 validate/use 间的 Bundle 漂移。

## Driver port

`FrozenExecutionDriver` 只有两个 surface：

- `binding`：Driver 声明自己实际使用的 Provider/Adapter/Model/Runtime/Host identity；
- `execute(FrozenExecutionRequest)`：接收只读 View 与 bundle documents，返回 `ExecutionDriverResult`。

Host 在调用前要求 Driver binding 与 View 完全一致，并由 Host 自有 `SystemHostClock` 或测试注入的 trusted
`HostClock` 观察 start/end；执行调用方不能提交或回填时间戳。Host-observed `started_at` 必须仍落在冻结的 Supply、
DataPolicy 与 Host-policy 三组有效期内；不一致或过期则零调用、`blocked`，并输出指向当前 Snapshot/View
的 re-resolution request。`actual_facts.elapsed_seconds` 由 Host 的 end-start observation 计算，`max_seconds`
也只使用该 Host-observed duration；Driver 的同名自报值不参与预算授权。调用后仍比较 actual binding，检测
Driver 静默 rebind。

## Boundary enforcement 与 facts

Driver 必须报告：

- turns、output tokens、Provider/Tool invocation counts 与实际 Tool identity 集合；Driver 可携带 elapsed
  observation，但 Host report 与 `max_seconds` enforcement 不信任该值；
- external write、data-egress payload classes、side effects；
- output artifacts 的 contract/path/hash；
- fact capture 是否完整及 capture gaps。

Host report 明确区分两类 enforcement：

- `preventive_controls`：Driver 调用前可判定的 exact binding、freshness 与 Runtime Bundle integrity；失败时
  Driver 零调用，因此可称 prevented；
- `detective_controls`：调用返回后对 actual binding、事实完整性、external write、egress、side effects、
  budget、artifact scope 与 outputs 的核对；这些只能称 detected，不能声称外部副作用已被沙箱阻止。

越界、缺失 output、artifact path/hash 漂移或事实捕获缺口均转为 `failed`，不会写成 completion。
`driver_claims_trusted: false` 明确 Driver 自报事实仍需 Trace/Receipt 后续闭合。Driver exception 只产生
content-free `HOST-DRIVER-EXCEPTION` 与 `driver-exception` capture gap；异常正文不会进入 report，Host 也
不会重试。

## Report 不是 Receipt

`execution_host_report` 固定本次 `runtime_bundle_ref`、View、Task 与 exact Action/Capability slice，并把
`requested_binding`/`requested_supply_report_ref` 和调用后的 actual facts 分开：preflight 零调用时没有
actual binding；post-call 成功或失败都保留 Driver 返回的 actual binding/Supply；driver exception 也不伪造
actual binding。其 boundary 固定：

- `actual_facts_only: true`；
- 不拥有 Supply selection、rebinding、automatic fallback；
- 不产生 Method decision、Claim effect 或 Human decision；
- 不实现 Topic 5 recovery。
- 不宣称 whole-Task completion。

失败时可包含 bounded Diagnostic。只有 binding 需要变化时才生成 re-resolution request；这不是 Host 自己
执行 re-resolution。M11-004 才把 fact report 连接到通用 Trace/Artifact/Validation/Receipt。

## 当前适用范围

测试使用 bounded local no-Skill procedure Driver，证明接口与边界，不证明任何真实 Provider 账号、模型、
SDK、网络调用或 OS 级副作用隔离可用。TOCTOU 防线覆盖受 pin 的仓库文件重载，不等同于锁定外部服务状态。
现有 M6 Provider/session 可以在后续通过薄 Driver 适配，但 M11-003 不修改其 SDK、认证或 live conformance。
