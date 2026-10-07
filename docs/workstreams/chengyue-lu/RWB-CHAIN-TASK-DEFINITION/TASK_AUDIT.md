# TASKS 组文档审计 — AUDIT-RWB-DOCS-003

2026-10-07；Profile：bounded documentation worker；required-Skills：[]。本组在两轮有界工作内编辑文档；未执行产品/API/Tool 测试、联网、Key/账、安装、commit/push、config 或 memory 操作，未再委派。

## 基线、读域与写域

checkout HEAD/base：`d3c4d23206339ebc7f18b5621f3aa5453f96335e`，分支由 Root 指定为 `codex/research-chain-task-definition`。开始时 TASKS/ROADMAP/施工图已有 Root 的三条 READY 候选和桥接导航；它们保留，不把未合并定义或 PR140 代码候选写成 develop 能力。共享 config/STATUS 的并行改动未触碰。

实际写域仅为 `docs/TASKS.md`、`docs/ROADMAP.md`、`docs/M_SERIES_IMPLEMENTATION_MAP.md` 与本目录的 `TASK_AUDIT.md`、`TASK_HANDOFF.md`、`TASK_COMMUNICATIONS.md`。

实际阅读：

| 来源 | 实际范围及用途 |
|---|---|
| 本目录 DOCUMENTATION_TASK_PACKET、README、RISK_LEDGER | 全文；最新人类授权、组 ownership、候选/接受边界 |
| checkout AGENTS、README；docs/README、DEVELOPMENT | 全文；文档权威、任务状态机、风险/owner 和 module-level DAG 规则 |
| TASKS | M0–M11、M14 全部 100 exact 行及全部 prose；M12/M13 reservations；首次输出截断后补读 116–223 行，核全部定义、依赖、owner 与历史边界 |
| ROADMAP、M_SERIES_IMPLEMENTATION_MAP | 编辑前全文；宏观 Gate、全部 M-family 导航及重复派生状态 |
| implementation/README、compatibility/README、decisions/README | 全文；active 协议与显式历史入口 |
| implementation/PHASE_C_BOUNDED_GATE | 全文；machine proof/Human semantic closeout/Topic 5 区别 |
| M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION | 全文；canonical DONE 的 exact 受限接受及新 purpose 的适用性要求；不跟入 raw Attempt/CHECKS/原件/账 |
| M14-CURATED-RELEASE/FIRST_RELEASE_COMPLETE | 阅读返回可见的开头、exact identity、review、CI 与 actual-main 分发开头；组合输出尾部被截断；只据前部明确首发事实去除派生矛盾，不重新验证远端/附件 |
| ADR-0019/0020/0021 | active 链接触发的标题/目标词命中行；不声称逐字通读 ADR 正文，不改 accepted ADR |
| docs/modules、implementation、compatibility、decisions 的文件名 | metadata inventory；不递归读模块正文或历史 workstream |
| 三份修改文档的内部链接目标 | 文件存在性；fragment 目标仅抽取 heading metadata，核 90 个路径/18 个锚点 |
| git HEAD/status/diff stat | metadata；不提交、不推送，不读取其他 agent 工件正文 |

没有新读代码、Schema、Registry、候选 Skill 正文、private oracle、原 logs 或真实账。

## 具体问题与修复

| 问题 | 定位与修复 | 保留边界 |
|---|---|---|
| TASKS 的“未完成索引”含多项 DONE 和重复完成日志 | [责任索引](../../../TASKS.md#task-责任与阶段索引)改为具名 owner/risk/Phase/Topic 表，状态/验收只由 exact 行拥有 | risk 与 review 分工保留；不修改原 DONE 定义 |
| M6-010 owner-index 的旧 BLOCKED/未合入 PR131/raw Attempt token 摘要与 DONE 冲突 | 删除派生运行日志；链接[受限收口](../M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)，说明 exact Flash、binding/purpose 适用性和十一厂商 offline/live 区别 | 原报告 warning 和 unknown 均留在历史来源，不代签 live/A4/pilot |
| ROADMAP 把 M5-007 写为正在实现/IN_PROGRESS | 用方向/Gate 说明替代状态快照，保留 Protocol/qualification/pairwise/overlap、pilot 与正式评价的独有约束，详情导航到 active 协议 | exact 状态只看 TASKS；不改 M5 四臂或净价值身份 |
| 施工图的 M14-005 同时出现 BLOCKED 与 DONE，大量状态图重复 TASKS | 删除派生状态图，保留 family 图、原子阅读路线、active contract/completion links 和 reservation activation | M14 release 信任边界保留，每次发布独立决定 |
| TASKS 重复一套较窄的 PARKED→DONE 例外，易与 DEVELOPMENT 5.2 漂移 | [施工规则](../../../TASKS.md#施工与证据读取规则)仅引用 DEVELOPMENT 的通用 module-level DAG 条件 | 不改状态机，不自动恢复 PARKED |
| 旧“multi-Agent orchestration 禁止”与新 M2-009 有界 child 易混读 | [Topic 4 Gate](../../../TASKS.md#topic-4--topic-5-权限-gate)和 ROADMAP 区分 caller 的有界 Task 提议/独立冻结与 Host/Runtime 的自主路由、重选、隐藏编排 | Host ownership、Resolver 唯一选择权、Human ceiling 不变；不引入 Supervisor/coreRole/固定团队 |
| 没有新 Task 间 hard dependency 易被误读为无需整链 | M11-008 导航明确必须实际消费前两切片的 producer 产物，不由 callback/单模块 PASS 替代 | 三入口依赖仍全为既有 DONE，不臆造新 Task/相互阻塞 |
| 人工 MainState、Guide、checkpoint 易被误读为自动恢复 | 文档说明人工显式输入/unknown、Guide 独立 approved-ref 只读、无默认主聊天/logs/全仓读取、无科研写入/自动回传；采纳为新 main 输入 | Topic 5 freeze、Phase C Human/R2 与独立 review/task-definition 保持 |

ROADMAP 从 452 行收束为 196 行；施工图从原约 240 行收束为 96 行。精简删除重复状态和实现日志，保留独有 Gate 条件、解释上限、direct+最多一个实验策略与证据导航。TASKS 全部旧 exact 行和三条新增候选完整保留。

## 静态核对

- exact Task ID 100 个无重复：DONE 72、READY 3、BLOCKED 6、PARKED 19；无新增或改变 Task 状态。
- 72 条原 DONE 的行内容按原顺序 UTF-8/LF 联接：修改前后 SHA-256 均为 `cd72a0c7d01e6473954f4a2b932f4290d54844cac2705686972c332d7d8ff5f7`。此检查比较行内容，不以整文件换行风格作为 Task 定义。
- M1-010：M1-003/M1-004/M1-005/M1-007/M8-003/M8-005 全 DONE；owner 路诚钺/R2。
- M2-009：M2-002/M1-004/M2-005/M3-008/M6-002 全 DONE；owner 路诚钺/R2，黄毅复核 Session。
- M11-008：M9-005/M6-002/M11-004 全 DONE；owner 黄毅/R2，路诚钺复核控制/权限/Trace。
- 三份文档的 90 个内部 Markdown 文件路径与 18 个 heading fragments 全部可解析；无产品脚本或产品测试运行。
- ROADMAP/施工图不再复制 DONE/BLOCKED/IN_PROGRESS Task 状态表；canonical Task 行仍唯一权威。

## Source pins 与交付 pins

| 相对文件 | 读取时 / 交付 SHA-256 |
|---|---|
| TASKS（Root 候选输入） | `cc95d5686b7a9f782d62baab9cf1652ff4eaaee9a41ef7cce8250f7cf5529938` |
| ROADMAP（Root 候选输入） | `8e02d48dca313d88c23c73dcf7280a12e7597be79c647942cac88b3d58850166` |
| M_SERIES_IMPLEMENTATION_MAP（Root 候选输入） | `756b24861df88255717dfc36789fcabb38db6c4f540074bde1bc411521ef7c38` |
| DEVELOPMENT（读取快照） | `a8155269c627b6476467f1f019e8373a356925a53a59965637c5c44a86601d8a` |
| 本轮 DOCUMENTATION_TASK_PACKET | `b6703437ea5e82a49502c93214041af43c194850f99803233819428ddba8d2c4` |
| M6-010_COMPLETION | `b86cef1a1db662be2cbcf1bd2f49e75ee1aaefa6086e342ac0905bd3d5059c2f` |
| FIRST_RELEASE_COMPLETE | `222a9c18214290b4e2b69f45cb0af6725ab88bae8940f62ad2c6b421961f93c5` |
| PHASE_C_BOUNDED_GATE | `fc80c8f73334c7ad312c256b25c960762e238f883d1f11dd504aa85316dd20ca` |
| TASKS（本组交付） | `1beb8e4ad6e4f8a0ca9f8cb10b4effe9ceefe94eae929838e26bb57af7fee566` |
| ROADMAP（本组交付） | `0b51328107949d55e591046011263cebbfc6e4b03a5ea02831568983a919296e` |
| M_SERIES_IMPLEMENTATION_MAP（本组交付） | `2836f6f6a287894f2b19e32c309ef2da8494128eeb2b40b06893752acd3e18a8` |

## 局限与下一动作

未重验历史 CI、远端 release/live acceptance、源码消费者或 PR140 整链；它们分别由来源证据和后续具名 Task 承担。旧 DONE 行中的 family/range dependency、PARKED 历史前驱及 M6-006 Part C 快照保持原样，不改写已接受 identity；新 READY 使用 exact IDs 并满足直接 harddeps。

Root 整合其他组与本组报告，执行文档/治理验证及跨表面复核，维护 primary memory 和 PR；本组无此写入权。Root 可在当前人类授权与正式 Task 计划下继续隔离桥接测试，测试不使候选定义自动成为共享接受，不置三 Task DONE。交付后停止。
