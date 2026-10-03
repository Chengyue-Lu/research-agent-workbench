# FOLLOWUP-013：报告与持久用量账本一致性

Task：M6-009，R2。用户要求修复 PR128 审核指出的实际用量核对缺口，并在修复、检查通过后合并。
黄毅仍负责 Provider/API；路诚钺负责本次共享证据语义协调。该合并授权不等于 M6-009 整项完成。

## 输入与写入范围

读取报告 verifier/writer、conformance driver 的回执与失败路径、durable journal/ledger 的 snapshot、
报告 Schema、既有 binding/reporting 测试及用户审核截图。只修改
`profile_conformance_report.py`、新增用量一致性测试、本次检查/交接及工作流导航；保持原字段和版本。
在 `tests/ci_components.json` 登记新测试及其共享 binding/reporting fixture 的直接消费者。

根协调 Agent Profile：Provider report correction coordinator；requiredSkills=[]。
独立回归作者：Provider report verifier regression；requiredSkills=[]；12 分钟。
独立审查者：Provider report P2 correction reviewer；requiredSkills=[]；5 分钟。
两角色只读取上述直接消费者；作者只新增测试及本地审计工件，审查者只写本地检查/交接。
根窗口执行集中测试、PR 更新和已授权合并；可见交付及 BEFORE/AFTER 发现保存在本地切片。

## 预期行为与停止条件

bound 1.1 报告当前 Attempt 的完整实际用量匹配对应 `reported_usage`；累计 input/output/total
来自全部历史完整回执。缓存输入、推理输出分别是父计数的子集。未知值不能改写为已知零，
删除已知回执不能制造零消耗。正常 partial、未结算写入失败及最终 accounting 不可得时保留事实；
旧 1.0 继续原来的结构回放。

一次新回归 fixture 计划 11 次 fake HTTP，全部篡改只做 cold verify；真实 API、凭据操作为零。
截图中的 9,000,000 输入篡改必须在 writer 创建文件前拒绝。适用检查失败时先诊断并修复，
不能沿用旧 source 的绿色结果或安装/Windows 绑定。正式 Task、Schema identity、SDK 替换不在本次范围。

真实 Flash 测试继续遵守北京时间 18:00 后及官方闲时、全部成功失败 input+output 累计不超过
10,000,000、未知用量 held-STOP 和无自动 retry/fallback。费用 unknown 不阻断。
