# 可复用项目 scaffold

`rwb init` 从安装包建立独立项目。项目只维护自己的 Protocol、Task、Profile、工件与 Attempt；
Schema、Mode/Action、Authority、Requirement、Protocol Profile 和发布的 Skill projection 由固定的
Runtime catalog 提供，不要求从开发 checkout 手工复制 Registry 或 Skills。

## 模板和根目录

| 模板 | 内容 |
|---|---|
| `no-skill`（默认） | Protocol、no-Skill Task、无 Provider 绑定的本地 Profile、使用说明与工作目录 |
| `offline-demo` | 默认模板，加上已有整数递推示例的代码、输入、参数、环境、Run、预期输出和 exact manifest |
| `minimal` | 保留最小 Protocol/目录入口，供已有用户显式选择 |

```shell
rwb init /absolute/project --template offline-demo --project-id local-demo --json
rwb project check /absolute/project
rwb validate /absolute/project/tasks/task.yaml /absolute/project/profiles/local-no-skill.yaml --root /absolute/project
```

输出明确给出 project root、Runtime root 和 Runtime manifest SHA-256。`rwb-project.toml` 保存
template/version、项目身份和 Runtime pin，不保存机器绝对路径；整个项目可移动后继续检查。
默认资源不从 cwd、父目录、环境变量或旁边的 checkout 搜索。自定义资源必须同时给
`--runtime-root /absolute/resources --manifest-sha256 <external-digest>`；创建与检查使用同一规则。
Integration root 仍由平台命令独立提供，scaffold 不创建 Provider 配置或凭据。

目标只能是不存在或为空的目录；文件、非空目录、符号链接和 reparse 路径均拒绝。
资源与模板先校验，再在目标父目录下暂存完整内容，最后安装目录；失败不覆盖用户文件。

## 离线用户路径

从本地可信源码或 wheel 安装后，在 checkout 外创建 `offline-demo` 项目。初始化不执行示例代码，
预存的 Run/trajectory 是明确标注的 synthetic reference fixture；环境绑定按当前 Python 实现、版本、
平台重新生成并 pin，不能解释为原历史运行的环境证明。

```shell
cd /absolute/project
rwb run check examples/run-reconstruction/linear-recurrence/manifest.yaml --root .
rwb hash examples/run-reconstruction/linear-recurrence/trajectory.csv
rwb run reproduce examples/run-reconstruction/linear-recurrence/manifest.yaml --root . --attempt-dir work/demo/A-001
rwb validate work/demo/A-001/reconstruction-report.json --root .
```

Manifest 定位输入、参数、代码和预期输出；report 定位该次独立进程实际捕获的输入、输出与诊断。
`run check` 只校验，`run reproduce` 才显式执行受信代码；后者不是 OS sandbox。每次使用新 Attempt
目录，保留零净变化这一 negative result。匹配结果只证明 bounded 文件重建，不产生科学正确性、
Claim 接受、promotion 或 Human Decision。

模板源位于 `src/research_workbench/_templates/offline-demo/0.1.0/`，catalog 和每个文件均校验
SHA-256；资源缺失、损坏、额外文件和链接均阻断。它属于安装包的项目模板，不扩展 Runtime catalog
的发布类别，也不改变既有 Registry、Schema 或 release-surface policy identity。

## 兼容与验证

版本和升级规则见 [CLI / Schema 0.x 兼容政策](../compatibility/CLI_SCHEMA_POLICY.md)。已有最小项目
仍可运行 `validate`、checkpoint 等原命令；`project check` 只识别新 scaffold 元数据，不静默接管旧目录。

[模板测试](../../tests/test_scaffold.py) 覆盖实际初始化/重建、搬移和 cwd poisoning、pin drift、损坏模板、
拒绝覆盖与失败清理。[双 Python package smoke](../../.github/scripts/portable_package_smoke.py) 在直接 wheel
和 sdist-to-wheel 的全新安装中执行同一路径。M14-004 的最终 Quickstart 接受仍是独立后续，M14-005
继续受许可证、远端保护和具名发布决定等 Gate 约束。
