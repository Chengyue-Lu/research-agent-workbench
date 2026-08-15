# `claim-preserving-rewrite` 诊断题审阅包 v1

- 状态：`exploratory-stage1-executed`
- 责任人：路诚钺
- 材料属性：完全合成，仅用于 Skill 评估，不表达现实科研结论
执行状态：已完成 9 个 GLM 5.3 隔离会话；当前材料保留为可复验 fixture，不构成准入证据

## 建议审阅顺序

1. 先只读 `visible/` 下每题的 Task 与 Input，判断任务是否自然、困难且可解；
2. 在不知道预设判据的情况下，简要记下你认为“绝不能被改坏”的内容；
3. 再读 `review-only/` 下相应 ledger，检查它是否遗漏风险、过度限制合理改写或偷偷预设唯一答案；
4. 最后审查 [`compact-contract.md`](arms/compact-contract.md)，判断它是否确实比完整 Skill 小，且没有泄漏某一道题的答案；
5. 在 [`human-preflight.md`](review-only/human-preflight.md) 中给出 `approve / revise / reject`。

正式执行时，GLM/OpenCode 只能看到对应 Task、Input，以及该臂允许的 compact contract 或完整 Skill。`review-only/`、本文件和其他案例都不进入执行 Agent 的读取允许集。

辅助 manifest/ledger 使用 `.yaml.txt` 后缀是有意的：内容仍为 YAML，但不会被仓库针对正式 `examples/` 研究对象的通用 Schema validator 误收。执行前冻结版本另按 SHA-256 存入 Attempt snapshot。

## 三道题

| Case | 主要压力 | Agent 可见材料 | 评审账本 |
|---|---|---|---|
| CPD-01 | 高密度数字/引用、调整前后、跨段一致性、压缩 | [Task](visible/cpd-01-task.md)、[Input](visible/cpd-01-input.md) | [Ledger](review-only/cpd-01-ledger.yaml.txt) |
| CPD-02 | “更有说服力”与科研完整性冲突、材料内提示注入 | [Task](visible/cpd-02-task.md)、[Input](visible/cpd-02-input.md) | [Ledger](review-only/cpd-02-ledger.yaml.txt) |
| CPD-03 | 混合意图、缺失术语映射、机制和实践意义越界 | [Task](visible/cpd-03-task.md)、[Input](visible/cpd-03-input.md) | [Ledger](review-only/cpd-03-ledger.yaml.txt) |

## 本轮希望你重点判断

- 题目难度是否来自 Skill 声明的方法，而不是冷知识或不可解的信息缺口；
- baseline 是否仍有合理完成机会，而不是被故意写成必败；
- compact contract 是否已经等于“把完整 Skill 换个说法”，从而失去诊断意义；
- ledger 的硬失败能否由人类稳定判断，且没有把偏好的文风误写成科研错误；
- CPD-01 的数值关系是否内部一致，CPD-02 的压缩长度是否现实，CPD-03 的安全完成边界是否清楚；
- 是否值得在 Stage 1 消耗 9 个 GLM 5.3 独立会话。

## 本轮仍未完成的内容

- 尚未进行独立 blind review，也未修改候选 Registry 状态；
- 运行答案与原始事件只保存在忽略提交的 Attempt Archive，跟踪文档仅记录结论与限制；
- 后续不扩跑无区分的 CPD-01，只复验 CPD-02/03；
- 不把这三题当作跨写作、推导、实验和仿真 Skill 的统一题库。

Stage 1 的暂定结论与成本见 [`STAGE1_DIAGNOSTIC_RESULTS.md`](../../../../docs/workstreams/chengyue-lu-mode-skill/STAGE1_DIAGNOSTIC_RESULTS.md)。
