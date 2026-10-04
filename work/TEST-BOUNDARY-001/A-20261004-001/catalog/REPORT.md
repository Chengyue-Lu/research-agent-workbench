# Catalog development-input boundary implementation

基于 `ede2bc1d5e3496b4e4c72abb1f39f0a3ce00aedf`，仅修改 `tests/test_catalog.py`。删除四个只固定开发 intake/archive 语料数量、hash pins 与决策名单的方法：

- `test_community_intake_has_one_decision_per_selected_skill`
- `test_first_party_intake_has_pinned_non_executable_decisions`
- `test_new_archive_candidates_have_explicit_non_executable_decisions`
- `test_user_archive_has_one_pinned_candidate_per_skill_entrypoint`

保留两个产品 API 方法及原方法名。`setUp` 每次创建独立 `TemporaryDirectory`；fixture 写真实 JSON 文件，经 `load_candidates → load_document → load_document_bytes → json.loads` 读取。loader 不引用 candidate schema，只要求 Mapping、`registry_kind="skill_candidates"` 和 candidates list；未模拟 loader 或直接把手工 catalog 交给 filter。

- quarantine 方法：2 条最小记录，分别为 quarantine/trial。两个真实 status filter 各返回正确记录，并断言输入 metadata 原样保持，保护 quarantine 不进入 trial 结果的行为。
- mode 方法：3 条记录，分别为匹配 mode+capability、错误 mode、错误 capability。仅匹配记录返回；其 quarantine 状态与所有输入 metadata 均不改变。选中记录引用不存在的 SKILL 路径，filter 成功且路径仍不存在，保护 metadata 过滤无需加载或安装 Skill 的边界。

这些断言针对本模块的候选 metadata API；不把 catalog filter 结果解释为 AcceptedSkillRegistry 的 runtime admission。M5/Provider 执行、状态、deadline、guard 代码没有修改。

指定 root 环境 Python 3.11.16，`-B -X utf8` 与 `PYTHONPATH=WT/src;WT;WT/tests`，仅两个保留方法各运行一次：2 PASS，0 FAIL/ERROR/SKIP，真实 testcase 总时间 0.006796700s（含 setUp/cleanup，无 coverage）。原始 `native.log`、`result.json` 和 `command.ps1` 已保存。没有 baseline timing 或性能提升主张。

独立文件读取观察器记录两条真实 parser 输入：2 records/168 bytes 与 3 records/456 bytes，两个不同的 WT 外临时目录，测试后均已清理。观察器禁止读取 WT 的 `registry/skills/candidates.json`；两例通过，确认开发 record-input 隔离。观察器额外读取原始字节计算独立 hash，不替换、修改 parser 或 fixture。

候选 loader 与 IO 的前后 SHA-256 相等。当前 release policy 1.7.0 的 include 未选中开发 candidates.json；此次没有修改 release policy 或扩展发布面。`git diff --check -- tests/test_catalog.py` 通过。完整差异保存在 `test_catalog.diff`，原始测试源保存在 `test_catalog.before.py`。

测试源 SHA-256：

- before: `6d3d46d7cd08468e2dc723cf1e9369478676b92776fead7cbd0f05d3a513ecf4`
- after: `0da0ccc8c0ce9474c4f5ed22d445beb5918c589b6253defc6e204411c5a2beab`

方法 body/source 输入绑定、原始证据 hash、移除名单见 `before.json`、`result.json` 与 `implementation.json`。未运行全局测试、CI、安装、网络/API；未 stage/commit/push。
