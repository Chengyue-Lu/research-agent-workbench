# M4 工件与复现 Workstream

- 责任人：黄毅（GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`，同一账户）
- 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- Tasks：`M4-001`、`M4-002`、`M4-003`、`M4-004`（`M4-005` 保持 PARKED，无真实大文件需求不启动）
- 基线：`develop@4ce83bc`（原实现基线）；Issue #41 M-series 规范化（PR #42）合入后已 rebase 至
  `develop@6b16129`，M4 行采用其精化的依赖与验收定义，仅状态列按本 workstream 证据置 DONE
- 目标 base：`develop`
- 阶段分支：`agent/m4-artifacts-provenance`
- 当前状态：实现完成；M4-003 按[实现映射](../../../M_SERIES_IMPLEMENTATION_MAP.md)为 R2 任务
  （Claim/counterevidence 语义面归路诚钺），PR 按 R2 提交并等待其跨负责人审查
- 风险触发：跨多个公共契约（新增 Schema、CLI 命令、风险码与 validator）、后继 M5-003 跨 PR 消费；
  M4-003 触发 R2（Claim 语义消费面）

## 1. 目标

按 [`TASKS.md`](../../../TASKS.md) M4 定义与[模块 07：工件与溯源](../../../modules/07-ARTIFACTS_AND_PROVENANCE.md)完成工件层四个任务的实现：

1. **M4-001 source admission 与 provenance**：`sources/inbox` 不可直接引用；接纳到
   `sources/raw` 时记录 sidecar manifest（原始文件名、接纳路径、SHA-256、获取时间、来源
   URI/DOI/设备/操作者、许可与数据使用边界、解析器版本、敏感性与外传限制、衍生关系）；
   网页/API/数据库来源需要快照或可复现 locator；
2. **M4-002 work → object/run promotion**：只有校验通过的工作产物可提升到正式对象区；
   accepted 工件不原地覆盖；失败与负结果不得因 promotion 被过滤；
3. **M4-003 Claim trace 与 counterevidence**：对既有 Claim 字段做支持/反证/限制的
   确定性一次定位与引用完整性校验；
4. **M4-004 Run manifest 与复现检查**：仿真/分析运行登记输入、参数、环境与输出哈希，
   支持无原 Agent 会话的机器可验证重建检查。

## 2. 非目标与实现边界

本 workstream 不实现或不修改：

- `claim*.schema.json`、Evidence–Claim 关系语义、Claim strength 词汇——M4-003 只消费既有
  `support_refs`/`counterevidence_refs`/`limitations` 字段；新关系语义属于 Phase C
  （Issue #38 已 R2 accept，路诚钺权属）；
- Research State、Failure/Attempt semantics、Method Trace（Phase C 范围）；
- DVC/MLflow/对象存储（M4-005 PARKED）；
- `.github/**`、治理脚本、TASKS.md 任务定义/依赖/验收列；
- Provider SDK、API session、Runtime、Topic 4/5 任何内容；
- 不伪造空 Skill Assignment：Run manifest 的 `skill_assignment_ref` 为可选，no-Skill 路径
  直接省略该字段（4/5 审计 P0-1 边界）。

## 3. 读取与写入范围

规范输入：

- `docs/TASKS.md`、`docs/ROADMAP.md`、`docs/DEVELOPMENT.md`；
- `docs/modules/07-ARTIFACTS_AND_PROVENANCE.md`；
- `docs/implementation/TESTING_STRATEGY.md`；
- `src/research_workbench/artifacts/integrity.py`、`contracts/risk_codes.py`、
  `kernel/objects.py`、`validation/*`、`cli.py` 既有实现；
- `schemas/v0.1.0/common.schema.json`、`research-object.schema.json` 等既有 Schema 约定。

允许写入：

- `schemas/v0.1.0/source-admission.schema.json`、`promotion-record.schema.json`、
  `run-manifest.schema.json` 及相应 fixture；
- `src/research_workbench/artifacts/**`（admission/promotion/repro 新模块）；
  `contracts/risk_codes.py`（新增 ARTIFACT-*/REPRO-GAP 风险码）；`validation/**` 增量；
  `cli.py` 新命令；
- `tests/test_*` 新测试；
- `examples/` 新 fixture 目录；
- 本 workstream、`docs/modules/07`、`docs/STATUS.md`、`docs/implementation/` 契约文档；
- `docs/TASKS.md` **仅状态单元格**（READY → DONE），定义/依赖/验收列一字不动。

## 4. 证据与风险

- [风险台账](RISK_LEDGER.md)：语义越权、与 Phase C 分支冲突、覆盖回退、fixture 误当真实数据；
- [验证证据](VALIDATION.md)：focused/full tests、coverage、`rwb validate`、负面 fixture 结果。

## 5. 合并与停止条件

- 一个 Stage PR（feature，R1）承载 M4-001..004 原子闭合；TASKS 状态变更仅状态列；
- 停止条件：四个任务的验收均有具名证据、全量测试与 CI 通过、路诚钺跨负责人审查完成；
  任何需要修改 Claim schema、Phase C 语义或治理脚本的发现登记到风险台账并转交，
  不在本分支扩张。

## 6. 与 M5 的衔接

M4-001..004 DONE 是 [`M5-EVALUATION-BASELINE`](../M5-EVALUATION-BASELINE/README.md)
中 M5-003 的真实前置；M5 分阶段口径在该 workstream 记录，不修改 TASKS.md。
