# M6-013 Slice 001 Compact Handoff

2026-10-11；implementation worker；required-Skills=[]；risk R2。输入/权限见 [Task Packet](TASK_PACKET.md)，版本/消费者见 [Migration](MIGRATION.md)，限制见 [Risk Ledger](RISK_LEDGER.md)，可见通信见 [Communications](COMMUNICATIONS.md)。

## 候选与交付

独立 managed worktree、branch `codex/m6-013-working-inputs` 从精确 `76fd3d892eb1f1a15799c9f24a255ef2dcf0190e` 开始；该本地组合 PR143/PR144 来源不是已合入 develop。最终 commit/ref 由本目录 COMMUNICATIONS/Git 和回传 pin；main 可 cherry-pick 仅本切片的提交。没有修改 PR140/143/144，也不借其测试/资格。

| 文件 | 状态 | SHA-256 |
| --- | --- | --- |
| [working_inputs.py](../../../../src/research_workbench/entry/working_inputs.py) | 纯程序白名单投影，输出 model-working-input 0.2.0；当前只接受 source Task 0.1.0 | `cfc4ede84553fbfd19bfee3e8424f2456b28fa5c79fd7504bc148db0d3e7ca21` |
| [model-working-input.schema.json](../../../../schemas/v0.2.0/model-working-input.schema.json) | 独立、无外部 $refs 的候选契约，边界 false；没有覆盖旧 Schema | `0cb858f0aeebf19f2132f5cb508737aff82580a38e42b3367bb91838a8aaceb1` |
| [test_entry_working_inputs.py](../../../../tests/test_entry_working_inputs.py) | 9 项测试代码，**未执行** | `f26498dee241ae747856312f99b5a133734e6ee2bacb79f67b85edf88f72f28f` |
| [TASKS](../../../TASKS.md) | 仅 M6-013 READY→IN_PROGRESS，定义/依赖/验收不变 | 用 Git diff 界定 |

投影包含职责、Task identity/原文目标、获准 UTF-8 snapshots、必要决定/反证的 exact refs、权限/委派治理、交付与显式 actual stops。不会遍历完整 Task，也不访问 economic budget、sub_budget、policy 或 ledger；类型化额外字段被拒绝，普通文本中的费用讨论完整保留。快照 hash 与 Task exact pins 再核对；revision pin 必须一致。没有实际文件读、Tool 调用、admission、Supply selection 或执行权；真正文件读取/版本解码/Human Gate 仍在 caller。

`project_working_input(task, role=..., responsibilities=..., materials=..., stop_conditions=..., necessary_decisions=..., counterevidence=...)` 返回独立 dict。caller 必须先按 source 版本验证控制 Task，批准 reads，并给经版本绑定的职责与明确 stop kind/condition；源 Task/Policy 留在程序侧。模块不自动识别旧自由文本的经济 stop、不秘密编辑旧 Prompt，也不声明新 runtime 已无额度。

## 测试与静态范围

9 项测试代码覆盖 whitelist/prose/CRLF UTF-8/hash、detached/deterministic、内部经济对象不读/不遍历、不支持 source version、stale/outside/duplicate/extras/revision、真实 stop 枚举、决定/反证 exact refs、Schema authority false/economic extra 拒绝、旧 Task Schema 仍必需 budget。仅 AST/内存 compile、JSON syntax、Markdown 文件目标、diff/源 hash 检查。没有运行项目 import、产品/tests/build/API/付费模型/生产 Tool/Attempt、Key/认证或账本。Root 是唯一测试执行者；结构通过不证明科学正确性或运行资格。

实际读范围：current guidance/README/primary 项目入口；docs navigation/Development/Architecture、ADR-0027/compatibility、TASKS 三项及 hard deps；接口/文件名发现后只读直接 roles/Task model/intake compiler/factory/View budget producer/Host actual checks/Session limits-policy与对应必要 Schema/Catalog 段、模块 03/05 接点。原 `.rwb`、凭据、API 日志和旧 Attempt 未读。全局 memory 仅用项目入口，不写全局记忆。新 worktree `.codex/config.toml` 的 recall=true/generate=false 保留为本地政策 diff，不进入此产品提交。

## 明确尚未接入的消费者

roles.build_role_request、intake_call/compile_control_draft、main/child 输出 Schema/职责、Guide/short/maintenance、factory/executor/driver、Protocol/Task/Policy/View/Bundle/Host/Session、workflow、Trace/Receipt、SchemaCatalog default/installed RuntimeResources/backend/CI **均未切换**。当前 actual request 仍含完整旧 Task 与预算 baseline；本片段没有 outbound difference 或无额度执行证据。

Task 0.2.0 source 目前明确拒绝。Task/Policy/View/Host/Session candidate 0.2.0 和 ApiSessionControls 2.0.0 仅迁移表决定，没有新可执行 Schema；为什么不能安全分离、真实能力/取消与旧 live grant 的边界见 MIGRATION。main actual Handoff/child state/profile options 和 intake draft 的新 work slots 还须明确，不能用任意 caller_context 打通。

测试窗口先修 PR140 direct CI consumer P2（tests/ci_components.json、test_ci_components.py）并接 M1-010；本切片未编辑这些共享文件，起点不含其后续修复。Root 需把新增 module/test/Schema 纳入其串行消费者/CI 接合。没有将本切片判 DONE、merged/accepted 或正式 Source/Human/Skill/live 合格。

## Root 下一步

1. 统一运行本独立测试，检查 v0.2.0 Schema 及旧 v0.1.0 正反证据，归档任何失败；静态结果不替代它。
2. 接受/修订候选版本号与 typed slots；按迁移表串行改 producer、dispatch、Core 消费者及角色输入/输出 baseline，保留旧 bytes/hash/live grant。
3. 给 actual request 差异、unknown usage 与有效交付独立判定、无经济额度运行、旧 budget 准确回放、权限/ref/资格取消失败等 evidence，再评估 M6-013 后续切片。无需等 review 才消费此源码候选。

