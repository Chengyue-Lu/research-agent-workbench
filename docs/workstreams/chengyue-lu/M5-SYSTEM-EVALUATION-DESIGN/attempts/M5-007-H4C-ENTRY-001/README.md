# M5-007 H4c 进入核对

日期：2026-09-27。Evaluation owner：路诚钺。Execution 接口复核：黄毅。
Agent Profile：Evaluation Harness 实施准备。Skills：[]。范围：进入核对与实施包细化。

## 核验的基线与接受边界

- `git fetch origin --prune` 后，远端及 `origin/develop` 均为
  `97d3b3d3141419b34ad47e0f42d9f01d0dfbd535`。
- [PR90](https://github.com/Chengyue-Lu/research-agent-workbench/pull/90) H4a 已接受合入；
  [PR96](https://github.com/Chengyue-Lu/research-agent-workbench/pull/96) H4b 已于
  `2026-09-26T16:41:18Z` squash 合入上述基线，原 head 为
  `e33422e153f84c3477701b7354dac22d3302f44d`。
- PR96 使用路诚钺亲自确认并授权的[单次维护者审核例外](https://github.com/Chengyue-Lu/research-agent-workbench/pull/96#issuecomment-5847972057)，
  [执行回执](https://github.com/Chengyue-Lu/research-agent-workbench/pull/96#issuecomment-5848003457)保留。
  不将 COMMENTED review 或该例外记成 cross-owner APPROVED；例外已经使用完毕。
- [实际 protected develop push CI36256347167](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36256347167)
  的 API 为 completed/success、headSha 等于上述 merge SHA，updatedAt 为
  `2026-09-26T17:21:51Z`。原文档中的“actual push 运行中 / H4b 待审”已经过期。

## 本轮准备交付

复用已完成 PR96 的空闲 checkout，创建 `feature/m5-007-harness-analysis`，从 exact develop
开始；旧 H4b 分支、远端与 archives 保留，本地 memory config 不提交。仅修正 M5 入口/STATUS/
implementation 的接受快照，并新增 [H4c 实施包](../../M5-007_H4C_PACKET.md)。

H4c 首先实现 measurement 的 run/Attempt/method/source association，然后闭合完整配对、
analysis-input overlap/pairwise/actual 重验及 frozen statistical parameters。旧数据缺外层时间
或成本继续 unavailable；H5 为后续完整 synthetic proof 与 R2 收口。

CI 窗口的测试组织维护候选 `1b97af282d5c0cf062785fcbb7734ce6260319bd` 保持独立本地分支，
未混入本准备分支或作为 H4c hard dependency。其报告中的首次 setup ERROR 和单项 cold replay
补跑证据保持原记录；它没有证明减测或使新 CI 规则生效。

本轮不修改源码/Schema/TASKS/ROADMAP，不运行业务全量、coverage 或真实模型；文档验证结果
为 `python -m unittest tests.test_documentation -v` 10 PASS（含全仓内部 Markdown 链接和表面权威检查），
`git diff --check` PASS。输入 pins 见 [INPUTS.json](INPUTS.json)。进入记录只证明当前准备依据，
不伪装成 H4c 实施 Trace 或已验证分析结果；历史 capture-gap 保留。

M5-007 仍 IN_PROGRESS。M5-008/004/005 的 live/case/admission/Human Gate 与 release 权限保持
原边界；完整 Harness 接受仍须 H4c、H5 及其各自 exact-head 证据。
