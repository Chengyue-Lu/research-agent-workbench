# Root 文档独立窄审 — AUDIT-RWB-DOCS-003

2026-10-07；Profile：targeted documentation reviewer；required-Skills=[]；5 分钟/一轮有界复核。
只写本报告与 REVIEW_COMMUNICATIONS；未改 canonical，未执行产品/API 测试、Tool、Key、账、安装、Git、memory 或再委派。
base SHA 采用本 Task 已知输入 `d3c4d23206339ebc7f18b5621f3aa5453f96335e`，本轮未重新调用 Git。

## 发现

**R1 / P2：Harness 末行保留过期的 M5-007 IN_PROGRESS，形成第二套冲突状态。**

定位：[SYSTEM_EVALUATION_HARNESS.md:257](../../../implementation/SYSTEM_EVALUATION_HARNESS.md#h5持久化四臂证明pr106-已接受)（本次审阅 SHA `f78c67980aad62ad4acb4ebc68c7ed5e9063cff46d8086a54f2c82c44d0b19e3`）写“整体验收仍需独立复核，Task 保持 IN_PROGRESS”。该文件 10–11 行已将接受证据和实时状态交回完成记录/TASKS，而 [TASKS](../../../TASKS.md) 的 M5-007 exact 行是 DONE。读者按末行选择下一动作会错误重启已闭合验收，且违背本轮状态单一来源要求。

最小修复：删除第 257 行；或替换为“整体验收及其边界见完成记录；实时状态见 TASKS”。只修活跃实现说明，不改 H4c/H5 历史 Attempt 原件，不扩大其 live/科研资格。已向 Root 发送精确定位；本报告保留发现快照，不把建议写成已修复。

## 四个目标的复核结论

| 目标 | 直接观察 | 结论及限制 |
|---|---|---|
| accepted authority / 默认行为 | Provider 15–18 为 optional Session，显式预绑定且无选择/fallback/whole-Task 权；Host 13–15/58–61/75–82 保留单 slice、caller 多 slice、preventive/detective 与 report≠Receipt；Development 106–138/159–183 保留 Task/DAG、immutable DONE、单 PR 人类例外及硬门禁 | 已读范围未发现无依据扩权；不认证未读取 ADR 正文、源码默认实现或远端规则 |
| API 诊断与正式 Trace 留存 | Provider 50–55 明确 credential 不留存、正式 Attempt 按 Task policy 捕获获准 request/response/Tool 原件，shape-only conformance 不能替代完整 Trace/archive；Testing 14/18–20/29–33 区分 live proof、slice authority、attempted/unknown 和冷回放 | 未见诊断例外被泛化到正式科研执行；不把文档声明当实际捕获证明 |
| 新 Task 与 M5/Topic 5 | 三条 READY scope 与定义 workstream 14–22/30–35 要求真实产物消费、总预算、Guide 独立 approved-ref 只读、unknown/blocked 和科学/live/admission Gate；Harness 66–68/122/131–133/208–224 保留 synthetic purpose、外部 verifier 和科研计量边界 | 未见新桥接 Task 改成四臂净价值评价或自动恢复；没有为 PR140/候选 prompt/Skill 代签资格 |
| 精简是否丢唯一必要条件 | Source 20–29 保留 dry-run/execute、exclusive publish、inbox 禁引用、raw sidecar/hash 与完整路径段区分；State 26–37 保留 revision、duplicate、hash、role/type、latest-current、supersedes 和 provenance closure；Harness H1–H5 保留外部 refs/time/verifiers、失败/retry、blind/reveal、overlap/pairwise/metric unavailable 与历史不可改写 | 除 R1 状态残留外，未发现已读必要条件被删除；本轮不以无 Git diff 的阅读证明所有历史字节不变 |

## 实际读域

- 全文：implementation/README、PROVIDER_ADAPTER_PLAN、TESTING_STRATEGY、RESEARCH_STATE_CANDIDATE_CONTRACT、SOURCE_ADMISSION_CONTRACT、SYSTEM_EVALUATION_HARNESS、THIN_EXECUTION_HOST；DEVELOPMENT；decisions/README。
- 全文：workstreams/README、chengyue-lu/README、huangyi/README 与 RWB-CHAIN-TASK-DEFINITION/README。未递归进入索引指向的历史 workstream。
- Task 定义：此前本组已读 TASKS 全文；本轮精读 M1-010/M2-009/M11-008、M5-007/M5-008 与 Topic 4/5 prose，保留之前完整输入作为上下文。
- 两次组合输出局部截断后，补读 Testing 35–45、State 1–8、Development 173–212 与 decisions/README 全文；Harness 1–257 单独完整读取。
- 未读取 public 函数/CLI 源码 metadata，因为没有依赖该扩展才能定位的剩余问题；无日志、凭据、账或产品执行。

## 审阅输入 pins

| repository-relative 文件 | SHA-256 |
|---|---|
| docs/implementation/README.md | `0af6d3e8de5190a520b94a906ea9fad5e4926799f879ed11c4eeb454bcf38ca1` |
| docs/implementation/PROVIDER_ADAPTER_PLAN.md | `ee3a061e2c0d409c4f74572f30d9ec378f0bcc56645289edc82d9c67af8f4076` |
| docs/implementation/TESTING_STRATEGY.md | `429924da38ab8fa549643d072b3bb6c52ab12ac7f561b85e7ce211c1ebdc83c1` |
| docs/implementation/RESEARCH_STATE_CANDIDATE_CONTRACT.md | `0613b81b89dad5eb0fcf0c65b0d43779337cfc9c18ad1b855aeeb83c804d1191` |
| docs/implementation/SOURCE_ADMISSION_CONTRACT.md | `41201a6b159ad8c1221187142ff25ab8bc23ea876fb66ba1072b43f17ac160e5` |
| docs/implementation/SYSTEM_EVALUATION_HARNESS.md | `f78c67980aad62ad4acb4ebc68c7ed5e9063cff46d8086a54f2c82c44d0b19e3` |
| docs/implementation/THIN_EXECUTION_HOST.md | `f688280f8e38afd199a9d60a0f22355968dff9c15694d4c6976dd67c2072e0e5` |
| docs/DEVELOPMENT.md | `18e42ea64fec58f49a3d090e5bf07a06822cf10ca7cb36e12bde421a7e5c9a20` |
| docs/decisions/README.md | `39d44de912e4e659642c603b1908d7b72cea55ac76a44625fc7441976d720c86` |
| docs/workstreams/README.md | `a5be72057bed6986ae102cd8f2a0ff2a304a301353159fdbfe1db38b6ca6ff38` |
| docs/workstreams/chengyue-lu/README.md | `be443fccf0cc75c255d24f12708ebffbca546e2780e2622b23773dc54e8c0155` |
| docs/workstreams/huangyi/README.md | `1de5a8fee62f23d6a037bec68fe514e762118e438a3d362d2d370d51f2be6751` |
| 本目录 README.md | `eb0fdb4b12a96f9790699b82f5974ff073af6c8b058d3739e3bb1df21e6d5d3e` |
| docs/TASKS.md | `1beb8e4ad6e4f8a0ca9f8cb10b4effe9ceefe94eae929838e26bb57af7fee566` |

不作全仓架构批准、live/CI/科研验证或合并决定。Root 修 R1 并完成其最终文档检查；本组报告交付后停止。
