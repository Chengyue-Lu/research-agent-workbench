# Results

结果：`VALID_SUPERSEDED`。

- 181 stable、237 experimental、56 experimental-only methods；
- 初始化前拒绝、正常握手、重复初始化拒绝、未知方法拒绝与 experimental Gate 均符合预期；
- 三个协议进程 exit code 0；
- 采样只见 `Bound` 及指向 `127.0.0.1:9` 的 `SynSent`，非回环远端数为 0；
- model/thread/turn/tool 请求均为 0；
- sanitized unknown-method 字段过宽，不符合 data minimization。

协议结论有效，但正式 fixture 由 Attempt 05替代。
