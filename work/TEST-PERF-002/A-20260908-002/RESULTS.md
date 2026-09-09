# Revision 14: precision implementation and local validation

Owner: Chengyue-Lu; cross-owner: let778750-cpu; TEST-PERF-002 / R2.
Base: `bdbac11a0c9a17fa221f8cc8bdd522c1bf4f9087`.
Implementation commits: `2390e10ad12f5c2aa30e031e4f166cfc8afe2643` and
`151c5f82a4156364785b0868025c953e28055f1f`.

The planner derives impact proof tests from executable subjects, reviewed base proof mappings and
mandatory critical evidence independently of behavioral test/fixture changes. Critical subjects without
an explicit proof contract keep complete acceptance modules. Agent additions remain possible; reductions
in the proof list or its minimum provenance fail verification.

Proposed local-function contracts cover claim trace and release projection. They preserve initialization,
bindings, definitions, imports, call expressions and string/resource inputs. Unknown execution and boundary
changes restore the ordinary closure; new/changed consumers remain additive. The ordinary graph retains
its real import edges. The [consumer inventory](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CONSUMER_CONTRACTS.md)
requires cross-owner acceptance before these contracts can serve as a narrower base.

Coverage collection now uses a path filter retaining the canonical production/script roots, the executing
runner and each additional planned subject. Real subprocess tests prove aliased backend code is measured,
unexecuted production files remain missing, and unrelated test code is not instrumented. Collection and
JSON export use the same generated configuration. Thresholds and declared exclusions are unchanged.

## Local evidence

- Python 3.11.16 focused CI/selector/witness regressions: **113/113 PASS**, 285.369 seconds.
- Whole-file coverage: dependency analyzer **100/100**, planner **99.8008/98.9474**,
  CI evidence checker **99.3590/98.0000** (line/branch percentages).
- Changed executable statement/outgoing branch preflight is recorded in [checks/summary.json](checks/summary.json).
- Documentation and coverage-policy checks: **30/30 PASS**.
- Repository validation: **183 validated / 0 errors / 0 warnings**.
- Frozen claim positive control on the isolated proposed M14 base: 27 behavioral tests PASS,
  15 coverage tests PASS, impact gate PASS; source and downstream CLI faults are rejected by
  the same selected behavioral suite. Local elapsed times and exact refs are in
  [checks/claim-probe.json](checks/claim-probe.json).

The M14 probe base `cbda9c2c78da3cc647f5e73da160053fca2d6a4e` combines the first implementation
commit with M14 and an additional proposed release contract. It is conditional prototype evidence,
not accepted develop authority or a matched hosted speedup. Projection/release probes continue separately.
The final implementation's additive-request change is validated by the 113-test regression above.

Final-head full Python 3.11/3.13, repository coverage, independently required smokes, governance and
a fresh independently pinned witness remain hosted acceptance obligations. Cross-owner review remains
required. The Attempt is safe-paused with an explicitly retained native capture gap; no complete native
event export or completed workstream is claimed. Subsequent probe/hosted receipts are separate evidence.
