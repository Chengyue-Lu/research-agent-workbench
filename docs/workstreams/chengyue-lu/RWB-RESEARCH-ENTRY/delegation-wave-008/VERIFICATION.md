# 整组委派预算：测试与结果

2026-10-10；M2-009 implementation slice / M11-008 direct consumer。后继分支来自 PR140 `766bf45`，仍为未合并候选；三项 M Task 均保持 IN_PROGRESS。

## 测试目的和输入输出

| 模块 / 接点 | 测试输入 | 要核对的实际输出与消费 |
| --- | --- | --- |
| main→整组 child 准入 | parent 无剩余 turn/output；whole calls/tokens 不足 | 第一 child 前停止，所有提议 child 为 unstarted，之前 intake/main actual/usage 保留，没有新 unknown hold |
| wave→child 首个 Session | 有多个已提出 child，Session 可有多个模型调用 | 第一个 child 不消耗后续 sibling 或 parent consumer 所需容量，配置上限与实际调用分别核验 |
| child→grandchild→child/main 消费 | 一个 child 再委派，外层还有待启动 sibling | 嵌套准入保留祖先与同级接点；正常路径实际形成并消费各级正式 Handoff，容量不足时不开始新层 |
| factory→Bundle/View→Host→Receipt→正式 Handoff | actual intake producer 的 exact Task/Method/Requirement，明确 offline Provider 与 test conformance | 包内受信工厂冻结本次产物，正常/停止结果实际形成输出与 Receipt，独立文件消费者复验；旧包反例与新来源分开 |
| dispatch→failed/unknown | 首次真实 offline Provider send 异常 | 当前实际 slice 保留 applicable fullhold，未派发的规划预留不成为 unknown，后续请求不自动重试 |
| source-only CI | 单独改变 workflow 或直接 helper | 两个新增回归进入 entry component，直接 helper 消费映射完整，缺失和删除行为保持 |

## 当前证据

旧安装包已在两个独立、完整保留的临时项目中复现：parent max_turns=1，或 whole calls=3（含一次 intake），仍实际调用 main 和 child，之后才停止。两案实际各 3 次 offline model calls（含 intake），known 114 / held 0，缺少 unstarted child 标记。原 package/module hashes、请求/输出、factory/Host/Receipt/Handoff 和 workflow 原件在私有 `entry-continuation-008` 中保存。它们是工程反例，不是付费 API 或科学资格。

新增[整组委派回归](../../../../../tests/test_entry_wave.py)24项通过；连同既有 workflow、CI组件映射、文档和公共表面检查共78项通过，无 source drift。它们验证多 turn Session、pending sibling/ancestor、取消/时限、释放 unused 容量、实际超限、unknown hold 和缺 Handoff 原件等边界。既有workflow的14项测试中，仅一项期望改变：parent只有一次turn时，现在在child前停止。

修复后的[包内桥接回归](../../../../../tests/test_entry_wave_bridge.py)源码6项全部通过，无 failure/error/skip 或 source drift。每个案例由一次实际离线 intake 生成 Task/Method/Requirement，再由受信工厂、Bundle/View、Host、Receipt 和正式 Handoff 消费。下表为本次实际结果；calls 含 intake，known/held 来自显式离线 Provider 观察，不是 API 计费或 live qualification。

| 测试场景 | 实际模块输出 | 下游消费与停止事实 |
| --- | --- | --- |
| 整组恰好满足4 calls/532 tokens | stage-completed；4 calls / known152 / held0；3份factory记录 | main→child→fresh main；新主请求收到child正式Handoff与Receipt；最终Handoff和3份Receipt由文件独立复验 |
| parent Task只剩1 turn | safe-paused；2 / 76 / 0 | 仅intake/main，child在工厂与Provider前未开始；最终停止Handoff可消费 |
| whole calls=3，或token总额531 | safe-paused；两案均2 / 76 / 0 | 首个child前整组拒绝，child未开始；先前intake/main事实保留，无新unknown hold |
| child再分派grandchild，外层还有sibling | stage-completed；7 / 266 / 0；6份factory记录 | 执行顺序main→child0→grandchild→child0消费→child1→main消费；子孙Method保留同一组限制并绑定不同Task pins，各Receipt与最终Handoff复验 |
| 嵌套整组只有6 calls | safe-paused；3 / 114 / 0 | intake/main/child0已实际执行，grandchild与外层sibling均未开始；保留已发生结果并形成可消费停止Handoff |
| 实际child Provider发送异常 | safe-paused；3 / 76 / 228 | 只保留当前实际失败slice的unknown fullhold；两个后续sibling未开始，没有父消费或自动重试；规划预留未计成unknown |

安装包的同6项独立进程消费全部通过，无failure/error/skip或source drift。修正后wheel SHA256为 `08e808d26485128eaef16bfedcbffd2093d36c2fd252f99707e2cab4febb4b1e`；CPython3.11.16，隔离模式，15个entry/Session模块和Runtime manifest与所测源码字节一致，未升级依赖。本轮共84个不同本地case通过（78基础回归与6个修后源码桥接）；安装包同6项和文档复测不重复累计。实际所测源码快照已保留；Git可按仓库规则规范换行，未从相同语义推定新的binary/live资格。

## 首轮问题与修正

第一轮在正常包构建前缺少生成的runtime pin，另有一个不存在的测试模块名；完成标准构建并改用真实测试入口后，78项基础回归通过。首次6项安装包消费者有1个failure/5个error（含两个subcase），其中一项通过；首轮广泛source run已在明确失败后终止，仅保留部分log，不算通过。

最终Handoff生产者会添加workflow report引用，新测试期望最初漏了这一项，现补齐该exact pin并保持生产校验。嵌套案例还暴露真实工厂缺口：派生Method重复追加同一条限制，违反既有uniqueItems；现仅对限制有序去重，保留原说明、其他限制、Schema和Task绑定。修后源码实际通过孙级冻结、执行和父消费。首次新venv的ensurepip失败原件也保留，较短隔离路径成功安装同一修正wheel；不据此宣称已确定环境故障原因。

私有原始log、旧包两个完整反例、首次嵌套失败项目、source/wheel origins、精确源码快照、静态复核与最终结果索引保留在本切片archive；公开评审以本页的模块、输入、输出和源码回归为入口。本轮没有付费API、新生产Attempt、凭据或账本修改，不重新累计或接受旧来源。

## 验收边界与下一步

本轮只闭合已提出的委派及父结果消费预算接点，不证明所有未来工作必能完成，也不预占全部 Task maximum 或预测后续研究 DAG。没有改变 Core Schema、Supply selection、Human boundary 或 Skill admission；正式 qualified Skill loader、材料接入和 Source/Evidence/Claim/Method Trace 的实际消费者仍按相应 Task 单独推进。无 Source/Human/Skill/科学接受或 M Task DONE。

下一切片优先补 M1-010 的材料 bytes、admission sidecar 与必要派生读取的 exact grants，使实际 intake 和冻结执行消费同一获准材料；Source admission 不等于来源科学可信。M4-006 实际 executable/cwd/dependency/Tool 环境观察可随后独立实施；M6-011 的能力/项目/Task/剩余预算交集按共享执行接口串行接合。
