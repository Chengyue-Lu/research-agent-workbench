# GOV-V2-STAGE-CLOSURE 风险台账

| ID | 风险 | 控制 | 状态 |
|---|---|---|---|
| GVS-AUTH-001 | authority 文件被普通文档或共享契约等级低估。 | 路径推导至少 R2，并由负面测试固定。 | controlled |
| GVS-ID-001 | 已发布对象通过同版本改写、删除或迁出 protected path 破坏历史重放。 | 每个 PR 无条件比较 policy 声明的 base/head published identity 全集；路径、内容和 identity 均不可原地变化，只允许保留旧版本后追加新版本。 | controlled |
| GVS-DAG-001 | PARKED 直接到 DONE 绕过激活语义，或通过独立、断连 completion component 偷渡。 | 仅 R2 可使用；必须包含非 PARKED anchor，所有 PARKED 完成从 anchor 沿 completion DAG 可达，并验证声明闭包、定义不变、逐 Task 证据、无环及 base-DONE/同 Stage 先行依赖。19 项新增对抗测试与 policy 测试已通过。 | controlled |
| GVS-EVIDENCE-001 | 批量置 DONE 只给笼统 CI 结论。 | Verification evidence 必须逐个提及每个新 DONE Task。 | controlled |
| GVS-PARSER-001 | 轻量 YAML identity 读取器无法理解复杂表达。 | 发布 identity 约定为顶层非空标量；形状异常直接失败，不猜测身份。 | accepted limitation |
