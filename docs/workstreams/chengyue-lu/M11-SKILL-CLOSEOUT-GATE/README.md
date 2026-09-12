# M11-007：Skill-bearing closeout replay 任务定义

- 定义提案负责人：路诚钺（`Chengyue-Lu`），负责 M5 consumer / Skill identity 与验收边界。
- 实施责任人：黄毅（`let778750-cpu`），负责 Execution / Host actual facts / Trace / Receipt。
- Task：新增 `M11-007`，为未完成的 `M5-007` 补充显式依赖；R2、docs-only task-definition。
- 起始基线：`develop@60bdf8c28f6cf8c52c04e481e0309bbd6e8cba8b`，M5-006 已由 PR71 合入。
- 当前集成基线：`451644064f558601d5778b9b115390f882f4d260`，保留 PR74 已接受的 scaffold。
- 分支：`docs/m11-skill-closeout-gate`，目标 `develop`。
- 状态：任务定义候选，等待双方 R2 review 与合入；[Gate B](GATE.md) 仍为 UNSATISFIED。
- 来源：[Issue #55](https://github.com/Chengyue-Lu/research-agent-workbench/issues/55)、
  [ADR-0020](../../../decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md)、
  [TASKS](../../../TASKS.md)、用户授权“71已合并，M6-008正在推进，开始推进gateB任务定义”。

## 1. 要解决的缺口

M11-005/006 已将 Projection-backed Skill Supply 送入统一 Bundle → View → Host 路径。
[M11-004 Core closeout](../../../implementation/GENERIC_EXECUTION_CLOSEOUT.md) 的 builder 仍明确拒绝
Skill Supply；legacy Receipt 则依赖 Skill Assignment。因此，M5-007 尚不能从独立文件重放中证明
Skill-bearing Host 的 actual Projection / Supply / binding。M11-007 补齐这一执行事实接口。

本定义沿用既有 Runtime ownership，不修改 ADR-0020 或 M5-006 的版本化契约。这里的 READY 是实施入口；
它不表示 closeout 实现或 Gate B 已被接受。canonical 状态、依赖与验收以 TASKS 为准。

## 2. 输入与交付

硬依赖仅为已 DONE 的 M11-004、M11-006，分别传递 Core Host/Trace/Receipt 与 Projection/Supply/View
机制。M6-008 的 baseline closeout 可独立并行推进，不是 M11-007 的实现依赖。
M5-006 的已接受 overlay 是 Evaluation consumer 的接口背景；Runtime 不因该接口而加载 Evaluation 对象。

| 输入 / 输出 | 本 Task 的要求 |
|---|---|
| 冻结执行输入 | exact Task / Action / Capability slice / Attempt、Resolution/Snapshot、selected Supply/component、Bundle/View、SkillReleaseProjection 的 identity/version/path/hash 与 Skill ID/version/hash |
| Host 与 typed Trace facts | 记录 use-boundary 实际消费的 Projection/Supply/binding；闭合 Provider/Adapter/Model/Runtime/Host、实际 Tool component 与调用事实；planned View 不能替代 actual evidence |
| 版本化 closeout extension | 明确支持 Skill-bearing execution 的版本与 Schema 分派，builder、独立文件 replay validator 及必要的 typed execution-fact 扩展；保留现有 Core v0.1 与 legacy Receipt 的版本语义和回放 |
| 输出与校验 | exact Artifacts、frozen Trace、Host report 与 deterministic Validation subject closed set；拒绝缺项、偷渡、hash/identity 漂移及自报 eligibility |
| M5 consumer 接口 | 从 replay-validated result 暴露实际 Projection/Supply/binding 和生命周期，由 M5-007 在评价侧与 M5-006 overlay 比较；M11-007 不读取 candidate、Evaluation、Human Admission 或 private oracle |

Schema 的具体发布版本与字段布局由 implementation PR 明确，已发布 identity 不原位扩义。
Skill fact 必须来自 Host 的实际消费边界；若需要补充 producer/report/Trace 字段，仅限完成该证据链的
最小版本化改动。closeout 消费已冻结的 Trace，不为了让 Receipt 通过而事后重造 actual facts。

## 3. 生命周期验收

| 情形 | Replay 必须验证的事实 | Completion ceiling |
|---|---|---|
| completed | actual Projection/Supply/binding 与 selected View 逐跳相同，且由 typed hash-pinned Trace fact 独立佐证；输出与 Validation closed set 完整 | `action-capability-slice-only`，`task_completion=false` |
| post-call-failed | 保留已观测的 actual facts、输出与 diagnostic；发生 binding drift 时可以与 requested View 不同，但必须被独立 Trace fact 佐证，不能用 requested 值覆盖 | `none`，`task_completion=false`；replay-valid failure 不代表 A4 overlay equality 或可进入成功样本 |
| preflight-blocked | 可保留 requested pins 与诊断；actual binding/Supply/Projection 不得出现，Trace 不得包含 Provider/Tool 调用或 actual-execution fact | `none`，`task_completion=false` |
| driver exception / capture 不完整 | 保留可得诊断与原始事实；不足以建立独立 actual closure 时拒绝 receipt eligibility | 不补写实际事实，不宣称 replay-valid closeout |

独立 replay 从 Receipt 自身 exact refs 重新加载 Bundle/View、Projection、Supply、Snapshot、Host report、
Trace INDEX/Actors/events/typed facts、Artifacts 与 Validation，重做跨对象和生命周期 invariant。
它不调用 Provider/Tool、不依赖原 Agent session，也不以重算作者提交的布尔值代替证据验证。

## 4. 有界验证交付

实施 PR 应提供一条完整的 synthetic Skill-bearing vertical proof，以及复用该链的独立正反验收案例。
测试必须实际经过 Bundle/View → bounded Host → typed Trace → Artifact/Validation → Receipt → 文件 replay；
只调用 reducer 或比较两份作者字典不构成该 vertical proof。

- 正向：completed 与具备完整事实的 post-call-failed 可独立重放；preflight-blocked 保持无调用、无 actual facts；
  no-Skill/direct-Tool Core 与 legacy 回放继续通过。
- 反向：Projection identity/hash 替换、Supply/component 与 Snapshot/View 错绑、Host/Trace 不一致、
  缺失或伪造 typed fact、Artifact/Validation subject 缺项、preflight 伪造调用均 fail closed。
- 失败漂移反例：真实记录的 post-call drift 可保留为失败 closeout；若改写成 completed 或声称与 overlay
  相同则必须拒绝，不能为追求 equality 丢掉失败 Attempt。
- 覆盖按现行 Coverage Policy 的 critical / impact 义务提供独立 positive/negative IDs；重用已有 fixture、
  生命周期产物和回放入口，不新增重复全套执行或独立性能门槛。

Synthetic proof 不要求 production admission、真实案例或付费模型调用；production A4 admission 仍由
M5-004 的独立 Gate 控制。结构/执行边界证据不构成科研有效性、真实 Provider readiness 或 Skill 净收益。

## 5. 集成与停止条件

1. 本 docs-only PR 新增 M11-007 为 READY，为 M5-007 增加该硬依赖；M5-007 保持 BLOCKED。
2. 黄毅按已接受定义实施；路诚钺复核 Projection identity 与 M5 consumer equality 边界。
3. M11-007 implementation PR 按 [Gate record](GATE.md) 提供可审计 evidence pins；实现、独立重放证据、
   exact-head CI 与双方 review 被接受并合入后，SATISFIED 才生效。任务定义合入本身不满足 Gate。
4. M5-007 还须等待 M6-008 DONE，才可进入 synthetic Harness；本 Task 不激活 M5-004/005。

保持 Capability Resolver 唯一选择权，View/Host supply-neutral；不增加 Skill dispatcher、fallback、reselection、
mandatory Assignment、Task/Claim/Human authority、admission/promotion 或 Topic 5 recovery。
如 implementation 需要改变这些既有责任、扩大 Runtime 读取面或修改已发布版本语义，停止该扩张并另行走
R2 ADR / task-definition；本定义没有预先授权该变化。

读集限于上述 Task/ADR、Core closeout、Skill mapping、M5 consumer 契约、相关治理/文档检查与 PR75 接口说明；
写集限于 TASKS、ROADMAP、施工图、STATUS、具名工作流索引与本目录。代码、Schema、M6-008 Task 行、
其他 worktree、M14 和 M12/M13 不在本次写集。执行记录见 [WORKLOG](WORKLOG.md)，风险见 [RISK_LEDGER](RISK_LEDGER.md)。
