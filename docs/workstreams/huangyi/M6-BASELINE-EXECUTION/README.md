# M6-008 Baseline Execution 候选

日期：2026-09-12。Task / implementation owner：黄毅。风险：R2。

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
的源码路径及哈希。它检查 Attempt 的 frozen write scope、Task 文件权限和 allowed roots，
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

当前候选的本地专项结果为 21 项 PASS：
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
