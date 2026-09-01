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
- hash-pinned `deterministic_check_report`；
- hash-pinned `promotion_validation_policy`，且 policy 位于 repository-governed
  `registry/validation-policies/`，固定 Task、checker 与 validation runner 的 identity/version/source hash；
- hash-pinned `promotion_validation_execution`，且 execution fact 位于 `runs/validation/`，固定同一
  Task/Attempt、policy、checker、runner、report、subjects、执行者、时间和 pass/fail outcome；
- 具名 `operator` 和显式 `recorded_at`；
- 每个受检工件的 `(path, sha256)`、`promote` / `retain-in-work` disposition、负结果声明；
- promote 项的目标路径，或 retain 项的具名原因；
- 不可放宽的 authority boundaries。

validator 会复验 policy、validation execution、report、checker/runner source、全部 subjects、entries 和
live bytes。policy → execution → report 的 Task/Attempt、组件 identity/version/source pin 与 exact refs
必须一致；execution outcome 与 report status 均须为 pass。report subject、execution subject 与 entry 必须按
规范化后的 exact file-reference 集合相等；重复 identity、遗漏、额外未受检工件、错误 pin 或调用方在
`work/` 内自建 checker/policy/execution 均阻断。`negative_result` 是保留/提升记录，不是科学语义推断；
负结果也必须有明确 disposition，不能静默丢弃。validation execution 必须先于
`recorded_at`完成，实际 promotion `executed_at` 不得早于 record。

## 3. 路径与发布规则

源工件、report 和可执行 promotion record 必须严格位于声明 workspace 内，字符串前缀相似不构成包含
关系。accepted policy、validation execution、checker/runner、subject、entry、target 与 receipt 都必须
留在各自固定 zone 和 project root 内，且不得穿越 symbolic-link 边界。

首版只允许三个 target zone：

- `objects/`
- `runs/`
- `deliverables/candidates/`

`deliverables/accepted/`、`checks/` 和任意相似前缀不具备 promotion 资格。目标已存在或多项指向同一
目标时 fail closed。

## 4. 执行模型

`rwb promotion execute` 按以下顺序工作：

1. 从 project root 内的实际 record 文件一次读取、解析并固定其 path/hash；拒绝
   in-memory mapping 执行和分离的 read/hash 窗口；
2. 完整执行 policy、validation execution、report、checker/runner、subject、entry、live byte 和路径检查；
3. 将每个 promote 源复制到目标目录内的私有临时文件，同时重新计算 SHA-256 并 `fsync`；
4. 对所有输入和目标进行第二次完整复验，并复核 staged bytes；
5. 生成 Schema-valid `promotion_execution_receipt`，exact-pin record、policy、validation execution、report、
   checker、全部 source refs、actual target refs/hash、operator、executed_at、outcome 和固定 authority boundary；
6. stage receipt 后执行 commit-time 第三次权威链复验，再将目标与 receipt 一起 hard-link exclusive-create；
7. 任一中途冲突或异常会撤销本次已创建且仍与 staged inode 相同的目标/receipt 并清理 staging；源始终保留。

这个协议不把 checker 变成任意代码执行入口；checker source 只作为 report 的 exact provenance 被验证。
突发进程/主机崩溃不被描述为跨目录事务；若系统在多个 exclusive-create 之间终止，后续验证会因既有
目标阻断，必须先按审计事实处理，不能覆盖重跑或声称完整提交。

## 5. CLI

```text
rwb promotion validate RECORD --root ROOT
rwb promotion execute RECORD --root ROOT
```

`validate` 只读。`execute` 必须接收 root 内、workspace 内的实际 record 文件，只复制 disposition 为
`promote` 的 exact bytes，并在 `runs/promotions/<promotion-id>/receipt.json` 留下 durable success fact；
即使全部 entry 都 retain，也会留下 receipt。两条命令均不修改 Claim、Decision 或 deliverable acceptance
状态。通用 `rwb validate` 识别 policy、validation execution、record 和 receipt，并会重新校验
receipt 中的 actual target byte pins。

## 6. 验收证据边界

专项测试覆盖自签 work checker/policy/execution、policy/execution/report 关系漂移、report/checker/subject/
entry pin 漂移、额外/遗漏工件、负结果 disposition、路径前缀伪装、root/symlink escape、重复 identity、
existing/accepted target、record/source/target 竞态、staged-byte 漂移、receipt 冲突和目标/receipt 同批回滚。
该证据只支持 M4-002；M4-003 Claim Trace 与 M4-004 Run reproduction 仍需各自独立实现、PR 和 owner 验收。
