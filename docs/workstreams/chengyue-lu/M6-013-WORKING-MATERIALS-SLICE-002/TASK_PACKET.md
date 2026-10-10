# M6-013 Slice 002 Task Packet

2026-10-11；Profile: implementation worker；required-Skills: []；risk: R2。主窗口转达人类继续实施授权，完整有界 Packet 见 [Input](INPUT_MESSAGE.md)，可见传递见 [Communications](COMMUNICATIONS.md)。

## 固定输入与范围

精确起点 `7341f968a561e9be4c28bf2899a8d81ccb24c346`，候选分支 `codex/m6-013-working-materials`。复用本窗口 managed worktree，原 Slice 001 分支和 source9a93/deliveryad7 保持身份；memory recall=true/generate=false 保留为本地环境设置。

获准读集：guidance/README/primary PROJECT_MEMORY 的相关 own-row，docs navigation/Development/Architecture 工作输入段，TASKS M6-013/M2-009/M1-010、ADR-0027，Slice 001 Migration/Handoff，working_inputs/materials 直接生产消费接口，0.2.0 Schema/测试及角色请求必要接口。为严格复制来源字段和常规 sidecar 路径，直接扩读 source-admission 0.1.0 Schema 与 artifacts/admission 的路径 marker/helper 段；不读研究材料、旧 API 日志、Key、账或其他工作档案。Root 授权 Packet 是本轮唯一读取的另一窗口私有输入。

## 互斥写域与输出

- 新增 [working_material_inputs.py](../../../../src/research_workbench/entry/working_material_inputs.py)、[独立测试](../../../../tests/test_entry_working_material_inputs.py)、[候选 Schema 0.3.0](../../../../schemas/v0.3.0/model-working-input.schema.json) 及本目录文档。
- primary PROJECT_MEMORY 仅本任务 own-row；写前重读并保留其他窗口条目。
- 不改原 working_inputs/v0.2.0/旧测试，roles/intake/factory/workflow/Driver/Host/Session、CI/build/resources/default Catalog、Task 定义/状态或 Registry。

输出是可消费的纯数据投影、明确签名/slots、测试代码、Source/Schema/Test pins、[迁移与消费者要求](MIGRATION.md)、[风险](RISK_LEDGER.md) 和 [Compact Handoff](HANDOFF.md)。五项原 authority boundaries 均 false；source Task 当前只支持 0.1.0。结果读取不代表 formal contract/scientific qualification/Task completion。

## 时间、验证与停止

工作段从北京时间 2026-10-11 01:28:24 起，15 分钟内收束首个可消费切片。仅 AST/内存 compile/JSON syntax/引用与 hash/Git 静态检查；不 import/运行产品或测试，不构建、不调用 API/Provider/Tool，不读取凭据/Key/账。Root 是唯一测试执行者并接独立 opt-in 只读 Guide actual request consumer。

可提交并正常 push 独立候选，不创建重复 PR、不 merge。共享接口需求回报 Root，停止在 typed 材料/结果投影；不扩到全 Runtime 迁移，不判 M6-013 DONE、默认无额度执行或科学/Skill 接受。
