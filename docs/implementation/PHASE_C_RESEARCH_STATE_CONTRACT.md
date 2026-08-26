# Phase C Research State Contract (M10-001..003, M3-009)

状态：Active implementation contract（bounded candidate，最终表示待 R2 接受）

更新：2026-08-26

## 1. 目的与边界

按 Issue #38（R2 ACCEPT）与 PR #40 的 bounded 任务定义实现跨 Runtime 可复用的最小科研语义：

- **exact-ref Research State**（M10-001）：compact composition，只存 exact ref/revision/
  可选 sha256 pin 与 disposition，不复制被引用正文；
- **Attempt / Research Failure**（M10-002）：与 execution failure 分离的研究失败语义；
- **Human Decision Record**（M10 切片）：provenance-bearing 的具名人类决定，与
  Authority Rule Eligibility（"假设事实成立时的资格"）严格分离；
- **Method Trace v0.1**（M3-009）：ref-only 的"科研/控制状态为何变化"事件账本，与
  Execution Trace（"发生了什么操作"）分层；
- **两个 bounded behavioral Gate**（M10-003）：staged 新进程 fresh actor 只读 compact
  State + Method Trace + 约定路径被引用文件即可重建关键决定、并回避已知失败路径。

本契约是 **bounded candidate**：Unknown/Assumption 为 State 内轻量 item、Contradiction
为既有 Evidence–Claim 关系的表达、Frontier 为 derived projection（本版未实现独立对象）。
这些表示假设须由两个 bounded case、反例和 R2 review 证明为足够弱表示后才进入 accepted
architecture；不预冻结最终 Schema，不改写既有 `research-object`/`claim`/`decision`
的 Schema identity。

## 2. 契约内容

### 2.1 research_state（`schemas/v0.1.0/research-state.schema.json`）

- `state_id` + `revision` + `status: active|superseded`；`supersedes` 指向**同 state_id
  的更早 revision**（closure 校验强制 lineage 单调递增）；
- `entries[]`：`role`（question/hypothesis/evidence/claim/decision/run/task/failure/
  human-decision）+ exact `ref`（objectRef：object_id@revision + 可选 sha256 pin）+
  `disposition: current|superseded`。closure 校验：ref 必须可解析、pin 必须与目标
  声明的 `content_hash` 一致（沿用 kernel 对象内容 pin 语义）、标记 current 的条目
  不得已被更高 revision 取代（staleness 检查）；
- `open_items[]`：`kind: unknown|assumption` 轻量 item；`invalidated` 状态强制
  `provenance_refs`；
- `revisit_refs[]`：只能指向 research_failure。

State lineage 与 Attempt lineage 分离：多个 Attempt 可共享同一 State revision；State
可因 Evidence/Human Decision 在没有 Attempt transition 时演化（本契约不建 Attempt
对象，from-State 引用由 failure 承载）。

### 2.2 research_failure（`research-failure.schema.json`）

- 必填 `learned_result` 与 `revisit_condition`（universal minimum）；可选
  `observed_result`/`remaining_uncertainty`/`execution_outcome`（bounded profile
  candidate：execution-succeeded | execution-failed | not-recorded）；
- `execution_outcome: execution-succeeded` + 存在的研究失败 = "仿真成功但假设被否定"
  的显式表达——execution failure 与 research failure 分离；
- `from_state_ref` / `source_attempt_ref` / `evidence_refs` /
  `invalidated_assumption_refs` 全部 exact-ref；
- revisit condition 是记录性的：condition 变化只使路径**可复审**（reviewable），
  不产生任何自动重跑（gate 行为锁定）。

### 2.3 human_decision_record（`human-decision-record.schema.json`）

- 具名 `actor` + `decision_kind`（accept-evidence/qualify-claim/record-failure/
  close-unknown/reopen-review/other）+ `authority_basis`（政策依据声明）+
  `subject_refs` + `asserted_fact_refs` + `state_effect_ref`（必须指向 research_state）
  + `decided_at` + `rationale`；可选 `decision_object_ref` 指向既有 kernel `Decision`
  research_object 以复用而非平行重建；
- 它记录"决定已发生及其 provenance"；不授予 permission、不提升 Claim、不代替
  Authority Rule Eligibility 的假设性资格判断。

### 2.4 method_trace（`method-trace.schema.json`）

- `subject_state_ref`（必须指向 research_state）+ append-only `events[]`（sequence
  从 1 连续，closure 校验强制）；
- event `family` 闭集与必备 ref：method-resolution-applied→method_resolution_ref、
  execution-fact-recorded→execution_ref（缺失即报"record an explicit gap instead of
  inventing the fact"）、human-decision-applied→decision_ref、research-state-changed→
  state_after_ref、failure-rationale-recorded→failure_ref、reopen-reviewable→failure_ref；
- 全 ref-only，不复制 Method Resolution/Snapshot/Evidence/Claim 正文——与
  Execution Trace 的职责分层（M3-008 核心 api 复用，不扩张）。

### 2.5 校验与 CLI

- `rwb validate`：`_validate_phase_c_set` 对仓库内 Phase C 文档做 schema + closure
  交叉校验（`PHASE-C-CLOSURE-INVALID`）；
- `rwb research-state validate <doc>`：单文档 schema + 全仓索引 closure 检查；
- `rwb research-state gate --case <dir>`：staged 新进程运行 fresh actor，对照
  `oracle-expected.yaml.txt` 的 exact 断言与 forbidden_reads 断言（private oracle 只测
  fixture predicates，不证明 reviewer reconstruction 或科学正确性）。

## 3. Fresh actor 门纪律

- 定位 active State（states/ 下 status=active 的最高 revision）与其 active Method
  Trace；其余文件只经 exact ref 按约定路径打开（objects/ failures/ decisions/
  states/ tasks/），记录完整 `read_surface`；
- 永不读取 original-chat.md、oracle/、expected answer；oracle 断言
  forbidden_reads 强制这一点；
- ref pin 漂移、ref 不可解析、sequence 断裂等任何 closure 问题 → fail-closed
  （status=blocked），不猜测；
- 固定选择集规则：`choices.yaml.txt` 声明候选及其 `repeats_failure_ref`；revisit
  条件未满足 → known-failed-avoid（不推荐、不重跑）；满足 → reviewable（浮出供
  审查，仍不自动执行）；fresh actor 由此**回避已知失败路径**——这是 gate 的核心
  行为断言，不是新 Runtime authority。

## 4. 非目标

- 不建知识图谱/数据库/全局 DAG/策略引擎；
- 不实现 Runtime Bundle、Resolved Execution View、Provider binding、Topic 5 的
  Handoff/context/recovery（M11/M12 范围）；
- 不自动创建 Skill Need、不自动 Claim promotion、不自动 retry/reopen/replan；
- 不改 `research-object`/`claim`/`decision` 既有 Schema identity（candidate 使用
  显式新文档）；
- Gate PASS ≠ Phase C closeout：具名 Human semantic review 与 R2 closeout 独立进行
  （M10-003 验收原文）；本契约不构成 Topic 5 解冻。

## 5. 示例与测试

- 示例：`examples/phase-c/case-a-evidence-synthesis/`（证据综合正路：支持+反证+
  限定 Claim+人类限定决定+unknown 关闭）与 `examples/phase-c/case-b-simulation-negative/`
  （仿真负路：execution-succeeded + 研究失败 + 假设作废 + revisit + 三选一固定选择集）；
- 测试：`tests/test_phase_c.py`（28 项）——四文档 schema 正例、跨 lineage/非递增
  supersession、stale current、invalidated 无 provenance、revisit 非 failure、pin
  漂移、sequence 断裂、execution-fact 缺 ref（gap 提示）、悬空 decision ref、
  交叉校验捕获、fresh actor 双 case 行为（known-failed-avoid/reviewable/recommended、
  forbidden read 排除）、revisit 满足时 reviewable 而非推荐、actor 对破坏 pin
  fail-closed、staged 子进程 gate PASS、CLI gate 谓词失败。
