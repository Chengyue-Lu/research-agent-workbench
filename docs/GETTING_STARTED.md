# 上手指南

本指南演示仓库外的离线用户路径：安装、创建 no-Skill 项目、校验输入，再显式重建一个 bounded 工程示例。
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
rwb project check project
rwb validate project/tasks/task.yaml project/profiles/local-no-skill.yaml --root project
```

`init` 默认创建完整 no-Skill 模板：Project Protocol、Task、本地 Profile、工作目录、使用说明和资源 pin。
`project check` 校验项目身份、模板版本和安装资源的 exact hash；项目可移到新目录后继续检查。
Registry 和发布的 Skill 资源由安装包提供，无需从源码目录复制。初始化拒绝覆盖非空目录。
模板另有 `--template offline-demo` 离线工程示例和 `--template minimal` 最小入口。
`resources quickstart` 仍可单独复制安装包中的 [no-Skill Task](../examples/quickstart/task-no-skill.yaml)。

Task 的 `required_skills` 为空，同时保留输入、输出、权限、预算、写入范围和停止条件。
成功表示输入契约与引用可校验，尚未执行研究 Task，也未生成 Runtime Bundle、Execution View 或研究结论。
再次体验时选用新的项目目录。

## 4. 定位证据并重建离线示例

回到第 2 节创建的 `rwb-demo` 目录，为示例创建另一个项目：

```shell
rwb init offline-project --template offline-demo --project-id offline-demo
rwb project check offline-project
cd offline-project
rwb validate tasks/task.yaml profiles/local-no-skill.yaml --root .
rwb run check examples/run-reconstruction/linear-recurrence/manifest.yaml --root .
rwb hash examples/run-reconstruction/linear-recurrence/trajectory.csv
```

`offline-demo` 包含固定整数递推的 synthetic reference fixture。初始化只写文件，不运行代码；
其环境描述绑定到初始化所用的 Python 解释器。保持同一虚拟环境完成以下步骤。

先用文本编辑器打开 `examples/run-reconstruction/linear-recurrence/manifest.yaml`，按引用核对这些文件：

| 文件 | 用途 |
|---|---|
| `inputs.json.txt`、`parameters.json.txt` | 初始值与递推参数（JSON 内容） |
| `simulate.py` | 将由用户显式执行的示例代码 |
| `environment.json` | 当前解释器的环境绑定 |
| `run.yaml`、`trajectory.csv` | 合成参考 Run 与预期输出 |

`run check` 成功表示 manifest 中的文件 pin 与环境可校验；`hash` 输出可与 manifest 的预期输出哈希对照。
确认代码可信后，显式启动一个独立进程重建该例：

```shell
rwb run reproduce examples/run-reconstruction/linear-recurrence/manifest.yaml --root . --attempt-dir work/demo/A-001
rwb validate work/demo/A-001/reconstruction-report.json --root .
```

预期报告 `work/demo/A-001/reconstruction-report.json` 中 `status` 为 `matched`，随后报告校验成功。
报告记录本次实际捕获的输入、输出、stdout/stderr 与诊断；沿其文件引用查看证据。
参考轨迹的零净变化也是需要保留的结果。`matched` 只证明这组固定文件能够重建，不接受科学 Claim，
也不证明通用研究 Task、Provider 或 Skill 的效果。重建执行受信代码，不提供 OS sandbox。

每次重建使用新的 Attempt 目录，例如 `work/demo/A-002`。若已有目标目录，选新目录并保留原材料；
若 pin 或解释器环境不匹配，先检查文件和环境，勿把修改哈希当作复现成功。

## 5. 验证自己已有的工件

```shell
rwb validate /path/to/document.yaml --root /path/to/project
rwb trace validate --attempt /path/to/attempt --root /path/to/project
```

替换为自己的真实文件路径。项目文件从显式 root 读取，默认 Runtime catalog 从安装包读取。
平台配置通过独立 integration root 提供。维护者 Registry、Provider 配置和模型凭据须由相应命令显式指定。
Trace 验证检查事件、索引和结果闭包；方法适用性、Claim 接受与发布仍由具名人类决定。

## 6. 后续集成

Runtime 接入按 Capability Supply Report → Resolution → Snapshot → Runtime Bundle → Resolved Execution View
→ Thin Host 的顺序冻结并消费执行边界。no-Skill、direct-tool 与 Skill-bearing 路径共享该 Core；
Skill-bearing 路径额外携带其精确 Skill 绑定。该路径当前由集成者显式接线，尚无一键研究运行入口。

若 `rwb` 命令不存在，确认虚拟环境已激活，并运行
`python -c "import research_workbench; print(research_workbench.__file__)"` 检查安装位置。
若资源检查失败，从可信源码或 wheel 重新安装；若任务能力或权限冲突，复核输入边界并由任务负责人决定后续。

下一步：[支持能力与证据边界](SUPPORTED_FEATURES.md) · [公开模块导航](PUBLIC_GUIDE.md) · [总体架构](ARCHITECTURE.md)。
