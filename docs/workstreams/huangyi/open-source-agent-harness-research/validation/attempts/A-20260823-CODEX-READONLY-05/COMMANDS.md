# Commands

运行入口要求 PowerShell 7+，并使用参数数组启动 Runtime：

```powershell
pwsh -NoProfile -File ../../probe_codex_app_server.ps1 `
  -RuntimePath <desktop-codex-runtime> `
  -AttemptRoot <this-attempt-root> `
  -ExpectedRuntimeSha256 73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515
```

探针内部逻辑命令：

```text
<runtime> app-server <analytics/feedback/otel/update/remote-control disabled>
  generate-json-schema --out raw/generated-schema/stable

<runtime> app-server <same config>
  generate-json-schema --out raw/generated-schema/experimental --experimental

<runtime> app-server --listen stdio:// --strict-config <same config>
```

stdio 场景严格限定为：

```text
preinit: server/diagnostics
handshake: initialize → initialized → duplicate initialize → unsupported method
experimental gate: initialize(experimentalApi=false) → initialized → server/diagnostics
```

命令不记录机器绝对路径、环境值或认证信息。
