# M5 Skill Closeout Replay Gate

- Gate identity：`M5-SKILL-CLOSEOUT-REPLAY-GATE`（Issue #55 Gate B）。
- 状态：**SATISFIED**；本 R2 收口记录获接受并合入 `develop` 后生效。
- 实施 identity：`M11-007`，`skill-execution@1.0.0`。
- Execution acceptance：黄毅（`let778750-cpu`）；Evaluation / Skill identity acceptance：路诚钺（`Chengyue-Lu`）。

## 接受依据

[PR #81](https://github.com/Chengyue-Lu/research-agent-workbench/pull/81) 于 `2026-09-15T14:17:44Z` 合入，
merge `7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba` 与获审核 head `c529ac19e09ad436980acd46209fd964d9c80977` 的 tree 完全相同。
黄毅的 [APPROVE](https://github.com/Chengyue-Lu/research-agent-workbench/pull/81#pullrequestreview-5211196644)
接受该实现及四个 synthetic lifecycle proof；其独立核验覆盖 source/file pins、隔离 replay 和 CI ordered projections。
路诚钺在本任务明确要求“对M11-007做收口与gateB收口，然后准备接手M6-008的开发任务。”，据此记录其 Evaluation / Skill consumer 范围内的收口接受。
这两项依据分别保留原文；本次文档状态变更仍按 R2 接受当前 head，不把实现 review 当作文档 PR 的批准。

| 必需证据 | accepted pin |
|---|---|
| 实现 / 集成 | implementation `e1022d408c805aefb81e9177020064fe85e0ebc3`；PR81 head `c529ac19e09ad436980acd46209fd964d9c80977`；merge `7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba` |
| 版本 / validator | `skill-execution@1.0.0`；Schema/producer/validator 的完整路径与 hash 见下表及证据索引 |
| synthetic vertical proof | [A-003 proof](../../../../work/M11-007/A-20260915-003/checks/vertical-proof.json)，SHA-256 `c71dd8394d19ee93afd1e036a9705dfae5107c8cf3ea0cd27bb2f65d1b7e59f0`；四个 case 的输入/输出、Receipt 与独立进程 replay pins 完整 |
| 独立正反验收 / compatibility | `tests/test_skill_execution_closeout.py`、`tests/test_skill_closeout_review.py`；Core/legacy 保持回归；用前/调用后事实、wrong-kind 零调用与矛盾重读反例均闭合 |
| CI binding | base `0bebafd81f0116a8269c63ac97378038a1eb2a5d`；head `c529ac19e09ad436980acd46209fd964d9c80977`；target `fef9abc85ba9fc74cf231f43a2f778dd7cfc5b03`；plan `55e01f39ef5122627e8844b45f59486639be1547d9433dd651ad7859e8b48b54` |
| CI 结果 | [content 34976956664](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34976956664) / [governance 34978544662](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34978544662) SUCCESS；focused 双 Python 各 1272 PASS；coverage 1248 PASS；source line 93.89%；两个 Skill 模块 100/100；repository 186/0/0；package 8/8 |
| 具名接受与 evidence index | [接受原文](attempts/GATE-B-CLOSEOUT-001/evidence/pr81-acceptance.json)；[Gate evidence index](attempts/GATE-B-CLOSEOUT-001/evidence/gate-b-evidence.json) SHA-256 `1791220e870babfc82f5485f70bf99c186bc8e3b00e60a8b973e4dd0f8901e97` |

## Schema 与执行实现 pins

下列字节与 reviewed head / merge tree 及 A-003 implementation source refs 一致。测试文件沿用各自
implementation 或 final-head 的证据身份；不将历史测试 hash 冒充当前源码 hash。

| repo-relative path | SHA-256 |
|---|---|
| `schemas/v0.1.0/skill-execution-consumption.schema.json` | `39df4b1c69fa4798e7103fb8fd97fcc8df718490b1079b20b24aff5f5707427f` |
| `schemas/v0.1.0/skill-execution-host-report.schema.json` | `352dded306dde7f7b5b72aa2d73262ff22c87f1e714c6fadfe85a9359467dfc7` |
| `schemas/v0.1.0/skill-execution-receipt.schema.json` | `2d3d3110697ec16870f2e0ef92f83b0bb6dfb6080d61a7ff94b1a0a0f5051608` |
| `schemas/v0.1.0/skill-execution-trace-fact.schema.json` | `72e3fccde36476da6c9af5e21c876e90c16e6e3001a85bfb2b04c95314c6825a` |
| `src/research_workbench/execution/generic_closeout.py` | `c0ebc1d212cb25586f277728e48a315bbbc5f8f4c0677940179896284074a7dd` |
| `src/research_workbench/execution/host.py` | `2229f666b13424e29af8a1cd9609ca19e1be8202548e1b7c1bff433cb12f9599` |
| `src/research_workbench/execution/skill_closeout.py` | `8c6ec0b6790452b1ecec03a4945bebf8187d4a278274f5b2fba72546b64588bb` |
| `src/research_workbench/execution/skill_facts.py` | `7f542631b9770fbb8dfa5b05d73f26463c69c9d68d0e47dfd8834b9fb594465e` |

## 满足的边界与剩余依赖

completed 的实际消费与 selected View 相等，且只达到 `action-capability-slice-only`；post-call-failed
保留独立 Trace 支持的真实 drift；preflight-blocked 无调用/actual facts；exception 或不完整 capture
拒绝 Receipt eligibility。全部 `task_completion=false`。M5 在评价侧独立比较 replay result 与 frozen overlay。

M11-007 DONE 与 Gate B SATISFIED 同时收口。M5-007 仍 BLOCKED，剩余实现硬依赖为 M6-008 DONE。
M6-008 的 [接手准备](M6-008-HANDOFF.md) 从 PR75 现有候选继续。真实案例、live conformance、
生产 Skill admission、科学有效性与发布决定各按原 Gate 承担，本 Gate 只闭合 bounded execution evidence。

开发归档为 scoped/gapped、safe-paused，保留 capture-gap warning；实现的四个 runtime proof 分别闭合。
原 A-002/A-003 与定义归档字节不变。以下历史段落保留候选形成过程，其状态不覆盖上方当前记录。

## Historical implementation candidate evidence

以下候选已收到 [PR81 review](REVIEW-REPAIR.md)。其 one-stage post-call proof 是修复前的历史证据，
原始归档字节保留；它不再作为当前实现验收证据，也不替换上方 accepted evidence 或 Gate 状态：

- implementation commit：`7b3405189e06210cae6552b0eb7699b049e14d73`，基于
  `develop@0bebafd81f0116a8269c63ac97378038a1eb2a5d`。
- extension identity：`skill-execution@1.0.0`；四种 Schema、validator、producer 与 fixture 的
  repo-relative source path/hash 见
  [vertical proof](../../../../work/M11-007/A-20260915-002/checks/vertical-proof.json)。
- proof SHA-256：`eeb86f824c398885df181e36d9e84c02bc3f3294e491da5649518a4114a6d312`。
  四个 case 分别保留 completed-with-tool、failed-model、failed-projection、preflight-blocked
  的全部输入与输出 pins，并记录 isolated-process replay result。
- [开发 Attempt](../../../../work/M11-007/A-20260915-002/README.md) 为 delayed/gapped
  `safe-paused` archive；运行样例各有独立 use-boundary Trace。
- implementation commit 的 Skill/documentation focused 37 PASS；27 项 Skill 正反验收包含
  缺事实、调用后补写、Host/Trace 联合改写、Projection identity 漂移和 subject closure 反例。
  最终 base/head/CI plan、full/coverage/package/repository/governance 与双方 review pins 留在实现 PR，
  接受后才更新上方 accepted evidence。

## Accepted repaired implementation evidence

- Review repair commit：`e1022d408c805aefb81e9177020064fe85e0ebc3`，依据
  [PR81 review](REVIEW-REPAIR.md) 分开 pre-use consumption / Core post-call binding，增加 before-call
  Skill closure assertion 与 canonical-path single-read 校验。
- 新 [vertical proof](../../../../work/M11-007/A-20260915-003/checks/vertical-proof.json)
  SHA-256：`c71dd8394d19ee93afd1e036a9705dfae5107c8cf3ea0cd27bb2f65d1b7e59f0`。
  四个 case 均经过独立进程 replay；post-call model drift 首次记录于响应阶段。
- [新开发 Attempt](../../../../work/M11-007/A-20260915-003/README.md) 保存 baseline 反例、
  114 PASS 回归与 100/100 Skill module coverage。开发 Trace 无 BLOCK、保留 capture-gap warning；
  runtime case Trace 分别闭合。最终 head CI、Execution review 与 merge 见 PR81；本收口记录另行绑定 Evaluation 接受。
