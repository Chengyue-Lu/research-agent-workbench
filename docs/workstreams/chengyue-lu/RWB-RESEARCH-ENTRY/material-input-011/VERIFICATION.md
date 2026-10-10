# 材料桥接与工作输入首切片验收

2026-10-11；候选分支 `codex/material-input-closure`。原三项桥接 Task 与 M6-013 均保持 IN_PROGRESS；本记录描述选定消费者的工程验证范围。

## 来源与实际修改

开发基线为 PR143 `fcb1cfd`、PR144 `fee6b3af` 的本地组合 `76fd3d8`，同步 PR140 最后 P2 后为 `9f2cfe6`。并行 M6-013 产品、格式和来源回执三提交 `a328698` → `9a93ae8` → `ad7c9fd`，在本分支分别接为 `3df14906` → `6a8c374c` → `05533b9c`。本地整合不是这些 PR 的合并或接受事件。

新增 `entry/materials.py`，由原 `roles.read_pinned_inputs` 统一消费；intake 编译/发布、角色请求继承同一读取规则。工厂在写角色目录前检查实际 Task 材料，Driver 构造、Trace 读取、派发及最终原 Provider 入口复验。实际 Provider 计数在最终复验之后增加，不把被拒绝的内部 facade 入场算成实际调用。新模块与实际 fixture 消费者已登记组件 CI，原波次及共享 helper 映射保留。

M6-013 新增纯工作输入投影与候选 0.2.0 Schema；角色请求、Task/Policy/View/Host/Session/workflow 尚未切换。默认 SchemaCatalog 保持原版本，安装包验证显式选择候选 0.2.0。

## 本轮验证

使用 Windows CPython 3.11.16，显式脚本与 `-I` 入口。以下最终源码运行的 case ID 不重叠，合计 **112 项 PASS、0 FAIL、0 ERROR、0 SKIP**。

| 消费层 | 结果 | 核实内容 |
| --- | --- | --- |
| 材料单元、角色、工作输入、CI/metadata、Schema | 90 PASS | 26 材料方法、14 角色方法、9 投影方法及 CI/Schema 回归；真实 Windows 大小写路径和 junction 的来源区拒绝，无隐式 sibling 读取 |
| 实际材料整链 | 7 PASS | intake → 编译 → 包内工厂 → Bundle/View → Host → child 正式 Handoff → fresh main 消费；各次实际请求均带同一组三类材料 pins/provenance；独立冷验成功 Receipt |
| Driver 与桥接回归 | 15 PASS | 普通输入、实际失败/unknown/取消、0/1/3 child、真实调用计数及既有只读 Tool 消费 |
| 独立安装包材料整链 | 7 PASS | 同 7 项重复消费者检查；短持久归档根下 0 FAIL/ERROR/SKIP、无 source drift；不加入上述独立 case 总数 |
| 文档与公开表面 | 17 PASS | 与 112 个工程方法分列；内部链接及 Task 保留另由最终文档检查核实 |

最终文档检查覆盖 138 个修改或新增 Markdown 文件、693 个内部目标与 28 个锚点；130 个 Task ID 唯一，73 条旧 DONE 行逐字不变，任务定义与 PR144 精确一致，只有本候选四项进行中状态按实施推进。

新 wheel SHA256 `bf9c9d9f06f97425c3188ec982ecb52e783bcd117ba1e846281d011149265f6a`。16 个 entry 模块与所测源码字节一致，安装后的 Runtime manifest 为 `9d9e3ad2dc78053aba10eff443467dec5188a280ebd27b262d5ee72a85e8c4a9`，与构建源相同；独立安装的 0.2.0 SchemaCatalog 能消费纯投影产物。这只证明候选包和独立契约消费者，不证明角色请求或无额度 Runtime 迁移。

## 正反链输出

成功链实际得到 1 次 intake 与 3 次角色调用、三个冻结角色记录、成功 Receipt、child/final Handoff 及新主会话消费；离线注入 Provider 的已知用量合计 152 tokens，held 为 0。每次请求只读取原件、canonical sidecar 和选中派生文本，sidecar 中声明但未选的缺失派生项没有被打开。此调用和用量属于离线端口测试，不是付费模型账。

缺 sidecar 时，intake 与直接工厂均在实际调用前拒绝；模型输出删掉 sidecar 时，保留已经发生的 intake 调用、30 input / 8 output 的已知用量及原响应，控制草稿编译失败。raw、sidecar、派生文件在 guard、builder、请求捕获或 Runner 最后时钟回调之后漂移，实际角色 Provider/Tool 调用均为 0，Host 事实保持 0。

请求已经捕获的零调用分支仍可能产生 incomplete closeout：旧 generic closeout 要求 capture 数量与调用数相同，无法据此生成完整 Receipt。本轮断言并保留这个缺口；它属于后续 M11/M6 消费者计数接合，不制造调用、科学通过或 Receipt。

## 原始运行与失败保留

私有工程证据入口为 `.rwb/material-input-011/`：最终 `deterministic_final_02`、`material_bridge_01`、`dispatch_regressions_final`、`material_installed_short_final` 与 `docs_final` 的原生日志/结果，`BUILD_INSTALL`、`INSTALL_PINS`，静态消费者映射、两轮来源边界审查及可见通信。原安装失败 case 在 `material_installed_final_cases/`，短根恢复 case 保留于任务指定的独立工程证据目录；`FINAL_PROOF_INDEX.json` 列出两组工件及最终源码字节快照的路径/hash，并重核 wheel 与 16 个源码/安装模块。该归档不作为公开包支持或正式科研评审包。

首次持久归档的安装整链为 6 PASS / 1 FAIL：正例在 child 的首个 Trace decision 附近发生 FileNotFoundError，Workflow safe-paused，并保留当时的 unknown hold。主 decision 绝对路径长 256、child 目标长 264；原 wrapper 没有持久化异常 filename/errno/stack，无法据此确认具体系统根因。只将归档根改短后，同一 wheel、产品、7 个方法与相对输入布局全部通过。这证明结果对归档路径或环境敏感，不能宣称长路径产品适用性或异常保真已完成。原失败、静态定位及恢复结果均保留，不以恢复重写旧 unknown。

首轮 CI 检查在新源码尚未进入 Git inventory 时有 1 项失败；显式登记该源码后重跑通过。首个 90 项运行真实 symlink 缺 Windows 权限而 SKIP，后继使用实际 junction 完成该反例，最终无 skip。较早 49 项 consumer 运行原生全部通过，但期间修复材料/Driver 导致 source drift，退出 1，不计作当前完整版本的最终通过。安装检查首轮错误使用默认 0.1.0 Catalog 查 0.2.0 kind 而失败；只修检查入口为显式版本，默认 Catalog 与产品保持原语义。原结果、脚本和 capture gap 说明分别保留。

## 接受与下一步

材料快照的 provenance 槽尚未接入 M6 纯投影白名单，须先明确版本化材料/结果槽，再迁移角色请求和旧 Runtime；Source/Evidence/Claim/MethodTrace、qualified Skill 装配、大材料消费、真实工程质量等仍按原 Task 推进。

本分支继承尚未合并 PR144 的 Task 定义。仓库治理明确禁止 feature PR 新增或重写 Task 定义，因此合并须先消费 PR144 的已接受 develop 基线，再检查实际差异与治理；不能以本轮工程检查替代该分界。候选保持 Draft，不改治理规则或旧 DONE 行。

本轮新增付费 API、生产 Tool、生产 Attempt、凭据和账本操作均为 0；旧 live grant、Source/Skill/Human 资格保持各自原身份。详细风险见 [Risk Ledger](RISK_LEDGER.md)，模块输入输出见 [README](README.md)。
