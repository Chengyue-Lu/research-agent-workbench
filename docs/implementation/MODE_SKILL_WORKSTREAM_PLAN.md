# Mode–Skill 工作流实施计划

状态：基线已实现，未关闭（`M7-006 IN_PROGRESS`）

日期：2026-08-16

## 1. 目标与停止点

本计划由路诚钺维护。黄毅负责 API Adapter、API session、live conformance 及其测试。路诚钺当前目标是把“任务特征 → Research Mode → 能力要求 → Skill 候选 → 显式选择/不选择 → 评估与准入”打磨成可解释、可回放、可删减的决策链。

`K-MS-1：Mode–Skill Selection Baseline` 的契约、Registry、fixtures 和确定性校验已实现，但节点尚未关闭。`M7-002..005` 已完成；`M7-006` 只有 fixture-only 对照，必须在可比实际 H1/H2 Attempt 上补齐运行时与成本证据后再做节点评审。评审前不批量新增 Mode 或 Skill。

`K-MS-1` 的完成条件：

1. 形成 Mode 触发、非触发、组合冲突和新增准入规则；
2. 至少 6 个代表性 Task fixture 覆盖 `evidence-synthesis`、`simulation`、模式歧义和“不需要 Skill”；
3. 每个 fixture 能得到 active Mode、能力缺口、候选 Skill、选择/拒绝理由和最小读取计划；
4. existing accepted Skills 至少完成一次适用/不适用边界审计；
5. 至少一个 triage candidate 得到 `reject / retain-reference / continue-trial` 的证据化决定，不要求准入；
6. 每个 fixture 分配 H0/H1/H2 Handoff 等级，并说明升级触发；
7. 每个实际 Agent Attempt 使用实名 actor 与完整 Archive 留存全部可见传递，主 Agent 仍只按需读取；
8. 没有修改 API 实现或把离线 fixture 宣称为真实科研价值。

当前验收记录：条件 1–6 的实现工件已落地，三个 accepted Skills 已完成边界审计，一个 candidate 已得到不准入的 `continue-trial` 决定。但 H0/H1/H2 比较仍是 fixture-only，尚不满足条件 7 所需的实际 Attempt 证据，因此不宣称 `K-MS-1` 关闭、H1/H2 有净收益或任一等级最优。

## 2. 当前缺口

### Mode 层

- Registry 只有 `evidence-synthesis` 与 `simulation` 两个正式 Mode；文档列出的 experiment、theory、observational-statistics、engineering-validation 仍是候选分类，不是已实现承诺。
- 两张同构 Mode 决策卡和 8 组 Task/选择 fixtures 已锁定 trigger、non-trigger、组合、歧义、no-Mode 与 Claim ceiling；这些只是可重放结构证据，不是科学正确性证明。
- accepted Skill manifests 只使用两个已注册 Mode 标签；未经真实案例和准入卡证明，不创建 experiment、theory、observational-statistics 或 engineering-validation Mode。

### Skill 层

- accepted Registry 只有 `literature-evidence-extraction`、`simulation-vv`、`handoff-integrity`；前两者只有离线合同证据，没有真实前向与增量价值证据。
- 三个 accepted Skills 已有 manifest-bound 的 trigger/boundary/non-trigger/删除条件审计，但还没有真实 with/without 增量价值证据。
- `claim-preserving-rewrite` 已得到 `continue-trial` 决定，仍留在 candidate 隔离边界内，未进入 accepted Registry 或可发现路径。
- 以任务特征为入口的选择矩阵已能解释显式 Skill、no-Skill、拆 Task、Human Gate 和拒绝理由；它不会把 fixture 通过视为 Skill 准入证据。
- Skill 评估契约较完整，但真实 baseline/with-Skill 样本、人工盲评和协调成本数据缺失。
- 供应链、方法质量、上下文成本和可删除性尚未汇总成一个简短的人类准入表。

### 协作与上下文

- H0/H1/H2 fixture-only 对照已量化字符、工件、审阅、回查、遗漏、返工、读取扩展和 capture gap；它未证明真实普通任务需要 H2，也未证明 H1/H2 的净收益。
- Agent Trace Schema、validator 与 API 两阶段 recorder 已实现；自动 API 路径覆盖 Assignment/Handoff、Provider/工具边界、受控读取结果和 closeout revision。平台不可见或当前未自动捕获的前置读取、命令与消息正文必须显式声明 capture gap，不能把 `gapped` 冒充 `complete`。
- 完整留存与克制读取已有离线 H1/H2 索引/Handoff 恢复和按 message ID 回放证据，但尚缺真实平台消息、前置命令/读取与 H1/H2 成本对照的实测。
- 责任以前用“本侧/同伴侧”表示，无法稳定追责；现已明确路诚钺与黄毅，但仍需在实际 Task/PR/Trace 中执行。

## 3. 实施阶段

### P0：冻结职责与术语

- 采用 `docs/DEVELOPMENT.md` 的实名责任制；
- 将黄毅负责的 API 任务标为 external，不再作为路诚钺的退出条件；
- 冻结 Mode、Capability、Agent Profile、Skill、Tool 的边界词汇；
- 建立路诚钺与黄毅共同确认共享接口的规则。

### P1：Mode 决策卡

状态：已完成（`M7-002`）。

为每个正式 Mode 建立同构决策卡：

- applies when / does not apply when；
- required artifacts；
- allowed 与 forbidden Claim；
- Human Gates；
- 核心风险；
- 与其他 Mode 的组合规则；
- 何种证据支持新增、拆分、合并或删除 Mode。

先打磨两个现有 Mode，不因为文档列出其他类别就补齐空包。

### P2：Task-to-Skill 选择矩阵

状态：已完成（`M7-003`）。

选择顺序固定为：

```text
Task characteristics
  → active Mode constraints
  → required capabilities
  → deterministic tool/check can solve?
  → accepted Skill candidates
  → permission/context/conflict filter
  → explicit Skill / split Task / no Skill / Human Gate
```

输出必须解释排除原因。若一个确定性工具已经足够，不为了“使用 Agent”再加载 Skill；若候选等价且证据不足，返回歧义而不是自动选择。

### P3：候选优先级

状态：accepted Skill 边界审计和首个 candidate 决定已完成（`M7-004..005`）；真实 with/without 证据仍属后续准入工作。

按以下顺序处理，不按候选总数铺开：

1. 审计现有三个 accepted Skills 的触发与非触发边界；
2. 完成 `claim-preserving-rewrite` 的 adversarial 与 with/without 决策，重点检查语义漂移和实际增量；
3. 从 `rc-papercheck` 只提取可确定性执行的 Claim/Citation 检查，不复制大工作流；
4. `rc-experiment-design` 等待 experiment Mode 的真实案例和方法审阅；
5. 搜索 API、Provider 或外部执行相关候选只保留接口需求，交由相应工作流实现。

### P4：轻量 Handoff 与受控读取演练

状态：进行中（`M7-006`）；fixture-only 对照已完成，实际 H1/H2 Attempt 的运行时与成本证据尚缺。

已用 `M3-007..008` 的 Attempt Archive、实名 actor、消息信封和手工 fixture 建立 H0/H1/H2 结构对照。下一阶段必须对可比实际 Task 记录 Handoff 字符量、完整消息/工件数、生成/审阅时间、主 Agent 回查次数、限制遗漏、capture gap 和返工。读取演练同时记录初始允许集、申请扩大的次数、实际使用的新输入和无关读取。

H1 与 H2 都保存完整 Agent 间可见消息；区别只在回传主上下文的内容和附加审计。完整 Trace 不默认加载，评估者通过 `INDEX.yaml` 选择需要回放的 message ID。

在没有真实运行数据前，不把任何固定字段数量或审计链设为“最优”。

### P5：节点评审

状态：待 `M7-006` 实际证据完成后启动。在此之前 `K-MS-1` 不关闭。

节点评审将做保留/删减决定：

- 删除没有改变决策的 Handoff 字段或触发器；
- 退回没有增量价值的 Skill；
- 合并难以区分的 capability 标签；
- 不为缺少真实案例的学科创建 Mode；
- 将 API 执行与自动 Trace 捕获缺口记录给黄毅，不在本分支补执行实现。

## 4. 分支计划

文档基线已经进入 `main`。`K-MS-1` 实现阶段使用：

```text
agent/mode-skill-selection-baseline
```

该分支只处理 `M3-007..008` 的 Trace 契约前置工作和 `K-MS-1`。当前后续仅限 `M7-006` 实际证据与节点评审；不得新增 Mode/Skill，也不得修改黄毅维护的 API Adapter、模型池、session runner、Provider conformance 或真实凭据配置。

## 5. 评估指标

| 维度 | 观察量 | 失败信号 |
|---|---|---|
| 选择质量 | 触发/非触发准确、排除理由、歧义显式化 | 依赖模型猜测或总选最多 Skill |
| 方法适配 | Mode 的 artifacts、Claim、Gate 是否改变行动 | Mode 只成为标签 |
| 上下文 | 读取正文量、未选 Skill 内容、Handoff 长度 | 主 Agent或子 Agent 默认扫描仓库 |
| 增量价值 | with-Skill 相对 baseline 的错误、遗漏、返工 | 只增加格式与审阅负担 |
| 可维护性 | Registry 重复标签、更新影响、删除难度 | 每个任务都需改内核 |
| 协调成本 | Handoff 工件数、审阅时间、回查次数 | 校核长期超过有效研究工作 |
| 可回放性 | 消息 sequence、hash、actor owner、capture gap | 只能依赖 Worklog 或聊天记忆还原过程 |

## 6. 非目标

- 不实现或测试模型 API；
- 不选择最终 Agent 平台；
- 不一次性补齐所有研究模式；
- 不把外部 Skill 下载等同于准入；
- 不用更多 reviewer Agent 解决定义不清或缺少确定性检查的问题；
- 不保存 Chain-of-Thought、密钥或无界逐 token 遥测来追求“全量 Trace”；
- 不以 fixture、格式通过或模型自评证明科学正确性。
