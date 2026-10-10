# CHAIN-NARROW-010 限定实现审查

2026-10-08；Agent Profile targeted implementation reviewer；required-Skills=[]。
结论：在下列实际读域与 source pins 内，未发现需要修复的实质 P 级缺口。本结论是有界静态审查，不是最终测试覆盖、整 API 链通过或 live/Source/Human 资格接受。整 API 链未全部完成，Source/Human=false。

## 已核修复与确切接点

| 主题 | 静态来源 | 判断与边界 |
| --- | --- | --- |
| Profile limits 进入纯 wire consumer | src/research_workbench/adapters/models/wire_codecs.py:162–172、175–231、270–301；schemas/v0.1.0/provider-api-profile.schema.json:768–786 | _Profile 保存 limits；_profile 将 implementation.limits 映射为 MappingProxyType；_validate_request 对实际提供的正整数 max_output_tokens/max_tools 执行 ceiling 检查，并将同一 limits 传给 ProviderCapabilities/preflight。超过输出限额、漏显式输出值或 Tool 声明过量均在 encoder 路径拒绝。完整 Profile schema 要求两项整数限额；旧 pure descriptor 未提供 limits 时取空 mapping，保留旧窄兼容路径，不虚构 vendor 默认限制。 |
| main 请求具备动态 child Task 的 schema | src/research_workbench/entry/roles.py:155–249，重点223–233；schemas/v0.1.0/task-packet.schema.json:7–17、25–76；schemas/v0.1.0/common.schema.json:53–80 | main 独立 payload 增加真实 catalog task_packet/common schemas，再与原 Task、exact inputs、caller context 一起 compact JSON。main baseline 明列完整 TaskPacket delegations、0..N 与 caller 校验。schema 是模型输入约束材料，未被当作模型输出已验证；实际 child 仍经 _validate_child 的 schema/权限/输入/预算检查。 |
| 可选 Task revision 使用既有默认1 | src/research_workbench/execution/runtime_bundle.py:104–179，重点177；src/research_workbench/entry/driver.py:383–444，重点428–429；schemas/v0.1.0/task-packet.schema.json:7–17 | Task schema 不把 revision 列入 required，存在时至少1。Method→Task 关联 identity 比较和 Trace recorder 初始化均 task.get('revision',1)，避免合法无 revision Task 被错拒或 recorder KeyError。没有写入/改造 Task 本体或改变已有 revision。 |
| child network/其他权限采用 canonical 关系 | src/research_workbench/entry/workflow.py:130–180，重点154–165；src/research_workbench/capability/resolver.py:26–40、364–387 | _validate_child 调用 permission_policy_covers(parent.permissions, child.permissions)，覆盖 canonical filesystem/network rank、external_write、allowed_roots；仍保留 write_scope、输入pin、question/Mode/capability、禁止Skill、深度与sub-budget校验。不存在另用旧network枚举而错拒canonical allowed/search-and-fetch 的本地分支。roles:175–181 仍拒绝执行前 unspecified 权限。 |

必要条件仍成立：entry no-Skill 请求在 required_skills 非空时明确拒绝（roles:171–172），不通过本次 schema 加载跳过 Profile 或 Skill 准入。driver 的 recorder 仍使用 Frozen View/Bundle 的绑定与权限读写集合，而非 Role 文本自报。此次没有重审 output closeout、source qualification、实际 Provider observer、完整账或 Tool 路径，不对这些域扩大结论。

## 实际读域与阅读限制

仅函数/相关窄正文：

- wire_codecs.py：_Profile/_profile 162–231，_validate_request 270–348；直接 encoder调用索引355–364，辅助内部相关纯schema/strict段在同次窗口234–267。
- roles.py：build_role_request 155–249；同文件角色baseline30–68用于 main输出约定核对。
- driver.py：execute_role_slice 383–444，含 recorder初始化428–434。
- workflow.py：_validate_task/_validate_child 130–180。
- runtime_bundle.py：_derived_edges 104–179。
- resolver.py：canonical rank26–40、permission_policy_covers364–387；相邻349–361/390–399在定位窗口输出，未扩大生产调用审查。
- Task/AgentProfile schemas的 required/revision/permission/delegation/budget 窄段；ProviderApiProfile schema limits768–786；common.schema 的 fileRef/permissions53–80系上述直接schema引用。其余历史/测试/运行正文未读。

两次批量输出被工具截断，关键 roles final schema段205–249及wire validator尾343–348已窄读补齐；没有把截断输出作为全文阅读证据。source hash用于固定整个文件 bytes，不表示整个文件正文均被审查。不运行产品/测试/API/Tool，不读取 Key、历史账/Attempt、不 Git 或记忆操作，不修改 source。

Root 提供的当前证据：64 Profile/wire OK skip1、预算8OK、Bundle12OK、第三次原始Bundle冷读PASS、workflow/roles21OK、bridge6OK。全部为 Root 反馈，本组没有重跑或读测试正文。bridge suite 在 roles 最后 schema 改前启动，因此不能宣称 bridge6覆盖本报告 pins 的最终 roles 版本；须保留其版本覆盖限制。

## Source pins

| Repo-relative source | SHA-256 |
| --- | --- |
| src/research_workbench/adapters/models/wire_codecs.py | fdf1c14ed6be7abee7be02f3cc8e11b1f5eb523d1ec33c50d0def1657959a427 |
| src/research_workbench/entry/roles.py | 31f0355bad1021760435f8a8bdeaee379d74484459418664ce53d9af471de50b |
| src/research_workbench/entry/driver.py | 9f1beba886947509bbd2ce77a1acc8b9191d1d37461eb6a500cc225b542130aa |
| src/research_workbench/entry/workflow.py | 5b70ed862c22a46535581bcbd407e3034ff8c1edfd52d74a8de6a0f30c6e2f5e |
| src/research_workbench/execution/runtime_bundle.py | f9a5b38d50772c354a69de230533ea05a37c1daabd8bfa5a43313632a87005a5 |
| src/research_workbench/capability/resolver.py | 6b295cbf7ca38bb819556b5aff26f6d6ae30285ad8516ef3cb65fcba70311e1e |
| schemas/v0.1.0/task-packet.schema.json | d2ebc01795522103d09465c8af0c54f025f26b69ed41abac08793d4a75a7d24f |
| schemas/v0.1.0/agent-profile.schema.json | b01dabfe08bd5c2fbfca44192301885f10c3246f5c7b4bbfb8ac87e170433ce8 |
| schemas/v0.1.0/provider-api-profile.schema.json | 5d097d2b75db1d931005cc623de4d5a10ca1f6e3a0db7ff65f4533d14725bec0 |
| schemas/v0.1.0/common.schema.json | f9e94daf4fd9250514d30d67a5307423ea724fe1b96fbc421c7c7c709352fa97 |

可见派单与回传记录：[NARROW_COMMUNICATIONS.md](NARROW_COMMUNICATIONS.md)。仅静态引用存在性检查及 hash；本组交付后停止。

## 3分钟增量审查：Profile列表与选定adapter前置（2026-10-08）

结论：在本次增量实际读域内未发现新增实质P级风险。新增文字/字段解释当前绑定的执行前置，没有在所读代码中改变人类权限、重新选供给、加载额外文件或创造资格。

- roles.py:48–60 明令使用 caller 提供的Profile，不发明identity；保留所选adapter prerequisites，不能容入人类ceiling时block，prerequisites不grant权限。roles.py:227–234 的 available_agent_profiles 只含当前经Task/Profile绑定检查提供的 profile.agent_profile_id，不伪称其他Profile可用；仍携带真实task_packet/common schema。这个列表描述当前caller实际提供的单Profile，并非平台固定只有一个Profile。
- executor.py:52–81 先 load已验证Bundle/View并精确核 frozen_task==invocation.task；从 View.selected_supply_report_ref 指向 Bundle.documents 的既有选中Supply复制 supply_ref/required_permissions/data_egress_behavior，覆写到独立 plain context。这里没有 read额外文件、grant权限或改selected Supply；role builder使用context说明字段，实际Task/Profile/resolver/Host约束仍负责拒绝不可执行的proposal。所读context注入代码不修改 frozen_task、Supply或View。
- test_entry_bridge_flow.py:79–112 新增 consumer断言：每个实际captured request中的三项约束与该binding的View selected pin及Supply正文相等（92–99）；现有child结果/receipt/usage消费断言100–112仍保留。只核测试正文断言接点，没有运行；该测试不能据静态存在被称为PASS/live或权限接受。

本次只读 roles.py:48–61、218–252，executor.py:46–138（新增核心73–85与上下文绑定消费），bridge测试79–114及对应符号索引；未读新账/原件、实际API响应、其他测试或资格材料。增量允许源的整个文件hash如下，前表roles pin是上一轮snapshot，应保留历史含义：

| Repo-relative source | 本次SHA-256 |
| --- | --- |
| src/research_workbench/entry/roles.py | c69f0e2e0c799b71b90c6975f436a991414c7922a549d842a03d132e07438f5b |
| src/research_workbench/entry/executor.py | 0a068d3b579646f56ddeece27dc38c0febd38a45309cb13231263642cf684f15 |
| tests/test_entry_bridge_flow.py | ee0f9aa090d274da7397fdf10bb899e5213eb77ffb0aecf3ca0a1fca3d8c272e |

Root提供Bundle13套PASS2.423s、三新mainReceipt冷验PASS及用量/hash核对等结果，仅在通信原文保留。没有独立验证这些结果；Root全入口最终套仍在运行，未宣称PASS。新8 Attempts/11HTTP entries的反馈不表示已发child/Guide/liveTool，本轮这三条路径尚未实际覆盖。整API链未全成、Source/Human=false仍适用。仅静态引用/hash；交付后停止。
