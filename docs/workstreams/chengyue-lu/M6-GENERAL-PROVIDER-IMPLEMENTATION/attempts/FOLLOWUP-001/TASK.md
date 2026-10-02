# M6-009 后续离线切片

Profile：Provider conformance integrator；Required Skills：[]；风险 R2。
Provider/Session owner：黄毅；协调与共享语义复核：路诚钺。
起点：已接受 develop `27cbf860e48e9639bd3af32a58c12bfd88d87526`，PR127 仅接受离线基础。
用户允许继续修复摘要异常并补齐驱动和报告。任务状态仍为 M6-009 IN_PROGRESS、M6-010 BLOCKED。

读集：AGENTS/README/docs导航、DEVELOPMENT、M6-009/010、已接受定义计划，
Provider/Session/配置/绑定/codec/journal及其直接测试、Schema、CLI、Runtime资源/构建/组件消费者，
本workstream与已冻结非秘密准备包。没有凭据原文、环境presence或无关研究材料读取。

互斥写域：Session owner仅显式Session函数及直接测试；driver owner仅新profile驱动/transport与测试；
catalog owner仅资源清单、typed kinds/manifest Schema和直接测试；root串行整合CLI、报告Schema/writer、
组件映射及本workstream。Root在owner结束后可做LF字节规范化，保留前后hash与AST等价证明。
不修改旧Port/facades/default Session、M5/M11/Resolver/Skill、Task定义/依赖/完成状态。

整合时核验 actual develop 的 source CI 37022594303，发现旧 consumer diagnostic
测试错误要求历史 source pins 永久匹配当前源码。追加唯一写域
tests/test_ci_consumer_contracts.py：保留政策和历史 pins，仅验证版本、诊断无执行权与
实际 consumer 的字节漂移可见；不得重写历史接受记录或降低运行接受义务。

实施：四个其余摘要阶段统一有界停止；固定至多三次synthetic调用完成一次add_ints(3,4)→
第二轮none-choice精确文本7→独立enum Schema和本地业务断言；复用持久Journal预占、intent、
委托transport入口观测及已知失败token结算，unknown保留预占停止；打包原disabled模板与profile。
报告version1.0.0与旧报告独立，闭集且排他新建；CLI只输出离线计划。

预算：Session25min、catalog25min、driver35min；独立复核先20min，再有界复核冻结driver/catalog。
Root可在本worktree忽略目录新建环境安装当前wheel，做适用组件/资源/报告/治理检查。
子代理0安装/网络/ProviderAPI/真实Key/presence/bridge/Git mutation；root也不执行真实Provider调用。
没有自动retry/fallback，不把执行计划数值当用户逐项批准。

本切片不认证完整source/helper/runtime闭包、官方计费input上界、唯一预算文件/namespace及Windows运行资格。
guard是调用者声明，transport entry不是socket证据，live_qualified/remote_strict_claim保持false。
真实执行仍需完整M6-009接受与M6-010 exact-run gate。用户累计成功/失败输入＋输出≤10,000,000，
仅Flash、每次北京时间18:00后且官方闲时；unknown金额不阻断，unknown token预占并停。
R2 draft PR请求cross-owner review，不继承PR127批准、不自行merge或替具名owner置DONE。

输出：可重现代码、原失败、冻结hash、独立检查、源版本绑定的CHECKS与Compact Handoff。
委派dispatch与可见消息/receipt保存在隔离worktree的忽略目录；完整平台事件未导出，capture gap如实保留。
