# Research Attempt Lineage and Research Failure Candidate (M10-002)

状态：Bounded implementation candidate；最终语义待 Human/R2 接受

更新：2026-08-27

## 1. 单层范围

本契约只实现 Phase C 依赖链的 M10-002。它在 M10-001 Research State 之上增加：

- 一个不修改 legacy execution `Attempt` 的 versioned Research Attempt lineage sidecar；
- 一个只冻结 `learned_result` / `revisit_condition` 语义最小值的 Research Failure candidate；
- 对上述对象的 explicit-closure、identity、type 和 pin fail-closed 检查。

M3-009 Method Trace 与 M10-003 fresh-process Gate 不在本层。M10-002 不授权自动 reopen、自动重跑、
科学判断或 Topic 5 实现。

## 2. Attempt 与 State 分离

`research_attempt_lineage` 使用独立 `lineage_id@revision`，并保留被描述的 execution `attempt_id`。
它通过 `execution_attempt_ref.path + sha256` 精确绑定已有 `attempt.schema.json` 文件；validator 只在调用者
显式提供的 closure 中解析路径，并对已加载文件字节计算 SHA-256。旧 Attempt Schema、归档、恢复和
Receipt 路径不被改写。

每个 lineage candidate 精确引用一个 Research State revision。多个 Attempt 可以共享同一 State revision；
后续 State 可以由 Evidence 或具名 Human Decision 独立演化。因此 validator 不把历史 `state_ref` 因出现
更新 State revision 而判 stale，也不从 Attempt 推导 State revision。

`predecessor_attempt_ref` 是可选的 Research Attempt lineage exact ref，且不得自环。`reopen_justification`
是与 predecessor 独立的第三条关系：它可 exact-ref Failure、kernel Decision、Evidence 或 State（State ref
可承载 Unknown item 所在 revision），也可记录 changed condition；至少一种 basis 必须存在。justification
只记录为何重新开启可审查，不产生 reopen authority。存在 predecessor 不强制产生 justification，存在
justification 也不要求 predecessor。

## 3. Research Failure 最小语义

Research Failure 的 universal semantic minimum 只有：

- `learned_result`：这条研究路径实际教会了什么；
- `revisit_condition`：出现什么新条件后才值得重访。

`failure_id@revision` 与 `content_hash` 是引用完整性元数据，不扩张其研究语义。`execution_profile` 是
可选且 all-or-nothing 的 bounded profile candidate，仅包含 source Research Attempt、observed result 和
uncertainty。它不冻结为所有 Research Failure 必须具备的字段。

Research Failure 不是 execution failure、negative Evidence、Capability Gap 或 Skill Need；Schema 明确
拒绝这些平行字段。执行是否异常不能单独推出 Research Failure，执行成功也不阻止记录研究路径无信息增量。

## 4. Exact closure

`ClosureIndex` 继续只消费调用者显式提供的 bounded document set，并新增以下检查：

- lineage、Failure 与现有对象共同参与 `identity@revision` duplicate/ambiguity 检查；
- `execution_attempt_ref` 必须命中 closure 中唯一 execution Attempt，目标 `attempt_id` 必须一致；
- file pin 必须与同一次加载对应的真实文件字节 SHA-256 一致；
- State、predecessor Attempt、Failure 和 source Attempt 均须 exact revision 且 semantic type 匹配；
- predecessor 必须是不同 Research Attempt；reopen basis exact/type-bound，且与 predecessor 独立。

`rwb research-state validate <document> --closure <path>...` 可校验 Research State、Research Attempt
lineage 或 Research Failure；命令不会扫描未声明目录，也不会按命名约定猜目标。

## 5. 证据边界

两个 synthetic bounded case 只证明结构可表达且反例能被确定性拒绝。它们不证明最终 Attempt/Failure
ontology、reviewer reconstruction、科研结论正确性或 reopen 决策合理性；这些仍由具名 Human semantic
review 与最终 R2 closeout 独立承担。
