# 执行阶段证据验收

2026-10-10；PR140未合并候选。本切片实施与验证正在进行，下面只记录已经完成的事实。

## 已完成的治理同步

人类明确要求先合并PR142。最新head `e602c2a1e50f488e7dc311568382f34c66902e02`的七类checks全成功，base `e49386140c18cdfb9e6065b7c59e2545f863e386`，冲突与实质changes-requested均无；四层ruleset fresh GET保持active、零bypass，两review层审批数0，hard层PR/CI/保护继续有效。

PR142正常squash为develop `67a7c5f6a0c3495f1ad583864d87b25f5bf892e2`，sole parent为上述base，tree与exact source head相同；未用admin，未改rulesets。M0-008已合并DONE。本分支随后同步新develop，STATUS一处文字冲突保留双方事实；PR140仍未合并。

## 新实现验证

本轮最终覆盖 68 个不同本地用例：首轮 67 项保留 1 failure / 9 error 记录（含参数化子例），原因是新 stage assessor 将 producer 的 `revision:null` 与省略可选字段直接比较；现有 caller/正式 Handoff 回归通过。修复统一 pin 表示，保留非空 revision、hash、Task、attempt、body 和读取授权检查，未改原失败断言。受影响的 stage/Guide/state 及新增非空 revision 正反例共 23 项复测全部通过；不重复计数此前已通过的不同用例。

覆盖实际离线 workflow/Handoff/checkpoint 的 0/1/2 子任务阶段来源、原 caller 的 0/1/3 子任务与 Receipt 冷回放、失败/未知/未开始、负面项保留、缺 grant 不读源、旧无 journal 为 unknown、来源/phase/authority/hash 篡改、越写域与禁止覆盖。文档检查通过：95 个 Markdown 文件、394 个本地链接目标；新 develop 中原有 73 项 DONE 行保留。R2 治理预检接受三项 READY→IN_PROGRESS，完整验收未完成。

安装消费和必要实际 API 结果仍待执行。前一轮 218 个不同本地 case 与 3 个完整实际链属于[前一来源](../planning-handoff-004/VERIFICATION.md)，不作新 HEAD 通过证明。累计 known 422,134 / held 0 为本切片开始时的账，不因新 Task 重置。

M2-009/M11-008保持IN_PROGRESS；M2-013/M3-012仍PARKED。未关闭研究风险，未接受Skill/Source/科学/Human判断，未启动自动恢复。当前范围见[Task Packet](TASK_PACKET.md)。
