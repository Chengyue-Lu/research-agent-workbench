# TEST-QUALITY-001 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| TQ-SUITE-001 | fact | dedicated suite 通过遗漏慢测试来冒充 behavioral correctness。 | 两版本 plain full discovery 保留全部 `test_*.py`；coverage manifest 对 omitted module 与 exact slow-test selection 具名，移出 coverage 不等于删除 behavioral test。 | controlled; repeated hosted full suites PASS |
| TQ-THRESHOLD-001 | fact | workflow、pyproject 与脚本形成多个可漂移 threshold authority。 | threshold 只由 `coverage_policy.yaml` 声明；checker 拒绝低于 90/95/90；workflow 不硬编码例外。 | controlled by checker tests |
| TQ-BRANCH-001 | fact | 没有 branch measurement 的 JSON 被当成满足 critical branch Gate。 | checker 要求 `meta.branch_coverage == true`，缺失即阻断。 | controlled by negative test |
| TQ-MASK-001 | fact | 高覆盖 critical module 掩盖另一关键文件的低覆盖。 | critical exact paths 逐文件计算 line/branch，不做 critical aggregate。 | controlled by checker tests |
| TQ-EVIDENCE-001 | fact | 百分比替代 allow/block 的正反 contract evidence，或同一测试同时冒充正反证据。 | 每个 critical file 映射到非空、内部唯一、互不相交的 positive/negative IDs；checker 只接受本次 suite JSON 中 outcome=passed。 | controlled locally; hosted evidence pending |
| TQ-EXCLUSION-001 | fact | wildcard、目录级、未声明实际 exclusion 或不存在的 policy exclusion 静默抬高 coverage。 | checker 将 `coverage.json` 的 actual `(path,line)` 集合与具名 policy 集合双向 exact 对账；仅登记两组 Protocol 声明体。 | controlled locally; hosted evidence pending |
| TQ-GLOBAL-001 | fact | policy 缩窄 source root 后以高覆盖子目录冒充 package 全局 90%。 | checker 固定只接受 `source_root == src/research_workbench`，并按该 canonical root 全量重算。 | controlled by adversarial test |
| TQ-SELF-001 | fact | 执行 Coverage Gate 的 checker 自身绕过 critical Gate。 | `check_coverage_policy.py` 纳入 critical_modules、95/90 与独立正反 evidence；无 checker-specific exemption。 | hosted coverage pending |
| TQ-GATE-001 | fact | 新 coverage/package check 未进入 branch ruleset，红灯不阻断合并。 | 轻量 aggregate jobs 保留既有 `test (3.11)` / `test (3.13)` identity，并传播 compatibility、coverage、package result。 | controlled; failing coverage runs propagated to both aggregate Gates |
| TQ-PERF-001 | inference | coverage suite 仍超过 12–15 分钟，或单次 runner 波动被误报成稳定优化。 | 每个 suite 输出 wall/test count/slowest/p50/p95；Generic closeout、长 Host 与完整 archive/recovery replay 保留在双 Python full suite；coverage 只运行 exact validator cases 与 isolated helpers。 | run 33240592061: 813.756s; current 527-test head pending |
| TQ-DUPLICATE-001 | fact | 同一 TestCase 经 `test_*` 与 `tests.test_*` 两种 module identity 被 coverage 重复执行。 | fixture/build helper 迁到非 discovery module；runner 按源码文件、类与方法生成 canonical identity，重复即阻断。 | controlled locally: coverage 543/543, full 604/604 unique |
| TQ-DOCUMENT-CRITICAL-001 | fact | `validation/documents.py` 中 Method、Authority、Capability/Supply 与 Phase B allow/block/hash 逻辑因大型聚合文件未列 critical 而绕过逐文件 95/90。 | Capability Requirement/core 之外，再拆出 `method_resolution_registry.py`、`authority_registry.py`、`capability_supply_registry.py`、`phase_b_gate.py` 并全部加入 critical/evidence；如实记录 `documents.py` 仍含其他域校验，不称其为纯 dispatch。 | focused contracts PASS; hosted per-file coverage pending |
| TQ-SOURCE-ADMISSION-001 | fact | 尚不存在的独立 Source Admission producer 被文档宣称已获 critical coverage。 | 明确记录当前映射仅为 artifact integrity + provenance relationship；未来 producer 必须新增 exact critical path 与正反 evidence。 | accepted current limitation |
| TQ-NAME-001 | fact | 历史 `capability/resolver.py` 因文件名被误作 M9 Capability Resolution，造成错误 critical ownership。 | Policy 明确 M9 demand/supply assessment 在 `supply.py`，Snapshot selected closure 在 `runtime_bundle.py`；legacy resolver 只保留 global coverage。 | corrected after initial baseline |
| TQ-SEMANTICS-001 | fact | 为填 coverage 修改 Runtime/Authority/Claim 行为或制造低价值断言。 | 本轮只改测试政策、runner、CI 与高价值负面测试；产品 contract 变更越界并阻断。 | active review boundary |
