# ENTRY-REVIEW：应用权限与生命周期有界审查

Profile：targeted application authority/lifecycle reviewer；required-Skills=[]。本轮只读本workstream Task Packet、新 `entry/workflow.py` / `state.py` / `executor.py` 与直接workflow/state tests；此前Driver/Role接口作为已读输入。只写本文件，不改已交付Driver/tests/Handoff或Root文件，不再委派。四个限定问题：跨fresh Session预算、动态child边界和结果消费、state决定/hash/权限、Executor exact Task与actual closeout。

## 当前结论

发现4项需要修复的实质缺口：3项高、1项中。前述9workflow+2state PASS不覆盖实际FrozenRoleExecutor参数/失败计数和下述Task末轮预算/state字段反例。这里只评价审查时可见源码快照，Root后续修正不被本报告自动接受。所有反例只使用TemporaryDirectory、现有ScriptedExecutor及本地Schema，0模型API/生产Tool/Key/真实账/生产Attempt；没有修改或扩大旧fixture矩阵。

### R1 高：实际 Executor 的 Session limits 构造始终失败

[executor.py](../../../../../src/research_workbench/entry/executor.py) `80–82` 使用 `ApiSessionLimits(max_turns=..., ...)`，也缺少必需的 `max_tool_result_chars`。此前已读Session公开构造参数是 `max_model_turns`、`max_tool_result_chars`。因此正确Task/Bundle/View也会在调用 `execute_role_slice` 前抛TypeError，通用编排只能转成unknown safe pause，不能执行已授权slice。

反例直接调用相同参数组合：`ApiSessionLimits(max_turns=1,max_tool_calls=0,max_parallel_tool_calls=0,max_output_tokens_per_turn=100,max_total_tokens=200,max_seconds=10)`，得到 `ApiSessionLimits.__init__() got an unexpected keyword argument 'max_turns'`。属于公开接口拼接错误，不是Provider/Key/live未授权。

必要修正：使用既有正确参数，并补零Tool路径仍要求的正 `max_tool_result_chars`。需要至少一项真实FrozenRoleExecutor→Driver离线调用证据，单测ScriptedExecutor不触及这个constructor。

### R2 高：发送后失败的请求被算为零调用，unknown hold丢失

`executor.py:103–105` 将 `session.model_turns` 当 `RoleObservation.model_calls`，并在session=None时把tokens也填0。已交付Driver实际Provider异常测试证明：请求真实进入Provider port后，Session没有收到response，`session.model_turns=0`，usage=None，而Host `actual_facts.provider_invocations=1`。

[workflow.py](../../../../../src/research_workbench/entry/workflow.py) `account:235–254` 中若 `model_calls==0` 立即return，未保留unknown reservation。因此本次虽然因status failed停止，Run报告会漏记真实发送及unknown；再作为prior_usage消费时也会被当0，不能称完整跨Session预算事实。

必要修正：RoleObservation调用数来自Host的实际Provider invocations；有实际发送但usage unavailable应保持None并hold reservation。driver-exception/fact-incomplete且无法证明零发送的情况不能以session=None补0；应返回unknown事实或抛给workflow既有unknown分支保留reservation。preflight明确0调用仍可保留0。

### R3 高：最后一轮超过Task输出/时间预算仍stage-completed

`workflow.py:265–310` 在dispatch前计算node剩余预算；`299–303`累计node output后只检查Run总calls/tokens，`308–309`只复检Run总时间。未在解析末轮complete前检查实际output超过本次cap/累计Task output，或当前node累计elapsed超过Task max_seconds。

已执行两项离线反例，均正常exit0：

1. `task().budget.max_output_tokens=10`；WorkflowBudget per-call output100、Run tokens10000；实际 `RoleObservation('completed', output(), 1, 20, 15)`。dispatch cap应10，返回 `{"status":"stage-completed","actual_output":15,"task_limit":10,"summary":"bounded output"}`。
2. `task().budget.max_seconds=10`；Run max_seconds60；clock依序 `[0,0,0,0,20]`。返回 `{"status":"stage-completed","Task_max_seconds":10,"observed_elapsed":20,"Run_max_seconds":60,"summary":"bounded output"}`。

在Frozen executor中Host已能检测单slice的冻结Task ceiling，但主Task每次新Session的本次剩余额度更窄；不能靠每次完整Task ceiling替代跨Session累计校验。必要修正：actual后立即校验本次输出cap、node累计输出、node累计时间，再允许parse_control/complete；保留实际usage和failed/paused事实，不能把超额结果删掉。原main结果消费的turn预算累计已实现，问题仅末轮实际复检。

### R4 中：state writer接受未由hash-pinned report佐证的可变Result字段

[state.py](../../../../../src/research_workbench/entry/state.py) `45–49` 只比较报告的task_id/status及两authority false；`62–86`却使用可变参数Result中的observations、limitations、held_tokens、disposition和next_actions构造state，未与已pin报告逐项对应。

已执行反例：用既有 `EntryStateTests.prepare` 得到真实workflow result，然后 `dataclasses.replace(result,next_actions=('tampered action absent from pinned report',))`；保留同一report_ref/hash、task_id/status。writer成功发布checkpoint：`next_actions=["tampered action absent from pinned report"]`，原retained report为 `["Human review."]`。没有伪造磁盘report或突破调用者write_scope，这正是对象字段与证据源分离造成的遗漏。

必要修正：从hash-pinned report读取所有被消费字段，或对Result的消费字段与report做确定性全等检查，再构造state。此项不表示writer生成了新的accepted_decisions：它目前正确只复制previous的列表；风险在新的动作、处置、限制和工件来源没有绑定同一report。

## 四个限定问题中的已有保护

- Run calls、known tokens、unknown holds集中于同一个workflow闭包；main重复fresh Session的 `node_usage` / `node_started` 按Task ID留存，prior intake usage计入全Run。没有因新Session自然重置预算。上述R2/R3是在actual消费者和postflight上的遗漏。
- `workflow.py:139–200` 对整波child验证Task Schema、无Skill、depth、write scopes、permission roots、external/network、exact path+hash input subset、question/Mode/capability及forbidden Skill、sub-budget。`323–333`先验证整个wave再调用，互斥scope和重复Task ID拒绝；`334–344`实际child控制结果进入fresh main的consume-child-results context。没有发现默许child权限扩大或Root固定N的实质缺口。input subset目前比较path+hash，未扩大可读内容；revision元数据严格性可另定，但本轮不升为新的authority发现。
- state `53–65/78/90–119` 验证previous Schema、读取machine pins、原样保留previous accepted_decisions、生成digest、caller显式write_scope、发布前重查pins、temp+fsync+os.link exclusive publish。同路径overwrite拒绝；没有宣称current-head CAS或Topic5。R4不否定这些已存在机制。
- Executor `49–68` 重读并外pin Bundle/View，比较整个冻结Task与RoleInvocation.task，不只比Task ID；错误Task会在任何Provider dispatch前失败。`99–102` completed Host无receipt时降为post-call-failed。此前Driver有observer/actual drift/gap检查及generic receipt重放。未发现可以直接把另一Task View或缺receipt的completed结果静默混成成功；R1使该真实桥尚未被现有workflow suite走通。

## 可复核源码定位

审查时五文件SHA256：

| 文件 | SHA256 |
|---|---|
| src/research_workbench/entry/workflow.py | 12f27f6ab3efb74ea53d846f35b8c21a40df97af21ae5799c57c5b68e2ff845a |
| src/research_workbench/entry/state.py | 0a43097ce1b4c1f24fc014453f36827020591a1bba5e0da062d3780670e93d79 |
| src/research_workbench/entry/executor.py | bdd1fabab2ed2be277345be23a247902cbc0a632d8bd69104553bf546894908e |
| tests/test_entry_workflow.py | 2a301c7a40a12bfd5ad242a4a9e727b3f8eb6fca56c4dfb022378f1d1ff3b029 |
| tests/test_entry_state.py | c25e4fe70cd758c29212433eaf5e0e7e0106c71437673c2959fb7e2e85119865 |

原联合read有工具截断，后续只对workflow265–382、state全文、executor65–108作有行号重读。两次反例命令直接导入允许域的tests helper，没有修改tests：第一次复现Session constructor、Task output末轮、state Result字段替换；第二次复现Task elapsed末轮并记录五文件hash。均exit0，运行本地Root给的Python环境。

## 可见通信原文

Root指派：

> 有界独立集成review ENTRY-REVIEW（10分钟/2轮）。不再修改已交付driver/tests/Handoff（Root保留hash）。Agent Profile=targeted application authority/lifecycle reviewer；required-Skills=[]；读域本workstreamTASK_PACKET与Root新src/entry/{workflow,state,executor}.py及tests/test_entry_{workflow,state}.py，你此前Driver/role接口作为已读输入。独占workstream/review/RUNTIME_REVIEW.md（记录此可见指派、发现+定位+必要性/反例），禁止其他写入/API/Tool/Key/账/再委派。只审4点：Task/Run预算是否跨freshsession不重置；动态child的inputs/scopes/permissions和results consumption；statewriter保留决定/hash/权限；FrozenRoleExecutor能否把返回View错Task/actual-closeout混过。不要重新全盘架构或扩大旧fixture矩阵。可跑Root相关测试作具体反例，但不要修改代码。给Root高/中实质缺口，没缺口如实。Root已9workflow+2state初步PASS；起初-I named discovery failed因tests不在sys.path，现用 -I -m unittest discover -s tests -t . -p ... 。Root立即修复关键项，再final验证后push PR。

发给Root（首轮）：

> ENTRY-REVIEW首轮发现可直接定位两项高缺口（未改代码）：executor.py构造ApiSessionLimits使用max_turns参数且缺max_tool_result_chars，现有Session真正参数是max_model_turns+必需max_tool_result_chars，因此FrozenRoleExecutor每次都会在实际Driver前TypeError；workflow ScriptedExecutor测试不覆盖该桥。另executor末尾RoleObservation.model_calls使用session.model_turns（收到response数）而非Host.actual_facts.provider_invocations（实际attempted request数），Provider发送后失败会session.model_turns=0+usage None，workflow.account见0直接return，造成真实调用/unknown hold被算0。建议该映射用Host实际invocations；driver-exception无完整facts时返回unknown或raise给workflow保留reservation，不得以session None填0。正在核state与跨session总Task预算，10分钟界内交报告。

发给Root（第二轮）：

> 第三项高：workflow.invoke300–310累计own_output，但仅检查Run总tokens/总calls，未检查actual result.output_tokens超过本次cap/Task剩余额度；最后一次返回complete会直接stage-completed。可用现有ScriptedExecutor：main budget.max_output_tokens=10，实际RoleObservation completed,input20/output15，WorkflowBudget percall100 => cap10但仍completed，Task预算已超。还需检查Task walltime本node（当前仅workflow totaltime），并在parse_control前校验本次/累计node预算。state中等：state.py45–49只比retained workflow.task_id/status，后续却从未比对的result.disposition/limitations/next_actions/observations构造checkpoint；dataclasses.replace(result,next_actions=...)保持reporthash，可把无原report证据的动作写入state。应完整比对消耗字段或从hashed report取权威值。

发给Root（反例）：

> 离线反例已确认：Task max_output_tokens=10、actual output15 => stage-completed；state dataclasses.replace(result,next_actions=('tampered action absent from pinned report',))仍写入checkpoint且retained report next_actions原Human review。同R3补Task walltime：Task max_seconds10、Run max_seconds60、注入实际elapsed20，workflow仍stage-completed；postcall仅检查Run总deadline，缺node自身elapsed复检。这两个Task budget反例均exit0、只TemporaryDirectory/ScriptedExecutor。不改代码，正在归档4项报告。

Root接收：

> 审核四项已接收。Root 正修 executor max_model_turns/requiredchars 和以Host实际provider_invocations+usage未知保留计数；control worker 负责workflow budget/state pinned-result一致性修复，Root另加真正FrozenRoleExecutor→Driver→Host→Workflow整链路测试。请完成有界review报告后停止；后续会给修复版本进行限定复查。

交付静态检查：本报告3处相对源码链接均存在。Root接收不等于本审查者核验修复；目前只对上表hash快照与离线反例给结论。

本轮修复由Root负责；审查交付后停止，不重写此前hash或扩大矩阵。
