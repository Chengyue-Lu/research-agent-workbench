# 实现接口导航

本页说明哪个文件定义接口和验证边界。当前实现成熟度见 [STATUS](../STATUS.md)，exact Task 定义、依赖及状态见
[TASKS](../TASKS.md)；接口文档存在、Schema PASS 与真实 API/科研验收分别判断。

## 按产物与消费者查找

| 责任域 | 接口说明 | 主要产物/消费者 |
|---|---|---|
| 问题与方法 | [Protocol Profile](PROTOCOL_PROFILE_CONTRACT.md)、[Mode Action](MODE_ACTION_CONTRACT.md)、[Method Resolution](METHOD_RESOLUTION_CONTRACT.md)、[Decision Authority](DECISION_AUTHORITY.md) | Task/Mode → Method 决策与能力需求；不绑定供应商 |
| 能力需求与供给 | [Requirement](CAPABILITY_REQUIREMENT_CONTRACT.md)、[Resolution/Snapshot](CAPABILITY_RESOLUTION_CONTRACT.md) | 显式 Report 比较、唯一选择、冻结 Snapshot → Runtime |
| 冻结执行 | [Bundle](RUNTIME_BUNDLE_PROFILE.md)、[View](RESOLVED_EXECUTION_VIEW.md)、[Thin Host](THIN_EXECUTION_HOST.md) | 完整输入闭包 → effective constraints → 单个预绑定 Driver 的 actual facts |
| 执行交接证据 | [Trace Core](TRACE_CORE.md)、[Trace Adapter](EXECUTION_TRACE_ADAPTER.md)、[generic closeout](GENERIC_EXECUTION_CLOSEOUT.md)、[Skill closeout](SKILL_EXECUTION_CLOSEOUT.md) | 实际事件/输出/检查 → 可独立文件重放的 slice Receipt |
| Provider/API Adapter | [端口、配置与会话边界](PROVIDER_ADAPTER_PLAN.md) | 显式 ModelRequest → ModelResponse/usage；是可选 Driver building block |
| 材料与科学对象 | [Source admission](SOURCE_ADMISSION_CONTRACT.md)、[artifact promotion](ARTIFACT_PROMOTION_CONTRACT.md)、[Claim localization](CLAIM_TRACE_CONTRACT.md) | 合格材料/确切验证产物 → 有定位的 Evidence/Claim 关系 |
| 研究状态 | [State composition](RESEARCH_STATE_CANDIDATE_CONTRACT.md)、[Attempt/Failure](RESEARCH_ATTEMPT_FAILURE_CONTRACT.md)、[Method Trace](METHOD_TRACE_CANDIDATE_CONTRACT.md)、[bounded Gate](PHASE_C_BOUNDED_GATE.md) | 显式对象闭包与引用；Human/R2 semantic closeout 独立 |
| Skill 维护者外环 | [Need](SKILL_NEED_CONTRACT.md)、[candidate pipeline](SKILL_CANDIDATE_PIPELINE.md)、[evaluation](SKILL_EVALUATION_PROTOCOL.md)、[lifecycle](SKILL_LIFECYCLE_V2.md)、[Release Projection](SKILL_RELEASE_PROJECTION.md) | Need → 评价/具名准入 → immutable release/projection；普通 no-Skill 执行不依赖此环 |
| 系统评价 | [Manifest](EVALUATION_MANIFEST_CONTRACT.md)、[Protocol](SYSTEM_EVALUATION_PROTOCOL.md)、[Harness](SYSTEM_EVALUATION_HARNESS.md) | 冻结计划/资格 → 运行证据 → 盲审/分析；与通用桥接测试分开 |
| 包、项目与发布 | [scaffold](PROJECT_SCAFFOLD.md)、[Runtime resources](RUNTIME_RESOURCES.md)、[release surface](RELEASE_SURFACE.md) | 显式 root、安装资源和确定性发行闭包 |
| 验证 | [测试与证据策略](TESTING_STRATEGY.md)、[Phase B Gate](PHASE_B_EVOLUTION_GATE.md) | 结构/边界、集成消费、live 与科研评价逐级证明 |

## 兼容与证据入口

[Mode 迁移](RESEARCH_MODE_MIGRATION.md)及旧 Assignment/Receipt 的适用条件统一从
[兼容性](../compatibility/README.md)进入。旧 [总体计划](IMPLEMENTATION_PLAN.md)、
[迁移计划](MIGRATION_PLAN.md)和 [仓库布局](REPOSITORY_LAYOUT.md)仅为历史输入，不承担当前规划。

需要 exact 接受/失败原件时，从 [STATUS](../STATUS.md) 或对应 Task 的来源链接进入 workstream；
[历史索引](../history/README.md)保留迁移与重大决定。普通入口的接口接合不改变 Mode/方法语义、
Skill admission、科学主张、人类接受或自动恢复的权威边界。
