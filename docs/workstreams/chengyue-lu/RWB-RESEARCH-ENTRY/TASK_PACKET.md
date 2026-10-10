# AUDIT-RWB-ENTRY-001：实施与协作Task Packet

2026-10-07；人类授权全文与分项见[README](README.md)。required-Skills=[]。Root协调、实现集成、测试、PR；候选有效风险R2（角色读写/执行绑定与状态边界），不是新增core authority。

## 输入与停止

- 基线d3c4d23；先读AGENTS/README、primary PROJECT_MEMORY对应M5/M12导航、docs/README/DEVELOPMENT/ARCHITECTURE/STATUS/TASKS和相关模块。之后仅读各组明确的源码/Schema/fixture/tests；新内容先metadata发现并说明直接必要性。
- 角色运行草案与十模块盘点的当前人类批准用于此隔离分支；接口以基线真实实现为准。不读旧私有API Attempt/Key/账/private oracle，不复用合成资格为真实执行。
- 本轮离线实现/确定性测试不调用付费模型或生产Tool。实际API验证沿用Root单窗口规则，须另检查当前授权/time/source/config/历史；不由新窗口执行。
- 遇核心身份/选择路由/Human boundary/Runtime ownership改变、权限扩大、正式Task定义缺口，保存候选设计并停止该越界切片；不阻断可复用接口内的隔离实现。需要formal M Task时另提docs-only task-definition；不得伪造M12-001已READY。
- 不merge/push main/develop、不改protected配置（本地新worktree只补既有memory policy且不stage）、不触碰其他窗口文件，不生成global memory；保存失败与unstarted事实。

## 新窗口 PLAN-M12

Agent Profile：bounded continuity-planning agent；required-Skills=[]。只讨论M12，不实现恢复/新Task/Schema。

输入：共同入口；docs/modules/06-CONTEXT_GOVERNANCE、docs/TASKS/ROADMAP的M12与Topic5；当前Phase-C closeout候选及已有M12-BOUNDED-CONTINUITY文件metadata，必要正文按索引定向读；src/context、execution/recovery接口及直接tests。既有PR137只作为参考，不续改或代为接受。

独占写域：本workstream`m12/PLAN.md`、`m12/COMMUNICATIONS.md`。输出：已实现/预留接口、普通人工再启动与Topic5恢复分界、PhaseC/ADR/task-definition前置、最小候选任务名称/依赖/验收、与本入口的接点和短期/远景；给Root Compact hash与≤10行结论。预算20分钟/4轮，禁止再委派，不写primary memory（给Root proposed entry）。

## 新窗口 PLAN-FRONTEND

Agent Profile：bounded frontend-product and intake-planning agent；required-Skills=[]。规划需求配置前端及人类产品交互，不写代码。

输入：共同入口；docs/modules/02-PROTOCOL_AND_MODES、03-AGENT_RUNTIME、05-TASK_AND_HANDOFF、06-CONTEXT_GOVERNANCE；scaffold/CLI/protocol与相关Schema/模板的直接接口。沿已有契约，不创造Prompt字段权限、Release、固定child或新建/接续Mode。

独占写域：本workstream`frontend/PLAN.md`、`frontend/COMMUNICATIONS.md`。输出：人类输入→内部角色→工件→human output各环、合法bootstrap、现有参数映射、错误/unknown/human决断、独立Guide视图、产品UI短期/远景与可验收任务候选。说明配置前端Agent与图形前端区别。预算20分钟/4轮，禁止再委派，不写primary memory。

## Root实现与委派

可向已有子代理分配有界代码ownership，必须在可见消息中给Agent Profile、required-Skills、输入、互斥路径、输出、预算与停止；各组不是唯一参与者，不撤销他人修改。Root独占公共CLI集成、workstream根文档/COMPLETION/RISK/WORKLOG及PR/Git操作。

Archive触发：多窗口/代理协作。本workstream通信存可见任务和消息、关键事件、不可变交付path/hash；不存隐藏推理、秘密或原始科研材料。普通测试结果按命令/结果/错误定位，不要求把每次文件打开写成日志。
