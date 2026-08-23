# GOV-V2-STAGE-CLOSURE 验证记录

2026-08-24 提交前验证：

```text
python -m unittest tests.test_pr_governance -v
结果：40 tests，PASS

PYTHONPATH=src python -c "from research_workbench.cli import main; ... main(['validate','examples','registry'])"
结果：validated=59 errors=0 warnings=0
```

治理测试覆盖 authority 路径 R2、四类 published identity 的同版本失败/追加通过、Stage 原子依赖链
通过、依赖或逐 Task 证据缺失失败，以及现有 Governance v2 轻量不变量。仓库完整测试仍由后续集成 PR
与 CI 按标准安装入口执行；本治理补丁不重复制造第二轮本地全测。
