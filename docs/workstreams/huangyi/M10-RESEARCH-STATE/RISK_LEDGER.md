# M10 Phase C 风险台账

| 风险 | 缓解 | 状态 |
|---|---|---|
| 多个文件声明同一 ID+revision，解析器静默取第一个 | index 记录 duplicate identity；exact resolve 返回 ambiguous；两类负面测试 | 已锁定 |
| ref 有 pin 但 target 无 `content_hash` 仍被接受 | 返回 `hash-unverifiable` 并 BLOCK | 已锁定 |
| State role 与目标对象类型不一致 | role→semantic type 显式映射，错配 BLOCK | 已锁定 |
| current ref 指向 stale revision | closure 中同 identity 最新 revision 比较 | 已锁定 |
| 新建 Human Decision 对象复制 kernel Decision | 删除平行 Schema；复用 `object_type: decision` | 已收缩 |
| 通过目录/文件名猜测 closure | M10-001～M3-009 CLI 要求显式 roots；M10-003 runner 只消费 source manifest exact path/hash 并按原相对路径 staging，不扫描目录 | 已锁定 |
| candidate 被误当最终 State ontology 或科学接受 | 文档、STATUS 与 fixture 均标注 bounded/R2 pending | 保留边界 |
| module PR 扩展后各层证据混淆 | M10-001 与后继 Task 保持独立 commit、契约、fixture 与专项测试；最终整链重审 | 进行中 |
| 为 lineage 直接改写 legacy Attempt | 使用独立 `lineage_id@revision` sidecar，execution Attempt Schema/恢复/Receipt 不变 | 已锁定 |
| sidecar 只按路径命中而未验证实际文件 | explicit closure 内唯一 type-bound path + loaded-byte SHA-256 + attempt_id 一致性 | 已锁定 |
| Attempt 与 State revision 被强制一一演化 | 两个 Attempt 共享同一 State r1，State r2 独立演化的正面测试 | 已锁定 |
| predecessor 与 reopen justification 被耦合，或 changed condition 退化为自由文本 | 两字段独立；predecessor exact/type-bound/distinct；每项 changed condition 必须携带 exact/type-bound provenance refs | 已锁定 |
| execution-origin Failure 静默省略 source Attempt | `origin_kind` 明确 execution/non-execution；execution 强制 all-or-nothing profile + exact source Attempt，non-execution 禁止 profile | 已锁定 |
| Research Failure 复制 execution failure / Evidence / Gap / Need | universal minimum 只含 learned/revisit；bounded execution profile 按 origin 条件化且 Schema 拒绝平行字段 | 已锁定 |
| M10-002 被误当自动 reopen 或科学判断 | 文档与 fixture 明确仅为 candidate；Human semantic review/R2 独立 | 保留边界 |
| Method Trace 复制 Execution Trace/Method/State 正文 | 独立 Schema 只保存 stable refs、decision IDs 与 disposition；operational Trace 不改 | 已锁定 |
| Method Resolution 未索引或 Trace 绑定 lookalike | `resolution_id@revision` 入 exact index；Schema、Task identity 与 Task byte pin 二次验证 | 已锁定 |
| Trace 把无关 Task/Attempt/State 拼接 | execution Attempt/Task/Resolution 三方 identity 与 Task question↔State Question 交集检查 | 已锁定 |
| selected Snapshot 被写成 actual execution | captured 只接受正式 `execution_trace_fact` file pin；Snapshot wrong-kind 反例 | 已锁定 |
| M11 producer 已存在却继续宣称全局无 producer | unavailable reason 收窄为当前 Attempt 无 authoritative fact；M11 producer-generated captured 正例 | 已锁定 |
| actual fact 只记录 availability、未解释路径效果 | captured 顶层 fact 必须 exact 重复绑定至少一个 applied disposition 与 State effect；ref 漂移/缺失/Attempt 错配阻断 | 已锁定 |
| gap-valid 被重分类为 fact-bound | unavailable 固定 `gap-only` 且 path fact 为空；captured 仅声明 `fact-bound-path-effect` | 已锁定 |
| actor 偷读 oracle/session/unlisted data 或覆盖 input | oracle 不进入 actor args/env/staging；audit hook deny-by-default；exact case-data read surface 与 input-write 反例；trusted runtime/schema 另行声明 | 已锁定（不声称完整进程/OS sandbox） |
| stale Method Trace 与新 State 拼接仍通过 | actor 要求 selected active State 出现在 Trace current/result ref，且 State/Trace lineage 各只有一个 active head | 已锁定 |
| 替换 case/oracle 与 canonical Gate ID 不可区分 | 每案报告 manifest/oracle/closure SHA，顶层 Gate digest 再绑定两案；替换输入 hash-distinguishable | 已锁定 |
| 弱 oracle 或 caller report 冒充 Gate | runner 固定 oracle minimum/predicate vocabulary；CLI 只重跑两案且拒绝覆盖 output，不消费 caller report | 已锁定 |
| machine PASS 越权宣称科学正确或解冻 Topic 5 | report 强制 Human/R2/Phase C pending 与三项 false authority boundary | 已锁定 |
