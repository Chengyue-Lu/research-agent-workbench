# M4 风险台账

状态：Stage PR 提交前更新。每项记录触发条件、缓解与当前判定。

| # | 风险 | 触发条件 | 缓解 | 判定 |
|---|---|---|---|---|
| R-1 | M4-003 越权改 Claim 语义 | 修改 `claim*.schema.json` 或新增 Evidence–Claim 关系词表 | 实现仅消费既有三字段；未触碰 claim schema；新关系语义明确留给 Phase C（契约文档 §1） | 守住 |
| R-2 | 与 Phase C 实现分支（Issue #38）在 `kernel/objects.py`、`validation/relationships.py`、`cli.py` 产生合并冲突 | Phase C 分支与 M4 并行开发相同文件 | M4 未改 `kernel/objects.py`；`documents.py`/`cli.py` 为增量分支；实测：`content_hash` 语义澄清为对象 pin 而非文件字节，避免 Phase C 语义冲突；提交后与路诚钺同步分支计划 | 缓解，收尾监控 |
| R-3 | 伪造 no-Skill 伪装 | Run manifest 强制 `skill_assignment_ref` 或生成空 Assignment | 字段可选并注释明示；空字符串被 schema 拒绝（负面测试锁定） | 守住 |
| R-4 | fixture 被误当真实供给/运行数据 | examples fixture 声明 availability 或 execution 资格 | fixture 仅结构样例（metadata.fixture=true、not_scientific_evidence）；不进入 registry/ | 守住 |
| R-5 | coverage 回退（CI 门槛 80%） | 新增 validator/CLI 无对应测试 | 每个 feature 均有专项测试文件；实测 TOTAL 83%、trace 92.96% | 守住 |
| R-6 | promotion 语义越权（绕过校验直接登记/覆盖 accepted） | promotion API/CLI 接受未验证来源或原地覆盖 | execute 前 fail-closed 全量检查；OVERWRITE/NEGATIVE-DROPPED/BYPASS 负面测试锁定 | 守住 |
| R-7 | inbox 引用绕过（相对路径/`..`/符号链接逃逸） | 引用路径解析逃出 root 或落 inbox | `relativePath` schema 约束 + `resolve_within_root` 复核 + 全局 inbox 分区阻断 + 负面 fixture | 守住 |
| R-8 | TASKS.md 误改定义列 | 编辑滑出状态单元格 | 仅 `edit` 状态单元格；`git diff` 逐行核对确认只有 4 个状态单元格变化 | 守住 |
| R-9 | artifacts 包循环导入（实测发生并修复） | `artifacts/__init__` 重导出 promotion→validation→capability→artifacts 回环 | `__init__` 保持轻量；promotion 对 validation 依赖改惰性导入；回归测试通过 | 已修复 |
| R-10 | 分区前缀锚定导致仓库内 fixture 永远失败 | `sources/raw/` 等按绝对前缀校验 | 分区段语义（`(^|/)zone/`），项目相对与仓库相对路径均成立 | 已修复 |
