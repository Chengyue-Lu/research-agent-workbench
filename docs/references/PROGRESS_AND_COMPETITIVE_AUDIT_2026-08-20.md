# 项目进度与竞争力审计（2026-08-20）

审计性质声明：本文件是 2026-08-20 时点的一次性**结构审计快照**，不是第二套状态权威——任务状态唯一权威仍是 [../TASKS.md](../TASKS.md)，稳定架构关系唯一权威仍是 [../ARCHITECTURE.md](../ARCHITECTURE.md)。本文所有"通过/一致"仅指**结构有效性**，不宣称科学正确性。

审计范围：五路只读审计（TASKS 符合性 / 架构不变量 / 会议全文转写挖掘 / 开源竞品调研 / PR #11 深读）+ GitHub PR #10 review 原文 + 本地代码核对。除开源调研外，全部结论均有仓库内 `路径:行号` 证据。

---

## 一、总体结论（先看这里）

1. **项目推进严格符合 TASKS.md 与 ARCHITECTURE.md**：抽查的 DONE 项产物全部在位，15 条架构不变量未发现明确违反，未提交的 M6-004 改动与 CHANGELOG、证据包、代码/测试 diff 四方互洽，无密钥泄漏。存在的偏差都是"小修级"，无方向性偏离。
2. **路诚钺 PR #11（K-MS-1）质量高且已被会议追认**：Mode→Action→Need 反推、Skill 生命周期、safe stop 在 08-17~19 已以 ADR + 代码 + fixture 落地；08-19 晚会议讨论的方向是对该基线的确认，不是新方向。
3. **竞争定位经得住检验**：human-gated + 证据可裁决是开源生态的空白地带；最大的重复造轮子风险在 Skill spec/发现层（应对齐 ToolUniverse/MCP），最大的短板是差异化缺量化基准。
4. **合并 main 的真实门槛是 PR #10 的 CHANGES_REQUESTED review**：4 项 blocking + 3 项 hardening，当前分支疑似只覆盖了其中一部分，需逐条核对修复后才能按会议确立的流程（改 → 本地虚拟 merge → 真合并）推进。

---

## 二、进度符合性审计（TASKS.md）

### 2.1 DONE 项抽查：全部有对应产物

| 条目 | 验收声明 | 核对结果 |
|---|---|---|
| M1-002 | 7 类对象 Schema | `schemas/v0.1.0/` 19 个 schema 全部声明 Draft 2020-12；`tests/test_schemas.py` 在 |
| M1-006 | 最小 CLI | `src/research_workbench/cli.py:1099-1398` 含 init/validate/resolve/handoff/trace/checkpoint；`tests/test_cli.py` 在 |
| M1-007 | 确定性风险检查 | `src/research_workbench/contracts/risk_codes.py`（200+ 码）+ 对应测试在 |
| M2-001/002/005 | Registry/Resolver、四 Profile、handoff-integrity | `capability/resolver.py`、`registry/agents/` 恰四份、`.agents/skills/handoff-integrity/scripts/check_handoff.py` 均在 |
| M6-002/003 | session kernel、文件闭环四终态 | `adapters/models/session.py`、`execution/{compiler,runner,closeout}.py`、`examples/api-execution/` 均在 |
| M6-004 | live completed + 脱敏证据包 | `docs/implementation/evidence/M6-004/`：README + 6 个 yaml/json + 4 个输出工件；`execution-receipt.yaml` 与 `attempt.yaml` 均为 completed、check-report 全 pass；按约定不含 execution-plan.yaml（自洽） |
| M7-016 | K-MS-1 九项条件 PASS | `docs/workstreams/chengyue-lu-mode-skill/K_MS_1_NODE_REVIEW.md:70-78` 恰九行逐项 PASS，Decision 工件 `examples/objects/decision/D-K-MS-1-BASELINE.yaml` 在 |

未发现"文档说 DONE 但产物缺失"的硬偏差。

### 2.2 IN_PROGRESS 项（M3-001..007）

各项验收文字均为"已实现 X；待演练/待采集 Y"结构，与代码证据（`context/models.py`、`context/handoff_transfer.py`、`observability/models.py`、`examples/continuity/` safe-pause fixtures、ADR-0012）一致。Y 部分（kill 矩阵、真实 H1/H2 成本、真实脱敏器）属真实运行证据，离线不可证实也不可证伪——状态定性合理。

### 2.3 发现的小偏差（不阻断，建议随下次提交修正）

1. `docs/tmp/rwb_second_round_audit_package/` 空壳 zip（186 字节，仅含空目录）+ 同名空目录残留，与 M6-004 无关、未登记、未 gitignore——建议删除。
2. CHANGELOG 称 M6-004 的 4 个修复"各配测试"，但第 4 项（prompt 最终消息契约，`execution/compiler.py:443-465`）在本次改动集中无对应新测试——建议补一个断言测试而非改文案。
3. TASKS.md 未定义 READY 语义，存在 READY 项依赖 IN_PROGRESS 项（如 M3-008 READY ← M3-007 IN_PROGRESS）——建议补一句状态语义定义。
4. M6-004 证据 README 的迭代列表从 AT-API-002 起列，未提 AT-API-001/004（本地 `work/` 中确实存在）—— trivia 级。
5. "verify 幂等"：证据包直接证实终态 completed 与 check pass；live 侧幂等只能由离线测试推断，表述上应注意。

### 2.4 密钥与脱敏核验

对证据包与 `examples/api-execution/task-evidence-live.yaml` 精确扫描：无 `sk-`{16+}/Bearer 形态密钥（初筛 5 处命中均为 `task-evidence` 子串误报）；凭据仅以环境变量名引用。原始 Attempt 目录在本地 `work/` 保留且被 `.gitignore:21` 忽略，与 README 声明一致。

---

## 三、架构一致性审计（ARCHITECTURE.md v0.4，15 条不变量）

### 3.1 未发现明确违反

- **无全局 Supervisor / 消息总线 / 固定 DAG**：`src/` 全目录 grep 零命中；docs 中 Supervisor 均以否定形式出现（ADR-0001、ADR-0010、`modules/08` 的新机制门槛）。
- **内核无学科词汇、无厂商绑定**（不变量 8）：`kernel/objects.py` 无学科词命中；`pyproject.toml` 依赖仅 jsonschema/PyYAML/rfc3339-validator；厂商名只出现在 `adapters/models/`；HTTP transport 用标准库 urllib，无 vendor SDK；内核/契约层不 import adapters。
- **Skill 路由硬规则**（§5）：required_skills 显式必填（`tasks/models.py:158-159`）；新分配只选 active（`capability/catalog.py:231`，SKILL-INACTIVE）；legacy/deprecated 仅精确版本回放（SKILL-VERSION-REQUIRED / SKILL-REPLAY-AUTOSELECT-FORBIDDEN）；forbidden 优先于推荐；Skill 不扩权限。均有测试覆盖。
- **API 执行边界**（§9）：显式槽位 + `SELECTION_POLICY="explicit-slot-only"`（`adapters/models/pool.py:26`）；`src/` grep `fallback` 零命中，槽位未绑定直接阻断（EXEC-MODEL-UNBOUND）；七种预算硬停（轮次/单轮 token/总 token/成本/wall time/并行工具/工具结果大小）。
- **Handoff 复杂度由风险决定**（不变量 13）：`HandoffPolicy` 默认 `require_transfer_manifest=False`、`semantic_review="risk-triggered"`——H1 默认、H2 触发式，有代码体现。
- **实名 owner 纪律**（不变量 15）：DEVELOPMENT.md 实名分工表、TASKS.md 每里程碑标实名、risk_codes.py 语义变更需双人确认、ADR-0012 绑定 accountable_owner。

### 3.2 存疑项（均属"文档承诺先行、代码滞后"，且已在 TASKS/risk_codes 显式登记）

- H0/H1/H2 字面标签未进代码/Schema（语义由 HandoffPolicy 字段表达，映射靠人读）。
- 不变量 11 后半句（模型 override 强制生成新可审计 Attempt）未追踪到闭环证据。
- 受控读取强制（TASK-READ-OUTSIDE-SCOPE / CTX-READ-SCOPE-DRIFT）仍 `not_yet_emitted`；Attempt Archive 自动捕获对应 M3-007 IN_PROGRESS / M3-008 READY——正是下一节点要解决的。
- 不变量 7 部分覆盖：HANDOFF-NEGATIVE-UNMAPPED 已发射，HANDOFF-OMITS-NEGATIVE 仍 not_yet_emitted。

---

## 四、路诚钺 PR #11（K-MS-1）评估

### 4.1 合并内容与语义落点

Merge commit `e7fa539`（9 提交、81 文件、+5729/-298）。核心语义——Skill 选择从"来源驱动"转为 **Mode→Action→Need→最小机制**：Mode 不携带固定 Skill bundle，每个 action 按六级阶梯（invariant→Task contract→Tool→Skill Need→Human Gate→blocked）选最小充分机制（ADR-0013 §1/§2）；dossier 主键从来源名改为 `need_id`（ADR-0013 §3）；project-internal lane 独立（ADR-0014）；active/legacy/deprecated 生命周期 + 精确版本回放（ADR-0015）。

### 4.2 验收与 safe stop

九项条件原文在 `docs/workstreams/chengyue-lu-mode-skill/README.md:138-146`，逐项 PASS 证据在 `K_MS_1_NODE_REVIEW.md:68-78`。safe stop = 停止本分支机制与库存扩张，后续仅三条有前置条件的路径（路先做 M3-008；Trace 可用后才解锁 M7-005/006/014；API 侧归黄毅独立 lane），且机读化为 `forbidden_automatic_next_steps`（D-K-MS-1-BASELINE.yaml:25-28）。合并 main 不解除 safe stop。

### 4.3 库存数字

73 条候选（48 reference / 10 triage / 10 rejected / 5 quarantine，`registry/skills/candidates.json`）；11 个来源（`sources.json`，含 K-Dense-AI/scientific-agent-skills 引入记录，与会议纪要互证）；三个 0.1.0 原型转 legacy×2 / deprecated×1，**active=0 是有意结果**（ADR-0015）；包本体保留在 `.agents/skills/`，未删除任何 Skill 包。

### 4.4 与会议纪要的关系：仓库先行、会议追认

时间线（已证实）：Mode-first 提交 `9666d74`（08-17）→ 原型迁移 `2821600`（08-18）→ lifecycle `0be3982` + PR #11 合并（08-19）→ 会议（08-19 晚）。会议讨论的"摒弃 Mode 直绑 Skill、Action 反推、Skill 内生"是对已落地基线的**追认**。

**纪要表述纠正一处**："已清理 3 个外部 Skill"与仓库事实不符——被降级的是 3 个**项目原创** 0.1.0 原型；73 条外部候选从未安装/执行/准入（M7-009），不存在"清理外部 Skill"的动作。建议两人对齐口径。

**GLM 三组对照实验**（纪要提及）：只有定性结论（"加不加 Skill 区别不大，有时更差"）、无数字、未入仓库证据链——可作转向动机，不可当量化证据引用。

---

## 五、会议决策对照（2026-08-19 晚）

### 5.1 与仓库既定决策一致

- LangGraph 只参考不引入运行时（ADR-0001/0009 既定策略，会议确认）。
- PR 流程：AI 审 → 本地虚拟 merge 测试 → 真合并（与 DEVELOPMENT.md 纪律兼容）。
- 下一节点 M3-008（Trace baseline），与 TASKS.md 末尾一致。

### 5.2 会议新增（仓库尚无记录，需落库）

- **FAROS（OpenNSWM-Lab）**＝纪要语音转写的"Barrels"（高置信推断：转写描述的 Blueprint/Capability/Profile/Provider 四层分离与 FAROS 自述逐词吻合）：竞品中与我方最像；我方差异 = no-Skill 选项 + Need 反推 + 治理生命周期。需持续跟踪其演进。
- **ToolUniverse（mims-harvard）**：Find Tool/Call Tool 两操作 + 三策略按需发现，会议已定"直接用"。其 spec/发现层与我方 Skill 注册同构——应对齐其格式与 MCP，治理层（准入/生命周期/人工门）才是我方增量。
- **PaperQA**＝纪要"ParaQA"（推断）：作为"架构频繁大改"的反面教材，警示持久化格式与行为版本提前松耦合。
- **Linux 部署优先**：新方向；仓库执行文档目前 Windows-first（PROVIDER_ADAPTER_PLAN），但 GETTING_STARTED 本有双验证计划——属优先级提前，非冲突。
- **未决**：文献检索"边搜边做 vs 集中检索后交付"（上下文稳定性/效率/成本三权衡），建议走 M7 Tool capability card 流程裁定。

### 5.3 张力与协作风险

- **Handoff Risk Classifier 归属模糊**：会上路问黄"你是不是做了"，黄未确认；全仓 grep 该词仅 ARCHITECTURE.md:81 图节点一处，**无实现**。需两人当场对齐归属与范围——这是当前唯一的协作认知差。
- **Skill 自进化 loop**（审计 agent 提修改建议、人工审核）：触碰"无全局 Supervisor"项目边界，落地必须走 ADR + 真实失败证据，建议暂缓。
- **Alpha 范围会议未定义**：仓库已有可对照定义——GETTING_STARTED.md 载"内部技术 alpha 已到位，外部 pilot 差 6 个 Gate"，建议以此为准对齐口径。
- **LICENSE 未定**（PENDING_ADJUDICATIONS #4）阻塞 M0-007 与一切对外发布，是任何分发/商业化讨论的前置。

---

## 六、开源竞争格局（2026-08-20 调研，星级为约数）

### 6.1 分档对比

| 类别 | 项目 | 规模/状态 | 核心机制 | 与我方关系 |
|---|---|---|---|---|
| Deep research 报告 | gpt-researcher | ~28k★，活跃 | planner+execution，provider 无关，MCP | 无人工门/证据哈希/治理；可复用检索器抽象 |
| 同上 | LangChain open_deep_research | ~13k★ | 三阶段图 + HITL 中断点 | 可复用 scope→research→write 图；绑死 LangGraph |
| 同上 | STORM / Co-STORM | ~30k★ | 两阶段检索提问→成文带引用 | 仓库已列参考并划界（知识整理≠因果判断） |
| 端到端 AI 科学家 | Sakana AI-Scientist v2 | 开源，Nature 相关论文 | Agentic Tree Search 全自动出论文 | 哲学与我方相反（无人工模板），恰是对照组 |
| 同上 | Agent Laboratory | ~5.6k★ | 角色化 agent + 三段管线，支持 copilot | **主流中最接近我方 human-governed**，但无契约/准入治理 |
| 同上 | AgentRxiv | arXiv:2503.18102 | agent 间共享预印本累积改进 | 理念呼应 Attempt Archive，但无人工治理 |
| 科学平台/工具 | FutureHouse PaperQA2 + aviary | Apache-2.0 | 高精度文献 RAG + agent 环境 | 仓库已列为 Tool Adapter 候选——维持"可选 adapter、非核心依赖" |
| 同上 | Biomni（snap-stanford） | 活跃 | 11GB 数据库 + 150+ 工具重型环境 | 反证我方"轻量可复现"价值；可借鉴工具目录组织 |
| 同上 | ToolUniverse（mims-harvard） | PyPI 可装 | Find/Call 两操作 + 三策略发现，600+（论文口径）~1000+（营销口径）工具 | **与我方 Skill 注册/发现同构度最高**；对齐格式，差异留治理层 |
| 同上 | Google AI co-scientist | **非开源** | 假设锦标赛多 agent | 仅 trusted tester；可借鉴锦标赛评审作 Mode Pack 思路 |
| 编排/基础设施 | LangGraph | v1.0（2025-10） | durable execution + interrupt() HITL | 既定"文件 checkpoint 先行、真实需求再接图运行时"策略维持 |
| 同上 | Microsoft Agent Framework | GA（2026-04） | AutoGen+SK 合并，图工作流 | 印证不把旧 AutoGen 作核心依赖 |
| 协议层 | MCP | 2025-12 捐 Linux 基金会 AAIF | 工具接入中立标准 | Tool/Provider adapter 优先兼容，不自造协议 |
| 同上 | A2A | v1.0 GA，150+ 组织 | agent↔agent 通信 | Task Packet/Handoff 语义可对齐，不必立即实现协议 |

### 6.2 差异化判断（辩证）

1. **坚持**：human-gated + 证据可裁决（版本化文件契约 + SHA-256 + 确定性校验 + Human Gate）是开源空白——主流全部押注"更高自治、更多工具"，无一把治理当一等公民。"可裁决性"应作为对外叙事核心。
2. **避让**：Skill 元数据注册 + 按需发现与 ToolUniverse Find Tool、MCP 同构。spec/发现层对齐外部格式，差异只留在治理层（准入、legacy/deprecated 生命周期、人工门）——生态尚无对应物。
3. **重述卖点**：provider 中立已是共识特性（gpt-researcher 等均有），不是壁垒；真正差异是"显式槽位 + 无自动 fallback + 可审计"，应与证据链绑定宣传而非单独叫卖。
4. **维持**：编排/持久化不重造（LangGraph durable execution/interrupt 已成熟）；文件 checkpoint 先行策略与生态演进一致。
5. **补短板**：差异化缺量化支撑。建议 M5 对照设计纳入 LitQA2 类公开基准子任务，证明治理开销不牺牲基础能力——否则"可信科研"叙事无数据。
6. **反面教训**：AI-Scientist 全自动路线（rebuttal 仍须人工、有伦理争议）与 PaperQA 多次大版本重写证明追自治 SOTA 与频繁重构代价高昂；我方"轻量可复现、文件契约优先"是可持续路线。

---

## 七、合并 main 的门槛：PR #10 review（路诚钺，CHANGES_REQUESTED，2026-08-18）

### 7.1 review 要求与当前代码核对状态

| # | 要求 | 当前分支状态（初步核对） |
|---|---|---|
| B1 | rebase 当前 main 并整体再生哈希派生 fixture（review 时模拟合并 241 测 5 败：HANDOFF-AUDIT-REF-HASH ×3、H2 fixture not-transfer-ready、task-evidence.yaml 双变更） | 未做——本地分支含 main（e7fa539），但 fixture 再生未验证 |
| B2 | `--from-state` 先校验再调 provider；previous_checkpoint_ref 钉确切前驱路径 | **疑似已修**：`cli.py:1004-1071` 已见 `_load_valid` + `_project_relative` 模式——需核验校验时机与 Attempt identity 绑定 |
| B3 | 完成标记经临时文件+原子步骤发布；replay 前严格校验计数/角色集/路径/哈希/Main State | 待核验：当前分支 `_write_marker`/`already_published` 零命中（closeout 已重构为原子 stage/validate/publish），需逐条对照是否等价覆盖 |
| B4 | Evidence provenance 绑定所选输入（显式 source path/id，受冻结输入集约束，locator+hash 联校） | 待修：execution 侧未见 SOURCE-HASH/LOCATOR 对应实现。注意：动 Evidence 契约属共享接口，须先与路确认 |
| H5 | reasoning_effort 透传并进 Attempt identity | 透传已见（`compiler.py:201,233` → `openai.py:158`）；Attempt identity 绑定待核验 |
| H6 | Tool 调用即计数（oversized-result 分支不得跳过 tool_call_count） | 待核验（`session.py:295` 计数点位置） |
| B7 | M6-004 独立验收证据（secret-free 证据索引/哈希钉住摘要） | **已回应**：`docs/implementation/evidence/M6-004/` 脱敏证据包即为此建，新 PR 描述中引用即可 |

回归要求：截断/部分 marker、缺失/分歧 from-state + 前驱连续性、多输入 source 选择与 locator 错配、effort 传播与 Attempt 敏感性、超大 tool 结果计数、3.11/3.13 CI。

注：review 的行级评论抓取失败（API 错误），动工前用 `gh` 复核一遍。review 末段明确：API/session 实现变更留在本 PR；共享 Trace schema 等 M3-008，不在执行包内自定。

---

## 八、行动建议（分阶段）

### P1 — M6-004 收尾（黄毅 lane，低风险）

1. 删除 `docs/tmp/rwb_second_round_audit_package/` 空壳残留。
2. 为 prompt 最终消息契约补断言测试（兑现 CHANGELOG"各配测试"）。
3. 全量回归 + 文档链接校验。
4. 提交推送 M6-004 全部改动到 `agent/m6-003-k-api-2-file-loop`，提交信息注明回应 review B7。
5. `.rwb/live.env` 由本人删除（文件已被 gitignore，后续 live 运行再建）。

### P2 — review 修复冲刺（合并 main 前置）

6. 按 §7.1 逐条修 B1-B4、H5-H6 并补全部回归；B4 动 Evidence 契约前先发路确认。
7. 本地虚拟 merge main 验证 → 全量测试（3.11/3.13）→ 开新 PR 请路复审，PR 描述逐条引用处置证据。

### P3 — 会议决策落库与治理（共享文件，草案先行、双人确认）

8. 本文即会议待办"审计内容整理"的落盘；FAROS/ToolUniverse/PaperQA 的逐一核对表可在此基础上扩展。
9. PENDING_ADJUDICATIONS 六项提请裁定：#4 LICENSE（建议 Apache-2.0，发布前置）；#5 建议采纳"降 WARN + 钉 session-transcript，M6-006 后恢复 BLOCK"；#1/#2/#3 口径类一并裁定；顺带重编号重复的两个 ADR-0005。
10. 需新 ADR/Decision 的会议结论：ToolUniverse/PaperQA 作 Tool Adapter 接入（与 ADR-0013 阶梯兼容）；文献检索方案二选一；Skill 自进化 loop 暂缓；Handoff Risk Classifier 归属对齐；Alpha 范围按 GETTING_STARTED 的 6 Gate 定义；Linux 部署优先级提前。

### P4 — 主线提醒

- 路诚钺 lane：M3-008（Trace Envelope/Index/Event Schema + validator + 手工 fixture）——解锁 M7-005/006/014 与 M6-006 的唯一前置。
- 黄毅 lane：P2 完成后可接 M3 系列真实演练（kill 矩阵、真实 H1/H2 成本采集）。

---

## 九、信息来源与置信度

- **已证实**（仓库内证据）：第二、三、四、七章全部结构性结论；PR #10/#11 内容（GitHub 原文）。
- **高置信推断**：纪要"Barrels"=FAROS（转写特征逐词吻合）；说话人归属（按内容与分工推断）。
- **中低置信推断**：纪要"ParaQA"≈PaperQA（特征吻合但未经当事人确认）。
- **未知/待核**：纪要"5 条成熟早期技术路线"完整清单（未进入语音流）；PR #10 行级评论；GLM 对照实验的原始记录（未入仓库证据链）。
- 开源项目星级/版本为 2026-08-20 调研时点约数，引用前建议复核。
- 会议纪要原文为本地存档（未入库）；本文不含采购、报销等私人话题，相关内容不构成项目决策。
