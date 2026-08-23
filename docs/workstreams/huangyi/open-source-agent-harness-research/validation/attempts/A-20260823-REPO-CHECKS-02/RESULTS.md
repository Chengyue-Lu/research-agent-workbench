# Results

状态：`PASS_LOCAL_WITH_MATRIX_PENDING`

## 本地通过

- Python 3.12.13 完整 test-extra 环境：264 项全部通过、无跳过，耗时 166.147 秒；
- PR #25 的治理单元测试：24 项通过；治理脚本非 PR 本地入口显式跳过 PR-only 检查；
- 文档测试：9 项通过；
- 总覆盖率 `83.2174%`，门禁 `>=80%`；Trace 覆盖率 `92.9577%`，门禁 `>=90%`；
- Registry/Schema 示例：`validated=59 errors=0 warnings=0`；
- `HEAD@933fdc9` 源码快照成功构建 171646 字节的 universal wheel；
- wheel clean install 后列出 24 个 Schema，并再次验证 59 个对象、0 错误、0 警告；
- Codex tracked evidence file-only verification 与 PowerShell 探针语法解析通过；
- 原始稿、Schema、stdout/stderr、覆盖率、wheel 和源码 ZIP 的 ignore 规则生效；
- 一次性源码展开目录和三个虚拟环境经路径核对后删除。

## 验证机制修正

- 首次按模块名运行单个治理测试时，本机第三方顶层 `tests` 包遮蔽仓库目录；改用
  `unittest discover -s tests -p test_pr_governance.py` 后 24 项通过。这是命令解析问题，
  不是项目测试失败；
- rebase 后首次 file-only verification 发现三个 tracked JSON 哈希仍绑定暂存前 CRLF
  工作副本，而 Git 的规范 blob 为 LF。已将 canonical Attempt 05 的三条 tracked hash
  更新为 LF blob SHA-256，公共 fixture 仍与 sanitized 文件逐字一致，复核通过；
- coverage 采集自 clean-installed wheel，因此本地 JSON 路径位于隔离环境；覆盖值符合门禁。
  目标 CI 使用 editable install，并负责复核其精确 `src/.../trace.py` 路径断言。

## 尚待远端门禁

- 本机没有 Python 3.11/3.13；
- 无真实 GitHub `pull_request` event payload，不能在本地证明 PR base、正文、标签和 reviewer；
- 上述两项必须由目标 PR 的 GitHub Actions 与跨 owner review 完成。
