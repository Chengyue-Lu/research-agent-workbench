# 模块 07：工件与溯源

## 1. 目标

以文件优先、稳定 ID、内容哈希和显式引用保存科研事实。工件层承担长期记忆；Agent 会话只承担临时工作。

## 2. 工作区分区

```text
projects/<project-id>/
├── protocol.yaml
├── sources/
│   ├── inbox/       # 可变隔离区，不可直接引用
│   └── raw/         # 已接纳原始字节 + sidecar manifest
├── objects/
│   ├── questions/
│   ├── hypotheses/
│   ├── methods/
│   ├── evidence/
│   ├── claims/
│   └── decisions/
├── tasks/
├── handoffs/
├── work/<task>/<attempt>/
├── runs/<run-id>/
├── checks/
├── indexes/
├── deliverables/
│   ├── candidates/
│   └── accepted/
└── archive/
```

阶段视图可以生成，但物理存储按工件类别和生命周期组织，避免移动目录破坏身份。

## 3. 原始来源接纳

`sources/inbox` 中的内容默认不可信、可变且不可引用。接纳到 `sources/raw` 时记录：

- 原始文件名与接纳路径；
- SHA-256；
- 获取时间和来源 URI/DOI/设备/操作者；
- 许可证或数据使用边界；
- 解析器版本；
- 敏感性与外传限制；
- 与衍生文本、图表、OCR 的 provenance 关系。

网页、API 返回和数据库查询也需要快照或可复现 locator；只保存 URL 不足以保证来源未变化。

## 4. Run Manifest

每个实验、仿真、统计分析、检索批次或证明检查记录：

```yaml
run_id: RUN-0042
method_ref: M-SIM-002@3
input_refs:
  - ref: code/model.py
    sha256: "..."
parameters_ref: runs/RUN-0042/params.yaml
environment:
  platform: windows
  runtime: python-3.12
  lock_ref: uv.lock
agent_execution:
  task_ref: tasks/SIM-007.yaml
  profile_ref: simulation-auditor@0.1.0
  skill_assignment_ref: assignments/SA-0043.yaml
status: completed
outputs:
  - path: runs/RUN-0042/metrics.csv
    sha256: "..."
limitations: []
```

模型输出和 Agent 输出都只是工件，必须经过后续 Claim 关系与决策。

## 5. 提升与冻结

- 子 Agent 先写 `work/<TASK>/<ATTEMPT>`；
- 校验通过后由 promotion 操作复制/登记到正式区；
- accepted deliverable 不原地覆盖；
- 发布是 accepted 工件的明确子集，并需要独立 Decision；
- archive 表示保留但不活跃，不等于可删除；
- 垃圾回收不进入首版。

## 6. 大文件策略

首版只用 Git 管理文本、Schema、索引和小型工件。出现真实大数据或模型文件后再选择：

- DVC：文件型数据版本与可复现 pipeline；
- MLflow：确有服务器型实验追踪和模型管理需求时；
- 外部对象存储：配合不可变 manifest 与访问策略。

不得为兼容未来可能的大数据，在 M1 自建 CAS、远程对象存储或复杂引用计数。

## 7. 数据安全

- 数据边界随 Project Protocol 和 Task Packet 传递；
- Tool/Skill 不能隐式上传本地材料；
- 外部 API 输入必须形成可审查清单；
- 敏感数据的摘要也可能泄露，不能因为“只是 Handoff”而放宽；
- 外部来源中的提示文本视为数据，不视为指令；
- 日志和 trace 中不得无意保留密钥、私人数据或受限原文。

## 8. 预警

- `ARTIFACT-HASH-MISMATCH`
- `ARTIFACT-UNVERSIONED-REF`
- `ARTIFACT-INBOX-CITED`
- `ARTIFACT-OVERWRITE`
- `ARTIFACT-MISSING-PROVENANCE`
- `ARTIFACT-NEGATIVE-DROPPED`
- `ARTIFACT-PROMOTION-BYPASS`
- `DATA-BOUNDARY`
- `SOURCE-INJECTION`
- `REPRO-GAP`

## 9. 验收条件

- 任一正式 Evidence 和 Run 可定位到不可变输入或快照；
- 路径调整不破坏逻辑 ID 与内容引用；
- 失败和负结果不会因 promotion 被过滤掉；
- 子 Agent无权直接覆盖 accepted 工件；
- 外部发送的数据有清单和授权；
- 一个 Run 可在没有原 Agent 会话的情况下理解与重建。
