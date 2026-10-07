# 通用入口：使用与接合范围

本分支增加可选的应用调用层，复用既有文件契约与执行内核。接口参数决定预算、委派数量上限、深度、输入和输出位置；main 的实际模型输出决定是否委派及具体子 Task。当前按顺序执行子 Task，再向新的 main 请求传入实际结果。没有固定角色编制，也没有常驻调度服务。

## 人类输入到执行结果

| 环节 | 当前入口 | 实际输出与下游 |
|---|---|---|
| 人类需求与获准材料 | `roles.build_role_request(role='intake', …)` | 必载内部输出规范与 exact 输入快照进入 ModelRequest；模型调用由显式 Provider 适配器负责 |
| 模型控制草稿 | `intake.compile_control_draft`、`persist_control_draft` | Protocol、Task、可选 Method/Requirement、unknown 和实际文件 pins；独立的人类 ceilings 限制扩权 |
| 需求与供给资格 | `binding.freeze_capability_selection` | 逐候选检查、Resolution、唯一满足时 Snapshot；gap/ambiguous/blocked 不自动换供给 |
| 运行输入 | `binding.freeze_execution_inputs` | exact manifest → Runtime Bundle → View；显式 Profile、DataPolicy、HostPolicy、ExecutionBinding |
| 任务执行与委派 | `workflow.run_research_workflow` + 注入 `RoleExecutor` | main 的0..N子任务、实际 child 输出、main 消费记录、全程预算和失败/unknown |
| 可选 API 执行接合 | `executor.FrozenRoleExecutor` + 显式 `binding_factory` | 每个真实 Task 对应冻结输入，经 Driver/Session/Host 产生实际调用、Trace、验证、slice receipt |
| 状态与人类决断 | `state.publish_workflow_checkpoint` | 固定工作流报告的不可覆盖 checkpoint；保留原人类决定，新增运行结果和下一动作 |
| 独立解释 | `guide.build_guide_request`、`ask_guide` | 只消费获准 MainState/必要 refs；不追随链接、不装 Tool、不向 main 回传或写科研状态 |

这些是明确的接合端口。`binding_factory(invocation)` 仍由调用方提供，它必须为本次真实 Task 产生合法冻结输入和独立实际配置观测；不得复制 View 作为 actual binding，也不得使用测试 fixture 或“总是 pass”的 verifier 建立真实来源资格。普通 native 实现可直接实现 `RoleExecutor`，无需导入 API 适配器。

## 可直接运行的两个离线命令

安装后使用 `rwb entry --help`。所有文件参数相对于显式项目 root；输出目录必须是新目录。

```powershell
rwb entry draft --root . --response intake-response.json --protocol-ceiling protocol-ceiling.json --task-ceiling task-ceiling.json --output-directory work/control-draft
rwb entry guide-preview --root . --state work/main-state.json --state-sha256 <actual-sha256> --question "目前需要我决定什么？" --model <explicit-model>
```

`draft` 读取已取得的模型 JSON 回答，校验并保存草稿。它不发送模型请求，不批准草稿。`guide-preview` 输出独立请求预览，零 Provider 调用、零 Tool、零状态写入。

研究执行的 Python 接点：

```python
from research_workbench.entry import WorkflowBudget, run_research_workflow
from research_workbench.entry.executor import FrozenRoleExecutor

executor = FrozenRoleExecutor(project_root,
    binding_factory=freeze_exact_task_binding,
    accountable_owner=named_owner)
result = run_research_workflow(project_root,
    directory=authorized_new_directory, task=validated_task,
    executor=executor, budget=explicit_workflow_budget,
    prior_usage=actual_upstream_intake_usage)
```

示例中的输入是调用方显式准备的真实对象。它不提供凭据发现、真实来源验收或自动研究规划器。预算对象要求正整数调用数/token上限、输入预占、单次输出上限、时间、子 Task 数量上限和委派深度；未知用量保留预占并停止后续调用。Task 自身预算跨 fresh 请求累计复检。

## 如何阅读输出

每次工作流写入 `REPORT.md`、`workflow.json` 和 `events.jsonl`。先读 REPORT 的阶段状态、主任务摘要、逐角色调用表、限制和下一动作。JSON/事件是复验附件；API Driver 另保留 exact Host/Trace/验证/receipt refs。checkpoint 引用固定报告和实际工件，Guide 仅读选中的快照。

`stage-completed` 表示主模型已消费当前执行阶段并提出 complete。报告和 generic receipt 都不授予 Task 完成、Claim 接受、Skill admission 或 Human 接受。失败、超预算、取消和未知消耗不会被改写为成功；合作取消不保证硬中断已经发送的请求。

目前支持 procedure/no-Skill/零 Tool 路径；required Skill、direct-tool 在当前接合层明确阻断。真实 API 资格、原生平台适配、完整研究任务语义验收和图形 UI 尚需各自证据。新建与缺 MainState 的人工接入采用同一研究契约，不改变研究方法；自动恢复与 M12 仍依赖独立前置条件。具体完成度见 [COMPLETION](COMPLETION.md)，后续候选见 [M12](m12/PLAN.md) 与 [前端](frontend/PLAN.md)。
