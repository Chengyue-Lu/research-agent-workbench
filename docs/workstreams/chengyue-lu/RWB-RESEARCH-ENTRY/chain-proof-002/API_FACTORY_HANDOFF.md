# CHAIN-API-PREP-005 Compact Handoff

2026-10-07；bounded implementation worker；required-Skills=[]。仅静态开发候选，未执行产品、Provider、Tool、Key、账或 fixture 测试。控制面由路诚钺负责，API具名审查由黄毅负责；本交付不表示正式 source/live/Human/Skill 接受。

输入与写域由 [API Factory Packet](API_FACTORY_TASK_PACKET.md) 冻结。仅新增 [runtime/api_factory.py](runtime/api_factory.py) 与本文件、[通信](API_FACTORY_COMMUNICATIONS.md)，不改 src/tests/Schema/Registry/config 或其他代理内容。

## 最小 public 接口

```python
ApiRoleBindingFactory(
    root, code_root, *, provider, observed_binding,
    task_pin, profile_pin, method_pin, requirement_pin,
    supplies, conformance_refs, evidence_check,
    data_policy_pin, host_policy_pin, timestamp,
    output_directory, output_contract,
    action_ref=None, planning_action_id=None,
    archive_scope=None, tools=(), tool_refs=None, session_limits=None,
    host_clock=None, session_clock=None, schema_root=None,
)
factory(invocation: RoleInvocation) -> FrozenRoleBinding
```

pins 可为带 path/sha256 的 Mapping 或现有 pin 对象，均指向 project `root` 内 exact 文件；`code_root` 只定位默认既有 Schema，不能据目录名认证 source。`observed_binding(provider)` 必须由 Root 独立返回五组件 `ObservedExecutionBinding`，含实际 Supply ref，不得从 View 倒抄；freeze 时与 Provider capabilities 身份比较，实际 Driver 在 use boundary 再调用同一 observer。`timestamp()` 返回实际 timezone-aware ISO 字符串，无虚构时间默认值。`evidence_check` 必须由 Root 显式提供，不存在内置 pass 或接受决定。

`action_ref` / `planning_action_id` 必须恰有一个，实际 Method 中唯一匹配且包含本 Requirement。**当前 Runtime consumer 仅匹配 action_ref**：Root 核 `runtime_bundle.py:455–475`，planning selector 因该现有缺口不能成为可执行通过；本 helper 让现有 freeze 拒绝并留下诊断，不改核心。Root 本实际 Attempt 使用独立候选 `ENTRY-A1@0.1.0` 的真实文件/hash与实际 intake Method；该候选不被此 helper 宣称 canonical/accepted，也不写 Registry。

## 逐 Task 实际消费

初始/回收 main 必须与 call_intake 实际 `task_pin` 文档完全一致，直接消费原 Method/Requirement pins，不从模板重建或改写 root 控制草稿。已知 Task identity 的内容变化、pin drift 或 Profile identity/权限越界阻断。

新 child 从 workflow 已实际调用的上一层 parent Method 派生，仅产生新 Method identity、绑定实际 child Task SHA/revision并追加复用限制；机制、义务、Mode、Gate 与 capability demand 保持。child 若改变 capability 集合，则需要实际新 Method，本片段保持阻断。depth/ordinal 来自实际 RoleInvocation，数量/总预算不写死，仍由现有 Workflow 管理。

每调用独占新 role 目录，调用现有 `freeze_capability_selection(...qualification="runtime-execution")` 比较实际 Supply并经 Root verifier核实际typed evidence，随后按真实 selected Supply构造 manifest/精确imports，调用 `freeze_execution_inputs` 生成 Bundle/View。支持多候选比较，Bundle只导入最终 selected Supply及其真实 conformance，保留 Task完整需求、单 Action/Requirement slice 与 task_completion=false；无 ranking、fallback 或 Source/Provider资格生成。

FACTORY.json 与 `factory.records` 提供实际 role/ordinal/depth、Task/Method/parent Method/Requirement refs、选定标识、真实 timestamp、archive scope 与 Bundle/View pins。实际 Host输出/Trace/Receipt尚未运行，由返回的 FrozenRoleBinding交现有 executor消费。失败可留下部分候选目录、selection或blocked summary，不作为成功 binding，也不覆盖原目录。

`output_directory` 必须是实际 Task授权目录；若child范围更窄，默认使用其首个 write_scope anchor。可显式提供 `archive_scope(invocation)`，但必须在该Task范围与allowed_roots内。Profile校验和既有View再交叉约束；不扩大Task/Profile权限。当前零Tool；可传显式readonly ClientTools、component mapping与Session limits，由现有Driver执行完整scope/identity/budget检查，factory不调用Tool。Guide不走此factory，维持专用独立只读接口。

## Root输入边界与待验证

原 contract-check Requirement与fixture Supply禁止project-context外传，不能被factory放宽。Root已确认并准备隔离 `entry-api-bridge` Requirement，显式allowlisted project-context仅本Attempt public synthetic、network search-and-fetch；实际Method/Task须来自同次成功intake产物。Driver固定默认payload标签project-context，所有实际需求/Supply/policy允许列表必须一致，不靠改标签绕过。fixture scope、deterministic-fixture证据和Skill Supply由本helper明确拒绝。

Root计划在真实intake完整响应、已知usage和compiler成功之后形成typed候选roundtrip证据；factory只消费其actual pins及独立verifier。local procedure evidence仅说明本地候选roundtrip范围，不表示供应商live/source接受，原source qualification=false不被修改。

已做 `ast.parse` 与内存 `compile(..., "exec")`，未执行code object、import产品或运行prepare/factory；零尾随空白。Root下一步以当前真实inputs、conformance、观察、时间/预算/出站guard执行正反验证，尤其检查所有结果与sameAttempt intake产物实际相同、parent/child scope、选定Supply/observer drift、typed evidence与规划Action缺口。静态编译不能证明freeze/Runtime/Host可运行。
