# A-20260823-REPO-CHECKS

- 工作流：`RESEARCH-HARNESS-001`
- 类型：RWB 仓库回归与可发布性验证
- 日期：2026-08-23（Asia/Shanghai）
- 基线：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- 工作分支：`codex/open-source-agent-harness-research`
- Python：主环境 `3.12.4`；独立 test-extra 环境 `3.12.13`
- 状态：`PASS_LOCAL_WITH_MATRIX_PENDING`
- canonical：否；本 Attempt 不替代 Codex 只读协议 Attempt 05

## 边界

本 Attempt 仅验证研究文档、已跟踪证据与既有 RWB 仓库。覆盖率、构建、安装和日志产物
必须写入本 Attempt 的 ignored `raw/`。Python 3.11/3.13 由远端 CI 验证，本地 3.12
结果不得代替该矩阵。一次性源码展开目录和虚拟环境经路径核对后已删除；保留源码 ZIP、
wheel 和覆盖率文件用于哈希核验。
