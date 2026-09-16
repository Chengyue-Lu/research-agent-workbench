# CI contract shadow v1

本文件保留首版阶段结果；当前实现与 smoke 来源修正见 [SHADOW_V2](SHADOW_V2.md)。

TEST-PERF-002；owner Chengyue-Lu；R2；2026-09-16；Draft implementation。
用户已认可 [CI 重规划方向](CI_REPLAN.md)，并授权第一版实现、Draft PR 和 Issue #48 进度记录。
本版交付 P1 的输入模型与可运行对照报告；P1 的完整消费契约和 P2 的减测激活尚未完成。

## 实现

[`ci_contract_shadow.py`](../../../../.github/scripts/ci_contract_shadow.py) 读取 exact Git snapshots 和
accepted `ci-plan.json`，重新计算现有 minimum 并验证 plan digest、base/head/merge-base/target、
merge parents、changed paths、policy、selection 与各项义务。它支持 immutable historical replay，
不要求把工作区切到历史 PR。

统一输入 inventory 区分 document、evidence-data、archive-attributes、test-code/input、runtime-input、
executable、selection/coverage/packaging/repository authority、selection-policy-metadata 和 unknown。
可执行 mode、脚本后缀、shebang 优先于文档/归档标签；symlink/gitlink/mode drift 为 unknown。
嵌套 attributes 仅识别具体的 byte-preservation 规则，其余语义仍为 unknown。

报告只读取 **base** 的现有 impact contract groups；candidate 新增声明不进入 accepted_contracts。
本版没有建立与现有 policy 平行的选择 authority，也没有把未审阅的输入范围写成减测 contract。

对每条已选 consumer chain，保留原始边及 base/head 文件名引用的语法线索：
`read-target-syntax`、`write-target-syntax`、`name-literal`。语法形态不是 I/O 语义证明；
如 monkeypatch、动态 helper、输出 dictionary 或对象重载仍需要独立输入/调用契约。
报告明确标出 unbounded-resource、opaque-execution、data-instance-to-code-consumers 等审计入口。
已选测试和正式 obligations 不被删改。

## CI 接入边界

`ci.yml` 新增独立 `CI contract shadow (diagnostic)` job：下载已上传的 `ci-plan`，生成并上传
`ci-contract-shadow` artifact。没有执行选择 outputs，其他 jobs 和固定 aggregates 不依赖它。
诊断失败仍在 GitHub job 中可见，不被伪装为成功；它不授权 skip，也不替代任何 required evidence。

报告协议为 `report_kind=ci-contract-shadow`、`schema_version=1`、`execution_authority=false`，
只持有 `observed_plan_id` / `report_id`，不提供可冒充 plan v4 的 `plan_id`。
`activation.eligible` 固定为 false。CLI 禁止覆盖输入 plan，且不写 `GITHUB_OUTPUT`。

本 PR 改动 workflow executable semantics，现有规则仍要求 full behavioral bootstrap 与 repository coverage；
新 CI Python 源码另有 impact 100/100 和 critical 95/90。coverage policy 2.2.1 只新增此模块、
对应 suite 与正反映射，threshold/exclusions 保持不变。

## 本地证据

- 12 项新测试（含角色/路径/mode 对抗矩阵）通过。
- 新模块 140/140 statements、58/58 outgoing branches；无新增 exclusion。
- 真实 Git 场景中，文档被故意改错后，reader 仍在 report 的 retained consumers 中，实际 unittest 失败。
- 删除输入仍保留 old consumer；source 变化保留 ordinary 与 opaque consumers。
- 篡改或重新签名后降低 coverage、修改 selection/changed paths、错误 merge parents、candidate contract
  注入、report 冒充 plan、覆盖 plan 输出和 `GITHUB_OUTPUT` 写入均有拒绝/隔离证据。
- workflow regression 验证两个固定 aggregate 名称保持不变，shadow 不被执行 jobs 消费。

## PR84 immutable replay

输入为 archived plan `b2a8eb54ba3b2fcc3d2f5028ecf70152d45695f1be726ffdbd8a8295f0896b34`，
base `b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22`、head `dfe3165a90ebcef99d107aef8e790bf7abc0c13f`、
target `7bc70fab34f947ff0e506d8a6b9450dba099589d`。

| 结果 | 数量 |
| --- | ---: |
| document | 15 |
| evidence-data | 8 |
| archive-attributes | 1 |
| 新输入分类与旧 unclassified fallback 冲突 | 9 |
| retained dependency test modules | 91 / 92 |
| representative chains with unbounded-resource | 81 |
| other data-instance-to-code consumer chains | 10 |

一次本地分析耗时 7.360 s（不是 hosted CI 缩时结果）。此版把旧模型缺口变为可重放、可 review 的工件，
还没有消除 PR84 的 91/92 选测，也没有满足 C01 的最终精度/性能验收。
下一版需要用具名输入/consumer contracts 关闭这些边，再在可信 witness 支持下激活；不能按本表数字直接截断。

复现入口：

```powershell
python .github/scripts/ci_contract_shadow.py --plan ci-plan.json --output ci-contract-shadow.json
```

原始证据与最终 exact-head 验证见 [本轮 Attempt](../../../../work/TEST-PERF-002/A-20260916-006/RESULTS.md)。

## 旧分支补充验证

按用户授权，拉取 #65、M14 #77/#80 的不可变 base/head，使用原 PR metadata 重放当前引擎。
原分支不变；target=head，结果不冒充历史托管 merge CI。

| 样本 | dependency modules | behavioral / coverage | smoke package / repository |
| --- | ---: | --- | --- |
| #65 test/fingerprint | 4/70，final plan 为 5 selectors | focused / none | false / false |
| #77 M14 Quickstart | 86/87 | full / repository | true / true |
| #80 M14 Source CI | 92/93 | full / impact + repository | true / true |

三项重放全部通过，正式 obligations、base groups 与 consumer chains 全部保留。
#65 在隔离的原始提交工作区实际执行所选 5 modules，134 PASS / 63.548 s；没有配对 full 执行，
不能由此声称 hosted 缩时比例。#77 的 pyproject、#80 的 workflow 变化为保留完整基线提供明确依据。

#80 的上述 test-level 链不能独立解释两项 smoke。v2 保留实际 affected source witnesses，
确认 CLI 的直接 opaque 边和 validation 的独立 unbounded-resource 边；后续以该源码级证据为准。

归档 `.log` 和旧 attributes 写法分别留下 1/7/22 个 unknown 输入，是后续输入契约需要补齐的分类范围。
本轮未为这些样本增加减测例外。原始计划、报告、metadata、#65 真实执行和初次托管 diagnostic 绑定
见 [分支测试 Attempt](../../../../work/TEST-PERF-002/A-20260916-007/RESULTS.md)。
