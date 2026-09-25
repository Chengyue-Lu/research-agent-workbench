# PR90 H4a archive exporter coverage repair

Date: 2026-09-20. Owner: Chengyue-Lu. Reviewer: Huang Yi (`let778750-cpu`). Risk: R2.
Profile: main implementation agent. Required Skills: none. No subagents.

## Authorized scope and baseline

The user assigned PR90 repair to this task; the coordinating task owns Issue87 shared CI remediation.
Read set: repository guidance, H4 packet/Attempt, the archived exporter and Trace API, its direct tests,
coverage policy, and the existing CI plan/configuration/checker required to reproduce the failure.
Write set: exporter tests and this workstream's repair record; preserve original H4a source/evidence.
Budget: one bounded repair with deterministic local tests and coverage; publish to existing PR90,
leave hosted CI asynchronous, and request cross-owner review. No merge or Task/Gate state changes.
Stop and coordinate if a repair requires changing shared CI authority, selector, exclusions or thresholds.

Independently verified PR90 head: `d9042fd1611f152573a7d2cae176cb1e1ec70065`.
Base: `171d4654f88e926f239cdf25bc8168109b81f391`; workspace clean before repair.
[Original CI run](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35449976025):
coverage job `105915342990` ran 1425 tests successfully, then failed with
`impact module absent: docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-007-H4-001/export_capture.py`.
That result belongs to the original head, not this repair candidate.

## Coordination record

Source task: `01a07632-120f-7802-ba5a-3b4976b7eaa0` (RWB开发 (2)). Received instruction:

> 用户明确要求 PR #90 由“RWB开发 (3)”自行负责修复，本窗口“RWB开发 (2)”只负责 Issue #87 的 CI 整改。现已核查你提交的 d9042fd1611f152573a7d2cae176cb1e1ec70065：CI run https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35449976025 ，base171d4654f88e926f239cdf25bc8168109b81f391 / target737fb419...。coverage job 37m43s，ordered execution step37m24s；1425项测试通过后，impact checker报 `impact module absent: docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-007-H4-001/export_capture.py`。请核对并在你的PR范围修复此归档可执行脚本及其必要证明问题，保留原始证据和覆盖门槛；若需要改共享CI authority先沟通，由本窗口统一处理。B=1425,C=1399,交集1399,C−B=0，现有去重正常。42个新归档文件的unclassified fallback扩大全量属于本窗口处理的长期CI边界问题，不建议在业务PR里加路径豁免或改selector。原始CI证据正在保存至 `<assessment-directory>/pr90`；请独立核验远端当前head，避免把以上旧head结果当新head验证。

The supplied assessment directory was normalized to a portable label; its files were not consumed.
The coordinating task subsequently supplied this additional observation:

> 补充最终核查，完整报告已保存 `<assessment-directory>/pr90/REPORT.md`，summary.json / SHA256SUMS.json 含原始绑定。准确 target 为737fb4198eac1e51f42da2f2204971ef96ec5ace。没有观测到M5业务失败：1425全PASS，新harness_evidence原始覆盖102/102、32/32。失败是archive exporter缺少impact证据。仓库现有 docs/workstreams/chengyue-lu/TEST-PERF-002/RISK_LEDGER.md 的 Archived producer identity 已记录PR83对冻结producer源码证据的处理，可先核对其适用性，勿改CI做目录豁免。另H3/H4各25/15cases耗时480.638s/456.542s，占coverage case时间46.49%；两个最慢H4矩阵各有四次完整H3 replay，共享class fixture已经存在。这是后续必要测试内部成本的审计线索，不证明可删除负例或替换必需integration。优先自行闭合当前PR失败；长期CI模型与扩散整改由本窗口推进。

The referenced Archived producer identity section was checked. This repair keeps the existing script
path/bytes and satisfies its current executable coverage obligation. The performance observations are
follow-up input from the coordinating task, not a reason to remove H4 negative cases or change shared CI.
This repair retains a partial observable tool record. Original native events/provider frames and their
timestamps are unavailable; no full capture or reconstructed timing claim is made. Retained
[tool results](partial-tool-results.json) declare omitted initial reads and missing arguments/results.

## Repair and checks

Keep the original exporter and H4a Attempt byte-identical. Exercise the archived implementation in an
isolated synthetic root through the already registered `test_m5_trace_export` suite. Verify payload and
outcome preservation, explicit gaps, exclusive archive creation and post-seal tamper rejection. Local
coverage must include the real canonical script filename with every changed line and branch covered.
Four new H4 exporter tests live in the already registered `test_m5_trace_export` module. The CLI test
executes the exact original source bytes with its canonical code filename and a disposable `__file__`;
it therefore covers the real entrypoint without writing into the original Attempt.

- [Original-run evidence](original-run-evidence.json) binds the failed job, exact merge target,
  downloaded artifact hashes and unaltered failure excerpts. The 1425 PASS result remains old-head evidence.
- [Exporter tests](export-coverage-tests.log): 8 PASS (four existing, four H4), 5.150 seconds under coverage.
- [Local coverage](local-coverage.json): original exporter 39/39 statements and 12/12 branches, measured
  with the existing `ci_checks.coverage_config` generated from the original CI plan. Its module is
  still an impact obligation; no absence, uncovered changed line or branch remains for this subject.
- [Integration tests](integration-tests.log): 54 PASS, 3.545 seconds (documentation, coverage policy,
  CI checker). This does not claim full repository coverage or replace candidate hosted CI.

The original exporter/Trace/evidence tree and H4a implementation remain unchanged. The tests exercise
success, failure, attempted and unknown results, exact payload/Task binding, empty-spool gaps, existing
and escaping archives, and post-seal evidence corruption causing a blocking report and nonzero CLI exit.
At repair implementation `215e67251b11959595aaca1a417e23d25013a83f`, the actual candidate plan was
generated and passed the existing `ci_checks configure` verification. The exporter remains among all
four impact modules, with both impact and repository obligations. Running the same 8 tests under that
candidate configuration passed in 4.285 seconds and again covered 39/39 statements and 12/12 branches.
See [candidate verification](candidate-verification.json) and [candidate test log](candidate-export-tests.log).
This is subject-level local proof, not a claim that the new full CI has passed. Existing review and all
hosted gates remain required; publication uses the same PR90 and does not merge it.

Local [governance](governance.log) PASS for the repair implementation head. The final evidence-only
handoff retains the same measured exporter/test source and required subject coverage.
