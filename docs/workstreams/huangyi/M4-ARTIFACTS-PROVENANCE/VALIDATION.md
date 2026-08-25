# M4 验证证据

状态：Stage PR 提交前记录（分支 `agent/m4-artifacts-provenance`，基线 `develop@4ce83bc`）。

## 全局验证

| 项 | 命令 | 结果 |
|---|---|---|
| 基线全量测试（实现前） | `py -3.11 -m unittest discover -s tests` | 432 passed（develop@4ce83bc，2026-08-25） |
| 全量测试（实现后） | `py -3.11 -m unittest discover -s tests` | 468 passed, 0 failed（新增 36 项 M4 测试） |
| 覆盖率 | `py -3.11 -m coverage run -m unittest discover -s tests && coverage report --fail-under=80` | TOTAL 83%（门槛 80%） |
| Trace 模块覆盖率（CI 专项） | `coverage json` + trace.py 百分比 | 92.96%（门槛 90%） |
| 仓库校验 | `py -3.11 -m research_workbench validate examples registry` | validated=159 errors=0 warnings=0（基线 124，新增 fixture 文档全部通过） |
| 仓库校验（仅新 fixture） | `py -3.11 -m research_workbench validate examples\artifacts --root .` | validated=5 errors=0 warnings=0 |
| 文档测试 | 随全量 `test_documentation.py` | 通过（内部链接与表面边界） |

注：本地仅 Python 3.11；3.13 矩阵由远端 CI 验证。wheel 构建与干净安装 smoke 由远端 CI
同流程覆盖。

## 任务级证据

### M4-001 source admission 与 provenance

- Schema：`schemas/v0.1.0/source-admission.schema.json`（origin 至少一 locator、显式
  `acquired_at`、分区段 `sources/raw/` 约束）；
- 实现：`src/research_workbench/artifacts/admission.py`；CLI `rwb source admit|check`；
  `rwb validate` 对全部文档类型执行 inbox 引用全局阻断（`ARTIFACT-INBOX-CITED`）；
- fixture：`examples/artifacts/sources/`（inbox 隔离 + raw sidecar）；
- 负面测试：inbox 路径引用、哈希漂移、origin 缺失、时间戳不可解析、derivative 漂移、
  构造器拒绝 inbox 目标/隐式时间戳/无定位来源（`tests/test_artifacts_admission.py`，11 项）。

### M4-002 work → object/run promotion

- Schema：`schemas/v0.1.0/promotion-record.schema.json`（disposition 条件required、
  retained/负结果必须 reason、target 分区约束）；
- 实现：`src/research_workbench/artifacts/promotion.py`；CLI `rwb promotion validate|execute`
  （execute fail-closed，先全量检查后复制）；
- fixture：`examples/artifacts/work/SIM-001/A-001/`（含负结果工件）+ `promotions/PR-SIM-001-A-001.yaml`
  （promoted + retained-in-work 负结果 entry 的完整决策）；
- 负面测试：非 pass 报告、workspace 越界、受检工件缺失（NEGATIVE-DROPPED）、目标已存在、
  target 分区非法、工件哈希漂移、schema 强制 reason、重复执行拒绝
  （`tests/test_artifacts_promotion.py`，10 项）。

### M4-003 Claim trace 与 counterevidence

- CLI：`rwb claim trace <claim> --root --objects [--protocol]` 单视图输出支持/反证/限制，
  每条引用解析 `object_id`/`revision`/仓库相对 `path`/`status`；
- 语义边界：不修改 `claim*.schema.json`；`content_hash` 按 kernel 语义作为对象内容 pin
  （与引用级 sha256 比对），不比对对象文件字节；新关系语义留给 Phase C；
- 负面测试：对象缺失（REF-MISSING）、引用缺 revision（ARTIFACT-UNVERSIONED-REF 警告）、
  ref pin 与对象 pin 不一致（ARTIFACT-HASH-MISMATCH）、匹配 pin 通过
  （`tests/test_claim_trace_localization.py`，5 项）；
- 既有示例回归：`examples/objects/claim/CLAIM-EVID-001-BOUNDARY.yaml` 定位 ok。

### M4-004 Run manifest 与复现检查

- Schema：`schemas/v0.1.0/run-manifest.schema.json`（`skill_assignment_ref` 可选，注释明示
  no-Skill 省略而非伪造）；
- 实现：`src/research_workbench/artifacts/repro.py`；CLI `rwb repro check [--rerun-dir]`；
- fixture：`examples/artifacts/runs/RUN-SIM-001/`（model.py + params + 环境 lock + 输出，
  均哈希钉定；`examples/artifacts/tasks/SIM-001.yaml` 为 task_ref 目标）；
- 确定性重建：`model.py` 的 `channel_means` 对 admitted fixture 字节重算输出与
  `outputs/channel-means.csv` 逐字节一致（rerun 比对通过）；
- 负面测试：输入哈希漂移、环境锁缺失（REPRO-GAP）、incomplete 状态警告、rerun 输出
  漂移（BLOCK）、rerun 输出缺失（BLOCK）、伪造空 assignment 字段被 schema 拒绝、
  no-Skill 路径一等成立（`tests/test_artifacts_repro.py`，10 项）。

## 风险码

`ARTIFACT-HASH-MISMATCH`、`ARTIFACT-UNVERSIONED-REF`、`ARTIFACT-INBOX-CITED`、
`ARTIFACT-OVERWRITE`、`ARTIFACT-MISSING-PROVENANCE`、`ARTIFACT-NEGATIVE-DROPPED`、
`ARTIFACT-PROMOTION-BYPASS`、`REPRO-GAP` 已注册于 `contracts/risk_codes.py`
`ARTIFACT_RISK_CODE_REGISTRY`；模块 07 §9 的 `DATA-BOUNDARY`/`SOURCE-INJECTION`
不在 M4 范围（记录于契约文档 §7）。
