# FOLLOWUP-013 检查

2026-10-03；真实 API、凭据操作为零。产品修改仅报告一致性 verifier；未改变 Schema 或报告版本。
`profile_conformance_report.py` SHA256
`daea5554338fc3cee5a8fd7e8b3a3f99859f0b0a0b3d4616f41e31a071e0ccf6`；
新测试 SHA256 `8b8b658519e8cbe34716442a12ed2f1ac7bc10021865232486951b8a974c8737`。

## 集中回归

Python 3.11.16，源码 `PYTHONPATH=src`，既有隔离 test 环境：

- `unittest tests.test_profile_conformance_usage_consistency`：13/13 PASS，467.900 秒。
  genuine fixture 共 11 次 fake HTTP；篡改只冷读，不重新发送。
- `unittest tests.test_profile_conformance_reporting tests.test_profile_conformance_binding
  tests.test_conformance_journal tests.test_conformance_usage_ledger`：79/79 PASS，324.930 秒。
- `unittest tests.test_documentation tests.test_public_surface tests.test_ci_components
  tests.test_ci_component_execution`：45/45 PASS，3.890 秒；覆盖文档链接和新增回归的组件选择。
- 独立审查：最终源码前后 hash 一致；9 组纯 AST helper 检查 PASS。回归作者只做 AST/compile，
  不将其静态交付冒称实际 driver 执行。

截图的 input 9,000,000、四个实际 token 字段与回执不符、响应标记不符、删除已知回执、
累计数各项不符及非法 cache/reasoning 子集均拒绝；writer 在验证失败时不创建文件。
历史失败 Attempt 已知 7 加当前 Attempt 21，累计 28 正常通过；篡改成仅当前 21 被拒绝。
partial input 5/output null 保持未知及预占 132；null 改为 0 被拒绝。
最终 accounting 不可得保留三响应/21 个模拟 tokens，状态 blocked/accounting-failed；旧 1.0 原样回放。

首轮 51 项运行保留 2 FAIL/1 ERROR：启动后又修改了被绑定的源码，导致旧归档的两项 driving 断言失败；
另一个 ERROR 是误写不存在的 ledger 测试模块名。稳定最终源码、改正模块名后的 79 项复验通过。
首轮文档命令也误写不存在的 navigation 测试模块名；后续使用实际 documentation/public-surface 模块。
这些失败不被最终绿色覆盖。完整平台导出仍有 capture gap，限定检查结果和可见交付保存在本地切片。

当前结果不是 full/global coverage 或真实 Flash 兼容认证。新 head 的必需远端检查独立确认，
旧 cb3 安装包、Windows 合成通过和 live parent/child 候选不得沿用于修改后的产品源码。
