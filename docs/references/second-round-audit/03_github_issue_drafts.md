# Research Agent Workbench — GitHub Issue 草案

> 用途：将第二轮架构审计结果拆成可直接创建的 GitHub Issues。
> 本文件不代表必须一次性全部实施；建议先创建 P0/P1，P2 保持 backlog。
> 标签名称可按仓库现有规范调整。

---

# P0 — 先让 PR11 成为正式 Core

## Issue 1 — Formalize Mode Action as a first-class contract

**Suggested labels:** `architecture`, `mode`, `schema`, `P0`

### Problem

PR11 已经以 Mode Action Catalog 驱动 Method Need，但 Action 目前主要存在于设计文档/fixture 中，尚未成为正式 schema 与 registry 对象。

### Goal

建立版本化、可验证、可引用的 `Mode Action` contract。

### Scope

- 新增 Mode Action schema；
- 为 `evidence-synthesis` 与 `simulation` 建立正式 Action documents；
- 明确 trigger/non-trigger、failure modes、artifact、claim effect、human gate、stop/blocked conditions；
- routing fixture 使用 action stable ID，而不是自由文本。

### Acceptance criteria

- 两个正式 Mode 的现有 Action Catalog 能无损映射到正式文档；
- `rwb validate` 能验证 Mode→Action 关系；
- Action version/hash 可被 Method Resolution 引用；
- 旧设计文档不再是唯一事实源。

### Out of scope

- 新增更多正式 Mode；
- 新增 Skill 实现；
- Runtime/API 改造。

---

## Issue 2 — Introduce a versioned Method Resolution contract

**Suggested labels:** `architecture`, `method`, `schema`, `P0`

### Problem

当前 Task 可以声明 Mode/Skill/Capability，但缺少一个正式对象解释：为什么此 Task 需要这些 Action，以及为什么选择 Skill/Tool/Task/Human/Blocked 中的某种机制。

### Goal

新增 `Method Resolution`，成为 PR11 核心决策的机器可读结果。

### Required fields

- task reference；
- primary/combined/no-new Mode resolution；
- selected Action IDs；
- method obligations；
- mechanism decisions；
- Skill Need references；
- Human Gates；
- blocked conditions；
- rejected alternatives / ambiguity；
- resolution status。

### Acceptance criteria

- 至少 8 个现有 routing fixture 能转换成正式 Method Resolution；
- Method Resolution 不包含 Provider/Model-specific 字段；
- 可以独立 hash / validate / archive；
- no-Skill、tool-only、Human Gate、blocked 均有正式表示。

### Dependencies

- Issue 1。

---

## Issue 3 — Remove legacy Mode-to-Skill recommendation coupling

**Suggested labels:** `architecture`, `mode`, `skill`, `breaking-change`, `P0`

### Problem

当前 Research Mode schema 仍要求 `recommended_skill_capabilities`，与 ADR-0013 的 Mode-first / Need-first 原则存在语义冲突。

### Goal

Research Mode v0.2 不再直接推荐 Skill；Skill Requirement 只能由 Action → Method Resolution → Skill Need 派生。

### Acceptance criteria

- `research-mode` 新版本不强制 `recommended_skill_capabilities`；
- evidence-synthesis / simulation 完成迁移；
- 历史 Mode v0.1 仍可读取/验证；
- 新 Task 不允许通过 Mode 名称隐式加载 Skill bundle。

### Dependencies

- Issue 1；
- Issue 2；
- migration baseline（Issue 7 可随后补齐完整框架）。

---

## Issue 4 — Define decision authority for Mode, Action, Skill, Tool and Claim promotion

**Suggested labels:** `architecture`, `governance`, `human-gate`, `P0`

### Problem

当前设计已区分 Agent、Resolver、Human Gate，但哪些决策可以自动做、哪些必须校验/人工批准尚未形成统一 contract。

### Goal

建立 `Decision Authority Matrix`，并映射到 validation / runtime preflight。

### Acceptance criteria

- 明确 Mode suggestion / Action selection / mechanism / Skill selection / Tool fallback / Claim promotion / permission relaxation 的决策权；
- 不允许 LLM 静默放宽 source/data/permission boundary；
- ambiguity 可明确返回 Human Gate / split / blocked；
- fixtures 覆盖至少一个 agent proposal 被 deterministic/human gate 拒绝的案例。

---

# P1 — 建立长期可演化基础设施

## Issue 5 — Formalize Skill Need and evaluation evidence

**Suggested labels:** `skill`, `evaluation`, `schema`, `P1`

### Goal

将 Skill Need 从文档约定升级为版本化 contract，并允许绑定 trial/evaluation evidence。

### Acceptance criteria

- Need 包含 trigger/non-trigger、semantic gap、no-Skill/direct-tool baseline、expected increment；
- candidate Skill 必须引用 Need；
- accepted/promotion 必须能引用 evaluation evidence；
- 一个 Need 可对应多个 Skill candidate；
- 无候选时保持 capability/method gap，不自动生成 accepted Skill。

---

## Issue 6 — Add evaluation-driven Skill lifecycle

**Suggested labels:** `skill`, `lifecycle`, `evaluation`, `P1`

### Goal

将 Skill lifecycle 扩展为：

`discovered → audited → candidate → trial → accepted → active → superseded → deprecated → retired`

### Acceptance criteria

- promotion/supersession 需要可验证 evidence；
- evaluation record 固定 Need、Task suite、Host、Model、Tool snapshot、baseline、metrics；
- 支持 no-Skill baseline；
- historical assignment 仍按旧 hash/version 重放。

### Dependencies

- Issue 5；
- Issue 11（evaluation harness，可先定义 schema 后实现 harness）。

---

## Issue 7 — Introduce schema and semantic migration framework

**Suggested labels:** `migration`, `schema`, `compatibility`, `P1`

### Problem

长期 Research State / Mode / Method contracts 会不可避免地演化，仅有 version 不能保证旧研究可继续解释。

### Goal

建立 explicit migration chain。

### Acceptance criteria

- migration 记录 from/to version、original/new hash、migration implementation version；
- migration 不覆盖原文档；
- 至少演示 Research Mode v0.1 → v0.2；
- validator 可区分 native document 与 migrated representation；
- migration 可复现。

---

## Issue 8 — Add Protocol Profile / Method Standard as a separate layer

**Suggested labels:** `architecture`, `protocol`, `method`, `P1`

### Goal

表达 PRISMA、V&V guideline、领域标准、project-specific methodology，而不污染 Mode 或 Skill。

### Acceptance criteria

- `Mode != Protocol != Skill` 在 schema 与 resolver 中成立；
- 一个 Task 可引用 Mode + zero/multiple approved Protocol Profiles；
- Protocol 能增加 artifact/gate/check obligations，但不能静默放宽 Mode；
- 提供至少一个 evidence-synthesis 协议 fixture 和一个 simulation 协议 fixture。

---

## Issue 9 — Introduce provider-neutral Capability Requirement and frozen Capability Snapshot

**Suggested labels:** `capability`, `tool`, `resolver`, `P1`

### Goal

让 Method Plane 请求能力，而不是指定厂商 Tool；执行前解析成冻结 capability snapshot。

### Acceptance criteria

- requirement 可表达 permission / data egress / side effects / version constraints；
- snapshot 记录 exact provider/adapter/version/hash；
- unavailable capability 返回 gap/blocked，不静默 fallback；
- ToolUniverse / MCP / local CLI 等都可以作为未来 provider 类型而不改变上层 schema。

---

# P1/P2 — 建立长期 Research State 与 Verification

## Issue 10 — Define Research State / Frontier primitives

**Suggested labels:** `research-state`, `memory`, `architecture`, `P1`

### Goal

建立与 Runtime/session 解耦的长期研究状态。

### Initial primitives

- Question；
- Evidence；
- Claim；
- Unknown；
- Contradiction；
- Assumption；
- Decision；
- Attempt；
- Failure；
- Frontier item。

### Acceptance criteria

- State 可仅凭 files/schema 恢复；
- 不依赖特定 Python object / Agent conversation；
- Failure 可记录 revisit condition；
- Main Agent 默认可读取 compact index，而非全量 history；
- 一个新 runtime 可从 frozen state 构建下一 Atomic Task。

---

## Issue 11 — Build Method-aware Trace Envelope (M3-008 alignment)

**Suggested labels:** `trace`, `verification`, `M3`, `P1`

### Goal

Trace 不只记录 API/tool execution，还解释科研方法决策。

### Required semantic events

- mode proposed/resolved；
- action selected；
- mechanism selected；
- Skill candidate rejected/selected；
- capability resolved；
- Human Gate requested/decided；
- Evidence changed；
- Claim promoted/rejected；
- safe pause / blocked；
- Attempt failure / reopen condition。

### Acceptance criteria

- reviewer 可从 Trace 回答“为什么使用此机制”；
- Execution Trace 与 Method Trace 可关联但分层；
- schema 支持 secret-safe / sensitive-data policy；
- 为 PR10 类 Runtime 定义消费接口，而不是让 runtime 自定义共享 Trace 语义。

---

## Issue 12 — Define Evidence composition and Claim admissibility rules

**Suggested labels:** `evidence`, `claim`, `method`, `P1`

### Problem

多 Mode 组合不能长期依赖“取更严格 ceiling”这一简单规则。

### Goal

基于 Evidence provenance + relation + composition rule 判断 Claim admissibility。

### Acceptance criteria

- Evidence 记录 produced_under / source / method provenance；
- Claim relation 至少支持 support / contradict / qualify / unknown；
- 能表达 simulation + experiment 的联合证据而不是简单 ceiling intersection；
- deterministic validator 不将结构 PASS 等同于 scientific correctness；
- high-risk promotion 可要求 Human Gate。

---

# P2 — 进化与策略层

## Issue 13 — Add Research Strategy as a replaceable execution policy

**Suggested labels:** `strategy`, `orchestration`, `P2`

### Goal

支持 direct / plan-act-reflect / tree-search / tournament / parallel-review 等策略，而不改变 Mode。

### Acceptance criteria

- `Mode != Strategy`；
- Method Resolution 可建议/约束 Strategy，但不硬编码 Host；
- Strategy 有 budget / termination / interaction policy；
- simple/direct 必须始终作为 baseline。

### Out of scope

- 第一版不需要实现多种复杂 strategy；先冻结 interface。

---

## Issue 14 — Build controlled baseline/evaluation harness for Method and Skill changes

**Suggested labels:** `evaluation`, `benchmark`, `P1`

### Goal

任何复杂度提升都要证明增量价值。

### Baselines

1. Plain Agent；
2. Plain Agent + Tool；
3. Mode + no-Skill/direct-tool；
4. Mode + candidate Skill。

### Suggested metrics

- method violation rate；
- claim overreach；
- provenance error；
- counterevidence omission；
- human correction distance；
- rework rate；
- tool errors；
- context tokens；
- cost；
- completion time。

### Acceptance criteria

- Evaluation Manifest 冻结 model/host/tool snapshot/budget；
- 支持 task-level/stepwise scoring；
- Skill promotion 可直接引用 evaluation result；
- 没有显著增量时允许保留 no-Skill。

---

## Issue 15 — Define governed evolution pipeline for external Skills / Tools / Methods

**Suggested labels:** `evolution`, `registry`, `security`, `P2`

### Goal

支持未来从外部 repo/paper/skill ecosystem 自动发现候选，但禁止自动进入正式科研路径。

### Pipeline

`discover → source audit → candidate → sandbox trial → evaluation → shadow use → human review → versioned promotion`

### Acceptance criteria

- discovery 不等于 admission；
- source/license/security/provenance 必须保存；
- candidate 可由 Paper2Agent/SkillFoundry 类工具自动生成；
- promotion 必须保留完整 evidence chain。

---

# P2 — Runtime 收敛

## Issue 16 — Rebase execution/runtime work onto frozen Method + Trace contracts

**Suggested labels:** `runtime`, `execution`, `integration`, `P2`

### Context

PR10 已验证大量 API execution / live closure 能力，但与 PR11 合并后暴露共享契约、hash-derived fixture、state/predecessor、marker/provenance 等冲突。

### Goal

在 Method Resolution / Trace contract 稳定后重新接入 execution plane。

### Acceptance criteria

- execution 只消费 frozen Task/Method/Capability contracts；
- execution 不定义 Mode/Claim/Skill fallback；
- from-state / predecessor / completion marker / provenance 均按当前 review blocker 修复；
- Method Trace 与 Runtime Receipt 自动关联；
- post-main fixtures 完整再生；
- clean CI。

### Dependencies

- Issue 2；
- Issue 9；
- Issue 11；
- PR10 review blockers resolved。

---

# 建议创建顺序

第一批建议真正创建：

1. Mode Action contract；
2. Method Resolution；
3. Remove Mode-to-Skill coupling；
4. Decision Authority Matrix；
5. Skill Need contract；
11. Method-aware Trace；
14. Evaluation harness。

第二批在上面稳定后创建：

6–10、12。

第三批保持 backlog：

13、15、16。
