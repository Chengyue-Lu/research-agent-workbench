# GOV-V2-STAGE-CLOSURE 风险台账

| ID | 风险 | 控制 | 状态 |
|---|---|---|---|
| GVS-AUTH-001 | authority 文件被普通文档或共享契约等级低估。 | 路径推导至少 R2，并由负面测试固定。 | controlled |
| GVS-ID-001 | 已发布同版本对象被原地改写，旧 Task 或 trace 无法重放。 | 按对象 identity 比较 develop/base 与 head 的完整文件内容；只允许保留旧版本后追加新版本。 | controlled |
| GVS-DAG-001 | PARKED 直接到 DONE 绕过真实依赖。 | 仅允许声明的完成集合；按 DAG 拓扑验证 base-DONE 或同 Stage 先行完成依赖。 | controlled |
| GVS-EVIDENCE-001 | 批量置 DONE 只给笼统 CI 结论。 | Verification evidence 必须逐个提及每个新 DONE Task。 | controlled |
| GVS-PARSER-001 | 轻量 YAML identity 读取器无法理解复杂表达。 | 发布 identity 约定为顶层非空标量；形状异常直接失败，不猜测身份。 | accepted limitation |
