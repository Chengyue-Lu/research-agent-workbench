# M8-004 验证记录

状态：本地 stacked implementation 验证完成；正式 PR/CI 待依赖落地。

## 已完成

- 聚焦 migration/Mode Action/Method Resolution：30 tests，全部通过；
- 完整单元测试：308 tests，全部通过，3 项按既有环境条件跳过；
- repository validation：`validated=106 errors=0 warnings=0`；
- Python `compileall`：通过；
- wheel：`pip wheel --no-deps --no-build-isolation` 构建成功；
- `git diff --check`：通过。

正反覆盖包括：

- v0.1 与 v0.2 Research Mode 同时可验证，未知版本和混用字段 fail closed；
- deterministic target 与两个 checked-in migration record 一致；
- source/target Mode 和两代 Action 的 raw-byte SHA-256、路径、ref 与 Registry 闭合；
- migration/implementation version、字段清单、Action 映射重复/遗漏/漂移均阻断；
- 旧 v0.1 Mode、Action 与八个历史 Method Resolution 继续显式解析；
- v0.2 不携带 Skill recommendation，也不产生 Tool/Skill/Provider/Runtime binding。

## 尚待正式 PR CI

当前本机 Python 环境未安装 `coverage` 与 `build` 模块，因此没有为本任务在线安装或改变系统环境。
wheel 已通过现有 `pip/setuptools` 路径构建；以下项目保留到依赖 PR #30 合并、分支重建并创建正式 PR 后
由既有 CI 执行：

- Python 3.11 / 3.13 matrix；
- coverage 总阈值与 Trace module 阈值；
- CI 的 `python -m build --wheel`；
- 隔离 venv 的 declared-dependency clean-install smoke。

上述待办是合并验证，不否定当前本地实现；在它们通过前不得宣告 M8-004 已进入共享基线。
