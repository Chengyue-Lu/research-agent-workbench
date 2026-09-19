# M5-007 H3：四臂 synthetic execution

更新：2026-09-19。Owner：路诚钺。Execution 接口复核：黄毅。风险：R2。

H1/H2 已由 PR86 合入 `develop@51dc3ab477f21f18ac3829bf553b5b779d49a4fe`。
按用户 2026-09-17 的后续授权，PR89 将 H3 独立提交迁移到该基线，并转为正式 R2 feature PR。
分支为 `feature/m5-007-harness-execution`，目标为 `develop`。H3 与 dispatch deadline 修复已获
黄毅对 `d725f7e` 的 APPROVE，并由 PR89 于 2026-09-18 合入 `171d465`。
下一切片为 [H4 评价证据与分析输入](M5-007_H4_PACKET.md)。
原始 Draft 候选与本次集成分别留痕，见 [rebase 记录](attempts/M5-007-H3-REBASE-001/README.md)。

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
- Host 完成自身 preflight 后、调用 Driver 前，通过可选的可信 `dispatch_guard` 再收紧调用条件。
  Harness 以首个 Host 的 `started_at` 为整臂时间原点，在该边界读取可信当前时间；等于或超过
  Protocol deadline 时生成零调用的 `HOST-DISPATCH-BLOCKED` Host/Receipt。准备、归档和回放
  间隙计入同一 deadline。guard 不能覆盖 Host 拒绝，异常保持未完成现场。
- Attempt 的 `dispatch_checks` 与 M11 Receipts 一一对应，记录实际边界的 `checked_at`；Host
  自身 preflight 已拒绝时对应项为 null，baseline 为空数组。cold replay 从首个 Host、冻结预算、
  每个 Host 的时间区间与该观察独立重算许可，拒绝缺失、时钟倒退、区间外时间或与 Host 不符的决定。
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
保留失败并停止该 run。cross-owner review 与 CI 是后续 R2 接受条件；2026-09-18 后续授权为修复
PR89 review comment 并推送原 PR，无需等待远端 CI。修复记录见
[review Attempt](attempts/M5-007-H3-REVIEW-001/README.md)。
