# Commands

```text
<runtime> app-server <disabled-network-config...>
  generate-json-schema --out raw/generated-schema/stable

<runtime> app-server <disabled-network-config...>
  generate-json-schema --out raw/generated-schema/experimental --experimental

<runtime> app-server --listen stdio:// --strict-config <disabled-network-config...>
stdin: {"method":"server/diagnostics","id":"rwb-preinit-1","params":{}}
```

读取响应时探针自身失败，App Server 进程树被终止。本文件不记录机器绝对路径。
