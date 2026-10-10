# AUDIT-RWB-DOCS-003 读者面审计

2026-10-07。Profile=bounded documentation worker；required-Skills=[]。基线由本轮 Task Packet 声明为 develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`；本 worker 未使用 Git、API 或产品测试重新确认。写域仅本表六个读者面和 SURFACE 专用归档。

| 表面 | 实际问题与判断 | 修复 | 保留边界 |
| --- | --- | --- | --- |
| [README](../../../../README.md) | 系统能力与角色部署易被读成固定模块/agent 映射；scaffold 被概括为项目而未强调仅文件生成 | 增加模块/角色/会话区别、main 动态子任务、baseline/可选 Skill、Guide 独立解释；称 no-Skill 文件模板 | 不新增 CLI 或宣称 PR140 producer 已被 develop 接受；稳定页不放 M Task 状态 |
| [docs/README](../../../README.md) | Public support 与 Status 同时声称成熟度/当前能力权威 | 精确区分公开使用契约、STATUS 工程成熟度、TASKS exact 定义/状态，说明 source 身份 | 开发导航可链接内部权威；curated public 页面不新增这些链接 |
| [PUBLIC_GUIDE](../../../PUBLIC_GUIDE.md) | Research State candidate/fresh actor 与常规 MainState 入口混在一行；Profile 类型难区分 | 增加 Agent Profile ceiling 位置，分开 MainState 与研究状态候选，解释模块/角色/Skill 区别 | 源码存在不证明当前任务适用性；Guide 职责与一键入口分开 |
| [SUPPORTED_FEATURES](../../../SUPPORTED_FEATURES.md) | 首段重复当前成熟度；Trace/MainState 与候选混列；“首次发行须…”未明确已发布 alpha 身份 | 保留四证据等级与接口矩阵，加入 exact live 适用性、候选独立限制、已发布 alpha/后续发布决定区分 | 无到 excluded STATUS/TASKS/workstreams 的 public 断链；空 Projection、无科研净收益结论保持 |
| [GETTING_STARTED](../../../GETTING_STARTED.md) | “不假设可下载发行物”与首发记录歧义；源码安装易借用 alpha 的多 Python 验证；“发布 Skill 资源”与空 Projection 歧义 | 明确 alpha 附件与源码身份、没有 PyPI、空 Projection 无随包 Skill；已有非空材料不 init，缺 MainState 保持 unknown | 所有受支持 CLI 命令原样保留；安装/重建命令未执行；材料接入只说明策略与显式接线 |
| [STATUS](../../../STATUS.md) | 日期与顶部候选混杂，已实现/受限表大量重复长篇历史；首发、Provider 部件 live、M5 Gate 与 PR140 未清楚分层 | 改为来源身份、13 类实现与 6 类限制的 compact 表，每行 exact contract/证据链接 | 原 DONE Task、历史原件和 API报告字段不改；PR140 独立未合并；选择性 live 不变全链或 evaluated |

## 源事实对照

首发记录固定 `v0.1.0`、source/main/tag/附件闭包与 checkout 外安装，说明未上传 PyPI；因此安装说明不能继续让读者误以为没有 alpha 附件。后续 develop 修复未自动进入该 tag。

M6-009 收口仅接受离线合同。M6-010 收口在历史报告外接受 source66/installed002/native005 的 exact Windows/Flash 部件，历史 `live_qualified=false`、warnings 与 unknown 成本保持；它不接受全部厂商、OpenAI、M11 E2E、A4 或 M5 pilot。STATUS 的 live 一行保留这个外部决定/原报告区别，不重写报告。

M5-007 整项历史收口仍写当时 M6-004 blocker；现行 M5-008 Gate 与 TASKS 已采用 M6-010，并保留 A4 admission/pilot 专项授权。采用现行权威解释接续，将旧收口视为原时点事实；历史原件不修改。真实 pilot/正式评价与通用桥接候选保持独立。

原 STATUS 的独有契约边界已保留到对应分类行：Method 不绑供给、Authority 不授权限、Snapshot 不等实际执行、唯一 Resolver、Host 不做 fallback/recovery、closeout 仅 slice completion、Skill index 空、promotion 不认证历史、候选最终表示/人类接受独立、负结果与未知测量保留。具体版本/hash/count/CI 与授权时间窗口留在其 exact 原始证据，不在成熟度页再次维护副本。

## 实际阅读

全文：AGENTS.md、根 README.md、本轮 DOCUMENTATION_TASK_PACKET.md；六个 owned surfaces 修改前与静态检查读取后的完整 UTF-8 内容；FIRST_RELEASE_COMPLETE.md、M6-009_COMPLETION.md、M6-010_COMPLETION.md、M5-007_COMPLETION.md、compatibility/README.md。长证据批读有输出截断，M6 两份单独重读，M5 顶部单独补读后才使用事实。

有界读取：M5-008_LIVE_PILOT_GATE.md 前 110 行；TASKS 中相关 Task 行，仅用于当前状态与 Gate 对照；implementation/README.md 和本 workstream README.md 的标题/指定关键词命中。元数据：implementation 文件名、workstream 目录名、docs 范围的标题/文件名发现；源码链接只做存在性检查，没有读取源码正文或其他代理域。

## 验证与未决

静态检查六文件严格 UTF-8、本地链接目标存在及公开 excluded-link 边界：128 links，0 issues；公开 README/PUBLIC_GUIDE/SUPPORTED_FEATURES/GETTING_STARTED 无 M Task 状态、PR140 或机器绝对路径命中。Markdown 目录链接计为合法目标；本 worker 不认证 release projection、远端发布、产品执行或全体系锚点。

Root 继续负责全文件 inventory/标题锚点/public projection 的统一验证，以及跨 TASKS/架构/implementation 面的最终一致性。PR140 实际桥接/Skill 文件装配仍由 Root 唯一测试者处理；此文档任务没有运行或提升任何测试候选。
