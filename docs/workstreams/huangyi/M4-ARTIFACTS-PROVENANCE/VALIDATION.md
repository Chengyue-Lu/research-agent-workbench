# M4-001 验证证据

状态：PR #39 第二轮 review 整改后；latest-base `develop@aa4e7eed`。

## Task 级证据

- Schema：`schemas/v0.1.0/source-admission.schema.json`；
- 实现：`src/research_workbench/artifacts/admission.py`；
- CLI：`rwb source admit|check`，执行模式拒绝覆盖 bytes/sidecar；
- repository gate：`rwb validate` 对已提取引用执行 inbox 阻断，并要求每个普通文档的完整
  `sources/raw` 引用绑定同路径有效 admission sidecar、精确 admitted path 与 live-byte SHA；
- fixture：`examples/artifacts/sources/{inbox,raw}`，raw sidecar exact hash 闭合；
- 负面用例：inbox、`raw-copy`/`inbox-old` 路径边界、hash drift、origin/time 缺失、
  derivative drift、路径 escape；raw citation 另覆盖 sidecar 缺失、Schema 无效、wrong admitted path、
  admission/live-byte drift、FileReference/admission SHA 不一致，并保留 valid exact-sidecar 正例。

## 复跑记录

| 项 | 命令 | 结果 |
|---|---|---|
| M4-001 专项 | `PYTHONPATH=src python -m unittest discover -s tests -p test_artifacts_admission.py` | 20 passed |
| Schema 目录 | `PYTHONPATH=src python -m unittest discover -s tests -p test_schemas.py` | 3 passed |
| 全量 coverage 回归（独立 `[test]` 环境） | `python -m coverage run -m unittest discover -s tests` | 495 passed |
| Coverage Gates | `python -m coverage report --fail-under=80` + Trace exact file check | total=83%；Trace=92.87% |
| 仓库校验 | `PYTHONPATH=src python -m research_workbench validate examples registry --root .` | validated=155, errors=0, warnings=0 |
