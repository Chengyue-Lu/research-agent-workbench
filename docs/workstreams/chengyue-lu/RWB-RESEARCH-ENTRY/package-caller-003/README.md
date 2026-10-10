# 包内研究入口桥接

本轮实现 [M1-010、M2-009、M11-008](../../../../TASKS.md) 的共同入口切片。状态由 TASKS 维护，验收过程见 [验证记录](VERIFICATION.md)，边界与输入见 [Task Packet](TASK_PACKET.md)。这是 PR140 分支候选，尚未计入 develop 支持。

此页保留前一 Action 切片的范围；当前 planning 身份及正式 Handoff 接合见[后续实现](../planning-handoff-004/README.md)与[当前验收](../planning-handoff-004/VERIFICATION.md)。下文的 planning 阻断是该切片当时的状态。

`call_intake` 接收已声明的需求、材料、权限及预算上限，发布控制草稿和调用事实。`run_frozen_intake_workflow` 重新读取本次发布报告，逐项检查事实与产物 pin，才将实际 Task/Method 交给显式 `ApiRoleBindingFactory`。Requirement 可以来自本次 intake，或由调用方单独提供；外部来源须与实际 Task/Method 的能力需求闭合，并单独记录。

factory 比较调用方提供的供给与资格证据，冻结每个实际角色的 Snapshot、Bundle、View。现有执行器消费这些文件，发出角色请求并保留 Trace、Host、Receipt。主 Agent 决定是否委派和委派数量，整批预检后执行子任务，再由新的主会话消费实际结果。caller 计入 intake 一次，沿用原总预算和截止时间。

Guide 和 checkpoint 由调用方在需要时显式开启。Guide 只读获准状态引用；checkpoint 保留 Human 待办。工件的结构有效、执行结束、开发 Task 验收和人类研究接受各自记录。

## 集成接口

```python
from research_workbench.entry.factory import ApiRoleBindingFactory
from research_workbench.entry.caller import run_frozen_intake_workflow

factory = ApiRoleBindingFactory(project_root, **explicit_frozen_inputs)
result = run_frozen_intake_workflow(
    project_root, intake_result=intake_result, binding_factory=factory,
    directory=workflow_directory, budget=whole_request_budget,
    accountable_owner=request_identity, deadline_monotonic=original_deadline,
)
```

调用方须提供 Provider、精确输入 refs、实际供给/证据、独立 binding observer 与证据 verifier、权限/数据策略和预算。包内接口不默认读取凭据，不产生付费授权或供给准入。当前可执行 factory 支持单一 Requirement 的 no-Skill Action 切片及显式 readonly Tool。planning Method 已有控制契约，但当前 Runtime Bundle 只接受 Action 身份；planning 执行在派发前明确阻断，该缺口单独保留。更广的材料/方法、角色配置和合格 Skill 由对应后续 Tasks 接入。
