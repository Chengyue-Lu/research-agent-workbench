# Attempt Manifest：A-20260823-CODEX-READONLY

- Task：`RESEARCH-HARNESS-001`
- Owner：黄毅（`let778750-cpu`）
- Reviewer：路诚钺（`Chengyue-Lu`）
- Baseline：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- Runtime：Codex Desktop `0.149.0-alpha.4.1`
- Runtime SHA-256：`73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515`
- Captured at：`2026-08-23T18:11:01+08:00`
- Status：`FAILED_PRE_PROTOCOL`
- Canonical：否

目标是生成 stable Schema。Schema CLI 在参数解析阶段拒绝 `--strict-config`，未启动 App
Server stdio 协议，也没有发送 initialize、Thread、Turn、Model 或 Tool 方法。

完整 stderr 保存在 ignored `raw/`；可提交证据为本 manifest、[命令](COMMANDS.md)、
[哈希](HASHES.sha256)与[结果](RESULTS.md)。
