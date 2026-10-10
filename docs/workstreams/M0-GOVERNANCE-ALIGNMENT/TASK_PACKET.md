# M0-008：机器治理与人员限制对齐

日期：2026-10-08。Task、状态与验收以 [TASKS](../../TASKS.md) 的 M0-008 为准；风险 R2，feature → develop。定义基线为已合并 PR141 的 develop `e49386140c18cdfb9e6065b7c59e2545f863e386`。本 Packet 不修改任务定义、运行身份 Schema 或历史接受记录。

## 授权与目标

人类已取消固定开发人员分工和指定人员门禁，并要求继续推进。[ADR-0023](../../decisions/0023-DEVELOPMENT-WITHOUT-PERSON-ASSIGNMENTS.md) 与 [Development](../../DEVELOPMENT.md) 是现行规则。目标是使本地治理器、模板、CODEOWNERS 与实际适用审核规则一致，同时保留 Task、风险、功能权限、PR、CI、合并拓扑和发布边界。

不要求人类现在选择固定角色编制、工具组合或另一个开发者。机器检查不把自报“通过”当审核事实；最终具体代码合并仍按人类指令。

## 输入与互斥范围

- Agent Profile：bounded governance implementation；required Skills：空列表。
- 允许输入：仓库指导、上述定义/规则，本次机器遗留审阅中定位的治理 policy、checker、PR 模板、CODEOWNERS、直接 tests，以及远端适用 ruleset 的脱敏事实。
- 实施写入范围：`.github/governance-policy.json`、`.github/scripts/check_pr_governance.py`、`.github/pull_request_template.md`、`.github/CODEOWNERS`、`tests/test_pr_governance.py`、`tests/test_governance_helper_branches.py`。若审阅证明另一个直接消费者必需，先在本 Packet 追加范围再修改。
- 文档/状态范围：本目录、`docs/STATUS.md`、M0-008 状态及真实化既有计划的事实校准；不改其他 Task 定义/依赖/验收，不改原 DONE 行。
- 本地开发阶段不修改 workflow 检查名称、release checker/policy、对象 Schema、产品权限、provider 配置、凭据或生产账本。共享主 checkout 的用户编辑保留。
- 本阶段预算：一个有界本地切片、一次实施与必要修复；实现与确定性验证不发付费请求。可见通信、检查和失败留在本次 archive；不记录密钥或隐藏推理。

## 实施与验证顺序

1. 核对具名 owner/reviewer 映射及直接消费，区分开发人员规则与运行事实身份。
2. 用变更风险、任务资格、证据和实际 review 状态取代固定人员组合；模板和 CODEOWNERS 保持一致。
3. 检查普通 feature/task-definition/release 的合法路径；证明另一个人员不可用不再是门禁，反面证明 CI 失败、非法拓扑、实质 blocker、权限/来源不足仍被拒绝。不能以减少测试覆盖实现政策放宽。
4. 保存本地 diff 和适用确定性测试；核线上规则修改前后的完整配置与实际适用对象，单独审查审核设置变化，硬门禁层须保持。
5. 给出可读输入、修改项、验证和剩余限制，逐项对照 Task；远端未同步时不标 DONE。准备具体 PR 供人类审阅。

## 交付与停止

2026-10-10 追加执行授权：人类明确要求“完成 M0-008 的剩余同步”。允许在线核对四层before、仅更新两review层、重新GET核对actual after与两hard层不变；本次2次PUT，无bypass新增，保留完整原件/hash、风险窄审与可读结果。此同步授权不推导PR142合并或任何release。

交付：机器政策/模板切片、测试证据、[风险记录](RISK_LEDGER.md)、本地与远端状态差异、紧凑 Handoff。工程检查不能替代人类决定或科学接受。若需要删除硬门禁、改变运行权限/核心语义、缺远端管理权限或发现共享写冲突，保留事实并停止相应动作；其他互斥工程工作可继续。

下一研究桥接切片仍属于 M1-010/M2-009/M11-008：按 PR140 候选核对实际产物到消费者，补包内受信 caller/factory。M0-008 不合并 PR140、不把隔离 API 成功改为三项 DONE，也不重新冻结或重写原测试账。
