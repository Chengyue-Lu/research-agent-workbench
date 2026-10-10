# 执行阶段证据验收

2026-10-10；PR140未合并候选。本切片实施与验证正在进行，下面只记录已经完成的事实。

## 已完成的治理同步

人类明确要求先合并PR142。最新head `e602c2a1e50f488e7dc311568382f34c66902e02`的七类checks全成功，base `e49386140c18cdfb9e6065b7c59e2545f863e386`，冲突与实质changes-requested均无；四层ruleset fresh GET保持active、零bypass，两review层审批数0，hard层PR/CI/保护继续有效。

PR142正常squash为develop `67a7c5f6a0c3495f1ad583864d87b25f5bf892e2`，sole parent为上述base，tree与exact source head相同；未用admin，未改rulesets。M0-008已合并DONE。本分支随后同步新develop，STATUS一处文字冲突保留双方事实；PR140仍未合并。

## 新实现验证

本轮最终覆盖 68 个不同本地用例：首轮 67 项保留 1 failure / 9 error 记录（含参数化子例），原因是新 stage assessor 将 producer 的 `revision:null` 与省略可选字段直接比较；现有 caller/正式 Handoff 回归通过。修复统一 pin 表示，保留非空 revision、hash、Task、attempt、body 和读取授权检查，未改原失败断言。受影响的 stage/Guide/state 及新增非空 revision 正反例共 23 项复测全部通过；不重复计数此前已通过的不同用例。

覆盖实际离线 workflow/Handoff/checkpoint 的 0/1/2 子任务阶段来源、原 caller 的 0/1/3 子任务与 Receipt 冷回放、失败/未知/未开始、负面项保留、缺 grant 不读源、旧无 journal 为 unknown、来源/phase/authority/hash 篡改、越写域与禁止覆盖。文档检查通过：95 个 Markdown 文件、394 个本地链接目标；新 develop 中原有 73 项 DONE 行保留。R2 治理预检接受三项 READY→IN_PROGRESS，完整验收未完成。

实现代码来源 `509c0be`；CPython 3.11.16 的独立安装包验证通过，9 个模块与 source 哈希一致，默认 Runtime resources 与实际离线阶段链可消费。wheel SHA256 `c112b6275b0d22ab87df5ba97804d6083f15e12919cd933c24d38ba018c8c4dd`，resources SHA256 `735e136de0c43f402de7462a7ff47f71c8b014c352d2ab6b9494f4139a79f5ca`。前一轮 218 个不同本地 case 与 3 个完整实际链属于[前一来源](../planning-handoff-004/VERIFICATION.md)，不作新 HEAD 通过证明。

## 实际测了哪些桥接

全部材料为公开合成记录：alpha 有 id 与 locator；beta 有 id、缺 locator。目标是核对实际执行和结果消费；缺 locator 不等于来源无效。没有研究、Skill 或 Source 接受。

| 模块 / 桥接 | 实际输入和执行 | 输出结果与消费者 |
| --- | --- | --- |
| intake → 冻结执行 | 真实 API 返回 Protocol/Task/Method 草稿；caller 重读本次 refs，factory 冻结 planning 身份及各角色 Bundle/View | 3 份实际 planning Receipt，分别绑定本角色 Task 与冻结链；新进程冷回放通过 |
| main → child → fresh main | 初始 main 实际提出一个有界 reviewer Task；独立 child 返回 beta 缺 locator；新 main 请求带完整已核验 child Handoff | 主响应具体比较 child 与自己的观察，并保留 source acceptance unknown；实际 HTTP 内容审计确认完整 packet、usage 和 refs 进入新 main |
| workflow → 阶段证据 | 最后事件后固定 journal，结合 exact report 与 child/final Handoff 重算 | 3 条有序阶段：main planning、child、main consume；来源、usage、限制及实际消费标记进入版本化 sidecar |
| final Handoff → checkpoint | 原正式消费者核验 actual result；显式选择发布 stage sidecar | MainState machine/index refs 固定 stage 与全部核验来源；限制、未解项、人类待办保留，accepted_decisions 为空 |
| checkpoint / stage → Guide | 独立 API 只读取 MainState、stage 和最终 Receipt 三份明确获准快照；Handoff/source/task/journal 另作获准前置核验 | 实际请求体 32,546 bytes，完整返回 189 output tokens，0 Tool；原始核验文档未成为额外模型快照，项目 bytes 完全不变 |

Producer Attempt `chain-535da9e9-8128-4867-961b-94937a344e14` 使用上述代码，4 次实际 HTTP，新增 known 19,776。它在临时 120 秒总时限耗尽后、Guide 派发前停止；保留 stopped，不标整次完成。已发布的 3 Receipt / 2 Handoff / checkpoint 在安装包新进程重放通过（模型 0 次），实际 28 份账本原件、101 份项目原件及 4 HTTP request/response 内容审计通过。child/final packet 也通过既有 Handoff integrity Skill 的结构检查。

随后通过明确的工件边界单独验证尚未派发的 Guide。一个入口包装器 accessor 错误在 preflight 停止，0 HTTP / 0 usage；另一轮真实响应触及 1024 output tokens、finish=length，新增 known 10,655，保持 stopped。初次零调用装配还发现重复 final-Handoff 快照导致请求体 38,341 bytes；调用方选择必要的三份快照，并明确本次简短回答范围，未改变包内权限或接受契约。废弃的一份未派发 preparation 与全部原件保留，未重写历史、提高上限或自动 retry/fallback。

最终 Guide Attempt `chain-2787de4c-a2a5-4ab6-901b-959d288c1d22` 实际 1 HTTP，4.578 秒，input 9,634 / output 189，新增 known 9,823，finish=complete。冷核验确认三个获准快照与 producer / consumer 原件 exact bytes 相同，前置 source-check 与实际 wire payload 一致，Guide 无 Tool、无项目写入、无 main 回传。实际回答区分 ordinal 1 的早期未返回与 ordinal 3 的真实消费，下一人类判断为采纳/拒绝当前 disposition 及 Source/Claim 判断。开头将三个阶段统称为 main-role stages 仍有角色措辞不精确；它不是通用 Guide 内容质量通过证明，完整审核按后续 Task 进行。

本切片累计新增 4 份闭合账本、6 个实际 HTTP；包含停止、截断及成功用量。总 known **462,388 / held 0**，上限 10,000,000，剩余 9,537,612。旧 17 份账本与 2,082 份原件、当前 28 份账本重新核验；新增实际请求均受北京时间 18:00–09:00及每请求 fresh 官方闲时限制。临时 6 calls / 1024 output / 32768 bytes / 120 秒为测试配置；本轮分段接合不宣称单个 120 秒 Attempt 跑完整链。最新 HEAD 的 hosted CI 以 GitHub Checks 为准。

M2-009/M11-008保持IN_PROGRESS；M2-013/M3-012仍PARKED。未关闭研究风险，未接受Skill/Source/科学/Human判断，未启动自动恢复。当前范围见[Task Packet](TASK_PACKET.md)。
