# AUDIT-RWB-DOCS-004 Compact Handoff

日期：2026-10-08（Asia/Shanghai）。状态：隔离文档候选；授权写域的两轮人员限制清理完成，范围外接合待 Root 处理。Profile：bounded documentation worker；required-Skills：`[]`。

## 结果与边界

依据本轮明确指令，在12个稳定文档中移除具体人员开发分工、双方审查、实名 Task owner 和具名维护者限制。模块通过契约连接；读取范围须有明确扩展决定；Skill Need 保留独立维护外环 triage。Human、Resolver、Host 的功能权威、权限/数据边界、Skill 人类准入及科学接受保持独立，模型不能代为批准。

本结果不表示已合并、全仓人员限制已撤销、远端门禁已变更或真实运行已验证。现有消息契约的 `accountable_owner` 示例字段及 `TRACE-ACTOR-UNOWNED` 名称保留；说明改为运行归因与授权关联，示例值为 `human-example`，不指定开发负责人。本轮未修改代码、Schema、Registry、config，也未重新定义这些运行字段的验证语义。Root随后明确：ADR-0023撤销固定人员开发规则，不取消Schema运行授权identity；本轮字段处理与该边界一致，未读取新ADR原件。

## 改动清单与冻结字节

下列哈希来自本轮修改后文件字节。之后其他任务的修改须重新计算，不能沿用本表。

| 文件 | 本轮改动 | SHA-256 |
|---|---|---|
| `docs/ARCHITECTURE.md` | 改用功能选择权威与明确 Human 决定；Need 保留独立维护外环；明确模型不得自批 | `64d35dbac4c4b4aff7ce13bb874977ca49074f8dcccdae988ee50b73c49a5baa` |
| `docs/DEVELOPER_ARCHITECTURE_MAP.md` | 去除两人分工与具名负责人，改为模块/契约接点 | `0ebfec879b278423c9b8968a1859576c731bb1915c1bc992fb67f419f6b6179d` |
| `docs/PROJECT_CHARTER.md` | 用执行要求与人类保留决定表达产品边界 | `970298ac8ee0c54d277828c27ce1f28ca0f673b54ede942577fdd340056162cf` |
| `docs/modules/03-AGENT_RUNTIME.md` | 删除 API/控制两人维护分配 | `5cb35e0938fc6b0550287849808539abf38b7b9af3edf0de8f1dec2d9cba67b9` |
| `docs/modules/04-SKILL_SYSTEM.md` | Resolver 保持唯一选择权威，Need 保留外环 triage，取消具名维护者限定 | `552f6c8ad68d403c05e19e4fca8020c41a995038b90f3fafbbc871540f62cca3` |
| `docs/modules/05-TASK_AND_HANDOFF.md` | 读取扩展不绑定实名 Task owner；归因预警沿用契约字段 | `6ea221b76f5b187d23197de8e0fd25e65feed10f1b9d8b3ded6b5ac38ca8f8fe` |
| `docs/modules/06-CONTEXT_GOVERNANCE.md` | 读取扩展改为明确 Task 范围决定 | `7bdf475c25f9d071bf8a0fd226a888cd0a957a0ce2bdddb32bb9b601a4839067` |
| `docs/modules/07-ARTIFACTS_AND_PROVENANCE.md` | 去除实名负责人及人名示例，保留运行身份/授权归因与消息字段 | `f9c0c14742e5f3a178dbf6a11689a1e0612b401612630092456a00fc6616988e` |
| `docs/modules/08-VALIDATION_RISK_AND_GATES.md` | Human Gate 以明确人类决定表达，不绑定姓名或开发分工 | `76ba602c1b6a3d157250cac15efed2f1dc1afb5a6daa49e2971a70c20c1bbcb6` |
| `docs/modules/09-ADAPTERS_AND_INTEGRATIONS.md` | 删除两人维护与双方审查，保留跨界契约一致性及授权依据 | `347493e6c05f7475841c22b36b56f7086e2c3b4b85474e6452c71ce834c0ccff` |
| `docs/modules/10-OBSERVABILITY_EVALUATION_COST.md` | 用运行归因/授权关联替代实名负责人，保留 Human 准入 | `65ec0cbbedebd1ee1d57fb9cda39f10d9ccc2309ca5d8e2be05ee7d6a64be94c` |
| `docs/modules/README.md` | 导航改为开发与贡献规则 | `b65d7e6f63ee18b6e7a922f6d4d60adce69bb0f5a0c667dc3951e22b087e13fd` |

## 两轮复查

1. 第一轮：读取指导与相关上下文，用精确 patch 清理上述12个文档；未回退其他改动。
2. 第二轮：对授权稳定文档搜索人名、负责人/责任人、实名/具名、双方审查、cross-owner/跨 owner 等。未发现实质人员分工残留；`工具名称` 等普通词误匹配不作为问题。`accountable_owner` 是保留的消息格式字段；Maintainer 是可选维护功能；历史工作流链接保持原路径。

本轮未运行产品、Tool、API 或 docs 测试。既有 Markdown 链接目标与标题未改变；两份新交接文档的本地链接作文件存在性静态核对。完整链接/anchor 与 docs CI 由 Root 执行，不能将本轮字符串复查称为测试通过。

## 范围外剩余匹配

以下定位来自只读指导或 `rg` 文件名/匹配行发现，快照时间为2026-10-08 01:31左右。未展开历史 workstreams/ADR 原件；已完成 Task 和历史证据不在本轮修改范围。匹配定位需要 Root 回读当前内容再处理，不能直接据此批量替换。

| 表面 | 待处理定位 | 本轮处置 |
|---|---|---|
| `AGENTS.md` | 10、21、28 | 只读：两人分工、named Task owner、指定维护者例外 |
| `docs/DEVELOPMENT.md` | 6–15、21、55–59、91–95、121–133、149–183、206 | 只读：实名分工、cross-owner、指定例外及远端约束说明 |
| `docs/README.md`；`docs/STATUS.md` | 33；5 | owner 导航字段；Root 与 TASKS 更新一起核对 |
| `docs/TASKS.md` | 5–9、34、87、117、124、132、201、212、239–284、300 | active 分工/未完成任务/后续定义字段与指定复核；DONE 原行保持历史定义 |
| `docs/ROADMAP.md` | 23、40 | 具名 owner 与导航；功能型 Maintainer 外环不作为人员限制删除 |
| `docs/DEVELOP_TO_MAIN_RELEASE.md` | 17、31、60、64–66、77 | 发布负责人、owner/cross-owner 审查；远端有效规则须另核对 |
| `docs/GETTING_STARTED.md` | 121 | 任务负责人决定后续 |
| `docs/M_SERIES_IMPLEMENTATION_MAP.md` | 4、40、91 | owner 字段/具名要求及 M6 人名标题 anchor |
| `docs/templates/TASK_WORKLOG.md` | 32、36、47、78、95 | 人名例子与 owner 字段；消息字段是否改变须独立处理 |
| `docs/implementation/IMPLEMENTATION_PLAN.md` | 18、31 | 实名维护与 API 人员分工 |
| `docs/implementation/PROVIDER_ADAPTER_PLAN.md` | 3 | API 人员维护绑定 |
| `docs/implementation/REPOSITORY_LAYOUT.md` | 42、48 | 实名责任/目录说明 |
| `docs/implementation/SKILL_CANDIDATE_PIPELINE.md` | 3、12 | 两人分工与具名 triage |
| `docs/implementation/SKILL_EVALUATION_PROTOCOL.md` | 3 | 评估/执行两人分工；科学评价的人类边界保留 |
| `docs/implementation/SYSTEM_EVALUATION_PROTOCOL.md`；`SYSTEM_EVALUATION_HARNESS.md` | 3–4；3 | Evaluation/Execution owner 绑定 |
| `docs/implementation/SKILL_NEED_CONTRACT.md`；`METHOD_RESOLUTION_CONTRACT.md` | 34；82 | 具名 Maintainer 要求；维护外环语义保留 |
| `docs/implementation/RELEASE_SURFACE.md`；`CLAIM_TRACE_CONTRACT.md` | 3；4 | 文稿 owner 绑定 |
| `docs/implementation/PHASE_B_EVOLUTION_GATE.md`；`PHASE_C_BOUNDED_GATE.md` | 56；30 | 跨负责人 R2 审查/owner 叙述；原 Gate 证据不能改为已接受 |
| `docs/implementation/EXECUTION_TRACE_ADAPTER.md`；`ARTIFACT_PROMOTION_CONTRACT.md` | 25；193 | 现有 accountable-owner 运行要求/owner 验收，需区分描述与实际契约 |

GitHub URL、历史路径、DONE 人名与普通 reviewer/功能型 Maintainer 匹配未归类为新的开发分工限制。发现搜索也命中过 `docs/references/second-round-audit/` 的 reviewer 用词，仅有匹配行进入上下文，未展开正文，未作为 active 清理目标。

## 实际读集与禁止项

- 内容读取：本 worktree 的 `AGENTS.md`、`docs/README.md`、`docs/DEVELOPMENT.md`；Architecture/Charter 全文；Developer Map 相关段；模块03–10与模块导航的人员/权限/归因相关匹配及局部上下文。
- 元数据/匹配行：授权 modules 的文件列表和限制搜索；范围外 active docs 的文件名与匹配行；改后 SHA-256。没有递归展开命中链接、历史 workstream、ADR 或其他工作目录。
- 写入：本表12个稳定文档与当前目录两份交接文档；Root后续授权增加 ignored `.rwb/docs004-communications/architecture_review_147.md` 保存原始可见payload。未修改 DONE Task、历史原件、产品、Schema、Registry、config、Git 状态或 primary memory；未读取 Key、实际账或执行日志。
- 可见通信见[通信记录](REALIZATION_ARCHITECTURE_COMMUNICATIONS.md)。

## 下一步决定

Root同步ADR-0023与范围外开发人员限制，核对有效远端治理规则。Root已明确运行授权identity保留，本轮不提议撤销这些字段；现有门禁不因本文而自行改变。Root 执行适用 docs/link 检查、PR/commit；本轮不需要新增科研或 API 测试，也不产生 Human/科学接受。
