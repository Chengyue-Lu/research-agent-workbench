# Artifact Promotion Contract（M4-002）

状态：R1 shared contract candidate；合入 `develop` 后成为 M4-002 当前实现。

## 1. 目的与权威上限

`promotion_record` 把一个真实 `work/<task>/<attempt>/` 工作区中的全部受检工件，按 exact byte pin
登记为“复制到正式候选区”或“保留在 work”。Promotion 只证明确定性校验闭合和复制资格：

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
- 具名 `operator` 和显式 `recorded_at`；
- 每个受检工件的 `(path, sha256)`、`promote` / `retain-in-work` disposition、负结果声明；
- promote 项的目标路径，或 retain 项的具名原因；
- 不可放宽的 authority boundaries。

validator 会复验 report 自身、checker source、全部 report subjects、全部 entries 和 live bytes。report
subject 与 entry 必须按规范化后的 `(path, sha256)` 完全集合相等；重复 identity、遗漏、额外未受检工件、
错误 pin 或 `status != pass` 均阻断。`negative_result` 是保留/提升记录，不是科学语义推断；负结果也必须有
明确 disposition，不能静默丢弃。

## 3. 路径与发布规则

源工件必须严格位于声明 workspace 内，字符串前缀相似不构成包含关系。源、report、checker、subject、
entry 与 target 都必须留在 project root 内，且不得穿越 symbolic-link 边界。

首版只允许三个 target zone：

- `objects/`
- `runs/`
- `deliverables/candidates/`

`deliverables/accepted/`、`checks/` 和任意相似前缀不具备 promotion 资格。目标已存在或多项指向同一
目标时 fail closed。

## 4. 执行模型

`rwb promotion execute` 按以下顺序工作：

1. 完整执行 Schema、report、checker、subject、entry、live byte 和路径检查；
2. 将每个 promote 源复制到目标目录内的私有临时文件，同时重新计算 SHA-256 并 `fsync`；
3. 对所有输入和目标进行第二次完整复验，并复核 staged bytes；
4. 使用 hard-link exclusive-create 发布完整 inode，永不覆盖目标；
5. 任一中途冲突或异常会撤销本次已创建且仍与 staged inode 相同的目标，并清理 staging；源文件始终保留。

这个协议不把 checker 变成任意代码执行入口；checker source 只作为 report 的 exact provenance 被验证。
突发进程/主机崩溃不被描述为跨目录事务；若系统在多个 exclusive-create 之间终止，后续验证会因既有
目标阻断，必须先按审计事实处理，不能覆盖重跑或声称完整提交。

## 5. CLI

```text
rwb promotion validate RECORD --root ROOT
rwb promotion execute RECORD --root ROOT
```

`validate` 只读。`execute` 只复制 disposition 为 `promote` 的 exact bytes；`retain-in-work` 和所有源材料
保持原位。两条命令均不修改 Claim、Decision 或 deliverable acceptance 状态。

## 6. 验收证据边界

专项测试覆盖 report/checker/subject/entry pin 漂移、额外/遗漏工件、负结果 disposition、路径前缀伪装、
root/symlink escape、重复 identity、existing/accepted target、源竞态、目标竞态、staged-byte 漂移和部分
发布回滚。该证据只支持 M4-002；M4-003 Claim Trace 与 M4-004 Run reproduction 仍需各自独立实现、PR
和 owner 验收。
