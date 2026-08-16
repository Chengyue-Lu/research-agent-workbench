# ADR-0013：项目级 K-API-2、Agent Trace 与显式 Model Assignment

状态：Accepted

日期：2026-08-16

共同确认：路诚钺（Mode–Skill、读取、Handoff、Trace 语义）；黄毅（Provider、隔离 API 执行、模型调用）

## 背景

现有 `K-API-2` 已证明一个明确的 H2 evidence Task 可以经 fake-local Provider 完成文件关闭、防重放和 fresh-process 恢复，但编译器、输出准入与 closeout 仍硬编码单一 evidence 合同。ADR-0012 已要求实名 actor 与可回放 Agent Trace，却尚无机器可验证的 Envelope、Index、Event 和 capture-gap 合同。模型池虽然坚持显式槽位，运行时仍只持有瞬时 `ModelBinding`，不能审计一次 Attempt 为什么使用该槽位、请求模型与 Provider 实际返回是否一致。

因此，继续增加 Provider 或 Mode 会扩大未冻结接口。当前应先把项目级执行标准、Trace 边界和模型指派冻结为兼容添加，再用 evidence/H2 与 simulation/H1 两个合同证明管线不依赖单一科研输出。

## 决定

### 1. 项目级 K-API-2

“项目级 K-API-2”只有在同一隔离执行内核同时满足以下条件时关闭：

1. 通过精确、无排名的 `ExecutionContract` Registry 选择合同；未知或多重匹配在 Provider 发现与调用前阻断，不默认、不降级、不回退。
2. 内置 `evidence-h2@0.1.0` 与 `simulation-h1@0.1.0` 两个合同。前者保留 Evidence、Handoff、Transfer Manifest/Audit；后者产生 Simulation V&V Report、Compact Handoff 和仅证明结构/引用/Claim 边界的 deterministic check report，不产生 Manifest/Audit。
3. fresh API 且 `require_transfer_manifest=false` 使用 H1；为 true 使用 H2；H0 不启动新 API 会话。实际等级与原因进入 Attempt、Receipt 和 Trace。
4. 模型阶段完成但科研语义尚未接受时使用 `stage-completed`，并指向明确 Human Gate。该状态不得表述为数值正确、科学验证或 Claim 已接受。
5. 成功、失败、阻断和安全暂停均以 Main State 最后发布；只有合同准入成功才保留科研输出，失败路径不得伪造 Artifact、Manifest 或 Audit。
6. intent、防重放、排他发布、stage 恢复和 committed 恢复继续有效；H1/H2 都必须能从文件引用在 fresh process 中恢复，且恢复不得再次调用 Provider。

### 2. Execution Contract 与受控工具

每个 Execution Contract 固定合同 ID/版本、精确输出集合、Handoff 等级、工具集合、响应 Schema、成功状态、输出准入和确定性检查。合同代码选择可信文件名，模型不能提交任意输出路径。

文件读取只允许 Task 冻结的精确路径，调用时重新核对字节哈希与 UTF-8。`bounded-compute` 只提供固定、纯内存、有限长度的数值原语；不接受代码、命令、模块、文件、环境、子进程、网络或写入参数。它不是任意代码执行器。

### 3. 不可变 Model Assignment

每个新 model-api Attempt 在首次 Provider 调用前冻结一份 `Model Assignment`。其内容至少绑定：Task/Attempt、Profile、模型池与槽位、选择来源、Provider Adapter、请求模型、reasoning、能力、数据政策、预算/限制和模型池配置哈希。

选择来源仅允许 `profile-default`、`task-override` 或 `human-override`；初始实现只启用具有可验证来源的显式选择。`automatic_fallback` 必须为 `false`。换模型、换槽、升降级或换 Provider 必须创建新 Attempt。Receipt 核对请求与实际 Provider/Model；不一致时失败关闭，不能在同一 Attempt 内重试到另一个模型。

本节点不实现 Model Catalog、价格数据库、自动评分、最低成本 Resolver 或静默 fallback。

### 4. Agent Trace Bundle

Agent Trace 由四个版本化合同组成：

- `Agent Trace Envelope`：一条实际可见消息的身份、顺序、sender/receiver、正文哈希、附件、删减与捕获状态；
- `Actor Registry`：稳定 `actor_id`、运行身份与实名 `accountable_owner`；
- `Trace Event`：读取、工具、命令/外部动作、文件 revision、消息捕获、Attempt 状态与 capture gap 的 JSONL 记录；
- `Trace Index`：Attempt 身份、允许读取集、写入范围、工具允许集、消息/事件/输出/检查引用与完整性声明。

Trace 保存实际可见内容与边界事件，不保存隐藏 Chain-of-Thought。密钥、认证头、政策禁止数据和受限个人信息不得写入；删减必须可声明、可定位，并在无法证明完整捕获时形成 capture gap。

声明且可解释的 delayed/gapped capture 是诚实的不完整记录，可产生警告；未声明缺口、错误宣称 `complete`、哈希漂移、越界读取/工具、瞬时结果丢失、无实名 owner 或不可变过程产物覆盖是阻断错误。结构通过不表示科研正确或不存在隐藏推理。

Attempt、Receipt 与 Main State 以兼容性可选字段引用 Trace/Model Assignment；所有新 model-api Attempt 必须生成并交叉核对这些引用，既有 `0.1.0` fixture 继续有效。

### 5. Mode–Skill 与执行端的接口所有权

路诚钺维护 Task 信号、Mode 决策、Skill 选择、最小读取计划、Handoff 等级与 Trace 语义；黄毅维护 Execution Contract 实现、Provider/session、工具循环和真实 conformance。共享 Schema、Model Assignment、Handoff 等级和 Trace 引用必须由两人共同确认，任一侧不得单方面改变另一侧的语义。

## 验收边界

项目级 K-API-2 关闭需同时具备：双合同、H1/H2、自动 Trace、Model Assignment、fresh-process 恢复和一次 OpenAI 真实 Gate。真实 Gate 只证明 Provider 能力、结构化输出、指定客户端工具、受限执行和审计链；不证明科研正确性。

K-MS-1 需具备两个 Mode 的边界卡、可回放选择 fixtures、三个 accepted Skill 审计、一个 trial candidate 去留决定以及 H0/H1/H2 成本数据。达到该节点后暂停新增 Mode/Skill。

## 后果

优点：执行选择、模型身份、可见协作和恢复证据都能由文件重放；H1/H2 的差异成为合同而非条件分支；单一 evidence 路径不再代表整个项目。

代价：Schema、哈希引用、stage identity 和负面测试显著增加；Trace 与 Model Assignment 写入失败必须 fail closed；simulation 的 deterministic report 只能证明结构边界，仍需要人类科研审查。

## 不采用

- 根据价格或能力自动选择“最低成本”模型；
- Provider 或模型失败后在同一 Attempt 静默 fallback；
- 用平台会话 ID 代替文件式权威状态；
- 把完整 prompt、工具正文、密钥或隐藏推理默认写入 Trace；
- 因 Trace 完整或 Schema 通过而宣称科研结论正确；
- 在两个真实科研案例前升级为外部 pilot。
