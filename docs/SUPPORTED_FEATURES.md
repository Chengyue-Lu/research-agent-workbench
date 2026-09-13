# 支持能力与证据边界

RWB 当前为内部技术 alpha，适合契约验证、受限执行集成与离线实验。此页是公开能力及其证据等级的单一来源；
README、上手指南和模块导航均引用本页。任务排期和工程施工记录由开发侧维护。

## 证据等级

| 等级 | 能说明什么 | 验收边界 |
|---|---|---|
| structural | Schema、identity、引用、哈希、权限与文件闭包符合确定性规则 | 不判断方法适用性或科学正确性 |
| bounded | 在声明的本地输入、工具、预算与对抗性 fixture 中完成受限运行或重建 | synthetic fixture 的结果只适用于该固定范围 |
| live | 在明确账号、模型、工具和环境上实际调用并留下可核验记录 | 只支持被记录的 exact binding，不能外推所有 Provider |
| evaluated | 按预先声明的真实任务、强基线、指标及成本完成对照评估 | 需要真实评估结果；运行成功本身不构成科研净收益 |

## 当前支持矩阵

| 能力 | 可用入口或模块 | 当前证据 | 限制 |
|---|---|---|---|
| 项目初始化与离线输入校验 | `rwb init`、`project check`、`resources check`、`schema list`、`validate` | structural；可复用 no-Skill 项目、exact Runtime pin 与本地 Profile；Python 3.11/3.13 的 direct wheel 与 sdist→wheel 在 checkout 外验证 | 初始化不执行 Task；可选 offline-demo 只复现 bounded 工程示例，尚无一键研究运行 |
| Task / Method / Capability 契约 | [控制与能力模块](PUBLIC_GUIDE.md#控制与能力) | structural；Mode/Action、需求、供给、确定性选择与 Snapshot 引用闭合 | asserted facts 的结构成立不授予权限或 Human approval |
| Runtime Bundle / View / Thin Host / Receipt | [执行与留痕模块](PUBLIC_GUIDE.md#执行与留痕) | bounded；no-Skill / direct-tool 的本地合成闭包与失败路径 | 需要集成者显式构造合法执行输入；仓库 structural replay fixture 不能充当运行输入 |
| Trace、Handoff、State 与恢复候选 | [状态与证据模块](PUBLIC_GUIDE.md#状态与证据) | structural / bounded；文件闭集、受控 fresh-process 读取与固定 case behavior | 当前恢复候选仍需人类语义验收；不提供通用自动恢复或科学判断 |
| Source admission、Promotion、Claim trace、Run reconstruction | [状态与证据模块](PUBLIC_GUIDE.md#状态与证据) | structural / bounded；exact bytes、当场重执行等价、证据定位与合成 Run 重建 | 不证明历史运行真实性、来源科学质量或 Claim 已获接受 |
| 可选 Skill publication / mapping | [能力模块](PUBLIC_GUIDE.md#控制与能力) | structural / bounded；非空引用闭包由 synthetic fixture 验证 | 生产 Projection index 为空，当前没有随包发布的 Skill；legacy Registry 不授予新绑定资格 |
| Provider Adapter 接缝 | [执行模块](PUBLIC_GUIDE.md#执行与留痕) | structural / bounded；离线 probe 与合成 conformance | 当前发行面不承诺任何 live Provider binding；真实账号、工具调用与长期兼容性需独立验证 |
| 科研机制净收益 | 显式评估契约 | structural 的评估计划 | evaluated 真实对照实验尚未完成，尚无科研效果或成本净收益结论 |

许可证决定、scaffold 与公开文档的具名验收、远端分支保护和人类发布决定仍是首次发行的前置条件。
当前文档与包验证结果不构成发布授权。

开始体验：[上手指南](GETTING_STARTED.md)。概念与源码位置：[公开模块导航](PUBLIC_GUIDE.md)。
