# 候选检查范围

以下均为离线候选验证，真实 API/Key 值读取/安装为 0。

- 配置/profile：Python3.11 和 3.14 各 29 tests，其中 28 PASS、1 Windows 符号链接权限 skip；
  十一家 Schema/config 正例、77 独立反例，九家实际文本编解码通过、两家明确拒绝。
- 协议：29/29 PASS；四协议、实际 profile、精确非思考控制、角色/Tool/Schema/usage/stops/安全错误反例。
- 工厂：最新源 15/15 PASS，官方已关闭 Google 模型在凭据前拒绝。
  八家 fake 正例及三条阻断覆盖深冻结配置、漂移、Schema 本地验证、指定非 strict Tool、
  畸形响应和请求 Schema 的安全诊断。DeepSeek Responses 未臆造官方未定义的 strict 成员。
- 工厂独立审查：11 个先前工厂检查与 5 个对抗检查通过；发现的错误上下文和实际 defaults 漂移已修复复验。
- Session：修复后 owner 离线检查 80/80 PASS，含 37 新政策、19 原 Session、22 原三家 Adapter 和 2 kernel。
  当前请求与 Tool 参数/结果在 capture 后重新校验；默认循环 AST 与起点相同。
  显式政策仅接收独立的闭集隐私摘要 sink，拒绝 generic AgentTraceRecorder，防止已发现的 raw dataclass Trace 缺口。
  Tool context 的 local-history 事实与 Provider.generate submission attempts 分开计数；独立复验待最终 receipt。
- 绑定：11/11 直接测试通过，含新 envelope 1.1 的 fake 执行、独立新进程 cold replay、篡改和使用前漂移；
  原 baseline 最终联合 56/56 PASS，source freeze receipt 已保存。

分切片 receipt 位于本候选 worktree 的忽略目录 `.rwb/m6-general-prototype/` 的
profiles、wire-codecs、factory、factory-review、binding、session 和 session-review。
组件联合、repository/package/governance 的最终结果尚未列为 PASS，待冻结后按 exact head 检查。
完整 full/coverage 或 remote live 证据不在本轮声称范围。

初始 Runtime 资源缺失、profile/codec 政策不一致、测试 fixture 错误及独立审查原失败日志保留。
不能用后续 PASS 覆盖前一源版本的失败，也不能把较早源哈希上的检查移用到新源。
