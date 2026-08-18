# 首轮 Skill 候选 Dossier

- 责任人：路诚钺
- 日期：2026-08-16
- 对应任务：`M7-010`
- 状态：候选驱动探索记录；ADR-0013 已取代其作为主动开发入口，本轮选择对象为 0
- 决策上限：四份 dossier，最多两个进入独立最小重写或困难任务；外部包仍不可执行。

## 1. 决策摘要

| 候选 | 相对现有能力的净增量 | 建议处置 | 是否进入下一轮 |
|---|---|---|---|
| `gh-build-evidence-map` | 推理边类型、unknown 与图连通/循环约束；Evidence/locator 本身高度重叠 | 下沉为 Evidence-map artifact schema、确定性 validator 与按需 Task 模板 | 否 |
| `kdense-citation-management` | claim/source 语义核对有价值；检索、元数据、BibTeX 主要是 Tool | 独立重写极小 `citation-claim-integrity`，Tool 与网络策略分离 | **建议 1** |
| `kdense-experimental-design` | 实验单位、伪重复、混杂、随机化/区组/DOE 选择需要方法语义 | 独立重写 gated `experiment-design-checkpoint`，统计功效仅作按需参考 | **建议 2** |
| `kdense-scientific-visualization` | honest encoding 与视觉语义检查有价值，但实现/导出大多是 Tool/模板 | 先拆 `figure-spec`、导出/元数据/视觉 QA capability；等待真实案例再决定 Skill | 否，保留 reserve |

表中的“建议 1/2”保留为当时的候选驱动判断，不再进入下一 Gate。2026-08-17 的 Human
Decision 选择 0 个来源候选直接重写，改为先完成 Mode Action Requirements，再以 `need_id`
汇总多个来源。四项均保持 `triage/reference`；`peer-review` 和 `statistical-power` 也不形成
主动开发清单。

## 2. 共同评估基线

每份 dossier 都与三条基线比较：

1. **no-Skill**：只给 Task Packet、Mode、输入/输出和停止条件；
2. **direct-tool**：只调用确定性 checker、文件/检索/计算/渲染 capability，不加载候选正文；
3. **compact Skill**：只加载不能由 Tool 表达的可复用语义约束，长参考按需读取。

完整外部 Skill 不作为默认第四条执行臂。只有 compact Skill 在困难任务中相对前两条稳定减少
关键错误，且上下文、审阅和修正成本可接受，才考虑 `trial`。

## 3. Dossier A：`gh-build-evidence-map`

### 来源与规模

- source：`github-awesome-copilot`，revision
  `a80885b76044550770f60f360f8a0e5ae3524a31`，仓库级 MIT；GitHub 托管不代表
  GitHub 编写或背书该社区条目。
- entry hash：`sha256:fb104196d94a0530eb5b86c56edfdaac0954a842f7cc71dfd4dcf87b20675fc9`。
- 107 行、5,080 bytes，静态估计 `low`；包还包含两个 `.mjs` validator 文件，首轮审计的
  `script_file_count=0` 没把 `.mjs` 计入脚本数，因此不能据此声称“无脚本”。

### 问题与适用边界

适用于一个有争议、需要显式展示支持、反驳、限定与缺失证据的技术判断。简单事实核验、单篇
提取、开放检索和最终决策不触发。可跨 evidence、theory、experiment、simulation 使用，但
Mode 决定证据标准与 Claim ceiling。

### 重叠判断

- 与 `literature-evidence-extraction` 高度重叠：原子 Evidence、稳定 locator、反证、缺失和
  来源边界已有项目契约。
- 与最小科研内核重叠：Claim/Evidence/Decision 已是正式对象，不应另造平行 source truth。
- 独特增量是四类推理边、所有节点通向 provisional position、无循环/孤立节点，以及把
  decision-changing gap 表达为 `unknown`。

因此不能照搬 `.doubt.json` 成为第二套 Evidence 存储。合理形式是项目 Evidence/Claim 引用
上的派生 map artifact；validator 只检查图结构，边的语义仍需 Human Gate。

### Tool、权限与上下文

- required：`document-read`、artifact read/write、evidence-map validator；本地验证不需网络。
- optional：显式授权的 source verification；只上传/请求批准的 URL 或 locator，禁止隐式
  读取新来源。
- direct-tool 基线：从已有 Evidence refs 生成/校验图 Schema、连通性、循环和孤立节点。
- 风险：把结构 VALID 误报为结论成立；复制来源 excerpt 增加版权/上下文；绝对路径不便迁移。

### 成功、停止与 Human Gate

成功条件：所有边均有可复核理由，反证和 unknown 没有被压平，position 不超出已有 Evidence，
validator 通过且明确标注 structural-only。

停止条件：来源未冻结、locator 不稳定、问题包含多个互不相干决策、图规模超过 Task 预算，或
边关系需要未授权的领域判断。Human Gate 判断 evidence weight、边是否真正蕴含目标，以及
unknown 是否足以改变决策。

### 处置

`demote-to-artifact-and-tool`。不占用两个 Skill 重写名额；在 M7-008/M7-003 中建立
`evidence-map-validate` capability 和 Task 模板。只有真实任务证明边类型选择需要一套稳定、
非显然的语义流程时才重开 Skill dossier。

## 4. Dossier B：`kdense-citation-management`

### 来源与规模

- source：`k-dense-scientific-agent-skills`，revision
  `43a3e619a1dd8f053abdeb258c87ce81c53b424f`，仓库级 MIT，仍按外部不可信处理。
- entry hash：`sha256:502331499c36890fdb37a00bbfca6dff2fb631ebe50684cec142c64e3a6566dc`。
- 329 行、15,048 bytes、20 个包文件、8 个脚本，静态估计 `high`；审计命中凭据、安装、
  进程、网络和大量外部 URL 信号。

### 问题拆分

原候选把五类工作捆在一起：发现论文、提取/补全元数据、BibTeX 格式化、citation validation、
写作集成。前四类中的检索、解析、格式化和远程查验主要属于 Tool；不能因为同处一个 Skill
就继承网络权限或 Provider。

可能值得保留的 Skill 语义仅是：把正文中的 claim/citation locator 与实际来源区域逐项对应，
区分“标识符有效”“元数据一致”“来源包含相关文字”“来源真的支持该 claim”，并保留冲突、
撤回/勘误、无法访问与未核对状态。

### no-Skill/direct-tool 与现有 Skill

- no-Skill：Task 可要求输出 citation ledger，但容易把 DOI 可解析误当作 claim 已被支持。
- direct-tool：`citation-resolve` 可做 DOI/题名/作者/年份/撤回状态和 BibTeX 规范化；
  `literature-search` 可发现候选；二者不判断 claim entailment。
- `literature-evidence-extraction` 从冻结来源生成 Evidence；新候选只应消费 Evidence/locator，
  不重复检索与摘录。
- `build-evidence-map` 处理多 Evidence 到 Claim/Decision 的关系；本候选只核对 manuscript
  citation 到 source region 的完整性。

### Tool、数据出口与权限

- required：`document-read`、`citation-resolve`、本地 citation-ledger checker。
- optional：`literature-search`，仅在 Task 允许补找来源时启用。
- 默认 network `forbidden`；若解析 DOI/元数据，数据出口应限制为 DOI、题名或最小书目信息，
  不上传未公开正文、手稿或项目材料。凭据与具体服务由 Adapter/Data Policy 决定。
- 外部写入始终禁止；BibTeX/ledger 只写 Task scope。

### 成功、停止与 Human Gate

成功条件：每个受审 claim 有 citation、source ref、locator、核对状态和限制；元数据冲突不被
静默合并；结构 checker 与已授权 resolver receipt 可复核。

停止条件：全文不可访问、同一 DOI/题名有歧义、locator 缺失、来源版本变化、需要付费/凭据但
未授权，或 claim 需要领域解释而非文字核对。Human Gate 判断来源质量、语义支持强度、合理
引用范围和是否需要替换/增加引用。

### 处置与困难任务

`derive-compact-skill`，建议进入名额 1。独立重写名为
`citation-claim-integrity`，目标正文低于 100 行，不含搜索命令、Provider、安装、BibTeX 教程或
写作流程。

困难任务至少包含：有效 DOI 但不支持附近 claim；支持方向正确但人群/条件不匹配；二手来源
引用原始结果；撤回/勘误；不可访问全文。比较 no-Skill、direct-tool 与 compact Skill，主要
指标是关键语义错判、漏报、人工修正时间和上下文成本。

## 5. Dossier C：`kdense-experimental-design`

### 来源与规模

- source/revision/license 同 K-Dense 上述记录。
- entry hash：`sha256:0071452b2927a75510a19019ac9a6a8e4b0ee7a3f2b27968b26dab1f164c465f`。
- 234 行、13,278 bytes、6 个包文件、2 个脚本，静态估计 `high`；明确依赖 Python、numpy、
  pandas、pyDOE3，并包含安装指令。

### 学科边界与净增量

随机数和 DOE 矩阵能由 Tool 生成，但 Tool 不会自动识别实验单位、伪重复、不可随机化因素、
批次/板位效应、干预污染、cluster、carryover、测量层级与计划分析是否匹配。这些是候选的
主要方法价值，也是不同学科不能共用一套僵化实验模板的原因。

建议只做“设计 checkpoint”，不包办完整科研计划：

1. 冻结问题、主要 outcome、实验单位与独立重复单位；
2. 显式列出处理、对照、可随机化/不可随机化因素和主要混杂；
3. 在候选设计间说明取舍，不自动选择唯一设计；
4. 生成设计 memo 与 unresolved assumptions；
5. 随机化表、DOE 矩阵和功效计算交给独立 Tool/按需方法参考。

当前 `experiment` Mode 尚未正式准入，因此该 Skill 即使通过困难任务也最多进入隔离
`trial`，不能在生产 Resolver 中隐式启用。真实案例可反向提供是否需要 M7-007 Mode 的证据。

### Tool、权限与统计功效

- required：artifact read/write；需要生成方案时使用 `bounded-compute`。
- optional：randomization/DOE generator、`statistical-power` 方法参考。
- network 与外部写入默认禁止；伦理、招募、临床/动物/生物安全系统的提交必须是独立 Human
  Gate 和外部写操作。
- `statistical-power` 不作为固定第二 Skill。只有主要 outcome、分析模型、SESOI、cluster、
  dropout 等假设已冻结时按需加载；观察后功效不作为结论。

### 成功、停止与 Human Gate

成功条件：design memo 明确单位、处理、随机化/区组、重复、主要 outcome、计划分析、混杂、
功效输入和剩余假设；生成的 schedule/matrix 可由确定性 Tool 重放。

停止条件：实验单位或 outcome 未定义、关键干预不可随机化但未说明、cluster/重复测量结构未知、
安全伦理边界未批准、资源约束与设计目标冲突，或要求 Skill 替人决定可接受效应/风险。

Human Gate 批准：设计代表性、伦理安全、主要 estimand/outcome、可接受误差/功效、资源取舍与
最终设计。Skill 不得把常见默认值当作批准。

### 处置与困难任务

`derive-gated-compact-skill`，建议进入名额 2，独立重写名为
`experiment-design-checkpoint`，正文目标低于 120 行。

困难任务至少覆盖两个异质场景：动物/细胞层级中的伪重复与笼/批次效应；工业/仿真 DOE 中
难变因素与 split-plot/运行顺序。若 compact Skill 只增加术语而未减少混杂、单位或分析错配，
则退回 Task 模板。

## 6. Dossier D：`kdense-scientific-visualization`

### 来源与规模

- source/revision/license 同 K-Dense 上述记录。
- entry hash：`sha256:d5b507dec004191eff12c5b387434b1666085b552c4c3c33713482689bc3d205`。
- 285 行、12,904 bytes、17 个包文件、8 个脚本，静态估计 `high`；覆盖 Matplotlib、Seaborn、
  Plotly、Pillow、pypdf、Kaleido/Chrome、样式和 publisher profiles，工具面过宽。

### 拆分与学科边界

应拆成三层：

1. `figure-spec` artifact：数据/变换/排除、统计单位、编码、uncertainty、缺失、目标介质、
   尺寸和 provenance；
2. Tool capabilities：绘图/渲染、导出、图像元数据、palette/contrast、文件检查；
3. 有界语义 review：是否误用面积/颜色/轴、是否隐去缺失/不确定性、是否把视觉强化当作数据。

不同学科需要不同图形规范：显微图、统计图、仿真场、网络图和交互图的错误模式不同。不能把
一个 publisher/Matplotlib 大模板设为全局 Skill，也不能把 WCAG 数值检查等同于科学可读性。

### 基线、权限和停止条件

- no-Skill：Task 可给 figure spec 和目标期刊要求；风险是忽略 honest encoding 和 provenance。
- direct-tool：渲染、尺寸/DPI/font/metadata、contrast、导出和视觉截图可自动检查；不能判断
  选择何种统计单位、误差表示或视觉编码是否科学诚实。
- required：data/artifact read、bounded compute、render/inspect；可选当前期刊指南读取。
- network 默认禁止；期刊要求若需联网，先确认版本与数据出口。图像生成或外部上传不是本
  dossier 的隐含权限。

停止条件：原始数据/变换不可追溯、统计单位不明、目标介质或尺寸未知、图像含敏感信息未获
授权、关键视觉判断无法在目标渲染尺寸复核。Human Gate 判断科学表达、可接受聚合/变换、
期刊合规和最终视觉质量。

### 处置

`split-and-reserve`。先在 M7-008 定义 `figure-render`、`figure-export-inspect`、
`image-metadata`、`visual-review` 等 capability，并把 figure-spec 纳入 Task/Artifact 契约。
等待至少一个真实高密度科研图案例证明 compact 语义 Skill 相对清单与 Tool 的增量，再决定
是否占用未来名额。

## 7. 下一 Gate

在用户/维护者确认两个建议对象后：

1. 为 `citation-claim-integrity` 和 `experiment-design-checkpoint` 各写独立 rewrite spec，
   不复制外部原文、脚本、资源或 Provider 命令；
2. 先完成 M3-008 最小 Trace validator，再执行同输入/模型/config 的 no-Skill、direct-tool、
   compact Skill 困难任务；
3. 每个对象最多一次有界修订，记录关键错误、人工修正时间、上下文/Tool/消息成本；
4. 结果只能是 `reject`、`retain-reference` 或 `continue-trial`；当前项目许可缺口关闭前不能
   自动进入 `accepted`。
