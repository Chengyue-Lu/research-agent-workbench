# 真实 API 测试：模块、输出与消费

2026-10-08 · Root 实际执行与冷核对；PR140 隔离开发候选。

**Attempt15 在同一次6次 HTTP 调用中完成 intake→main/Tool→child→fresh main→checkpoint→Guide，child 与 fresh main 均返回 complete。** 这是本例启用的接口和消费者接通证据。Attempt13 的 child blocked、Attempt14 的 main blocked 保留原结果；后续角色说明修复没有改写这些原件。未接入真实项目，也未评价研究净价值；当前时段限制仅用于本轮测试。

## 测试输入与执行方式

全部请求使用同一供应商的独立 DeepSeek Flash API 会话，材料是公开的合成短文本：alpha 声明有 id 和 locator，beta 声明有 id、缺 locator。目标是报告缺失项并保留未知，不把两个记录升级为真实证据。main 在人类 ceiling 内决定是否委派；Root 没有固定 child 数量或预置 child 结果。

intake 当前采用受控转录：模型复制调用方给定的 Protocol、Task、Method 模板，返回可校验草稿。其真实产物 pins 被下游使用。它验证请求、产物和消费者的桥接，不评价从一句自由需求自行设计方法的能力。

当前配置：`evidence-synthesis` mode、隔离候选 `ENTRY-A1@0.1.0` action、`entry-api-bridge` capability、`chain-main` Profile、no-Skill；main 和 child 均消费各自的实际 Task，不继承完整聊天。候选 prompt/三个 Skill 文件尚未装载，不据此声称 Skill 路径通过。

## 逐模块的实际结果

| 模块 | 实际输入→输出 | 消费证据与结论 |
|---|---|---|
| 人类输入→intake | 合成意图＋独立 ceilings→模型返回控制 JSON；compiler 校验并发布 Protocol/Task/Method refs | 后续工厂使用本次返回 pins。多个实际 intake 成功；Attempt6 LENGTH 被拒绝，无成功草稿 |
| Capability→Bundle/View | 当前实际 Task＋独立候选资格检查/observer→selection、冻结 Bundle 和 View | main、child、回接 main 各自冻结。仅为本次隔离技术观察；正式 Source/具名接受仍 false |
| main→child | Attempt15 main 两轮合计 input6581/output1018、readonly Tool1次，自选 `CHAIN-API-CHILD-1` | 独立 child 实际 API input1464/output341、decision=complete；非 Root 代填结果 |
| child→fresh main | child 验证已核验快照，报告 beta 缺 locator；回接 main input4188/output645、complete | main 明确消费本次 child 的实际 disposition、usage 与结果；三个执行切片均有 Host/Trace/Receipt |
| 执行→MainState | 本次 hash-pinned workflow＋实际 Protocol pin→独占 checkpoint | Attempt15 workflow 含 intake 为5calls、known21922/held0；checkpoint 发布。task_completion=false、human_acceptance=false |
| MainState→独立 Guide | 本次获准 MainState＋独立问题→同 Attempt 第6次 HTTP | input2738/output202、COMPLETE，项目文件字节集合不变；Guide 未回灌 main。正文解释质量局限如下 |
| 模型→readonly Tool→模型 | Attempt15 readonly handler1、模型2轮；原始结果保存并进入下一模型请求 | 实际 Tool 消息与原结果 bytes/hash 一致，Host/Trace/Receipt 完整；A12～15四份独立冷证明通过 |

可读输出示例（忠实摘要）：Attempt15 child 报告 alpha 有 id 和 locator、beta 没有 locator，保留合成材料和未定义字段的限制。fresh main 明确消费该 child 的一次模型调用和结果，返回 complete。Guide 独立回答并保持项目不变，但因只读取 MainState、未展开 Receipt 正文，使用了“没有 Receipt 确认发布”的表述；实际 machine refs 与 Root 冷检已有 Receipt。接口成功不等于这句内容正确，解释质量缺口保留。

## 每次 Attempt 的停点

| Attempt | HTTP 调用数 | 新增 known tokens | 实际结果 / 修复 |
|---|---:|---:|---|
| 1 | 1 | 7,388 | intake 成功；Root 构造 Supply 的 enum 错误，main 未发送；修复 caller |
| 2 | 1 | 7,410 | 选择成功；Method 缺 blocked_conditions，View 未冻结；补齐候选输入 |
| 3 | 1 | 7,374 | Bundle 比较可省略 Task revision 时不一致；按已有默认 revision=1 修复 |
| 4 | 1 | 7,344 | Trace 初始化仍直接取可省略 revision；同一默认值修复 |
| 5 | 2 | 8,966 | main 实际选择1 child，但 child Task 缺必需 forbidden_skills；child 未发送；请求加入现有 Task Schema |
| 6 | 1 | 7,504 | intake output1024、finish=LENGTH；无成功草稿，原响应保留 |
| 7 | 2 | 10,079 | main 自选0 child、执行成功；Root checkpoint caller 引用类型错误；修复后以原件克隆冷验证 |
| 8 | 2 | 10,166 | main 自选1 child；旧 network 比较误判、Profile ID 无可用绑定；child 未发送；复用权限比较器并传入可用 Profile |
| 9 | 5 | 19,653 | intake→main→child→main→checkpoint 成功；同次 Guide LENGTH。原 caller 的 completed 旗标是过度声明，原件保留并在此纠正 |
| 10 | 3 | 11,875 | intake→main 自选0 child→checkpoint→Guide COMPLETE；零 child 闭环成功 |
| 11 | 2 | 10,262 | Tool handler1，结果 Trace 写入失败，安全停止；Root 复现276字符路径失败、251字符短名成功，开发（4）修复命名 |
| 12 | 5 | 20,104 | Tool循环与三执行Receipt成功；main自选1child，child误认为已核验快照不可读，fresh main实际消费blocked后停止；无checkpoint/Guide。角色baseline补充快照来源，不扩大权限 |
| 13 | 6 | 23,932 | 同次intake→main/Tool→child→main→checkpoint→Guide COMPLETE/项目bytes不变；child误解禁止再委派而blocked，main消费其实际观测后complete。通路完成，child语义未记成功；补child职责说明 |
| 14 | 3 | 14,327 | main/Tool实际观察成功且有Receipt，但main认为无写Tool不能发布report而blocked；无child/checkpoint/Guide。补冻结Driver的pending发布职责和实际path/contract，不制造新权限 |
| 15 | 6 | 24,862 | 同次32.641秒：intake6778/907；main两轮/Tool→child1464/341 complete→fresh main4188/645 complete→checkpoint→Guide2738/202 COMPLETE、项目不变。全部本例启用桥实际成立 |

上述15次共41个 HTTP entries：intake15、main18（包含回接和Tool后续轮次）、child4、Guide4。累计 **246,860 known / held0**，包含原历史55,614；不从10,000,000上限重新起算，剩余9,753,140。内部 workflow 的工程预占与实际 API settlement 分开保存，不把内部预占当成额外已消费 tokens，也不把 unknown 清零。

Attempt9 和10是两份独立原件，不能拼接成一次五调用全通过。每个请求均重新核实际时间、source/config/grant 和官方闲时；无自动付费重试或 fallback。

## 原件与冷检范围

Root 已在新进程核15份新增 closed books、全部原件集合/哈希/settlement，及原17账的2082项引用；17份实际 generic Receipt 与其 Bundle 冷验证通过。Attempt12/13/14/15四份实际 Tool 证明单独冷检查：原始结果 bytes/hash 等于下一实际请求 Tool 消息，Trace validator PASS。Attempt12结果文件SHA256 `006b5d55976243650d2307295cf46e94cc9aeca62ff7f9f0cf116a49908f1f94`，绝对路径251字符。没有将该检查说成原17次运行的全部语义重放或科学复核。失败、截断、unknown、未开始与原始错误状态保持不变。

原始 request/response/Tool/usage 与冻结 source 在调用方的 ignored `.rwb/api-chain/attempts/<namespace>`、`.rwb/api-chain/prepared/<namespace>`；不包含 Key 或认证头。该目录不随 PR 发布，本文、[ROOT_REPORT](ROOT_REPORT.md) 和 [COVERAGE](COVERAGE.md) 是主要评审入口。Root 摘录归档为 `.rwb/entry-archive/actual-facts-15.json`，用于核对本文，不要求评审人逐份阅读 JSON。

当前关键 namespace：Attempt9 `chain-cb22901c-ad73-469c-accb-9d6fb876a080`；10 `chain-e4b59337-20bd-4973-94c8-0c384ef48895`；11 `chain-4927c3a2-28d9-4553-bfaa-9653d4eb1073`。Attempt9 checkpoint SHA256 为 `430516528ef3b8ae57137bfa38461b4573a0418fdd079acfcc8ce730d5e390cd`；10 为 `503fcbb190780f1777ccdb8fd9228abeae350e5b1b7ba427e61b5a347b1eaf64`。

Attempt15 namespace 为 `chain-390138a6-3dd8-4fa5-9615-d8986b6b5345`，checkpoint SHA256 为 `dc68dd094a574584a474de4767014ba3d516ffdfe9d15eb933af5ae082fea698`。它是本轮同次全例成功依据，不拼接先前 Attempt。

## 尚未证明什么

非空 required Skill loader、正式 Skill evaluation/admission、黄毅具名 live 接受、正式 Source 资格、四臂/64-slot/Pilot、任意原生平台、真实复杂研究和科学正确性均未完成。材料接续与从零建基座共用入口契约；本轮没有测试真实杂乱文件夹，也不改变后续研究流程。M12/自动恢复与 GUI 只交付规划，M5-008 不因这些接口测试被标 DONE。
