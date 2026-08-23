# 来源清单

状态：`AUDIT-EXEC-RUNTIME-001` 的 hash-bound 来源索引；不保存私密原文。

每个条目记录 `source_id / type / logical locator / captured_at / revision-or-hash / access /
attribution / authority / supported claims / limitations / verification`。

## `SRC-CANONICAL-MAIN`

- 类型：Git commit 与 repository blobs
- commit：`b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- 获取：2026-08-23，`git fetch origin --prune` 后核对
- access：公开 Git 仓库
- authority：按文档表面分别为 accepted normative、planning 或 implementation evidence
- verification：`origin/main` 与 `origin/develop` 均解析到该 commit

关键 blob：

| 路径 | Git blob |
|---|---|
| `docs/ARCHITECTURE.md` | `75f9f8b0a8ca9e819c116d9b05202501f27d5658` |
| `docs/STATUS.md` | `924b158b814802b895e8501de473fa59c369103e` |
| `docs/TASKS.md` | `e83424bbab1969be0f52ed958552804711839c6c` |
| `docs/ROADMAP.md` | `3be6de49ff31d85007458ed6a136fe762d5d3b70` |
| `docs/DEVELOPMENT.md` | `5fe20e7ea45b586c0e8d0a2c1d57c968c2b4276d` |
| `docs/decisions/0009-FILE-FIRST-CONTINUITY-AND-SAFE-PAUSE.md` | `cb88855a62cb58b3a7ad2df03264d1b96f9c2d84` |
| `docs/decisions/0010-API-FIRST-ISOLATED-EXECUTION.md` | `a15089ba42979113c3047e95f426f1f21efc36a2` |
| `docs/decisions/0016-METHOD-AWARE-RESEARCH-CONTROL-PLANE.md` | `bbe62b2528cb5b089b171bb43333bb3278b55c27` |
| `src/research_workbench/adapters/models/session.py` | `b08cb2f62544c9c4319898c2842b840372e7ba9c` |
| `src/research_workbench/execution/recovery.py` | `ae4b397d8996680eb48e9308162f40853b34943a` |

## `SRC-PR23`

- 类型：GitHub PR candidate branch
- logical locator：`Chengyue-Lu/research-agent-workbench#23`
- base/merge-base：`b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- head：`57b3d24a8383ec3618dd29b4d5c52ee7ff9fcbef`
- 获取：2026-08-23，刷新远端引用后核对
- authority：branch-only implementation evidence；不能证明 `main` 状态或 Task DONE
- limitation：PR 状态、checks 和 head 可能变化；每次审查前必须重新获取

关键 blob：

| 路径 | Git blob |
|---|---|
| `docs/TASKS.md` | `8252482e40ad067cb7e44164292a1569f981b701` |
| `src/research_workbench/execution/compiler.py` | `3d867e7694243e29b68b45c66cdf9dcdb7dcd9f5` |
| `src/research_workbench/execution/runner.py` | `09ed434c4fda8f0d68bdbc85c14d3fac7128e524` |
| `src/research_workbench/execution/closeout.py` | `8f712ddd49c1ddce1661e8da3bf2e56f8dcd59ad` |

## `SRC-PR23-GOVERNANCE-20260823`

- 类型：mutable GitHub PR governance metadata snapshot
- logical locator：<https://github.com/Chengyue-Lu/research-agent-workbench/pull/23>
- observed_at：`2026-08-23T07:51:44Z`
- base/head：`main@b1d5a5a5850e0e7541e4c460f15384cd45357ab2` /
  `agent/k-api-2-rework@57b3d24a8383ec3618dd29b4d5c52ee7ff9fcbef`
- observed state：open、Draft；labels 为 `blocked` 与 `do-not-merge`
- reviewer state：已向 `Chengyue-Lu` 发出 reviewer request；submitted reviews 为 `0`
- hard-block comment：
  <https://github.com/Chengyue-Lu/research-agent-workbench/pull/23#issuecomment-5384190781>
- actor：PR author、comment author 与治理提交的 canonical GitHub login 均为 `let778750-cpu`
- authority：只证明该观测时刻的远端治理状态；不替代 `SRC-PR23` 的 commit-pinned 代码证据
- limitation：PR metadata 可变；每次依赖该状态采取动作前必须重新获取，不能从 reviewer request
  推导出已完成 review 或 approval
- identity attestation：黄毅于 2026-08-23 本人确认 `huangyi855` 是昵称/界面名，
  `let778750-cpu` 是同一账户的主名。远端 API 只显示 canonical login `let778750-cpu`，因此别名映射
  属于 human-attested fact，不能由 GitHub API 独立证明，也不能把 `huangyi855` 当成第二个可请求
  review 或写入 CODEOWNERS 的 handle

## `SRC-MEETING-MINUTES`

- 类型：private local meeting summary
- logical locator：`meeting_01_智能会议纪要.md`
- SHA-256：`07C8C82352AAD98089276AF129F47C78E568857DBE4185C339E7F3D071E71AB2`
- bytes：`35024`
- captured_at：2026-08-23
- attribution：材料是整理纪要，不逐句归因给某位发言者
- authority：meeting input；需由仓库变更或双方审查 ratify
- limitation：材料明确缺少字幕/逐字转写；只能按其“确认/会议判断/未定”分级使用
- access：私有原文不入 Git；不记录机器绝对路径

它支持“优先 M8 主线、PR #23 不进入当前主线、建立 develop 集成流程”等讨论来源；不单独证明
Architecture Hold 已被项目正式接受。

## `SRC-CHATGPT-SHARE`

- 类型：mutable public ChatGPT Share
- URL：<https://chatgpt.com/share/6a89f2f6-7604-83ec-8549-7fc03c25a63f>
- 标题：`审核文档规划建议`
- captured_at：`2026-08-23T03:00:10.108Z`
- normalized snapshot：按 DOM 顺序保存 `id / role / visible text` 后进行 UTF-8 JSON 规范化
- visible messages：`5`
- normalized bytes：`24758`
- SHA-256：`5FD1A09AF07E50A6C07269A097631E48AF111DC716F2C231906C0D29E3437CE6`
- access：完整正文不入 Git；仓库只保留本索引和下列脱敏摘要
- attribution：页面只有 `user/assistant`；不能证明 user 对应黄毅或路诚钺
- authority：人类消息是意图候选；GPT 消息是 hypothesis/proposal
- limitation：Share 可撤销或更新，公开引用不能替代 commit-pinned 代码核验

消息定位：

- user 风险请求：`c9e69d74-f35c-4f95-8764-996a32e0e3ab`；
- GPT 风险分析：`ccb87561-d472-4512-833c-a142be9b8a71`；
- user 暂缓意图：`099f5a4c-59ea-4b52-9883-7feeb65c413b`；
- GPT Architecture Hold 建议：`7c513497-5ddf-4278-91a6-9dfe77b68fa6`。

最小脱敏摘要：匿名 user 请求评估个人导航第 4/5 域的隐藏冲突，并提出暂缓扩建、先补前序
控制链和调查外部 Agent 机制；GPT 提出风险分级、边界不变量及三条并行 workstream。这些内容
不涉及 PR #23、develop 或 M8 的正式决定。

## `SRC-HUANGYI-DRAFT`

- 类型：derived private working paper
- logical locator：`RWB_4-5部分恢复开发风险审计.md`
- SHA-256：`1640D9AA38CA910A8F24EF2DF10FDC8570CDE49196E5C85406EC51B3B0663E99`
- bytes/lines：`24532 / 1640`
- captured_at：2026-08-23
- context：存在于 `agent/issue-21-trace-schema-export@6ca4a4af145fe1730c62910ebf9f3e3a08418086`
  工作树但保持 untracked，不属于该分支提交
- authority：个人审计参考版；不能成为 Decision、TASK 状态或 H2 Archive
- handling：只提炼 claims；不得随 PR #24 或本审计 PR 提交原文

## 获取与复核限制

- 本清单不证明共享页 user 的真实身份，也不把 GPT 技术判断当代码事实；
- PR #23 的所有结论必须同时给出 commit-pinned blob 或测试证据；
- 若任一远端 SHA、Share 指纹或私有来源哈希变化，先创建新 revision，不覆盖本清单；
- 私有原文的保存、访问控制和删除策略由两位维护者在线下决定，本仓库只保留不可逆哈希。
