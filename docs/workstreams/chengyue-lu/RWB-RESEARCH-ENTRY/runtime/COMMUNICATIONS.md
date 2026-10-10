# ENTRY-B 可见通信与验证记录

本分支基线 `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。Profile：bounded FrozenView-to-Session Driver and closeout worker；required-Skills=[]。本组不是唯一参与者，仅写 `src/research_workbench/entry/driver.py`、`tests/test_entry_driver.py` 和本runtime两文档；未撤销其他编辑。以下保留可见消息，不记录隐藏推理或秘密。消息中的机器路径仅为收到的原文记录；操作入口和交付引用使用仓库相对路径。

## 收到 Root 的任务（原文）

> 开始有界实现子Task ENTRY-B；用户已明确批准隔离分支实现/测试/推送。你不是唯一参与者，不撤销其他人编辑。cwd .，branch codex/research-entry-integration/base d3c4d23。先读当前AGENTS/README/primary own-row、docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/{README,TASK_PACKET,RISK_LEDGER}。Agent Profile=bounded FrozenView-to-Session Driver and closeout worker；required-Skills=[]；输入读域src/execution、adapters/models、Trace与直接Schema/closeout tests、control/Task/Profile调用接口。独占新src/research_workbench/entry/driver.py，tests/test_entry_driver.py及workstream/runtime/COMMUNICATIONS.md、HANDOFF.md，不改entry/__init__/CLI或旧Host/Session/Schema/Registry。实现选定通用 no-Skill FrozenExecutionDriver：从validated View/Bundle exact Task/Profile/声明输入生成真实Role ModelRequest，现有Session执行，记录实际Provider/request/response/Tool/usage/失败，返回真实ExecutionDriverResult；使用同一recorder→现有Host→Core closeout/replay保存桥，不能照selected binding自证actual、不伪造qualification/source或completed Task。Provider/Session/实际binding observer/clock由caller显式注入，actual drift失败、unknown保留、不fallback。Role helper另一代理负责roles.py，拟接口 build_role_request(root, *,role,task,profile,model,input_refs=(),tools=(),max_output_tokens=...)；可先实现自己的接口对接后调整，不复制baseline。Host dispatch预算/时间/权限交集明确，所有actual读/输出在scope且hash，output参数可变。提供execute_role_slice(root, bundle_ref, view_ref, ..., driver_factory或者provider/session/observer)->refs/results的可复用入口，core receipt及独立文件verify真实执行。Existing harness_runtime是synthetic例，可窄读桥接口借法不可引evaluation dependency/guard或把fixture资格生产化。先元数据找actual existing file names（generic_closeout不是core_closeout）；测试优先现有fixtures只作明确offline输入并注入ScriptedProvider，不读真实source/raw logs。预算30分钟最多6轮，可跑所属离线 tests，Root给Python；0API/生产Tool/Key/账/Attempt/安装/再委派/commit/push，必要核心ownership变更候选停该切片。尽快发具体public接口给Root编排；最终persist handoff、hash/验证和限制后停止。

## 发给 Root：public 接口

> ENTRY-B public接口候选：SessionExecutionDriver(root, *, view, role, provider, binding_observer, recorder, output_path, output_contract, input_refs=(), limits=None, session_clock=..., cancel_requested=None, request_builder=None)；binding_observer(provider)->实际五组件Binding Mapping，必须caller显式提供并从能力/response独立校核provider/model，绝不复制selected binding。execute_role_slice(root, *, bundle_ref:CloseoutPin, view_ref:CloseoutPin, role, provider, binding_observer, output_dir, output_path, output_contract, attempt_id, report_id, receipt_id, accountable_owner, input_refs=(), limits=None, host_clock=None, session_clock=..., cancel_requested=None, schema_root=None)->RoleSliceResult（Host/Trace/check/receipt pins及session，receipt可因capture gap为None）。本切片选定procedure no-Skill/零Tool；selected Skill/direct-tool先拒绝，避免无授权Tool。真实Usage unknown保留于session/输出及Trace，并使Host fact-gap失败、不能伪造完整receipt。Role helper若返回wrapper请尽快告知。接口只复用既有Host/generic_closeout，无evaluation依赖。

## 收到 Root：接口确认

> 接口批准按所述实施，首轮procedure/no-Skill/零Tool即可，direct-tool/Skill阻断在完成矩阵明确。Root将caller动态委派放Host之外，executor每次接有界Task/role/input refs并通过binding factory生成/冻结；保留slice完成与整体处置分离。Role helper计划直接返回ModelRequest；同名build_role_request另组实施。请告诉Rootoutput_contract允许的schema/ref形式，确保main输出JSONdecision/childTasks/summary/limitations/next_actions能作真实delegation而非Root固定N。Driver不要擅自加载Rootworkflow模块。测试解释unknown须facts-gap/receipt none既定；代码中observer要config/source真实观测，不靠selected。Python新venv正在创建，完成后给路径。

## 发给 Root：实际 Supply 与输出契约

> output_contract使用既有View.required_outputs的contract字符串（Host/Schema只是contract identity，不限定JSONshape/ref类型），output_path实际保存provider response的text；可让角色输出JSONdecision/childTasks/summary/limitations/next_actions作为某显式contract，main caller另解析/校验其JSON。首轮no-Skill零Tool不改workflow模块。为避免actual Supply也自证，observer具体调整返回ObservedExecutionBinding(binding=<五组件真实观测>, supply_report_ref=<实际runtime注册/源闭包绑定的Supply ref>)；可兼容Mapping含五组件+selected_supply_report_ref，缺实际Supply观测失败。caller不能从View复制此观测，离线tests明确独立script metadata，生产交付不附任何live/新qualification。remote请求预检network/egress，默认request_payloads=('project-context',)，本地Provider不产生remote egress。

## 收到 Root：Python 与编排接口

> Python ./.rwb/entry-venv/Scripts/python.exe（3.11，editable .[test]）已可用，不reinstall。Role helper当前签名直接ModelRequest，增加 instructions=None/context=None/data_policy=None；Driver.request_builder可由Root闭包使用context actualchildresults+JSON控制instructions。另observer object已同意，实际Supply source不能取View。Root准备FrozenRoleExecutor adapter：binding_factory(invocation)->FrozenRoleBinding(provider, observer, bundle/view pins等)，你的RoleSliceResult请保留session/refs供总预算/实际结果抽取。Core失败/exception保留新目录，不能宣称硬取消。

## 发给 Root：实现进度

> Driver与7个离线测试已写，正在所属suite验证。execute_role_slice和ObservedExecutionBinding按已确认接口，真实Role helper直接对接（当前可见roles.py）。provider/server Tool零、Session limits<=View交集、remote egress预检、actualObserver每次dispatch/response重观测、unknown保留session且facts-gap/receipt None。DataPolicy合并保留builder更强控制。注意output_contract只是既有Host artifact contract identity；若caller要JSONdecision语法/业务校验，应自行用专门contract与parser，不把本桥hash/check当语义验证。输出文件和archive paths均先验证effective allowed_roots，exclusive创建。

## 发给 Root：首轮结果与 Session 注入限定

> ENTRY-B第一版7/7 PASS（45.759s），已补dispatch瞬时config drift与实际usage超Host ceiling两例，9测试重跑中。当前Session复用IsolatedApiSessionRunner，由显式Provider创建独立Registry并注入session_clock；未接受可替换任意runner，避免runner偷偷换Provider后observer盯错对象。若编排需要显式Session工厂，我可加session_runner_factory(registry,*,clock)->IsolatedApiSessionRunner，约束使用传入Registry和零Tools，Root显式传默认现有Session类；这属于可选应用接点，无旧Session变更。

## 实際读域与关键事件

已读当前AGENTS/README及本workstream README/TASK_PACKET/RISK_LEDGER；primary PROJECT_MEMORY按M5/M12/ENTRY导航定位，无本Task own-row匹配，Root统一连续性写入。读docs/README/DEVELOPMENT、ARCHITECTURE初始架构/对象/执行映射、STATUS相关实现与03/09相关模块片段。源码定向读 `execution/host.py`、`generic_closeout.py`、`runtime_bundle.py`、`execution_view.py`、`runner.py`、`adapters/models/session.py`/`port.py`/exports、Trace recorder与直接validator片段。直接tests/fixture：execution_fixtures、test_generic_execution_closeout、test_api_session_runner；Task例仅现有fixture直接依赖的no-Skill Task。直接Schema：task-packet、deterministic-check-report。Root明确给Role helper后仅读其public接口/直接校验段；没有改另组文件。

metadata发现 `generic_closeout.py` 后使用其真正接口。窄读 `evaluation/harness_runtime.py` 的既有 `execute_slice`/`replay_slice` 桥，未引其import、qualification、fixture guard或evaluation依赖。第一次合并读取输出曾工具截断，后续对必要接口定向重读；两个猜测路径 `control/models.py`、`schemas/task.schema.json` 不存在，立即metadata定位真实文件，未将错误当源码事实。两次suite均用Root给的venv；没有reinstall。`git status`仅核本组路径，未stage/commit/push。

测试只创建TemporaryDirectory下的离线工件及注入ScriptedRoleProvider，包含明确人工script metadata；无网络/API/生产Tool/Key/真实账/生产Attempt。原Host/Session/Schema/Registry/CLI未改。测试及最终hash结果见 [HANDOFF](HANDOFF.md)。

## 最终验证事件

Root提供的Python3.11 editable test环境，调用 `python -m unittest tests.test_entry_driver -v`；第一轮7tests/45.759s/OK，最终9tests/59.992s/OK。九个test逐项输出均ok：actual_provider_exception_retains_attempted_request_and_unknown、actual_usage_above_host_intersection_fails_after_real_call、cancel_before_dispatch_retains_failed_slice_without_fake_call、contemporaneous_observer_drift_blocks_before_actual_send、observer_binding_or_supply_drift_blocks_before_provider、real_role_request_port_trace_host_closeout_and_independent_replay、response_drift_is_retained_failed_and_never_falls_back、unknown_output_usage_is_not_promoted_to_complete_receipt、write_scope_remote_policy_and_limits_fail_before_provider。exit0，无失败重跑或额外产品matrix。测试中的Scope/usage/drift/cancel反例都是offline注入。

`python -m py_compile src/research_workbench/entry/driver.py tests/test_entry_driver.py` exit0。两交付文档四处相对Markdown链接全部存在。限定 `git diff --check` exit0，但本组文件目前untracked，因此只作为局部Git状态观察，不夸大成完整已stage差异验证。最终四文件SHA由Compact给Root持久化；本组没有stage/commit/push。
