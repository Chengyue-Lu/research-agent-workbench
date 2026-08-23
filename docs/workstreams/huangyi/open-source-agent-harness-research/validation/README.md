# 结构化验证

本目录保存 `RESEARCH-HARNESS-001` 的可复现只读验证。所有运行产物必须位于某个
`attempts/<attempt-id>/`；不得使用仓库根目录 `work/`、系统临时目录或其他分支目录。

## 跟踪策略

| 类型 | 位置 | Git |
|---|---|---|
| 原始 Schema、stdout/stderr、网络快照、SQLite、临时 Home ZIP | `attempts/*/raw/` | ignored |
| Attempt 命令、manifest、hash、结果 | `attempts/*/` | tracked |
| 最小脱敏结果 | canonical Attempt 的 `sanitized/` | tracked |
| 复用 fixture | `fixtures/codex/` | tracked |
| 综合报告 | `reports/` | tracked |
| 覆盖率、wheel、源码构建快照 | `attempts/A-20260823-REPO-CHECKS*/raw/` | ignored |

raw 目录中的 `.gitignore` 固定为：

```gitignore
*
!.gitignore
```

## Codex 探针约束

[`probe_codex_app_server.ps1`](probe_codex_app_server.ps1) 要求 PowerShell 7+，并执行以下
保护：

- 先核对 Runtime SHA-256；
- 检查系统级 Codex config/requirements/managed config 不存在；
- 清空子进程继承环境，只保留最小 Windows 环境；
- 将 `CODEX_HOME`、`CODEX_SQLITE_HOME`、`TEMP`、`TMP` 指向当前 Attempt raw；
- 将 HTTP/HTTPS/ALL proxy 指向不可达的 loopback port 9；
- 禁用 analytics、feedback、OTel、启动更新检查和 remote control；
- 工作目录不属于 RWB Git 树；
- 不发送任何 Thread、Turn、Model、Tool、Account、MCP、FS 或写接口；
- 超时杀死整个子进程树。

运行结束后，探针将 `raw/temp-home/` 无损压缩为 `raw/temp-home.zip`，验证 ZIP 可读后才
移除展开目录，避免其中 bundled Skills 的 Markdown 被仓库文档测试误扫描。

探针允许的协议消息只有：

1. 初始化前的 `server/diagnostics`，用于验证 `Not initialized`；
2. `initialize` 和随后 `initialized`；
3. 重复 `initialize`，用于验证 `Already initialized`；
4. 一个不存在的方法，用于验证显式拒绝；
5. 在 `experimentalApi:false` 下调用由 Schema 证明为 experimental-only 的
   `server/diagnostics`，用于验证 capability Gate。

## 复现接口

不要复制本机绝对路径。先创建全新 Attempt 目录和 raw `.gitignore`，再运行：

```powershell
pwsh -NoProfile -File validation/probe_codex_app_server.ps1 `
  -RuntimePath <desktop-codex-runtime> `
  -AttemptRoot <new-attempt-root> `
  -ExpectedRuntimeSha256 <expected-runtime-sha256>
```

旧 Attempt 不得覆盖。Runtime 版本、binary hash 或探针版本变化时必须新建 Attempt。

## 两种验证不能混淆

- **file-only verification**：在干净检出中核对已提交 manifest、hash、最小 fixture 和报告；
- **live protocol rerun**：依赖本地 Runtime，重新生成 raw Schema并执行握手。

前者不能证明本地 Runtime 仍与当时相同；后者也不能证明科学正确性或生产 Host 安全。

干净检出的 file-only 命令为：

```text
python docs/workstreams/huangyi/open-source-agent-harness-research/validation/verify_tracked_evidence.py
```

Attempt 状态见 [INDEX.md](INDEX.md)，最终结论见
[CODEX_READ_ONLY_SPIKE.md](reports/CODEX_READ_ONLY_SPIKE.md)。

初始 RWB 仓库回归见
[`A-20260823-REPO-CHECKS`](attempts/A-20260823-REPO-CHECKS/RESULTS.md)；PR #25 合入并
rebase 后的治理、覆盖率、wheel 和 clean-install 见
[`A-20260823-REPO-CHECKS-02`](attempts/A-20260823-REPO-CHECKS-02/RESULTS.md)。两者都与
Codex App Server 协议验证分离，也不能代替目标 PR 的 Python 3.11/3.13 和真实 PR event CI。
