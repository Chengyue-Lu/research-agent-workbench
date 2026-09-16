# Phase C：具名语义收口输入

状态：模型辅助预检及人类审查输入；不是 Human review 结果。基线和责任见 [README](README.md)。

## 1. 为什么现在只缺这个决定

[Phase C workstream](../../chengyue-lu/PHASE-C-RESEARCH-STATE/README.md)和
[bounded Gate contract](../../../implementation/PHASE_C_BOUNDED_GATE.md)明确：M10-001/002/003、M3-009
的机器实现已经完成，当前最小表示的 Human semantic/R2 closeout 仍待接受。

[Issue38 规划接受](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38#issuecomment-5403110100)
允许探索和实现 bounded candidate；[规划收尾](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38#issuecomment-5415874531)
继续把最终人类语义决定、Topic 5 review 和未来 task-definition 分开。Issue38 CLOSED 不是最终表示已经获得接受。

本次提出的具体决定是：当前 exact-ref State、轻量 Unknown/Assumption、Evidence–Claim relation、派生 Frontier、独立 Attempt lineage/Failure/Method Trace 是否足以作为下一阶段有界连续性设计的研究意义输入，适用范围和保留项是什么。

## 2. 输入和事实解释

使用已有两个 source manifest；实际字节 pin 与核对记录见 [EVIDENCE](EVIDENCE.md)。不重新生成案例，也不把 fixture Decision 当作路诚钺或黄毅的真实签字。

| 问题 | 当前输入支持的解释 | 具名审查需要判断什么 |
|---|---|---|
| Case A 关闭了什么 | State r2 的 UNKNOWN-PC-A-01 为 resolved，来源是 D-PC-A；Claim 仍 proposed-fixture、strength unresolved，保留无因果接受的限制 | 关闭未知项与接受 Claim 的区别是否清楚，下一执行者会不会误读 |
| Case A 是否有实际执行证明 | MTRACE-PC-A 记录 applied Method/Action 与 State effect；actual_binding 是 unavailable/gap-only，fact refs 为空 | 是否保留“声明方法路径”和“观察到真实执行”的差别 |
| Case B 学到了什么 | 粗网格足够的 Assumption 已 invalidated；高分辨率是否改变结果仍 open；Failure 记录粗网格无法解析边界效应及未定原因 | Failure、负 Evidence、未解决研究问题能否分别恢复；不能推导假设已被最终证伪 |
| Case B 何时重访 | RFAIL-PC-B-001 要求更高分辨率输入先经 Human review 准入 | 学到的结果及重访条件是否足够，且不产生自动重试或输入替换许可 |
| Case B 的下一行动 | manifest 给出 repeat-coarse-grid 与 inspect-higher-resolution-input；前者关联已知 Failure | 检查可用输入与直接运行更大仿真必须区分；推荐路径不是执行许可 |
| State 与 Attempt 的关系 | Case A 两个 Attempt 可共享 State r1，State r2 可由 Evidence/Decision 独立演化 | from-State、predecessor、reopen justification 是否保留各自意义 |

表格由 assistant 阅读显式源文档形成，没有运行 fresh actor 或读取 private oracle，不能声称完成独立人类重建。Contradiction/Frontier 等未在这里全面演示的语义，须结合原表示和已存在证据审查；没有覆盖的部分可以明确限定或保留。

关键文件：

- Case A：[State](../../../../examples/phase-c/m10-001-case-a/states/RSTATE-PC-A-r2.yaml)、[Claim](../../../../examples/phase-c/m10-001-case-a/objects/CLAIM-PC-A.yaml)、[Decision](../../../../examples/phase-c/m10-001-case-a/objects/D-PC-A.yaml)、[Method Trace](../../../../examples/phase-c/m3-009-case-a/traces/MTRACE-PC-A.yaml)。
- Case B：[State](../../../../examples/phase-c/m10-001-case-b/states/RSTATE-PC-B-r2.yaml)、[Failure](../../../../examples/phase-c/m10-002-case-b/failures/RFAIL-PC-B-001.yaml)、[Decision](../../../../examples/phase-c/m10-003-gate/case-b/closure/objects/D-PC-B.yaml)、[Method Trace](../../../../examples/phase-c/m10-003-gate/case-b/closure/traces/MTRACE-PC-B.yaml)。

## 3. 待完成的具名记录

| 内容 | 当前结果 |
|---|---|
| 路诚钺对最小表示、研究含义与适用范围的决定 | PENDING |
| 黄毅对当前 M11 execution fact / Method Trace 接口的具名意见 | PENDING；assistant 已核对 per-Attempt gap 与全局 producer 存在是两件事 |
| 对保留项或具体不可表达问题的判断 | PENDING；不能以机器 PASS 代填 |
| Phase C Human/R2 closeout | PENDING；不得由本材料自动推导 |

记录可以采用文档或正式 review：列明评审人、日期、exact 基线与两个 manifest pin，逐项给出接受、限定接受或需修正的理由，说明是否允许进入独立 Topic 5 设计。无需增加签名系统、Decision Schema 或新测试框架。

建议讨论的结论是“在明确范围内接受当前最小表示，允许进入独立连续性设计”。它只是候选文本；审阅者可以修正或拒绝。此后的 Topic 5 ADR/task-definition 与 feature 仍分别接受。

## 4. 接受后的最小文档收口

仅在真实决定存在后，按其范围更新 ROADMAP Phase C、TASKS Topic 5 Gate 说明、两个 Phase C workstream 的当前状态和 implementation 文档的 pending 提示。旧机器报告中的 Human pending/Topic5 false 仍准确描述当时执行，不改成今天的接受证明。原 M10/M3-009 DONE 行不重定义。
