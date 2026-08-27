# TEST-QUALITY-001 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| TQ-SUITE-001 | fact | dedicated suite 通过遗漏慢测试来冒充 behavioral correctness。 | 两版本 plain full discovery 保留全部 `test_*.py`；coverage manifest 对每个 omitted module 具名说明。 | controlled by topology; hosted evidence pending |
| TQ-THRESHOLD-001 | fact | workflow、pyproject 与脚本形成多个可漂移 threshold authority。 | threshold 只由 `coverage_policy.yaml` 声明；checker 拒绝低于 90/95/90；workflow 不硬编码例外。 | controlled by checker tests |
| TQ-BRANCH-001 | fact | 没有 branch measurement 的 JSON 被当成满足 critical branch Gate。 | checker 要求 `meta.branch_coverage == true`，缺失即阻断。 | controlled by negative test |
| TQ-MASK-001 | fact | 高覆盖 critical module 掩盖另一关键文件的低覆盖。 | critical exact paths 逐文件计算 line/branch，不做 critical aggregate。 | controlled by checker tests |
| TQ-EVIDENCE-001 | fact | 百分比替代 allow/block 的正反 contract evidence，或 policy 引用未执行测试。 | 每个 critical file 映射到 positive + negative test IDs；checker 只接受本次 suite JSON 中 outcome=passed。 | controlled by checker; semantic review pending |
| TQ-EXCLUSION-001 | fact | wildcard、目录级或无责任人的 exclusion 静默抬高 coverage。 | 首版 exclusions 为空；checker 要求 exact path、lines、reason、owner 并拒绝 wildcard。 | controlled by negative test |
| TQ-GLOBAL-001 | fact | 加入外部治理脚本后 aggregate total 改变，掩盖 `research_workbench` 未覆盖源码。 | global line 仅按 policy `source_root` 下所有 coverage files 重新聚合；未执行源码仍由 coverage source inventory 计入。 | controlled by checker |
| TQ-GATE-001 | fact | 新 coverage/package check 未进入 branch ruleset，红灯不阻断合并。 | 轻量 aggregate jobs 保留既有 `test (3.11)` / `test (3.13)` identity，并传播 compatibility、coverage、package result。 | controlled by workflow; PR CI pending |
| TQ-PERF-001 | inference | coverage suite 仍超过 12–15 分钟，或单次 runner 波动被误报成稳定优化。 | 每个 suite 输出 wall/test count/slowest/p50/p95；保留 run 链接；慢点只进入后续 TEST-PERF-002。 | baseline pending |
| TQ-SOURCE-ADMISSION-001 | fact | 尚不存在的独立 Source Admission producer 被文档宣称已获 critical coverage。 | 明确记录当前映射仅为 artifact integrity + provenance relationship；未来 producer 必须新增 exact critical path 与正反 evidence。 | accepted current limitation |
| TQ-SEMANTICS-001 | fact | 为填 coverage 修改 Runtime/Authority/Claim 行为或制造低价值断言。 | 本轮只改测试政策、runner、CI 与高价值负面测试；产品 contract 变更越界并阻断。 | active review boundary |
