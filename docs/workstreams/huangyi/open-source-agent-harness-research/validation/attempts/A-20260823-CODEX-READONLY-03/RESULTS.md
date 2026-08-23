# Results

结果：`PARTIAL_SUCCESS`。

- stable/experimental Schema 与基本握手成功；
- `Not initialized`、`Already initialized` 和 unknown-variant 均被观测；
- returned codexHome 与隔离 Attempt Home 一致；
- derived method count 为错误的 0/0，不能使用；
- experimental capability Gate 未执行；
- model/thread/turn/tool 请求均为 0。

Attempt 04 修复 `enum` 提取，Attempt 05 再收敛最小 fixture。
