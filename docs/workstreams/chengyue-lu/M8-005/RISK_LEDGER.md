# M8-005 风险台账

| ID | 类型 | 风险与边界 | 处置 | 状态 |
|---|---|---|---|---|
| M8D-PASS-001 | fact | 把 structural PASS 写成 scientific approval 会越过 Claim/Method authority。 | `validate` 与 `commit` 分离；文档和结果明确 allowed 不等于正确。 | controlled |
| M8D-RELAX-001 | fact | Agent/Resolver 若能 commit permission/data relaxation，会绕过冻结 Task/Protocol。 | v1 commit actor 只允许 Human Gate，并要求 revised Task/Protocol 与风险事实。 | controlled |
| M8D-CLAIM-001 | fact | Claim promotion 若只检查 Schema 就可提交，会把 Evidence 完整性误作科学判断。 | Resolver 只能 validate；Human Gate commit 仍需 evidence、ceiling 与 limitation facts。 | controlled |
| M8D-GATE-001 | fact | 任意附加 Gate ref 可能被包装为 cosmetic approval。 | 非 Gate rule 出现 `human_gate_ref` 时 fail closed。 | controlled |
| M8D-DRIFT-001 | fact | 原位放宽 Matrix required facts 会改变历史 authority。 | exact v1 commit facts、Matrix raw hash 和 result recomputation 闭合；变化须新版本。 | controlled |
| M8D-BIND-001 | limitation | Matrix 声明 binding authority 不等于 Capability/Skill/Tool binding 已实现。 | 不创建 binding/Assignment/Execution 对象；等待独立 consumer Task。 | accepted limitation |
| M8D-STAGE-001 | fact | 为 M8-005 再建小节点分支会重复 R2 审查与文档 churn。 | 继续使用统一 M8 阶段分支与 PR #30，不新增 Handoff。 | controlled |
