# 恢复点与下一步规划

状态：`K-API-2 Offline Minimal File Loop Gate Passed`，等待维护者的 `M6-004` 授权决定

日期：2026-08-15

## 1. 当前架构判断

主 Agent 只维护大局、决定、风险、工件索引和下一 Atomic Work Unit；每个子任务在 fresh context 中执行，并在结束前把不可丢失内容固化为文件契约。子会话可以关闭或压缩，项目方向不依赖聊天历史。

执行优先级保持为：

1. 文件式科研契约和连续性；
2. 纯 API fresh session 的可移植基线；
3. Codex、OpenCode、Claude Code 等可选平台 Adapter 或人工新窗口；
4. 只有真实失败证明需要时，才评估更重的运行时。

模型仍只通过 `primary`、`worker` 和按需 `specialist` 显式绑定；不建设价格数据库、评分 Router 或自动 fallback。

## 2. 已到达的节点

### K-API-1：隔离 API session kernel

已具备 provider-neutral fresh session、显式模型槽、能力/data-policy 前置阻断和有界工具循环。单轮 tool-call fan-out 有上限，但 handler 当前串行执行。累计 token/成本、wall time 和输出限制是调用边界/响应后 guard，不能取消 in-flight 调用。

### K-API-2：离线最小文件闭环

已实现的最小链路：

```text
Protocol + Task + Profile + frozen Skill Assignment
  + optional previous Main State + explicit worker slot
        ↓ exact-byte capture + Schema/canonical-ref validation
trusted Task-to-ModelRequest compiler
  + bounded refs + selected Skill only + read-only document-read
        ↓ fake-local fresh API session
strict Research Object / Handoff output validation
        ↓ commit-last closeout
completed:
  Attempt + Research Artifacts + Manifest/Audit + Handoff
  + task/main Context Snapshots + Receipt + Main State
non-completed:
  Attempt + Handoff + task/main Context Snapshots + Receipt + Main State
        ↓ delete in-memory transcript
fresh Python subprocess resume-check → one bounded next action
```

关键安全语义：

- 四个合同文件及可选 previous Main State 使用执行前同一份字节快照；Schema 无效、ref 非 canonical 或执行期漂移都会 fail-closed。
- Task 输入和选定 Skill 有哈希锁；主历史、未选 Skill 和 source 正文不会被预先注入 prompt。
- Task 输入以执行前精确字节复制进 stage；Main State 发布前再次核验合同、输入、Skill lock、已发布非 Main 文件及 staged Main State，漂移时不提交且不重放 Provider。
- dynamic artifact 路径必须逐个通过真实 write scope 与 allowed roots。
- closeout 是 Main State last 的 commit-last 协议，不是多文件事务。
- 完整 validated stage 可续发且不重放；执行已开始但 stage plan 尚未形成时，持久 intent 使同 Attempt 返回结果未知并禁止自动重放。
- staged/committed 恢复重新绑定规范 Attempt 路径、write scope 和 optional previous Main State，不能用同一 Attempt 换前序状态或输出根。
- 模型身份、工具失败、Evidence hash 和 Transfer 语义失败不能产生 `contract-satisfied`。

专项程序化 fixtures 已覆盖 completed、tool-failed、safe-paused、incomplete、stale/missing input、Adapter ID/规范 Provider 分离、合同漂移、错误模型、错误 Evidence、并发同 Attempt、关键发布崩溃和 Main 提交窗口漂移。删除 transcript 后的恢复由 fresh Python subprocess 以 Main State 为入口，在 Protocol 与哈希锁定的项目文件树中验证；这不是一次真实主模型会话，也不是单个 Main State 文件自足。结构合法的 `completed` 尚不等于通用证明 Provider 一定调用了 `document-read`，只有 happy-path fixture 明确验证该工具往返。

## 3. 当前唯一动作：停在授权门前

`K-API-2` 已通过离线最小节点评审。评审已确认最小编译上下文、可信权限交集、五类终态输出差异、Adapter/Provider 身份分离、intent/validated-stage/Main-State 边界和 no-replay 证据。同时，审计未发现阻断性 P0/P1，并确认文档未将 fake-local 证据写成 live API、真实 Windows 或科研价值证明。

当前不得继续编码扩展。唯一下一动作是由维护者决定是否明确授权 `M6-004`。风险触发候选结果未保留、mandatory semantic review 未支持、Provider 中途异常 partial aggregate unavailable 等仍是后续设计限制，但不扩大本 Gate 的证明范围。

## 4. 明确不做

- 不自动启动 `M6-004` 或发送真实 API 请求；
- 不实现 OpenCode、Codex、Claude Code 的新 Runtime Adapter；
- 不实现模型排名、价格抓取、Router、静默升级或 fallback；
- 不实现 GUI、服务端、数据库、消息总线或长期 Supervisor；
- 不扩展 streaming、多模态、server tools 或 external-write 工具；
- 不安装 ZIP 候选 Skill；
- 不把离线闭环标为科研正确、语义等价、可公开发布或多 Agent 更有效。

## 5. 评审后的候选顺序

仅在维护者明确批准后依次考虑：

1. `M6-004`：对实际启用的 `primary`/`worker` 槽做受限、脱敏的真实 Windows conformance 和一次 evidence 调用；
2. 设计 human-review waiting 边界，保留 negative-result/conflict 等候选内容；
3. 用同一 evidence Task 比较轻量单 Agent 与主/子隔离执行的上下文、质量和成本；
4. 运行 simulation Task，验证第二种 Skill 和工具边界；
5. 只有出现真实消费者时再增加 specialist、平台 Adapter 或额外能力。

## 6. 恢复入口

1. `docs/CURRENT_HANDOFF.md`；
2. `docs/TASKS.md`；
3. `docs/decisions/0010-API-FIRST-ISOLATED-EXECUTION.md`；
4. `src/research_workbench/execution/`；
5. `tests/test_k_api_2_pipeline.py`；
6. `CHANGELOG.md` 最新条目。

不要从旧聊天记录或某个平台会话重建项目状态。
