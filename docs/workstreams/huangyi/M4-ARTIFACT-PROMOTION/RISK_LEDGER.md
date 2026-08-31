# M4-002 风险台账

| ID | 风险 | 控制 | 状态 |
|---|---|---|---|
| M4P-PIN-001 | report pin 正确但 checker/subject/entry/live bytes 漂移 | 对五层引用逐一复验；任一 missing/hash drift/root escape 阻断 | 已测试 |
| M4P-SET-001 | 只按 path 比较导致错误 hash 或额外未受检 entry 混入 | subjects 与 entries 按规范化 `(path, sha256)` 完全集合相等，并拒绝重复 identity | 已测试 |
| M4P-NEG-001 | 失败或负结果被静默丢弃 | 每个 report subject 必须有 entry；每个 entry 必须声明 negative_result 与 promote/retain disposition | 已测试 |
| M4P-PATH-001 | prefix lookalike、`..`、root/symlink escape 绕过分区 | 完整 path parts、root resolve 与 lexical path 一致性检查；accepted target 永久禁止 | 已测试；Windows symlink 用例受本机权限跳过，Linux CI 必跑 |
| M4P-TOCTOU-001 | precheck 后源、staging 或目标发生竞态 | copy 时计算 digest、发布前完整复验、staged digest 复核、hard-link exclusive-create | 已测试 |
| M4P-PARTIAL-001 | 多目标发布中途失败留下误导性子集 | 对本次创建且仍与 staged inode 相同的目标逆序回滚；源始终保留 | 已测试；突发主机崩溃保留为显式非事务边界 |
| M4P-AUTH-001 | promotion 被解释为 Claim/Human/publication authority | Schema 常量和实现文档固定四项 false；CLI 不写 Claim/Decision/accepted | 已测试 |
| M4P-BASE-001 | PR #51 修改共享 document/coverage 文件导致 latest-base 语义漂移 | #51 最终集成后 rebase，重新跑 focused/full/coverage/package/双 Python CI | 待最终 rebase |
