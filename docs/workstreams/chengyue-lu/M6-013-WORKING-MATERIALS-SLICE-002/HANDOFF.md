# M6-013 Slice 002 Compact Handoff

2026-10-11；implementation worker；required-Skills=[]；R2。授权、输入和范围见 [Task Packet](TASK_PACKET.md) / [Input](INPUT_MESSAGE.md)，消费者见 [Migration](MIGRATION.md)，风险见 [Risk Ledger](RISK_LEDGER.md)，可见通信与检查事实见 [Communications](COMMUNICATIONS.md)。

## 交付与 pins

独立候选分支 `codex/m6-013-working-materials`，精确起点 `7341f968a561e9be4c28bf2899a8d81ccb24c346`；最终提交由 Git 与实际回传固定。旧 Slice 001 source9a93/deliveryad7 与原分支档案保持身份，无重复 PR 或 merge。

| 工件 | 内容 | SHA-256 |
| --- | --- | --- |
| [working_material_inputs.py](../../../../src/research_workbench/entry/working_material_inputs.py) | candidate 0.3.0 pure projection；strict typed provenance 与独立 results | `f2f2d5304aa0ddeef59d022a78ff36cae365c90db9a4df1e1fde3246a23cffbe` |
| [model-working-input.schema.json](../../../../schemas/v0.3.0/model-working-input.schema.json) | 新独立 Schema，无外部 refs，所有 boundaries=false | `abd3f3cd8346933cc4c225a2927c0fb0805b913e7029f7b1a382a9e43705f100` |
| [test_entry_working_material_inputs.py](../../../../tests/test_entry_working_material_inputs.py) | 14 个方法代码，未执行；含实际 reader golden closure 与正反契约 | `cff4e31c4d22af3991ac5d6fd3845cc61ffc60dd5751072c735fd76edc8c1e25` |

函数：`project_working_material_input(task, *, role, responsibilities, materials, stop_conditions, results=(), necessary_decisions=(), counterevidence=())`。source Task 仅 0.1.0；materials 必须为完整的已获准 read_material_inputs captures；results 输入为 kind/source_ref/text，ref 预先列入本次 Task.input_refs，UTF-8 hash 重核并与材料槽分离。result-artifact 或 formal-handoff 标签均不产生正式内容接受，输出 contract/scientific not-established、task_completion=false。

原 v0.2.0 三份模块/Schema/测试对固定基线逐字节相等。新函数复用旧纯投影公共函数及严格私有 record/ref helper，费用文字不删；旧经济 Task/Policy/运行控制由 caller 按原语义处理。新 provenance 不是任意 context；raw/sidecar/selected derivative typed closure 及 nested extra/claim 检查见 Migration。

## 实际验证范围与缺口

本窗口仅 AST、内存 compile（未执行 code object）、JSON syntax、引用/文件 hash 和 Git diff 检查，具体结果见 [Static Checks](STATIC_CHECKS.json)；14 项测试代码未运行，没有产品 import/测试/构建/API/Provider/生产 Tool/Attempt、Key、认证或账本操作。静态结果不证明测试通过、科学正确性或 live 资格。

Root 本轮拟接独立 opt-in 只读 Guide actual request；本片段未写 working_guide 或实际请求消费者。main/intake/child/原 Guide、Task/Policy/View/Host/Session/workflow/默认 Catalog/backend/resources/CI 均未由本片段迁移。M6-013 仍 IN_PROGRESS，不判 DONE 或新默认无额度 Runtime 已通。

Root 后继：统一运行 14 项新代码和旧 0.2.0 保留反例；接结果 refs 的 caller 授权/分槽、Guide request→Provider→response 与 zero-request 反例；独立检查安装 Schema/模块/版本分派与 CI 消费映射。仍须 admission 原件语义、权限/DataPolicy/最终文件复验及正式 Handoff 接收检查，不用 pure slot 替代。
