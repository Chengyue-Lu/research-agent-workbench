# Accepted Skill 重叠审计

- 责任人：路诚钺
- 日期：2026-08-16
- 对应任务：`M7-004`
- 状态：历史审计输入；后续决定见 [`ACCEPTED_SKILL_MIGRATION.md`](ACCEPTED_SKILL_MIGRATION.md)
- 证据边界：当前三个 accepted Skill、manifest、确定性 checker、既有 fixtures 与首批候选 dossier；本审计不宣称真实模型增量或科学正确性。

## 1. 结论

| Skill | no-Skill / direct-tool 基线 | 仍有价值的语义增量 | 审计结论 |
|---|---|---|---|
| `literature-evidence-extraction` | `document-read` 加 `check_evidence_record.py` 可完成读取、Schema 和 locator/hash 结构检查 | 原子化 Evidence、来源陈述与 Agent 推断分离、保留反证/缺失、限制 Claim ceiling | `retain-revise`：保留方法 Skill；Transfer Manifest 与 `handoff-integrity` 改为 Task/H2 触发，不再每次强制 |
| `simulation-vv` | `file-read`/`bounded-compute` 加 `check_vv_report.py` 可检查报告字段、hash 语法和 evidence refs | 区分数值验证、模型假设、校准和外部验证；独立检查收敛、敏感性、基准与 Claim ceiling | `retain-revise`：保留方法/完整性 Skill；移除未准入 Mode 的隐式适用并取消普通任务的强制 Handoff Skill |
| `handoff-integrity` | `check_handoff.py` 已覆盖 Task/Handoff 匹配、输入锁、Skill 锁、引用存在性和 Transfer coverage | H2 中决定“哪些语义项目必须转移”与有限人工抽样，但这应由 Mode/Task 风险策略定义 | `deprecate-wrapper`：迁移为确定性 `handoff-validation` Tool + H2 Task 模板；在 Tool card 和 Resolver 迁移完成前暂不从 Registry 删除 |

这三个结论都不是立即改写 accepted Registry 的授权。`M7-008` 已把确定性检查统一归入
`research-contract-check` Tool card；`M7-004` 随后冻结 manifest/hash，并用迁移夹具把新
Mode-action 路由与历史 Assignment 解析分开，避免旧对象静默改义。

## 2. `literature-evidence-extraction`

### 2.1 Trigger 与 non-trigger

应触发：输入是已冻结、有限的论文或报告集合，输出要求可定位的原子 Evidence、反证、
冲突或缺失记录，并且结果将进入后续综合或 Handoff。

不应触发：开放式文献发现、只查 DOI/题名元数据、单次定位一段原文、最终综合、因果解释、
来源权重决策、写作和 evidence graph 可视化。前四类分别属于 Tool、普通 Task、其他
Skill 或 Human Gate。

### 2.2 与 Tool/候选的重叠

- `document-read` 决定能否访问正文；`citation-resolve` 处理标识符与元数据；二者不判断
  一段正文支持什么。
- `check_evidence_record.py` 只能证明字段、locator 和 hash 结构满足契约，不能证明提取
  没有歪曲来源。
- `build-evidence-map` 在 locator、反证、unknown 上高度重叠；其独特部分是
  `supports/contradicts/qualifies/missing` 推理边和图连通性，不应复制第二套 Evidence 对象。
- `citation-management` 的检索、元数据和 BibTeX 部分不属于本 Skill；只有 claim/source
  语义核对与其相邻。

### 2.3 发现的问题与修订要求

当前正文第 7–8 步把 Transfer Manifest 和 `$handoff-integrity` 设为所有任务的固定步骤，
manifest 也把二者列为固定输出/验证。这与 H0/H1/H2 按风险分级的架构冲突，并会让普通
提取任务产生不必要的反馈、上下文和校核成本。

下一版本应：

1. 只在 Task Packet 要求、上下文即将不可逆压缩或 H2 触发时创建 Transfer Manifest；
2. 普通 H0/H1 只返回 Evidence refs、限制和 unresolved；
3. 将 `handoff-integrity` 从固定依赖改为风险触发的验证 capability；
4. 保留 Evidence 原子性、负面结果、来源/推断分离和 Claim ceiling 规则。

删除条件：若困难任务证明“原子化、反证与来源/推断分离”可由短 Task contract 稳定替代，
且质量不低于完整 Skill，则退为 Task 模板；当前只有结构 fixtures，尚不足以删除。

## 3. `simulation-vv`

### 3.1 Trigger 与 non-trigger

应触发：审查一个有版本锁和参数边界的仿真 Run，要求分别检查收敛、敏感性、基准比较、
假设、限制与可支持的 Claim ceiling。

不应触发：只是执行程序、生成图、调参优化、实验设计、软件单元测试、认证真实世界准确性，
或在没有外部验证证据时宣称物理有效。

### 3.2 direct-tool 基线与语义增量

直接运行 `check_vv_report.py` 可以发现缺字段、无 evidence ref 的 `pass`、hash 语法和
claim-ceiling 结构错误；它不能判断网格/时间步是否足以证明收敛、基准是否相关、参数区间
是否外推，也不能区分 numerical verification 与 physical validation。后一组判断是该
Skill 相对 Tool 的主要增量，仍有明确保留价值。

### 3.3 发现的问题与修订要求

- manifest 当前列出尚未准入的 `engineering-validation` Mode。下一版本只对正式
  `simulation` Mode 可解析；工程验证需求先作为 Task 标签/候选 Mode gap，不能暗中激活。
- 正文把 `$handoff-integrity` 作为每次运行的固定步骤。普通 H0/H1 只需 checker 与紧凑
  Handoff；H2 或压缩风险再加载 transfer audit。
- `bounded-compute` 是 Tool capability，不由 Skill 授权；无可用实现时应返回 capability
  gap，而不是安装依赖或换服务。

删除条件：若真实配对测试表明短 checklist 加 checker 已稳定覆盖数值/物理边界判断，则拆成
Task 模板与 Tool；在此之前保留并缩短，不扩大为全工程验证 Skill。

## 4. `handoff-integrity`

### 4.1 Trigger 与 non-trigger

当前 description 对“正式 Handoff、压缩上下文、工件晋升”均触发，范围过宽。普通 H0、
低风险 H1 以及只需 schema/hash/reference 检查的 Handoff 不应加载 Skill 正文。

真正需要语义层的场景仅包括：不可逆上下文压缩、Evidence/Claim/Decision promotion、外部副作用、
争议或 Task 明确要求的 H2。即使在 H2，Mode/Task 决定转移义务，完整性层不能发明统一科研流程。

### 4.2 迁移结论

1. 把 `check_handoff.py` 及错误代码归入 provider-neutral `research-contract-check` Tool
   capability；默认直接运行，不加载 Skill 正文，也不另造同义 Tool card。
2. 把 Transfer Manifest/Audit 的触发条件写入 H2 Task/Trace 模板和 Resolver 规则。
3. 保留一个按需 reference，解释结构 PASS 不等于科学正确性、何时需要人工抽样；它不是
   standing Skill。
4. 新路由将当前 wrapper 判为 `deprecated-wrapper`；历史版本继续可解析，不原地改写。
   Registry/Resolver 的 lifecycle enforcement 由 `M7-015` 单独完成。

该结论直接回应主 Agent 上下文克制原则：确定性失败只回传错误码与工件路径，只有风险触发
时才回读原始消息或加载语义 reference，不能让每个子 Agent 都生成并互审一套完整审计链。

## 5. 验收与下一步

- [x] 每个 accepted Skill 有 trigger/non-trigger。
- [x] 每个 Skill 有 no-Skill/direct-tool 基线和语义增量判断。
- [x] Tool、权限、上下文与删除条件明确。
- [x] 给出 `retain-revise` 或 `deprecate-wrapper` 结论。
- [x] 逐项冻结历史正文/manifest/hash，并决定不在缺少困难任务证据时创建占位新版本。
- [x] 在 `M7-008` 的 `research-contract-check` Tool card 后完成 wrapper 的新路由退役决定。
- [x] 迁移夹具覆盖历史解析、new-assignment 决定、action baseline 与版本 Gate。
- [ ] `M7-015` 实现 historical/active/deprecated lifecycle 与精确版本约束。
- [ ] 真实 with/without 价值判断等待 M3-008 Trace validator 与困难任务，不把本审计当成
  forward-test 证据。
