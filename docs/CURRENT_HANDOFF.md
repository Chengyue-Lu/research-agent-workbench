# 当前开发 Handoff

状态：`K-API-2 Offline Minimal File Loop Gate Passed`，仍停在 `M6-004` 授权门前

更新日期：2026-08-15

实现分支：`codex/k-api-2-minimal`（评审合并后仍以 `main` 为权威）

这份文件用于让没有既往聊天上下文的人或 AI 直接恢复开发。聊天摘要、平台线程和临时 transcript 都不是项目状态的权威来源。

## 1. 恢复结论

仓库已经完成 `EVID-001` 的最小离线 Task-to-API 文件闭环：冻结的 Project Protocol、Task、Profile、Skill Assignment 和显式 `worker` 槽可以编译为 fresh API session；fake-local Provider 的结果可以关闭为可验证文件；删除内存 transcript 后，fresh Python subprocess 可以以 Main State 为恢复入口，在 Protocol 与哈希锁定的项目文件树中得到唯一下一动作。

这不是完整 Task 执行产品，也不是 live Provider、Windows 槽、科研正确性或多 Agent 净收益证明。`K-API-2` 节点评审已通过；当前唯一下一动作是由维护者决定是否明确授权 `M6-004`，不得自动进入。

## 2. 接手时先读取

1. `AGENTS.md`：不可违反的仓库边界；
2. `docs/decisions/0010-API-FIRST-ISOLATED-EXECUTION.md`：当前执行方向；
3. 本文件；
4. `docs/TASKS.md` 与 `docs/NEXT_STEPS.md`；
5. `src/research_workbench/execution/compiler.py`、`pipeline.py`、`output.py`、`closeout.py`；
6. `tests/test_k_api_2_pipeline.py` 及三个 K2 专项单元测试文件；
7. 只有修改具体契约时，再读取相应 Schema、ADR 和模块文档。

若本文与已接受 ADR 冲突，以较新的 ADR 和机器验证结果为准。不要用旧聊天记录补全仓库没有表达的状态。

## 3. 已冻结的架构边界

- 文件契约是权威状态；会话历史不是。
- 纯 API fresh session 是可移植执行基线；平台原生 Agent/线程只是可选 Adapter 或人工入口。
- 模型只通过少量显式槽绑定；不实现评分 Router、价格抓取、静默升级或跨 Provider fallback。
- 主 Agent 不接收全部原始材料与工具日志；子 Agent 只获得 Task、选定 Skill、必要输入、有效权限、输出合同和预算。
- 不建立全局 Supervisor、固定科研 DAG、消息总线或连续性数据库，除非真实失败证据支持新的 ADR。
- `K-API-2` 只允许只读 `document-read`；外部写入、streaming、多模态、server tools、新 Provider 和平台 Adapter 均不在本节点。

## 4. 本次已实现

### 4.1 可信编译边界

- `verify_execution_material` 只接受 Task 的冻结输入与 Assignment 中选定的 Skill；未选 Skill 和主会话历史不进入请求。
- Protocol、Task、Profile、Assignment 及可选 previous Main State 在 Provider 前按精确字节捕获，先做 canonical relative-ref 和 JSON Schema 校验；执行后及 Main State 发布前再次核对，漂移时 fail-closed。
- Skill 指令和 `document-read` 对同一份字节完成哈希与 UTF-8 解码，避免“先验哈希、后读不同内容”的窗口。
- Task budget、runtime ceiling、有效权限、工具 allowlist、显式模型槽和 Project data boundary 取可信交集；远程上传需要批准但本节点没有批准证据时直接阻断。
- 编译结果包含显式 Provider Adapter ID、冻结的规范 Provider capability identity、`ModelRequest`、`ApiSessionLimits` 和精确 client-tool handlers，不做 fallback。Adapter ID 是 Registry 查找键，不能与 Provider 响应自报的规范身份混用。

### 4.2 bounded API runner

- fresh session 有模型回合、工具调用、单轮 fan-out、工具结果字符数、单轮输出、累计 token/可得成本和 wall-time guard。
- `max_parallel_tool_calls` 是单轮 fan-out 上限；当前 handler 按顺序串行执行，不宣称并行。
- token/成本在响应后检查，wall time 在调用前后检查；这些 guard 不能取消 in-flight Provider 或工具调用。
- Provider/模型身份和 Usage 数值在工具执行前校验。Receipt 的 `model_binding` 保存请求的 Adapter ID/模型，`model_usage.provider` 保存规范 Provider 身份；错误身份会停止执行其工具并阻断完成宣称。
- 工具失败只持久化本地调用序号、工具名和异常类型，不持久化 Provider call/response ID 或异常正文。

### 4.3 结构化输出与 closeout

- 模型只能提出受 Schema、Evidence source/hash、claim ceiling、locator 和 Transfer statement 一致性约束的 Research Objects 与 Handoff 内容；Attempt、路径、Receipt 和 Main State 由可信 closeout 生成。
- closeout 是 `stage → validate → 逐文件排他 publish → real-tree revalidate → Main State last` 的 commit-last 协议，不是多文件事务。Task 输入以执行前捕获的精确字节写入 stage，而不是链接到可变源文件；stage plan 锁定每个待发布文件的哈希。
- 动态 artifact 路径按模型返回的真实 `object_id` 再做 write-scope 和 allowed-root 检查；placeholder 不能授权别的路径。
- 完整、已验证的 stage 可在同一 `attempt_id` 下续发，不重放 Provider/工具；已提交 bundle 只有在合同、previous Main State、请求的 Adapter ID 和模型都相同时才验证并幂等返回。
- 恢复时会从 `task_id + attempt_id` 重建规范输出路径、重新执行 write-scope/allowed-root 检查，并把 optional previous Main State（包括 `None`）绑定到 intent、stage plan 和 committed fast path；调用者不能用同一 Attempt 静默换前序状态或发布位置。
- 在 Main State 发布前的最后边界，closeout 再次核验真实树中的合同、Task 输入、selected Skill lock、全部已发布非 Main 文件和 staged Main State；此窗口出现漂移时不提交 Main State，恢复源文件后可从 stage 续发且不重放 Provider。
- Provider 前以排他文件记录持久 execution intent。若进程在执行开始后、可恢复 stage plan 形成前丢失，同 Attempt 只返回 `API-ATTEMPT-RESULT-UNKNOWN`，不会自动重放；需要人工检查并显式创建新 Attempt。
- Main State 发布后即为 commit point。崩溃可能留下未被 Main State 引用的不可变孤立文件，因此不得把该协议称为跨文件事务。

## 5. 终态输出合同

| 终态 | 持久输出 |
|---|---|
| `completed` | Attempt、正式 Research Artifacts、Transfer Manifest、Transfer Audit、Handoff、task/main Context Snapshots、Execution Receipt、Main State |
| `safe-paused` / `incomplete` / `failed` / `blocked` | Attempt、Handoff、task/main Context Snapshots、Execution Receipt、Main State；不得伪造 Research Artifact、Manifest 或 Audit。`incomplete` 必须使用自己的有界下一动作，不得静默套用 `failed` 动作 |
| 合同文件在执行期漂移、执行结果不确定、stage 不完整 | fail-closed；不发布 Main State，也不自动重放同 Attempt |

模型/Provider 身份不符、工具失败、无效 Research Object、错误 Evidence 哈希或高风险 Transfer 语义都不能产生 `contract-satisfied`。

## 6. K-API-2 的验证证据

专项测试位于：

- `tests/test_api_execution_compiler.py`；
- `tests/test_api_session_runner.py`；
- `tests/test_api_execution_closeout.py`；
- `tests/test_k_api_2_pipeline.py`；
- `tests/test_io.py`。

程序化 fake-local fixtures 已覆盖 completed、tool-failed、safe-paused、`LENGTH/PAUSED/CONTEXT_LIMIT → incomplete`、stale/missing input，以及 Adapter ID/规范 Provider 分离、错误模型、无效/漂移合同、错误 Evidence 哈希、窄 write scope、同 Attempt 并发、intent 写入后的进程丢失、关键发布崩溃、Main 提交窗口的输入/Skill/非 Main 文件漂移、提交后部分清理和 fresh-process `resume-check`。

最终验证：仓库全量 `226/226 passed`；独立冻结字节 K2 专项 `92/92 passed`（compiler 18、session 16、I/O 6、closeout 11、pipeline 41）；Registry validator 为 `validated=53 errors=0 warnings=0`；变更 Python 文件 Ruff、文档链接与 `git diff --check` 均通过。三路只读复审均给出 `PASS`，未发现阻断性 P0/P1。未执行任何真实 API 调用。

## 7. 仍未证明与已知限制

- fake-local、合成 source、临时目录和 fresh Python subprocess 不等于真实 Windows 主 Agent/worker 会话。
- 三家 Provider 只有离线 Adapter 合同；实际启用槽的 live conformance 仍是 `M6-004`。
- 风险触发的 negative-result/conflict/assumption 候选当前转为失败 closeout，候选内容不会被保留；mandatory semantic review 也尚不支持。因此本节点不是一般科研语义闭环。
- Provider 在中途异常时，已返回回合与工具的部分 aggregate 目前记为 unavailable，而不是虚构为零。
- `completed` 证明输出结构、引用、哈希与文件 closeout 合同成立，但通用路径尚未强制证明 Provider 实际调用过 `document-read`；只有 happy-path fixture 明确覆盖了该只读工具往返。
- 多文件目录快照不是 OS 级原子快照；本实现以同字节读取、前后包哈希、执行后合同复验和 fail-closed 缩小并发篡改窗口。
- 外部副作用幂等、真实 token/time 误差、科学正确性、Transfer 语义等价和多 Agent 净收益均未验证。
- 项目许可证、真实 evidence/simulation 案例与公开发布 Gate 仍需人类维护者决定。

## 8. 节点评审结论与当前停止条件

`K-API-2` 离线最小文件闭环 Gate 已通过。评审确认：

1. 编译输入保持最小，无主历史/未选 Skill 泄漏；
2. completed 与非 completed 的完成宣称由文件和机器验证约束；
3. commit-last、intent 和恢复边界未被误写成“事务”或“任意崩溃自动恢复”；
4. 文档明确区分 fake-local 证明与 live/科研证明。

当前依然必须停止。唯一下一动作是维护者决定是否明确授权 `M6-004`；Gate PASS 本身不构成授权。不要顺手扩展 GUI、数据库、多模态、streaming、server tools、新 Provider 或平台 Adapter。

## 9. 接手者最小回传

- 基线提交与工作分支；
- 修改过的正式文件；
- 执行过的验证及原始结果位置；
- 未证明内容和剩余风险；
- `K-API-2` 审查结论，以及唯一下一动作。

缺少以上任一项时，不应把聊天中的“已完成”同步回 Main State。
