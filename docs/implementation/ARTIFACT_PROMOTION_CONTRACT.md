# Artifact Promotion Contract（M4-002）

状态：R1 shared contract candidate；合入 `develop` 后成为 M4-002 当前实现。

## 1. 目的与权威上限

`promotion_record` 把一个真实 `work/<task>/<attempt>/` 工作区中的全部受检工件，按 exact byte pin
登记为“复制到正式候选区”或“保留在 work”。Promotion 只证明受信验证链闭合、实际复制和持久化
receipt 事实：

- 不接受 Claim，不判断 Evidence 是否充分；
- 不记录或替代 Human Decision；
- 不直接发布 accepted deliverable；
- 不证明科学正确性、来源真实性或方法适用性；
- 不删除、移动或覆盖 work/archive 中的原始材料。

上述边界作为固定常量写入每份记录，不能由调用方放宽。

## 2. 记录闭包

每份记录必须固定：

- exact `source_workspace`，且必须是三段式 `work/<task>/<attempt>` 根；
- pre-Attempt、revision-pinned `task_packet`，位于 canonical `objects/tasks/<task>/r<revision>/TASK.yaml`；
  Task 的 exact inputs 必须同时 pin accepted-policy registry 与 policy，write scope 必须收窄到该
  `work/<task>/<attempt>`；
- hash-pinned `promotion_validation_authority_registry`，且只能是
  `registry/validation-policies/accepted.yaml`；registry 按 Task revision 接受唯一 policy，并固定
  checker、runner 与 validation host 的 identity/version/source hash、具名接受人和接受时间；
- hash-pinned `deterministic_check_report`；
- hash-pinned `promotion_validation_policy`，且 policy 位于
  `registry/validation-policies/`，固定 Task、checker 与 validation runner 的 identity/version/source hash；
- hash-pinned `promotion_validation_execution`，该 claimed provenance metadata 位于 `runs/validation/`，固定同一
  Task/Attempt、Task/registry/policy refs、checker、runner、host binding、report、subjects、自声明执行者、时间和
  pass/fail outcome，并以必需 `host_receipt_ref` exact-pin 同样位于 `runs/validation/` 的
  `promotion_validation_host_receipt`；
- 具名 `operator` 和显式 `recorded_at`；
- 每个受检工件的 `(path, sha256)`、`promote` / `retain-in-work` disposition、负结果声明；
- promote 项的目标路径，或 retain 项的具名原因；
- 不可放宽的 authority boundaries。

validator 会复验 Task、accepted registry、policy、validation execution、host receipt、report、
checker/runner/host source、全部 subjects、entries 和 live bytes。Task → registry/policy → host-bound
execution → host receipt → report 的 Task/Attempt/revision、组件 identity/version/source pin 与 exact refs
必须一致；execution outcome 与 report status 均须为 pass。report subject、execution subject 与 entry 必须按
规范化后的 exact file-reference 集合相等；重复 identity、遗漏、额外未受检工件、错误 pin 或调用方在
`work/` 内自建或在允许稳定目录内拼装的 fake checker/runner/host/policy/execution 均阻断，除非它们与
pre-Attempt Task input pins 及唯一 accepted registry entry 完全一致。记录闭包自身不授予 eligibility；
只有 promotion 时重执行 accepted pinned runner/checker 并复现 PASS report 与 transcript 才确立有效性。
错误的手写 PASS 声称会被阻断；byte-exact 的自报历史可以通过有效性检查，但不产生历史
producer/operator/time 权威（见第 4 节）。
`negative_result` 是保留/提升记录，
不是科学语义推断；
负结果也必须有明确 disposition，不能静默丢弃。自声明 validation `finished_at` 必须不晚于
`recorded_at`，promotion `executed_at` 不得早于 record；时间顺序检查不证明自声明历史真实。

## 3. 路径与发布规则

源工件、report 和可执行 promotion record 必须严格位于声明 workspace 内，字符串前缀相似不构成包含
关系。accepted policy、validation execution 与其 host receipt、checker/runner、subject、entry、target 与
receipt 都必须留在各自固定 zone 和 project root 内，且不得穿越 symbolic-link 边界。

首版只允许三个 target zone：

- `objects/`
- `runs/`
- `deliverables/candidates/`

`deliverables/accepted/`、`checks/` 和任意相似前缀不具备 promotion 资格。目标已存在或多项指向同一
目标时 fail closed。

## 4. 验证执行与 promotion-time 重执行（validity semantics）

promotion eligibility 是一个 **validity fact**，只在 promotion 验证时确立：`check_promotion` 在其余
检查全部干净后，通过同一受控 host seam 对 live subject bytes 确定性重执行 accepted、hash-pinned 的
runner/checker，要求 byte-exact 复现记录的 PASS report 与 run transcript（deterministic
rebuild-and-compare，不引入签名密钥）；任何漂移以 `VALIDATION-EXECUTION-UNPROVEN` 阻断。

`rwb validation run`（validation host）是产生候选验证记录的规范入口：它解析 pre-Attempt 权威链
（revision-pinned canonical Task → accepted-policy registry → 该 Task revision 的唯一 accepted
policy → checker/runner/host identity/version/source pin），在 scrubbed subprocess 中实际执行 pinned
runner，并 exclusive-create 三份 durable 文档——PASS report、`promotion_validation_execution` 与
`promotion_validation_host_receipt`。这份三元组是 **provenance metadata**：它把一次"声称的运行"的
pinned inputs、transcript、自声明 operator 与时间以 durable、交叉 exact-pin 的形式记录下来，供审计与
故障排查使用；它**不证明该历史运行确实发生过**，也从不单独授予 eligibility。因此：

- 手写 execution/report/receipt 且声称与真实 runner 输出不符：重执行直接证伪，阻断；
- 手写但 byte-exact 的三元组（攻击者离线运行 pinned runner 后伪造"历史"）：可以通过 promotion
  有效性验证。重执行当场确认的是 pinned pipeline 在 exact pinned bytes 上通过；错误 PASS report
  或 transcript 会被阻断，自报的历史 producer/operator/time 仍不可验证，也不获得历史权威。

权威链为：pre-Attempt 冻结且 revision-pinned 的 Task Packet（canonical
`objects/tasks/<task>/r<revision>/TASK.yaml`）→ accepted-policy registry
（`registry/validation-policies/accepted.yaml`）→ 该 Task revision 的唯一 accepted policy →
checker/runner/host 的 identity/version/source pin。host 在执行前核验：Task 的 `input_refs`
exact-pin registry 与 policy；`write_scope` 绑定 exact `work/<task>/<attempt>`；checker/runner/host
pin 指向 repository-governed 受信 source zone（`src/`、`checks/`、`.github/scripts/`、
`registry/validation-tools/`）。registry 中的 host pin 以 metadata 形式标识 operator 声称使用的
producer 实现；真正的 producer 始终是 installed `rwb` package——本协议的 TCB 为执行 promotion 验证的
rwb installed package 代码与 pinned runner/checker source。单一信任域（同一台主机、同一文件系统）内
不存在调用方无法离线重建的 proof，因此本协议刻意不声称 trusted-host historical provenance；若未来
引入跨信任域的签名/attestation 基础设施，需独立 ADR。

host 在 scrubbed subprocess 中执行 pinned runner：环境只继承 OS 必需变量白名单（Windows
`PATH`/`SystemRoot`/`TEMP` 等，POSIX `PATH`/`HOME`/`TMPDIR` 等，大小写不敏感匹配），丢弃会话/Agent
注入变量、凭据与解释器污染开关（`PYTHONPATH`/`PYTHONHOME`/`PYTHONSTARTUP` 等），并固定
`PYTHONHASHSEED=0`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONNOUSERSITE=1`、`TZ=UTC`；90 秒超时，捕获
stdout/stderr/exit code。host exclusive-create 三份 durable 文档：

- `work/<task>/<attempt>/checks/validation.yaml`：`deterministic_check_report`——PASS 时为 runner
  产出的原始 bytes；runner 未产出 report 时由 host 合成 fail report；
- `runs/validation/<task>/<attempt>/execution.yaml`：`promotion_validation_execution`，必需
  `host_receipt_ref`；
- `runs/validation/<task>/<attempt>/receipt.json`：`promotion_validation_host_receipt`（Schema
  `schemas/v0.1.0/promotion-validation-host-receipt.schema.json`），固定 receipt/execution/Task/Attempt
  id、Task/registry/policy/report exact refs、checker/runner/host binding、subject_refs、
  `run_inputs_sha256`（对 runner contract id、execution/report id、全部 authority refs、组件 pin 与
  subject pin 的 canonical closure hash）、`transcript{exit_code, stdout_sha256, stderr_sha256,
  report_sha256}`、`report_produced_by`（`runner` | `host-failure-synthesis`）、自声明 operator 与
  started/finished 时间、outcome 与固定 authority boundaries（全部为 false——包括
  `validation_execution_fact=false`，因为这份文档不证明历史执行；promotion-time 重执行确立的是
  当前 pipeline validity）。

失败语义保持 fail closed：authority 或 boundary 故障在任何执行与写入之前以 ContractError 中止；
runner 崩溃、超时或未产出 report 仍持久化一份 `outcome=fail` 的 report/execution/receipt 三元组（缺失
的 report 由 host 合成并标记 `report_produced_by: host-failure-synthesis`）——它是 durable failure metadata，
永远不构成 eligibility。

runner 与 checker 必须 byte-deterministic：report 内容不得包含 wall-clock、随机数、绝对路径或主机
细节。确定性是 policy-owned 要求，因为 promotion 验证会重执行并逐字节比较。参考 runner 为
`registry/validation-tools/deterministic_runner.py`，实现 runner contract
`rwb-validation-runner-contract/1`：manifest 驱动、重算 pinned checker source 与每个 subject 的 hash、
按 exact path 经 importlib 加载 checker、要求 checker 暴露 `evaluate(subjects)` 并返回
`{checks, scope, limitations}`、写出 canonical deterministic YAML report，以退出码 0/1/2 区分
PASS / FAIL / runner fault。

## 5. Promotion 执行模型

`rwb promotion execute` 按以下顺序工作：

1. 从 project root 内的实际 record 文件一次读取、解析并固定其 path/hash；拒绝
   in-memory mapping 执行和分离的 read/hash 窗口；
2. 完整执行 Task/registry/policy、host-bound validation execution、host receipt 闭包、report、
   checker/runner/host、subject、entry、live byte 和路径检查，并在其余检查干净后通过 host seam 对 pinned
   runner/checker 做确定性重执行等价复核；
3. 将每个 promote 源复制到目标目录内的私有临时文件，同时重新计算 SHA-256 并 `fsync`；
4. 对所有输入和目标进行第二次完整复验，并复核 staged bytes；
5. 生成 Schema-valid `promotion_execution_receipt`，exact-pin record、Task、authority registry、policy、
   validation execution、report、checker/runner/host、全部 source refs、actual target refs/hash、operator、
   executed_at、outcome 和固定 authority boundary；
6. stage receipt 后执行 commit-time 第三次权威链复验，再将目标与 receipt 一起 hard-link exclusive-create；
7. 任一中途冲突或异常会撤销本次已创建且仍与 staged inode 相同的目标/receipt 并清理 staging；源始终保留。

只有被 Task/registry/policy 三重 exact-pin 的 runner/checker 会通过 host seam 运行；调用方不能为
本次 promotion 临时指定其他代码。正常成功路径中的三次完整复验各重执行一次 pinned pipeline。
环境清理与临时工作目录不构成 OS 沙箱；已接受的 runner/checker 必须受信且无仓库写入等副作用。
突发进程/主机崩溃不被描述为跨目录事务；若系统在多个 exclusive-create 之间终止，后续验证会因既有
目标阻断，必须先按审计事实处理，不能覆盖重跑或声称完整提交。

## 6. CLI

```text
rwb validation run --task objects/tasks/<task>/r<revision>/TASK.yaml --attempt <id> \
    --subject <path>... --operator <name> [--report-path <p>] [--root .]
rwb promotion validate RECORD --root ROOT
rwb promotion execute RECORD --root ROOT
```

`rwb validation run` 是产生候选 validation 三元组（report/execution/host receipt provenance
metadata）的规范入口：authority 或 boundary 故障在任何执行与写入之前直接拒绝；runner 失败会持久化
`outcome=fail` 三元组并以非零退出。`validate` 的宿主逻辑不写仓库，但会在临时工作目录中经同一
host seam 实际执行 pinned runner/checker 以完成 rebuild-and-compare，eligibility 正是在这里确立。
该命令依赖第 5 节的受信、无副作用组件前提，不提供 OS 级写入隔离。`execute` 必须接收 root 内、
workspace 内的实际 record 文件，只复制 disposition 为
`promote` 的 exact bytes，并在 `runs/promotions/<promotion-id>/receipt.json` 留下 durable success fact；
即使全部 entry 都 retain，也会留下 receipt。三条命令均不修改 Claim、Decision 或 deliverable acceptance
状态。通用 `rwb validate` 识别 policy、validation execution、host receipt、record 和 receipt，并会重新
校验 receipt 中的 actual target byte pins。

## 7. 验收证据边界

专项测试覆盖允许稳定目录内完整自洽的 fake authority 链、自签 work checker/policy/execution、
Task/registry/policy/execution/report 关系漂移、report/checker/subject/
entry pin 漂移、额外/遗漏工件、负结果 disposition、路径前缀伪装、root/symlink escape、重复 identity、
existing/accepted target、record/source/target 竞态、staged-byte 漂移、receipt 冲突和目标/receipt 同批回滚；
validation host 闭合新增覆盖：无 host 记录的手写 execution、伪造 host receipt、receipt↔execution↔record
闭包漂移、把 failing checker 伪报为 PASS、非确定性 checker/runner 的重执行 transcript 漂移、runner
崩溃/超时/未产 report 时的 durable failure metadata、runner 子进程环境 scrub（OS 白名单 + 确定性 pin、丢弃
会话注入变量与凭据），以及 validity semantics 的边界锁定——host 从未运行、report/transcript 与
pinned runner/checker 输出逐字节一致、operator/时间纯属伪造的三元组可以通过验证但不携带任何历史
权威（三元组自身声明 `validation_execution_fact=false`，eligibility 完全由 promotion-time 重执行
当场确立）。
该证据只支持 M4-002；M4-003 Claim Trace 与 M4-004 Run reproduction 仍需各自独立实现、PR 和 owner 验收。
