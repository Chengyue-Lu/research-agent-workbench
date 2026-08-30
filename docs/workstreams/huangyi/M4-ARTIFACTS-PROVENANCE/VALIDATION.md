# M4-001 验证证据

状态：PR #39 基于 PR #44 / TEST-QUALITY-001 后的 latest `develop` 完成语义 rebase；hosted
exact-HEAD 证据在推送后回填。

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
| M4-001 专项 | `PYTHONPATH=src python -m unittest discover -s tests -p test_artifacts_admission.py` | 26 passed（含 raw-reference 与 producer critical 分支） |
| Schema 目录 | `PYTHONPATH=src python -m unittest discover -s tests -p test_schemas.py` | 3 passed |
| Coverage Policy | `artifacts/admission.py` 纳入 critical inventory；valid exact-sidecar 与五类 fail-closed 用例作为独立正反 evidence | 待 exact-HEAD hosted run |
| 双 Python full suite / coverage-quality | 仓库 authoritative CI topology | 待 exact-HEAD hosted run |
| 仓库校验 / package-smoke / governance | 仓库 authoritative CI topology | 待 exact-HEAD hosted run |
