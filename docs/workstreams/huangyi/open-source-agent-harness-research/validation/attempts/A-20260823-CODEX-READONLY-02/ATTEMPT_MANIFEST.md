# Attempt Manifest：A-20260823-CODEX-READONLY-02

- Task：`RESEARCH-HARNESS-001`
- Owner：黄毅（`let778750-cpu`）
- Reviewer：路诚钺（`Chengyue-Lu`）
- Baseline：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- Runtime：Codex Desktop `0.149.0-alpha.4.1`
- Runtime SHA-256：`73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515`
- Captured at：`2026-08-23T18:21:06+08:00`
- Status：`PARTIAL`
- Canonical：否

stable/experimental Schema 生成成功。探针写入初始化前 `server/diagnostics` 后，在读取响应
前因 PowerShell 空集合参数绑定失败而终止进程树。没有 initialize、Thread、Turn、Model
或 Tool 方法。

完整 Schema 和临时 Home 保存在 ignored `raw/`；未产生可用 sanitized fixture。
