# M6-009 通用 Provider 离线收口

验收对象为 develop `3e01158bbf6730bcd3089356e7e307cef4b857dc`：
[PR #128](https://github.com/Chengyue-Lu/research-agent-workbench/pull/128) 的 squash tree
与已修复 head `c3af91f78918d13149dbadf22697562ddff0c661` 相同，sole parent 为
`27cbf860e48e9639bd3af32a58c12bfd88d87526`。

路诚钺在 2026-10-03 明确授权修复后合并 PR #128，并默认批准其后授权范围内的推进，实际硬阻断除外。
本记录据此提出并接受以下离线完成判断；[直接维护者决定及执行回执](https://github.com/Chengyue-Lu/research-agent-workbench/pull/128#issuecomment-5966860653)
保留该授权来源。Provider/Session 维护者仍为黄毅，不记录黄毅新的整项批准、reviewer 不可用或续获
cross-owner approval。Task 状态由 [TASKS](../../../TASKS.md) 维护。

## 定义条款与结果

| M6-009 离线要求 | 已合入的实现与可定位证据 |
|---|---|
| 真实厂商身份、协议、endpoint/auth、exact model/mode 与配置 hash 分离 | 闭集 v2 profile/config 与独立 factory，不按 URL 推断厂商；[初始合同检查](attempts/CANDIDATE-001/CHECKS.md)及[配置后继](attempts/FOLLOWUP-002/CHECKS.md) |
| 四协议与十一家 Key 接入 | Responses、Messages、generateContent 与 Chat Completions；十四份默认禁用 profile，十一家 factory 合成正例；同上 |
| 官方能力、认证、模式、Tool、Schema、usage/error/rate、价格及数据控制矩阵 | [官方矩阵](../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_MATRIX.md)和[逐字段记录](../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_FIELD_COVERAGE.md)：十一家 × 十五字段，D31/P129/U5，保留日期、官方来源、有限事实和 unresolved；Azure/Vertex/Bedrock 部署认证边界独列 |
| 晚解析 CredentialProvider 与非秘密 source reference | 跨平台环境引用基线、可选本地桥；配置构造与能力预检先于密钥解析；[传输安全维护](https://github.com/Chengyue-Lu/research-agent-workbench/pull/126)及初始合同检查 |
| 未知或不支持硬能力出站前拒绝 | 独立 text-only 路径和显式模式/能力 gap；未把 JSON、本地 Schema 或兼容协议伪装成远端 strict、thinking 续传或不同 Provider；配置后继检查 |
| 原三家/default Session/config/report 兼容与用量保真 | 合法 incomplete/部分文本、响应摘要失败的已知用量保留；[PR #127](https://github.com/Chengyue-Lu/research-agent-workbench/pull/127)；[报告 P2 修复检查](attempts/FOLLOWUP-013/CHECKS.md) |
| endpoint/config/codec/helper 闭包、baseline producer 与 cold replay | opt-in manifest1.1/provider-binding-v3/envelope1.2；helper/package-init 图在构造、用边界和 cold replay 独立匹配；[图消费者检查](attempts/FOLLOWUP-003/CHECKS.md)及[驱动绑定检查](attempts/FOLLOWUP-004/CHECKS.md) |
| 显式 specific→一次纯 Tool result→none Session 与 Schema 方言 | 同一 Session 两轮政策、实际本地 Tool、固定三阶段驱动；wire Schema 和本地业务断言分别检查；默认 caller 不变；驱动绑定检查 |
| 零真实 API、保持实现边界 | 离线 fake 路径和零调用拒绝；CLI 仅生成计划；未新增 retry/fallback/Router/Supply selection 或 M5/M11/Resolver/Skill 实现；上述检查均按源版本限定 |

矩阵的 P/U 是已声明的限制与后续来源。定义允许未知字段保留 unresolved；这些字段没有取得能力通过
或账户可用结论，也不要求先完成所有厂商的真实验收才能接受通用离线合同。

## 当前源码验证

- 最终报告修复：13 项用量一致性、79 项 report/binding/journal/ledger、45 项
  documentation/public/component 检查，共 137 PASS；[FOLLOWUP-013](attempts/FOLLOWUP-013/CHECKS.md)
  保存命令、原失败和 source hash。
- [当前 PR Component/CI result](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37103999479)
  completed/SUCCESS，实际 868 tests / 2629.975s / OK；workflow head 为 c3af91f。
- [当前 governance](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37104000818)
  SUCCESS；合并前 latest base/head、零未解决讨论及 hard gates 均核对。
- CI 日志的 synthetic merge checkout 为 ce86b6a5；合并后该 commit 无法从本地 Git 或 GitHub
  git-commit API 重新取得。该捕获限制保留，不声称已重新验证它的 tree；最终 accepted merge 与
  head 的 tree 等价由 Git 直接核实。

以上范围不称为 full、global coverage、多 Python 或当前 Windows 全流程 PASS。
早期源的 FAIL/ERROR、被取代的取消工作流与平台 capture gap 保留；历史安装检查按其 source 身份读取。

## M6-010 的独立剩项

M6-009 离线完成不转移旧安装包或本地原型的执行资格。当前可选 Windows 凭据/启动链存在 genuine
typed guard 拒绝，正在以新安装版修复和验证；旧 cb3 安装与合成 PASS 不覆盖当前合入源码。
该 exact 路径的安装、helper、Windows context、固定 run/Tool/session、报告输出和唯一预算历史
仍须闭合后才执行 M6-010。

实际请求只使用官方精确 `deepseek-flash`，每次北京时间 18:00 后且官方闲时；全部成功和失败
input+output 累计不超过 10,000,000，cache/reasoning 子项不重复加。每 Attempt 最多三调用、
一次纯 Tool、每调用 256 output，API 阶段 120 秒；外层 Windows 600 秒及合作式 605 秒发布检查
分别记录，无自动 retry/fallback。未知用量保留预占并停止，未知费用/币种/账单不阻断。

第三方 SDK 替换和进一步竞品调查没有成为本次 M6-009 新完成条件。真实 Flash conformance、
M5 四臂 Pilot、A4 admission、科学评价与发布各自保留定义和验收边界。
