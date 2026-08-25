# M4 风险台账

状态：随实现更新。每项记录触发条件、缓解与当前判定。

| # | 风险 | 触发条件 | 缓解 | 判定 |
|---|---|---|---|---|
| R-1 | M4-003 越权改 Claim 语义 | 修改 `claim*.schema.json` 或新增 Evidence–Claim 关系词表 | 实现仅消费既有三字段；触碰 schema 即停止并转交路诚钺（Phase C 权属） | 守住 |
| R-2 | 与 Phase C 实现分支（Issue #38）在 `kernel/objects.py`、`validation/relationships.py`、`cli.py` 产生合并冲突 | Phase C 分支与 M4 并行开发相同文件 | M4-004 用新 document 类型（run-manifest）而非重写 kernel `Run`；M4-003 只在 relationships.py 增量扩展；提交前与路诚钺同步分支计划 | 开放，监控中 |
| R-3 | 伪造 no-Skill 伪装 | Run manifest 强制 `skill_assignment_ref` 或生成空 Assignment | 字段可选；省略即合法；负面测试锁定 | 守住 |
| R-4 | fixture 被误当真实供给/运行数据 | examples fixture 声明 availability 或 execution 资格 | fixture 仅结构样例；文档标注；不进入 registry/ | 守住 |
| R-5 | coverage 回退（CI 门槛 80%） | 新增 validator/CLI 无对应测试 | 每个语义 commit 本地跑全量 + coverage | 监控中 |
| R-6 | promotion 语义越权（绕过校验直接登记/覆盖 accepted） | promotion API/CLI 接受未验证来源或原地覆盖 | `ARTIFACT-PROMOTION-BYPASS`、`ARTIFACT-OVERWRITE` fail-closed；负结果保留检查 | 守住 |
| R-7 | inbox 引用绕过（相对路径/`..`/符号链接逃逸） | 引用路径解析逃出 root 或落 inbox | `relativePath` schema 约束 + `resolve_within_root` 复核 + `ARTIFACT-INBOX-CITED` 负面 fixture | 守住 |
| R-8 | TASKS.md 误改定义列 | 编辑滑出状态单元格 | 仅 `edit` 状态单元格；提交前 `git diff` 逐行核对 TASKS.md | 守住 |
