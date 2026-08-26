# M10-001 风险台账

| 风险 | 缓解 | 状态 |
|---|---|---|
| 多个文件声明同一 ID+revision，解析器静默取第一个 | index 记录 duplicate identity；exact resolve 返回 ambiguous；两类负面测试 | 已锁定 |
| ref 有 pin 但 target 无 `content_hash` 仍被接受 | 返回 `hash-unverifiable` 并 BLOCK | 已锁定 |
| State role 与目标对象类型不一致 | role→semantic type 显式映射，错配 BLOCK | 已锁定 |
| current ref 指向 stale revision | closure 中同 identity 最新 revision 比较 | 已锁定 |
| 新建 Human Decision 对象复制 kernel Decision | 删除平行 Schema；复用 `object_type: decision` | 已收缩 |
| 通过目录/文件名猜测 closure | CLI 要求调用者显式给出 closure roots；不提供 fresh-actor runner | 已收缩 |
| candidate 被误当最终 State ontology 或科学接受 | 文档、STATUS 与 fixture 均标注 bounded/R2 pending | 保留边界 |
| 后继 Task 混入同 PR | M10-002/M3-009/M10-003 文件和 DONE 状态全部移除 | 已锁定 |
