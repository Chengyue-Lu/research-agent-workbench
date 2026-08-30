# 上手指南

本指南面向第一次接触 RWB 的开发者，演示当前受支持的离线 alpha 路径：安装、验证仓库、解析一个不依赖 Skill 的 Task，并理解输出边界。全程不调用模型、网络或外部服务。

## 1. 准备环境

需要 Python 3.11 或更高版本、Git 和 PowerShell、bash 或等价终端。克隆仓库后，在根目录建立独立虚拟环境并安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

如需运行测试，可安装 `python -m pip install -e ".[test]"`。

## 2. 验证仓库基线

```powershell
rwb validate examples registry
rwb schema list
```

第一条命令检查示例与 Registry 的 Schema、引用和确定性规则；第二条列出可用 Schema。成功只说明结构与引用有效，不代表研究内容科学正确。

## 3. 初始化一个最小项目

```powershell
rwb init work/quickstart-project --project-id quickstart
```

该命令创建最小文件式项目入口，不会复制完整仓库模板、安装外部工具或启动 Agent。

## 4. 阅读一个 no-Skill Task

仓库提供 [`examples/quickstart/task-no-skill.yaml`](../examples/quickstart/task-no-skill.yaml)。它要求产出一个有界 Handoff packet，但不要求 Skill 或外部能力。

```powershell
Get-Content examples/quickstart/task-no-skill.yaml
rwb validate examples registry
```

重点观察：

- Task 自己声明输入、输出、权限和写入范围；
- `required_skills` 为空是合法结果；
- 预算、原子边界和停止条件仍由 Task 约束。

这个文件代表已接受的 no-Skill Task 语义，并会参与仓库验证。legacy alpha CLI 的 `task resolve` 目前仍
要求显式 Skill 或 Registry 中可选的 active Skill，尚不能为该文件生成 no-Skill Assignment；因此本指南
不伪造一条解析成功路径。这个兼容实现缺口集中记录在[实现状态](STATUS.md)，但不阻塞 M11 no-Skill /
direct-tool Core。当前 Runtime 接入应消费经过校验的 Runtime Bundle 与 Resolved Execution View；只有
Skill-bearing 或 legacy compatibility 路径才额外携带 Assignment。

## 5. 验证已有 Trace 或执行归档

当 Runtime 已经产生文件式 Attempt，可运行：

```powershell
rwb trace validate --attempt <attempt-directory> --root .
rwb execute verify `
  --attempt <attempt-directory> `
  --protocol <protocol-file> `
  --root .
```

Trace 校验检查 Envelope、Index、事件、工具结果与文件之间的闭集关系；执行校验在此基础上检查归档和协议约束。尖括号参数必须替换为真实路径。不要把校验通过解读为方法适用或科学结论已获批准。

## 6. 接入模型或其他 Runtime

核心集成顺序是：

1. 把外部 Tool、Adapter、Provider 或 procedure 映射为带 exact identity/version/hash、输入输出、权限、
   data-egress 与 side-effect 事实的 Capability Supply Report；
2. 由 Capability Resolution 比较 Requirement 与候选供给，并冻结 Resolved Capability Snapshot；供给方和
   Adapter 不得自行选择自己，也不得放宽上游边界；
3. 生成 Runtime Bundle 与 Resolved Execution View，再让 Thin Host 只消费该 exact View；no-Skill、
   direct-tool 和 Skill-bearing 路径共享这一 Core，Skill Assignment 只在需要时附加；
4. 把 actual execution facts、Trace、Artifact、Validation 与 generic Receipt 写成可重放闭包；
5. 把方法适用性、Claim 接受和 Human Decision 留给相应的人类 Gate。

Codex、OpenCode、自建 API Runner、MCP 或本地 CLI 都应停留在 Adapter/Driver 边界。平台会话可用于执行，
但不是跨会话权威状态；Host 不得在执行时重新选择 Supply 或静默 fallback。

## 7. 常见问题

### `rwb` 命令不存在

确认虚拟环境已激活，并重新执行 `python -m pip install -e .`。也可运行 `python -c "import research_workbench; print(research_workbench.__file__)"` 检查安装。

### 解析提示能力或权限冲突

不要通过放宽 Profile 或静默增加 Skill 来绕过。先检查 Task 的 `required_capabilities`、`required_outputs`、`permissions` 和 `write_scope` 是否必要；不能安全满足时应拆分或阻塞。

### 为什么没有自动启动 Agent

RWB 的可移植核心负责契约、解析、验证和连续性。实际模型调用由显式 Adapter 或原生 Runtime 执行；这避免把某一家平台变成核心依赖。

## 8. 下一步阅读

- [总体架构](ARCHITECTURE.md)：理解各平面和传递关系；
- [实现状态](STATUS.md)：确认哪些能力可用、哪些仍有限；
- [兼容性说明](compatibility/README.md)：处理旧工件；
- [开发协作指南](DEVELOPMENT.md)：开始贡献代码或文档。
