# 实现文档索引

这里说明“如何实现或验证一个已接受接口”。当前成熟度仍以 [`STATUS.md`](../STATUS.md) 为准，实时工作项仍以 [`TASKS.md`](../TASKS.md) 为准。

## Active implementation contracts

- [Mode Action contract and registry](MODE_ACTION_CONTRACT.md)
- [Method Resolution contract](METHOD_RESOLUTION_CONTRACT.md)
- [Capability Requirement demand contract](CAPABILITY_REQUIREMENT_CONTRACT.md)
- [Skill Need requirements contract](SKILL_NEED_CONTRACT.md)
- [Skill lifecycle v2](SKILL_LIFECYCLE_V2.md)
- [Protocol Profile contract](PROTOCOL_PROFILE_CONTRACT.md)
- [Capability Resolution and Snapshot Core](CAPABILITY_RESOLUTION_CONTRACT.md)
- [Phase B migration/replay/replacement Gate](PHASE_B_EVOLUTION_GATE.md)
- [Runtime Bundle / Consumer Profile](RUNTIME_BUNDLE_PROFILE.md)
- [Resolved Execution View Core](RESOLVED_EXECUTION_VIEW.md)
- [Thin Execution Host](THIN_EXECUTION_HOST.md)
- [Generic Execution Closeout and M11 Core Gate](GENERIC_EXECUTION_CLOSEOUT.md)
- [Research Mode v0.1 to v0.2 migration](RESEARCH_MODE_MIGRATION.md)
- [Decision Authority Matrix and Authority Rule Eligibility](DECISION_AUTHORITY.md)
- [Durable Research State composition candidate (M10-001)](RESEARCH_STATE_CANDIDATE_CONTRACT.md)
- [Research Attempt lineage and Research Failure candidate (M10-002)](RESEARCH_ATTEMPT_FAILURE_CONTRACT.md)
- [Ref-only Method Trace v0.1 candidate (M3-009)](METHOD_TRACE_CANDIDATE_CONTRACT.md)
- [Phase C runner-owned bounded Gate (M10-003)](PHASE_C_BOUNDED_GATE.md)
- [Accepted source admission implementation (M4-001)](SOURCE_ADMISSION_CONTRACT.md)
- [Accepted artifact promotion implementation (M4-002)](ARTIFACT_PROMOTION_CONTRACT.md)
- [Accepted Claim evidence localization implementation (M4-003)](CLAIM_TRACE_CONTRACT.md)
- [Accepted bounded Run reconstruction implementation and synthetic case (M4-004)](../workstreams/huangyi/M4-RUN-RECONSTRUCTION/README.md)
- [Deterministic release surface (M14-002)](RELEASE_SURFACE.md)
- [Portable Runtime resources (M14-003)](RUNTIME_RESOURCES.md)
- [Evaluation Manifest and non-executing plan contract (M5-003)](EVALUATION_MANIFEST_CONTRACT.md)
- [System-Level Evaluation Protocol (M5-006)](SYSTEM_EVALUATION_PROTOCOL.md)
- [Baseline A1/A2 transport candidate (M6-008)](../workstreams/huangyi/M6-BASELINE-EXECUTION/README.md)
- [File-authoritative Trace Core](TRACE_CORE.md)
- [Execution Trace Adapter](EXECUTION_TRACE_ADAPTER.md)
- [Provider Adapter plan and seam](PROVIDER_ADAPTER_PLAN.md)
- [Testing strategy](TESTING_STRATEGY.md)

M4 入口对应已接受的有界实现；各契约继续分别负责 source admission、promotion、Claim evidence
localization 与 synthetic Run reconstruction，不因此取得 Claim/Human acceptance 或科学正确性权威。

Evaluation 的 active implementation contracts 包括 M5-003 Manifest/check/non-executing plan，以及
M5-006 System-Level Evaluation Protocol、资格/overlap/overlay/pairwise 校验器。
[ADR-0020](../decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md) 已接受 Phase D dual transport
与 system-level estimand；M6-008 baseline envelope/closeout、Skill closeout replay Gate、M5-007 Harness
和真实案例/live/admission 仍由 [TASKS](../TASKS.md) 与 [ROADMAP](../ROADMAP.md) 跟踪。

## Evaluation and intake protocols

- [Skill evaluation protocol](SKILL_EVALUATION_PROTOCOL.md)
- [Skill candidate pipeline](SKILL_CANDIDATE_PIPELINE.md)

这些协议用于设计试验和候选入口，不代表候选已准入或证明有科学价值。

## Superseded planning records

- [旧总体实施计划](IMPLEMENTATION_PLAN.md)
- [旧迁移计划](MIGRATION_PLAN.md)
- [早期仓库布局](REPOSITORY_LAYOUT.md)

这些文件保留为历史输入，不承担当前架构、状态或规划权威。历史导航见[历史与审计](../history/README.md)。
