# Method-to-Execution 初版闭环

状态：**experimental combined prototype / non-authoritative**。本分支只用于保全和审查
当前 Method/Capability/Execution/Trace 混合候选，不得直接合入 `main`，不表示
M8-002～005 已启动或完成。正式合入必须按 Issue #13 将 M3-008 Trace Core、M6-006
Execution Trace Adapter 与 M8 Method/Core 分支拆分。

## 冻结链

```text
Task Packet
  → Mode Action
  → provider-neutral Method Resolution
  → Resolved Capability Snapshot
  → Resolved Execution View
  → Trace initialized before the first Provider call
  → fresh bounded API session + write-before-send events
  → outputs / Trace / Attempt / Receipt / Handoff / checks
  → marker-last completion manifest
  → file-only replay
```

Method 不含 Provider、Model、Host 或 Adapter。Capability Snapshot 才绑定本次 Attempt 的 Skill、
client Tool、Provider Adapter、版本/hash、数据出口与副作用。Execution View 再冻结 Task、Assignment、
Method、Snapshot、可选前序 Main State、模型槽与预算，生成 SHA-256 execution identity。

## 严格 CLI 路径

先在独立本地模型池副本中显式启用一个已通过 conformance 的槽，并创建精确 Skill Assignment；
不要修改仓库模板或把凭据写进配置。离线 scripted 路径示意：

```powershell
rwb execute task `
  --task examples/task-evidence.yaml `
  --assignment <project-relative-assignment.yaml> `
  --method-resolution examples/method-resolutions/MR-EVID-001.yaml `
  --capability-snapshot examples/capability-snapshots/RCS-EVID-001.yaml `
  --slot primary `
  --accountable-owner "黄毅" `
  --pool <enabled-local-pool.yaml> `
  --adapters registry/providers/adapters.yaml `
  --scripted-session examples/api-execution/scripted-session-evidence.json.txt `
  --root .
```

恢复尝试额外传入 `--from-state <exact-main-state.yaml>`。该状态必须有有效 canonical digest、
created_at、未漂移 machine refs，并把当前 Task 标成唯一可恢复前序。恢复总是生成新 Attempt identity，
不在旧 Attempt 目录续写。

## 完成与失败语义

- Evidence 必须在 `metadata.source_file_ref` 精确绑定 Task input 的 path 与 SHA-256；普通
  `source_ref`/locator 不能替代文件身份。
- 工具一经调用就消耗预算并记录副作用，即使 handler 失败或返回结果过大。
- cancel 或 deadline 不伪装成 completed；Provider 错误保留已发生轮次和显式停止原因。
- `model-api` Attempt 必须有 hash-bound `trace_ref`；`session-transcript.json` 是由 Trace 派生的
  兼容视图，不是第二套运行真值。safe pause 依然必须钉住必要上下文；恢复使用
  新 Attempt，不续写旧 Trace。
- Trace 在 Provider 调用前写入失败时不得发请求；调用后写入失败时记录
  `capture-gap` 并 SAFE_PAUSE。如果 gap 本身也无法持久化，不得发布 completion marker。
- closeout 的普通文件先以独占方式发布，`completion-manifest.yaml` 最后发布并固定整批文件/hash。
  没有 marker 的半批次不可 replay 为已提交，也不得复用同一 Attempt 执行模型。
- `rwb execute verify --attempt <dir> --root .` 只凭文件验证 marker、hash、Schema、Receipt、Handoff、
  Transfer Audit 与未索引输出。

## 合并 Gate

1. 路诚钺审查 Mode Action、Method Resolution、Mode migration 与 Decision Authority 语义。
2. 黄毅审查 Provider/timeout/cancel、tool accounting、compiler、closeout 和 live 配置。
3. 双方共同审查 Snapshot、Resolved Execution View、Task/Handoff/Receipt 和风险码。
4. 在当前 `origin/main` 重放全量 tests、coverage、`rwb validate examples registry` 与补丁检查。
5. 黄毅在不回显密钥的 Windows 环境重跑 OpenAI text/schema/tool conformance，
   再跑 `EVID-SIR-001` 和 `SIM-SIR-001` 两个完整 Attempt。
6. 扫描两个 Attempt 包，确认无密钥、认证头、hidden reasoning 或绝对用户路径，
   且 `rwb trace validate` 与 `rwb execute verify` 均无 BLOCK。
7. 只有上述证据齐全后才把 M8-002..006/M6-003 标为 DONE，并单独授权 commit/push/PR/merge。

本闭环不完成长期 Research State、Method-aware Trace、Skill 增量价值、科学正确性、LICENSE 或
对外发布；这些不能由离线结构测试推断。

`EVID-SIR-001`/`SIM-SIR-001` 已有公开、可复现的 Task/Question/Method/Snapshot 输入，
但现行兼容 Assignment 仍要求非空 Skill lock，而 Method Resolution 允许
`task-contract`/`tool-only` 的 no-Skill 路径。这是 Method/Core shared seam：语义审查前不得
伪造 Skill Assignment 来启动 live canary。

黄毅原工作树中的 2026-08-19 M6-004 脱敏包仍是有价值的历史 live 诊断，但它有意省略
`execution-plan.yaml`，也早于本分支的 `completion-manifest.yaml` 与 exact Evidence file binding，
因此没有被搬入本集成候选或升级成新 Gate 证据。它暴露的 ProviderError、代码栅栏、并行工具上限
和 prompt 约束修复已连同测试重放；live Gate 必须用当前 strict contract 重新生成完整证据包。
