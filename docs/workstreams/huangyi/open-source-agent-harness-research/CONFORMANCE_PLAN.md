# 外部 Harness / Host Conformance 计划

状态：研究与验证模板；不是生产 Runtime 接入计划。

## 1. 比较单位

不按项目名整体照搬，按以下机制维度比较：

| 维度 | 必须回答的问题 |
|---|---|
| delegation | child 身份、direct-parent authority、消息确认、取消与结果聚合如何表示？ |
| context isolation | child 实际能读到什么；压缩、fork 与隐式 memory 是否可观察？ |
| routing | Model/Tool/Skill/Agent 是否显式选择；缺失能力会失败还是 silent fallback？ |
| checkpoint/recovery | checkpoint 是不可变输入 pin、resume、fork 还是 salvage；副作用如何 fencing？ |
| human intervention | 执行 approval 与 scientific Human Gate 是否严格分开？ |
| observability | 请求、工具、消息、审批、重试与 omission 是否有同一最低 Trace？ |
| concurrency | depth/parallel/deadline/slot accounting 是否可限制并可归因？ |
| failure semantics | timeout、eviction、context limit、partial output 和 unknown effect 如何终止？ |

## 2. 最低报告字段

每个 future Host 试验至少记录：

- canonical repository、许可证、source commit、binary/package version 与 binary hash；
- transport、protocol/schema version、stable/experimental capability；
- RWB Task/Method/Skill/Tool/Provider/Model 到 Host 输入的映射；
- 每项权限的 `preventive / detective / advisory / unknown`；
- 事件覆盖、capture-gap、数据出口、retention 与 redaction；
- session termination、Attempt lifecycle、contract satisfaction 与 scientific acceptance 的边界；
- checkpoint/recovery 术语、side-effect fencing 与重复执行行为；
- 负面 fixture、结果、未证明内容和 `ADOPT / ADAPT / REJECT / DEFER`。

这些字段是报告要求，不是本工作流新增的公共 Schema。

## 3. 分阶段 Gate

### Gate A：来源可信

- 使用规范仓库、固定 commit、路径适用许可证和获取时间；
- moving branch 不能作为可复核结论的唯一证据；
- 同名项目或重定向必须消歧。

### Gate B：主线边界稳定

- M8-002、M8-003 已经 develop 集成并提升至 main；
- no-Skill/tool-only/Skill/Human/split/blocked Resolution 有正式 consumer seam；
- Execution 不自行增加 Method、权限或 Claim 语义。

### Gate C：只读协议验证

- 不创建业务 Thread/Turn，不调用模型、工具、账户或写接口；
- runtime source/binary identity 分开记录；
- Schema、initialize/initialized、版本/实验 Gate 与显式错误可复现；
- 原始产物只在 workstream raw，提交最小脱敏 fixture；
- 无 OS 级证据时保留网络/外写 capture-gap。

### Gate D：独立实现授权

只有真实 consumer 和独立 Task/ADR 才能进入 Host/Team 生产实现。必须证明：

- no implicit activation、fallback 或 hidden authority；
- permissions 单调收窄，数据出口 fail closed；
- native 与 model-api 满足相同最低 Trace 和 Receipt 语义；
- failure/timeout/context-limit 不伪装 completed 或 recovery；
- 干净安装、干净检出与 Python 3.11/3.13 全部通过。

## 4. 调研顺序与停止条件

研究顺序为 Codex → Pi → OpenCode。它只是最小可比性顺序，不是 M2-006、M6-005 或新
Runtime 的实施授权。Cline 与 DeepSeek Harness先作为 team/recovery 设计来源。

遇到以下任一条件立即停止当前试验：需要 API Key、模型调用、真实账户、Thread/Turn、
工具执行、仓库外写入、无法隔离的系统配置、未固定的源码版本、未知许可证或未授权网络。

## 5. 对抗场景库存

- 版本或 Schema 不兼容必须显式失败；
- 未 opt-in 的实验方法必须被阻断；
- parent deny 不能被 child scope 放宽；
- outer deadline 必须覆盖 spawn/wait；
- native stream 缺 child event 时产生 capture-gap；
- compaction 后 Task/Method/input hash 不漂移；
- unknown-effect Attempt 不自动重放；
- Runtime completed 不产生 `contract-satisfied`；
- no-Skill/tool-only 不生成 synthetic Assignment；
- model drift 在正式 evaluation 中阻断。

首次 Codex 实证见 [validation/reports/CODEX_READ_ONLY_SPIKE.md](validation/reports/CODEX_READ_ONLY_SPIKE.md)。
