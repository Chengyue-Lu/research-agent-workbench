# M5-006 implementation work log

- Owner: 路诚钺 (`Chengyue-Lu`); Execution interface owner: 黄毅 (`let778750-cpu`).
- Task: M5-006; risk: R2; branch: `feature/m5-evaluation-protocol`.
- Starting base: `11c3b57dfbf8af0dc2587fc421d097e2544941c3`.
- Authorization: user requested implementation of the recorded [entry plan](ENTRY_PLAN.md).
- Input scope: accepted M5 Task/ADR/Gate and workstream, evaluation/Capability/Runtime contracts and their fixtures, repository validation/CI/governance integration.
- Write scope: M5 evaluation modules, new schemas/tests/fixtures, necessary validation/CLI/coverage integration, M5 implementation documentation and this workstream. Other worktrees remain independently owned.
- Execution: one Codex actor; no delegated agents, Provider experiments, release action or Human admission.
- Trace: local capture spool under `.rwb/m5-006/`; archived v0.1 records will disclose delayed capture, setup reads not captured in the spool, and any missing tool results. No hidden reasoning or secrets are retained.

## Progress

2026-09-12 PR70 integration: fetched/pruned origin and verified both the dedicated M5 worktree and
the primary `develop` checkout were clean. Rebased the 15 M5 commits from base
`1cb0c19c1182aac368cd61afee111249a86818bb` onto accepted PR70 at
`ab98caf25125e6567d8bb2c8afff02105b54c940`. The previous reviewed head was
`372363046509ca549ef2194881e0a7a7693b9aea`; the rebased implementation head is
`a61b1330e9b689f7ac60028f1bdc9212ed825be5`. Range-diff preserves every patch;
the Schema-test import context incorporates PR70's accepted validator-cache tests.
Historical checkout conversion affected seven Trace files during replay; each difference was verified
as line-ending-only before restoring the exact intermediate Git blob. Existing archives remain immutable.
The primary checkout was not changed. The new final candidate is validated under PR70's accepted CI
workflow, which shares ordered Python 3.11 behavioral execution with coverage and runs Python 3.13
compatibility separately. Old CI run 34670209343 and its approval belong to the previous head/base;
new exact-head plan/results and renewed review are recorded on PR71.

Next integration sequence, based on TASKS and Issue55: first accept M5-006 through PR71; then activate
Execution-owned M6-008 using the frozen A2 qualification contract. In parallel, define a separate
docs-only Task for the Skill-bearing generic closeout replay seam before implementing Gate B with
Execution review. M5-007 remains BLOCKED until M6-008 is DONE and Gate B is satisfied; its next
implementation milestone is synthetic four-arm Harness proof, independently of real-case data.
M5-001/002 case approval, M6-004 live conformance and production A4 admission remain M5-004 execution
gates. PR69 is still open; M14 public documentation and later M12/M13 work are not new M5 dependencies.
This integration record does not change Task definitions or downstream statuses.

2026-09-12 cross-owner review on `cc1e214d8fdeea9644a261305b26f38469ce4b59`:
[review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/71#pullrequestreview-5184735519)
accepted the preceding three fixes and requested case-scoped A3 comparison plus PR68 integration. Rebased onto
`1cb0c19c1182aac368cd61afee111249a86818bb`; the implementation index retains M5-003's non-executing label
and M5-006's link. Git checkout's line-ending conversion during historical Trace commits was verified to be
line-ending-only and restored from exact Git blobs before replay continued; historical archives stay immutable.
Updated the inherited M5 status/navigation paragraphs to distinguish implemented Protocol validators from
M6-008, Skill replay, Harness, real-case/live/admission obligations. Task definitions and downstream states are unchanged.

The pairwise validator still qualifies the full A3 arm and reloads every A3 Bundle/View. Its comparison step
selects only the overlay's exact Task FileReference, rechecks that Task's frozen A3 Method/Requirement closure,
then compares the paired surfaces. The regression observes the actual single-Task validator's qualified chains,
extends the in-memory frozen demand with a second Task, and checks the original package-effect result/digest,
selected-Task omissions, whole-arm omissions and path/hash mismatches. It is a bounded composition regression,
not a complete multi-Task disk execution or research experiment. Current-head checks and re-review remain on PR71;
the prior base's successful CI does not validate this new integration candidate.

Local verification on this revision: seven comparison/composition/preregistration tests PASS under coverage
(362.484 s); `comparability.py` has 66/66 covered statements and 14/14 branches. Documentation/coverage-policy
checks: 30 PASS; Schema catalog checks: 3 PASS; changed-file Ruff and `git diff --check`: PASS. All 129 prior
archive files match their pre-rebase Git bytes. A separate REVIEW-003 archive records this bounded repair;
the final archive commit and newly rebased base still require the existing hosted CI obligations and cross-owner review.

Hosted preflight [34669923680](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34669923680)
on `7c07616` rejected the impact proof mapping with `positive/negative reuse` before running coverage tests:
the combined composition regression was listed in both sets. Split its success and rejection assertions into
independent test IDs sharing the same bounded fixture helper; CI policy and production code are unchanged.
The preceding 7-test run remains diagnostic for that earlier test layout. The revised committed candidate is
checked with the actual planner and independent regressions before fresh hosted verification.

2026-09-12 PR #71 review repair: reviewed the comment on `1eac55de9293ff0e5b19f9b838307d8a0650cf0f`
and reproduced the completeness gaps. Added schema/semantic confirmatory admission pin enforcement, exact
Task/Method Requirement closure for A3/A4, and unique admitted extension counting. Synthetic fixtures now bind
both document-read and research-contract-check through independently validated capability slices, including one
Skill serving both. M5-003 and Runtime contracts remain unchanged. The original implementation archive remains
immutable; this review attempt records subsequent evidence separately, with capture gaps disclosed. Current-head
validation and review status are recorded on the same PR; earlier CI applies only to its own head.

The follow-up review preserves Requirement uniqueness within a Task even across distinct frozen Method refs;
separate Tasks may reuse the same Capability Requirement. An adversarial multiset that otherwise exactly matches
both frozen Methods is rejected. The new regression and case-scoped positive checks supplement the PR71 repair.
The initial local CLI replay also exposed an outdated editable Schema resource; rebuilding the editable install
restored exact Schema-byte equality and the affected test passed without changing the implementation.

2026-09-11: fetched origin; base unchanged; only the prior entry-plan file was untracked. Verified current Snapshot, Bundle and View validators as reuse points. M11 Core requires `no-skill` Method disposition for non-Skill and `skill-need|mixed` for Skill: current executable A3/A4 paths therefore cannot honestly claim an exact Skill-only delta.

Implementation and validation evidence will be added by slice. No new Task is marked DONE by this initial record.

Implementation pass: added S1/S2 protocol and qualification, S3 pairwise comparison, S4 overlap, S5 pre-run overlay and S6 public verifier/CLI/Schema registration. Existing M5-003 and Skill Evaluation schemas remain unchanged. First focused runs: 11 protocol/qualification tests PASS; 13 overlap/comparison tests PASS. Complete synthetic A4 lineage and A3/A4 pairwise probes PASS, with the pairwise result correctly downgraded to `skill-bearing-package`. Broader regression/coverage is in progress; these probes are not live/admission evidence.

Integration audit: the first partial coverage invocation was stopped to tighten independently supplied case pins and View/Manifest binding checks. Its partial output is not acceptance evidence. Added per-invocation Protocol/Manifest/schema-result reuse with content-based keys and reference rechecks; returned cached documents are copied so caller mutation cannot poison subsequent validation. No cross-invocation trust cache is used. Full focused tests and targeted coverage will run after these changes.

First implementation commit: `a3dfed5d9610bd0c60f68a6fb7ed6c56e0f53df2`. Its source passed 52 focused tests under coverage (559.604 s): all seven new modules reached 100% line coverage; six reached 100% branch coverage and overlap reached 95.83%. Two uncaptured-admission branches were identified for additional tests. The complete A4/pairwise integration subset passed 15 tests (102.729 s), including a coherently rebuilt View with a substituted model version. Earlier integrated focused pass: 40/40 (268.611 s).

Repository validation: 186 validated / 0 errors / 0 warnings. Documentation and coverage-policy tests: 30 PASS. Portable package smoke: Python 3.11.16 and 3.13.15, direct wheel and sdist-to-wheel, isolated and normal imports, all eight combinations PASS; Runtime resource manifest hash `03677958839e4ecc77a8aba0bc8036c9bf1f6aec8d369ef09a2edb1d8bbc67d8`.

Final audit adds complete provider-interface I/O comparison and integer-safe count validation. The old-head full run was stopped while still passing observed tests because the implementation was about to change; it is not a completed full-suite result. Final acceptance will use the revised head and a forced full CI plan retaining both impact and repository coverage obligations. The ordinary current plan selected focused + impact with no blocked reasons; no threshold or CI authority was weakened.

Trace export was probed separately: an initial invalid stream/scope encoding was corrected in the local export adapter; the corrected probe has no BLOCK and retains `TRACE-CAPTURE-DELAYED`. The formal archive will preserve actual captured payloads and evidence with their original diagnostic/commit boundaries, not reconstruct missing history.

Final delta checks: all three targeted tests PASS (58.290 s), covering uncaptured admission Task/input, arbitrary-size integral measurements and full interface I/O comparison. The implementation PR proposes M5-006 READY → DONE without changing its definition or dependencies. Acceptance remains gated by exact-head full/coverage/package/repository/governance CI and cross-owner review; M6-008, Gate B, M5-007 and real execution stay separately owned and gated.

[Implementation Attempt Archive](attempts/M5-006-IMPLEMENTATION-001/README.md) preserves the available construction evidence. Hosted CI runs and PR review are subsequent evidence bound to the PR's exact head; their logs/results remain in GitHub Actions. Capture incompleteness is explicit rather than filled with reconstructed events.

Formal Trace validation: no BLOCK; `TRACE-CAPTURE-DELAYED` warning retained. The Trace Attempt is `incomplete` because original capture was gapped; it does not claim a complete transcript or reconstruct unseen results. Contract implementation and the proposed Task status remain separately subject to CI/review acceptance. Final documentation links: 9 tests PASS.

2026-09-12 hosted CI follow-up: run [34618373895](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34618373895), bound to head `173d08e1779912b5454608520ec2eac7c3d59384` and base `11c3b57dfbf8af0dc2587fc421d097e2544941c3`, exposed one full Python 3.13 regression: the existing Schema catalog equality test omitted the eight newly registered M5 record kinds (1148 passed / 1 failed / 0 errors). The repair adds those eight explicit names and preserves strict set equality; production contracts and coverage thresholds are unchanged. This failed run is diagnostic evidence. The revised commit requires fresh exact-head full, impact/repository coverage, package, repository and governance checks before acceptance.

The hosted impact plan also includes the archived `export_capture.py` as an executable Python subject. Added four isolated synthetic-spool tests for byte preservation, observed versus missing results, explicit empty-spool gaps, path rejection and post-seal corruption. All four PASS; the unchanged archived adapter has 78/78 covered statements and 26/26 covered branches, with no exclusions. The new test module is included in the existing coverage-quality suite. Schema, documentation and coverage-policy regression: 33 PASS. Earlier full/coverage runs interrupted by these verification repairs remain diagnostic; the next exact-head run supplies final acceptance evidence. Original archive bytes are preserved.

## M5-007 进入准备（2026-09-16）

PR75 接受合入后，M6-008 Task 收口与 M5-007 READY 激活在同一 feature/R2 提案中进行，既有 Task 定义不变。新增 [Harness 进入计划](M5-007_ENTRY_PLAN.md)，按 H1/H2 冻结 plan/preflight → H3 fresh 四臂 synthetic execution → H4 replay/盲审/metric/analysis → H5 集成验收推进。此处仅准备实施，未实现 Harness、运行真实模型或关闭 M5-004 的真实 case/live/admission 条件。

## M5-008 task-definition（2026-09-17）

基于 `develop@0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`，按 Human 请求新增
M5-008 Live Evaluation Pilot Gate，作为 M5-004 hard dependency。独立分支维护 Task 行、派生图和
[pilot 验收定义](M5-008_LIVE_PILOT_GATE.md)；M5-007 定义与状态不变，PR86 H1/H2 不计作完整 Harness 接受。
pilot 独立冻结工程 dossier，必须走真实四臂 transport、实际 Provider/Tool、失败与 cold replay/盲审/分析
输入闭包；M6-004、A4 admission 和具名专项授权仍为执行前置。M5-008 为 BLOCKED；pilot 不产生
confirmatory net-benefit conclusion，M5-004/005 保持 BLOCKED。

[Definition Attempt](attempts/M5-008-DEFINITION-001/README.md) 记录输入、变更范围、检查与 capture gap。
本次无 live 调用、Harness 实现或 Task DONE；Task-definition PR 的 CI/review 单独绑定其最终提交。

## M5-007 H1/H2 分支与接口准备（2026-09-16）

PR84 已合入 `develop@0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`，M6-008 DONE、M5-007 READY。
从该基线建立独立分支 `feature/m5-007-harness-preflight` 和独立 Python 3.11.16 虚拟环境；editable
安装的 import path 指向新 checkout，`pip check` 与 `rwb --help` 通过。主 develop checkout 保持原样。

[H1/H2 实施包](M5-007_H1_H2_PACKET.md) 固定复用接口、调用方责任、拟定写入面、实现顺序和六组反例。
已核对现有 baseline plan 尚不编排 case/replicate/retry；overlap/overlay/comparability 必须接收独立的
case/time pins，A4 admission verifier 由授权评价侧提供；当前完整 synthetic A3/A4 fixture 的比较等级
保持 package effect。首次 implementation PR 再提出 IN_PROGRESS，并在实施开始前建立正式 Attempt capture。

进入基线回归：`test_evaluation_manifest`、`test_system_evaluation_protocol`、`test_evaluation_overlap`、
`test_evaluation_overlay`、`test_evaluation_comparability`、`test_evaluation_contracts`、`test_baseline_envelope`
共 **115 PASS / 0 skip**，60.775 秒；文档检查 **10 PASS**（含内链），repository validation
**186 validated / 0 errors / 0 warnings**，diff check PASS。本地检查日志保存在未跟踪的
`.rwb/m5-entry/`。这些结果是既有依赖的进入基线；新增 Harness、H3–H5、真实 case/live/admission
与科学收益仍须各自实施和验收。此次准备只修改 workstream 文档，不修改 Task 状态、源码或 Schema。

## M5-007 H1/H2 implementation candidate（2026-09-16）

在 `develop@0d4a1d00a4c32ca9b822df6482a95920e7c21b1b` 上实现两个 version 1.0.0 的评价侧 record：
确定性非执行 plan 和独立重算 preflight。H1 冻结 case/phase/replicate/arm/retry slots 与公共输入摘要；
H2 复用 M5 validators，并验证外部 qualification、overlap、overlay、pairwise 和 admission callback。
Task 提案仅为 M5-007 READY → IN_PROGRESS；所有 Task 定义、依赖、验收与其他状态逐项比较保持不变。

本轮反馈落实为三个接口约束：Harness 只读取 M6 已产生的 A2 qualification；H1 phase 不产生 primary
eligibility；H2 与 A3 组装使用显式 `preflight_checked_at`，重放由调用方提供 expected time。反例覆盖
内部调用 M6 producer、confirmatory phase 掩盖 overlap、自选时间、缺失 admission verifier、私有输入
哈希别名、记录/输入/validator drift 和 planned-to-actual 自我升级。

提交前候选回归 **176 PASS / 0 skip，247.800 秒**，含新增 Harness **24 项**及现有 M5/M6、Schema、
文档内链和 coverage-policy 检查。新增 H1 行覆盖 **100%**、分支 **95.83%**；H2 两项均 **100%**。
repository validation **186/0/0**；portable package 的 direct wheel 与 sdist-wheel 两条路径、四个隔离
安装 probe 全部通过，Runtime resources identical。初始诊断中固定向量预期、测试用过期时间和一次
文档测试模块名错误均已纠正；最终上述回归通过。coverage 阈值未降低，也未新增豁免。

[Attempt Archive](attempts/M5-007-H1-H2-001/README.md) 保留 Task snapshot、可观察工具记录与上述检查。
Trace v0.1 无 BLOCK，仅保留 `TRACE-CAPTURE-DELAYED` / capture-gap warning，Attempt 为 incomplete；
不将缺失的 provider frames/native events 重建为完整 capture。记录中的代码哈希绑定提交前候选字节；
最终 full/coverage/governance/package CI 绑定 PR 的 exact head/base，证据由 GitHub Actions 保留。
H1/H2 接受仍需 cross-owner review；H3–H5、真实执行与 M5-004 的 Human/live/admission 条件保持后续验收。

PR86 首次 hosted [CI 35105112446](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35105112446)
绑定 head `94448bf781730b4af8528089a79794b748be2c2b`，Python 3.11/3.13 全量各 **1,355 PASS**；
repository coverage policy 也通过（global line 94.96%）。CI 在更严格的 changed-branch 100% 门禁失败：
H1 尚未覆盖 synthetic Protocol 的 `admission_case_closure_ref=null` 路径。补充该非执行计划正例及
confirmatory Protocol 同样缺失 closure 时拒绝的反例；新用例本地通过，生产代码和所有门槛不变。
原候选 Attempt evidence 保持冻结，后续 exact-head CI 由 PR86 关联；首次失败 run 只作为诊断记录。

## PR85 后的 M5-007 集成（2026-09-17）

按具名 Human 授权，PR85 先合入 `develop@348d6257ddd28637c9d06abe177fc685ac4368b6`；
PR86 三个原提交纯 rebase，patch 内容不变。新基线 CI 发现新增 consumer record 的两处 pin 仍指向
Harness 注册前的 `validation/documents.py` 与 Schema catalog 测试。只更新这两处显式 hash，保持
accepted-base shadow drift、选择义务、全部测试断言与覆盖率门槛。详见
[Integration Attempt](attempts/M5-007-REBASE-001/README.md)；新提交仍须 exact-head CI 与有效审核。

## M5-007 H3 Draft candidate（2026-09-17）

按用户授权，从仍 OPEN 的 PR86 `b53a391ece3a4be7207c00c636dc9e1570e71473` 建立
`feature/m5-007-harness-execution`；进入与提交前观察到的 develop 均为
`0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`。父分支及主 develop checkout 保持 clean、原样。

[H3 实施包](M5-007_H3_PACKET.md) 交付四臂 local synthetic 调度、每个必需 M11 capability slice 的
独立 Host/Trace/Receipt、独占创建的 Attempt 账本和独立 cold replay。失败与重试按冻结顺序保留；
M11 slices 共用整臂预算，后续 slice 阻断不会掩盖已有调用。集成中的 Trace token-boundary 修复使
TASK-prefixed 路径继续形成有效 Skill fact，同时保留真实密钥脱敏。

提交前候选：H3 **22/22 PASS**（branch coverage 下 451.036 秒），两个新模块 line/branch 均
**100%**；含独立新进程中禁用执行端口、项目 Tool/checker 和外部进程的 replay。相关 H1/H2、
Trace 与 governance 回归 **148 PASS**，文档/Schema/coverage-policy **37 PASS**；repository
**186/0/0**，final portable package 的 direct wheel / sdist-wheel 四个安装 probe PASS，runtime
resources identical。失败的初期集成输出仅作为诊断保留，不作为候选接受证据。

[H3 Attempt Archive](attempts/M5-007-H3-001/README.md) 保存原始 Task snapshot、范围补充、候选
字节 pins、检查输出和部分 delayed Trace；capture gaps 保持显式声明。最终 full/global coverage 与
changed-line/branch 门禁由 Draft PR 的 exact-head/base hosted CI 执行；不把父 PR CI 当作 H3 的证据。
M5-007 保持 IN_PROGRESS，H4/H5 与真实 M5-004 条件按原计划推进；此次提交 Draft，不 merge。

## PR89 rebase 与正式 review 准备（2026-09-17）

PR86 已合入 `develop@51dc3ab477f21f18ac3829bf553b5b779d49a4fe`。按用户授权，以原父
`b53a391` 为边界只迁移 H3 提交；源码、Schema、H3/Trace 测试和原 Attempt Archive 字节不变。
语义合并 STATUS / WORKLOG，保留主线 M5-008 Gate；更新当前文档与 CI consumer 的 Schema
测试文件 pin。Task 定义和状态与 develop 相同。详情见
[H3 integration record](attempts/M5-007-H3-REBASE-001/README.md)；新候选证据与正式 review 状态
以 PR89 的 exact-head 检查为准。

## PR89 dispatch deadline review 修复（2026-09-18）

用户授权修复 review 并推送原 PR，无需等待远端 CI。进入候选为 `4b3101a`，develop 仍为
`51dc3ab`。原 P2 指出 slice 间归档、回放和准备时间可耗尽整臂预算，却仍启动下一个 Driver。

修复将可信时间检查放到 Host 完成 preflight 后、调用 Driver 前；所有 slice 共用首个 Host
起点与 Protocol 预算。超时保留零调用的 blocked Host/Receipt；Harness 的每 slice dispatch
观察与 Host 区间、实际决定和冻结预算独立交叉验证。Host 可选 guard 只能收紧调用许可，不能
覆盖已有拒绝，异常保留未完成现场。A3/A4 的 deadline 边界、Host 准备延迟、时间证据篡改和
原有完成/失败/retry/cold replay 纳入本地检查，详见
[review Attempt](attempts/M5-007-H3-REVIEW-001/README.md)。

原始 H3 与 rebase evidence 保持冻结。本地检查绑定候选源码 hashes，新 head 的远端 CI 与
cross-owner rereview 按 PR89 独立进行；本次只提交修复，M5-007 仍 IN_PROGRESS。

## M5-007 H4 进入准备（2026-09-19）

PR89 已由黄毅对 `d725f7e` APPROVE，并于 2026-09-18 合入 `develop@171d465`；合并树与该
reviewed head 相同。H1–H3 已接受，M5-007 仍 IN_PROGRESS。按用户“准备继续推进”请求，
从最新 develop 建立独立 `feature/m5-007-harness-evidence`，主 develop 与 H3 工作区保持原样。

[H4 实施包](M5-007_H4_PACKET.md) 固定 H4a actual evidence → H4b blind review/reveal → H4c
metric/analysis 的顺序。源码核对确认现有 measurement validator 不验证 run/Attempt evidence
关联，pairwise validator 不消费 actual facts；H4 将在评价记录层闭合这些责任。旧 H3 缺失外层
计时/成本数据时保持 unavailable，不能用 Host 区间或缺省零替代。首个实现节点为 H4a。

新建独立 Python 3.11.16 环境，pip check、当前工作区 import 与 CLI help 正常。现有 Protocol /
overlap / overlay / comparability / contract 五模块 **63 PASS，54.542 秒**；文档内链 **10 PASS**；
repository validation **186/0/0**。这是进入基线检查，不是 H4 实现证据。结果与输入 hashes 见
[entry record](attempts/M5-007-H4-ENTRY-001/README.md)。H4 实现开始前另建正式 Attempt capture。

## M5-007 H4a implementation candidate（2026-09-19）

用户授权“开始实现”，从 H4a actual evidence 开始。新增 evaluation-owned record、确定性编译与
外部上下文驱动的独立验证：先 replay 完整 H3，再核对每项实际 binding/Supply/Skill consumption。
所有预留 slots 和必需 slices 显式保留；失败 retry、未启动与零调用阻断不转写成成功。

新增实际值替换、遗漏、身份/哈希/validator 漂移和禁执行冷回放反例；catalog、Schema 与 coverage
inventory 一并注册。共享执行端口保持现有契约，Task/ROADMAP 无状态变更。
本地检查、源码 pins 与部分可观察事件见 [H4a Attempt](attempts/M5-007-H4-001/README.md)。
H4b/H4c/H5 仍待后续实现；该分支按普通 R2 implementation PR 请求黄毅审核，不自行合并。

## PR90 archive exporter coverage repair（2026-09-20）

独立核查 `d9042fd` 的 run 35449976025：1425 tests PASS 后，impact gate 因新归档 executable
`M5-007-H4-001/export_capture.py` 未出现在 coverage report 而失败。原始 exporter 和 H4a evidence
保持原字节，在已注册 `test_m5_trace_export` 中增加独立临时 root 的真实导出/失败反例。
8 个 exporter tests PASS，原 CI 配置下脚本 39/39 statements、12/12 branches；54 个集成检查 PASS。
证据及作用域见 [CI repair Attempt](attempts/M5-007-H4-CI-REPAIR-001/README.md)。
共享 CI selector/authority、覆盖门槛和路径分类由 Issue87 任务负责；本修复不修改这些表面。
旧 run 的 PASS 不归给新候选，远端 CI 保持异步；M5-007 仍 IN_PROGRESS，PR90 不自行合并。

## H4b 独立 draft candidate（2026-09-21）

用户要求推进 H4b 并建立独立 draft PR，PR90 继续等待审核。新分支从 PR90 `b9ad97e`
创建，面向 develop；H4a 尚未接受，draft 明确依赖及后续 rebase 顺序。实现提交 `e700b6f`
增加匿名包/私有映射、具名 freeze/reveal 及七个 Evaluation Schemas，所有入口独立 replay H4a。
本地专项 13 PASS、141/141 statements、12/12 branches；四臂新进程禁执行回放通过。
完整 scoped checks、边界与保留 capture gaps 见 [H4b Attempt](attempts/M5-007-H4B-001/README.md)。
H4c/H5 为后续节点，未运行真实 Provider，未给出 Human/Task/analysis 接受或 merge。

## H4c 进入准备（2026-09-27）

核对 PR90/96 MERGED 与 exact `develop@97d3b3d`；实际 push CI36256347167 completed/SUCCESS。
PR96 单次维护者审核例外已使用完毕，不记为 cross-owner APPROVED。修正上述实施后的当前入口
快照，历史 Attempts 保留。复用空闲 checkout，从 exact develop 创建 `feature/m5-007-harness-analysis`。

[H4c 实施包](M5-007_H4C_PACKET.md) 固定 measurement association→配对 analysis input 的交付顺序、
方法/观察/冻结 review 来源、缺测量状态、analysis-input actual/overlap/pairwise 重验与负例。
源码/Schema 未改；独立 CI fixture 候选1b97af2不混入。文档10 PASS、diff check PASS；
基线/接受与输入 pins 见 [进入记录](attempts/M5-007-H4C-ENTRY-001/README.md)。
本轮只完成准备；实施开始时固定新的 Task Attempt 和 exact candidate 输入。M5-007 IN_PROGRESS，
H5 与 live/Human/release Gates 保持各自后继验收。

## H4c implementation candidate (2026-09-27)

Implemented four versioned records and metric/analysis compile/validate APIs under the accepted H4c packet.
Retained all 13 statuses, actual failed/retry/unstarted scope, external method/observation trust and complete paired inputs.
Candidate verification and capture-gap disclosure: [H4c Attempt](attempts/M5-007-H4C-001/README.md).
M5-007 remains IN_PROGRESS; H4c review precedes H5 overall closeout. No previous exception extends to this PR.

## PR104 component-CI rebase (2026-09-28)

Rebased the four H4c commits from `97d3b3d` onto accepted PR105 `24e1a3e` without conflicts;
range-diff retains their original patches and the H4c source, tests and Attempts retain their bytes.
Registered H4c in the evaluation component and its fixture consumers in `tests/ci_components.json`.
Local adaptation checks: 15 component-selector tests PASS; all five relevant source/fixture inputs
select the H4c test module. This verification does not repeat the historical full or coverage runs.
The updated PR awaits its own component CI and governance results, then R2 review; M5-007 remains IN_PROGRESS.

## PR104 installed-source mutation test repair (2026-09-28)

Component run36333156402 on `20fc5be` retained 318 parent tests: 317 PASS, one evidence test
failed in two source-mutation subtests; H4c24 and installed smoke8 passed. The fixed CI result
correctly blocked the candidate. The test patched checkout src, while identity read the installed wheel.
Resolve its mutation paths from the actual imported package, preserving both mutations, original hash
equality, changed validator identity and saved-evidence rejection. Production and CI code are unchanged.
An isolated fresh wheel environment with the actual component executor reproduced both failures
(66.663 seconds) and passed the repaired case (64.323 seconds). Evidence remains under its original run;
the repair candidate awaits its own component results and R2 review, with no merge or Task completion.

## H5 dependent draft (2026-09-28)

User authorized forward implementation and an independent draft. PR104 is still OPEN at
`34a4b05`, with CI PASS and R2 pending; latest develop remains `24e1a3e`.
Reuse the current isolated checkout on `feature/m5-007-harness-proof`; preserve local config.
The [H5 packet](M5-007_H5_PACKET.md) keeps H4c acceptance ahead of integration/overall review.

Implement the developer-only builder/replayer and current-source integrated tests. Preserve a real
local transient Provider failure/fresh retry, all four arms, blind synthetic review/freeze/reveal,
13 unavailable/null metrics and frozen comparison parameters. Pin every retained file, the outer
request and trusted helper/authority sources; call the public analysis validator under denied
Provider/Host/network/process/proof-code execution. No production source, Schema or Task definition changes.

The complete 454-file proof is stored as an immutable ZIP to avoid Windows deep-path limits.
Every member's original pin survived ZIP/extraction; new-process archived replay PASS, 8 cells /
10 pairs / 8 completed + 1 failed + 7 not-started. Chain7 and independent current guard1 PASS,
docs/selector25 PASS, repository186/0/0, short installed smoke8 PASS with 106-module/106-Schema
byte equality. Proof-only coverage is diagnostic; no full/checkpoint or extra hosted run dispatched.
Initial assertion/path/encoding diagnostics and capture gaps remain explicit in the
[Attempt](attempts/M5-007-H5-001/README.md). M5-007 stays IN_PROGRESS, Issue55 OPEN, all live Gates retained.

## PR104 merge / PR106 H5 rebase and review entry (2026-09-28)

PR104 obtained named cross-owner R2 approval on `34a4b05cacbce81459720c3363ef781a55334b42`.
All required checks passed and review threads had no unresolved blockers. Normal squash merge
produced `develop@26eca5742ba08d504d273423471fd7aab876a6d5`.

Rebased the two H5 commits from the former PR104 head onto that develop commit without conflicts:
`f6a199b` → `17dc32d` and `a1aba27` → `7d09587`. `git range-diff` matched both patches and
the rebased committed Git tree was byte-identical to `a1aba27`; historical proof ZIP, pins,
Trace and Attempt records were not rewritten. Local user config remained outside the commit.
The earlier hosted component CI run 36346486222 was SUCCESS on `a1aba27`; it is not a claim
about the new head. After the live status/navigation updates, Python 3.11 documentation and
public-surface tests passed 23/23, including internal Markdown links; `git diff --check` passed.

PR106 now carries H5 alone over accepted H4c. Its own exact-head hosted checks and named
cross-owner R2 review remain required. M5-007 stays IN_PROGRESS and Issue55 remains open;
synthetic proof does not satisfy the live, admission, Human or scientific gates.

## M5-007 closeout preparation (2026-09-28)

With PR106 still OPEN/Ready, its exact head `68e612b` passed hosted component
CI36431821489 and governance CI36432661027; the requested cross-owner R2 review is
not yet an approval. Created a separate dependent `feature/m5-007-harness-closeout`
branch from that head. [Closeout packet](M5-007_CLOSEOUT_PACKET.md) records accepted
H1–H4c merge identities, H5 proof/CI pins, final acceptance checks and live Gate
separation. [Entry Attempt](attempts/M5-007-CLOSEOUT-ENTRY-001/README.md) retains input
hashes and capture limits. No H5 archive rewrite, product/Schema change, Task DONE,
Issue55 closure, live execution or PR106 merge occurred. This remains a Draft until
PR106 review/merge and a fresh exact-head closeout audit.

## PR106 normal merge / PR107 independent closeout rebase (2026-09-28)

Huang Yi approved PR106 at exact head `68e612b353233bb8faf739d5012876739793cd84`
after independent 8/8 proof tests and cold replay. Component CI36431821489 and
governance CI36432661027 succeeded; review threads were empty and merge state CLEAN.
Normal squash merge produced `develop@81a058b228a5da2a6f46192a954f62efc72895e3`
(2026-09-28 15:29:38 UTC). The approved head and merge Git trees are equal.
PR107's closeout-only commit was rebased onto the merge without conflicts;
`range-diff` showed patch equivalence. The historical closeout entry Attempt
remains pinned to the prior PR106 head. PR107 stays Draft for independent overall
Task review; M5-007 remains IN_PROGRESS and Issue55 remains OPEN.

## PR107 latest-base rebase and review entry (2026-09-29)

Fetched origin and rebased PR107's two docs-only commits from `develop@81a058b`
onto `develop@39cf61e9fc728a2a6c1494b7a641a011dd6bf114` without conflicts.
Both commits are patch-equivalent by `git range-diff`. The new base contains
PR102's M14 release diagnostics and does not change the M5 Harness source,
schemas or retained H5 proof. The closeout Attempt keeps its original
pre-PR106-merge pins; it is not rewritten as current-head evidence.
M5-007 remains IN_PROGRESS, Issue55 OPEN and the M5-008 live gate BLOCKED.
This PR is offered for review of the overall acceptance preparation, not a
Task DONE decision.

## PR107 rebase onto completed release baseline (2026-10-01)

Rebased the M5-007 closeout review candidate onto `develop@54192efed0fe68ab7b7bd2fb5005c8710b16535a`.
The `docs/STATUS.md` conflict was resolved by retaining both the accepted H5
implementation / pending M5-007 whole-Task state and the accepted M14 first-release
state. No M5 Harness source, Schema, trusted H5 replay helper or historical proof
changed in the intervening release commits. The old branch's docs-only
`jsonschema` CI dependency fix was already present in the new baseline and its
duplicate commit was omitted. The closeout entry Attempt remains pinned to its
original pre-PR106-merge inputs; current-head validation and review must be
re-established separately. M5-007 remains IN_PROGRESS and Issue55 remains OPEN.
The prior docs-only CI failure remains [run 36497143420](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36497143420);
the new baseline contains the correction, so this PR does not reapply it.
Python 3.11 related documentation/public-surface/CI/governance tests ran 138:
137 passed and one explicitly Windows-skipped case. A wheel built from this
candidate validated the repository examples/registry at 186/0/0; diff check
passed. Huang Yi's prior PR107 approval was bound to the old base/head and
must be refreshed for this rebased candidate.

## M5-007 whole-Task review entry (2026-10-02)

PR107's docs-only preparation was squash-merged by direct owner instruction as
`develop@2618ef4fa7a1b16722e097af9a91b00b40ec700a`. The earlier cross-owner
approval had been dismissed after rebase; there was no new-head approval or recorded
reviewer-unavailable decision. It is not whole-Task R2 acceptance. The actual
[component push](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36955201813)
succeeded; the parallel source CI was still in progress at this entry.

Opened a separate [acceptance review](M5-007_ACCEPTANCE_REVIEW.md) from that exact
source. Five historical input pins match their declared snapshot/archive, the M5-007
Task row is unchanged from the accepted H5 head, and product source/Schema/trusted
H5 helper bytes have no intervening Git diff. Focused current-source H1–H5 tests
passed 111/111 on Python 3.11.16; documentation/public-surface passed 23/23,
and the original 454-file archive cold replay passed. Exact commands, results
and output hash are in the [review Attempt](attempts/M5-007-ACCEPTANCE-REVIEW-001/README.md).
The actual protected-develop source CI for `2618ef4` later completed SUCCESS with all
12 jobs successful; the earlier in-progress observation remains a dated entry fact.
Task remains IN_PROGRESS, Issue55 OPEN, M5-008 BLOCKED; no
live/admission/analysis authority was granted.

## M5-007 whole-Task completion candidate (2026-10-02)

PR121's audit documents were merged as `develop@30600f2e9ae25852289f1d0ca12f114291c31457`;
that integration did not accept the whole Task. On the user's instruction to close
M5-007 first, one feature/R2 candidate now combines whole-Task acceptance, the
IN_PROGRESS-to-DONE status proposal, STATUS/derived navigation and the original
Issue #55 closure checklist. Scope and source pins are in the
[new completion Attempt](attempts/M5-007-COMPLETION-001/README.md).

Retained H1–H5 implementation/proof bytes and the existing 111-test/replay result
keep their original identities. Current documentation/governance and Task-row
checks are recorded separately. The twelve Issue criteria have evidence mappings;
named whole-Task review and merge remain the final closeout conditions. M5-008,
real case/admission/live/Human gates stay BLOCKED; no real calls or release action.
