# 按组件执行的 CI

负责人 Chengyue-Lu；TEST-PERF-002；2026-09-27。PR105 实现候选，尚未切换 required checks。
依据 [Issue87 路线决定](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87#issuecomment-5852428933)，
日常开发采用 Python3.11、短 smoke 和稳定组件测试组；完整验收在明确 checkpoint 执行。
未登记跨组件回归和其他版本差异可能延迟发现，这是本路线明确接受的成本取舍。

## 日常流程

[ci_components.yml](../../../../.github/workflows/ci_components.yml) 名称为 CI components，
在面向 develop 的 PR 内容事件及 develop push 上运行。PR 正文、标题编辑由既有治理工作流处理，
不会重复执行业务测试。同一 PR 的过时执行取消；没有 workflow 级路径过滤。

| profile | 执行范围 |
|---|---|
| component | PR默认：3.11组件测试；构建/依赖变化另加3.13安装smoke，业务仍只在3.11执行 |
| integration-smoke | develop push：真实安装、短smoke与固定短回归 |
| checkpoint | 显式或有新输入的夜间检查：全仓测试，Python3.11 |
| release-checkpoint | 显式develop checkpoint：全仓测试与安装smoke，3.11/3.13，并核真实合入源治理 |

日常固定汇总名为 `CI result`。[ci_component_result.py](../../../../.github/scripts/ci_component_result.py)
核对 plan、各 Python 实际结果及适用 smoke。上游 failure/cancel/missing/skip 不能当作执行成功；
纯文档明确不要求产品 smoke。新结果不替代尚在使用的两个旧 test checks。

[ci_components.py](../../../../.github/scripts/ci_components.py) 按目录职责选组件整组，
追加直接修改测试、共享 fixture 的登记消费者和现存同名测试。增删与 rename 两侧均考虑。
未映射路径公开列入 unknown_paths，选最近组件、自身测试与短smoke，不自动升级FULL。
旧图分析器与其测试保留在 checkpoint 库存。

[run_component_ci.py](../../../../.github/scripts/run_component_ci.py) 从 Git base/head、merge-base、
policy与跟踪文件生成计划；执行端重算以发现误传。digest是一致性校验，不提供独立授权。
plan/native schema=0.1.0，authority=profile-result-only；汇总schema=1、contract_version=components-v1，
记录事件、ref、run/attempt、source、实际范围和结论。没有跨提交测试结果复用。

## 安装 smoke 与 coverage

[ci_component_smoke.py](../../../../.github/scripts/ci_component_smoke.py) 使用 fresh wheel 环境，
在 checkout 外执行8步：import/Schema正反例、Runtime资源、schema CLI、research-state注册、
离线项目初始化/检查、Task+Profile验证、非法timestamp的真实CLI拒绝。总预算120秒，失败即停。
解释器保留venv的lexical absolute path，避免resolve POSIX链接后误用base Python。

七项固定短回归保留hash/路径完整性、disabled provider、未批准发布、Schema/dispatcher与CLI边界。
原behavioral/adversarial测试没有删除。新链不收集阻断用coverage，标注diagnostic-only/not-collected。
本切片未增加自动coverage采集，也未把组件通过宣称为全仓coverage。

## Checkpoint

[ci_checkpoint.yml](../../../../.github/workflows/ci_checkpoint.yml) 独立运行，汇总名 `CI checkpoint result`。
手动选择checkpoint或release-checkpoint；普通PR修改函数不会启动全仓。
工作日02:30 Asia/Shanghai夜间计划由GitHub UTC schedule驱动。

[ci_checkpoint.py](../../../../.github/scripts/ci_checkpoint.py) 比较产品、依赖、测试及CI输入的Git blob指纹。
仅近期成功的该夜间工作流marker可抑制相同内容的下一次执行。失败、过期/缺失记录、输入变化或显式checkpoint
都执行。纯文档提交不反复触发全量；跳过只报告无新输入，不生成新回执、不把旧结果重签到新提交。

仓库默认分支当前为main。GitHub schedule与manual discovery需要workflow存在于默认分支；
合入develop本身不完成该登记。此次只准备实现，部署方式另行接受，不修改main或默认分支。

## 证据与交付边界

旧候选 [36294874387](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36294874387)
在a1983f3上通过42项实际测试、8步安装smoke：测试3.344秒，smoke12.993秒，run到汇总55秒。
这是上一版候选的单次观察，不能套到当前修改，也不是M14/M5加速百分比。
首次POSIX解释器失败与修复的原始身份保留在A-20260927-010及相应评估记录。

当前HEAD的局部测试、版本兼容和hosted结果见PR105正文及本阶段独立archive。
原生产36294876605的changed-lines覆盖失败保留，新绿色不改写它。
旧三组配对实验、完整输入闭包/witness与覆盖百分比不是本路线的上线前提。
版本消费、required切换和回退见[迁移包](COMPONENT_CI_MIGRATION.md)。