# PR140 审查修复验收

2026-10-10；M1-010 / M2-009 / M11-008；PR140 未合并候选。审查来源为 `e938dfab320124f56bd5fc9ae047bbb9eab168f6`，base 为 develop `67a7c5f6a0c3495f1ad583864d87b25f5bf892e2`。本轮只修复四条具体现象，Task 定义、依赖和状态保持。

## 每条评论对应的模块与结果

| 评论 / 模块 | 实际测试输入与旧结果 | 修复后的行为与消费者 |
| --- | --- | --- |
| [4237860714](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140#discussion_r4237860714)：intake 人类预算 | 人类 Task 输出上限 128，模型省略该字段；旧安装包的 actual caller 请求 512 并发布正式 Handoff | 编译器要求人类提供的每个 ceiling 保留且等于或低于原值，覆盖 Task 预算、完整 child sub-budget、关闭 delegation 时的预算。省略被拒绝，保留已发生 intake 响应/usage，不发布控制草稿或角色派发；合法保留/收窄仍走 caller→factory→Host/Receipt→formal Handoff |
| [4237860716](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140#discussion_r4237860716)：intake Skill/Handoff 条件及 workflow preflight | 模型删除必需 Skill，或省略要求 Manifest/semantic review 的 Handoff policy；旧包各实际调用角色 1 次并发布 compact Handoff | 必需 Skill 不可移除或擅自增加；显式 policy 不可省略，manifest/review/sample 条件按有效默认值保持或加强。完整保留但当前未支持的 Skill/H2 路径，在 factory 冻结和 workflow 目录创建前停止，角色调用 0；不会把结构草稿当执行准入 |
| [4237860718](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140#discussion_r4237860718)：workflow→executor→Host/Driver→Session | 原 deadline 为 t120，factory 在 t121 完成；旧安装包仍实际派发角色 1 次，之后才 safe-paused | 同一可信 monotonic clock 和 absolute deadline 从准备阶段传到底层，factory、Bundle/View、Host、请求构建、durable intent capture、最后 guard/validation 耗时后均不得晚派发。Runner 在真实 generate/handler 紧邻边界记录 per-run actual facts，Driver 使用该事实；意图记录和准入不等于实际调用 |
| [4237860723](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140#discussion_r4237860723)：component CI | 只改 entry 源码时，旧规则将其视为未知，退回 6 个 runtime_cli 测试，未选择 entry | 新增 literal entry 路径归属，单独修改 intake/executor/driver/workflow/caller/init 的实际 planner 均选择全部 18 个 entry 模块及现有 smoke，无 unknown。两份 entry support 选择准确直接消费者；缺 mapped test 仍显式报 unknown，不掩盖缺失 |

“旧结果”由未更换的旧安装包离线复现，保留 package/module hashes、观测及原 log；不是对不可获得的评审者私有原件作独立证明。所有离线 Providers 和 Tool handlers 明确标识测试来源，没有 Key 或付费 API。被拒绝的 intake 仍有一次实际离线模型响应；“角色 0 次”不抹除该事实。

## 正常链与停止事实

预算正常例使用真实 `call_intake`、`ApiRoleBindingFactory`、`FrozenRoleExecutor`、Bundle/View/Host、Receipt 与正式 compact-Handoff 消费；检查冻结 Task 和 wire 输出上限。deadline 正常例检查子结果消费、只读 Tool、Receipt 独立冻结链复验，以及 clock 域一致。适用的失败例检查首次真实发送异常、已知 usage、unknown fullhold、零重试及未派发操作。

当前不支持的必需 Skill/H2 由现有 caller API 抛 `ValueError`：错误代码为 `HANDOFF-SKILL-LOADING-UNSUPPORTED` 或 `HANDOFF-TRANSFER-AUDIT-REQUIRED`，没有伪造 WorkflowResult。当前 compact 路径限制在执行前核验；完整 required-Skill 和 H2 执行支持仍属于后续义务。

首轮 119 个 case 无 failure/error，Windows 跳过 1 个现有 POSIX venv symlink case。随后静态复核指出新增 Runner 的 guard 自身耗时和 conformance 最后 validation 耗时仍可能晚派发；首轮来源、结果和初版 wheel 保留。补修在最后耗时操作之后再核 deadline，同时把 actual 计数从 admission callback 移到真实派发边界；新增慢 guard/validation 的正常与超时反例、per-run facts 独立性、真正发送失败用量例。最终来源及运行结果另列，不借首轮绿色接受补修代码。

## 最终本地验收

| 验收层 | 已执行结果 |
| --- | --- |
| entry 全部 18 模块及直接 Session、文档/公开表面、治理消费者 | 333 个不同 case，首轮 1 failure / 0 errors；全部 26 个新增预算/条件/deadline 回归通过。唯一失败是旧 workflow 用例按第五次 clock 读取模拟 t70；消除冗余读取后它实际未推进时间，生产代码的调用后 deadline 核验仍在 |
| workflow 与最终 CI、文档/公开消费者复测 | 68 个 case 无 failure/error，1 个现有 POSIX symlink case 在 Windows 跳过。仅将上述测试的同一 clock 在真实执行返回后推进到 t70，保留 safe-paused 并加强 actual1/known35/held0、response 和停止事件；整个 workflow 模块通过，生产代码未为此改动 |
| 去重后的当前本地范围 | 共 370 个不同 case，最终 369 通过、1 平台跳过，无未解决 failure/error。首败和复测分开保存；未再重复执行全部已通过的用例，产品源码与 333-case 来源一致，单个模拟时钟测试及 CI 最终变化另有复测 |
| 新 wheel 独立安装消费 | CPython 3.11.16，`-I -B`；6 个正常/反例方法全部通过。实际安装包执行预算省略拒绝、合法保留/收窄的 Host/Receipt/正式 Handoff、H2 前置停止、factory 超时零派发、正常 clock 以及真实发送异常的 unknown fullhold/无重试。15 个 entry/Session 模块与 source hash 相同，包来源不被源码 shadow |
| 实际 CI planner 的单路径选择 | 6 个 entry 源码路径各选择 18 个模块和现有 smoke；2 份 support 及 7 份 `test_*.py` helper 各选择显式直接消费者。direct-test 分支同时保留自身和政策映射，旧 4 条已声明映射、删除 owner 与 missing-consumer 反例通过；unknown/install/smoke 行为保持 |

wheel SHA256 为 `07e540a68cb076b3ac75bf5cd75924c74dbae4c608d6c2775da81e5037c142ec`；source/installed Runtime manifest 均为 `735e136de0c43f402de7462a7ff47f71c8b014c352d2ab6b9494f4139a79f5ca`。Core MainState Schema hash 保持 `c05d31a93f46b16ca81632b97130ffddd7effc85ae8139aa35d6c0eb76dd9fa4`；本轮未改 Schema、Task 定义/依赖/状态或已 DONE 行。

独立窄静态复核确认最终 callback/validation 之后的 deadline 与实际计数顺序无遗留必改项；该复核未运行模型或测试，不作为 Human 接受。文档、R2 本地预检及新 HEAD hosted 结果分别保留原始输出；远端执行结果以该 HEAD 的 GitHub Checks 为准。

## 验收边界

本轮没有付费请求、自动 retry/fallback、merge/release 或任何接受代签。此前 [stage 实际 API 与累计账](../stage-evidence-006/VERIFICATION.md)仍按原代码来源解释：known 462,388 / held 0，本轮不新增。修复后的离线结构与安装消费不重新签发 Source/Skill/live conformance 资格，也不完成三项 M Task 的全部科研及工程义务。

范围见 [Task Packet](TASK_PACKET.md)，实施导航见 [README](README.md)。原评审及每个可见协作传递、首轮和最终来源、独立窄静态复核、确定性 run logs、wheel/安装来源和发布证据在私有 `pr140-review-007` 留存；可读结果以本页为入口。
