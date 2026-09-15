# M11-007 task-definition Risk Ledger

定义 owner：路诚钺；Execution implementation owner：黄毅。风险等级 R2。
当前处置为 ADAPT：将 Issue55 已有 Gate B 要求落实为窄实施 Task，仍待 cross-owner review。

| 风险 | 定义中的控制 | 实施验收证据 / 剩余责任 |
|---|---|---|
| READY 或 task-definition 被当作 Gate SATISFIED | 独立 Gate record 保持 UNSATISFIED，全部实施 evidence pins 为尚无 | implementation + exact-head CI + 双方 acceptance 才闭合 |
| planned Projection/View 被冒充 actual consumption | producer 的 use-boundary facts、typed Trace 与 replay 三方闭合 | Host/Trace 错绑和 Projection 替换必须被独立拒绝 |
| 强制 equality 使 post-call failure 被擦除 | failed 可保留真实 drift，completed 才要求 selected equality | failure replay 不等于成功或 M5 overlay 一致 |
| 缺事实的 exception 被伪造为 replay-valid | 事实不完整即拒绝 receipt eligibility，保留诊断 | 不新增事后事实或补写调用历史 |
| generic Skill extension 扩大 Runtime 读取面 | Runtime 只消费发布的 Projection/执行闭包，M5 在评价侧验证 admission/overlay | candidate、Evaluation、Human Decision、oracle 不进入 Runtime |
| 新 Task 与 M6-008 互相阻塞或抢占修改 | M11-007 只依赖 M11-004/006，M6-008 Task 行与实现保持独立 | M5-007 在两支闭合后集成，PR75 是进行中候选 |
| 将工作流提案 owner 偷换为执行 owner | 具名区分路诚钺定义/consumer 与黄毅实施/事实责任 | 双方在各自 authority 范围 review |
| 新版本损坏既有 Core 或 legacy replay | 明确 version dispatch，保持已发布语义与历史文件 | 复用既有兼容证据，禁止原位扩义 |
| 任务定义越界到 implementation / 科研执行 | 本 PR 仅 docs，M5-007 继续 BLOCKED，未新增 DONE | synthetic proof 在 implementation PR；real evaluation 留给 M5-004 |

本次审查是定义/依赖/生命周期的静态一致性核对，不冒充尚未执行的 Runtime 对抗测试。

## M11-007 implementation candidate

本节跟踪 PR76 已接受定义之后的独立实施，风险仍为 R2。

| 风险 | 实施控制 | 验收证据 |
|---|---|---|
| 用 planned View 填充 actual Skill facts | Driver 消费 exact bytes 的 immutable inputs；Trace 在调用前记录 input hashes 与 typed fact 创建事件；Host 仅保留观测 | 完整 synthetic vertical proof、fresh-process replay、missing/late fact 反例 |
| 同时重签 Host 和 Trace 掩盖错误身份 | replay 重新加载 actual Supply/Projection，重算 Skill/component identity；completed 还须与 selected View 相同 | rehashed Host/fact 与 Projection identity 漂移反例 |
| 失败事实被要求等同请求而丢失 | failed 保留 Provider/Adapter/Model/Runtime/Host 与 Supply/Projection 真实漂移，completion none | 五类 binding 与 Supply/Projection drift replay |
| 新契约混入 Core 或旧 Receipt | 独立 kind + contract_version 1.0.0，旧 Schema 字节保留；Core API 明确拒绝 Skill contract | Core/legacy 回归与版本/authority 字段反例 |
| 可验证实现被误读为 Gate 接受 | 候选证据与 accepted pins 分列；Gate B UNSATISFIED，M5-007 BLOCKED | 当前 CI、PR review 与 Gate record |

实施接受仍由黄毅与路诚钺按各自边界承担；PR76 的单次维护者例外已使用，不适用于本实现候选。

## PR81 review controls

| Review risk | Repair and independent evidence |
|---|---|
| Pre-use identity predicts later binding | Separate consumption and Core post-call fact; reject missing/early binding creation; synthetic response is the first model-drift observation |
| Wrong-kind contract executes before rejection | Read-only selected Skill closure preflight; direct-tool, procedure and invalid Projection cases prove zero Driver calls |
| Restored files conceal contradictory reads | One hash-pinned read per canonical consumed path; later different-hash and alias duplicate cases reject |

See [review repair](REVIEW-REPAIR.md). The old post-call archive is historical, while new proof and exact-head
CI support focused re-review. Gate B remains UNSATISFIED.
