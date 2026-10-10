# Planning 与正式 Handoff 桥接切片

2026-10-10；R2；M1-010 / M2-009 / M11-008；状态以 [TASKS](../../../../TASKS.md) 为准。前一切片见 [package caller](../package-caller-003/VERIFICATION.md)。本轮为 PR140 中的新实施切片，不改前一实际 Attempt 的冻结原件或来源身份。

人类本轮明确授权：“继续推进，优先补齐 planning 执行身份和正式 Handoff 消费链，再按已有授权验证剩余桥接，更新 PR140 的实现与验收记录。”该范围扩展允许修复 planning 的 Core 执行身份及 Handoff Schema/消费者；原包内调用切片的 Core 不修改限制仅适用于原切片。本轮不授权合并或发布。

## 输入、边界和输出

读取仓库入口、现行 Architecture、相关模块 02/03/05/06/08、三项 exact Task，现有 Task/Method/Runtime Bundle/View/Host/Receipt、Handoff/transfer、entry 及直接消费者/测试。来源和权限决定仍由原有控制面持有。执行身份扩展须有 candidate ADR、明确版本与兼容规则；保持旧 Action 的 exact 身份和冻结回放。不得虚构 Action、填造 Skill lock、跳过 validator 或赋予 Runtime 供给重选权。

交付：planning exact Method identity 经 factory → Bundle → View → Host → Receipt；actual child result 经正式 Handoff producer 与完整性消费者进入 fresh main；最终 Handoff 经检查进入 checkpoint 与 Human 待办。记录实际输入、输出、直接消费者、正反证据、失败及未触发场景。Compact 为默认；Task 要求 Manifest/Audit 的路径必须真实满足或阻断。结构通过不授予 Task、Claim、Skill、来源或人类接受。

## 并行写域和测试

- Planning worker Profile=bounded execution identity implementer，required Skills=[]；独占 planning 相关 execution、factory、Runtime/View/Host/Receipt Schema、对应测试及 ADR-0025。共享 catalog 修改先协调。
- Handoff worker Profile=bounded formal Handoff implementer，required Skills=[handoff-integrity]；独占 entry/handoff、workflow/state/caller、Handoff Schema/验证器及对应测试。完整性 Skill 的执行检查由本测试窗口承担。
- Reviewer Profile=targeted architecture/acceptance reviewer，required Skills=[]；只读上述接口，输出逐桥验收计划和精确风险。
- 各首轮实施预算20分钟，审查12分钟；持久化可见传递与紧凑交接。互斥写域之外先说明原因，保留其他编辑。实现/审查不运行测试、真实 API、生产 Tool，不读 Key、不建生产账、不操作 Git。

本窗口执行全部适用确定性测试、安装包外消费、独立冷回放以及必要实际 API。沿用人类既有无限 Attempt / 累计 10,000,000 token 授权；当前每 Attempt 最高6次模型调用、1024 output/call、32768 bytes/body、120秒、2个只读 Tool。北京时间18:00–09:00且每次请求 fresh 官方闲时；仅授权凭据引用，不归档 Key/认证头。输入预占、成功/失败 usage、unknown holds 和历史原件闭合均复查，无自动付费 retry/fallback。上述上限仅是当前测试配置。

## 验收与停止

先验证精确 identity、引用、hash、Schema、权限、输出与 Receipt 闭合，再执行实际 API。planning 正例和原 Action 兼容均需真实消费者；歧义、错误 identity、漂移或范围扩大必须在派发前阻断。Handoff 保留限制、冲突、未解项、Human required 与实际执行事实；Task/输入/Skill/产物替换、缺失必要转移链或消费后漂移必须拒绝。

有真实 unknown、权限/历史漂移、缺必需输入或无法克服的硬阻断时停止对应执行并保存事实；独立合法切片可以继续。更广材料、研究方法语义、合格 Skill、Guide 解释质量、真实科研净价值和 Topic 5 不从本切片自动验收。三项 Task 只有完整义务满足才可改变完成状态。
