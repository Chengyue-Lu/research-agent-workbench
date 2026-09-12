# M12 / M13 后续任务边界候选

状态：待独立接受的 Task drafting 输入，表中工作包不是 canonical M Task ID，也不授权执行。责任和现状见 [README](README.md)。

## 1. M12：一个 action 边界的实际接续

**用户结果：**上一 action slice 闭合、原会话结束后，下一执行者凭项目文件创建新 Attempt，继续原 Task 范围内下一项已经冻结的 action，得到实际产物、Trace 和 Receipt。

已有地基可复用：Main State 的 checkpoint/resume-check、Research State/Failure/Method Trace、Handoff 的分级审计，以及 M11 generic closeout。具体代码是 [recovery preflight](../../../../src/research_workbench/execution/recovery.py)、[Handoff audit](../../../../src/research_workbench/context/handoff_transfer.py)、[Host](../../../../src/research_workbench/execution/host.py)和 [generic closeout](../../../../src/research_workbench/execution/generic_closeout.py)。

现有 `prepare_recovery_attempt()` 只返回含可选 RecoverySeed 与 risks 的 RecoveryPreparation，CLI recovery-check 只显示 risks，没有创建或启动新 Attempt 的当前 Runtime consumer。M11 generic closeout 仍显式不授予 Topic 5 authority；legacy mandatory Skill 字段不能通过伪造 Assignment 填入 no-Skill 接续路径。

| 工作包 | 负责人建议与依赖 | 验收对象 |
|---|---|---|
| 连续性映射与独立 Task 定义 | 黄毅负责 consumer，路诚钺负责 State/Method/continuation 语义；先有 Phase C 具名收口 | Main State、Research State、lineage、Handoff、已完成 slice 和下一 action 各自职责；一个最小 Task 的允许读取、写入、输出、停止与验收 |
| 新进程实际接续 | 黄毅实施、路诚钺审语义；依赖前项接受及已有 M10/M3-009/M11 Core | 新 Attempt/目录唯一，源状态和旧执行闭合可定位；实际只执行下一 action；保留旧工件和新实际 Trace/Receipt |

Main State 是控制恢复入口；Research State 保存研究含义；旧 Receipt 证明 action slice 的执行事实，不代表整个 Task 完成。原 Control/Resolver 生成 Resolution/Snapshot，既有 Bundle/View producer 按冻结 selection 生成后续执行输入，再由现有 consumer 重验。引用漂移、View 过期、研究前提变化或 Human Gate 缺失时，给出明确阻塞；需要新选择时回到原 Resolver，continuation consumer 不重选 Supply 或扩大权限。

初始案例可复用既有整数递推或标准库仿真工件，在**已闭合 action 之间**验证接续。具体暂停点、下一 action 和输入需在 Task 中冻结；不修改 Host 为运行中 safe-paused，不把未完成调用伪装成已完成 slice。

实施验证限于一条 fresh-process 接续及直接破坏该路径的 pin 漂移、Attempt 复用、下一动作/许可缺失反例。检查已完成 action 不重复执行、阻塞不调用、旧工件保持不变。复用 fixture 和消费者，记录读取量、准备/执行时间及人工纠正，不新增任意耗时阈值或进程 kill 笛卡尔矩阵。实时取消、salvage、外部副作用恢复在有实际案例后另行定义。

M5/M14/Skill admission 不作为这条 no-Skill 功能的新增硬依赖；M4 接受状态不变。原 M3-001～007 PARKED 历史行不重开为恢复 umbrella。

## 2. M13：先定位一个真实反馈问题

目标沿用计算/仿真协作。候选问题是：已有失败原因和用户纠正可用时，下一相似 Task 是否仍重复同一模型行为，增加研究者返工。**当前没有可用于判断这一现象的稳定真实样本。** Case B 合成 Failure 只能作表示示例；PR70/71 的确定性程序缺陷应修程序，不是训练模型的依据。

| 必要输入 | 当前状态 |
|---|---|
| 实际 Task/Attempt/工件及版本 | 待正常试用采集 |
| 用户纠正原文、依据和适用前提 | 待实际反馈，不强制评分 |
| 在后续任务中的重复及条件变化 | 未测量 |
| 反馈用于个人/项目后续适应的范围 | 具体样本按用户选择记录；默认本地本次 |
| 现有 M2/M7 不能承载的独立策略职责 | 尚无充分证据 |

先按原因确定承载处：

| 原因 | 优先路线 |
|---|---|
| 参数/说明缺失 | Task/Project Protocol 澄清 |
| 程序、路径、hash 或工具错误 | 对应实现修复与窄回归 |
| 数值摘要优先等协作偏好 | 有作用域、可撤回的项目/个人配置设计；不自动成为 Skill |
| 可复用的非平凡方法程序缺口 | M7 Need-first 与 M9 Evaluation/Admission/Lifecycle/Release |
| 仍无法表达的跨 Task 策略职责 | 以真实反例、消费者和维护成本论证独立 M13；再走 R2 task-definition |

准备阶段允许 `reuse-existing / bounded-new-family / defer`。改进能在现有模块完成也属于推进成功。M7-013 的既有 `hold-no-skill` 结论及 M7-014 的 PARKED 状态不被本建议覆盖。

样本具备后，只冻结 direct 加至多一个 prompt/example/config 候选。固定配置与改进配置获得同等可用历史/反馈，模型、工具、信息可获得性、运行预算一致；候选制作/筛选和最终未见 Task 分开，private oracle/终评分不回流优化。分别报告科研质量、人工分钟、运行成本、反馈整理/筛选/维护/撤回成本，保留失败、暂停、重试和退出。收益不足或新前提下错误固化则简化、撤回。

改进只对后续 Task 生效，不原位改变 frozen Task/Method/Snapshot/View，不自动准入公共 Skill，不删除历史 Evidence 或回滚科学结论。收到反馈、待核对、采用和失效分开；已授权的后续用途持续有效，跨项目共享/外发另按其实际用途边界处理。

该纵向候选不改 M5 既有四臂和 ADR-0020 estimand。参数训练、自动候选搜索和通用策略引擎都不是首个交付。未来只有可靠数据、评价和维护瓶颈支持时，才分别比较参数训练或最小反馈桥的价值；[ADR-0019](../../../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md) 的 Runtime→Maintainer bridge 仍有自身进入条件。

## 3. 并行与成本

M12 语义收口和 M13 真实反馈归因可以并行准备；两人实施/审查容量必须计入排期，不能将多个工作树当成额外人力。M5 仍按已接受任务推进，不等待本提案。M12/M13 的运行和试验分别依赖其实际已接受契约、案例和预算，不把全部 M5 DONE 设为材料准备前置。

本 PR 只检查链接、来源、任务与依赖一致性，不运行功能实验或 full/coverage/install/model 测试。未来实现只对新增行为做必要检查。材料支持范围不够时记录具体缺口，不通过追加通用防御机制替代研究和产品目标。
