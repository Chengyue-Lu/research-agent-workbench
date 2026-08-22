# 文档导航与权威边界

本目录按读者任务组织。默认阅读路径只描述已经接受的系统；计划、实时状态、兼容说明和历史证据各有独立入口。

## 第一次阅读

1. [项目章程](PROJECT_CHARTER.md)：产品长期使命、责任与边界；
2. [总体架构](ARCHITECTURE.md)：已接受的概念、传递关系与不变量；
3. [上手指南](GETTING_STARTED.md)：当前受支持的离线开发者路径；
4. [实现状态](STATUS.md)：当前成熟度、已实现能力与已知限制。

## 按任务查找

| 你要做什么 | 首选入口 | 后续入口 |
|---|---|---|
| 理解核心概念 | [总体架构](ARCHITECTURE.md) | [模块设计](modules/) |
| 运行或排错 | [上手指南](GETTING_STARTED.md) | [实现状态](STATUS.md) |
| 参与开发 | [开发协作指南](DEVELOPMENT.md) | [任务清单](TASKS.md)、[路线图](ROADMAP.md) |
| 查看实现协议 | [实现文档索引](implementation/README.md) | 对应实现说明与测试 |
| 理解架构决定 | [ADR 索引](decisions/README.md) | 对应 ADR |
| 理解旧对象或回放 | [兼容性说明](compatibility/README.md) | [历史与审计](history/README.md) |

## 文档表面及其权威

| 表面 | 只回答什么 | 权威文件 |
|---|---|---|
| Stable | 系统是什么、概念如何协作、长期规则是什么 | `README`、Charter、Architecture、Modules、Development |
| Status | 当前实现和成熟度如何 | [STATUS.md](STATUS.md) |
| Planning | 接下来改什么、依赖和实时状态如何 | [ROADMAP.md](ROADMAP.md)、[TASKS.md](TASKS.md) |
| Compatibility | 旧契约如何显式读取、迁移或回放 | [compatibility/](compatibility/README.md) |
| Audit / History | 为什么改变、曾经如何推进、证据在哪里 | [decisions/](decisions/README.md)、[history/](history/README.md) |

稳定表面不复制实时任务状态，不用历史迁移叙事解释常规路径。历史材料会保留，但不是新用户的默认入口。
