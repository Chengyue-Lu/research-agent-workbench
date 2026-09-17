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
