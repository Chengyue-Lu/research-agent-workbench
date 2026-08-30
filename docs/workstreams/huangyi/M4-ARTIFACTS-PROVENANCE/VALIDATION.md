# M4-001 验证证据

状态：PR #39 基于 PR #44 / TEST-QUALITY-001 后的 latest `develop` 完成语义 rebase 与最终
exact-head hosted CI，并以 `e5cca23` 合入 `develop`。code-complete 与 docs evidence 已由同一
authoritative Gate 闭合。

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
| Coverage Policy | `artifacts/admission.py` 纳入 critical inventory；valid exact-sidecar 与五类 fail-closed 用例作为独立正反 evidence | final run `33308110868`: global 91.47%；admission 97.06% line / 95.45% branch；665/665 PASS，无 duplicate canonical test |
| 双 Python full suite | 仓库 authoritative CI topology | final run `33308110868`: Python 3.11 726/726 PASS；Python 3.13 726/726 PASS |
| 仓库校验 / package-smoke / governance / aggregate Gates | 仓库 authoritative CI topology | final run `33308110868`: 全部 PASS；repository validation 由 clean wheel 执行 |
