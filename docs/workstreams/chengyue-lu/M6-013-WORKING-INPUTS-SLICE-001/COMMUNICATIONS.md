# M6-013 Slice 001 Communications / Work Log

2026-10-11；所有记录限本片段可见传递与 runtime-observable 静态/Git 事实，不保存隐藏推理或 secrets。原始授权消息来自主准备窗口 `01a1064a-eaef-7da0-aebd-962910ff42b8`；长任务正文按 [Task Packet](TASK_PACKET.md) 归纳，原消息由发送窗口保存（本记录省略绝对机器路径以保持仓库可移植）。

## 输入与范围

Root 转达：人类允许与本窗口并行推进 PR144 新规划；从本地组合提交 `76fd3d892eb1f1a15799c9f24a255ef2dcf0190e` 在独立 worktree 开始 M6-013 第一切片；Skills=[]，20 分钟；只新投影模块/测试/可分离新版本 Schema/own docs/status/primary own-row；不碰共享消费者/CI/旧版本，禁止运行测试/API/付费/Key/账/生产 Attempt，由 Root 测试。完整可见 body 见 [INPUT_MESSAGE](INPUT_MESSAGE.md)。

补充原文：

> 补充最新人类优先级：测试窗口先修 PR140 最后 P2（discussion_r4238260123，entry shared helper 的 direct CI consumer 映射）并转 Ready for review。该修复仅 tests/ci_components.json 和 tests/test_ci_components.py 及验收记录，我会再同步到 material 分支；你刚收到的 M6-013 第一切片保持原范围并行，不编辑这两个CI文件或共享角色/入口消费者，返回ref时注明基于76fd3d8。没有新增API/测试授权给开发窗口。

## 发 Root 的起点通知

> M6-013 第一切片已在 managed worktree m6-013-working-inputs、branch codex/m6-013-working-inputs 从 exact 76fd3d892eb1f1a15799c9f24a255ef2dcf0190e 开始；本地已保留 memories generate=false/use=true（不混入产品提交）。计划只新增纯投影模块/独立测试及候选 schemas/v0.2.0/model-working-input.schema.json，不伪造 Task/Policy/View/Host/Session 已迁移。旧 budget/sub_budget/ceiling 的实际消费者仍闭合旧版本；迁移表给其明确 0.2.0 候选目标与后续接点。投影按 whitelist 保留目标原文/获准材料hash/决定反证/权限交付/typed实际stop，费用讨论文字不删；不复制完整控制对象/账本。不触碰 CI 两文件、共享入口消费者或测试窗口checkout，测试均留 Root。

工具返回发送成功。managed worktree 创建成功，HEAD 与 fixed source 一致；初始 config 缺 memory 段，使用前补 generate=false/use=true，本地保留不 stage。新分支 `codex/m6-013-working-inputs`。

## 对用户的可见进展

> 我会从指定提交建立独立 worktree，先核对 M6-013 的任务边界和直接契约链，再实现工作输入投影、迁移表及测试代码。现有消费者暂不接入；本段不运行测试，约 20 分钟内交付可供主窗口集成的候选。

> 独立 worktree 已固定在 76fd3d8，并补齐记忆配置。现有 Task、Policy、View、Host 和 Session 仍强制耦合旧预算字段，不能靠投影就宣称完成迁移。本切片会交付独立版本的工作输入契约，并在迁移表中列出后续必须串行修改的生产者和消费者。

> 投影模块、候选 Schema 和测试代码已写好：按白名单保留目标原文、获准快照、决定与反证、权限、交付和显式分类的停止条件；不会遍历完整 Task 或读取内部预算、账本。快照 hash 与 Task exact refs 也会核对。现有角色、编译器和执行消费者仍未接入，我正在补迁移表与交接。

> 首切片已完成代码与设计边界，包含 9 项测试代码；AST、内存编译和 JSON 语法检查通过，测试未运行。工作输入采用候选 0.2.0 契约，旧 0.1.0 文件保持不变。我正在提交独立候选 ref；现有角色请求仍走旧路径，M6-013 继续为 IN_PROGRESS。

## 静态观察及限制

00:29:52+08:00 开始；00:41:33+08:00 AST/内存 compile 与 JSON syntax 通过，9 个 test methods；没有 import 项目或执行 code object/测试。逐次补丁只在新 scope，旧文件唯一产品状态改动为 M6-013 行 READY→IN_PROGRESS；所有 deps 在固定 source 为 DONE。当前 guidance/primary entry 和旧Schema生产/消费接口读取范围见 HANDOFF。

有一次必要契约 filename 推测为 conformance-budget-grant.schema.json，发现该路径不存在；只保留旧 live grant 原 version/pins 语义，未打开实际 grant/账本。源模块无外部 $refs，未改 Core/default catalog。提交前复核 source pins、相对 Markdown 文件目标和 diff。Git commit/ref、最后回传追加于本节后的记录；不将 push/结构检查描述为 merge/测试/资格。

## 首次提交与格式修正

初次产品提交 `a32869870d6b94f70252342965364f6aee5c98ea` 的 parent 为固定起点 `76fd3d892eb1f1a15799c9f24a255ef2dcf0190e`，10 个有界文件。cached diff 检查报告新 Markdown/Schema 的额外 EOF 空行，但串联命令仍创建提交；该失败原样记录，不称首次 diff check 通过。随后只规范化新文件 EOF 并更新 Schema pin，产品 Python bytes 与旧 Schema 未动，00:44:27+08:00 working diff check 通过；后续格式提交保留该历史。

> 提交检查发现新文档和候选 Schema 尾部多了空行，首次提交仍被创建了。我会用后续格式提交修正、更新 Schema hash，并保留这条检查记录；产品代码与旧版本文件不受影响。

## Root 接入与验证回执

2026-10-11：收到主窗口接入回执，完整可见正文保存在 [ROOT_INTEGRATION_RECEIPT](ROOT_INTEGRATION_RECEIPT.md)。Root 报告按 a328→9a93→ad7 三提交接入 `codex/material-input-closure`，接入提交为 `3df14906`→`6a8c374c`→`05533b9c`，保留 PR140 P2 同步 `9f2`。Root 报告独立投影及旧 Schema 正反共 9 项无失败；同组 CI 首次因新 material source 未入 Git inventory 失败，原件保留并显式 stage，后继组验证另行归档。本窗口没有执行测试或复核其原始日志。

新材料快照包含 `material_provenance`，当前投影白名单会拒绝该字段，尚未组合消费。该差异交由 Root 后续接合；本片段产品/Schema/tests 原 hash、首次失败历史和 source ref 保持冻结，M6-013 继续 IN_PROGRESS。本次仅归档可见回执并更新 primary 项目记忆 own-row，无共享代码修改、测试执行或重复 PR。

## Root 并行首切片收口回执

2026-10-11：第二份完整回传追加在 [ROOT_INTEGRATION_RECEIPT](ROOT_INTEGRATION_RECEIPT.md) 的“并行首切片收口回执”。Root 报告材料消费追加提交 `ddada2af04b186d283d9958ce813ee38982be535`，新建 [Draft PR145](https://github.com/Chengyue-Lu/research-agent-workbench/pull/145)；源码 112 独立方法（包含本片段 9 项）全 PASS、文档 17 PASS、同源码独立 wheel 材料整链重复 7 方法 PASS、16 entry 模块/resources 字节身份核实，独立 0.2.0 Catalog 消费投影通过。次数分属不同验证范围，不累加为独立方法总数；本窗口未运行测试或读取原始验证日志。

首轮持久长归档正例的 FileNotFoundError 与 unknown 原件保留，Root 只改短证据根后恢复，未证明具体系统根因。实际角色/旧 Runtime 尚未消费投影，`material_provenance` 仍未进入白名单；PR144 未合并，Root 报告实际 develop feature 治理仍受继承 Task 定义阻断。M6-013 保持 IN_PROGRESS，产品冻结；下一实施接点为版本化材料/结果槽及真实角色消费者，须后继有界 Packet。本次仅归档与 own-row 更新。
