# M6-009 显式驱动绑定与报告复核

2026-10-03；延续 Draft PR128，base develop27cbf860；Provider/Session 责任人黄毅，
路诚钺协调共享语义。Agent Profile：bounded Provider integration；Required Skills：[]；R2。
沿用已接受 [定义计划](../../../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md) 的产品写域。

读集：AGENTS/README/docs 导航及 Development、上述 PLAN、Provider/配置/codec/conformance/
source binding、直接 Schema/tests/fixtures/CI/build 消费者。保持 filename/import metadata 扩展方式。
写域：profile_conformance、profile_conformance_report、直接报告 Schema、测试和 CI 登记、本工作流。
不修改 Port/Resolver/Skill/M5/M11/Research State 或 release policy。

互斥委派：设计 reviewer 15min 只读及本地 handoff；report owner25min仅 writer/report Schema/
直接 reporting tests；root串行驱动、独立消费测试、旧安装路径回归及整合。发现公开语义/运行时
所有权变化、代码所有权重叠、意外 Key/presence/bridge/API 访问、无界执行或 unresolved ambiguity 即停。

显式 binding_manifest_ref 需要 v3 manifest、conformance source roots、固定 body policy 与实际
UrllibTransport。Attempt 前匹配 actual Provider；caller guard 返回后重验 graph/config，再进入
credential/intent 边界。报告 1.1 消费冻结 manifest/config/graph/source refs 及政策/actual Attempt ordinal。
独立 cold reader 只解析/compile 归档 source，不执行归档代码；旧报告1.0与默认None保留。
native/compiler/dependency、callback全局/closure、Windows和remote authority仍是明确边界。

保留失败、可见委派/结果及 exact-source checks；完整平台 transcript导出不可得，capture gap如实保留，
不记录密钥或隐藏思考。原head组件安装路径ERROR不改标；修复和新head CI另留证据。

用户实际成功/失败 input+output 累计≤10,000,000，精确 Flash、每次北京18+且官方闲时。
金额unknown非阻断，tokenunknown held-stop；每Attempt最多3call/1pureTool/256output/120秒，
无auto retry/fallback。当前仅合成离线；真实API/Key/presence/bridge0。
M6-009 IN_PROGRESS、M6-010 BLOCKED，NOT_EXECUTABLE；同一R2 Draft待cross-owner接受，
不代填具名Task/运行接受、不ready/merge，不扩展Pilot/A4/科研/发布。
