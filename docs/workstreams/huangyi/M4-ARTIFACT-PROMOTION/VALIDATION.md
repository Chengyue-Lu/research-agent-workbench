# M4-002 验证证据

本轮：2026-09-05，针对 PR #54 在 `b61c05485aed1920814d6d615563aa5faf5f0880` 上的两项收尾审查。
集成基线为 `develop@6a032e12c30a88a501258eec8c0b5d6c6082d81d`。最终提交的 hosted checks 与具名
Task owner 接受以 [PR #54](https://github.com/Chengyue-Lu/research-agent-workbench/pull/54) 为准；本地通过
不等于 owner 接受，也不使候选 Task 状态提前成为 develop 真值。

## 本轮修复与回归

- host receipt discriminator 先于宽泛的 validation execution discriminator；真实 host 生成的 receipt
  现在可经通用 `rwb validate` 验证，无需 explicit-kind 绕过。
- 两条现有回归先增强、后修代码：旧顺序下分别因错误类型和 3 个 Schema errors 失败；修复后通过。
  正向链使用 `run_validation_execution` 生成实际三元组，验证全部 7 份 authority/promotion 文档，
  输出 `validated=7 errors=0 warnings=0`。
- TASKS 的实现说明、contract、STATUS、module、CLI 与 workstream 统一为 promotion-time validity。
  原始 Task 定义/验收、Schema、authority ceiling 与 promotion 执行逻辑未改。

## 本地结果

在独立 Python 3.11 venv 安装现有 `.[test]`，包含 Hypothesis；完整回归和 coverage 各执行一次。
原始测试 JSON、duration logs、wheel 与治理事件保存在本地 ignored Attempt
`work/M4-002/A-20260905-CLOSEOUT/`；这些本地耗时不作为跨机器性能比较。

| 检查 | 结果 |
|---|---|
| Focused + Schema + documentation + governance | 141 项：139 PASS，2 Windows symlink permission skips |
| Full compatibility | 855 项：852 PASS，3 Windows symlink permission skips；0 failures/errors；940.549 秒 |
| Coverage Policy v2 | 794 项：791 PASS，3 Windows symlink permission skips；global line 91.97%；32 个 critical files 全部达到 line >=95% / branch >=90%；1400.184 秒 |
| Promotion critical coverage | promotion.py line 97.96% / branch 96.46%；validation_host.py line 97.74% / branch 97.14%；document_kinds.py line 99.17% / branch 99.14% |
| Repository validation | `validated=183 errors=0 warnings=0` |
| Wheel / clean install | 69 Schema；确认从 clean venv 的 site-packages 加载；两条真实 producer 回归及 repository validation PASS |
| Static / links | compileall、documentation checks 和 `git diff --check` PASS |

Python 3.13 和 Linux symlink 路径由最终提交的 hosted compatibility/coverage jobs 验证；不以本地其他
Python 版本冒充该证据。数值报告完成后的文档整理不改变已经测试的 source/test/schema/registry bytes。

## 语义证据边界

eligibility 只由 promotion 时重执行 accepted pinned pipeline 并复现 PASS report/transcript 当场确立。
validation 三元组是 claimed provenance metadata；自声明 operator/time 仅参与格式与顺序一致性检查，
不提供历史权威。错误 PASS/report/transcript 会被阻断；byte-exact 自报历史可满足当前有效性，但不能
证明过去的 producer/operator/time。`test_byte_exact_fabricated_history_carries_no_historical_authority`
继续固定这个边界，两个既有 Schema 仍将 `validation_execution_fact` 固定为 false。

环境白名单和临时 cwd 不构成 OS 沙箱。CLI/contract 明确要求预先接受、受信且无副作用的组件；
宿主自身不向仓库写入的行为，不被扩展为对恶意已接受代码的隔离保证。失败三元组属于 durable failure
metadata，永不构成 eligibility。既有 source/target pins、负结果 disposition、receipt、staging、
TOCTOU、exclusive-create 与 rollback 回归继续保留。

三次完整重执行成本、非沙箱信任边界和整 registry hash 的多 Task 耦合已登记在
[RISK_LEDGER.md](RISK_LEDGER.md)，待真实下游案例验证；本 PR 不新增签名、沙箱、缓存或 registry 重构。
本证据仅支持 M4-002；M4-003 Claim Trace 与 M4-004 Run reproduction 仍须在本 PR 被接受并合入后
各自实现与验收，不把 checker 重执行解释为科学 Run 复现或科学正确性。
