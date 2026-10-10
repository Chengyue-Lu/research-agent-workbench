# M6-013 Slice 002 Typed Slot Migration

2026-10-11；ADR-0027 方向下的独立候选数据契约，source Task 0.1.0 → model-working-input **0.3.0**。Root 报告 PR144 已合并、PR145 基线已同步；本片段不以此推定新 Runtime 接受。固定基线为 `7341f968a561e9be4c28bf2899a8d81ccb24c346`。

## 函数与字段接口

`project_working_material_input(task, *, role, responsibilities, materials, stop_conditions, results=(), necessary_decisions=(), counterevidence=()) -> dict`

所有参数为已获准、已捕获的数据，无文件 I/O。未变化职责/目标/权限/交付/actual stops/必要决定/反证由冻结 v0.2.0 的 `project_working_input` 显式复用；该纯函数的私有严格记录/ref helper 是固定依赖。新函数不遍历完整 Task，不复制经济对象或账本。费用文字原样保留，source Task 的经济控制留在 caller。

| Slot / producer | 新输入白名单 | 投影与 consumer 义务 |
| --- | --- | --- |
| `read_material_inputs` → materials | path/sha256/revision?/text/material_provenance | Task exact refs 与 UTF-8 hash 重核，保持材料顺序；拒绝别名重复、未准入 inbox 和 extras |
| ordinary-input provenance | kind/source_relation/scientific_qualification/gap | source_relation=not-declared；科学资格 not-established；raw/sidecar 不能伪装 ordinary |
| raw-source / source-admission provenance | kind/schema_version/admission_id/admission_ref/raw_ref/acquisition/parser/license_or_data_use/sensitivity/egress_restriction/verification_scope/scientific_qualification/permission_grant | source-admission version 0.1.0；raw 与 sidecar 均必须在本次 materials captures 和 Task 精确读集中，own pin/常规 sidecar path/同组 base 一致；permission_grant=false |
| source-derivative provenance | 上述 base + derivative_ref/relation | derivative own pin 必须一致并与 raw/sidecar 区分，仅本次显式选中 capture 进入工作输入，不读取或扩充未选 derivative |
| acquisition / origin / parser | acquisition: origin/acquired_at/operator；origin: uri?/doi?/device?（至少一项）；parser: name/version | 每层 exact keys；时间须有时区；provenance 是已由 reader 验证的来源声明，不是科学质量判断 |
| 显式获准结果 → results | kind（formal-handoff 或 result-artifact）/source_ref（path/sha256/revision?）/text | 每个 ref 必须预先进入当前 Task.input_refs；同字节 UTF-8 hash 重核；与 materials 不重复；kind 是 caller 标签，不能自行接受正式 Handoff |
| results 输出 | 输入三项 + verification_scope/scientific_qualification/contract_validation/task_completion | scope=captured-utf8-bytes-and-task-pin，科学/契约资格 not-established，task_completion=false；结果不会进入普通材料槽 |
| necessary_decisions / counterevidence | statement/source_ref | 沿用当前 Task 精确 refs；不接受整段 caller_context，费用讨论原文保留 |

五项顶层 boundaries 为 permission_grant/input_admission/supply_selection/runtime_authority/task_completion=false。未知 Task/provenance 版本、额外嵌套字段或 positive authority/qualification 结构化主张拒绝。普通源文本中的主张照原文保留，不用关键词删除。

## 双版本与消费者

旧 v0.2.0 模块/Schema/测试保持固定字节，继续拒绝 material_provenance 与 results；新模块/Schema 发布在新路径，不原位扩宽旧版。0.3.0 是 model-working-input 数据版本，**不是** Task/Policy/View/Host/Session 0.3.0。默认 Catalog、安装 resources/backend、CI 登记由 Root 单独接合。

Root 本轮接点为独立 opt-in 只读 Guide `working_guide.py`：内部验证旧 Task/Profile/原 grant、完整读取获准 material captures，按明确授权的结果 ref 将结果从材料槽分离，用新函数构造实际工作请求；不发送完整 Task/Policy/context。Guide 使用 kind=result-artifact 即可，不把 slot 名当 formal Handoff 接受。结果来源授权必须由 caller 在 fresh Task.input_refs 中装配；函数不会发现文件、补 ref 或 grant。

caller 仍负责 source-admission 原件解析/准入、egress/DataPolicy/Profile 交集、Provider 前实际文件/版本复验、正式 Handoff 内容/权限与资格、响应/交付存在性和科学接受。本投影检查 provenance typed closure 的一致性，不重新解析 sidecar 文本来证明声明语义。

main/intake/child/原 Guide、Task/Protocol/Policy/View/Bundle/Host/Session/workflow/Trace/Receipt 与默认无经济额度执行仍未迁移。本片段不改旧 Runtime 或 actual request；Root 统一给新请求→Provider→response、零请求反例、installed/CI 与旧版保留证据，再推进后继有界切片。
