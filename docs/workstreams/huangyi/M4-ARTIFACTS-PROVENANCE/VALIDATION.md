# M4-001 验证证据

状态：PR #39 review 整改后；基线 `develop@2b3362a`。

## Task 级证据

- Schema：`schemas/v0.1.0/source-admission.schema.json`；
- 实现：`src/research_workbench/artifacts/admission.py`；
- CLI：`rwb source admit|check`，执行模式拒绝覆盖 bytes/sidecar；
- repository gate：`rwb validate` 对已提取引用执行 inbox 阻断；
- fixture：`examples/artifacts/sources/{inbox,raw}`，raw sidecar exact hash 闭合；
- 负面用例：inbox、`raw-copy`/`inbox-old` 路径边界、hash drift、origin/time 缺失、
  derivative drift、路径 escape。

## 复跑记录

| 项 | 命令 | 结果 |
|---|---|---|
| M4-001 专项 | `PYTHONPATH=src python -m unittest discover -s tests -p test_artifacts_admission.py` | 14 passed |
| Schema 目录 | `PYTHONPATH=src python -m unittest discover -s tests -p test_schemas.py` | 3 passed |
| 全量回归 | `PYTHONPATH=src python -m unittest discover -s tests` | 446 passed, 3 skipped |
| 仓库校验 | `PYTHONPATH=src python -m research_workbench validate examples registry --root .` | validated=155, errors=0, warnings=0 |
