# Changelog

本项目遵循“证据先于宣称”：离线契约、fixture 和真实运行结果分开记录。日期按仓库当前开发快照标记。

## 2026-08-21 — K-INTEGRATION-1 Method / Execution Shared Seam Freeze

### Integrated

- 冻结 M3-008 file-authoritative Execution/Archive Trace Core：四个 Trace Schema、append-only recorder、
  deterministic validator、tool-result provenance、Trace CLI、覆盖率与 packaging Gate 已形成闭环。
- 冻结 legacy M6-006 Trace Adapter：SessionEventSink、traced runner、archive closeout、file-only verify、
  recovery preflight，以及 v0.1 Attempt/Receipt 的可选 `trace_ref` 已接入；原 Skill lock 未删除或放松。
- PR #15 作为统一集成分支包含 PR #14 Core 与 Part B Adapter；PR #16 的全表 Owner 重写不进入主线，
  仅吸收状态轴与当前任务真值的必要同步。

### Boundaries

- 当前 legacy 路径保持 Task + Skill Assignment → M6 Adapter → M3-008 Trace；future Method-first 路径
  继续由 M8-002/M8-003 定义 Mode Action、Method Resolution、Capability Resolution 与执行桥接。
- OpenAI live conformance、EVID/SIM SIR、process-kill recovery 与 Method-dependent Part C 不属于本同步点
  的 merge gate，继续分别由 M6-004、M3-001/M3-006、M8-002/M8-003 跟踪。
- `K-INTEGRATION-1` 不声明科学正确性，不改变 Method/Core、Claim 或 Human Gate 语义。

## 2026-08-20 — 第二轮架构审计与全局文档重整

### Decided

- ADR-0016 将 RWB 定位为版本化、方法感知的科研控制平面，采用 Integrity、Research State、
  Method、Capability/Strategy、Execution 五个逻辑平面。
- `Method Resolution` 成为 Task 到 Execution 的目标中间语义；Mode/Protocol/Strategy/Skill/Tool/
  Capability 保持正交，Execution 不拥有科研语义解释权。
- M3-008 保留为 Execution/Archive Trace 基线，Method Trace 使用后续独立 Task；外部项目声明本轮
  未重新核验，未被提升为产品能力证据。

### Consolidated

- 新增 `ROADMAP.md`、第二轮审计吸收记录与 M8 Method Core 任务组；唯一下一任务调整为 M8-002
  Mode Action first-class contract。
- 按 Issue #12 完成 M8-002 前的 docs semantic freeze：正式/候选 Mode 分离，Task/Method/Resolved
  Capability/Execution 边界、Skill 状态轴、no-Skill 及 Claim promotion 权限统一到 ADR-0016。
- 重写 Charter/Architecture，并更新开发入口、模块边界、使用指南和根 README；旧总实施计划
  缩减为历史映射，实时状态继续只由 `TASKS.md` 维护。
- K-MS-1 workstream 保留为历史证据，不再承担当前开发入口；真实 Skill/H1/H2 对照在 Method
  Resolution 和相应 Trace/Evaluation contract 前保持 parked。

### Boundaries

- 本次只修改文档，不实现 Schema、Resolver、Research State、Trace 或 Runtime；不验证、安装或
  调用审计材料中的外部项目。

## 2026-08-19 — K-MS-1 节点评审与分支收束

### Reviewed

- K-MS-1 九项条件逐项通过：两个 Mode 的 action/机制、每个 Mode 不超过两个 Need、八个 Task fixture、五张 Tool cards、三个原型迁移、来源/项目内生边界和非扩张约束均有可复验工件。
- 正式 Decision 接受 K-MS-1 为离线 Mode–Skill–Tool 选择/治理基线；明确不包含真实模型增量、科学正确性、H1/H2 成本、API 执行或发布就绪度。

### Consolidated

- `K_MS_1_NODE_REVIEW.md` 归纳本分支的来源筛选、GLM 困难任务诊断、Mode-first 转向、project-internal 路线、Tool/路由、原型迁移、lifecycle、测试和提交序列。
- 当前库存快照为 73 个 candidate、11 个来源、3 个历史 accepted 条目且 0 active；这些数量不被当作质量或待开发清单。

### Stopped

- 本分支进入 safe stop，不继续新增 Mode/Skill/Tool。下一前置为 M3-008 Trace Schema/validator/fixture；完成前不启动 M7-005/006/014 的真实比较。
- M2-003/004/007/008 从误导性的 `IN_PROGRESS` 转为 `PARKED`：保留历史原型、垂直切片和来源库存，但只能由 Mode-derived Need 与 Trace Gate 重新激活。

### Integration review

- 远端/主线合并审计确认分支相对最新 `origin/main` 为 `0 behind / 9 ahead`，工作区干净，159 项测试与补丁检查通过，建议合并离线基线并保留原分支历史。
- 合并不解除 M0-007 许可证阻断，不构成 Skill 效果、科研价值、API 执行或对外发布结论；下一节点必须从更新后的 `main` 另建 Task/分支。

## 2026-08-19 — Skill lifecycle 与精确版本回放

### Added

- ADR-0015 分离 accepted 准入历史与 `active | legacy | deprecated` 分配 lifecycle，并复用 `skill-id@semver` 作为 Task 精确版本 selector。
- Registry/Resolver 默认只允许 active Skill 进入新 Assignment；historical replay 必须显式指定、使用精确版本且禁止 auto-select。
- CLI 增加 `--historical-replay`，accepted 列表显示 lifecycle；测试覆盖新分配阻断、精确历史回放、多版本歧义、旧 Assignment 自校验和版本化 Handoff lock。

### Changed

- literature/simulation `0.1.0` 标为 legacy，handoff wrapper 标为 deprecated；当前 active accepted Skill 为零，不自动创建替代包。
- 两个历史 Task fixture 改用精确版本，并同步更新引用它们的 Transfer Audit、Main State hash 与 checkpoint digest。

### Boundaries

- 未修改锁定 Skill 包或 manifests，未创建新 Skill；未修改 Provider/API/session/Adapter、模型路由或 live conformance。直接 `--skill <manifest>` 仍是本地开发输入，不代表 Registry 准入。

## 2026-08-18 — Accepted Skill 0.1.0 迁移基线

### Decided

- 三个 accepted `0.1.0` 包保持内容与包哈希冻结，只用于历史 Assignment 解析；新的 Mode-action 路由不再默认分配这些原型。
- `literature-evidence-extraction` 回到 ES-A4 的 Task+checker 基线和 ES-A6 的窄 Need；`simulation-vv` 拆回 Tool、两个方法 Need、Mode/Human Gate，不创建新的宽泛 V&V bundle。
- `handoff-integrity` 判为 `deprecated-wrapper`：确定性检查归入现有 `research-contract-check` card，H2 语义义务仍由 Task/Trace/Human sample 决定，不创建换名 Skill。
- 当前 accepted Registry 缺少 historical/active/deprecated lifecycle、精确版本约束且禁止同 ID 多版本；该 enforcement 缺口独立记为 M7-015，不在文档层假称已实现。

### Added

- `ACCEPTED_SKILL_MIGRATION.md` 与机器可读迁移夹具，逐项固定 action、direct baseline、content/package hash、new-assignment 决定和 next-version Gate。
- 确定性测试核对夹具与实际 accepted Registry/包哈希一致，并阻止迁移文件暗示占位新版本或 Runtime enforcement。

### Boundaries

- 未修改三个历史 Skill 包、accepted manifests/Registry、Schema、Provider/API/Runtime/Adapter、模型路由或 live conformance；没有创建或准入新 Skill。

## 2026-08-18 — Action-driven Tool 与路由 fixtures

### Added

- 五张 provider-neutral Tool capability card：`document-read`、`literature-search`、`citation-resolve`、`bounded-compute` 与 `research-contract-check`；逐项声明数据出口、权限、副作用、预算、失败、验证、fallback、Action 消费者和责任边界。
- 八个 Task–Mode–Action–Mechanism 诊断 fixture，覆盖 evidence/simulation trigger、no-Mode、candidate Mode、组合拆分、内部 Handoff、tool-only、no-Skill、Skill Need、Human Gate、capability gap 与 blocked。
- 六项 fixture 覆盖测试；`.yaml.txt` 明确不是 Runtime Schema，不因规划测试创建新的正式契约。

### Decided

- Tool card 只从已确认 Action gap 产生；没有 Runtime 消费者前不建立 `registry/tools/`。具体 CLI/MCP/API 只是 Adapter 候选，不能反向定义 Mode 或 Skill。
- Skill Need 不自动形成 Assignment。三个尚未实现的 Mode-derived Need 在 fixture 中保持 Need/Human Gate，两个 tool-only 场景明确不加载额外 Skill。
- candidate observational Mode 的子任务被拆分并阻断，不强塞进 evidence-synthesis 或 simulation。

### Boundaries

- 未实现、选择、安装、探测或调用任何 Adapter/MCP/CLI/API；未读取凭据，未修改 Registry、Schema、Resolver、Runtime、Provider 或模型路由。

## 2026-08-18 — Project-internal Handoff direct baseline

### Added

- `PROJECT_INTERNAL_SKILL_DOSSIERS.md`：为 Compact Handoff 与 H2 Audited Transfer 建立 trigger/non-trigger、direct baseline、边界、compact candidate hypothesis 和进入条件。
- `examples/evals/project-internal-handoff/`：保存 H1 negative omission 与 H2 semantic reversal 两个诊断样例；review-only challenge ledger 与 worker 可见输入分离。
- 两项 fixture 测试，固定“结构检查通过但语义问题仍存在”的预期行为，防止未来把结构 PASS 误报为语义等价。

### Decided

- 两个 project-internal Need 均保持 `hold-no-skill`。合成 fixture 只证明 Schema/结构 mapping 的已知边界，不能证明 Skill 优于 Task policy、template、Tool 或 Human sample。
- M7-013 完成后，主线返回 M7-008/M7-003；project-internal 的真实比较继续等待独立 Task family 与 M3-008，不初始化 Skill 包。

### Boundaries

- 未修改 Handoff/Transfer Schema、assessor、Registry、Skill package、Runtime、Provider/API 或模型路由；未调用模型或外部系统。

## 2026-08-17 — 转为 Mode-first Skill 需求推导

### Decided

- ADR-0013 冻结新顺序：Research Mode → 可选 Action → Failure/Artifact/Human Gate → 最小机制 → Skill Need；禁止从外部来源候选直接反推项目 Skill。
- 四份来源候选 dossier 保留为历史探索，本轮选择 0 个来源候选直接重写；后续 dossier 以 `need_id` 汇总多来源参考、真实失败和 no-Skill/direct-tool 基线。
- 三个 0.1.0 accepted Skill 作为历史原型冻结，不立即删除或原地扩写；后续按 Mode action 创建新版本或显式 deprecation。
- ADR-0014 增加与 Mode-derived Need 并行的 project-internal Need 来源，用于本项目特有的交接、恢复和 Human Gate 准备语义；强制交互留痕、读取边界、输出 Schema 和确定性校验仍不是 Skill。

### Added

- `MODE_ACTION_REQUIREMENTS.md`：为 `evidence-synthesis` 与 `simulation` 建立 Action–Failure–Artifact–Gate 和机制分配，首批每个 Mode 最多保留两个 Skill Need 入口。
- M7-011 Mode-derived requirement baseline 完成，并显式加入 `blocked/capability gap` 出口；M7-004/M7-005 暂停到 Need/Tool/Trace 前置条件满足，M7-010 以零直接重写对象完成。
- `PROJECT_INTERNAL_SKILLS.md`：预留五个 project-only Need，其中只允许 Compact Handoff 与 H2 Transfer 两项进入首批 dossier；没有创建 Skill 包、Registry 记录或全局 bundle。
- M7-012 项目内生 Skill 规划完成；M7-013 可与 Mode-derived Tool/路由工作并行，真实比较 M7-014 继续等待 M3-008。

### Boundaries

- 未新增 Mode、Skill、Tool Registry 条目，未修改 API/Provider/Runtime、模型路由或 live conformance；未安装、执行或注册 GLM 采集到的外部内容。
- GLM 第二批的 14 个 Tool/MCP 与 6 个 Skill 条目继续留在 Attempt Archive，只在已确认 action gap 下作为 reference inventory 使用。
- project-internal Skill 计入现有 Skill 数量和上下文预算，默认最多一个；不能授予权限、改变 Mode/Claim 或替代 Runtime Trace。

## 2026-08-16 — Accepted Skill 重叠审计与首轮 Dossier

### Audited

- `literature-evidence-extraction` 与 `simulation-vv` 结论为 `retain-revise`：保留方法语义，但 Transfer Manifest/`handoff-integrity` 从固定依赖改为 Task/H2 风险触发。
- `handoff-integrity` 结论为 `deprecate-wrapper`：确定性部分迁移为 `handoff-validation` Tool capability，H2 语义义务进入 Task/Trace 模板；Tool card 和 Resolver 迁移前不直接删除 accepted 条目。

### Triaged

- 完成 `build-evidence-map`、K-Dense citation management、experimental design、scientific visualization 四份 dossier，均包含 no-Skill/direct-tool、上下文、学科、Tool/权限、Human Gate、停止与重叠判断。
- evidence map 下沉为项目 Artifact/validator，scientific visualization 先拆 figure spec 与 Tool capability；两者不占当前重写名额。
- 建议只让极小 `citation-claim-integrity` 与 gated `experiment-design-checkpoint` 进入下一 Human Gate；该建议不是 `trial` 或 `accepted` 决定。

### Delegated discovery

- 通过原 OpenCode/GLM 5.3 会话派发第二批 S5/S6/S1/S2 候选采集；输出被限制在忽略的 Attempt Archive，不得修改 Registry、受控文档、commit 或 push，且新增模型预算目标不超过 30,000 tokens。

## 2026-08-16 — 多来源 Skill 摄取与首批机器筛选

### Changed

- Skill 方向从优先重复单个候选的高成本模型测试，调整为先建立多来源隔离候选池，再执行机器初筛、人工语义筛选和小规模困难任务验证。
- 工具/文件格式类以标准组织和官方仓库为优先；科研方法类按学科与研究形态比较多个来源，不接受全流程“大总管”作为默认架构。
- 高成本 GLM 搜索改为分片候选发现；GitHub 元数据、Tree、revision、许可和下载由主 Agent 独立核验。

### Added

- 首批固定 9 个来源；8 个筛选归档包含 54 个 `SKILL.md`，覆盖格式工具、证据、完整性、实验统计、理论推导和元技能。
- 只读静态初筛报告：140 个脚本文件、0 个不安全 ZIP 路径、0 个跳过文本；所有风险命中保留为人工定位信号，不解释为漏洞数量。
- [Skill 来源搜集、隔离与筛选](docs/workstreams/chengyue-lu-mode-skill/SKILL_SOURCE_INTAKE.md)：来源层级、开放分类轴、机器/人工 Gate、首批快照和 `K-MS-SOURCE-1`。

### Known gaps

- GLM 5.3 source scout 因抓取大型渲染页面至少消耗 82,966 reported tokens，超过 30,000 预算且未形成 JSON handoff；会话已终止并留存 capture gap。
- OpenAI/Anthropic/Google 的 19 个一方入口和其他来源的 35 个入口均已完成人工处置；6 个仅进入 `triage` 候选池，详细 dossier、困难任务和正式准入仍待完成。没有下载内容被安装、执行或写入 accepted Registry。

### Screened

- 补入 Google `gws-shared` 前置 Skill，修正首批 Google 工具选择缺少认证、dry-run、写前确认和输出规则的问题。
- OpenAI 的 Notebook/PDF/Skill authoring 进入 portable-core/authoring baseline；截图和图像生成转为 Tool/specialist Adapter 参考。
- Anthropic 的 `docx/pdf/pptx/xlsx` 按限制性 source-available 保持 reference-only；`skill-creator` 只吸收 Apache-2.0 评估结构。
- Google 广泛 API 目录降为按需 reference，窄 read/write recipe 转入 capability card，`persona-researcher` 因宽泛人格和跨工具写操作被拒绝为架构 Skill。
- 跨 GPT/Claude/GLM 采用公共 Skill core、薄 runtime binding 和测试生成的 model conformance policy，不维护三套完整分叉。
- GitHub、K-Dense、Academic Research Agent、lingzhi 与 Superpowers 的 35 个入口已逐项固定哈希并写入候选 Registry：6 个 `triage`、21 个 `reference`、3 个 `quarantine`、5 个 `rejected`。
- `build-evidence-map` 与 K-Dense citation/experiment/peer-review/visualization/power 组成 dossier 候选池；转换、上下文请求和完成前验证下沉为 Tool/模板/运行时契约，单体研究总管和递归 reviewer 工作流不进入当前架构。
- 补齐 OpenAI 5、Anthropic 6、Google 8 个一方入口的逐项 Registry 记录，替换两条无内容哈希的早期占位引用；结果为 18 个 `reference` 和 1 个 `rejected`，没有一方条目进入 `triage`、`trial` 或 `accepted`。
- M7-009 多来源筛选 Gate 完成；下一任务 M7-010 固定为四份 dossier，并在 accepted Skill 重叠审计后最多选择两个独立重写或困难任务对象。

## 2026-08-16 — `claim-preserving-rewrite` 探索性 Stage 1

### Tested

- 用 9 个隔离 OpenCode/GLM 5.3 会话完成 CPD-01..03 的 baseline、compact contract、full Skill 三臂诊断；总 reported tokens 125,709，无 worker 工具调用或外部副作用。
- CPD-02/03 产生可解释的硬失败差异：compact contract 两案均通过，baseline 分别发生 Claim 遗漏与无据机制生成，full Skill 在 CPD-03 仍越过术语/应用边界。
- CPD-01 三臂均保留 Claim，但只压缩 7.4%–10.0%，未达到约 25% Task 目标，因此不把“内容更完整”误记为任务成功。

### Decided

- 候选暂定 `revise-compact`：完整 Skill 暂未证明比 8 条最小约束更有价值，不进入 `accepted`。
- 暂不直接使用真实研究材料；先修复 checker 并只复验有区分的 CPD-02/03，差异可重复后再申请脱敏真实片段。

### Known gaps

- surface checker 把 Markdown case ID、列表编号当作科研数字，且中文 polarity/strength 正则存在编码问题；当前报告只能作诊断，不能作准入 Gate。
- CPD-03/full 超过单臂 120 秒和 20,000 token 边界；Attempt 只有手工 Trace，仍缺 M3-008 validator 与独立盲评。
- 诊断辅助 manifest/ledger 改用 `.yaml.txt`，避免被正式 `examples/` 对象的 Schema validator 误收；执行前 manifest 以原始 SHA-256 单独归档。

## 2026-08-16 — Skill 诊断性困难任务测试计划

### Changed

- 简单、单约束 fixture 降为结构/checker 冒烟，不再单独作为 Skill 增量价值证据。
- 首轮评估改为 baseline、compact contract、完整 Skill 三臂诊断；存在 checker 重叠时再做 direct-tool/full-Skill 配对，以区分普通提示、确定性 Tool 与 Skill workflow 的贡献。
- 测试采用分层预算：先运行少量高辨识度案例，只重复出现实质差异的案例；没有区分度时停止并优先缩短、降级或删除。

### Added

- 路诚钺维护的 Skill 诊断性困难任务计划：定义学科/动作相关压力类型、隐藏 challenge ledger、GLM 5.3 隔离执行、盲评、硬失败、上下文/协调成本和停止规则。
- `claim-preserving-rewrite` 首轮 CPD-01..03：高密度跨段 Claim、诱导增强/提示注入、混合意图/术语边界，共 9 个 Stage 1 会话的冻结计划。
- `examples/evals/claim-preserving-rewrite/diagnostic-v1/`：三份合成困难题、隔离的 review-only ledgers、8 条 compact contract、draft hash manifest 与人类预审表；尚未调用模型或写入理想答案。

## 2026-08-15 — 路诚钺 Mode–Skill–Tool 分支计划

### Changed

- 当前分支顺序调整为：先审计 accepted Skills、独立整理/重写最多两个明确候选并定义 Tool capabilities，再完善 Mode/Skill/Tool 路由；Attempt Trace validator 保留为真实 forward test 的前置条件。
- `handoff-integrity` 必须与 direct-tool/no-Skill 基线比较，不再因 accepted 状态默认保留 Skill wrapper。
- 外部 Tool 在本分支只冻结 provider-neutral 能力、数据出口、副作用、失败、验证与调用规则；Adapter、凭据和 API 测试仍由黄毅负责。

### Added

- `docs/workstreams/chengyue-lu-mode-skill/`：以实名责任人命名的分支计划目录。
- Skill 来源/许可、独立重写、渐进披露、首批候选队列和停止条件。
- Mode–Skill–Tool 路由 Mermaid、Tool Capability Card、首批 Tool 能力和 8 个路由 fixture 规划。

### Consolidated

- 原 `docs/implementation/MODE_SKILL_WORKSTREAM_PLAN.md` 已并入新的实名分支计划目录，避免维护两份当前专项计划。

## 2026-08-14 — 实名责任、完整 Agent Trace 与文档归并

### Changed

- 维护责任改为实名：路诚钺负责 Mode/Skill、读取、Handoff/Trace 方法与评估；黄毅负责 API 执行实现、自动 Trace 捕获与测试；工作流名称不再替代审批主体。
- Worklog 降为 Attempt Archive 的导航摘要。所有 Agent 间实际可见传递，以及运行时可观察的读取、工具/命令、文件 revision、结果和状态事件均要求留存。
- 完整留存与上下文加载解耦：主 Agent 默认只读取 `INDEX.yaml` 与 Handoff，排障或评估时才按 message ID 回放原文。
- 原 `CURRENT_HANDOFF.md`、`NEXT_STEPS.md` 和 `WORKSTREAM_OWNERSHIP.md` 合并为 `docs/DEVELOPMENT.md`、`docs/TASKS.md` 与 `docs/README.md`，减少当前状态的重复来源。

### Added

- ADR-0012：实名责任人与可回放 Agent Trace 决策。
- Attempt Archive 目录、actor registry、消息信封、capture-gap、删减和保留规则。
- 总体架构 Mermaid 图中的 Trace 写入、默认只读索引与实名维护关系。

## 2026-08-14 — Mode–Skill 工作流接管与上下文简化

### Changed

- API Adapter、API session、Task-to-API、live conformance 与 API 测试由黄毅维护；路诚钺主线改为 Research Mode、Skill 选择/评估/准入和协调成本。
- 当前下一节点从 `K-API-2` 调整为 `K-MS-1 Mode–Skill Selection Baseline`；API backlog 保留为共享仓库中的 external workstream。
- Handoff 改为 H0/H1/H2 风险分级：普通子 Agent 默认只返回 Compact Handoff，完整 Manifest/Audit/Receipt 只在压缩、高风险、外部副作用、promotion、争议或明确策略下触发。
- Agent 内容读取采用默认拒绝与逐级扩大：允许路径元数据发现，但未声明正文需先扩展 Task 允许集。

### Added

- `docs/WORKSTREAM_OWNERSHIP.md`：曾用于冻结工作流边界，现已归并到 `docs/DEVELOPMENT.md` 并改用实名责任。
- ADR-0011：记录风险分级 Handoff、受控内容读取和简短工作留痕原则。
- `docs/implementation/MODE_SKILL_WORKSTREAM_PLAN.md`：记录当前缺口、候选优先级、`K-MS-1` 验收和分支范围。
- 更新总体架构 Mermaid 图，显示 Mode–Skill 决策、执行工作流、内容允许集、读取扩展和 H1/H2 返回关系。

### Clarified

- 正式 Mode 目前只有 evidence-synthesis 与 simulation；其他模式名称不是待批量补齐的承诺。
- Worklog 记录基线、重要决定、范围变化、修改和验证；Agent 间实际可见传递另由 Attempt Archive 完整保存，仍不记录隐藏推理。
- 流程简化仍是假设；后续必须比较 H1/H2 的工件数、字符、审阅、回查、遗漏和返工。

## 2026-08-13 — API-first 隔离执行关键节点

### Changed

- 执行优先级从“Codex 原生运行时优先”调整为“文件契约 + 纯 API fresh session 优先”；Codex、OpenCode、Claude Code 等保留为可选 Runtime Adapter 或人工窗口入口，不预先固化最终平台。
- 模型选择收缩为显式 `primary`、`worker` 和少量 `specialist` 槽，不建设价格数据库、评分 Router 或静默 fallback。
- coordinator 默认指向 `primary`；evidence、simulation 和 targeted review Profile 默认指向 `worker`，高风险任务可由 Task/人类显式覆盖。

### Added

- ADR-0010，冻结 API-first 隔离执行、平台可替换和小型模型池边界。
- `ModelPool`/`ModelSlotConfig`：默认不读取环境，只按调用者指定槽位绑定一个 Provider/Model。
- `IsolatedApiSessionRunner`：单 Attempt 内的 fresh context 工具循环，限制模型轮次、工具调用、单轮并行、工具副作用类别、工具结果、单轮输出、累计 token/可得成本和 wall time。
- `rwb models probe` 与禁用状态的 `registry/models/pool.example.yaml` 模板。
- 离线测试覆盖显式槽位、禁用/未知槽、工具往返、data policy、预算暂停、工具结果不静默截断和无 Provider fallback。
- `docs/CURRENT_HANDOFF.md`：为无既往会话上下文的开发者或 AI 固化恢复顺序、已证明/未证明边界、`K-API-2` 验收、并行写入范围和风险预警。

### Milestone

- `K-API-1` 已到达：隔离 API 执行缝可离线验证，但尚未形成 Task-to-API 的 Attempt/Handoff/Receipt 文件闭环。
- 下一唯一节点为 `K-API-2`：完成一个 evidence Task 的 fresh API session 文件闭环，并在删除临时 transcript 后由新主会话恢复。该节点不是 GUI、发布或科研交付点。

### Fixed

- 目录包哈希改为按仓库相对 POSIX 路径排序，消除 Windows 与 Linux 对路径大小写排序不同造成的 Skill package drift。
- 显式声明 RFC3339 format validator 依赖，确保干净环境不会静默跳过 JSON Schema 日期时间校验。

## 2026-08-13 — 零基础使用与发布就绪度指南

### Added

- `docs/GETTING_STARTED.md`：从安装、自检、Task/Assignment/dispatch、原生 Agent 接力、Handoff 验收到 SAFE_PAUSE 恢复的完整上手路线。
- 按内部 alpha、外部 pilot、公开 beta 和稳定 `1.0` 分级的发布门槛，明确当前可用范围以及真实原生执行、项目脚手架、许可、兼容性、工件复现和科研价值证据缺口。

### Clarified

- `rwb init` 当前只是最小文件目录初始化器，不复制 Agent Profiles、accepted Skills、Registry 或 Codex 配置。
- `render` 只生成最小派发，不启动 Agent；Workbench 管契约和验证，线程生命周期继续由原生平台负责。

## 2026-08-13 — CCRML 讨论吸收与连续性闭环

### Added

- Task Packet 的原子工作边界、机器完成检查与安全暂停条件；Codex dispatch 会显式携带这些边界。
- Context Snapshot 的动态预算比较：下一 AWU 成本、closeout 成本与安全余量使用同一单位，不再以固定百分比单独决定 rollover。
- `stage-completed`、`safe-paused`、`waiting` 状态，以及包含 Attempt/Handoff/Receipt/Main State 的可恢复 SAFE_PAUSE fixture。
- Main State 的 `continuity_status`、哈希锁定 `machine_state_refs`、可选 Git HEAD 和恢复冲突检查。
- Execution Receipt 区分“执行结束”和显式 `completion_claim: contract-satisfied`；机器 `fail` 会阻断后者，但不会抹掉失败实验或负对照记录。
- YAML 工件先在同目录完整落盘，再以排他硬链接原子发布；注入发布故障不会暴露半文件或残留临时文件。
- CCRML 会议吸收差距表与 ADR-0009，明确复用现有工件并暂缓 SQLite/Graph/额外运行时。

### Not yet proven

- 文件式 SAFE_PAUSE 尚未在真实新原生会话中完成一次端到端恢复。
- 动态 AWU 成本仍为显式测量/估计输入，尚无跨模型校准数据。
- `continuity.sqlite`、Failure Memory 和混合检索的净收益仍无 benchmark 证据，因此未实现。

## 2026-08-13 — 暂停前开发快照

### Added

- 平台中立的 Research Object、Project Protocol、Research Mode、Agent Profile、Skill、Task、Attempt、Handoff、Main State、Context Snapshot 与 Execution Receipt 契约及 CLI。
- Codex 原生 Agent/Skill 映射和 evidence/simulation 双 Skill 离线垂直切片。
- OpenAI Responses、Anthropic Messages、Gemini `generateContent` 薄 Adapter，ToolChoice、本地工具参数复验和默认不读环境、不联网的 live conformance runner。
- 外部 Skill 来源 Registry、只读 ZIP 审计、18/18 入口追溯、隔离候选区及 `claim-preserving-rewrite` 原始候选。
- provider-neutral paired same-input Skill Evaluation、确定性检查报告、盲评/人工准入边界和故意 `not-eligible` 的 fixture。
- Handoff Transfer Manifest/Audit：稳定条目 ID、源工件哈希、Handoff locator、负面区段覆盖、风险触发的人类抽查，以及压缩 Context Snapshot/Receipt 绑定。
- `docs/NEXT_STEPS.md`，记录暂停点、恢复输入、执行顺序和禁止扩张项。

### Changed

- 主 Agent 明确只维护问题、约束、决定、冲突和工件索引；原始材料与长日志留在 Task/Artifact Context。
- Skill Assignment 固定 Skill 内容与包哈希、工具、权限和 Registry digest；不同 Agent 继续使用不同 Skill。
- `literature-evidence-extraction` 在压缩前输出 Transfer Manifest；`handoff-integrity` 可审计结构覆盖和有界语义抽查，不承担科学正确性评审。
- token/成本不可得时记录 `unavailable`，不以 0 代替，也不宣称节省。

### Security and governance

- 外部候选默认不可执行；发现、评估、trial、accepted 分离。
- Provider 凭据延迟读取；文档、报告和测试不保存 token、完整响应、Chain-of-Thought 或无消费方的 trace。
- GitHub/API 令牌不得在 Codex 沙箱读取或导出；真实认证和 live 调用在真实 Windows 用户上下文执行。

### Not yet proven

- 尚未完成三家 Provider 的真实模型 conformance。
- 尚未执行两个真实原生子 Agent 并删除会话后恢复。
- 尚未用真实研究材料验证 Transfer Manifest 是否遗漏关键语义及其维护成本。
- 首个候选 Skill 尚未完成四类真实 paired evaluation，也未准入。
- 尚无真实科研案例证明多 Agent 相对单 Agent 的净收益。

## 2026-08-12 — 初始重构方向

- 将原项目从“全局科研代理/全盘外包”方向收缩为研究者主导、平台优先、模式化组合的轻量契约层。
- 决定不自建通用 Supervisor、不建立单一跨学科流水线，并把上下文、证据、权限、成本和人工 Gate 设为核心边界。
