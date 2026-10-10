# M6-013 Slice 002 Risk Ledger

2026-10-11；R2 authority/data boundary evidence candidate。依据为 [Task Packet](TASK_PACKET.md) 与 ADR-0027 已授权方向；版本 0.3.0 工程候选不授予新权限。

| 风险 | 当前措施与限制 | 后继责任 |
| --- | --- | --- |
| 来源 ref 扩读或跨材料绑定 | 每项 captured UTF-8 hash/Task exact ref 重核；raw/sidecar/derivative own role、同组 base 与 captured closure 一致；extras/别名重复拒绝 | Root 在真实读取、最终 Provider dispatch 时验证文件与 admission 语义/数据规则 |
| nested arbitrary Mapping 变成控制输入 | acquisition/origin/parser/ref/普通与来源 provenance 都为闭集键与类型；结构化 permission/scientific 正主张拒绝 | Root 给完整 actual request 正反证据；结构检查不判科学正确性 |
| 结果标签伪装正式 Handoff/完成 | 独立 source_ref/text slot，Task exact refs 与 hash，contract/scientific not-established、task_completion=false | Root 验证正式契约与接收权，不通过 kind 名称自动接受 |
| 同一文件被双槽/路径别名注入 | materials/results captured paths 规范化后大小写去重，跨槽 exact ref 重复由冻结 hash 校验路径拒绝 | Root 真实文件身份检查保留；纯函数不能解析 junction/真实文件别名 |
| provenance 结构一致但声明内容未被 reader 验证 | caller 必须先消费现有 read_material_inputs/admission 验证；投影不解析 sidecar 内容 | 不把此模块当 admission、scientific qualification 或 Runtime 权限服务 |
| 旧数据被静默宽化/重解释 | v0.2.0 模块/Schema/测试字节保留，新 0.3.0 独立；旧 grant 与控制留 caller | Root 双版本正反与新 actual consumer；全 M6 迁移未完成 |
| 私有 helper 依赖和资源尚未发布 | 复用固定基线 v0.2.0 的 _items/_object/_ref/_ref_key/_text，只增新模块；资源/默认 Catalog/CI 未修改 | Root 协同冻结依赖、安装包与 CI 映射，未来契约重构须另发 Packet |
| 只写测试却误称通过 | 本窗口只 AST/内存 compile/JSON syntax/links/hash/Git；14 项测试代码未执行 | Root 唯一执行并保留任何失败、unknown 和修复身份 |

未运行 API/Provider/生产 Tools/Attempt/Key/认证/账本；产品只纯投影。M6-013 保持现有 IN_PROGRESS，本片段不改变 Task 状态或人类/Resolver/Runtime 权属。
