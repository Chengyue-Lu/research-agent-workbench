# Commands

命令从 rebase 后的仓库根目录执行；生成物统一写入本 Attempt 的 ignored `raw/`。

```text
python .github/scripts/check_pr_governance.py
<test-python> -m unittest discover -s tests
<test-python> -m coverage run --data-file=raw/coverage/.coverage -m unittest discover -s tests
<test-python> -m coverage report --data-file=raw/coverage/.coverage --fail-under=80
<test-python> -m coverage json --data-file=raw/coverage/.coverage -o raw/coverage/coverage.json
<test-rwb> validate examples registry
git archive --format=zip --output=raw/build-source/source.zip HEAD
<build-python> -m build --wheel --no-isolation --outdir raw/wheel
<smoke-python> -m pip install <wheel>
<smoke-rwb> schema list
<smoke-rwb> validate examples registry
python -B -m pytest tests/test_documentation.py -q -p no:cacheprovider
python -B validation/verify_tracked_evidence.py
git diff --check
```

本地直接运行治理脚本只覆盖 push/non-PR 分支；真实 PR payload、base、标签和正文由目标 PR
的 GitHub Actions 验证。治理单元测试仍属于完整 unittest 集合。单文件复核须使用
`unittest discover -s tests -p test_pr_governance.py`；直接导入 `tests.test_pr_governance`
会在本机被无关的第三方顶层 `tests` 包遮蔽。
