# Results

状态：`PASS_LOCAL_WITH_MATRIX_PENDING`

## 本地通过

- 主环境 Python 3.12.4：237 项通过，3 项因未安装 Hypothesis 按既有条件跳过；退出码 0；
- 主环境覆盖率回归：237 项通过、3 项跳过；总覆盖率 `83.2174%`，门禁 `>=80%`；
- Trace 模块覆盖率 `92.9577%`，门禁 `>=90%`；
- 模块入口验证 Registry/Schema 示例：`validated=59 errors=0 warnings=0`；
- 从 `HEAD@b1d5a5a` 的归档快照构建 `research_agent_workbench-0.1.0-py3-none-any.whl`；
- wheel clean install 后列出 24 个 Schema，并再次得到 `validated=59 errors=0 warnings=0`；
- Python 3.12.13 独立环境安装 wheel 的完整 `test` extra 后：237 项全部通过、无跳过；
- wheel、源码 ZIP、覆盖率数据库及 JSON 均保存在 ignored `raw/`，并由 `HASHES.sha256` 绑定；
- 一次性源码展开目录和虚拟环境在解析确认均位于本 Attempt 后删除。

## 环境差异

- 主环境存在 `coverage` 模块但没有同名可执行入口，使用 `python -m coverage`；
- 主环境没有注册 `rwb` 入口，使用 `python -m research_workbench`；
- 主环境没有 `build` 模块；构建工具和声明依赖只安装在 ignored 一次性虚拟环境；
- 上述差异不改变测试断言，但必须保留，不能把首次入口失败隐藏为成功。

## 尚待远端门禁

- 本机没有可执行的 Python 3.11/3.13，因此这两个版本只能由目标 PR 的 GitHub Actions 验证；
- PR #25 尚未合入 `develop`，本工作流不得绕过其跨 owner 审查而发布；
- 在 PR #25 合入并 rebase 后，应重新运行远端矩阵和治理检查。
