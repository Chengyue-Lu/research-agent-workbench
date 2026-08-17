# Accepted Skill 0.1.0 迁移决定

- 责任人：路诚钺
- 日期：2026-08-18
- 对应任务：`M7-004`
- 状态：迁移决策基线完成；历史包冻结，新分配按 Mode action 停用
- 机器夹具：[`accepted-skill-migration-v1.yaml.txt`](../../../examples/mode-skill-routing/accepted-skill-migration-v1.yaml.txt)

本文把三个早期 accepted Skill 从“可用库存”重新解释为“历史可解析原型”。决定只影响新的
Task 规划与路由，不原地改写已被内容哈希和包哈希锁定的 `0.1.0` 包，也不把文档结论伪装成
真实 Agent 效果证据。

## 1. 总结决定

| Skill | 当前包 | 新 Task 默认 | Mode-action 迁移 | 版本决定 |
|---|---|---|---|---|
| `literature-evidence-extraction@0.1.0` | `legacy-frozen`，保留历史 Assignment 解析 | 不分配 | ES-A3 用 `document-read`；ES-A4 用 Task contract + `research-contract-check`；ES-A6 回到 `NEED-ES-CONFLICT-SYNTHESIS` | 不创建 `0.2.0`；真实困难任务证明方法增量后再从 Need 新建 |
| `simulation-vv@0.1.0` | `legacy-frozen`，保留历史 Assignment 解析 | 不分配宽泛 bundle | SIM-A2/A6 为 Tool；SIM-A3/A4 为两个独立 Need；SIM-A5/A7 为 Mode/Task/checker/Human Gate | 不创建 `0.2.0`；禁止把 A2–A7 重新捆成单一 Skill |
| `handoff-integrity@0.1.0` | `deprecated-wrapper`，历史包暂留 Registry | 禁止分配 | 结构检查归入 `research-contract-check`；H2 语义转移义务归 Task/Trace/Human sample | 无替代 Skill 版本；wrapper 退役 |

这里的“不分配”是新的 Mode-action 路由政策，不是当前 Runtime 已执行的 lifecycle 状态。现有
accepted Registry 只接受 `status: accepted`，Task 只写 Skill ID，不支持精确版本约束，而且同一
Skill ID 不能并存多个版本。因此，本次若直接写 `deprecated`、增加 `0.2.0` 或删除条目，会破坏
Registry 加载或历史 Assignment 的可解析性。

## 2. 不原地改包的理由

三个原型的冻结身份如下；机器夹具逐项与 `accepted.json` 及实际包哈希核对：

| Skill | content hash | package hash |
|---|---|---|
| `literature-evidence-extraction@0.1.0` | `c0a080ea9c4743a599000bc6978386a8dcbb8aaa09e1ed4c0e54a4deadca780b` | `60c8b11adc147fbcb3c0d1c79d05c441d3143f446502a5b12c73f1b8b04895cb` |
| `simulation-vv@0.1.0` | `2a3c19b5af6288c4d5eab6e2fc2557231cc684f0ec9b6ec8bb5b864d126a99c4` | `e71c2977b8b839b7b7edc3e3af8b5a923f46c96ad44d30adc23c965bf8f96040` |
| `handoff-integrity@0.1.0` | `2a4c727eb7462628e9f246a5363a8add1ba244c05b6c7b7e7b2ad450befabbf7` | `7ef583e26e3759705ae2c4b75f978e80cce01b5307f858570601fb44fcd5d1cd` |

迁移遵循三条规则：

1. 历史对象只读冻结；任何正文、script、reference 或 manifest 改动都必须产生新版本和新哈希。
2. 没有 Mode-derived Need、困难任务和 Trace 证据时，不创建“修订版”占位包。
3. Tool、Task template、Mode invariant 和 Human Gate 足够时，以 no-Skill 为完成结果。

因此，本轮没有初始化新 Skill 包。`skill-creator` 的 trigger/non-trigger、短正文和渐进披露原则
只作为未来 Need 通过 Gate 后的 authoring 约束，而不是补写三个缺乏证据的新版本。

## 3. 逐项迁移

### 3.1 Literature evidence extraction

`0.1.0` 中仍值得验证的部分是原子 Evidence、来源陈述与 Agent 推断分离、负面/冲突/缺失
证据保留和 Claim ceiling。它们只对应 ES-A4 的潜在方法增量，不足以证明整个 Skill 应被保留。

- ES-A3 的读取、固定、hash 和 locator 是 `document-read` 与 Artifact contract。
- ES-A4 默认先用 Task contract 加 Evidence checker；结构检查通过不等于语义提取正确。
- ES-A6 的冲突综合不沿用本 Skill，而进入 `NEED-ES-CONFLICT-SYNTHESIS`。
- H0/H1 不强制 Transfer Manifest 或额外 Handoff Skill；H2 由 Task 风险触发。

若未来 ES-A4 对照测试证明短 Task contract 不足，再从 `NEED-ES-ATOMIC-EVIDENCE` 或等价明确
Need 创建新 Skill；它不自动继承 `0.1.0` 的固定交接依赖。

### 3.2 Simulation V&V

`0.1.0` 同时覆盖版本固定、执行、收敛、敏感性、benchmark、外部验证和 Claim 审计，导致普通
重放任务也加载完整方法说明。迁移后：

- SIM-A2/A6 使用 `bounded-compute`、Artifact contract 和 `research-contract-check`；
- SIM-A3 进入 `NEED-SIM-CONVERGENCE-STUDY`；
- SIM-A4 进入 `NEED-SIM-SENSITIVITY-UQ`；
- SIM-A5 由 Mode、Task 方法参考和 Human Gate 处理；
- SIM-A7 由 Mode invariant、checker 与 Human Gate 限制 Claim。

这意味着不创建一个更短但仍跨 A2–A7 的 `simulation-vv@0.2.0`。两个方法 Need 后续可以各自
失败、退役或产生窄 Skill，不共享“V&V 全包”生命周期。

### 3.3 Handoff integrity

该包的确定性价值已经由 `check_handoff.py` 表达；模型说明不能覆盖“Task/Handoff 是否同一
revision、引用是否存在、hash 是否匹配”这些检查。迁移后的职责为：

- `research-contract-check` 统一承载 Schema、hash、reference、coverage 与状态转换检查；
  `check_handoff.py` 是其中一个现有实现入口，不另造同义 Tool card。
- H2 必须转移哪些 Decision/Evidence/limitation/negative result，由 Task/Trace template 决定。
- 语义等价与科学含义仍需有界人工抽样；结构 PASS 不得覆盖语义失败。
- 新 Task 不再加载 `$handoff-integrity`；历史显式 Assignment 继续靠冻结包解析。

这是一项 wrapper deprecation，而不是删除 checker，也不创建新的“交接 Skill”换名替代。

## 4. 当前生命周期缺口

当前代码把“包是否存在且哈希有效”和“新 Task 是否仍可选择”合并在同一个 accepted Registry。
完成真正的 Runtime lifecycle 还需要一个独立小切面：

1. 保留可解析的历史版本，同时为新 Assignment 表达 `active | legacy | deprecated` eligibility；
2. Task/Assignment 使用 `skill_id@version` 或等价精确约束，不能只凭 ID 取唯一版本；
3. 自动选择只能看 `active`，显式选择 legacy/deprecated 必须有迁移或 replay 意图；
4. 旧 Assignment 的 Registry digest、Skill locks 与工件 hash 继续可验证；
5. migration fixture 同时覆盖 historical replay、new assignment block 和 version ambiguity。

这个缺口记为 `M7-015`。它属于 Skill Registry/Resolver 语义，不涉及 Provider、API、模型或 Runtime
Adapter。完成前，本文与机器夹具是规划 Gate，不能声称代码已经阻止所有旧 Skill 新分配。

## 5. 完成与未证明边界

M7-004 已完成的是：三个原型逐项绑定 action、direct baseline、冻结 manifest/hash、no-Skill 或
Need 路径和版本决定；迁移夹具可确定校核。未完成、也未宣称的是：

- 真实模型 with/without 增量；
- `0.2.0` Skill 的 authoring、准入或发布；
- Runtime lifecycle enforcement；
- API、Provider、MCP、外部 Tool 绑定与 live conformance。

下一步只做 `M7-015` 的 Registry/Resolver lifecycle seam，然后在 K-MS-1 节点评审停止扩张。真实
Skill 比较仍等待 `M3-008` Trace 前置条件。
