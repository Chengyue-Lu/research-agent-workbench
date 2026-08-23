# RESEARCH-HARNESS-001：开源 Agent Harness 调研与结构化验证

- 状态：Working paper；不是 Stable Architecture、TASKS 或 Runtime 实施授权
- 责任人：黄毅（GitHub 主名 `let778750-cpu`，昵称 `huangyi855`）
- 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- 代码证据基线：`main@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- 当前集成基线：`develop@5991cafdb7f536cd7b871508de9055d02b558728`
- 证据截止：`2026-08-23T19:20:00+08:00`

## 1. 结论先行

`main@b1d5a5a` 已具备文件权威、方法感知研究控制、隔离 API 基线和窄范围单 Attempt
Trace，但仍是 internal alpha。`develop@5991caf` 在此代码基线上增加 PR #25 的治理、
审计和 CI 门禁，没有改变 Runtime 实际行为。规范已经接受 no-Skill 和 direct-tool 路径，
正式 CLI、Registry、Receipt 与 archive 链尚未形成诚实的 no-Skill 闭环。

本调研支持的目标形态是“可移植研究控制与证据内核 + 最小 API 参考执行 + 可替换
Host Adapter”。它不支持在 Core 中增加全局 Supervisor、第二套科研状态数据库或固定
团队 DAG。Host/Team Port、复杂恢复和新 Runtime 目前都是等待真实消费者的可证伪假设，
不得改写 M8-002 → M8-003 主线。

## 2. 范围与非目标

本工作流负责：

- 固定核心与补充 Harness 的仓库、证据提交、检索时 HEAD 和许可证；
- 将原始讨论稿拆为 `FACT / INFERENCE / PROPOSAL / CAPTURE_GAP`；
- 对 Codex Desktop App Server 做不创建 Thread/Turn 的只读协议验证；
- 为 PR #20 提供经核验的差异，而不把完整报告塞入 PR #20。

本工作流不负责：

- 修改 `TASKS.md`、`STATUS.md`、`ROADMAP.md`、ADR 或稳定责任表；
- 实现 Runtime、Router、Team、Host、Capability Snapshot v2 或 recovery Schema；
- 创建虚假 Active Skill，或为 no-Skill 路径伪造 Assignment；
- 解除 Architecture Hold，或把 GPT 讨论提升为项目真值；
- 阻断、重排或代替 M8-002/M8-003。

黄毅在本工作流中的角色是“架构调研、证据核验和小规模只读验证”。这不是对
[`docs/DEVELOPMENT.md`](../../../DEVELOPMENT.md) 稳定责任表的修改。

## 3. 证据纪律

证据优先级固定为：accepted ADR/Stable docs → `TASKS.md` 的实时状态 → main 代码和测试
的实际行为 → 固定 PR diff → 上游固定提交 → 人类 working paper。公开 Issue 只证明某个
失败模式被报告过，不证明发生频率、普遍性或当前版本仍受影响。

检索时 HEAD 只表示一次快照；正文主张继续引用原始证据提交。无法唯一定位的
“Open Science”保持 `UNVERIFIED_IDENTITY_MISMATCH`。

## 4. 导航

- [SOURCE_MANIFEST.md](SOURCE_MANIFEST.md)：来源、提交、许可证和身份状态；
- [CLAIM_LEDGER.md](CLAIM_LEDGER.md)：逐项事实、推断、提案和缺口；
- [ADOPTION_MATRIX.md](ADOPTION_MATRIX.md)：`COVERED / ADAPT / DEFER / REJECT`；
- [CONFORMANCE_PLAN.md](CONFORMANCE_PLAN.md)：未来 Host 机制对照与验证 Gate；
- [SYNTHESIS.md](SYNTHESIS.md)：面向 RWB 的综合结论与 PR #20 差异；
- [validation/](validation/README.md)：只读探针、Attempt 索引和脱敏 fixture；
- [history/](history/README.md)：本工作流过程记录与未来 closeout。

## 5. Git 与隐私边界

原始稿、完整 Schema、stdout/stderr、SQLite、临时 Codex Home 和网络端点快照只存放在
本工作流的 `raw/` 子目录，并由各自的 `.gitignore` 排除。仓库只跟踪来源清单、逻辑
命令、哈希、最小脱敏 fixture、结果和 capture gap。

原始 Harness 稿迁移前后 SHA-256 均为
`4C33CF931AE660EB42627D450794A905674C92B653A7E7ED8767288F5101FB79`。
它不是正式结论，且不进入 Git。

## 6. 分支与发布门禁

工作分支为 `codex/open-source-agent-harness-research`。它最初从 `develop@b1d5a5a` 创建，
在 PR #25 以 `5991caf` 合入后已 rebase 到该最新 develop。目标 PR 的基线必须填写完整
`5991caf...`，并以 `RESEARCH-HARNESS-001` 向 develop 提交；后续 develop 若再次移动，
仍须重新获取、rebase 和验证。

合并 develop 后，本材料随完整 workstream 经 `develop → main` 发布。公共
`docs/history/` 最多增加索引；验证材料的唯一规范位置仍是本目录。

## 7. 完成定义

- 来源 ID 唯一、固定 SHA、许可证和获取时间完整；
- 每条结论标明类型、scope、证据、置信度和处置；
- Codex 探针没有 Thread、Turn、模型或工具调用；
- raw 产物全部被忽略，脱敏 fixture 可在干净检出中验证；
- 文档链接、Schema/Registry、Python 3.11/3.13 和完整测试通过；
- 路诚钺完成审查，且本 PR 未改动任务状态或稳定架构。
