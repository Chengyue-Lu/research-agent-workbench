# M4-002 验证证据

状态：本地验证已在合并候选 HEAD 全部刷新完成；hosted exact-head CI 与 Task owner acceptance 尚未发生。

## 已完成的本地证据

| 项 | 结果 |
|---|---|
| Promotion focused tests | 62 项收集（`test_artifacts_promotion` + `test_artifacts_validation_host`）：60 项通过；2 项 Windows symlink 权限跳过，Linux CI 保留执行 |
| Promotion critical coverage | `promotion.py` line 97.96% / branch 96.46%；`validation_host.py` line 97.74% / branch 97.14%，满足 95% / 90% 门槛 |
| 对抗面 | pre-Attempt Task/registry/policy/host closure、稳定目录内完整自洽 fake checker/runner/host/policy/execution/PASS 链不再获得 eligibility、work 内自签链、record/report/subject/entry drift、时间倒置、额外/遗漏 entry、failed report/execution、prefix/accepted/existing target、duplicate identity、record/source/staging/target/receipt race、target+receipt rollback、repository receipt target drift、hand-written execution without host run、fabricated host receipt、failing checker reported as PASS、runner crash/timeout 仍落 durable fail fact、receipt closure/transcript drift、re-execution byte drift |
| Coverage Policy v2 | 按 PR #47/#49 优化路径仅在 Python 3.11 执行一次：794 项收集，791 PASS、3 项 Windows symlink 权限跳过；global line 91.88%；全部 critical line/branch 门槛 PASS |
| Full suite | Python 3.11 plain compatibility 只执行一次：855 项收集，849 PASS、6 项跳过（3 项 Windows symlink 权限 + 3 项 Hypothesis test extras 未安装，CI 均会执行）；本机没有 Python 3.13，不以其他版本冒充，等待 hosted exact-head CI |
| Repository validation | `validated=183 errors=0 warnings=0` |
| Wheel / clean install | Python 3.11 临时 clean venv 成功安装 wheel：`share/` 分发 69 项 Schema（含 `promotion-validation-host-receipt`），`rwb` console script 与 `rwb validation run --help` 可用，并完成 repository validation |
| Static checks | `compileall`、documentation 9、Schema 3、governance 67、Coverage Policy 21 项测试与 `git diff --check` PASS |

## Trusted validation host 闭合（2026-09-02）与 validity semantics 收口（2026-09-04）

注意：上表全部数值证据已在 validity semantics 收口之后的最终验证中刷新（2026-09-05，合并候选 HEAD，本机 Python 3.11）。

PR #54 第三轮 review 要求闭合 trusted producer P1：此前一份手写 `promotion_validation_execution` 加
自声明 PASS report（内部 hash 完全自洽、引用完全合法的 accepted authority 对象）仍可能获得 promotion
eligibility，因为没有任何机制证明 accepted runner/checker/host 真的运行过。闭合设计：

- 新增 validation host（`src/research_workbench/artifacts/validation_host.py`，CLI `rwb validation
  run`）：解析 pre-Attempt 权威链（revision-pinned canonical Task → accepted-policy registry → 该 Task
  revision 的唯一 accepted policy → checker/runner/host identity/version/source pin），在 scrubbed
  subprocess 中实际执行 pinned runner，并 exclusive-create report / execution / receipt 三份 durable
  文档；
- 新增文档种类 `promotion_validation_host_receipt`；`promotion_validation_execution` 新增必需
  `host_receipt_ref`；receipt 固定 `run_inputs_sha256` closure hash 与 transcript（exit code、
  stdout/stderr/report hash）；
- `check_promotion` 在其余检查全部干净后通过同一 host seam 对 live subject bytes 确定性重执行 pinned
  runner/checker，要求 byte-exact 复现 PASS report 与记录 transcript；任何不匹配以
  `VALIDATION-EXECUTION-UNPROVEN` 阻断——deterministic rebuild-and-compare，无需签名密钥；
- byte-determinism 成为 checker/runner 的 policy-owned 要求；runner 崩溃、超时或未产出 report 仍持久化
  `outcome=fail` 三元组（`report_produced_by: host-failure-synthesis`），是 durable fail fact，永不构成
  eligibility。

第四轮 review 指出语义级裂缝：上述实现证明的是 deterministic validation validity，而文档/Schema 声称的
是 trusted-host historical execution provenance；且 registry 的 `host.source_ref` 只被校验从未被执行。
实证探针确认：host 从未运行、report/transcript 与 pinned runner/checker 输出逐字节一致的伪造三元组
（含编造的 operator/时间）在修复前可通过 `check_promotion` 获得 eligibility。二选一收口经实证评估：

- **Producer-provenance semantics（未选）**：要求调用方无法离线重建的 attestation。探针证明伪造三元组的
  每个字节（report、transcript hash、run-inputs closure、全部 refs）都可从 repo 公开信息离线算出；
  绑定 `host.source_ref` 同样无效——pinned host source 本身也在仓库公开区。单一信任域内不存在
  调用方无法重建的 proof；引入签名/attestation 基础设施属于新全局依赖，需独立 ADR，超出本轮范围；
- **Validity semantics（选定）**：authoritative fact ≡ promotion-time 确定性重执行；三元组降级为
  provenance metadata（两个 Schema 以 `const: false` 强制 `validation_execution_fact`）；自声明
  operator/timestamps 明确为不可验证字段，从不参与 eligibility。伪造能力被限制在"声称真事实"之内，
  任何假 PASS 都被重执行证伪。

同源两处 contract mismatch 一并修正：runner 子进程环境从"复制 `os.environ`"修正为真实 scrub
（OS 必需变量白名单 + 丢弃凭据与 `PYTHONPATH` 等解释器污染开关 + 固定
`PYTHONHASHSEED=0`/`PYTHONDONTWRITEBYTECODE=1`/`PYTHONNOUSERSITE=1`/`TZ=UTC`）；"`promotion validate`
只读"修正为"不修改仓库状态，但在隔离临时目录实际执行 pinned pipeline 完成 rebuild-and-compare"。

对抗与边界覆盖（已随本轮最终验证通过）：

- `test_hand_written_execution_without_host_run_cannot_gain_eligibility`
- `test_hand_written_execution_with_fabricated_receipt_cannot_gain_eligibility`
- `test_failing_checker_reported_as_pass_blocks_promotion`
- `test_byte_exact_fabricated_history_carries_no_historical_authority`（强反例：通过验证但无历史权威，
  语义边界锁定）
- `test_runner_subprocess_environment_is_scrubbed`（ENV-SCRUBBED guard checker 端到端）
- `test_scrubbed_environment_allowlist_and_determinism_pins`

对应风险台账 M4P-VALIDATION-PRODUCER-001、M4P-VALIDATION-REEXEC-001、M4P-VALIDATION-RUNNER-FAIL-001、
M4P-VALIDATION-SEMANTICS-001、M4P-VALIDATION-ENV-001。

## 合并前仍需更新

- 已完成：rebase 到最新 `develop@dd2454b5595e33a12aa058529358d46d311a08c4`，保留 PR #53 的 M5 Task/navigation 真值；
- exact HEAD Python 3.11/3.13 hosted CI；
- 所有 review conversation resolved，且路诚钺对 exact HEAD 接受。
