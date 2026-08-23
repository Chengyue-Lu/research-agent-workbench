# Results

结果：`PASS_WITH_CAPTURE_GAPS`。

## Deterministic results

- Runtime hash match：PASS；
- system config absence preflight：PASS；
- stable Schema：291 files、181 methods；
- experimental Schema：401 files、237 methods；
- experimental-only：56 methods；
- preinitialize rejection：`-32600 Not initialized`；
- initialize/initialized：PASS；
- returned codexHome matches isolated root：PASS；
- duplicate initialize：`-32600 Already initialized`；
- unknown method：`-32600 unknown-variant`；
- experimental Gate：`-32600 requires experimentalApi capability`；
- protocol child exit codes：0；
- model/thread/turn/tool requests：0。

Schema bundle manifest digests记录在 `sanitized/schema-summary.json`。它们是按
`relative-path<TAB>sha256<TAB>bytes` 排序后形成的 manifest digest，不是单个文件哈希。

## Observed side effects

- 隔离 Home 内创建 SQLite、installation ID、log DB 和 bundled system skills；
- 每个协议场景采样到 2 个 `Bound` 和 2 个 loopback proxy `SynSent`；
- 非回环 remote endpoint 采样计数为 0。
- 隔离 Home ZIP SHA-256：`95cc6d230568ae065258b7e7196fc5368e1e5da21fe717635d29ef5c18afb96a`。

## Capture gaps

- 没有 OS 级网络无外联证明；
- 没有全系统无外写证明；
- 没有 source commit 与 binary build 的精确映射；
- 没有 Thread/Turn/Model/Tool 功能验证；
- 没有科学有效性结论。
