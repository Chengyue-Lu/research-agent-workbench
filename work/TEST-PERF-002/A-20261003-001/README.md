# 慢用例实验交接

本归档是 R0 测试维护的 Compact Handoff，责任人 Chengyue-Lu。
[实施与实耗报告](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/SLOW_TESTS_20261003.md)。

- [Task 与授权范围](TASK.yaml)、[Agent Profiles](ACTORS.yaml)、[source binding](checks/source-binding.json)。
- [实际局部验证](checks/validation-complete.json)、[Provider 单配对](checks/provider-after-comparison.json)、[M5 三配对](checks/format-pairs-complete.json)。
- [真实副本隔离](checks/provider-isolation.json)、[路径与哈希闭包](checks/format-contract/result.json)、[独立证据复核](checks/FINAL_EVIDENCE_REVIEW.json)。
- [全量 CI 原生时长提取](checks/hosted-audit.json)、[分支覆盖核实](checks/coverage-mode-verification.json)。
- [交接](HANDOFF.json)、[capture gaps](CAPTURE_GAPS.json)、[冻结文件索引](MANIFEST.json)。

checks 的原回执保持原字节和原 run/进程身份；tools 与 agent-reports 用 txt 保存实际工具和报告来源，不进入 CI executable discovery。
完整 hosted ZIP、coverage DB、profile 和原始 setup 失败日志仍在任务审计输入中，未改写或删除。
有 capture gap，未宣称完整 Trace 认证、科学正确性或新 HEAD 全量绿色。
性能只证明列出的局部受控样本，不签发 repository coverage、新 target CI 或合并资格。
