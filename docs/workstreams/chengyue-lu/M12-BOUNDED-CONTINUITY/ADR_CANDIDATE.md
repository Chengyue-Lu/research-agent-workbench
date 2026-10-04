# Topic 5 ADR 候选：闭合 action 边界后的文件式接续

状态：**PROPOSED / pre-activation drafting input**。本文件不占用正式 ADR 编号，不接受架构、不激活 M12，也不授权实现。

日期：2026-10-04。语义责任人：路诚钺（`Chengyue-Lu`）；执行 consumer / Host 接口责任人：黄毅（`let778750-cpu`）；起草 actor：assistant。对应 [Task 定义候选](TASK_DEFINITION_CANDIDATE.md)。

## 1. 问题与已知地基

用户需要在上一 action 完成、原进程结束后，只凭项目文件执行原 Task 内下一项已经冻结的 action，得到新产物及真实执行闭合。当前缺口是消费方接续，不是增加恢复预检条目。

- [ADR-0009](../../../decisions/0009-FILE-FIRST-CONTINUITY-AND-SAFE-PAUSE.md) 已接受文件优先、Main State 恢复入口、原子发布及生命周期完成与合同满足分离；[ADR-0006](../../../decisions/0006-CONTEXT-AND-EXECUTION-RECEIPTS.md) 要求未知量保持未知。
- [M10-003 / M3-009](../../../TASKS.md) 已完成 bounded machine prerequisite；[ROADMAP](../../../ROADMAP.md) 仍明确 Phase C Human/R2 semantic closeout 与独立 Topic 5 R2 architecture/task-definition 条件。
- [recovery.py](../../../../src/research_workbench/execution/recovery.py) 的 `prepare_recovery_attempt(...) -> RecoveryPreparation` 只预检、返回可选 `RecoverySeed`，不创建新 Attempt。它要求旧 Attempt/Main State 为 `safe-paused`，并沿 legacy Skill lock / Assignment 取值，不能直接当本候选的 no-Skill consumer。
- [Host](../../../../src/research_workbench/execution/host.py) 的 `execute_frozen_view(...)` 最多调用一个 pre-bound Driver 一次，并重验 freshness、Bundle 与 binding；[generic closeout](../../../../src/research_workbench/execution/generic_closeout.py) 已支持 no-Skill/direct-tool actual facts、Trace、Artifact 与 Validation 的 Receipt 闭集。Receipt 的 `topic5_recovery:false`、`task_completion:false` 保持原义，不因 M12 复用而改成 true。
- [模块 05](../../../modules/05-TASK_AND_HANDOFF.md) 如实保留 legacy Attempt/Handoff/Receipt 的 mandatory Skill gap；[handoff_transfer.py](../../../../src/research_workbench/context/handoff_transfer.py) 消费现行 `handoff_packet`，不能用空值、虚构 Skill 或 Markdown 摘要假写成已经适配。

以上是静态接口核对，未运行接续或测试。[PR72 的入口方案](../../huangyi/M12-M13-ENTRY/ENTRY_PLAN.md) 是审查输入，其合并或普通 APPROVE 不自动填充具名 Gate 决定。

## 2. 建议决定

首个交付只支持 **completed action boundary → one already-frozen next action → new unique Attempt in a fresh OS/Python process**。调用方显式启动新进程；RWB 不建立常驻调度服务，也不管理窗口生命周期。

源边界必须已有 replay-valid completed action Receipt、完整 actual Trace/Artifact/Validation 和闭合 Handoff。Main State 表示上层 Task 仍未完成、当前 `stage-completed`，明确引用旧边界与下一 action。一个 Task 可以包含已冻结的后续 action；接续只消费其中一个 exact slice，不生成新研究计划。

这里的 `stage-completed` 是本候选所选入口，不把运行中的 Attempt 改写为 `safe-paused`。现行 legacy recovery 路径继续按原契约回放；失败、waiting、blocked、in-flight 与 salvage 不进入本首版。

### 对象职责

| 对象 / owner | 负责什么 | 不产生什么 authority |
|---|---|---|
| Task / Research Control | 预先冻结原 Task revision、next action identity、输入/输出、权限、预算与停止条件 | 不以接续请求扩写原 Task |
| Research State | Evidence/Claim/Decision/Failure、研究前提和适用限制；按 exact refs 读取 | 不从进程成功推出 Claim 或科学接受 |
| Main State / checkpoint | 小型控制恢复入口：protocol revision、约束、决定、已完成边界、下一动作、machine refs/digest | 不复制研究正文，不成为另一个 research state store |
| Handoff | 指向旧产物、actual Trace/Receipt、失败/限制/未完成/需人类决定项的最小充分交接 | 不是新权限、新 Supply 或成功事实的来源 |
| Attempt lineage | 同一 Task revision 下旧 Attempt / completed slice 与新 Attempt / next slice 的 ref-only 关联 | 不把 `previous_state_ref` 当成新 Attempt 的 `state_at_attempt_ref` |
| Capability Resolver | 唯一 compare/qualify/select owner；必要时产生新的 Resolution/Snapshot | consumer 不代选，不沿用 stale selection 冒充有效 |
| Bundle / View producers | 按 Resolver 已冻结的 selection 构造新的 exact allowed-read closure 与最严边界 | 不重选 Supply；View 不扩大 Task/Policy/Supply ceiling |
| M12 consumer | 校验边界和 lineage、排他认领本次目标 Attempt、调用既有 Host 一次、固化闭合 | 不 fallback/retry/rebind，不授予 Method/Claim/Gate 权限 |
| Thin Host / M11 closeout | 重验并消费 exact View + Bundle，记录实际调用/产物/Trace，独立 replay Receipt | Receipt 仍只证明 action/capability slice |

`state_at_attempt_ref` 指本次执行时冻结的 Research State；`previous_state_ref` 只表示 predecessor，Main State checkpoint ref 则是控制恢复入口。三者不得因路径相邻或摘要相似互换。Research State 或具名 Decision 表明前提已变化时，返回阻塞并交原 Control/Human 决定，不由 consumer 推断“仍适用”。

### no-Skill 兼容选择

建议在独立 R2 定义时接受一个**窄、版本化、供给中立的 Attempt/Handoff 边界投影**：只承载 existing Task/Main State/Research State、旧 generic Receipt/Trace/Artifact/Validation refs、已冻结 next action 和本次 target Attempt refs；不承载新的 scientific truth、Supply selection 或 mutable global cursor。它是既有对象的接续投影，不新增 continuity 数据库。

实现仅需本 slice 的 no-Skill 结构和 validator。legacy Schema 保持可显式回放，不同版本不得静默重解释；本轮不做全仓 Attempt/Handoff migration。H2 的负面条目/哈希/定位/语义抽查语义沿用 [ADR-0011](../../../decisions/0011-RISK-TIERED-HANDOFF-AND-CONTROLLED-READS.md)，但现行 audit validator 尚不能自动证明新投影合格；其最小映射和版本在 R2 中明确后才能实现。

这项兼容选择尚未获接受。具名审查也可要求复用既有版本化对象的最小扩展；两种写法都必须保持原 version 可回放、no-Skill 无伪造 Assignment、唯一事实来源和 direct consumers 明确。未定前不编码。

## 3. 接续算法边界

1. 原 action 闭合时生成源 checkpoint / Handoff，冻结 next action refs 和本次唯一 target Attempt ID/path。消费者只接收此请求及显式 refs；可沿其闭包读取，不扫描目录、历史聊天、Registry、Skills 或研究语料。
2. 新进程重载并按字节 hash 验证 Task/protocol、Main State/digest、Research State、旧 actual closeout、Handoff、next action 的 Resolution/Snapshot/Bundle/View。校验旧 slice 与 next slice 不同、next slice 确已冻结、权限/预算仍适用且无 pending Human Gate。执行闭包可以在旧 action 闭合后由既有 producer 构造，但必须在源进程结束前冻结。
3. 对请求绑定的目标目录做原子、排他认领；ID 不能复用，目录必须此前不存在且位于声明 write scope 内。单纯 `exists()` 预检不能替代实际排他创建。同一源请求绑定同一 target ID/path；换 ID/path 是新的显式请求，首版不自动生成。重复/并发消费原请求只能有一个认领者，未认领者零调用。
4. 源 checkpoint、旧 Attempt、旧 actual Trace/Receipt 与源输入只读。只在新 Attempt 内写 lineage/观察证据、Host report、实际工件、Trace/Validation、generic Receipt 和本次 Handoff；源指针不原位滚动更新。需要更新 Main State 时由控制面另行发布新 checkpoint，不由 Host 改旧 checkpoint。
5. 在 Host 的既有 preflight 后，通过 trusted `dispatch_guard` 再验证排他认领和 source-bound request 未漂移；guard 只能收窄 dispatch。freshness/binding/Supply 失效时记录 bounded Diagnostic / re-resolution request，返回原 Resolver；本次不重选、不替换 View、不重试。
6. 已调用后用实际 facts 闭合输出；generic closeout 独立校验 typed hash-pinned execution fact、output identity/hash、Validation 闭集及 View/Host/Trace 一致。缺 facts、缺 output、Receipt replay 失败保留为 failed/incomplete；不能改写 completed。若 Driver exception 没有完整事实，保留 gap 和失败，不能伪造 receipt-eligible closeout。

预检阻断允许留下本次拒绝/Diagnostic 的有界审计证据，provider/tool/procedure dispatch 均为零；不形成 success-qualified Attempt、actual binding 或 output-completed 事实。Host 若可产生 replay-valid `blocked` Receipt，只保留其 `completion_claim:none`；阻断记录不当成功接续。

首版只保证同一冻结请求的排他消费和本地输出隔离。没有外部副作用的 exactly-once guarantee、崩溃后自动解锁或自动重试；认领后事实不完整时保留目录并停止，由具名 owner 决定另一个任务。

## 4. 首个离线用例与最小验证

复用 [整数递推工程例](../../../../examples/run-reconstruction/linear-recurrence/manifest.yaml)中的 [simulate.py](../../../../examples/run-reconstruction/linear-recurrence/simulate.py)、[parameters](../../../../examples/run-reconstruction/linear-recurrence/parameters.json.txt) 和 [inputs](../../../../examples/run-reconstruction/linear-recurrence/inputs.json.txt)。源码静态行为为 `x[n+1] = a*x[n] + u[n]`，当前值 `x0=0,a=1,u=[1,-1,2,-2]`；写出 `trajectory.csv`，只允许整数且输入长度不超过 1000。本例的零净变化是 synthetic 工程结果，不是科学 Claim。

建议 fixture 在同一 Task 内预先固定 A（输入冻结/验证并实际闭合）与 B（调用该整数程序）；源进程完成 A 和 checkpoint 后退出。独立新进程 B 只读上述 pinned bytes 和 exact control/lineage refs，通过 direct-tool Driver 执行一次，在新 Attempt 输出 CSV 并形成 M11 actual Trace/Receipt。不能把原 manifest 的 reconstruction timeout、旧 Run 或输出 hash 当成 M12 的执行授权。本候选尚未构造/冻结执行 manifest、A/B Task、运行资格材料或输出 layout。

未来只验证一条正常接续，以及直接破坏该路径的三组故障：pin/freshness/binding 漂移；缺失/错误 next action 或许可/Human 条件；同一请求/目标目录重复消费。再检查 actual output / Trace / Receipt 的必要闭集反例。记录实际读取量、准备/执行时间和人工纠正；无 token 数据标 unknown。无需性能阈值、kill 笛卡尔矩阵、模型 API、实时取消或科学 benchmark。

## 5. 接受顺序与停止条件

1. 路诚钺在 exact Phase C 输入上作具名 Human semantic decision；黄毅核对 execution fact interface；R2 closeout 保存接受范围、残留限制及实际审查证据。
2. 之后进行独立 Topic 5 R2 architecture review，决定本边界、no-Skill 投影/兼容选择及两个 owner 的职责。具名接受记录必须绑定当轮候选的完整 commit HEAD、实际 ADR/Task 候选字节 pins、所消费 Phase C closeout exact refs 与接受范围；旧 develop base、未提交候选或笼统 APPROVE 不能代替该绑定。候选自身不自填接受记录；后续改动使接受适用性待重验。
3. 独立 docs-only `task-definition` 才可在 canonical TASKS 分配/激活首个正式 Task、确立写入路径/Schema consumer/验收；本文件中的 `M12-001` 仅为候选标签。
4. 真实闭合前只准备文档和隔离工程材料；闭合后按已接受 Task 实现、检查、正常 PR，保持不代 merge。

M5/M14/Skill admission 不增加为本 no-Skill 接续的 hard dependency；M13 保持 RESERVED。本轮只起草文档，不改 Schema/Runtime。未来首版只允许独立 R2 接受的 exact Task scope 内必要的 no-Skill 投影与直接 consumer delta；该范围之外的跨模块 Schema/Runtime 改动仍禁止。首版不恢复 in-flight call、不实现安全暂停消费/salvage、不运行 Provider/API、不实现外部 side effect 恢复、不自动 Task completion、Claim promotion、Human acceptance 或科学接受。扩展这些范围另以具名 Task/ADR 接受。

本 ADR 候选的有效结果是可审查设计输入，既有 validator PASS 与本轮文档检查都不构成其接受。
