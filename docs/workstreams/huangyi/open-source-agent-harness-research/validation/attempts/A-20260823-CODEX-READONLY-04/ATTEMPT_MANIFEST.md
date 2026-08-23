# Attempt Manifest：A-20260823-CODEX-READONLY-04

- Task：`RESEARCH-HARNESS-001`
- Owner：黄毅（`let778750-cpu`）
- Reviewer：路诚钺（`Chengyue-Lu`）
- Baseline：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- Runtime：Codex Desktop `0.149.0-alpha.4.1`
- Runtime SHA-256：`73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515`
- Captured at：`2026-08-23T19:16:34+08:00`
- Status：`VALID_SUPERSEDED`
- Canonical：否

本 Attempt 正确识别 181 stable、237 experimental、56 experimental-only methods，并完成
全部协议场景与网络采样。其自动 sanitized unknown-method 字段保留了服务端完整 method
枚举，不符合最小化原则，因此不作为公共 fixture；Attempt 05 在不改变协议场景的情况下
只记录错误类型和 code。

自动 sanitized 文件由 `sanitized/.gitignore` 排除；原始内容由 raw `.gitignore` 排除。
