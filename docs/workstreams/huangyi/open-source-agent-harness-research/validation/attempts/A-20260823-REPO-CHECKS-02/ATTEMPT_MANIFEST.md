# A-20260823-REPO-CHECKS-02

- 工作流：`RESEARCH-HARNESS-001`
- 类型：PR #25 后的 RWB 治理、回归与可发布性验证
- 日期：2026-08-23（Asia/Shanghai）
- 集成基线：`develop@5991cafdb7f536cd7b871508de9055d02b558728`
- 工作分支：`codex/open-source-agent-harness-research`
- Python：`3.12.13`
- 构建源码提交：`933fdc9319804a5ea69605d41fd6e931359236f6`
- 状态：`PASS_LOCAL_WITH_MATRIX_PENDING`
- canonical：否；Codex 协议 canonical 仍为 Attempt 05

## 边界

本 Attempt 在研究分支 rebase 到 PR #25 后创建。它验证新增治理脚本、文档约束、完整测试、
覆盖率、wheel 和 clean install；不重跑 Codex live protocol，也不改变基于 `b1d5a5a` 的
旧运行事实。Attempt 05 仅修复 tracked JSON 从暂存前 CRLF 哈希到 Git LF 规范字节的绑定。
所有生成物只能进入本 Attempt 的 ignored `raw/`。

构建源码提交已经包含 `develop@5991caf` 与本工作流首个提交；本 Attempt 后续修正仅涉及
研究文档、哈希清单和验证记录，不改变 wheel 中的 Python 包或 Schema。
