# Post-integration documentation alignment

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- Audit ID：`DOC-ALIGN-001`
- 风险：`R2`；触及 stable Architecture 与 Agent governance guidance，但不改变实现或 authority
- PR class：`feature`
- 基线：`develop@9d2f72fb583bac2e58fb00a02678c89685644536`
- 分支：`docs/post-integration-alignment`
- 状态：文档对齐已完成，等待独立 PR 审查与 CI

## 目标与范围

本 workstream 只消除 M10、M11 Core、M4-001 与 M5-003 集成后的文档漂移：

- `TASKS.md` 保持唯一 implementation-level status authority，并合法激活 `M4-002`；
- Developer Architecture Map、ROADMAP 与 M-series navigation 派生自当前 canonical truth；
- current Runtime 文档统一为 Capability Resolution → Snapshot → Bundle → View → Host → actual facts；
- 模块、状态、历史和既有 workstream 明确区分 bounded implementation、live/E2E evidence 与 Human/R2 closeout。

本轮不修改代码、Schema、Registry、测试、治理器、accepted ADR 或 DONE Task definition。历史快照继续保留，
但不得覆盖当前 `TASKS`、`STATUS`、stable Architecture 与 ROADMAP Gate。

## Authority ceiling

- machine validation 不产生 scientific correctness、Claim promotion 或 Human acceptance；
- M10 machine Gate 完成不自动解冻 Topic 5；
- Resolved Capability Snapshot 不是 final executable authorization；
- M11 Core 的 no-Skill/direct-Tool 路径不依赖 M11-005/006；
- Assignment 只用于 Skill-bearing 或 legacy compatibility，不是通用 Runtime 输入；
- 文档校正不授予 Host selection、fallback、Method、Claim、Gate 或 permission relaxation authority。

## 验证证据

- `python -m unittest tests.test_documentation tests.test_pr_governance -v`：76 tests PASS；
- repository validation：`validated=182 errors=0 warnings=0`；
- `git diff --check` 与 `python -m compileall -q src tests .github/scripts`：PASS；
- 当前文档旧 Task 状态与禁止 Runtime 断言扫描：0 命中；
- `src/`、`schemas/`、`tests/`、`registry/`、`.github/`：无差异。

风险与剩余决定见 [`RISK_LEDGER.md`](RISK_LEDGER.md)。
