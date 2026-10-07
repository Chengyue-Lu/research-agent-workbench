# 架构与模块文档 Compact Handoff

任务：AUDIT-RWB-DOCS-003；Profile：bounded documentation worker；required-Skills：[]。
日期：2026-10-07；状态：本窗口文档编辑与静态检查完成，交Root集成。不是merge、R2接受或产品测试完成。
声明基线：DOCUMENTATION_TASK_PACKET中的develop d3c4d23206339ebc7f18b5621f3aa5453f96335e；本轮没有Git操作。

## 实际结果

- ARCHITECTURE/CHARTER补全人类需求或显式既有材料→Protocol/Task/Method/Capability→冻结执行→结果消费→
  Main State/Human的职责接点；新旧入口共用研究契约，缺失保持未知。
- main动态决定0..N有界子Task；职责可合并会话；Profile、职责指令、Skill、模块和会话分别说明。
- Guide独立只读批准的Main State/显式refs，回答不自动回传主执行或写研究状态。
- DEVELOPER_ARCHITECTURE_MAP从661行缩为183行：逐跳producer/contract/consumer/启用条件；状态/成熟度/方向
  回到TASKS/STATUS/ROADMAP，不在第一接触面保存旧任务快照。
- 10模块均补接点与条件，README增加横向表；Source/Evidence/Claim/MethodTrace/Need维护/四臂价值评价是
  条件启用外环，未制造固定科研DAG或新coreRole。
- 清理实施历史与旧状态，细节保留为原契约/兼容/历史链接，未修改旧证据。
- 总审后进一步修正：Skill Assignment仅legacy Skill-bound兼容；当前Skill运行依赖合法
  Projection/Supply/Snapshot/View锁及实际加载/consumption/Trace/closeout，不要求Assignment。
- 模块05Task YAML声明为字段示意，不能冒称完整可执行输入；Root随后Schema实测。

## 自检与限制

14份拥有文档的相对Markdown文件目标均存在，Skill边界修正后复查仍通过。公开架构/章程/模块的旧M任务
DONE/PARKED/BLOCKED快照、当前已实现/本PR及本机路径搜索无命中。未检查所有fragment锚点。

0产品测试、0CLI/API/生产Tool、0Key/生产账/私有oracle读取、0Git/安装/config/memory操作。
仅按明确引用读取公共接口片段和ADR章节。详情/读集/问题/待决见ARCHITECTURE_AUDIT.md；实际可见
通信见ARCHITECTURE_COMMUNICATIONS.md。Task归档的初始cwd字段已明确规范化为当前仓库根。

保留唯一Supply selection、Bundle→View→Host、View不重选、无fallback、最严交集、planned/actual分离、
slice-only Receipt、Human authority、可选Skill维护外环及PhaseC/Topic5 Gate。未宣称候选入口已合并、
自动接合、live可用、科研正确或正式接受。

## Root下一动作

1. 合并其他拥有面的文档校准，核Task例Schema与current Skill接口措辞，完成统一Markdown/公开闭包检查。
2. 若Schema实测发现示意仍易误解，提供合法当前Task片段或保持明确示意；不通过文档补造执行资格。
3. 更新共享PROJECT_MEMORY唯一own-row并记录本地文档结果、来源、验证范围与后续动作；本窗口未写memory。

建议PROJECT_MEMORY摘要：2026-10-07 AUDIT-RWB-DOCS-003：架构/章程/地图及10模块完成本地校准与精简；
补应用职责与模块接点、new/existing intake、main0..N、Guide只读；Assignment限定legacy，current Skill用
Projection/Supply/View及actual consumption；静态相对链接目标检查通过，未跑产品/API；来源本工作流
ARCHITECTURE_AUDIT/HANDOFF/COMMUNICATIONS。下一步Root统一Schema/公开闭包检查与集成，未宣称合并或科研接受。

## 当前输出 pins

以下SHA-256固定本窗口交付字节；后续Root编辑须重算，不以旧pins覆盖别人更新。

| Repository-relative path | SHA-256 |
|---|---|
| docs/ARCHITECTURE.md | 9f453f0e8cb3e53de04ffabc7682b504620d6ce19e7854b2744905c5a17daabe |
| docs/DEVELOPER_ARCHITECTURE_MAP.md | f37177671011a8fc9ae6d970ff42fd9a3f9ed0e931fedd73b3f3b07d1c074dd2 |
| docs/PROJECT_CHARTER.md | ef4b2019e03102bfb148958350e98847fae3646af7a6eba18bc35068e559d2c8 |
| docs/modules/01-RESEARCH_KERNEL.md | 53066b7cac04876ea89c030efe2b3cd90b3f8b41793c121f066c7993d2a8e767 |
| docs/modules/02-PROTOCOL_AND_MODES.md | 2cf3592fef3a91c213c8bfe8780c4f212efdc42d7e9fd5e41d0a8ee3add48eb6 |
| docs/modules/03-AGENT_RUNTIME.md | db23724793b456efb10dd3e1b03713f53e07ad75e3c781ca4890fe4cc829a7ec |
| docs/modules/04-SKILL_SYSTEM.md | d4dabca8c782fb2b7fc2048f98fbe7641d59851c4490ff31a00c618f732b3590 |
| docs/modules/05-TASK_AND_HANDOFF.md | 9b804d47bd32c2246c32c682b106408118d048cb53cd82997396449077574664 |
| docs/modules/06-CONTEXT_GOVERNANCE.md | c8fcc72e73638aee2cb8341104ee04ff04d2c9a21f6b824d6961b29ca2ac5492 |
| docs/modules/07-ARTIFACTS_AND_PROVENANCE.md | 097d1e7cf5b323ec7b2cf54c9b555144696e1858fe07c099972369d7552bb081 |
| docs/modules/08-VALIDATION_RISK_AND_GATES.md | ce2896a1431a6c6b98bf1cc5ae46b22f8daab7e52f17a6beb9a3f337412c239f |
| docs/modules/09-ADAPTERS_AND_INTEGRATIONS.md | 7e8d4868f6b6f868680146138d5b9925770ccd8ad79b361b579e6e0aa9e6bc04 |
| docs/modules/10-OBSERVABILITY_EVALUATION_COST.md | 056fa15f7c3aabf103b96a264bdadfa02b776d43e778b0a3e52d7b4fa6a80a3d |
| docs/modules/README.md | 620973832c25a534591de5ee12deaf82c3d834767a97ad3da1cadd04087e922d |
| docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/ARCHITECTURE_AUDIT.md | 5cc01088c0513df855662712b7cdc7014b82c856e9f3a70295ff0dd648ef893d |
| docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/ARCHITECTURE_COMMUNICATIONS.md | e2352e7c509baf98346aa791383869c8b331cf503e7184eb6f81f91ecc71eba4 |
