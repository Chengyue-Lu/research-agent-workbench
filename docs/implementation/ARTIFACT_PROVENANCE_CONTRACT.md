# Artifact Provenance Contract (M4)

状态：Active implementation contract（M4-001..004）

更新：2026-08-25

## 1. 目的与边界

本契约把[模块 07：工件与溯源](../modules/07-ARTIFACTS_AND_PROVENANCE.md)中 M4 范围内的四条
确定性规则实现为可验证契约：source admission、work → object/run promotion、Claim trace
一次定位、Run manifest 复现检查。

本契约只证明结构、引用与哈希闭合，不证明科学正确性、来源可信或机制净收益。
M4-003 不修改 `claim*.schema.json`、不新增 Evidence–Claim 关系语义；Evidence–Claim
关系扩展属于 Phase C（Issue #38）。M4-004 的 `skill_assignment_ref` 是可选的 legacy
兼容字段，no-Skill 路径直接省略该字段，不得伪造空 Skill Assignment。

## 2. 路径分区语义

`sources/inbox/`、`sources/raw/`、`work/`、`objects/`、`runs/`、`deliverables/` 是
**分区段**（path zone）而非绝对前缀：仓库相对路径（如示例中的
`examples/artifacts/sources/raw/...`）与项目相对路径（`sources/raw/...`）同样接受。
分区判定为 `path == zone 或 path 以 zone 开头，或 zone 作为完整路径段出现`。

`sources/inbox/` 引用是全局阻断项：任何被校验文档的 file 引用或路径引用落到 inbox
分区时，`rwb validate` 与各专项命令都发出 `ARTIFACT-INBOX-CITED`（BLOCK）。

## 3. source admission（M4-001）

Schema：`schemas/v0.1.0/source-admission.schema.json`（document kind
`source_admission`）。

- Sidecar 记录：`admission_id`、`original_filename`、`admitted_path`（必须落在
  `sources/raw/` 分区）、字节 `sha256`、`acquisition`（origin 至少含 uri/doi/device
  之一、显式 `acquired_at`、具名 `operator`）、`license_or_data_use`、`parser`
  （name/version）、`sensitivity`、`egress_restriction`、可选 `derivatives`
  （path/sha256/relation）；
- `rwb source admit` 生成确定性 sidecar（无隐式时间戳，`--acquired-at` 必填）；
  默认 dry-run，`--execute` 才复制字节并写入 sidecar，拒绝覆盖已存在目标；
- `rwb source check` 与 `rwb validate` 校验：字节哈希一致
  （`ARTIFACT-HASH-MISMATCH`）、provenance 完整（`ARTIFACT-MISSING-PROVENANCE`）、
  不引用 inbox（`ARTIFACT-INBOX-CITED`）；
- 网页/API/数据库来源的"快照或可复现 locator"由 origin 定位字段 + derivatives
  承载；本契约不抓取网页。

## 4. promotion（M4-002）

Schema：`schemas/v0.1.0/promotion-record.schema.json`（document kind
`promotion_record`）。

- Promotion record 声明 `source_workspace`（`work/` 分区）、`validation_report`
  （必须是 schema-valid 且 `status: pass` 的 `deterministic_check_report`）、
  具名 `decided_by`/`decided_at`，以及覆盖全部受检工件的 `entries`；
- 每个 entry 声明 `artifact`（fileRef）、`disposition`（`promoted` /
  `retained-in-work`）、`negative_result` 与（保留或负结果时的）`reason`；
  `promoted` 必须给出落在 `objects/`、`runs/`、`deliverables/` 分区的 `target`；
- 阻断项：`ARTIFACT-PROMOTION-BYPASS`（报告缺失/失败/非确定性报告/工件越出
  workspace/target 分区非法）、`ARTIFACT-OVERWRITE`（目标已存在或重复目标）、
  `ARTIFACT-NEGATIVE-DROPPED`（受检工件未出现在任何 entry——负结果不得因
  promotion 被过滤）、`ARTIFACT-HASH-MISMATCH`（工件字节漂移）；
- `rwb promotion validate` 只校验；`rwb promotion execute` 在无 BLOCK 风险时才
  复制字节，fail-closed。

## 5. Claim trace 一次定位（M4-003）

`rwb claim trace <claim> [--root R] [--objects DIR] [--protocol P]`：

- 索引 `--objects`（默认 `--root`）下的 research object，按 `object_id` + `revision`
  解析 claim 的 `support_refs` 与 `counterevidence_refs`；
- 输出单视图 JSON：每条支持/反证引用的 `object_id`、解析出的 `revision`、
  仓库相对 `path` 与 `status`，连同 `limitations` 一次给出；
- 风险：`REF-MISSING`（对象不存在）、`ARTIFACT-UNVERSIONED-REF`（引用缺
  revision，按最新版解析并警告）、`ARTIFACT-HASH-MISMATCH`（引用级 sha256 pin
  与对象自身 `content_hash` 声明不一致）；
- `content_hash` 语义沿用 kernel：它是对象内容 pin（进入 `ObjectRef.sha256`），
  不定义为对象文件字节的 hash；本命令不做文件字节比对。

## 6. Run manifest 与复现（M4-004）

Schema：`schemas/v0.1.0/run-manifest.schema.json`（document kind `run_manifest`）。

- 必填：`run_id`、`method_ref`（objectRef）、`input_refs`（fileRef≥1）、
  `parameters_ref`、`environment`（platform/runtime/lock_ref）、`agent_execution`
  （`task_ref`、`profile_ref`，可选 `skill_assignment_ref`）、`status`、`outputs`；
- `rwb repro check [--rerun-dir D]`：输入/参数/锁/任务/输出存在性与哈希校验；
  `--rerun-dir` 对每个输出按文件名做字节级比对（确定性重建检查）；
- 风险：`REPRO-GAP`（缺失输入/锁/输出、未完成 status 的警告、rerun 未复现
  输出）、`ARTIFACT-HASH-MISMATCH`（输入/输出漂移、rerun 与记录不一致）、
  `REF-MISSING`/`REF-OUTSIDE-ROOT`（任务或赋值引用失效）；
- "无原 Agent 会话可理解重建"的机器可测子集 = 输入/参数/环境/任务/输出全部
  hash 闭合 + rerun 字节比对；语义可理解性不由本契约断言。

## 7. 风险码归属

`ARTIFACT-HASH-MISMATCH`、`ARTIFACT-UNVERSIONED-REF`、`ARTIFACT-INBOX-CITED`、
`ARTIFACT-OVERWRITE`、`ARTIFACT-MISSING-PROVENANCE`、`ARTIFACT-NEGATIVE-DROPPED`、
`ARTIFACT-PROMOTION-BYPASS`、`REPRO-GAP` 定义于
`src/research_workbench/contracts/risk_codes.py` 的
`ARTIFACT_RISK_CODE_REGISTRY`，只表达工件层确定性事实，不判科学有效性。

模块 07 §9 的 `DATA-BOUNDARY`、`SOURCE-INJECTION` 不在本契约范围：前者属于数据
治理平面，后者需要来源内容扫描，均留待相应 Task。

## 8. 示例与测试

- 示例：`examples/artifacts/`（inbox 隔离、raw sidecar、work 输出与负结果、
  确定性检查报告、promotion record、run manifest 与冻结环境/参数）；
- 测试：`tests/test_artifacts_admission.py`、`tests/test_artifacts_promotion.py`、
  `tests/test_artifacts_repro.py`、`tests/test_claim_trace_localization.py`，
  含 inbox 引用、伪造提升、负结果丢弃、哈希漂移、rerun 漂移等对抗用例。
