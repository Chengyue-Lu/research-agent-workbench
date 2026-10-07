# 公开模块导航

首次阅读：[项目章程](PROJECT_CHARTER.md) → [总体架构](ARCHITECTURE.md) → [上手指南](GETTING_STARTED.md)。
当前可用能力、证据等级与限制统一见[支持能力与证据边界](SUPPORTED_FEATURES.md)。

这里按稳定责任组织模块，源码链接指向同一发行源码树。模块存在说明实现位置，是否可用于当前任务还需输入、资格、权限和对应证据。角色、会话与模块没有固定一一对应关系；角色 baseline 承担职责，可选 Skill 提供有界方法。

## 控制与能力

| 责任 | 实现入口 | 契约入口 |
|---|---|---|
| Task、边界与 Handoff | [任务模块](../src/research_workbench/tasks/) | [Schema catalog](../schemas/v0.1.0/) |
| Mode、Action 与 Method | [方法模块](../src/research_workbench/protocol/) | [Mode catalog](../registry/modes/v0.2.0/) |
| Requirement、Supply、Resolution 与可选 Skill mapping | [能力模块](../src/research_workbench/capability/) | [Requirement index](../registry/capabilities/requirements.json)、[Projection index](../registry/skills/release-projections.json) |
| Protocol Profile 与方法义务 | [协议模块](../src/research_workbench/protocol/) | [Profile index](../registry/protocol-profiles.json) |
| Agent Profile 的模型、工具、权限与委派上限 | [能力模型](../src/research_workbench/capability/models.py) | [Schema catalog](../schemas/v0.1.0/) |

## 执行与留痕

| 责任 | 实现入口 |
|---|---|
| Runtime Bundle、Resolved Execution View 与平台适配 | [Runtime 模块](../src/research_workbench/execution/runtime_bundle.py) |
| Provider-neutral 执行与 Receipt | [执行模块](../src/research_workbench/execution/) |
| 文件式事件和 Attempt 验证 | [Trace 模块](../src/research_workbench/observability/trace.py) |
| 安装包资源、显式 root 与哈希 pin | [Runtime resources](../src/research_workbench/resources.py) |

## 状态与证据

| 责任 | 实现入口 |
|---|---|
| MainState、checkpoint 与显式恢复检查 | [上下文模块](../src/research_workbench/context/) |
| Research State 组合与 bounded fresh actor 候选接口 | [研究状态模块](../src/research_workbench/research_state/) |
| 来源、工件提升、Claim 定位与 Run 重建 | [工件模块](../src/research_workbench/artifacts/) |
| Schema、索引与引用校验 | [验证模块](../src/research_workbench/validation/) |

具名人类保留研究问题、方法适用性、权限放宽、Claim 接受和发布决定。状态解释使用独立只读 Guide 上下文，不自动回传 main 或写项目状态；这项职责边界不等于存在一键运行入口。架构关系见[总体架构](ARCHITECTURE.md)。
