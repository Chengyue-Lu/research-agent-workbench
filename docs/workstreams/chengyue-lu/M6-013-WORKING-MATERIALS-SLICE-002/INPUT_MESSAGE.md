# M6-013 Slice 002 Input Message

2026-10-11；主窗口明确授权的有界 Packet 原正文。获准源引用：.rwb/material-continuation-012/DEV4_TASK_PACKET.txt（发送窗口）；源字节 SHA-256：4c81eab164d1c77d9354c629c5202e22c3019108f3e10170c3c296c3516859b1。归档头不属于原正文；机器绝对路径不进入仓库。

## 有界 Packet 原正文

用户本轮已授权合并PR144、同步PR145并确认治理后与开发4继续实施。前置已完成：PR144 fee6b3af于北京时间2026-10-11 01:21正常squash合并2009bd6a2368785062fe7cd5f014a5e43cc8e20b；PR145基线同步到7341f968a561e9be4c28bf2899a8d81ccb24c346，local R2无ERROR、hosted governance重跑SUCCESS。原首失败component plan尚不可用的metadata日志保留，没有绕治理。源码/旧Schema/CI35pins不变。PR145保持Draft，其他components正在运行，不再混入后继产品。

新有界Task：M6-013 working material/result slots Slice 002，Profile implementation worker，required Skills []。从精确7341f968开始，复用你的managed worktree另开codex/m6-013-working-materials分支（或合适隔离checkout）；保留generate_memories=false/use_memories=true，勿改Root和primary代码。你不独自在代码库，勿覆盖/回退他人修改。

读集：guidance/README/PROJECT_MEMORY你的相关own-row；docs/README、DEVELOPMENT、ARCHITECTURE工作输入段；TASKS M6-013/M2-009/M1-010；ADR0027；你Slice001迁移与handoff；entry/working_inputs.py、entry/materials.py返回数据的具体provenance结构；现有model-working-input v0.2.0 Schema、test_entry_working_inputs.py与角色请求的必要接口。只按直接契约扩读并记录，禁旧API日志、Key、账、用户研究材料或其他workstream。

实现一个明确新版本的纯工作输入投影（建议0.3.0，先确认文件名未占用；保留已固定0.2.0源码/Schema/测试字节，不原位变宽）。必要目标：1) 消费现有read_material_inputs快照的material_provenance，普通/raw/admission/derivative保持typed关系、exact pins与未知/资格边界，不用任意Mapping放行nested extras；2) 结果槽允许显式授权的准确source_ref和已捕获UTF8文本（例如本次正式Handoff/结果文件），在本切片可先要求源ref必须在当前Task.input_refs内，重核同字节hash；标明实际读取结果不等于科学内容正确/Task完成，结果不是普通材料或调用者整段context；3) necessary_decisions/counterevidence沿用明确refs，不丢原文费用讨论；4) 把新的材料/结果槽扩展写入独立候选Schema，所有permission/admission/supply/runtime/task_completion boundaries仍false。支持的source Task当前仍0.1.0，未知版本拒绝。不要偷偷过滤budget字段后冒称新Runtime路径。

写范围互斥：新增src/research_workbench/entry/working_material_inputs.py（或事先报明确的新相邻模块）、tests/test_entry_working_material_inputs.py，必要schemas/v0.3.0/model-working-input.schema.json；只新增你的M6-013-Slice002 workstream/TaskPacket/Migration/Handoff/可见通信。禁止改working_inputs.py和v0.2.0/旧测试、roles/intake/factory/workflow/Driver/Host/Session、CI/build/resources/defaultCatalog、Task定义/状态与Registry。Root负责新实际请求consumer和统一tests/installed/CI登记，不把纯投影重复当成果。

输出：具体新函数签名、版本、字段白名单与来源/结果refs如何进入Task的新消费者要求；测试代码包含ordinary与完整raw-sidecar-selected-derived、新结果源、hash/未授权/mismatched provenance/nested extras/伪科学或permission claim拒绝，旧0.2.0拒绝新字段保持；Compact Handoff列Source/Schema/Test pins与所有未接Runtime层。纯函数无IO/Provider/Tool；无凭据、账或隐藏推理；不运行测试（Root唯一执行），可做AST/JSON/静态语法，提交本有界新文件并正常push，暂不另建重复PR，由Root集成发布。旧source9a93/deliveryad7/私有结果冻结。

预算15分钟完成第一可消费切片；需要跨共享消费者先报具体接口，不越写scope。停止于新的typed材料/结果投影交付，不扩到全M6版本迁移、不称DONE、新默认无额度执行或科学/Skill接受。本轮不创建测试窗口或全局记忆。可更新primary你的own-row，立即重读保留其他窗口内容。
