# M6-013 Slice 001 Risk Ledger

声明风险 R2：新工作输入契约处于权限/上下文边界，未进入默认执行。

| 风险 | 控制与测试代码 | 当前证据 / 未决 |
| --- | --- | --- |
| 投影被误当预算运行迁移 | 新 contract 0.2.0，source Task 0.1.0；旧控制文件不动，列全部消费者 | 仅静态；Root 必须集成完整版本闭包 |
| 额外文件/声明权限被注入 | exact Task pins、snapshot SHA、record refs；authority boundary false | 测试代码含 outside/stale/duplicate/true-boundary，未执行；caller 仍负责真正 admission |
| 完整经济内部对象泄漏 | 源 Task 不遍历，嵌套 whitelist；typed stop kinds 无经济类别 | 测试含 trap Mapping/ledger/预算 wrappers；未检查 actual requests |
| 删除人类费用问题 | 仅按字段投影，文本原样保留，不按 budget/token/cost 词过滤 | 测试含中文费用/ledger 原文与 CRLF/UTF-8 |
| 停止语义误分类 | caller 明确分类，模块不猜旧 free-form stop | kind 类型可程序检查，condition 语义和实际 Gate 仍需 caller/人类依据 |
| 旧 live grant 被放宽 | 不读或改实际 grant/账/Attempt；无新付费授权 | 历史版本/失败证据保持；不作 live 接受 |
| 默认/安装消费者与 CI 漏接 | 新文件/显式 pending 列表；不写共享 backend/resources/CI | Root 串行映射和安装/全消费者验证；不能借静态通过判通用路径通过 |
