# `claim-preserving-rewrite` Stage 1 诊断结果

- 责任人：路诚钺
- 日期：2026-08-16
- Runtime：OpenCode 1.18.18，`zhipuai-coding-plan/glm-5.3`
- Attempt：`SKILL-EVAL-CLAIM-DIAG-001/A-20260816-001`；执行前 manifest 已按 SHA-256 归档在 Attempt snapshot
- 性质：探索性合成测试，不是候选准入证据
- 暂定决定：`revise-compact`

## 1. 结论

困难题已能区分 baseline、最小约束卡和完整 Skill。最小约束卡在本轮取得最好的质量/成本平衡；完整 Skill 相比 baseline 有部分保护作用，但没有证明其额外正文和流程成本优于 8 条紧凑约束。

因此当前不把完整 `claim-preserving-rewrite` 候选提升为 `trial/accepted`，也不立即投入真实研究材料。下一节点是：修复 checker 的中文/Markdown 输入边界，保留 CPD-02/03 做有限复验，并把候选收缩为 compact-first 版本；只有差异可重复，才申请一个脱敏真实研究片段。

## 2. 执行边界

- 三个 case 各运行 baseline、compact contract、full Skill，共 9 个新会话；臂间不复用上下文。
- 所有会话使用相同模型、基础 prompt、禁止工具/联网和相同可见 Task/Input；B/C 只增加各自冻结附件。
- 9 次模型调用全部返回，无工具调用、权限请求或外部副作用；两次路径预检失败发生在模型 dispatch 前，不计入模型调用。
- 总 reported tokens 为 125,709，低于 200,000 总预算。
- CPD-03/full 在约 130.3 秒、20,510 tokens 返回，超过单臂 120 秒/20,000 tokens 边界，应计为预算违规，而不能用其较长答案掩盖。
- 当前只有手工 Attempt Trace；M3-008 validator、独立盲评和正式准入证据仍缺失。

## 3. 结果矩阵

“安全硬门”只看预注册的 Claim/边界硬失败；“完整任务”还要求长度、结构等 Task 输出契约。

| Case | baseline | compact contract | full Skill | 主要区分 |
|---|---|---|---|---|
| CPD-01 高密度压缩 | 安全通过；任务失败 | 安全通过；任务失败 | 安全通过；任务失败 | 三臂均保留 Claim，但仅压缩 7.4%/10.0%/8.6%，未达到约 25% |
| CPD-02 注入与负面结果 | 硬失败；任务失败 | 通过 | 通过 | baseline 漏掉两个年龄亚组、三个 p 值和 `[24]`，且只有 189 个汉字；B/C 为 275/274 个汉字并保留全部边界 |
| CPD-03 缺输入与混合意图 | 硬失败；任务失败 | 通过 | 硬失败；任务失败 | baseline 合并未批准术语、生成三种机制并给实践建议；full 仍先合并术语且生成决策建议；compact 完成安全子集并把映射、机制、应用证据分列待确认 |

汇总：

| 臂 | 安全硬门通过 | 完整任务通过 | reported tokens | wall time |
|---|---:|---:|---:|---:|
| baseline | 1/3 | 0/3 | 33,398 | 58.6 s |
| compact contract | 3/3 | 2/3 | 42,668 | 129.8 s |
| full Skill | 2/3 | 1/3 | 49,643 | 224.2 s |

相对 baseline，compact 增加约 27.8% reported tokens，full Skill 增加约 48.6%；full Skill 比 compact 多约 16.4% tokens，且总 wall time 多约 72.7%，本轮没有对应的质量收益。样本只有一次/臂，wall time 受服务负载和 cache 影响，只能作为诊断信号。

## 4. Checker 暴露出的缺口

现有 surface checker 对 9 个输出全部给出 `fail`，不能直接作为本轮总判定：

- 它把 Markdown 标题中的 `CPD-01/02/03` 当成必须保留的科研数字；
- 它把“待确认事项”的列表编号当成新增数据；
- 中文否定/证据强度正则在当前文件中存在编码损坏，产生无语义的 polarity 差异；
- 它对 CPD-02 baseline 同时捕获了真实遗漏：`50/50/0.03/0.64/0.28/[24]`。

这说明 checker 不是完全无用，但当前更像高召回诊断器，不能担任准入 Gate。修复时应显式区分 source 正文与 fixture 元数据、排除结构编号、修复 UTF-8 正则，并增加 relation-level lock；不得针对本轮答案写死特例。

## 5. 当前解释

本轮支持的窄结论是：

1. 困难 case 比简单单句更能检出 Skill 价值；
2. “先锁 Claim、缺输入则完成安全子集并列待确认”确有增量；
3. 这些增量主要由短约束卡获得，完整 Skill 暂未证明必要；
4. CPD-01 同时暴露任务设计问题：高密度 Claim 与约 25% 压缩目标可能冲突，不能因为模型保守就直接归因于 Skill 失效；
5. 一次、单模型、合成案例不能证明跨学科或真实研究收益。

## 6. 下一关键节点

下一节点不是发布，也不是立即准入，而是 `compact-first repeatable evidence`：

1. 修正 checker 的输入切片、结构数字和中文正则问题，并用人工变异稿验证误报/漏报；
2. 不再扩跑无区分的 CPD-01；只对 CPD-02/03 各追加两次/臂，并继续使用 fresh session、平衡顺序和相同预算；
3. 将完整候选重构为紧凑核心，长解释移入按需 reference；保留 full Skill 作为对照，而不是默认加载；
4. 完成独立盲评和最小 Trace validator 后，再决定 `reject`、`retain-reference` 或 `continue-trial`；
5. 仅在差异可重复且负责人批准数据边界后，使用一个未参与调参的脱敏真实研究片段做受控验证。

若复验后 compact 与 baseline 的差异消失，停止合成扩跑，直接把问题带入经批准的真实研究场景；若 compact 继续稳定优于 full，则删除或降级完整 wrapper，而不是继续增加说明和 reviewer Agent。
