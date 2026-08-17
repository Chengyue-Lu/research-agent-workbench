# Project-internal Skill Need Dossiers

- 责任人：路诚钺
- 状态：M7-013 compact dossier baseline
- 日期：2026-08-18
- 上游计划：[项目内生协议 Skill 规划](PROJECT_INTERNAL_SKILLS.md)
- direct baseline：[Project-internal Handoff Direct Baselines](../../../examples/evals/project-internal-handoff/DIRECT_BASELINES.md)

两份 dossier 比较的是“是否需要额外的 project-internal Skill”。现有 Task 中的 Mode-derived Skill
不属于对照变量。当前没有 Skill ID、Skill 包、Registry 状态或准入决定。

## 1. `NEED-INT-COMPACT-HANDOFF`

### Need

H1 需要从有限的正式工件中选择最小充分的结果、限制、冲突、未解决项和下一动作。字段格式可由
Schema 保证，但“哪些负面信息会改变下一决策”需要语义判断。

### Trigger / non-trigger

- trigger：跨 Agent H1；存在多个正式输出，或省略某项会改变接受、回查、返工或下一 Task；
- non-trigger：H0；单一确定性输出；Task/模板能够逐项机械映射；H2 已由更严格策略接管；
- blocked：正式输出、Task 状态或引用不完整；不得从聊天记忆补造 Handoff。

### Direct baseline

使用 Handoff Schema、Task relationship check 和 `DIRECT_BASELINES.md` 的 H1 八步 closeout。主 Agent
只读 Handoff，争议时沿 artifact/validation refs 有界回查。

### Failure fixture

`PIH-01` 是结构有效的 H1，但省略 synthetic-only 限制、mediator 未测量项，并把下一动作从有界
replication search 改成 downstream synthesis。它证明 Schema 不知道来源中的 decision-changing
negative；不证明 Skill 可以稳定发现这些内容。

### Compact candidate hypothesis

若真实失败重复，可尝试一个短 output/integrity Skill，只做三件事：

1. 从 Task completion/stop conditions 和正式输出提取 decision-changing obligations；
2. 强制把 negative/unknown 与对应下一动作成对写入；
3. 超出 allowlist 或无法定位时返回 incomplete/blocked。

它不得读取完整 Trace、重写科研结论、决定 Claim、补引用或授予权限。

### Current decision

`hold-no-skill`。保留 Need 与 fixture；先在 M7-013 复用模板，等待至少两个独立 Task 家族的遗漏。
若模板同样有效，关闭 Need；若失败只来自 Task required outputs 不完整，修 Task contract。

## 2. `NEED-INT-AUDITED-TRANSFER`

### Need

H2 的 Manifest/Audit 能证明条目、hash、locator、section 和 mapping 覆盖，却不能证明执行者在
Manifest 源头列全了关键项，也不能单靠结构映射证明 Handoff 改写保持语义。

### Trigger / non-trigger

- trigger：压缩、关键 promotion、摘要争议、会话销毁或 Task 明确要求 H2；
- non-trigger：普通 H1；无跨上下文转移；结构缺失可由现有 checker 直接阻断；
- blocked：source ref/hash、Manifest identity 或 required mapping 不完整；不得进入语义补救。

### Direct baseline

使用 H1 baseline，加 Transfer Manifest/Audit、`rwb handoff audit-transfer` 和风险触发的独立人工
sample。未抽样的结构 PASS 只能称 `structurally-ready`。

### Failure fixture

`PIH-02` 将 Manifest 的“does not support a causal claim”改写为“supports a causal claim”，但保留
合法 locator 与 section。预期 deterministic assessment 仍为 `structurally-ready`，同时报告
`HANDOFF-SEMANTIC-UNREVIEWED`。这正是既有 ADR 已声明的结构边界，不是 checker 缺陷。

### Compact candidate hypothesis

只有真实案例显示 Task policy 与 bounded Human sample 仍不足时，才考虑短 integrity Skill：

1. 建议需要语义抽样的条目，不替代 Human reviewer；
2. 对比 Manifest statement 与 Handoff target，生成待审差异；
3. 只返回 sampled item、locator、差异和不确定性，不宣称语义等价。

确定性字符串/引用比较仍应下沉 Tool。Skill 不得变成所有 H2 的常驻 reviewer。

### Current decision

`hold-no-skill`。当前 direct baseline 已明确 Human sample 是语义 Gate；先验证 H2 trigger 与 sample
是否足够。只有跨 Task 重复出现“应抽但未触发”或“抽样准备成本过高”才进入 compact trial。

## 3. 共同进入条件

两个 Need 都必须满足以下条件才可从 `hold-no-skill` 进入 candidate package：

1. 至少两个不同 Task 家族重复同类语义失败；
2. failure 不是缺字段、坏 hash、错误 locator、越权读取或 Task contract 遗漏；
3. direct baseline 与修订 Task policy 仍无法在可接受成本下解决；
4. 候选正文不复制模块文档，且默认只读 Task、正式输出索引与明确 locator；
5. 有 no-Skill/template-tool/compact Skill 三臂对照和 M3-008 Trace；
6. Human Gate、Claim ceiling、读取和权限边界不变。

当前结论是两项都继续作为 Need，而不是 Skill。下一动作应收集独立 Task family，而不是初始化
`.agents/skills` 或修改 Registry。
