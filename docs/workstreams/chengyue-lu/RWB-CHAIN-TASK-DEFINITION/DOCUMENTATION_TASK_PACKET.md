# AUDIT-RWB-DOCS-003：全文档校准与精简

2026-10-07 路诚钺最新指令：

> 这轮提升为全文档级别更新，处理目前M系列task以及architecture系列一些有缺口以及歧义问题，而且部分文档出现了较为臃肿的问题，也一并在本轮处理。

在通用桥接任务定义基础上扩展为整个文档体系的校准。Root 负责总体一致性、实施协议/兼容索引、验证与交付；已有准备代理各负责互斥文档面。Root 保留唯一整链/API/Tool 测试执行权；当前先文档对齐，后按校准 Task 继续隔离桥接测试。旧 paused Goal 不操作。

## 输入与范围

基线 develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`，分支 `codex/research-chain-task-definition`。PR140 是独立未合并代码候选，只引用其明确证据，不写成 develop 能力。允许读取全仓文档的文件/标题 metadata，以及 active docs（根 README、docs 根、modules、implementation、compatibility、decisions 索引）。ADR 正文和历史 workstream 仅按 active 文档具体链接与待核事实定位；不递归读取历史原件、私有评价答案、API logs、Key 或账。

## 修改标准

- 按已有 accepted 文件契约、ADR 与具名权威解释；概念、执行、实现成熟度与真实测试证据明确区分。
- TASKS 唯一承载 exact Task 的状态/定义/依赖/验收；STATUS 唯一当前成熟度；ROADMAP 只承载架构方向/Gate；施工图只导航并链接 TASKS，避免重复状态表漂移。
- 稳定 Architecture/Modules/Development 说明正向结构，不堆实施日志、当前完成记录和历史争论。实现接口放 implementation，历史原证据保留可达，不重写已经接受的记录。
- 角色职责与模块/会话分别解释；角色可合并，child 0..N 由 main 在授权上限内决定，必载职责提示与可选方法 Skill 分开。Guide 使用独立只读上下文，不自动回传或污染 main。
- 新建/人工既有材料接入是入口策略；两者共用研究契约与 Mode/Method 流程，缺 MainState 保持 unknown，不制造历史接受或自动恢复。
- 原 DONE Task 行保持定义/状态/依赖/验收内容不变；过期派生 prose/index 修正或去重。三条新增 Task 定义保持候选 READY，不置 DONE。不改变对象身份/Schema、Mode routing、Human 边界或 Runtime ownership；需要此类改变时记录具体待决项并保留 accepted 基线。
- 精简保留独有规则、必需条件和证据位置，不为字数删除契约含义。全文档级别指全体系 inventory/一致性覆盖，不要求改写每份历史工件。

## 委派边界

所有 Profile 为 bounded documentation worker，required-Skills=[]。预算各 20 分钟、两轮；不独自在仓库，保留他人编辑。不得执行产品/API/Tool 测试、安装、读取凭据/账、commit/push、修改代码/Schema/config/Registry 或 primary memory。每组保存可见通信、实际阅读列表、变更依据、未解决点与 Compact handoff。

1. TASKS 组：只写 docs/TASKS.md、M_SERIES_IMPLEMENTATION_MAP.md、ROADMAP.md 及本目录 TASK_AUDIT/HANDOFF/COMMUNICATIONS。核全部 M 系列定义与派生矛盾、READY deps、owner 和桥接任务边界；压缩重复导航/状态。
2. 架构组：只写 docs/ARCHITECTURE.md、DEVELOPER_ARCHITECTURE_MAP.md、PROJECT_CHARTER.md、modules/*.md 及本目录 ARCHITECTURE_AUDIT/HANDOFF/COMMUNICATIONS。核模块启用条件、producer/consumer、角色/Skill/Profile 区别、入口策略、Human/Runtime 边界；去重但不引入固定 DAG/编制。
3. 读者面组：只写 README.md、docs/README.md、PUBLIC_GUIDE.md、SUPPORTED_FEATURES.md、GETTING_STARTED.md、STATUS.md 及本目录 SURFACE_AUDIT/HANDOFF/COMMUNICATIONS。统一入口/证据等级/成熟度，清除 current 与 historical/candidate 混写，减少重复。

Root 处理 Development、implementation/compatibility/history/decisions/workstreams 索引及受链接指向的活跃协议说明；核互相引用、源码元数据与现行证据，保存全文件覆盖清单和链接报告。所有测试由 Root 执行。最终 docs-only PR 记录具体问题/修复、阅读覆盖与待决缺口；独立代码 PR 不夹带 Task 定义。未经授权不 merge/release。
