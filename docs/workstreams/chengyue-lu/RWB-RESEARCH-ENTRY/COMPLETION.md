# 任务名称与完成度

**历史快照：PR140 候选提交 `d630f8e174846f4932d05a7a0d69076930b53ee1`，65 项离线入口套、零付费 API/生产 Tool。** 以下正文保留当时事实和限制，不能用作最新桥接完成度。当前阅读 [ROOT_REPORT](chain-proof-002/ROOT_REPORT.md)、[COVERAGE](chain-proof-002/COVERAGE.md) 和 [USAGE](chain-proof-002/USAGE.md)；[API_RESULTS](chain-proof-002/API_RESULTS.md) 由 Root 后续交付，本文未验证其存在或内容。PR140 尚未合并，正式资格、真实科研及 M12 未完成。

2026-10-07；Audit `AUDIT-RWB-ENTRY-001`，分支 `codex/research-entry-integration`，base develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。完成度只描述本分支候选。逐项区分支持路径已实现、实际验证和仍缺桥接；不累计为系统整体百分比或 canonical M Task DONE。

## 本轮实际交付

| ID / 名称 | 本轮完成度 | 实际输入 → 输出 | 测试证据 / 尚缺 |
|---|---|---|---|
| ENTRY-01 入口与角色指令装配 | no-Skill 请求装配完成 | explicit Task/Profile/获准 pins +角色 → fresh ModelRequest，必载baseline与输入摘要hash | roles 8；真正Driver读取该请求。required Skill 实际加载仍缺，非空明确阻断 |
| ENTRY-02 需求与材料接入/控制产物 | 草稿 producer 与下游接合完成；自然语言规划器待实现 | 模型 JSON proposal +独立人类 ceilings → Protocol/Task/Method/Requirement/unknown/pins → selection/Runtime消费者 | intake 7、CLI draft及完整模块链；从零/人工接入不改研究契约。尚无模型实际需求重写质量、杂乱材料整理器或自动 Method planner |
| ENTRY-03 通用执行绑定与Driver接合 | procedure/no-Skill/零 Tool 路径完成 | exact control pins、typed Supply/可信检查、Profile/policies/binding → Resolution/Snapshot/Bundle/View → Session/Host/Trace/验证/receipt | binding 15、driver 9、executor 4及control-chain 1；选择/漂移/unknown冷复验。direct-tool、Skill、Native/live 实测待补 |
| ENTRY-04 main动态委派与执行链预算 | 可变0..N caller完成 | main真实控制输出 → child Task边界校验 → actual child输出 → fresh main消费 | workflow 13，含0/1/3、递归、整波拒绝、互斥scope、Task/Run预算、取消、失败/unknown。子Task顺序执行；当前整链Provider例为main/0 child，多API子树仍待独立冻结输入后的实测 |
| ENTRY-05 交接消费与人工续接状态 | generic结果消费及单提交者发布完成 | fixed workflow report与actual工件pins +Protocol/可选旧state → 新immutable checkpoint | state 3、joint端到端state/receipt；拒绝dataclass篡改、覆盖与hash漂移，保留人类决定。科学/Task语义完成、legacy Skill-bearing迁移、CAS及自动恢复仍缺 |
| ENTRY-06 独立只读Guide | 只读请求与注入调用完成 | 人类问题 +approved MainState/necessary refs →独立请求/返回usage | guide 3、CLI preview、整链快照；无Tool/磁盘writer/main回传。真实Provider Guide适用性/外层账与timeout由caller承担 |
| ENTRY-07 通用入口轻量验收与可读报告 | 轻量报告/CLI与接合验证完成 | 显式配置 → REPORT.md、逐角色observations、限制、下一动作、fixed refs | 最终新入口65项（含完整control-chain1项）；原消费者回归与安装证据见下表。图形UI、完整实际研究验收与净价值评价未运行 |
| PLAN-M12 M12边界与后续任务候选 | 规划输出完成 | 现有continuity/checkpoint/recovery接口 →当前人工再接入/Topic5分界、依赖、候选验收 | [PLAN](m12/PLAN.md)；静态规划，不是M12实现/READY/接受 |
| PLAN-FRONTEND 前端产品与控制入口方案 | 规划输出完成 | 当前fields/commands/interfaces →bootstrap、配置角色与GUI职责、错误/unknown、人类待办、Guide、FE-C01～06/F01～02候选 | [PLAN](frontend/PLAN.md)；静态规划，无GUI原型/实现/产品测试 |

## 测试实际测了什么、得到什么

完整模块链使用独立的 **offline injected Provider**，不是付费 API。它先编译并保存控制草稿，使用这些实际返回pins产生selection，再重绑manifest并生成Bundle/View；FrozenRoleExecutor真正调用现有Session的Provider端口，经Host产生Trace与receipt；工作流消费响应后生成checkpoint，Guide只取该快照。结果：1次Provider调用、input30/output8、known38/held0、stage-completed、receipt独立复验通过、Task/Human接受保持false。Guide在这个整链例只构造请求，没有发送。

动态委派例另测 main 选择0、1、3个子Task和递归，在同一预算中实际消费不同child结果。失败请求例真正进入Provider端口后抛错：Host attempted1、Session response0、工作流 model_calls1、held228、safe-paused，无重试。初始资格/来源/配置漂移例在发送前阻断；调用后漂移/usage unknown保留结果与缺口，不能完整收据放行。

末轮输出/时间超Task预算、篡改Result后提交state是独立review发现的实质缺口，已经修复并加入反例；原发现报告保留在[review](review/RUNTIME_REVIEW.md)，修复交付见[HANDOFF_FIX](control/HANDOFF_FIX.md)。最终复查单独记录，不改写原发现快照。

| 验证 | 当前结果 | 范围 |
|---|---|---|
| 全新增入口 suite | 65 PASS，86.855s | roles8/intake7/guide3/binding15/driver9/executor4/CLI2/workflow13/state3/control-chain1；最终源码 |
| 完整控制到执行接合 | 1 PASS（已含在65项中） | producer返回pins实际被下游消费；独立冷读receipt |
| 原消费者回归 | 53 PASS，66.655s | 原CLI、Host、generic closeout、Bundle、public documentation |
| 安装 | 候选wheel构建/干净venv安装通过；installed CLI 2 PASS/4.071s、help/resources/pip check通过 | imported module确定来自installed site-packages；resources177/schemas112/modes4/projections0，merge_eligible=false保持原样 |
| Markdown与交付pins | 见最终DELIVERY_MANIFEST | 本workstream内部链接、owned交付hash与路径 |
| 修复独立复查 | 原R1～R4闭合；workflow13/state3与最终executor4限定PASS | [FIX_VERIFICATION](review/FIX_VERIFICATION.md)；不是科学或具名R2接受 |
| 新付费API/生产Tool | 0 | 本轮未开始，没有借用历史成功或合成来源证明live |

详细命令、首次失败、交付 pins 与最终 PR/CI 定位见 [WORKLOG](WORKLOG.md)、[COMMUNICATIONS](COMMUNICATIONS.md)。执行/发布权限来自本轮人类指令；治理、owner、合并与发行的最终接受仍由具名人类和 PR 规则负责。

## 后续应优先接通的部分

1. 将自然语言intake与Method/Capability控制 producer装到同一个真实研究caller，并给每个main/child真实Task提供完整binding factory；再测同供应商独立API主子树。
2. 按研究任务的实际需求补必要Tool与Skill加载；沿现有资格/权限/receipt契约验收。新建/人工接续只影响材料与研究基座的浅层接入。
3. 用这些可读结果建设前端的配置/预检/结果/Guide切片，再安排真实工程场景。M12恢复按其独立前置条件推进。

这些剩余项不会因为本地结构测试通过而自动完成。M5-008、M12、Skill准入、科研净价值与完整系统接受均保持各自原有状态。
