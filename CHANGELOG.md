# Changelog

本文件只记录被主线接受、会影响使用者理解的基线变化。逐任务、分支和实验过程保存在[详细开发日志](DEVELOPMENT_HISTORY.md)。

## 2026-08-22 — Documentation surface baseline

- 分离 stable、status、planning、compatibility 与 history 文档权威；
- 新增面向首次使用者的 no-Skill 离线 quickstart；
- 将当前实现覆盖集中到 `docs/STATUS.md`，把旧工件回放移至兼容性说明；
- 增加 ADR 与 implementation 导航，并为稳定表面加入防历史泄漏测试。

## 2026-08-21 — File-authoritative execution trace

- 接受 Execution / Archive Trace Core：版本化 Envelope、Index、append-only event 与工具结果闭集校验；
- 接受 legacy execution adapter，使既有 Assignment / Attempt 可写入并验证规范 Trace；
- 明确 Execution Trace 只记录可观察事实，Method 决策与科学正确性保持独立。

## 2026-08-20 — Method-aware control model

- 接受 Mode Action、Method Resolution、Research State、Decision Authority 和 Strategy / Evaluation 的五平面架构方向；
- no-Skill、direct-tool、Human Gate、split 与 blocked 成为一级解析结果；
- 路线图与实时任务状态分离。

## 2026-08-19 — Mode-first capability governance

- Skill 选择转为从 Mode Action 和可重复 Need 派生；
- 增加 Skill 生命周期与精确版本约束；
- 固定历史 Skill 包退出新任务默认路由的兼容边界。

## 2026-08-19 — M6-004 live 验收（deepseek-v4-flash，Windows）

### Live evidence（与离线记录分开）

- `worker` 槽经 DeepSeek Anthropic 兼容端点完成一次真实 evidence 调用：AT-API-009 终态 `completed`，`rwb execute verify` 退出码 0；requested/observed 模型一致，用量可入账（4 请求，output 10254 tokens）。脱敏工件入库于 `docs/implementation/evidence/M6-004/`（execution-plan.yaml 因钉本机绝对路径按约定不提交）。
- `registry/providers/adapters.yaml` 新增 `deepseek-anthropic` 条目（enabled: false，`live_conformance: passed`，指向证据包）。

### Fixed（全部由 live 验收暴露，各配测试）

- 会话内核未捕获 `ProviderError`：provider 契约违约会从 CLI 栈溢出、不落任何工件；现在转为 `failed` 终态并保留已完成轮次的用量与 transcript。
- 结构化输出不耐受 Markdown 代码栅栏：剥一层 fence 再校验；错误信息附前 80 字符有界预览。
- 编译器默认并行工具上限 4 过低（真实模型单轮批量调用常见 5+）：调至 8，总工具数上限不变。
- 编译期 prompt 未约束最终消息格式/输出自封包：user 消息末尾新增最终 JSON 契约与"每文件一个对象、显式声明契约身份"要求。
- `examples/api-execution/task-evidence-live.yaml`：新增 live 任务（output 预算 16384，声明输出契约与正例为输入）。

### Known issues（已登记，见 PENDING_ADJUDICATIONS.md）

- safe-paused 终态触发 `RECEIPT-SAFE-PAUSE-CONTEXT-MISSING`：API 会话尚无 Context Snapshot 可钉，语义待裁定。

## 2026-08-19 — K-API-2 Task-to-API 文件闭环（离线）

### Added

- `src/research_workbench/execution/`：`compile_execution` → `execute_plan` → `closeout` → `verify_attempt` 的推倒重写实现，把已冻结 Task Packet + Skill Assignment 编译成有界隔离 API 会话，并以原子发布落盘 execution-plan、session-transcript、outputs、attempt、execution-receipt、handoff 与 check-report；closeout 终态为 completed/safe-paused/incomplete/failed，确定性检查 BLOCK 不伪造完成。
- CLI 新增 `rwb execute task` 与 `rwb execute verify`：`--scripted-session FILE` 与 `--allow-live` 互斥必选；脚本化路径以 `model_override=scripted-offline` 离线复现，live 路径只从环境变量取模型名与凭据且缺失时不半程执行。
- `examples/api-execution/`：两轮脚本化会话 fixture（read_file→write_artifact→completed，`.json.txt` 后缀不进入文档校验）与用法 README。
- 风险码 EXEC-TASK-ASSIGNMENT-MISMATCH、EXEC-PROFILE-MISMATCH、EXEC-INPUT-STALE、EXEC-SKILL-DRIFT、EXEC-MODEL-UNBOUND、EXEC-ADAPTER-MISMATCH、EXEC-WRITESCOPE-INVALID、EXEC-CLOSEOUT-INVALID、EXEC-CLOSEOUT-SUMMARY、EXEC-LIVE-NOT-ALLOWED 登记入 `contracts/risk_codes.py`。
- 离线测试：编译期风险码反向分支、脚本化工具全链路、四终态、Receipt 用量对账、verify 幂等与篡改检出、CLI e2e 与假凭据标记不泄漏。

### Boundaries

- 未新增共享 Schema 文档种类，未修改 Task/Mode/Skill/read/Handoff/Receipt 冻结接口；live 真实 Windows 验收属于 M6-004，仓库内不保存任何 key/url/model 名。

## 2026-08-13 — Repository foundation

- 建立人类治理、文件优先、provider-neutral 的项目边界；
- 加入核心对象 Schema、CLI、示例、Registry 和确定性测试；
- 建立受限写入、显式 Skill 绑定、Handoff、连续性与薄 Adapter 决策。
