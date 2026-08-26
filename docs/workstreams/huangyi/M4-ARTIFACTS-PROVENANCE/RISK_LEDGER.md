# M4-001 风险台账

| 风险 | 缓解 | 状态 |
|---|---|---|
| 未准入 inbox 内容被引用 | 对既有引用提取面执行完整路径段检查并 BLOCK；含 lookalike 与 escape 负面测试 | 已锁定 |
| admitted bytes 或 derivative 漂移 | FileReference SHA-256 逐字节验证，漂移 BLOCK | 已锁定 |
| provenance 事实缺失 | Schema 与语义检查共同要求 locator、带时区时间、operator 与数据边界 | 已锁定 |
| 路径字符串前缀误判 | 规范化后按完整 segment 序列匹配；拒绝 `raw-copy`，不误判 `inbox-old` | 已锁定 |
| 执行覆盖已有正式字节/sidecar | `--execute` 写入前同时检查目标和 sidecar 不存在 | 已锁定 |
| 将确定性检查误当科研/法律判断 | 契约明确只证明结构、路径与字节 pin | 保留边界 |
