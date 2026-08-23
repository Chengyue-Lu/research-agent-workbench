# M8-004 风险台账

| ID | 类型 | 风险与边界 | 处置 | 状态 |
|---|---|---|---|---|
| M8M-OVERWRITE-001 | fact | 原位改写 v0.1 Mode 会破坏历史 Resolution 与 Action 解释。 | source 文件只读保留；v0.2 使用新路径、版本和 hash。 | controlled |
| M8M-ACTION-001 | fact | v0.2 Mode 若引用 `mode_ref` 仍为 v0.1 的 Action，会违反精确 revision ownership。 | 为 v0.2 发布新 Action version 和 append-only Registry entry；不重写旧 entry。 | controlled |
| M8M-SKILL-001 | fact | 迁移器若把旧 Skill recommendation 转成具体 Skill/Tool binding，会重新建立 Mode→Skill 耦合。 | 旧 recommendation 只作为 removed field 留痕；target 仅引用 Mode Action。 | controlled |
| M8M-HASH-001 | fact | 只记录结构值而不固定文件字节，无法证明迁移针对哪个原件。 | migration record 固定 source/target/action path 与 raw-byte SHA-256。 | controlled |
| M8M-SILENT-001 | fact | 自动发现并升级旧 Mode 会改变历史 Task 语义。 | migration 必须显式调用；缺失映射、hash drift 或未知版本均 fail closed。 | controlled |
| M8M-FRAMEWORK-001 | inference | 为两个 Mode 先建通用 migration engine 会放大复杂度。 | 只实现一个 versioned v0.1→v0.2 seam；新的对象类型或版本另行证明需求。 | controlled |
| M8M-STAGE-001 | fact | 为每个 M8 小节点建立分支和交接会造成分支/文档 churn，并重复同一 R2 审查。 | M8-004 合入统一 M8 阶段分支与 PR #30；不保留独立小节点分支或 handoff。 | controlled |
| M8M-VALUE-001 | limitation | 离线迁移 fixture 不能证明真实研究质量提升。 | 仅声称兼容与边界完整；净收益留给后续 forward case/evaluation。 | accepted limitation |
