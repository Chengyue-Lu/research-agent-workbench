# GOV-V2-STAGE-CLOSURE 验证记录

2026-08-24 首轮提交前验证：

```text
python -m unittest tests.test_pr_governance -v
结果：40 tests，PASS

PYTHONPATH=src python -c "from research_workbench.cli import main; ... main(['validate','examples','registry'])"
结果：validated=59 errors=0 warnings=0
```

治理测试覆盖 authority 路径 R2、四类 published identity 的同版本失败/追加通过、Stage 原子依赖链
通过、依赖或逐 Task 证据缺失失败，以及现有 Governance v2 轻量不变量。仓库完整测试仍由后续集成 PR
与 CI 按标准安装入口执行；本治理补丁不重复制造第二轮本地全测。

2026-08-24 本轮审计修复 focused 验证：

```text
python -m unittest tests.test_pr_governance -v
结果：59 tests，PASS（新增 19 tests）
```

新增覆盖包括 R2 linear/branching anchor 可达链通过；R1 PARKED 直达、base-DONE 独立 PARKED、
断连 component、缺失 anchor、未声明中间 Task、逐 Task 证据缺失及循环 DAG 失败；四类 published
identity 的 move-out、Action 删除、同 identity 重定位失败，以及保留旧路径追加新版本和无关 archive
文件通过。另有一项集成测试固定：即使 changed path 本身已不匹配 protected policy，PR 检查仍必须
无条件读取并比较 base/head published identity 全集。完整仓库测试、coverage、wheel 与 clean-install
留给本 R2 PR 的标准 CI 执行。

2026-08-24 Research Mode versioned-directory 补漏：

```text
python -m unittest tests.test_pr_governance -v
结果：61 tests，PASS（新增 v0.2 目录识别与 move-out 负面测试）
```

Policy 现同时覆盖 `registry/modes/*.yaml` 与 `registry/modes/v*/*.yaml`，并保持 Action、Migration
各自按独立 kind 解释。
