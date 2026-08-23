# Commands

逻辑调用顺序：

```text
1. generate stable Schema
2. generate experimental Schema
3. preinit server/diagnostics
4. initialize → initialized → duplicate initialize → unsupported method
5. initialize(experimentalApi=false) → initialized → server/diagnostics
6. close stdin and wait for clean exit
```

所有子进程使用隔离 Home、失败代理、strict stdio config、超时和 process-tree kill。没有
Thread、Turn、Model、Tool、Account、MCP 或 FS 请求。
