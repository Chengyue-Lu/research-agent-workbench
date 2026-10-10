# 工作材料与结果进入独立 Guide

本切片按 M6-013 的工作输入迁移方向，将已获准材料和明确结果送入独立只读 Guide 的实际模型请求。它衔接 [材料读取切片](../material-input-011/README.md)，使用显式选择的 0.3.0 工作输入；旧 0.2.0 纯投影及现行角色请求保持各自版本。

| 测试模块 | 输入 | 输出与实际消费者 |
| --- | --- | --- |
| 材料/结果投影 | 经旧 Task 控制验证、同批捕获的 UTF-8 材料；显式分类且 exact pinned 的结果 | `work.materials` 保留原件、来源 sidecar 与选中派生关系；`work.results` 单独记录原文及有限验证范围。由新 Schema 校验 |
| Guide 请求 | 明确 Task/Profile、模型、输出参数、实际停止条件及选中的引用 | 模型消息只含角色 baseline 和 `work`；完整 Task、旧 budget、账本与主会话上下文留在调用者内 |
| Provider 边界 | 已构造的工作请求、明确 Provider 与取消信号 | 能力和数据策略协商后复验实际文件，再调用选定 Provider 一次；取消、错误、原生用量和 unknown 如实保留 |
| 只读隔离 | Task 允许的材料与结果；没有 Tool 或状态写入器 | 返回人类解释。模型意外返回的 ToolCall 不执行；项目文件、MainState 与主会话不因 Guide 调用改变 |
| 安装包消费者 | 从本分支生成并独立安装的 wheel | 在 checkout 源码目录不入产品导入路径时，消费同一模块和新 Schema，验证输出与边界 |

结果的 `formal-handoff` 分类由调用者明确提供；本接口只核验文本字节和 Task pin，不执行正式 Handoff 契约接受。正式 child → main 消费继续使用已有 Handoff 链，不能从此标签推导接受、完成或科学资格。

这是 opt-in 的 Guide 应用接口。main、child、intake、默认角色入口及 Task/Policy/View/Host/Session 尚未迁移；新工作输入不改变它们的现行控制契约。技术性输出参数须显式提供，旧 Task 的实际 output grant 仍在程序中验证。取消按离散检查处理，回调只报告取消；接口不提供文件系统原子快照或在途取消保证。

范围见 [Task Packet](TASK_PACKET.md)，实测与缺口见 [验证记录](VERIFICATION.md)。M1-010、M2-009、M11-008 与 M6-013 的剩余义务及状态仍由 [TASKS](../../../../TASKS.md)维护，本切片不将整项置为 DONE。
