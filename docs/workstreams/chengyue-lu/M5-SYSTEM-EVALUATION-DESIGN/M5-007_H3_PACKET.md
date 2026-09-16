# M5-007 H3：四臂 synthetic execution

更新：2026-09-17。Owner：路诚钺。Execution 接口复核：黄毅。风险：R2。

用户授权在仍未合入的 PR86（`b53a391ece3a4be7207c00c636dc9e1570e71473`）上继续 H3，
完成后提交 Draft PR。分支 `feature/m5-007-harness-execution`，PR 目标仍为 `develop`。
H1/H2 接受与 H3 review 分别完成；本次授权只提前进入独立开发，不代表接受父 PR。

## 输入与执行边界

- `HarnessContext` 由调用方提供 exact plan/preflight/Protocol/case closure、run identity 与可信 preflight time；
  启动和 cold replay 都重算 H2，包括外部 admission verifier。
- H3 入口要求 `purpose=synthetic-contract-proof`。本地 Python Provider/Driver 为显式注入端口；
  工厂不能获得 private oracle、qualification、overlay 或评价闭包。端口是可信本地代码，未提供进程级隔离。
- A1/A2 经现有 M6 envelope/session/receipt；A2 qualification 在 Harness 外由 M6 产生。
  A3 消费 pre-run pairwise 指向的完整 Task slice 集合，A4 消费 overlay 的完整 Task slice 集合，
  分别进入 M11 Core 与 Skill closeout。每个 slice 均有独立 Host Attempt/Trace/Receipt。
- 单个 run 按 H1 的 block/arm 顺序执行；完成全部必需 slice 才能完成该 arm。
  目录和文件 exclusive-create，run identity 与 frozen Attempt identity 均不能重复使用。
- 所有 M11 slice 累计使用同一 arm 的冻结预算，耗尽后停止后续调用；累计超限按实际 facts 记为
  post-call failure。已执行 slice 后再遇 preflight block 时，整臂同样保留 post-call failure。
- 每次 dispatch 前保留 started marker；执行后重新 replay Receipt，再保留 finished record。
  失败停止后保留已有全部记录；异常或 capture 不完整时保留 started marker 与已有 Host/Trace，不能生成有效的完成记录。

## Retry 与状态

`completed`、`post-call-failed`、`preflight-blocked` 从独立 replay 的实际 Receipt 推导。
M6 的 `provider-error:transient` / `provider-error:rate_limit` 可映射到预注册的 `provider-transient`；
只有策略允许且尚有 retry slot 时才启动 fresh Attempt。保留所有失败与成功 Receipt，不选择最优结果。
M11 目前没有同等可重放的错误分类接口；M11 失败和未具备 typed 分类的 `transport-interrupted`
在本切片中保守停止，不推测其 retry 资格。冻结 refs、实际 lifecycle 和 retry 派生结果分别留存。

## 写入面与验收

实现位于 Evaluation 的 `harness_execution.py` / `harness_runtime.py`，消费既有 M6/M11 public ports；
新增 `evaluation_harness_execution@1.0.0` 记录和 Schema/catalog 注册。运行记录是执行账本，
H4 的盲审、reveal、metric evidence、analysis input，以及 H5 的持久化集成收口仍为后续工作。
整个 M5-007 保持 IN_PROGRESS，M5-004/005 保持原 Gate 与状态。

集成同时修复 Trace credential regex 对 `TASK-…` 路径的误判，保留真实密钥脱敏；范围补充见
[说明](attempts/M5-007-H3-001/SCOPE-AMENDMENT.md)。

正例覆盖四臂真实本地调用、多 slice 闭包、fresh retry 和禁止执行端口的 cold replay。
反例覆盖 Host preflight/post-call/exception 生命周期、失败保留、输入/输出漂移、漏 slice、
Attempt/retry 替换、漏记录、重复 run/Driver、越界目录和外层可信上下文替换。
检查按当前 coverage policy 执行；结果写入 [H3 Attempt Archive](attempts/M5-007-H3-001/README.md)。

不改变 Runtime 所有权、treatment、Resolver 选择权和 Human authority；若现有接口不能闭合证据，
保留失败并停止该 run。cross-owner review 与 CI 是后续 R2 接受条件；Draft PR 不触发 merge。
