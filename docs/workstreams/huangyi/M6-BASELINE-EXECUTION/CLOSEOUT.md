# M6-008 收口与 M5-007 交接

更新：2026-09-16。M6 Task / Execution owner：黄毅；M5 consumer / 后继 Harness owner：路诚钺。风险：R2。

## 接受来源与生效边界

[PR75](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75) 已于 `2026-09-16T10:26:11Z` 合入，
merge commit 为 `b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22`。
路诚钺的 [APPROVE](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75#pullrequestreview-5221444234)
明确绑定 head `f704bfdaa5f9c3774dcf24ad06680576a1a60e0c` 和 base
`75fbf97c001c7e399135c97e603124cc7a2b06b3`，接受修复后的实现候选，要求另行完成 Task 状态收口。
本次用户指令为：“下一步就是M6-008收口，准备进入M5-007”。

本 feature PR 提议 `M6-008 READY → DONE`、`M5-007 BLOCKED → READY`，只改状态及派生导航，
保留目标、依赖、验收和具名 owner。依照 [DEVELOPMENT 5.2](../../../DEVELOPMENT.md#52-pr-类型与-tasks-授权)，
同一 PR 可完成当前 Task 并激活前置已满足的后继 Task。本记录接受合入后，状态才进入 develop。
本收口 PR 仍需当前 diff/CI 的 cross-owner review，不将原实现 APPROVE 复用为新 PR 审批。

## 原验收逐项闭合

| M6-008 验收项 | 已接受的实现与证据 |
|---|---|
| A1/A2 public projection | `baseline_envelope.py` 与 envelope Schema 采用严格白名单；Task/Profile/Mode/Method/Capability 控制留在 metadata。A1 无 Tool，A2 只暴露 qualified exact interface；公开自然语言公平性仍由冻结者负责 |
| A2 shared qualification | `produce_a2_qualification` 消费 M5-006 validator，核对 runtime execution、Task/Requirement/Supply/implementation/interface 和收窄边界；M6 不产生 A3 record、不取得 Supply selection |
| 每次调用的输入闭包 | Provider / Tool use-boundary 重验全部 refs、实际 callable、同名 Tool 的全部 Requirement availability；请求与观察历史逐轮重建，拒绝漏验、漂移、替换和 history 注入 |
| trusted time 与终态 | 一次 end-clock sample 绑定判定与终态 fact；completed 要求成功最终响应、Tool loop 闭合、elapsed 严格低于冻结时限。达限、超时、缺失响应和未执行 Tool 的全重哈希反例被拒绝 |
| actual facts / Trace / Validation | 每份 fact 有紧邻观察事件的 hash-pinned 创建事件；checker source snapshot 与本次 Trace/output 的 exact Validation subject closure 被独立检查 |
| 独立 replay 与 lifecycle | `verify_baseline_receipt` 从文件闭包重算，不重跑 Provider/Tool。A1/A2 completed、turn-limit failure、timeout、preflight-blocked 五个实际本地 synthetic 案例均通过冷回放 |
| 权威边界 | 三种生命周期均保留；`task_completion=false`。没有自动 fallback/reselection、Human/Claim/Skill admission 或科研接受权威 |

源码入口与残余约束见 [README](README.md) 和 [Risk Ledger](RISK_LEDGER.md)。
本轮 [接受证据归档](attempts/M6-CLOSEOUT-001/evidence/closeout-evidence.json) 保存 review/merge 来源、
实现及 Schema pins、原案例归档 pin 和 CI receipt 摘要；development Trace 如实标注 capture gap。

## exact implementation 证据

- reviewed head 与 merge commit 的 tree 相同；归档 `A-20260916-003` 的三个 implementation source pins 与合入源码相同。
- [实现 CI 35082325569](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35082325569)：
  Python 3.11/3.13 各 1,329 PASS，零失败/跳过；impact coverage 1,293 项证据通过；
  三个 baseline 模块 line/branch 100%（582 statements / 120 branches）；package、repository、documentation 与 test 汇总均通过。
- plan `55c27151507c90add323ae29d2a550b3a9b1a4c501cf515e975439990ab0b773`，
  merge target `ab97430f87df2ff57ae75d35da5670477778380e`；其 tree 与 reviewed head 相同。
- [最终治理检查](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35083993070) 通过。
  新的收口 PR CI 独立验证本次文档/状态差异，不重新标注为实现回归证据。
- [五案例归档](../../../../work/M6-008/A-20260916-003/README.md) ZIP 为 375 个成员，
  SHA-256 `a4c894d871de4a0bf2a1de016851fd907c479d418157f96c5013bb4638fd53af`；历史归档原字节保留。

CI 总耗时为 16m54s，rebase 前 13m37s；选测仍为 91/92 behavioral modules。
这是单次执行对照，不作 PR83 提速或分析器性能回退结论，详见
[耗时记录](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75#issuecomment-5695844753)。

## 交接结果

M5-006、M11-004/006/007 已 DONE，Gate B 已 SATISFIED；本 PR 将最后一项实现依赖 M6-008 收口后，
M5-007 可进入 synthetic Harness 开发。具体切片、输入和负例见
[M5-007 进入计划](../../chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_ENTRY_PLAN.md)。

下一实施 PR 从冻结 plan / evaluation-side preflight 开始，保留两种 transport 和独立 replay 入口。
M5-004 继续受真实 case、live conformance、admission 和 Human review 条件约束；M6 DONE 不提供这些证据。
