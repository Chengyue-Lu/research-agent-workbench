# 当前开发 Handoff

状态：`K-MS-0` 职责与文档基线已确立；下一节点为 `K-MS-1`

更新日期：2026-08-14

权威基线：`main`

这份文件用于让没有既往聊天上下文的人或 AI 直接恢复 Mode–Skill 工作流。旧聊天、平台线程和临时 transcript 都不是权威状态。

## 1. 当前分工

本侧只维护 Research Mode、Capability 词汇、Skill 发现/选择/评估/准入、Resolver 选择理由、受控读取、Handoff 成本策略和相关 fixtures/文档。

API Adapter、模型槽、API session、Task-to-API、live conformance 和 API 测试已经移交给独立 API Execution 工作流。本侧不得为了推进自己的节点而修改这些实现；共享 Task/Assignment/Handoff/Receipt 接口需要双方确认。

详细 owner 见 `docs/WORKSTREAM_OWNERSHIP.md`。

## 2. 最小恢复读取集

按顺序只读：

1. `AGENTS.md`；
2. `docs/WORKSTREAM_OWNERSHIP.md`；
3. `docs/decisions/0011-RISK-TIERED-HANDOFF-AND-CONTROLLED-READS.md`；
4. `docs/implementation/MODE_SKILL_WORKSTREAM_PLAN.md`；
5. `docs/TASKS.md` 的 M2/M7 和当前下一任务；
6. `docs/modules/02-PROTOCOL_AND_MODES.md` 与 `docs/modules/04-SKILL_SYSTEM.md`；
7. 只有接到具体 Task 后，才读取其目标 Mode、Skill、fixture 和直接依赖。

不要默认扫描全部 `docs/`、`examples/`、候选 Registry 或另一个 Agent 的工作目录。可以先查询文件名和元数据；确需正文时记录原因并扩展 Task 允许读取集。

## 3. 当前仓库事实

- 正式 Mode 只有 `evidence-synthesis` 和 `simulation`；其他模式名称目前只是候选分类。
- accepted Skills 只有 `literature-evidence-extraction`、`simulation-vv`、`handoff-integrity`。
- candidate Registry 共 24 项，其中 4 项 triage、2 项 discovered；只有 `claim-preserving-rewrite` 已形成隔离 candidate package。
- 现有 Skill 绑定、哈希、权限交集和离线 fixtures 可重放，但真实前向与 with/without 增量价值尚未证明。
- Handoff/Manifest/Audit/Receipt 全链已经可表达，但普通任务是否值得承担该成本尚未用真实运行验证。
- `K-API-1` 已进入仓库；后续 API 缺口由 API Execution 工作流维护。

## 4. 当前唯一节点：K-MS-1

目标：形成一条可解释的 Mode–Skill 选择基线，而不是增加更多空 Mode 或把更多 Skill 放进 Registry。

完成标准：

1. Mode trigger/non-trigger、组合冲突和新增准入规则明确；
2. 至少 6 个 Task fixtures 覆盖现有两种 Mode、歧义和 no-Skill；
3. 每个 fixture 产出能力要求、候选、选择/拒绝理由和最小读取计划；
4. 审计三个 accepted Skills 的适用/不适用边界；
5. 至少一个 triage candidate 得到证据化去留决定；
6. 每个任务分配 H0/H1/H2 Handoff 等级；
7. 到达后暂停评审，不扩展 API 或批量新增 Mode/Skill。

完整顺序见 `docs/implementation/MODE_SKILL_WORKSTREAM_PLAN.md`。

## 5. Handoff 与留痕规则

- H0：没有跨 Agent/上下文转移，只保留工作留痕、正式输出和验证。
- H1：普通子 Agent 默认返回一个 Compact Handoff Packet。
- H2：压缩、高风险 Claim/Decision、外部副作用、长等待/会话销毁、摘要争议或明确 Task policy 才追加 Manifest/Audit/Receipt 等审计链。
- 工作留痕记录基线、重要决定、读取范围扩大、修改路径、关键检查和未完成项；不记录每次文件打开或隐藏推理。
- 新 Task 可以复制 `docs/templates/TASK_WORKLOG.md` 到自己的 Attempt 目录。

## 6. 后续工作分支

从包含本 Handoff 的最新 `main` 创建：

```text
agent/mode-skill-selection-baseline
```

该分支默认不得修改：

- `src/research_workbench/adapters/models/`
- `registry/providers/`
- `registry/models/`
- Provider/API conformance 与 session runner 测试

共享 Schema 或 `cli.py` 只有在 Mode–Skill 节点确实需要且接口 owner 已确认后才能修改。

## 7. 恢复验证

```powershell
python -m pip install -e .
rwb validate examples registry --root .
python -m unittest tests.test_documentation tests.test_catalog tests.test_skill_evaluation tests.test_validation -v
```

本文更新前最近一次全量基线为 137 项测试通过、`validated=53 errors=0 warnings=0`。该数字只证明仓库契约状态，不证明 Skill 增量价值或科学正确性。

## 8. 最小回传

接手者至少回传：基线提交、Task ID、允许读取集、独占写入范围、修改路径、验证、未证明内容、Handoff 等级和唯一下一动作。缺少这些内容时，不能把聊天中的“已完成”写回 Main State。
