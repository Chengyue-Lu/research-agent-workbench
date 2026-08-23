# Attempt Manifest：A-20260823-CODEX-READONLY-03

- Task：`RESEARCH-HARNESS-001`
- Owner：黄毅（`let778750-cpu`）
- Reviewer：路诚钺（`Chengyue-Lu`）
- Baseline：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- Runtime：Codex Desktop `0.149.0-alpha.4.1`
- Runtime SHA-256：`73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515`
- Captured at：`2026-08-23T18:22:05+08:00`
- Status：`PARTIAL_SUCCESS`
- Canonical：否

Schema、初始化前拒绝、正常握手、重复初始化拒绝和未知方法拒绝均成功。但 Schema 方法
提取器只识别 `const`，而该版本使用单元素 `enum`，因此 derived summary 错写为 0 方法并
跳过 experimental Gate。原始协议结果有效，派生能力统计无效。

自动 sanitized 文件保留在本地但由 `sanitized/.gitignore` 排除，不进入正式证据。
