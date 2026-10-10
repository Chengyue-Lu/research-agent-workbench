# CHAIN-DEV4-002：动态消费与 direct Tool 桥接

人类 2026-10-07 要求校准 Task 后直接执行全桥测试；AUDIT-RWB-CHAIN-002；Task-definition 候选 M1-010/M2-009/M11-008 单独 docs-only PR。Profile：bounded implementation worker；required-Skills=[]。具名范围路诚钺控制/Trace，黄毅 Runtime 接点的正式接受保持待审。

输入：[总 Packet](TASK_PACKET.md)、entry/driver.py、executor.py、workflow.py、roles.py、其直接依赖 adapters/models/session.py ClientTool 和 ApiSessionLimits、execution Host/closeout 公开接口；existing entry tests 仅作接口参考。本 checkout 为 PR140 d630f8e 候选，与旧 primary 不同。

Ownership 只包括 src/research_workbench/entry/{driver,executor,workflow}.py，以及本目录 DEV4_HANDOFF.md/DEV4_COMMUNICATIONS.md。Root 负责其他入口 caller 与全部测试；资产代理负责 assets。你不独自在代码库，保留他人编辑，不回滚其他内容。不得修改 Schema、Registry、accepted Skill/config、权威语义/Task 定义或 primary memory。不得 commit/push/install、运行产品测试、读取 Key/账、调用 API/生产 Tool、创建或预占生产账。

目标：

1. child 完成后，新的 main context 显式携带本轮 child 的 execution status、usage 与 artifact/receipt opaque pins；保留原控制摘要。引用只传递不默认读正文，不加载不在 Task allowlist 的文件。
2. 为 RoleExecution 提供显式、受整 Run/Task 剩余预算约束的 session model-turn 可变上限；现默认 1 保持兼容。预占全部可能调用，未知保留，实际 calls 不能在请求后才发现额外调用无授权。不能固定所有角色必须使用 Tool。
3. 可选 procedure/direct Tool Driver 接入显式 ClientTool 映射，精确 Task/Profile/Supply permission/tool allowlists，Session tool side-effects 与数量/结果字数上限；request tools 必须等于声明定义。真实 tool events/actual counts/Tool failures 纳入 Trace/Host/Receipt，unsupported Skill 路径保持 preflight 阻断。不要只取消零 Tool 判断就当桥通过。

输出：最小通用接口实现、Compact handoff 中列改动/必要性/Root应跑的关键正反场景、尚未解决缺口和未测试事实。禁止宣称 source/live/Skill/Human 接受或全链完成。预算 20 分钟、两轮；超范围/需 Core 权威变化则停对应切片并列具体缺口。不派测试子代理。
