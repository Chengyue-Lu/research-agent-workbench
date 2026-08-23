# Codex App Server 只读协议验证

- 状态：`PASS_WITH_CAPTURE_GAPS`
- Canonical Attempt：`A-20260823-CODEX-READONLY-05`
- 执行日期：2026-08-23（Asia/Shanghai）

## 1. 身份分离

| 对象 | 记录 |
|---|---|
| 上游分析证据 | `openai/codex@343074d4207d572809bd8cea15f4be1d09d98e0b` |
| 检索时上游 HEAD | `83d1fe0e67b1323f71febc2925817732b449f1d9` |
| PATH 中 npm CLI | `codex-cli 0.124.0`；未用于本验证 |
| Desktop Store 包 | `OpenAI.Codex_26.818.5229.0` |
| 实际 Desktop 缓存 Runtime | `codex-cli 0.149.0-alpha.4.1` |
| Runtime SHA-256 | `73D6D4A082A7CAD601A446A45B1B3FA9B77AFF9D3996052B74D9003D7947D515` |

上游 commit、检索时 HEAD 和本地 binary 是三个不同身份。本验证没有证明该 alpha binary
精确对应任一上游 commit，因此不做这种归因。

## 2. 已验证结果

| 场景 | 结果 |
|---|---|
| stable Schema | 291 files、3,023,451 bytes；181 个 client methods |
| experimental Schema | 401 files、3,778,968 bytes；237 个 client methods |
| experimental-only | 56 methods；包括 `server/diagnostics` |
| 初始化前请求 | `server/diagnostics` 返回 `-32600 Not initialized` |
| 正常握手 | `initialize` 返回 userAgent、codexHome、platformFamily、platformOs；随后接受 `initialized` |
| Home 约束 | 返回的 codexHome 与 Attempt 隔离目录一致 |
| 重复初始化 | 返回 `-32600 Already initialized` |
| 未知方法 | 返回 `-32600`、类型为 `unknown-variant` |
| 实验 Gate | `experimentalApi:false` 时返回 `server/diagnostics requires experimentalApi capability` |
| 进程终止 | 三个协议场景均在关闭 stdin 后 exit code 0 |

运行期间发送的 model/thread/turn/tool 方法均为 0。没有创建业务 Thread，没有模型输入、
工具结果、账户操作或仓库写接口。

## 3. 本地副作用与网络限定

App Server 启动会在隔离 raw Home 中创建 SQLite、installation ID、日志数据库和 bundled
system skills；验证后该 Home 被无损收口为 ignored `raw/temp-home.zip`。这是已观测的本地
副作用，因此“只读协议验证”只描述所发送的协议方法，不表示进程完全无写入。

三个协议场景的 TCP 采样均为 4 条：2 个 `Bound`，2 个指向失败代理
`127.0.0.1:9` 的 `SynSent`；采样时非回环远端数为 0。它支持以下有限结论：

- 代理失败保护被实际触发；
- 采样窗口没有看到非回环远端；
- 不能确定连接尝试来自更新、插件同步或其他内部组件。

本机 Codex Windows sandbox 不能提供可靠的独立网络阻断，且本轮没有系统级文件审计。
因此不能宣称“已证明无任何外联”或“已证明没有仓库外写入”。这两项保持
`CAPTURE_GAP`。

## 4. 对 RWB 的含义

1. Host source、binary、协议 Schema 和 negotiated capability 必须分开记录；
2. generated Schema 比 moving main 文档更适合描述当前 binary 的协议表面；
3. experimental capability 缺失可显式失败，适合纳入未来 Host conformance；
4. initialize 本身也可能触发 Runtime 内部状态和网络尝试，因此 adapter 不能只审计业务
   request；
5. 本结果只支持 read-only Host 研究，不授权 native Codex Runtime 接入。

## 5. 可提交证据

- [`codex-app-server-protocol-summary.v1.json`](../fixtures/codex/codex-app-server-protocol-summary.v1.json)
- [`codex-app-server-schema-summary.v1.json`](../fixtures/codex/codex-app-server-schema-summary.v1.json)
- [`codex-app-server-command-results.v1.json`](../fixtures/codex/codex-app-server-command-results.v1.json)
- [Canonical Attempt manifest](../attempts/A-20260823-CODEX-READONLY-05/ATTEMPT_MANIFEST.md)

完整 Schema、stdout/stderr、网络端点和隔离 Home 仅保存在 ignored raw；干净检出只验证
上述脱敏投影，不能重新构造完整 raw。
