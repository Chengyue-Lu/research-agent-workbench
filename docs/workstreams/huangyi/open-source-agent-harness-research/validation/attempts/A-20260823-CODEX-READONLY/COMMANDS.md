# Commands

失败命令由探针以参数数组调用，逻辑形态为：

```text
<runtime> app-server --strict-config <disabled-network-config...>
  generate-json-schema --out raw/generated-schema/stable
```

返回：`--strict-config is not supported for codex app-server generate-json-schema`。

处置：后续 Attempt 只从 Schema 子命令移除该选项；stdio App Server 仍使用
`--strict-config`。本文件不记录机器绝对路径。
