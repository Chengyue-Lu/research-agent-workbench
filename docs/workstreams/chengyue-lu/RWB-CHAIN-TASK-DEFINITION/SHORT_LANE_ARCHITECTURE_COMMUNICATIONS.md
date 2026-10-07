# 统一入口短程架构：可见通信

2026-10-08；AUDIT-RWB-DOCS-005；架构文档工作者。本文使用仓库相对路径；DOCSWT 表示 PR141 文档工作树根。原始 Packet/可见传递留存于 ignored `.rwb/docs005-communications/architecture.md`。公开记录规范化路径、组织定位及限定，不是 byte-exact 原件。

## 收到的范围与约束

协调者分派 bounded documentation worker，required-Skills=[]，预算 15 分钟/两轮。允许读取 AGENTS、docs/README、DEVELOPMENT、Architecture/DeveloperMap、模块 03/05/06/09、STATUS 和原 REALIZATION_PLAN。写域为六个架构面以及本 workstream 的 SHORT_LANE_ARCHITECTURE_HANDOFF/COMMUNICATIONS；原始传递另存 ignored 目录。其他工作者同时写 Task/plan/ADR 和窄合同审查，须保留其更新。

协调者转述的人类要求为：一个对话框先区分 Guide 查询、与 Guide 同级的独立短程局部修改和需 Protocol 的完整研究；短程写后评估 Main State 影响；main 保持原 Task，旁路默认不回传/污染 main，普通入口不任意修改 child。本 PR 只定义设计和 M 任务，不实现或调用 API。

设计约束包括最小 Task 与合法冻结执行边界、写前占用/冲突协调、按语义影响分流、写后 none/relevant/unknown 状态提案、人类明确采纳与 current state pins、活动 main/child 的最小失效通知、文件维护与语义状态分离。保留 Human/Resolver/Host 功能权威；不能用后置评估补授权、自动恢复或科学接受。新 ADR/详细设计由协调者维护，架构侧只链接和摘要。

## 发出的可见更新

1. 开始更新：将统一入口、Guide 和独立短程任务职责接点补入授权架构文档，明确候选与当前支持的区别；详细规则链接协调者 ADR/设计文稿，保留他人编辑。
2. 中间更新：现有 Guide 是独立只读职责，执行链由冻结 Bundle/View 与权限交集约束；补短程写前冲突协调和写后影响评估，将待采纳提案与正式 Main State revision 分开。
3. 发给协调者：六文件已补候选小节，包含 Protocol 编译前分流、main 旁独立职责、minimal Task/Method/Requirement/Bundle/View、写前协调、写后影响分类、采纳/pins 与失效通知；未实现/检查，进入第二轮文字自核和持久化，请协调者统一验证新链接。
4. 收尾更新：六架构面完成第二轮文字复读；none 示例要求相关语义均未改变，活动 main/child 的输入失效仍须通知；保存读写范围与通信，文档检查由协调者完成。

## 执行事实与交接

收尾时协调者传递人类校正：统一入口是既有主线外的前置/新分支；具体意图、路由与影响判断由角色绑定的 Skill 或提示词承担，不在架构/内核硬编码。已在六文件补职责/权限/I/O 边界、版本绑定和评审的 Prompt/合法 Skill、结构校验与语义判断区别、低置信澄清/提案，以及既有主线保持。Guide/Short 为概念职责，不是独立固定 API 角色。没有改协调者 ADR/spec/TASKS。

本工作仅以文件正文读取、按段补读、metadata/hash 定位及精确 patch 完成授权文档修改。第一批输出截断后补读相关段；第二轮明确上游选择冻结 model/API binding，并补齐 none 示例的敏感语义。没有执行测试、Host、API、生产 Tool、cold、Key/账读取、Git mutation 或 primary memory 写入。

正式工件与实际读写范围见 [Compact Handoff](SHORT_LANE_ARCHITECTURE_HANDOFF.md)。当前结果为设计候选摘要，不能替代协调者 ADR/Task 审阅、文档验证或人类批准。
