# M10 Phase C 风险台账

| 风险 | 缓解 | 状态 |
|---|---|---|
| 多个文件声明同一 ID+revision，解析器静默取第一个 | index 记录 duplicate identity；exact resolve 返回 ambiguous；两类负面测试 | 已锁定 |
| ref 有 pin 但 target 无 `content_hash` 仍被接受 | 返回 `hash-unverifiable` 并 BLOCK | 已锁定 |
| State role 与目标对象类型不一致 | role→semantic type 显式映射，错配 BLOCK | 已锁定 |
| current ref 指向 stale revision | closure 中同 identity 最新 revision 比较 | 已锁定 |
| 新建 Human Decision 对象复制 kernel Decision | 删除平行 Schema；复用 `object_type: decision` | 已收缩 |
| 通过目录/文件名猜测 closure | CLI 要求调用者显式给出 closure roots；不提供 fresh-actor runner | 已收缩 |
| candidate 被误当最终 State ontology 或科学接受 | 文档、STATUS 与 fixture 均标注 bounded/R2 pending | 保留边界 |
| module PR 扩展后各层证据混淆 | M10-001 与后继 Task 保持独立 commit、契约、fixture 与专项测试；最终整链重审 | 进行中 |
| 为 lineage 直接改写 legacy Attempt | 使用独立 `lineage_id@revision` sidecar，execution Attempt Schema/恢复/Receipt 不变 | 已锁定 |
| sidecar 只按路径命中而未验证实际文件 | explicit closure 内唯一 type-bound path + loaded-byte SHA-256 + attempt_id 一致性 | 已锁定 |
| Attempt 与 State revision 被强制一一演化 | 两个 Attempt 共享同一 State r1，State r2 独立演化的正面测试 | 已锁定 |
| predecessor 与 reopen justification 被耦合为同一关系 | 两字段独立；predecessor exact/type-bound/distinct，reopen basis exact/type-bound 或 changed condition | 已锁定 |
| Research Failure 复制 execution failure / Evidence / Gap / Need | universal minimum 只含 learned/revisit；bounded execution profile 可选且 Schema 拒绝平行字段 | 已锁定 |
| M10-002 被误当自动 reopen 或科学判断 | 文档与 fixture 明确仅为 candidate；Human semantic review/R2 独立 | 保留边界 |
