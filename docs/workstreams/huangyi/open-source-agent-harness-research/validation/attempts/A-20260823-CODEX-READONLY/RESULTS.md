# Results

结果：`FAILED_PRE_PROTOCOL`。

- Runtime hash 验证通过；
- 系统级 Codex 配置预检通过；
- Schema 命令参数校验失败；
- 未生成 Schema；
- 未启动协议握手；
- model/thread/turn/tool 请求均为 0。

该失败揭示 CLI 父命令帮助中的选项不一定适用于 Schema 子命令。Attempt 保留，不覆盖。
