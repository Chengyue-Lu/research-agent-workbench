# Changelog

本文件只记录被主线接受、会影响使用者理解的基线变化。逐任务、分支和实验过程保存在[详细开发日志](DEVELOPMENT_HISTORY.md)。

## 2026-08-24 — Capability Requirement demand contract

- 将八个 Method Resolution 复用的四个 Capability Requirement 冻结为不可变需求侧契约；
- 用小型 path/hash 完整性索引闭合 Task→Method→Requirement 引用，同时保持 M8 工件原始字节不变；
- 显式拒绝 Provider/Model/Adapter、具体供给、availability/gap/blocked、fallback 与价格路由进入需求层；
- 将 Capability Requirement Schema、实现和发布身份纳入 R2 治理与 append-only 保护。

## 2026-08-22 — Documentation surface baseline

- 分离 stable、status、planning、compatibility 与 history 文档权威；
- 新增面向首次使用者的 no-Skill 离线 quickstart；
- 将当前实现覆盖集中到 `docs/STATUS.md`，把旧工件回放移至兼容性说明；
- 增加 ADR 与 implementation 导航，并为稳定表面加入防历史泄漏测试。

## 2026-08-21 — File-authoritative execution trace

- 接受 Execution / Archive Trace Core：版本化 Envelope、Index、append-only event 与工具结果闭集校验；
- 接受 legacy execution adapter，使既有 Assignment / Attempt 可写入并验证规范 Trace；
- 明确 Execution Trace 只记录可观察事实，Method 决策与科学正确性保持独立。

## 2026-08-20 — Method-aware control model

- 接受 Mode Action、Method Resolution、Research State、Decision Authority 和 Strategy / Evaluation 的五平面架构方向；
- no-Skill、direct-tool、Human Gate、split 与 blocked 成为一级解析结果；
- 路线图与实时任务状态分离。

## 2026-08-19 — Mode-first capability governance

- Skill 选择转为从 Mode Action 和可重复 Need 派生；
- 增加 Skill 生命周期与精确版本约束；
- 固定历史 Skill 包退出新任务默认路由的兼容边界。

## 2026-08-13 — Repository foundation

- 建立人类治理、文件优先、provider-neutral 的项目边界；
- 加入核心对象 Schema、CLI、示例、Registry 和确定性测试；
- 建立受限写入、显式 Skill 绑定、Handoff、连续性与薄 Adapter 决策。
