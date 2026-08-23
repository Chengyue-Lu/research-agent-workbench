# Commands

命令均从仓库根目录执行；生成物路径省略机器绝对前缀，并统一位于本 Attempt 的 `raw/`。

```text
python -m unittest discover -s tests -v
python -m coverage run --data-file=raw/coverage/.coverage -m unittest discover -s tests
python -m coverage report --data-file=raw/coverage/.coverage --fail-under=80
python -m coverage json --data-file=raw/coverage/.coverage -o raw/coverage/coverage.json
python -m research_workbench validate examples registry
git archive --format=zip --output=raw/build-source/source.zip HEAD
<build-python> -m build --wheel --no-isolation --outdir raw/wheel
<isolated-python> -m pip install <wheel>[test]
<isolated-python> -m unittest discover -s tests
<isolated-rwb> schema list
<isolated-rwb> validate examples registry
python -m pytest tests/test_documentation.py -q -p no:cacheprovider
python validation/verify_tracked_evidence.py
git diff --cached --check
```

实际执行参数、退出码和例外均以 `RESULTS.md` 为准。主环境没有注册 `coverage`、`rwb`
可执行入口且没有 `build` 模块，因此分别改用模块入口，或在 ignored 一次性环境安装项目
声明的构建/测试依赖。完整日志若保存，只能进入 ignored `raw/logs/`，不得将机器路径、
环境变量值或凭据写入已跟踪文件。
