# M6-009 源码图消费与固定请求体准入

Profile：Provider integration coordinator；Required Skills：[]；风险 R2。
基线 develop `27cbf860e48e9639bd3af32a58c12bfd88d87526`，延续 Draft PR128。
黄毅负责 Provider/Session，路诚钺协调共享语义；沿用已接受 M6-009 定义和 baseline 写域。

读集为 Repository guidance、定义计划、当前 Provider/配置/codec/conformance、直接 baseline
生产及回放消费者、Schema/CI/build/tests 和已声明官方来源。以 import metadata 扩展 helper
依赖和 package initialization 读集；不读取无关研究、密钥原文或环境 presence。

互斥有界委派：source observer 45min，仅新增观察器、Schema、直接测试及四份 fixtures；
prepared-body owner 40min，仅 body、guarded transport、driver 和直接测试；官方资料编辑35min，
仅十五字段表；独立 reviewer25min，只读产品及本地证据。root串行整合 Provider manifest、
ConfiguredProvider、baseline envelope、消费/回放测试、CI、构建及本 workstream。
完整平台事件导出不可得；本地留可见消息、原失败、工具结果与 exact-source receipts，保留 capture gap。

源码图从实际 roots 派生，包括 package parent initialization；归档 bytes 只做 AST/compile，
不执行归档代码。检查支持语法的源码 callable/defaults、alias、global/class policy，并对实际
canonical 对象及声明位置复核。compiler/native/dependency、生成的 dataclass/Enum/typing 行为
是明确的信任边界，不冒称远程认证或完整 Windows 运行上下文。

新 manifest 1.1.0 / provider-binding-v3 引用独立 provider_source_closure 1.0.0；
ConfiguredProvider 显式选择该 FileRef，构造及 credential 前重验。baseline envelope 1.2.0
消费新 manifest，各次 use_refs 包含图与全部 source refs，cold replay 独立重派生。
默认配置、manifest1.0、envelope1.0/1.1 和旧绑定语义保留；无 self/envelope/Protocol hash 循环。

显式 ConformanceBodyPolicy 绑定已有 DeepSeek Flash Responses nonthinking 路径，三个 local
phase 的固定合成输入、Tool/history/call ID/结果、enum Schema、输出及 body 上限。在 credential
前验证 ModelRequest，在 intent 前验证实际编码 body；None 保留旧 API/报告。实际 service
strict、取消失败 token 账单和完整执行上下文另验，不借用 Chat Schema 或型号兼容推断。

原失败及复验分别留档；不得放宽 reader 语法或 pin 校验迁就 fixture/安装环境。出现权限/权威
或 Core 语义变动、所有权重叠、意外凭据/API访问、无界输入、支持外语法或时限到达即停。

真实 API/Key/presence/bridge、实际预算 claim 均0；新配置仍disabled、CLI仍仅离线计划。
M6-009 IN_PROGRESS，M6-010 BLOCKED，exact-run NOT_EXECUTABLE；继续同一 R2 Draft
cross-owner review，不代填具名接受/TaskDONE/merge。M5/A4/Pilot/科研和发布权威独立。
用户累计成功/失败 input+output≤10,000,000，精确 Flash、每次北京18+且官方闲时；
unknown 金额非阻断，unknown token 保留预占并停止。完整运行消费、唯一 claim、dated
context/window、报告目标和具名接受仍是后继具体工作，不把本切片当全目标完成。
