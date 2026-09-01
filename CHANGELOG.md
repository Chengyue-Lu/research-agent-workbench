# Changelog

## 2026-09-05 — M14 curated release task-definition

- 依据 Issue #57 与 ADR-0021，将 M14 从 namespace reservation 转为正式 Product / Release Closure family，
  并以 M14-001～005 映射 release governance、deterministic surface、portable package、public docs 与首次发行；
- 固定 frozen `develop` 内容来源、exact current `main` Git 父提交、generated `release/v*` 与 curated `main`
  的目标拓扑，同时声明 M14-005 readiness/cutover 验收前现有发布规则仍有效且新 release path 必须 fail closed；
- 首个合法实现入口仅为 M14-001。许可证、scaffold、远端 GitHub protection、public/package closure 与
  exact release evidence 继续阻断 M14-005，本次文档不实现 exporter、package migration 或真实发行。

## 2026-09-02 — Phase D dual-transport entry decision（本 R2 PR 合入时生效）

- 本 R2 PR 合入时接受 ADR-0020：A1/A2 使用 M6 isolated session，A3/A4 使用 M11，并把 `A4 − A2` 固定为明确包含
  transport difference 的 primary system-level estimand；A2/A3 structural→runtime binding 由 shared
  `ArmExecutionQualificationRecord` 闭合；`A4 − A3` 只有在 pairwise exact-equality 证明唯一 Skill delta 时才作
  conditional increment，否则降级为 bundled/package effect 或 unavailable；
- 同一次合入关闭 `M5-BASELINE-TRANSPORT-ARCHITECTURE-GATE` 并将 M5-006 解锁为 READY，同时新增 Execution-owned
  M6-008（PARKED until M5-006 freezes the shared contract），后续负责 A1/A2 treatment-visible input、actual facts
  与 replay-valid closeout；Decision 本身不冒充实现；
- M5-007 继续等待 M5-006、M6-008 与 Skill-bearing replay Gate；M5-003、M11 authority、真实案例/live
  Provider/Human Gate 与 Topic 5 均未被改写或提前解冻。

## 2026-08-31 — M4-002 fail-closed artifact promotion

- 新增 `promotion_record`、accepted promotion validation policy、deterministic validation execution、
  durable Promotion Receipt、`rwb promotion validate|execute` 与独立 validator/executor，完整闭合
  Task/Attempt、checker/runner、report、subject、entry 和 live-byte pins；
- promotion 仅接受 file-bound record，采用 staging、commit-time revalidation 和 exclusive-create 同批发布
  目标/receipt，拒绝仅靠 work 内自签 PASS、额外未受检工件、accepted 直达、覆盖、路径逃逸与竞态，
  并保留 work、archive 和负结果 disposition；
- M4-002 完成不产生 Claim acceptance、Human Decision、publication 或 scientific correctness；
  M4-003/004 只因依赖满足而激活，仍须独立实现和验收。

## 2026-08-30 — Phase C、Source Admission 与 Evaluation 基线

- 接受 M10-001、M10-002、M3-009 与 M10-003 的 bounded candidate chain：durable Research State、
  Research Attempt/Failure、ref-only Method Trace 与 fresh-process Phase C machine Gate 已进入 `develop`；
  Human semantic review、R2/Phase C closeout 与 Topic 5 authority 继续独立且仍未完成；
- 接受 M4-001 Source Admission：`sources/inbox` 保持 mutable/untrusted/non-referenceable，`sources/raw`
  必须绑定 exact provenance sidecar 与 live-byte hash；promotion、Claim trace、Run reproduction、来源科学
  质量和许可法律判断均不在本层；
- 接受 M5-003 canonical four-arm Evaluation Manifest 与 non-executing baseline plan；它冻结可比条件，
  但没有执行真实案例，也没有证明 Mode、Method 或 Skill 的净收益。

## 2026-08-29 — TEST-QUALITY-001 / Coverage Policy v2

- 将 Python 3.11/3.13 behavioral compatibility、Python 3.11 coverage-quality、package-smoke 与 governance
  拆为职责独立但能传播到既有 required-check identity 的 Gate；
- 全包 global line floor 固定为 90%，authority-sensitive critical modules 逐文件固定为 line 95% / branch
  90%，并要求互斥的 positive/negative acceptance evidence、exact exclusion 对账和 canonical test identity；
- Coverage checker 自身进入 critical inventory；重型 behavioral E2E 仍完整保留在双 Python full suite，
  没有通过删测试、降低阈值或修改产品契约换取绿灯。

## 2026-08-27 — PR #45 R2 contract remediation

- 将 M11 Runtime Core 明确限定为 exact Action/Capability execution slice：manifest 同时公开完整 Task demand 与 singleton closed set，阻断 unresolved capability 下的 whole-Task completion；
- `satisfied` Capability Resolution 现在要求唯一 eligible candidate；View 的 Tool allowlist 只约束真实 Tool Supply，并在最终 policy intersection 后验证 selected Supply 仍可运行；
- Thin Host 改用 Host-owned/injected trusted clock，分离 requested 与 actual binding；Generic Receipt 对 completed、post-call failed、preflight blocked 作端到端 status-aware replay，并将 completion claim 收窄为 slice-only；
- Runtime Bundle 仅接受 `Method Resolution.resolution_status=proceed`，校验 Task capability set 等于 Method Action requirement union，并永久固定 `task_completion=false`；
- Host 的 elapsed 与 `max_seconds` enforcement 改取 trusted clock end-start，Driver 低报耗时不能绕过预算；
- post-call Trace 新增 typed、hash-pinned actual execution fact，Generic Receipt replay 独立闭合 Provider/Adapter/Model/Runtime/Host 与 actual Supply；缺失或漂移事实不具备 Receipt eligibility；

本文件只记录被主线接受、会影响使用者理解的基线变化。逐任务、分支和实验过程保存在[详细开发日志](DEVELOPMENT_HISTORY.md)。

## 2026-08-26 — M-series implementation vocabulary normalization

- 将 `TASKS.md` 固定为 Task status、hard dependency、owner、scope 与 implementation scheduling 的唯一真值，ROADMAP 只保留 Phase/Topic/Gate 聚合；
- 对 develop 中 M0～M10 的 79 个 Task 做全量审计，修正 M3/M4/M5/M6/M10 的长期或依赖不一致状态，同时保持 DONE 行与历史 ID 不变；
- 将 M6-003 的未来 Runtime umbrella 拆为 M11-001～006：Core 的 Bundle→View→Host→Trace/Receipt 与 optional Skill supply projection/mapping 两条不互相阻塞的路径，并按一 dependency layer 一 PR 验收；
- 明确 Topic 5 仍冻结，Phase C chain 只是 Topic 5 activation prerequisite 而非 membership；M11 thin execution 也不属于 Topic 5，Skill mapping 保留在统一 View/Capability 语义，Task 拆分不授予 Runtime fallback、Supply selection、Method、Claim、Gate 或 Recovery authority；
- 固定 Phase/Topic/M-group/M Task 四层词汇，新增由 TASKS 派生的 M-series-only 施工图，并将 M12 Continuity/Recovery、M13 Strategy/Evolution、M14 Product/Release 仅登记为无状态、无原子 Task、无 implementation authority 的 future namespace reservation。

## 2026-08-24 — Phase B evolution contracts

- 将 Skill Need 与 actual trial/evaluation result 分离，并建立 intake、evaluation、Human admission、runtime eligibility 与 lifecycle disposition 正交的 lifecycle v2；
- 增加有界 Protocol Profile，以及 Requirement→Supply Report→Resolution→Snapshot 的 provider-neutral 供给缝；
- 保留 no-Skill/direct Tool Core，使完整 Skill lifecycle 不阻塞 Snapshot；Skill Supply 仅在 exact runtime eligibility 成立时可绑定；
- 新增 hash-bound Phase B Gate，证明 Supply A→B 不修改 Task/Mode/Action/Method/Requirement，不放宽 permission/data-egress/side-effect，也不赋予 Runtime Method authority；
- 保持 Runtime/API、Method Trace、Recovery、fallback、routing 与多 Agent 编排在本阶段范围之外。

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
