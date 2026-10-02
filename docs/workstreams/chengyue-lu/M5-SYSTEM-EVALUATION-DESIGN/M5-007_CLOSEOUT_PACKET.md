# M5-007 H1–H5 整体验收准备

首次记录：2026-09-28；更新：2026-10-02。Task / Evaluation owner：路诚钺；Execution 接口复核：黄毅。风险：R2。
状态：PR106 H5 已具名 R2 接受并合入；PR107 准备文档已合入 `develop@2618ef4fa7a1b16722e097af9a91b00b40ec700a`。
M5-007 仍为 IN_PROGRESS，Issue55 仍 OPEN，整体验收尚未作出。
[当前整体验收复核候选](M5-007_ACCEPTANCE_REVIEW.md)另行审计现行源码、Task 与历史证明；
PR107 的旧审批因 rebase 失效，本次复核不得把它当作具名 R2 接受。

## 目标与输入

本包把已合入的 H1–H5 放进同一验收视图，准备 M5-007 的最终状态审查。
它只整理现有证据、缺口和复核顺序；不生成新的产品契约、
测试结果、正式评价结论或 Task DONE 决定。原始输入及原字节哈希见
[进入记录](attempts/M5-007-CLOSEOUT-ENTRY-001/README.md)，其 pins 属于 PR106 合入前的
`68e612b353233bb8faf739d5012876739793cd84` 入口快照，不要求与后续现行文档字节相同。

| 切片 | 已核对的合入或候选身份 | 整体验收时要复核的闭包 |
|---|---|---|
| H1/H2 | [PR86](https://github.com/Chengyue-Lu/research-agent-workbench/pull/86) MERGED，`51dc3ab477f21f18ac3829bf553b5b779d49a4fe` | frozen plan、评价侧 preflight、A2/A3 qualification 与 A4 overlay/admission/overlap/pairwise 独立重算；不把 structural fixture 当正式 execution |
| H3 | [PR89](https://github.com/Chengyue-Lu/research-agent-workbench/pull/89) MERGED，`171d4654f88e926f239cdf25bc8168109b81f391` | 四臂 synthetic fresh Attempt/session、实际生命周期与冷回放；失败/retry 不裁剪 |
| H4a | [PR90](https://github.com/Chengyue-Lu/research-agent-workbench/pull/90) MERGED，`a542a06f781b4b4bce6696a2e6a888f4243f66c0` | evaluation-owned actual evidence、冻结/实际身份匹配与来源重算 |
| H4b | [PR96](https://github.com/Chengyue-Lu/research-agent-workbench/pull/96) MERGED，`97d3b3d3141419b34ad47e0f42d9f01d0dfbd535` | finite synthetic 盲审、具名 freeze 与受控 reveal；该 PR 的单次维护者审核例外只属于其自身，不记为 cross-owner APPROVED |
| H4c | [PR104](https://github.com/Chengyue-Lu/research-agent-workbench/pull/104) 具名 R2 接受并 MERGED，`26eca5742ba08d504d273423471fd7aab876a6d5` | 四种版本化 method/observation/metric/analysis records、13 项缺测量状态、实际全 Attempt 与 paired input 重算 |
| H5 | [PR106](https://github.com/Chengyue-Lu/research-agent-workbench/pull/106) 由黄毅具名 R2 接受 exact head `68e612b353233bb8faf739d5012876739793cd84`，MERGED 为 `81a058b228a5da2a6f46192a954f62efc72895e3` | 454 文件的持久化 proof、外部 inventory/request pin、新进程全链 replay 与篡改/越权/生命周期负例；[H5 Attempt](attempts/M5-007-H5-001/README.md) 保持历史字节 |

PR106 合入前获批 head 的 [component CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36431821489)
和[最新治理检查](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36432661027)
均 SUCCESS；黄毅在该 exact head 的正式 review 已 APPROVED，PR106 已正常 squash 合入。
合入前后 Git tree 字节等价；整体 M5-007 的具名 R2 接受仍是独立决定。
H5 proof 的 ZIP SHA-256 为 `176c47b3ebbc8e71d3cdb27f835d82a8e5af2ac876638d7ca7d0c7601a063b2d`；
其冷回放保留四臂、8 cells / 10 pairs、8 completed / 1 failed / 7 not-started，
13 指标全部 unavailable/null，synthetic primary eligibility 为 false。以上是结构与重放证据，
不证明科研有效性或真实 Provider/Human/admission。

## 整体验收步骤

1. PR106 已完成 exact-head R2 review 与正常 squash merge；PR107 的原文档补丁先迁至
   `develop@81a058b`、再等价迁至 `develop@39cf61e`，最终 rebase 到首发收口后的
   `develop@54192ef` 并 squash 合入 `develop@2618ef4`。`docs/STATUS.md` 同时保留
   H5 接受与 M14 首发完成；旧分支的文档 CI 依赖修复已由新基线吸收。PR107 的
   exact-head component/governance 与实际 protected-develop component push 均已通过；
   整体验收仍须按[当前复核](M5-007_ACCEPTANCE_REVIEW.md)单独审查。
2. 独立复核 M5-007 Task 行的全部验收：冻结和实际 binding、qualification/overlap/pairwise、
   typed execution fact/Receipt、失败/retry、blind review/reveal、metric/analysis、全链 cold
   replay、negative tests 与双方接口边界。任何新发现保存具体失败证据，回到所属 H 切片修复。
3. 只有 H1–H5 整体证据和具名 R2 接受闭合后，才在后继审查候选中提出
   `docs/TASKS.md` 的 M5-007 `IN_PROGRESS → DONE`；Issue55 是否关闭须再核对其独立
   Gate 与内部 acceptance，不能因 PR106 CI 绿灯自动关闭。

PR107 仅同步已接受 H5 的实现状态，已按用户直接指示合入；它没有修改 `docs/TASKS.md`
或 Issue55，也没有完成 M5-007 的具名 R2 整体验收。
旧 H5 proof 只在其 pinned source/Schema/helper 身份下有效；若接受中的源码身份变化，
必须生成新的证据，不能改写旧 archive 的 hashes。

## 下游 Gate 与权威

M5-008 仍为 BLOCKED：除 M5-007 完整接受外，仍要求 M6-004 live conformance、
`A4-RUNTIME-ADMISSION-GATE` 和专项 `M5-LIVE-PILOT-AUTHORIZATION-GATE`。
M6-004 当前也是 BLOCKED；本包不调用真实 API、不消耗凭据、不执行 Tool 副作用。
M5-004/005 的真实 case、Human 决策、正式分析与 Skill lifecycle Gate 原样保留。
路诚钺负责 Evaluation/Task 接受，黄毅负责 Execution 接口复核；自动测试、归档 hash
和本 PR 都不能代替具名接受。
