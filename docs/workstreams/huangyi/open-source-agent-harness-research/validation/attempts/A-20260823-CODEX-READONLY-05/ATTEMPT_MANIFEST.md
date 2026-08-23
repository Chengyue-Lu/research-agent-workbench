# Attempt Manifest：A-20260823-CODEX-READONLY-05

- Task：`RESEARCH-HARNESS-001`
- Owner：黄毅（`let778750-cpu`）
- Reviewer：路诚钺（`Chengyue-Lu`）
- Baseline：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- Runtime source evidence：`openai/codex@343074d4207d572809bd8cea15f4be1d09d98e0b`
- Retrieved source HEAD：`83d1fe0e67b1323f71febc2925817732b449f1d9`
- Local Runtime：Codex Desktop `0.149.0-alpha.4.1`
- Runtime SHA-256：`73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515`
- Captured at：`2026-08-23T19:19:14+08:00`
- Status：`PASS_WITH_CAPTURE_GAPS`
- Canonical：是

## Scope

只生成 stable/experimental Schema，执行 initialize 生命周期和无业务副作用的错误场景。
未发送 Thread、Turn、Model、Tool、Account、MCP 或 FS 请求。

## Outputs

- raw：完整 Schema、stdout/stderr、TCP snapshot 与隔离 Codex Home ZIP；全部 ignored；
- sanitized：3 个最小 JSON summary；tracked；
- public fixtures：由 sanitized 逐字复制；tracked；
- report：`validation/reports/CODEX_READ_ONLY_SPIKE.md`。

## Capture gaps

- 本地 binary 与上游 commit 的精确构建对应关系未证明；
- 没有 OS 级网络过滤，只使用失败代理并做时点采样；
- 没有全系统文件写入审计；
- file-only evidence 不能重建 ignored raw。

本次运行后用与当前探针相同的“创建 ZIP→验证条目→删除展开目录”流程收口 Home；该步骤
不改变任何协议结果。
