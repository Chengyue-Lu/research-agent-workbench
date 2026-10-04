# 首个 M12 Task 定义候选

状态：**PROPOSED / RESERVED namespace only**；候选标签 `M12-001` 不是 canonical Task ID，不具有 READY/IN_PROGRESS/DONE 状态。对应 [ADR 候选](ADR_CANDIDATE.md)。

日期：2026-10-04。语义与 task-definition accountable owner：路诚钺（`Chengyue-Lu`）；实现 consumer / execution evidence owner：黄毅（`let778750-cpu`）；起草 actor：assistant。required Skills：`[]`。

## 1. 提议的原子目标

在已闭合 action 边界后，fresh OS/Python process 只凭 exact project-file refs 创建一个新 unique Attempt，执行原 Task revision 内下一项已经冻结的 no-Skill/direct-tool action，保留旧输入/工件，产生新实际 Artifact、Trace、Validation 和 replay-valid M11 generic Receipt。Receipt 只证明本 slice，不能宣布整个 Task 或研究结论已接受。

初始形状是一条 local offline direct-tool 接续。调用方显式启动独立进程并提供项目根和冻结请求；不自动管理窗口、调度下一步或重试。

## 2. activation 与 hard dependencies

| 条件 | 当前可核对事实 | 正式进入实现前需要的证据 |
|---|---|---|
| Phase C Human/R2 semantic closeout | [TASKS](../../../TASKS.md) / [ROADMAP](../../../ROADMAP.md) 仍区分 machine DONE 与独立具名 semantic closeout | exact inputs、具名 Human semantic decision、R2 closeout 接受范围与保留项；机器 PASS、fixture Decision、Issue closed 和普通文档 APPROVE 不代填 |
| Topic 5 architecture + docs-only task-definition | M12 仍 RESERVED；本文件是起草输入 | Phase C 接受后独立 R2 接受本边界、兼容选择、owner/consumer/Schema 影响，再按 [DEVELOPMENT](../../../DEVELOPMENT.md) 定义正式 Task |
| `M10-003` | DONE：bounded continuity/verification machine prerequisite | 保留其 synthetic / exact predicate scope，不改写历史 DONE 定义 |
| `M3-009` | DONE：独立 Method Trace / actual-binding gap 区分 | 本次 state/action/Method lineage 按已接受语义 exact 引用 |
| `M11-004` | DONE：Core no-Skill/direct-tool Host/actual Trace/generic Receipt 闭合 | 复用其既有 contract；传递依赖覆盖 M11-001/002/003，不额外重建执行地基 |

正式 Task 的建议 hard Task deps 为 `M10-003, M3-009, M11-004`，另保留上述可审计外部 activation 条件。后者不是新增的 Gate 产品、自动 checker 状态或本轮虚构决定。M5/M14/Skill admission 不新增为 hard dependency；M13 不随本 Task 激活。Phase C prerequisite Task 不是 Topic 5 membership，使用 M11 closeout 也不改变其 Topic 4 authority。

Topic 5 具名接受记录必须绑定当轮完整 candidate commit HEAD、ADR/Task 候选实际字节 pins 和 consumed Phase C closeout exact refs，并明确接受的投影版本/直接消费者/路径范围。旧 develop base 或普通 APPROVE 不补齐此记录；更新候选后重新核对接受适用性。

## 3. 初始允许读取集

执行时仅允许以下**具体 artifact refs 及 manifest 显式哈希闭包**；路径/identity/hash 在正式 fixture freeze 时给出，当前没有可执行 manifest：

1. 本次 accepted Task revision / project protocol、仓库 guidance、选定 local no-Skill Profile 和具名许可/Decision refs；不读取全局记忆或完整聊天。
2. 源 Main State checkpoint（digest、previous checkpoint、protocol revision、pinned constraints/decisions、`stage-completed` 边界、exact next action）及其明确 machine refs；相邻 checkpoint 只按缺失决定/约束检查实际所需引用读取。
3. 本次 `state_at_attempt_ref`、其明确 predecessor `previous_state_ref`、旧 completed action 的 Attempt/Handoff、replay-valid generic Receipt/Host report/Trace index/typed actual fact、必要 Artifact/Validation pins。按 ref 定位，不加载完整历史 Attempt 消息或 research corpus。
4. next action 的 Method/Capability Requirement、Resolver-produced Resolution/Snapshot，以及既有 producer 生成的 Bundle/View/Policy/Binding/typed conformance exact closure。必须具有适用的 runtime-execution qualification；`structural-replay` 或 fixture-only 替代不获执行资格。功能测试材料明确标为测试，不推出生产/真实 Provider 接受。
5. 整数例候选：[manifest](../../../../examples/run-reconstruction/linear-recurrence/manifest.yaml)、[simulate.py](../../../../examples/run-reconstruction/linear-recurrence/simulate.py)、[inputs](../../../../examples/run-reconstruction/linear-recurrence/inputs.json.txt)、[parameters](../../../../examples/run-reconstruction/linear-recurrence/parameters.json.txt)。其余 manifest 中 Run/environment/旧 CSV refs 本轮仅作元数据关系，未读取正文；未来执行需要什么必须在 accepted fixture 显式声明。

不得递归扫描 Registry/examples/Skills、读 private oracle、凭可见性扩读研究语料、载入 Candidate/Evaluation/Lifecycle 或导入 Evolution validator。遇到未声明正文，停止并交具名 Task owner 扩展本任务的实际允许集。

## 4. 提议的写入范围和最小契约影响

现在只写本 workstream 的候选文档，**不修改 canonical TASKS/ADR 索引、源码、Schema、CLI、Registry、CI 或共享 PROJECT_MEMORY**。

建议供 R2 审查的 implementation 路径清单为：

| 提议路径 | 窄职责 |
|---|---|
| `src/research_workbench/execution/continuity.py`（新） | source-bound request validator、排他新 Attempt consumer、单次 Host/closeout 调用；可经独立 `python -m` 进程调用的本地入口，尚不存在 |
| `schemas/v0.1.0/bounded-continuation.schema.json`（新候选 identity） | 单个 ref-only no-Skill Attempt/Handoff 边界投影；version/id/field shape 须 R2 接受；不修改既有 legacy Schema |
| `tests/test_execution_continuity.py`（新） | 一条 fresh-process 正例和本页最小直接故障；不运行 API/kill/performance suite |
| `examples/execution-continuity/closed-action/`（新） | exact A/B Task、local procedure qualification、source closeout、checkpoint、B Bundle/View 与 read/output manifest；仅 explicit 文件清单，不开放目录扫描 |
| `docs/implementation/BOUNDED_EXECUTION_CONTINUITY.md`（新） | accepted 输入/命令、consumer、结果资格和直接验证；不扩大 public support |

这些名称与 schema identity 都是未接受提议，不宣称命令或契约已经存在。source closure 的最小字段建议为 `task_ref`、`protocol_ref`、`checkpoint_ref`、`state_at_attempt_ref`、`previous_state_ref`、`previous_attempt_ref`、旧 actual closeout/Handoff pins、`next_action_ref`、其 `runtime_bundle_ref`/`view_ref`，及固定 `new_attempt_id`/`new_attempt_dir`。这些 refs 只指向各自权威对象，不能覆写它们。

现行 SchemaCatalog / resource 包装的登记路径本轮没有读取，不能据此承诺新 Schema 已可发现。正式 task-definition 在受控核对实际直接注册点后，列出必要的 exact 适配文件；未列明或超出投影/直接消费者的跨模块变更另行 R2 定义，不以“相关模块”授权写入。Schema-only登记不授权 runtime selection、Handoff semantic migration 或宽泛 CLI 改造。

现行 legacy mandatory Skill 字段保留；不伪造 Assignment、不静默改写旧 Schema。投影只保存引用、next action、target Attempt 和 lineage；Research State、Main State、Resolver selection、Host report、Trace/Receipt 继续各自拥有事实。跨模块 shared Schema/Runtime 改动必须在对应 R2 接受范围内，未接受前不实施。

运行写入只限请求绑定的新 `work/<accepted-task-id>/<new-attempt-id>/` 目录，包括本次 lineage/认领证据、实际输出、Host report、Trace、Validation、generic Receipt 和 Handoff。旧 Attempt/源 checkpoint/source inputs 只读，哈希保持不变。不得覆盖旧失败或成功结果，不创建数据库、全局 continuation cursor、研究成果文件或发布工件。

## 5. 状态与消费步骤

| 阶段 | 必需事实 | 输出资格与停止 |
|---|---|---|
| source boundary | 旧 action actual closeout completed/replay-valid；上层 Task 未完成；checkpoint/Handoff 同指旧边界和已冻结 next action | 若旧调用未闭合、source blocked/failed/waiting 或需新 Human decision，拒绝接续 |
| preflight | 各 ref/hash/digest/protocol/state/next action/permission 与 runtime closure 一致；预算含必要 closeout reserve；无 binding/freshness drift | 不满足即零 Driver/Tool/Provider 调用，只留 bounded refusal/Diagnostic；无 success-qualified Attempt/actual binding |
| exclusive claim | 一个请求绑定一个唯一新 Attempt ID/path；原子排他认领，directory 在 write scope 内且原本不存在 | 重复/并发消费者阻断；不自动另生 ID/目录 |
| dispatch | Host 重验 View/Bundle/freshness；其 trusted dispatch guard 再确认认领和源请求仍适用 | 最多一次 pre-bound direct-tool action；无 fallback/retry/rebind |
| post-call closeout | actual facts、指定 output pins、typed Trace、Validation、generic Receipt 独立 replay 闭合 | successful slice 或真实 failed/incomplete 分开；缺事实不伪造 Receipt |
| handoff | 新 Attempt 指旧 lineage 和本次实际输出；保留失败/限制/未完成/需人类项 | source immutable；main checkpoint 更新由控制面另行发布；不自动推进下一 action |

新 Attempt 必须重绑定本次 execution-time Research State，不能复制 `previous_state_ref` 冒充 `state_at_attempt_ref`。Main State checkpoint、Research State 与 Attempt lineage 是三个职责不同的引用。Checkpoint 出现新增/撤回决定、前提变化或许可缺口，consumer 只能阻断并请求 Control/Human 判断。

同一请求多次启动的去重边界是固定 target Attempt + 排他创建；不宣称外部 exactly-once。认领后崩溃/事实缺失保留目录并停止，禁止删除认领后偷偷重试。供给或 binding 变化回原 Resolver，由它形成新 Resolution→Snapshot，再由既有 producers 形成新 Bundle/View；本次 consumer 不能完成这项选择。

## 6. 首个 test fixture 的具体提案

预先冻结同一测试 Task 的 A、B 两个不同 slices：A 校验 pinned integer inputs 并实际生成验证工件，经 M11 闭合；B 执行现有整数程序。源进程完成 A，构造/冻结 B 的合法执行 closure 和 checkpoint/Handoff，然后退出。新进程只凭文件执行 B。

静态核对的输入字节 pins：

| 文件 | SHA-256 |
|---|---|
| `simulate.py` | `2c99193380b4d298c85e3e033e1e63d3e5c76319a5e69d17a0a371442f3f3213` |
| `inputs.json.txt` | `34daf86ea235053be067394df1f8d4fe3fa964328c280fb8de75bf38622afbe2` |
| `parameters.json.txt` | `2ed7e189cbf7b578cf3477c192b68b99aeed586b606752b202cb1988708f283b` |

现有参数/输入是 `x0=0,a=1,u=[1,-1,2,-2]`；源码的 CSV 行为为 header `n,x`、初始行 `(0,0)`、逐步行 `(1,1),(2,0),(3,2),(4,0)`。这些数值是源码与输入的静态推导，本轮未运行程序。未来 B 的 expected bytes/output identity 在 fixture freeze 时明确，并写入其新 Attempt 的 `trajectory.csv`，不得直接将旧 CSV/Run 当本次 actual output。

现有 reconstruction manifest 的 `timeout_seconds:5`、旧 environment/Run/CSV pins 和 negative-result 声明不自动成为 M12 运行参数或 acceptance。正式 fixture 的 A/B Task、合法 typed runtime qualification、target ID/path、执行 manifest、freshness/budget、输出 layout **尚未构造或冻结**；接受后按既有 local bounded execution 规则建立，不增加任意性能 pass/fail 阈值。

## 7. 建议 acceptance 与最小反例

1. 一条正常 fresh-process 接续：源进程已退出，新进程读取清单可核对；旧 A 没有再执行，B 只调用一次；新 ID/目录、Task revision、next action slice 和 lineage 正确；source hashes 不变；CSV 属于新 Attempt。
2. M11 actual fact→Trace→Artifact/Validation→generic Receipt 独立冷 replay 通过；actual binding/Supply 等于冻结 View，输出存在/hash 正确。保留 `skill_assignment:absent`、`completion_claim:action-capability-slice-only`、`task_completion:false`、`topic5_recovery:false`。
3. pin/freshness/binding 漂移，或 next action/权限/Human 条件缺失时零调用；停止原因明确，binding/Supply drift 只提出 re-resolution request。用直接反例覆盖相关判断，不建立通用防御矩阵。
4. 重复请求/已存在目标目录及两个进程争抢同一冻结请求只有一个认领者；拒绝者不调用、不覆盖源或新输出。只验证此 local one-request 边界。
5. 缺 output/hash mismatch/typed actual fact 或必要闭集 Validation 时不能成功闭合；真实 post-call failure、driver-exception/capture gap 及 partial artifacts 保留，不追加自动 retry。
6. 记录 actual read set/字符量、准备与执行时间、必要人工纠正和 unknown 成本；记录只是工程证据，不以净收益、性能百分比或科学正确性作此 Task 完成条件。

以上是待接受的验收建议，不是已通过检查。本轮只检查文档链接、引用的静态接口/字节 pins 和边界一致性；不运行程序、测试、安装、模型 API 或恢复实验。

## 8. 实施顺序与停止

先真实完成 Phase C semantic closeout，再独立接受 Topic 5 ADR / docs-only task-definition；之后按 accepted exact Task 冻结 fixture 和写入清单，实现 boundary validator / exclusive consumer，接既有 Host 和 generic closeout，运行上述 narrow offline checks，再开正常 implementation PR 供跨 owner 审查。禁止直接 merge。

Gate 未闭合时的下一动作是提供确切候选与具名决定选项；不可将接手授权、machine PASS、PR72 文档合并或测试通过解释为这些决定。first task 不恢复 in-flight action、safe-paused/salvage、Provider/API、外部 side effects，不改研究问题、Method/Supply 选择、预算权限、Task completion、Claim、Human/科学接受，不激活 M13，不混入 M5/A4/Pilot/M6/全量 CI 或发布线。
