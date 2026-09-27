# M5-007 H5：持久化 synthetic vertical proof

日期：2026-09-28。Task / Evaluation owner：路诚钺。Execution 接口复核：黄毅。风险：R2。
Task 保持 IN_PROGRESS。PR104 的 H4c 尚待 R2 接受；按用户“准备继续向前实现并推送到draftPR”
授权，在 `feature/m5-007-harness-proof` 上准备依赖 PR104 的独立 draft。
H4c 接受是 H5 集成及整体验收的前置条件，draft 开发不代表条件已经满足。

## 交付与边界

沿用 [进入计划](M5-007_ENTRY_PLAN.md) 的 H5 验收和现有 H1–H4c API，保存一套完整四臂
synthetic plan → preflight → execution → actual evidence → blind package → frozen synthetic
review → reveal → 13 metric associations → paired inputs。保留一次真实本地 Provider transient
failure 及 fresh retry，不把失败记录裁掉。所有固定指标仍为有原因的 unavailable/null。

开发辅助入口放在 tests，负责生成证据库存及冷回放；不增加产品的 authority 或重复 record kind。
库存和外部调用请求用独立 SHA-256 引用选择，公开 validator 从完整 contexts 重建分析；
新进程禁止网络、Provider/Tool/Host 执行和证据目录内代码执行。验证者与 synthetic 回调取自
受信仓库源码，不从库存读取并执行任何代码。

正反验证覆盖可重放成功链、失败/retry 完整性、原字节 hash drift、重新签名的结果/上下文替换、
冻结时序、外部 verifier 拒绝、源码/Schema 身份漂移。测试生成当前源码下的新证据；保存的
历史 proof 只绑定其自身源码/Schema 身份，后续 rebase 若改变身份另存新证据，不改写旧 archive。

## 接受

[H5 Attempt](attempts/M5-007-H5-001/README.md) 保存 Task snapshot、输入 pins、Agent Profile、
Skills[]、预算、捕获缺口和验证输出。按现行 component CI 执行 Python 3.11 相关模块、直接
fixture 消费者和短 installed smoke；coverage 是诊断。repository/docs/governance 检查分别
保留身份，scoped PASS 不代替 hosted CI/R2 接受。

H5 draft 不将 M5-007 置 DONE，不关闭 Issue55；H4c 接受后仍需整体 R2 审核。
不进行真实 case/live Provider、bootstrap 数值计算、加权评分、自动 admission/promotion、
M5-008/004/005 Gate 解除或发布。若必须更改已接受 Task/Protocol/权威/Runtime ownership，
保存最小失败证据并转具名 review。
