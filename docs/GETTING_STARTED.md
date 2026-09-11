# 上手指南

本指南演示离线 structural 路径：安装、检查随包资源、创建项目入口，并验证一个 no-Skill Task。
安装需要获取 Python 依赖；安装后的这些命令不调用模型或外部服务。

## 1. 安装

需要 Python 3.11+，已验证的安装环境为 Python 3.11 和 3.13。取得本源码目录后，在根目录执行：

```shell
python -m venv .venv
```

PowerShell 使用 `.\.venv\Scripts\Activate.ps1` 激活；bash 使用 `source .venv/bin/activate`。
随后安装到该环境：

```shell
python -m pip install .
```

命令从本地源码构建 wheel 并安装。使用已取得的 wheel 时，也可执行
`python -m pip install /path/to/research_agent_workbench-0.1.0-py3-none-any.whl`，替换为实际文件路径。
这里不假设已有 PyPI 发布或可下载的正式发行物。

## 2. 在源码目录外检查资源

保持虚拟环境激活，切换到一个新的工作目录：

```shell
cd ..
mkdir rwb-demo
cd rwb-demo
rwb resources check
rwb schema list
```

`resources check` 校验随包 RuntimeResourceManifest 的 pin、文件哈希、索引和引用闭包。
Schema、Mode/Action、Authority、Requirement、Protocol Profile 和 Projection index 由安装包提供。
生产 Projection index 为空；资源检查成功不表示存在可执行的已发布 Skill。

## 3. 创建项目与 no-Skill 输入

```shell
rwb init project --project-id quickstart
rwb resources quickstart --output project/task.yaml
rwb validate project/task.yaml --root project
```

`init` 创建 `project-protocol.yaml` 以及 `objects/`、`tasks/`、`handoffs/`、`checkpoints/`、`work/` 目录。
它是最小项目入口，完整外部项目 scaffold 尚待交付。`resources quickstart` 从安装包复制
[no-Skill Task](../examples/quickstart/task-no-skill.yaml) 的 exact bytes 到新文件，并做结构验证；已存在的输出不会被覆盖。

Task 的 `required_skills` 为空，同时保留输入、输出、权限、预算、写入范围和停止条件。
成功表示输入契约与引用可校验，尚未执行研究 Task，也未生成 Runtime Bundle、Execution View 或研究结论。
再次体验时选用新的项目目录。

## 4. 验证自己已有的工件

```shell
rwb validate /path/to/document.yaml --root /path/to/project
rwb trace validate --attempt /path/to/attempt --root /path/to/project
```

替换为自己的真实文件路径。项目文件从显式 root 读取，默认 Runtime catalog 从安装包读取。
平台配置通过独立 integration root 提供。维护者 Registry、Provider 配置和模型凭据须由相应命令显式指定。
Trace 验证检查事件、索引和结果闭包；方法适用性、Claim 接受与发布仍由具名人类决定。

## 5. 后续集成

Runtime 接入按 Capability Supply Report → Resolution → Snapshot → Runtime Bundle → Resolved Execution View
→ Thin Host 的顺序冻结并消费执行边界。no-Skill、direct-tool 与 Skill-bearing 路径共享该 Core；
Skill-bearing 路径额外携带其精确 Skill 绑定。该路径当前由集成者显式接线，尚无一键研究运行入口。

若 `rwb` 命令不存在，确认虚拟环境已激活，并运行
`python -c "import research_workbench; print(research_workbench.__file__)"` 检查安装位置。
若资源检查失败，从可信源码或 wheel 重新安装；若任务能力或权限冲突，复核输入边界并由任务负责人决定后续。

下一步：[支持能力与证据边界](SUPPORTED_FEATURES.md) · [公开模块导航](PUBLIC_GUIDE.md) · [总体架构](ARCHITECTURE.md)。
