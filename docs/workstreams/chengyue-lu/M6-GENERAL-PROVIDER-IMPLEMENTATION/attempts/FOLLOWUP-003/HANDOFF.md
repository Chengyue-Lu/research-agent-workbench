# FOLLOWUP-003 交接

继续同一 [R2 Draft PR128](https://github.com/Chengyue-Lu/research-agent-workbench/pull/128)，
base `27cbf860e48e9639bd3af32a58c12bfd88d87526`；cross-owner审核请求维持，不代具名接受/merge。
产品源`f7969bb2a3434ef603cce5743884307af5025473`；测试修复源`5a0b19d73f63477b66613ffade73045b75a74ed7`仅补新kind清单。
831组件原轮826PASS/1catalog FAIL/4skip，该清单修复6PASS；产品/Schema/CI/policy同源。
177资源/119模块/安装8smokes及独立复核见[CHECKS](CHECKS.md)。

新增显式源码闭包和 manifest1.1/policy-v3，ConfiguredProvider构造及credential前重验，
baseline1.2 producer/use/cold replay消费全图引用。旧manifest/Envelope保持原语义，新绑定
实例不能降级使用旧manifest。源码图从实际roots派生，含package initialization，cold replay
只AST/compile归档bytes；trusted compiler/native/dependency/generated行为是明确限制。

显式 body policy绑定已有Flash Responses nonthinking三local phases，冻结ModelRequest
及实际body的model/mode/Tool/history/call ID/result/Schema/大小上限；credential及intent前检查。
None维持旧driver/报告。source graph尚未与当前driver/report完整运行上下文自动整合，
不把局部manifest或本地业务断言当M6-010资格、remote strict或service取消/并行保证。

下一具体切片：把 opt-in graph/bounded body 绑定接入显式 driver和版本化脱敏报告，冻结实际
非秘密profile/config/transport/keyref/Session/Tool/report/Windows观测，保留旧报告回放。
随后准备实际唯一DB/anchor/namespace、固定输入预占依据、dated北京18+且官方idle窗和新建
报告目标，形成可审查exact-run packet；实现审核和具名运行接受仍由人承担。

用户累计成功/失败input+output≤10,000,000，精确Flash，每次北京18+且官方闲时。
执行计划≤3call/Attempt、≤3fresh Attempts仅经离线修复/refreeze，无auto retry/fallback；
unknown金额非阻断，unknown token保持预占并停止。真实调用/Key/presence/bridge均0。
M6-009 IN_PROGRESS、M6-010 BLOCKED，NOT_EXECUTABLE。M5/A4/Pilot/科学和发布权威独立；
共享进度写前重读合并，未将全目标置complete。
