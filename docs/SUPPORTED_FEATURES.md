# 支持能力与证据边界

此页定义公开入口的使用契约、证据等级与限制，供 README、上手指南和模块导航引用。工程成熟度与任务状态由开发侧各自权威记录维护。使用发行包时按该包的固定来源身份解释证据；后续源码与未合并候选不会自动成为已发布能力。

## 证据等级

| 等级 | 能说明什么 | 验收边界 |
|---|---|---|
| structural | Schema、identity、引用、哈希、权限与文件闭包符合确定性规则 | 不判断方法适用性或科学正确性 |
| bounded | 在声明的本地输入、工具、固定参数与对抗性 fixture 中完成受限运行或重建 | synthetic fixture 的结果只适用于该固定范围 |
| live | 在明确账号、模型、工具和环境上实际调用并留下可核验记录 | 只支持被记录的 exact binding，不能外推所有 Provider |
| evaluated | 按预先声明的真实任务、强基线、指标及成本完成对照评估 | 需要真实评估结果；运行成功本身不构成科研净收益 |

这些等级说明具体证据能够支持什么，不能把某个模块的 structural/bounded 结果累加成全系统 live 或 evaluated 结论。live 事实还须在每次消费时核对 exact source/config/model/Host/Tool 与用途是否相符。

## 当前支持矩阵

| 能力 | 可用入口或模块 | 当前证据 | 限制 |
|---|---|---|---|
| 项目初始化与离线输入校验 | `rwb init`、`project check`、`resources check`、`schema list`、`validate` | structural；no-Skill 文件模板、exact Runtime pin 与本地 Profile；alpha 包有 checkout 外 Python 3.11/3.13 安装证据 | 初始化不执行 Task；可选 offline-demo 只复现 bounded 工程示例，尚无一键研究运行 |
| 离线示例与证据定位 | [上手指南](GETTING_STARTED.md#4-定位证据并重建离线示例)中的 `offline-demo`、`run check`、`hash`、`run reproduce` | bounded；从项目自己的 manifest 定位代码、输入与预期输出，独立进程重建后验证实际报告 | 合成参考 Run 与当次执行证据分开；保留零净变化；`matched` 不构成科学 Claim 接受 |
| Task / Method / Capability 契约 | [控制与能力模块](PUBLIC_GUIDE.md#控制与能力) | structural；Mode/Action、需求、供给、确定性选择与 Snapshot 引用闭合 | asserted facts 的结构成立不授予权限或 Human approval |
| Runtime Bundle / View / Thin Host / Receipt | [执行与留痕模块](PUBLIC_GUIDE.md#执行与留痕) | bounded；no-Skill / direct-tool 的本地合成闭包与失败路径 | 当前支持版本仍要求预算字段并执行相应限制，工作输入投影与新运行契约尚待迁移；需要集成者显式构造合法执行输入，仓库 structural replay fixture 不能充当运行输入 |
| Trace、Handoff 与 MainState 文件连续性 | [状态与证据模块](PUBLIC_GUIDE.md#状态与证据) | structural / bounded；文件闭集、checkpoint 和显式 resume-check | 可校验状态工件不表示自动恢复旧会话或接受研究结果 |
| Source admission、Promotion、Claim trace、Run reconstruction | [状态与证据模块](PUBLIC_GUIDE.md#状态与证据) | structural / bounded；exact bytes、当场重执行等价、证据定位与合成 Run 重建 | 不证明历史运行真实性、来源科学质量或 Claim 已获接受 |
| 可选 Skill publication / mapping | [能力模块](PUBLIC_GUIDE.md#控制与能力) | structural / bounded；非空引用闭包由 synthetic fixture 验证 | 生产 Projection index 为空，当前没有随包发布的 Skill；legacy Registry 不授予新绑定资格 |
| Provider Adapter 接缝 | [执行模块](PUBLIC_GUIDE.md#执行与留痕) | structural / bounded；离线 probe 与合成 conformance | 公开包不承诺任何 live Provider binding；来源侧具体部件的验收不自动授予新账号、配置、工具或用途资格 |
| 科研机制净收益 | 显式评估契约 | structural 的评估计划 | evaluated 真实对照实验尚未完成，尚无科研效果或成本净收益结论 |

Research State 组合、Research Attempt/Failure、Method Trace 与 bounded fresh actor 是有界候选接口；固定 synthetic case 行为不证明最终研究状态表示、语义接受或自动恢复能力。模块源码可定位，实际启用仍需对应输入和人类判断。

项目原创内容采用 [MIT License](../LICENSE)。[v0.1.0 alpha prerelease](https://github.com/Chengyue-Lu/research-agent-workbench/releases/tag/v0.1.0)有独立发布身份；后续版本继续需要就绪审查与具名人类发布决定。文档或验证通过不产生下一次发布授权。

开始体验：[上手指南](GETTING_STARTED.md)。概念与源码位置：[公开模块导航](PUBLIC_GUIDE.md)。
