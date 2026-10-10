# 候选入口：实际产物接合与 caller 责任

2026-10-08 · PR140 未合并开发候选。本文说明当前可复用 Python 接点；真实 API 成功、失败和未开始只引用 [ROOT_REPORT](ROOT_REPORT.md)，验证范围见 [COVERAGE](COVERAGE.md)。静态接口存在不构成运行通过、来源资格或人类接受。

## 从人类输入到独立 Guide

| 步骤 | 可调用入口与输入 | 返回及实际消费者 |
|---|---|---|
| intake | [call_intake](../../../../../src/research_workbench/entry/intake_call.py)：显式 intake Task/Profile、人类 Protocol/Task ceilings、获准材料、注入 Provider/model、独占 directory、IntakeCallBudget | 一次无 Tool 的独立请求；只有完整、有界输出才能编译并保存草稿，返回 IntakeCallResult 的 actual draft_refs、artifact_refs、report_ref 与 usage |
| 实际控制 pins | caller 从成功 result.draft_refs 中按实际文档种类选 Protocol/Task/Method/Requirement refs，并冷读/hash/schema 检查 | 下游使用此次实际保存的产物；不得用旧 Task/fixture 替换，unknown 保留，草稿不自动 approved |
| 逐 Task 冻结 | [ApiRoleBindingFactory](runtime/api_factory.py)：实际 pins、Profile、typed Supply/conformance、独立 observer/evidence_check、policies、显式 Action 与 output contract | 每次 RoleInvocation 独立选择/冻结，返回 FrozenRoleBinding；拒绝不同实际 Task 替换与 fixture 资格，产生 Bundle/View 及冻结记录 |
| 角色执行 | [FrozenRoleExecutor](../../../../../src/research_workbench/entry/executor.py)(root, binding_factory=factory, accountable_owner=...) | 经 [execute_role_slice](../../../../../src/research_workbench/entry/driver.py) 调 Session/Host，返回 actual usage、工件/Trace/Receipt refs；不由 executor 重选 Supply |
| main → 0..N child → main | [run_research_workflow](../../../../../src/research_workbench/entry/workflow.py)(root, directory=..., task=actual_task, executor=..., budget=..., prior_usage=(intake_result.as_role_observation(),)) | main 实际控制输出决定是否及多少子 Task；边界复检后顺序执行，fresh main 消费 actual 子状态、usage、工件和 Receipt pins；REPORT.md 为首读面 |
| checkpoint | [publish_workflow_checkpoint](../../../../../src/research_workbench/entry/state.py)(root, result=..., protocol_ref=actual_protocol_pin, checkpoint_id=..., output=..., write_scope=..., previous_state_ref=...) | 从 hash-pinned workflow report 校验全部结果字段后独占写 immutable MainState checkpoint，保留人类决定 |
| Guide | [ask_guide](../../../../../src/research_workbench/entry/guide.py)(root, providers=..., provider_name=..., question=..., main_state_ref=..., approved_refs=..., model=..., max_output_tokens=..., data_policy=...) | 独立 ModelResponse/usage；只读获准 MainState/必要 exact refs，不继承 main 历史、不追链、不执行 Tool、不写项目或自动回传 main |

`ApiRoleBindingFactory` 是本 workstream 的候选应用 helper，不是已安装的 core API，也不负责 intake 或 Guide。现有 [binding](../../../../../src/research_workbench/entry/binding.py) 的 freeze_capability_selection / freeze_execution_inputs 是它复用的选择、Bundle/View 接点。其他 native Adapter 可实现 RoleExecutor，隔离 API 不是 core 前提。

## 必须由 trusted caller 提供的边界

caller 提供人类授权、材料允许集、当前 Provider/Profile 配置及所需 remote 数据授权；认证晚解析、累计授权/用量账和 fresh dispatch 检查属于外层责任。`call_intake` 的 before_dispatch 接受当前授权检查，external_upload_authorized 不替代 DataPolicy。只在 status=success 时沿 actual draft_refs 继续；失败、截断、unknown 必须保留，不自动重试或换供给。

factory 的 observed_binding 必须观测当前真实 Provider/adapter/model/runtime/host；不得复制 selected View 来充当 actual binding。evidence_check 必须依据具体 typed conformance 与适用范围，返回 pass/fail/unknown；不是恒真 callback。当前 factory 是有界 no-Skill、单 Action/Requirement helper；child 改变 capability 需求时需要新的实际 Method，不能沿用父方法证明。使用已有消费者支持的 versioned action_ref；构造器的 planning_action_id 参数不证明下游接受该 selector，当前缺口保留。

workflow 的显式 WorkflowBudget 给出 calls、tokens、时间、max_children_per_task、max_depth、max_session_model_turns；这些是本次上限，main 不必用满。prior_usage 包含同一请求的实际 intake 消耗；Guide 单独计账。未知用量保留 reservation/held，并停止后续派发。Task 的 output/turns/elapsed 还跨 fresh sessions 复检；合作取消不承诺硬中断已发送请求。

## 可选 readonly Tool

需要 Tool 时，caller 明确提供 FrozenRoleBinding / factory 的 tools、tool_refs 和 session_limits。tools 是实际 ClientTool；tool_refs 将 Tool 名映射到该次实际组件身份；Task/Profile/Supply、允许 side effects 与 DataPolicy 必须一致。Session limits 显式限定模型轮数、Tool 次数、并行上限、结果字符数、输出/token/time，并覆盖可能的后续模型轮次预留。readonly 声明还需要可信 handler 的 exact ref/path/hash 检查；任意 callback 的声明不产生 OS 沙箱或来源认证。

当前隔离合成例可用 entry-api-bridge 读取 Task 明确允许的短材料，strict=False 不声明供应商 strict mode；闭集 arguments 检查仍保留。它不是每个任务必选 Tool，也不替换 canonical Tool 的数据外传边界。真实执行事实、结果是否进入下一模型请求、Trace/Receipt 是否完整必须分别核对；当前结果以报告为准。

模型请求中有冻结 binding 给出的 pending Driver 发布元数据时，模型返回有界报告文本，由 Driver 按原权限和 I/O 检查尝试发布；真实输出、hash 和 Receipt 才证明结果。该说明不是写权限或发布保证。当前已选 contract 有效；通用 caller 对其他 truthy 非字符串、空白或未匹配 contract 的派发前拒绝尚未全部闭合，见 [ROLE_REVIEW](ROLE_REVIEW.md)。

## checkpoint、Guide 与资格

state writer 由 caller 单独负责，output/write_scope 必须获准；checkpoint 不提供 CAS、自动恢复或 M12/Topic5 权限。Guide 只接 selected MainState 和人类批准的必要 refs，问题与回答不自动进入 main/project memory；人类显式采纳后再作为新研究输入。ask_guide 直接返回 ModelResponse，caller 须检查 finish_reason 是否 COMPLETE、实际 usage、timeout/remote 授权及只读事实；截断不能因有文本就记成功。

角色最低职责来自内置 baseline。外部 prompt 变体及 control-format、bounded-summary、faithful-writing 三个 Skill 仍是 test-candidate，未实际加载或准入；非空 required_skills 明确阻断。stage-completed、结构校验、Receipt 或 checkpoint 不授予 Task/Claim/Human/Skill/Source 接受；真实科研和 M12 仍未完成。

## 离线 CLI 与最新记录

既有 `rwb entry draft` 消费已取得的 response 编译草稿；`rwb entry guide-preview` 构造只读请求预览。两者不发送模型请求，不能替代上述实际调用链。参数说明保留在[历史使用说明](../USAGE.md)。

[API_RESULTS](API_RESULTS.md) 逐模块列出实际输入、输出与消费，[DELIVERY](DELIVERY.md) 固定最终验证范围和 source/report hashes。历史交接中的 pending 或当时 source pins 保留其时点；最新结果以这些入口为准，机器 JSON 不作为主要阅读入口。
