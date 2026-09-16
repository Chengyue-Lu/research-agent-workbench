# M5-008 — Live Evaluation Pilot Gate

Task definition proposal，2026-09-17。状态与依赖以 [TASKS](../../../TASKS.md) 为准。
Evaluation / Task owner：路诚钺；Provider / Tool / M6 / M11 执行接口复核：黄毅。风险：R2。

## 目的与进入顺序

在 M5-007 完整 synthetic Harness 验收之后，用真实 API、真实 Provider/Tool execution 和完整四臂
transport 验证 live 环境中的调度、资格重验、实际执行事实、独立 replay、盲审与分析输入闭包。
验收对象是 Harness 的工程可用性；pilot observations 不产生 confirmatory net-benefit conclusion。

```text
M5-007 完整验收 + M6-004 live conformance + A4 admission + pilot 专项授权
  → M5-008 四臂 live pilot 与具名验收
  → M5-004（仍须满足获批真实 dossiers 和所有原有 Gate）
  → M5-005 Human disposition
```

M5-008 为 BLOCKED。M5-007 的 H1/H2 PR 或单独 synthetic proof 不满足完整 Harness 前置；
M6-004 只证明选定 Provider/session 的 live conformance，也不能替代本 Task 的跨 transport 集成证据。
本任务定义及其 PR 合入不授权 API 消费、真实数据出站、Tool 副作用或 Skill 准入。

## 启动条件

| 前置 | 执行前必须冻结、核对的依据 |
|---|---|
| M5-007 DONE | 完整 H1–H5 已接受的 implementation、validator、Schema、四臂 synthetic/replay 与 CI pins；传递 M5-006、M6-008、M11-004/006/007 和 Skill replay Gate |
| M6-004 DONE | 适用于本次 exact Provider/Adapter/model slot、Windows Host/session 与 Tool surface 的有效 live conformance；旧模型或不同配置证据不能直接沿用 |
| `A4-RUNTIME-ADMISSION-GATE` | 按[既有 Gate](README.md#a4-runtime-admission-gate)核对 exact candidate/evaluation、具名 Human Admission Decision、accepted Release、Projection、Supply 以及唯一 Resolver 形成的 Snapshot→Bundle→View→Host 全链；live pilot 同样禁止 synthetic projection 和 candidate direct-load |
| `M5-LIVE-PILOT-AUTHORIZATION-GATE` | 具名 Human 对 exact pilot dossier/Protocol、账户与模型、执行人、允许时间窗口、费用/token/turn/time/retry 上限、数据出站/读取范围、Tool 权限/副作用及停止条件的专项授权；只记录 credential reference，不归档密钥；执行负责人核对资源与配置有效性 |

后一个 Gate 是本 Task 的可审计外部条件，不能由 Agent、绿色 CI 或已保存的 preflight 自行授予。
任一 hard/external condition 未满足都保持 BLOCKED；每次调用仍执行既有 use-boundary 重验。
M5-001/002 的 confirmatory dossiers 不作为 M5-008 的 hard dependencies：pilot 使用独立的小规模
工程 dossier，并在首次观察 output 前由 Human 批准 public/private packages、case/Task/input/oracle
identities/hashes、选择理由和读取边界。这样可以先检验执行链路，同时保留后续正式案例的独立审批。

## 冻结计划与四臂执行

复用 M5-006 的已接受 Protocol、M5-007 plan/preflight 和既有 pilot phase；冻结具体 case set、
replicate 数、seed/randomization、共享条件、预算、retry、complete-block stopping 与 drift 规则。
执行白名单仅含 pilot slots；即使合法 Protocol/plan 同时描述 confirmatory slots，也不得调度它们。
不得把 live execution 标成 synthetic 以绕过资格校验，或修改既有 Schema 来省略必要前置。

| Arm | 必须观测的 live 路径 | 必须保持的 treatment boundary |
|---|---|---|
| A1 `plain-agent` | M6 isolated session → 真实 Provider API → baseline closeout | 只读 allowlisted public payload，Tool surface 为空 |
| A2 `plain-agent-tool` | M6 isolated session → 真实 Provider API → exact qualified Tool 实际调用 → baseline closeout | 仅增加 frozen Tool interface；A2 qualification 由 M6 producer 产生 |
| A3 `mode-no-skill` | M11 Core → 真实 Provider API / frozen non-Skill Tool 或 procedure → Core closeout | Resolver 唯一选择 Supply；Harness 重算 A3 qualification，不伪造 Method/Snapshot |
| A4 `mode-candidate-skill` | M11 Skill extension → 真实 Provider API / admitted Skill 所需 Tool 或 procedure → Skill closeout | actual Projection/Supply/binding 与 preflight overlay 一致，Runtime 不读取 candidate/Evaluation/oracle |

同一 case × replicate block 的四臂共享 exact Model/Adapter、Host、context、Task、预算和 data policy，
按预注册次序运行，每个 arm/retry 使用 fresh Attempt/session。四条 transport 均须真实走通；
只调用 API、只运行 A1/A2、只预留 slots、返回 mock/canned output 或冷重放旧 Trace 均不足以验收。
pilot dossier 必须实际触发 A2 的 qualified Tool，以及 A3/A4 frozen path 声明的执行能力；不以
Tool schema 已注册冒充 Tool 已调用，也不额外给 A1 注入 Tool 来凑四臂同形。

## 交付与验收

| 交付 | 必须可独立核对的验收 |
|---|---|
| Frozen pilot packet | exact source/validator/config、Protocol/Manifest/dossier、authorization/conformance/admission、qualification/overlap/overlay/pairwise pins，预注册 block 数与完整 run inventory |
| 完整 live blocks | 完成预注册 pilot run set，至少一个四臂均完成执行与证据闭包的 block；每臂 live request/session、use-boundary Provider/Tool/Host facts、输出与 closeout 可追溯。completed 仍只表示既有 action-capability slice，`task_completion=false` |
| 失败与停止账本 | 所有 completed、post-call-failed、preflight-blocked 和 retry 均保留；失败费用/time/token 进入账本，无法测量则显式标记；安全或预算停止保留未完成 slots，不能写成 Gate PASS，也不能因答案差而择优重跑 |
| 独立 cold replay 与绑定复核 | 在新进程中只读归档文件重放 M6 baseline、M11 Core/Skill Receipt，再与 frozen plan/preflight/overlay 比较 actual facts；不调用 Provider/Tool，不信任自报 PASS、planned View 或旧 replay 结果；漂移与 capture gap 使相应成功资格失败 |
| Live evidence 消费链 | 盲审包先隐藏 arm/Skill/RWB、执行 identity、cost/token；具名 Human 完成并冻结 review 后才 reveal；metric evidence、run IDs、reveal map 与 analysis inputs 全部 join 闭合。measured/estimated/unavailable/not-applicable 分开，缺值不填零 |
| Gate record 与交接 | 路诚钺接受 Harness/Evaluation 工程闭包，黄毅复核 live transport/use-boundary/closeout；绑定 exact source/config、run set、检查与具名接受记录，列出限制和 M5-004 待满足条件；仅在全部验收满足后以 feature/R2 PR 提议 M5-008 DONE |

至少一个完整 block 是链路覆盖的最低要求，不是统计样本量论证，也不能替代完成已冻结的更大 pilot
run set。科研输出不佳本身不等于 Harness 故障；验收判断执行、测量与人工复核是否如实记录。

需要覆盖的负面路径包括：资格/admission/预算不满足时零调用，真实调用后失败的证据保留、
fresh retry 与预算停止，归档篡改/actual binding drift 的 replay 拒绝，以及确认性输入拒收 pilot runs。
本地故障注入和保存的 live 证据篡改实验须单独标注，不能计作成功 live arm。若没有自然 post-call
failure，可在专项授权范围内于真实调用后注入受控本地故障；禁止为验收主动制造数据泄漏、越权或
不可逆 Tool 副作用。无法安全覆盖必要路径时记录缺口，Gate 保持未通过。

## Pilot 与正式评价隔离

pilot run records 和分析入口始终属于 pilot evidence，不进入 primary confirmatory run set；即便某个
case 的 admission overlap assessment 为 held-out / eligible，也不能因此提升 pilot run 的用途。
独立重算 overlap/pairwise，保留真实 case 资格，不通过篡改 assessment 来实现 phase 隔离。
`admission-overlap` 仅在既有 Protocol 允许时用于 pilot/secondary；unknown/absent/unresolved 继续
fail closed，pilot 身份不绕过既有 preflight 规则。

M5-004 冻结正式案例前须审计 pilot 已暴露的 case/Task/input/private-oracle 和据此作出的修改；
受 pilot 观察或调参影响的案例不能重新标为未观察 held-out。修复/调参需新版本、重新冻结与独立的
confirmatory case/oracle；保留旧输出、失败和决策，禁止事后改 oracle 或把 pilot 数据升级进主分析。
M5-008 的描述性指标只支持工程诊断；不据此接受 system-level net benefit、自动 Human scoring、
Skill promotion 或 M5-005 pruning/KEEP。`A4 − A2` 仍包含 transport difference；`A4 − A3` 仅在
`exact-skill-only` 时具备 Skill conditional interpretation 的资格，pilot 不产生确认性效果结论。

Gate 接受只覆盖记录中的 exact source/config/Provider/Tool/Skill/数据边界。M5-004 开始前必须复核
这些 pins、证据适用性和所有原有 Human/case/live/admission Gate；影响执行或证据链的修改使旧
pilot 证据不再足够，须重新进行受影响验证并取得具名接受，不能凭历史 DONE 自动放行。

## 修复与停止边界

发现 Harness 缺陷先保留 failure evidence，在 M5-007 所属实现边界内经合法 Task/PR 修复，再以新
source/config pins 重验；Provider/Tool/Host 缺陷交给黄毅。已经 DONE 的 Task 定义保持 immutable，
若修复超出原验收或需要新能力，先提出后续 task-definition。不得在 pilot 脚本中另建 runner、Supply
selector、admission shortcut、自动判断器，或借此解冻 Topic 5。正式研究评价仍由 M5-004 承担。
