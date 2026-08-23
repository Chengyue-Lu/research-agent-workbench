# M8-005 验证记录

状态：本地 implementation validation 完成；PR #30 CI 待更新 head 后复核。

已建立的正反面：

- Agent Mode proposal、Resolver Action commit、Human permission revision 与 Human Claim promotion 允许；
- Agent Claim commit、Resolver permission commit、缺失 unambiguous fact、缺失 Human Gate 和 cosmetic Gate 阻断；
- Matrix exact decision kind、commit actor 与 commit required facts 闭集；
- Matrix ref/path/raw SHA-256 与 preflight recorded result 可重算；
- duplicate preflight identity 与高风险 commit authority 放宽阻断。

本地结果：

- Decision Authority + Schema + documentation focused：21 tests，全部通过；
- 完整单元测试：317 tests，全部通过，3 项按既有环境条件跳过；
- repository validation：`validated=116 errors=0 warnings=0`；
- Python `compileall`：通过；
- `pip wheel --no-deps --no-build-isolation`：通过；
- `git diff --check`：通过。

本机未安装 `coverage` 与 `build` 模块，没有为本节点在线安装或修改系统环境。Python 3.11/3.13、
coverage、canonical `python -m build --wheel` 与 clean-install smoke 由更新后的 PR #30 CI 复核。
