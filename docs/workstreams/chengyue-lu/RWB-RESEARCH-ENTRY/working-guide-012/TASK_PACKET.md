# 工作 Guide 消费：执行范围

2026-10-11；R2 implementation slice。人类要求先合并 PR144、同步 PR145 并确认治理，再继续并行实现。PR144 已合入 develop `2009bd6a2368785062fe7cd5f014a5e43cc8e20b`；PR145 基线同步固定于 `7341f968a561e9be4c28bf2899a8d81ccb24c346`。本切片从该 head 新开 `codex/working-input-material-slots`，候选实现不计入 develop 已合并支持。

执行 Profile 为 coordinator/test executor；开发 Profile 为 implementation worker；静态检查为 targeted reviewer；required Skills 均为 `[]`。实现输入限于旧 Task/Profile、材料捕获、Provider port、0.2.0 候选及其新版本独立扩展。并行写范围限于纯材料/结果投影、新 Schema、独立测试和切片记录；消费者与统一验证顺序接合。可见交接和原始工程结果保存在本次任务归档，不写入全局记忆。

交付为版本化材料/结果投影、新独立只读 Guide consumer、输入输出说明和实际 source/installed 检查。材料与结果必须先在原 Task exact read set 内；必要决定和反证引用也必须为本请求实际捕获项。没有任意 caller_context、引用自动递归、凭据读取、生产 Tool 或新实际 API 请求。

验收首先验证同一供应接口的实际请求消费者，再验证原件/sidecar/派生关系、结果槽、显式选择、权限和旧控制未松绑、最终 pin 漂移、取消、失败一次调用和不写项目状态。独立安装包验证新资源与模块来源，保留原失败及失败后的修复身份；通过 Schema 或工程测试仅说明结构与接合成立。

停止于可评审的单一实现切片与候选 PR。缺少精确 pin、必需来源闭包、权限或实际执行事实时，停止对应调用并保留缺口。新无经济配额 Runtime、全部角色迁移、研究对象编译、真实科研和产品 Gate 均不是本切片完成标准；不以固定任务、固定子 Agent 数量或固定交付文件格式替代通用决策。
