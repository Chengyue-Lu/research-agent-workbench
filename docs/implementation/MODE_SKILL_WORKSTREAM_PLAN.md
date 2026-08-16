# Mode–Skill 工作流实施计划

状态：准备实施

日期：2026-08-14

## 1. 目标与停止点

本计划由路诚钺维护。黄毅负责 API Adapter、API session、live conformance 及其测试。路诚钺当前目标是把“任务特征 → Research Mode → 能力要求 → Skill 候选 → 显式选择/不选择 → 评估与准入”打磨成可解释、可回放、可删减的决策链。

下一个关键节点为 `K-MS-1：Mode–Skill Selection Baseline`。达到该节点后暂停评审，不立即批量新增 Mode 或 Skill。

`K-MS-1` 的完成条件：

1. 形成 Mode 触发、非触发、组合冲突和新增准入规则；
2. 至少 6 个代表性 Task fixture 覆盖 `evidence-synthesis`、`simulation`、模式歧义和“不需要 Skill”；
3. 每个 fixture 能得到 active Mode、能力缺口、候选 Skill、选择/拒绝理由和最小读取计划；
4. existing accepted Skills 至少完成一次适用/不适用边界审计；
5. 至少一个 triage candidate 得到 `reject / retain-reference / continue-trial` 的证据化决定，不要求准入；
6. 每个 fixture 分配 H0/H1/H2 Handoff 等级，并说明升级触发；
7. 每个实际 Agent Attempt 使用实名 actor 与完整 Archive 留存全部可见传递，主 Agent 仍只按需读取；
8. 没有修改 API 实现或把离线 fixture 宣称为真实科研价值。

## 2. 当前缺口

### Mode 层

- Registry 只有 `evidence-synthesis` 与 `simulation` 两个正式 Mode；文档列出的 experiment、theory、observational-statistics、engineering-validation 仍是候选分类，不是已实现承诺。
- 缺少统一的 Mode trigger/non-trigger 测试卡，以及“现有 Mode 组合已经足够”与“必须新增 Mode”的判定门槛。
- 缺少组合模式 fixture，尚未真实验证 Claim ceiling、Human Gate 和风险规则取更严格约束。
- `engineering-validation` 已出现在部分 Skill 适用标签中，但没有正式 Registry Mode，需要决定删除标签、视为别名还是等待真实案例后建包。

### Skill 层

- accepted Registry 只有 `literature-evidence-extraction`、`simulation-vv`、`handoff-integrity`；前两者只有离线合同证据，没有真实前向与增量价值证据。
- 候选 Registry 共 24 项：4 项 triage、2 项 discovered，其余为 reference/quarantine/rejected；只有 `claim-preserving-rewrite` 已形成隔离的本地 candidate package。
- 缺少以任务特征为入口的选择矩阵。目前 Registry 能解析显式 Skill，但还不能帮助人判断“应显式选哪个、何时不选、何时拆任务”。
- Skill 评估契约较完整，但真实 baseline/with-Skill 样本、人工盲评和协调成本数据缺失。
- 供应链、方法质量、上下文成本和可删除性尚未汇总成一个简短的人类准入表。

### 协作与上下文

- 现有示例倾向完整 Handoff 审计链，尚未证明普通任务需要同等复杂度。
- Worklog 只能提供摘要，尚无 Agent Trace Schema/validator 自动保证每条 Assignment、澄清、scope change、Handoff 与 review 都被留存。
- 完整留存与克制读取尚未经过实测：需要证明可由索引/Handoff 恢复，同时在排障时按 message ID 回放。
- 责任以前用“本侧/同伴侧”表示，无法稳定追责；现已明确路诚钺与黄毅，但仍需在实际 Task/PR/Trace 中执行。

## 3. 实施阶段

### P0：冻结职责与术语

- 采用 `docs/DEVELOPMENT.md` 的实名责任制；
- 将黄毅负责的 API 任务标为 external，不再作为路诚钺的退出条件；
- 冻结 Mode、Capability、Agent Profile、Skill、Tool 的边界词汇；
- 建立路诚钺与黄毅共同确认共享接口的规则。

### P1：Mode 决策卡

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

按以下顺序处理，不按候选总数铺开：

1. 审计现有三个 accepted Skills 的触发与非触发边界；
2. 完成 `claim-preserving-rewrite` 的 adversarial 与 with/without 决策，重点检查语义漂移和实际增量；
3. 从 `rc-papercheck` 只提取可确定性执行的 Claim/Citation 检查，不复制大工作流；
4. `rc-experiment-design` 等待 experiment Mode 的真实案例和方法审阅；
5. 搜索 API、Provider 或外部执行相关候选只保留接口需求，交由相应工作流实现。

### P4：轻量 Handoff 与受控读取演练

在真实 Agent 试验前先以 `M3-007..008` 建立 Attempt Archive、实名 actor、消息信封和手工 fixture。对同一类 Task 比较 H1 与 H2：记录 Handoff 字符量、完整消息/工件数、生成/审阅时间、主 Agent 回查次数、限制遗漏、capture gap 和返工。读取演练记录初始允许集、申请扩大的次数、实际使用的新输入和无关读取。

H1 与 H2 都保存完整 Agent 间可见消息；区别只在回传主上下文的内容和附加审计。完整 Trace 不默认加载，评估者通过 `INDEX.yaml` 选择需要回放的 message ID。

在没有真实运行数据前，不把任何固定字段数量或审计链设为“最优”。

### P5：节点评审

达到 `K-MS-1` 后做保留/删减决定：

- 删除没有改变决策的 Handoff 字段或触发器；
- 退回没有增量价值的 Skill；
- 合并难以区分的 capability 标签；
- 不为缺少真实案例的学科创建 Mode；
- 将 API 执行与自动 Trace 捕获缺口记录给黄毅，不在本分支补执行实现。

## 4. 分支计划

文档基线已经进入 `main`。路诚钺随后从最新 `main` 创建：

```text
agent/mode-skill-selection-baseline
```

该分支只处理 `M3-007..008` 的 Trace 契约前置工作和 `K-MS-1`。默认写入范围为 Agent Trace/Mode/Skill 文档、Schema、Registry、fixtures、相关 resolver/validation 测试；不得修改黄毅维护的 API Adapter、模型池、session runner、Provider conformance 或真实凭据配置。

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
