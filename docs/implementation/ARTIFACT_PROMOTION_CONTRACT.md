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
- hash-pinned `promotion_validation_execution`，且 execution fact 位于 `runs/validation/`，固定同一
  Task/Attempt、Task/registry/policy refs、checker、runner、trusted host、report、subjects、执行者、时间和
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
pre-Attempt Task input pins 及唯一 accepted registry entry 完全一致；即使完全一致，缺少 trusted host
实际运行痕迹（host receipt 闭包与确定性重执行等价）的手写 execution 也不得获得 eligibility（见第 4 节）。
`negative_result` 是保留/提升记录，
不是科学语义推断；
负结果也必须有明确 disposition，不能静默丢弃。validation execution 必须先于
`recorded_at`完成，实际 promotion `executed_at` 不得早于 record。

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

## 4. 受信验证执行（trusted validation host）

`promotion_validation_execution` 只有在由受信 validation host 实际调用 accepted、hash-pinned 的
runner/checker、对 exact pinned subject bytes 运行之后，才携带 promotion eligibility。手写的
execution record——即使内部 hash 完全自洽、且引用完全合法的 accepted authority 对象——本身永远不能
获得 eligibility。

权威链为：pre-Attempt 冻结且 revision-pinned 的 Task Packet（canonical
`objects/tasks/<task>/r<revision>/TASK.yaml`）→ accepted-policy registry
（`registry/validation-policies/accepted.yaml`）→ 该 Task revision 的唯一 accepted policy → trusted
validation host 实际执行 accepted runner/checker → host 产出的 receipt →
`promotion_validation_execution` → PASS report → promotion。host 在执行前核验：Task 的
`input_refs` exact-pin registry 与 policy；`write_scope` 绑定 exact `work/<task>/<attempt>`；
checker/runner/host 的 identity/version/source-sha256 pin 指向 repository-governed 受信 source zone
（`src/`、`checks/`、`.github/scripts/`、`registry/validation-tools/`）。

host 在全新 scrubbed subprocess（`PYTHONHASHSEED=0`、90 秒超时、捕获 stdout/stderr/exit code）中实际
执行 pinned runner，并 exclusive-create 三份 durable fact：

- `work/<task>/<attempt>/checks/validation.yaml`：`deterministic_check_report`——PASS 时为 runner
  产出的原始 bytes；runner 未产出 report 时由 host 合成 fail report；
- `runs/validation/<task>/<attempt>/execution.yaml`：`promotion_validation_execution`，新增必需
  `host_receipt_ref`；
- `runs/validation/<task>/<attempt>/receipt.json`：新文档种类
  `promotion_validation_host_receipt`（Schema
  `schemas/v0.1.0/promotion-validation-host-receipt.schema.json`），固定 receipt/execution/Task/Attempt
  id、Task/registry/policy/report exact refs、checker/runner/host binding、subject_refs、
  `run_inputs_sha256`（对 runner contract id、execution/report id、全部 authority refs、组件 pin 与
  subject pin 的 canonical closure hash）、`transcript{exit_code, stdout_sha256, stderr_sha256,
  report_sha256}`、`report_produced_by`（`runner` | `host-failure-synthesis`）、具名 operator、
  started/finished 时间、outcome 与固定 authority boundaries（`validation_execution_fact=true`；
  `promotion_execution` / `claim_acceptance` / `human_decision` / `scientific_correctness`
  均为 false）。

失败语义保持 fail closed：authority 或 boundary 故障在任何执行与写入之前以 ContractError 中止；
runner 崩溃、超时或未产出 report 仍持久化一份 `outcome=fail` 的 report/execution/receipt 三元组（缺失
的 report 由 host 合成并标记 `report_produced_by: host-failure-synthesis`）——它是 durable fail fact，
永远不构成 eligibility。

runner 与 checker 必须 byte-deterministic：report 内容不得包含 wall-clock、随机数、绝对路径或主机
细节。确定性是 policy-owned 要求，因为 promotion 验证会重执行并逐字节比较。参考 runner 为
`registry/validation-tools/deterministic_runner.py`，实现 runner contract
`rwb-validation-runner-contract/1`：manifest 驱动、重算 pinned checker source 与每个 subject 的 hash、
按 exact path 经 importlib 加载 checker、要求 checker 暴露 `evaluate(subjects)` 并返回
`{checks, scope, limitations}`、写出 canonical deterministic YAML report，以退出码 0/1/2 区分
PASS / FAIL / runner fault。

promotion 验证在其余检查全部干净后，通过同一 host seam 对 live subject bytes 重新执行 pinned
runner/checker，要求 PASS report 与记录的 transcript（exit code、stdout/stderr hash）byte-exact
复现；任何漂移都以 `VALIDATION-EXECUTION-UNPROVEN` 阻断。这是 deterministic
rebuild-and-compare：不引入签名密钥，eligibility 的等价定义是——pinned validation 确实在 exact
pinned bytes 上运行过并产生了这份 exact PASS report。本协议的 TCB 为 rwb installed package 代码与
pinned runner/checker/host source。

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

这个协议不把 checker 变成任意代码执行入口：只有被 Task/registry/policy 三重 exact-pin 的
runner/checker 会运行，且仅通过受信 host seam 在 validation 阶段执行；`rwb promotion execute` 不运行
任何调用方提供的代码——其内部复验触发的确定性重执行同样只命中 pinned 组件与 exact pinned subject
bytes。突发进程/主机崩溃不被描述为跨目录事务；若系统在多个 exclusive-create 之间终止，后续验证会因既有
目标阻断，必须先按审计事实处理，不能覆盖重跑或声称完整提交。

## 6. CLI

```text
rwb validation run --task objects/tasks/<task>/r<revision>/TASK.yaml --attempt <id> \
    --subject <path>... --operator <name> [--report-path <p>] [--root .]
rwb promotion validate RECORD --root ROOT
rwb promotion execute RECORD --root ROOT
```

`rwb validation run` 是唯一产生携带 eligibility 的 validation execution fact 的入口：authority 或
boundary 故障在任何执行与写入之前直接拒绝；runner 失败会持久化 `outcome=fail` 三元组并以非零退出。
`validate` 只读。`execute` 必须接收 root 内、workspace 内的实际 record 文件，只复制 disposition 为
`promote` 的 exact bytes，并在 `runs/promotions/<promotion-id>/receipt.json` 留下 durable success fact；
即使全部 entry 都 retain，也会留下 receipt。三条命令均不修改 Claim、Decision 或 deliverable acceptance
状态。通用 `rwb validate` 识别 policy、validation execution、host receipt、record 和 receipt，并会重新
校验 receipt 中的 actual target byte pins。

## 7. 验收证据边界

专项测试覆盖允许稳定目录内完整自洽的 fake authority 链、自签 work checker/policy/execution、
Task/registry/policy/execution/report 关系漂移、report/checker/subject/
entry pin 漂移、额外/遗漏工件、负结果 disposition、路径前缀伪装、root/symlink escape、重复 identity、
existing/accepted target、record/source/target 竞态、staged-byte 漂移、receipt 冲突和目标/receipt 同批回滚；
trusted host 闭合新增覆盖：无 host 实际运行的手写 execution、伪造 host receipt、receipt↔execution↔record
闭包漂移、把 failing checker 伪报为 PASS、非确定性 checker/runner 的重执行 transcript 漂移，以及 runner
崩溃/超时/未产 report 时的 durable fail fact。
该证据只支持 M4-002；M4-003 Claim Trace 与 M4-004 Run reproduction 仍需各自独立实现、PR 和 owner 验收。
