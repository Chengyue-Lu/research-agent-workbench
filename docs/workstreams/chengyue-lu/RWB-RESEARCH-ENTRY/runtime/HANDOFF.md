# ENTRY-B Compact Handoff

基线：develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`；候选分支 `codex/research-entry-integration`。人类runtime/Provider维护者黄毅；语义/权限/Trace维护者路诚钺。Agent交付不是具名review或接受。

## 已实现

- [driver.py](../../../../../src/research_workbench/entry/driver.py)：可选procedure/no-Skill、零Tool的 `SessionExecutionDriver`，使用真实 `build_role_request`，读取Bundle/View中exact Task/Profile及声明输入，通过既有隔离Session调用显式Provider，再返回实际 `ExecutionDriverResult`。
- `ObservedExecutionBinding(binding, supply_report_ref)` 由caller从实际config/source/runtime注册观测。五组件Binding与实际Supply不得从selected View复制；Provider capabilities及response provider/model分别校核，dispatch/response再观测变化。初始不匹配由Host preflight零调用阻断；调用中漂移失败，保留实际响应、未知项，禁止fallback。
- `execute_role_slice` 保留同一recorder的实际Provider request/response、Usage与失败、actual execution fact，再运行既有Host、保存Host/Trace/真实deterministic file check及Core receipt，最后由独立文件validator冷读重建receipt。receipt只声明action/capability slice；Task/Claim/Human/Topic5边界保持false。
- 输出路径和archive路径显式可变，必须位于View最严allowed_roots且fresh/exclusive；拒绝保留archive文件冲突。声明输入必须exact Task refs+hash；Session limits不超过View预算；远端请求预检network/data-egress，保留Role builder更强DataPolicy。取消合作式；Host观察实际wall time和actual output usage，超额结果失败。
- `RoleSliceResult` 返回Host、pins、Session及closeout_error。provider error/usage unavailable/capture gap保留事实与新目录，不发布完整receipt。Host整数output_tokens字段仅记已观察subtotal；有未知输出usage时facts_complete=false+显式gap，真实Session usage保持None，不能把subtotal当完整零。

## Public 接点

`execute_role_slice(root, *, bundle_ref:CloseoutPin, view_ref:CloseoutPin, role, provider, binding_observer, output_dir, output_path, output_contract, attempt_id, report_id, receipt_id, accountable_owner, input_refs=(), limits=None, host_clock=None, session_clock=..., cancel_requested=None, schema_root=None, request_builder=None, request_payloads=('project-context',), dispatch_guard=None)`。

`binding_observer(provider)` 返回 `ObservedExecutionBinding`；也支持五组件加 `selected_supply_report_ref` 的Mapping。`request_builder` 可由Root闭包绑定明确instructions/context，再调用Role helper。Session使用显式Provider绑定的独立Registry及既有IsolatedApiSessionRunner；没有允许任意runner静默换Provider。`dispatch_guard`只进一步收窄既有Host。

`output_contract` 是既有Host required_outputs的contract字符串；response文本真实保存并pin，core file checker不证明文本满足额外JSON业务/科学语义。Root caller使用专门contract及parser消费 `decision/childTasks/summary/limitations/next_actions`；本组不加载workflow或固定child数量。

## 验证

所属 [test_entry_driver.py](../../../../../tests/test_entry_driver.py) 使用既有Core fixtures，仅为显式离线输入；人工ScriptedRoleProvider真正被Session调用。首轮 `python -m unittest tests.test_entry_driver -v`：7/7 PASS、45.759s；最终9/9 PASS、59.992s。覆盖真实Role输入/实际请求与响应/Usage/Trace/Host/Core receipt独立重放及artifact篡改、初始Binding/Supply阻断、dispatch前config变动、response漂移、unknown、Provider异常、合作取消、权限/远端policy/预算及actual超额。`python -m py_compile src/research_workbench/entry/driver.py tests/test_entry_driver.py` PASS；4处相对Markdown链接均存在。没有安装/live/CI证据借用。

## 限制与下一动作

首轮只支持procedure/no-Skill/零Tool；direct-tool、Skill、原生平台launch和硬中断未实现。Provider模型请求/响应与本地usage未知诚实保留；未知cost/input不被本桥认作完整Run账，Root caller必须检查其总预算。没有跨child调度、Run统一账、MainState提交、Guide科研Trace豁免或Topic5恢复；这些由其他已分配caller切片处理。无新core对象/Schema/Registry/旧Host/旧Session变更，0API/生产Tool/Key/真实账/生产Attempt/安装/再委派/commit/push。

Root集成driver及所属测试，更新COMPLETION/风险与PROJECT_MEMORY唯一own-row，执行必要独立review/集成checks；需真实API或具名ownership接受另走原规则。通信见 [COMMUNICATIONS](COMMUNICATIONS.md)。本组hash定位由最终Compact通信记录保留，避免self-hash循环。
