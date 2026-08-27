# TEST-QUALITY-001 Validation

## Local evidence

```text
python -m py_compile tests/run_unittest_suite.py .github/scripts/check_coverage_policy.py tests/test_coverage_policy.py
python -m unittest tests.test_coverage_policy -v
python tests/run_unittest_suite.py --suite coverage-quality --json-output <temporary> --verbosity 0 --slowest 10
```

- checker adversarial tests：8 PASS；
- dedicated suite classification：327 tests PASS，wall 330.515 秒，p50 0.030 秒，p95 4.958 秒；
- 该分类 run 未启用 coverage instrumentation，仅证明选择与 runner 语义可执行；
- 本机解释器无 coverage module，未安装网络依赖或修改系统环境。

## Required hosted evidence

最终 R2 PR 必须在 Python 3.11 hosted runner 生成 branch-enabled `coverage.json`，并记录：

- global line；
- 每个 critical file 的 line/branch；
- coverage-quality test count/wall/p50/p95/slowest 20；
- Python 3.11/3.13 full suite count/wall/p50/p95/slowest 20；
- governance、package-smoke、repository validation 与 aggregate required Gates；
- 未达到 12–15 分钟时的具名慢测试事实。

在这些证据齐全前，本 workstream 不标记完成。

### Initial hosted baseline — run 33099480345

- governance：7 秒，PASS；package-smoke：17 秒，PASS；
- Python 3.11 full：732 秒，PASS；Python 3.13 full：804 秒，PASS；
- coverage-quality：394 tests，1055 秒，测试本身全部 PASS，policy Gate 按预期 FAIL；
- coverage suite：wall 1036.889 秒，p50 0.013 秒，p95 14.960 秒；
- global line：79.31%；
- 唯一已同时满足 critical line/branch 的首轮文件：`kernel/objects.py`（98.72% / 100%）；
- 两个既有 `test (3.11)` / `test (3.13)` aggregate checks 均因 coverage-quality 失败而失败，证明 Gate
  propagation 生效。

完整逐文件缺口必须从下一 run 保留的 `coverage-quality-evidence` artifact 读取后再补测试；不以降低
90/95/90 阈值或增加宽泛 exclusion 处理。
