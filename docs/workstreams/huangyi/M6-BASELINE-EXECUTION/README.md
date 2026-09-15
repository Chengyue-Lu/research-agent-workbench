# M6-008 Baseline Execution 候选

更新：2026-09-16。Task / Execution owner：黄毅。风险：R2。
路诚钺已授权当前 Agent 接手 PR #75 的基线集成、回放修复与验证；任务归属不变。

本目录记录 M6-008 的实现候选，尚未接受，不宣称 DONE。共享输入契约已由
[PR #71](https://github.com/Chengyue-Lu/research-agent-workbench/pull/71)
合入 `develop`，squash commit 为 `60bdf8c28f6cf8c52c04e481e0309bbd6e8cba8b`。
本轮建议在原定义、依赖和负责人不变的前提下，将 M6-008 从 PARKED 激活为 READY；
实际状态只由 [TASKS.md](../../../TASKS.md) 维护。本候选及其离线测试不能关闭 M5 的正式执行 Gate。

## 目标与已实现路径

依照 [ADR-0020](../../../decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md)，
A1 `plain-agent` 和 A2 `plain-agent-tool` 使用 M6 隔离 API session。
候选从 frozen Protocol / Manifest 确定性编译公开输入，经实际注册的 Provider 和 A2 Tool
执行，保存 typed execution facts、Trace、最后响应工件、transport Validation 和独立 Receipt。
文件回放从这些记录重算结果，不启动 Provider、Tool 或新的研究执行。

这条路径的输出是可检查的 transport 事实。`completed` 表示本次受限传输正常结束，
`task_completion` 始终为 false；输出检查不批准 Claim、科学结论、Human Decision 或 Skill admission。
A3/A4 仍使用既有 M11 路径。M6 不生成 A3 qualification、不选择 Supply，也不修改 M5 共享契约的所有权。

## 公开输入与执行约束

上游先冻结明确的 public projection，字段仅为 `task_ref`、`instruction`、`input_refs`、
`required_outputs`。它必须绑定本次 exact Task pin，自身 FileRef 必须列入
`Manifest.frozen_conditions.context.initial_context_refs`；引用的公开输入须属于已冻结的
Task / context 输入集合。输入以严格 UTF-8 实际内容进入请求。

编译后的 `provider_visible_payload` 仅含 `instruction`、`inputs`、`required_outputs`、`tools`，
未知字段由 Schema 拒绝。A1 的 tools 为空，A2 仅增加已资格验证的 exact Tool definition/interface。
完整 Task、Profile、Mode/Action/Method、Capability 控制与 qualification 保留在不可见 metadata。
公开 instruction / output contract 不从 Task.goal / Task.required_outputs 自动复制；例如 Task 中的
`method-resolution` 控制义务不应流入 plain arm。冻结公开 case 时仍需人确认其科研含义与公平性，
字节和字段校验不自动证明自然语言无偏。

A2 producer 复用 M5 的 `validate_qualification`。运行输入须满足既有
`runtime-execution`、`execution_input=true` 及 Tool identity / implementation / interface /
availability / boundary / typed conformance 闭包。开发测试以合成文件构造这些契约并实际调用本地
只读函数；这不是生产 live conformance。checked-in `structural-replay` fixture 不能因此用于正式执行。

transport 在每次 Provider request 和 Tool invocation 前重验已读取的 pin 闭包、编译器、
实际 Provider/Adapter/Model/Runtime/Host binding 和 Tool availability；Tool 调用还核对真实 callable
的源码路径及哈希。同名 Tool 保留每条 Task-specific Requirement 绑定；接口与实现可复用，
每条 runtime Supply availability 都必须在每个使用边界有效。它检查 Attempt 的 frozen write scope、Task 文件权限和 allowed roots，
并拒绝超过 Task 已声明预算上限的 Manifest / Protocol 配置。

输入 token 上限和 Tool 结果字符上限分开。A2 的已 pin ProjectProtocol 须明确提供：

```yaml
context_policy:
  baseline_transport:
    max_tool_result_chars: 16000
```

上例是测试 fixture 的显式选择，不是默认值或 token 换算。A2 缺少正整数声明时拒绝执行；
A1 不消费 Tool 结果。该值复用现有 ProjectProtocol.context_policy 扩展和 ClientTool loop 边界，
不新增共享 Schema。`context.data_policy_ref` 当前明确消费 Schema-valid ProjectProtocol.data_boundary。

## 接口与文件入口

| 入口 | 作用 |
| --- | --- |
| [baseline_envelope.py](../../../../src/research_workbench/execution/baseline_envelope.py) | `produce_a2_qualification` 生成 A2 record；`compile_baseline_envelope` 编译；`validate_baseline_envelope` 重读源并严格比较 |
| [baseline.py](../../../../src/research_workbench/execution/baseline.py) | `observe_baseline_binding` 观察待冻结的实际 transport；`run_baseline_session` 执行一个 fresh Attempt 并保存 closeout |
| [baseline_closeout.py](../../../../src/research_workbench/execution/baseline_closeout.py) | `produce_baseline_closeout` 从 Trace/facts 派生 Receipt；`verify_baseline_receipt` 独立文件回放 |
| [Envelope Schema](../../../../schemas/v0.1.0/baseline-execution-envelope.schema.json) | 公开 projection 与 envelope 的严格结构 |
| [Fact Schema](../../../../schemas/v0.1.0/baseline-execution-fact.schema.json) | use-boundary actual fact 与 Trace 事件绑定 |
| [Receipt Schema](../../../../schemas/v0.1.0/baseline-execution-receipt.schema.json) | transport 结果、文件引用及无权威边界 |

调用方保存 envelope / Receipt 后，须保留其外部 FileRef（相对项目路径与实际字节 SHA-256）。
回放用调用方已知的 exact envelope pin，不能从待验证 Receipt 自报字段取得期望值。
下面仅展示消费接口；参数由已有 Attempt 的真实文件引用提供，不表示仓库附带一套已运行的 demo：

```python
from research_workbench.execution.baseline_closeout import verify_baseline_receipt

def replay_existing_attempt(project_root, receipt_ref, expected_envelope_ref):
    return verify_baseline_receipt(
        project_root,
        receipt_ref,
        expected_envelope_ref=expected_envelope_ref,
    )
```

Receipt 区分 `completed`、`post-call-failed`、`preflight-blocked`。
在初始结构/权限检查通过并建立 Attempt 后，Provider 异常、超时及使用边界漂移保留失败记录；
非法初始输入或不可写 Attempt 路径在写入执行档案前拒绝。源文件漂移时可保留失败及 envelope snapshot，
但完整 strict replay 仍会报告 pin 不一致，不能把“留下失败”写成“全部回放有效”。

## 验证与下一步

2026-09-16 根据 [PR #75 review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75#issuecomment-5685397753)
修复两个 P1 和一个 P2：同名 Tool 的绑定列表保留所有 availability；每份 Provider / Tool / session fact
写入后立即记录 hash-pinned `file-revision(created)`，回放要求它紧随所绑定的请求、结果或终态事件，
发生在后续活动之前。事件路径相对于 Attempt，与 decision refs 一致；外层 Receipt 仍使用 project-relative refs。
Validation checker 源码在执行前保存为 `checker-source.py`，回放核对固定归档路径、实际字节哈希、
checker identity 和创建事件。回放读取这个历史快照，不导入执行它，也不要求当前安装相同源码。

专项反例覆盖运行前、Provider 返回后、Tool 返回后过期，调用后补写 before fact，逐份事实的缺失、
重复或迟到创建事件，以及 checker 路径、pin 和实际文件漂移。旧实现错误接受已复现，修复证据及最终
CI 绑定由本轮 PR 记录。`A-20260916-001` 保留旧候选原始字节；其中缺少创建事件与 checker 快照的
Receipt 不满足本轮候选要求，不能作为当前回放通过证据。本轮未修改已接受的 M5 / M11 契约。
本轮 [独立归档](../../../../work/M6-008/A-20260916-002/README.md) 绑定实现 `0877542`，
保存 38 项通过的专项证据及 A1/A2 cold replay；三个 M6 模块 line / branch 均为 100%。
ZIP 的 169 个成员哈希逐一通过验证，development Trace 无 BLOCK，保留 capture-gap warning。

2026-09-16 接手时，PR #75 从 `60bdf8c` 基线迁移到 `develop@7b1323f`，
保留已合入的 M11-007 实现与独立 PR #82 收口边界。新增
[回放完整性测试](../../../../tests/test_baseline_replay_integrity.py) 复用一份实际 A2 成功档案，
修改内容后重算全部外围哈希，先复现 9 个错误接受的样例，再补齐四项检查：

- 每次 Provider request 精确匹配冻结公开 payload、Tool surface、控制参数及已观察到的历史。
- 每次调用前的 use refs 与从冻结 Protocol / qualification 推导的完整闭包相同；终态汇总不能补偿漏验。
- 每次 Tool 调用的身份、顺序与参数匹配 Provider 实际请求，返回字节绑定下一次请求的 Tool history。
- Validation subject refs 精确等于本次 Trace 与实际输出，拒绝额外或重复 subject。

历史回放按 v1 契约读取冻结字节，保留当时的 compiler identity，无需运行旧编译器、Provider 或 Tool。
29 项专项及新增 batch / oversized 两项共 31 项通过；三个 M6 模块同源码累计局部覆盖率
line / branch 均为 100%（549 条语句、114 个分支）。完整验证与当前提交绑定见 PR #75。

以下为原候选的历史本地证据，不能代替接手后的 exact-head 检查。原专项为 21 项 PASS：
[8 项 envelope 测试](../../../../tests/test_baseline_envelope.py) 与
[13 项 execution 测试](../../../../tests/test_baseline_execution.py)。它们覆盖真实 UTF-8 输入、
A1/A2 公开差异、共享 qualification、实际只读 Tool 调用、通用文档验证、fresh-process 文件回放、
Provider/Tool 异常、调用后超时、使用前漂移、实际模型变化、输入 token 超额、响应脱敏和
Receipt 自报 actual binding 被 Trace 驳回。
测试通过不意味着 hosted CI、全仓 full 或全局 coverage 已通过；最终提交证据由本轮 PR 补齐。

接缝修复前，本地按既有变更影响规则核对三个新增模块，共 480 条可执行语句、86 个分支，line / branch
均为 100%。21 项专项执行为 79.411 秒；随后仅将已有 A1 成功案例改用 API 默认 UTC 时钟并复验
该方法（8.124 秒），没有新增计时器测试。源码未变，局部 coverage 合并这次窄复验。
文档链接、Schema catalog 与 coverage inventory 三项窄检查通过。局部 coverage 不代表全局覆盖率，
也不据此新增性能阈值或扩张测试范围。

最终只读复核另发现 Tool fact 与 frozen qualification 的文件关系缺口。复用已有 A2 成功产物，
将两条 Tool ref 改指已读取的公开输入并重哈希，旧实现错误接受（反例 FAIL，10.308 秒）；
补齐 exact Task / Tool name / implementation pin 对比后同一方法 PASS（10.770 秒）。
成功执行、通用校验、cold replay 与变造拒绝在同一产物上完成；测试数仍为 21。
此次只复验受影响方法；前述局部 coverage 是修复前快照，最终源码覆盖率由 hosted CI 核对。
M6 候选完成 review / 必需检查后再作接受决定。M5 Harness 继续由路诚钺维护；真实 case、
当前 live conformance 和 Skill closeout / admission 条件仍按
[TASKS](../../../TASKS.md) 与 [ROADMAP](../../../ROADMAP.md) 推进。
M12/M13 的下一步保持 Phase C Human review 与真实反馈入口，参见
[PR #72](https://github.com/Chengyue-Lu/research-agent-workbench/pull/72)，不并入本次 M6 transport。

限制见 [RISK_LEDGER.md](RISK_LEDGER.md)，过程与证据边界见 [WORKLOG.md](WORKLOG.md)。
