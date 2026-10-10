# CHAIN-ASSET-002 候选资产索引

本目录全部内容为 **test-candidate / 未准入**。用途是人工材料的桥接与文件装配测试，既不发布 Skill Release，也不认证来源、科学结论或生产可用性。角色 baseline 是职责要求；这里的可选 Skill 不成为角色启动条件。PR140 源基线为 `d630f8e174846f4932d05a7a0d69076930b53ee1`。

| 资产 | 用途与调用位置 | 输入 → 输出 | 启用条件 | 关闭与边界 |
| --- | --- | --- | --- | --- |
| [control-intake](prompts/control-intake.md) | `build_role_request(role="intake", instructions=...)` 的人类意图成形变体 | 人类意图、完整人类 ceilings、精确 refs → control JSON | 需要把口语要求变成可检查草稿 | 权限/预算/身份未知时保留 unknown；缺合法 ceilings 时 caller 阻断编译 |
| [protocol-task-method](prompts/protocol-task-method.md) | 同一 intake 入口的已有 Protocol 配置变体 | 已有 Protocol、Task ceiling、获准 Mode/Action/Profile → Task/可选 Method/Requirement 草稿 | 已有人类约束，需要配置下游契约 | 不选择 Registry Supply；没有资格证据不填 proceed 或伪造 pins |
| [main-orchestration](prompts/main-orchestration.md) | `build_role_request(role="main", instructions=..., context=...)` | Task、链路剩余预算、实际子结果 → control decision | main 首次规划或消费实际返回 | 是否委派与数量动态决定；不继承旧 chat，不把提案算成已运行 |
| [child-handoff-state](prompts/child-handoff-state.md) | `role="child"` 或 `role="handoff"` 的受限结果消费变体 | 原子 Task、实际结果/refs → control decision 与可追溯摘要 | 原子执行后交付或 main 对交付作 disposition | checkpoint 写入由 caller 决定；不从模型文字伪造 usage、ref、Human 接纳 |
| [guide-read-only](prompts/guide-read-only.md) | 专用 `build_guide_request` / `ask_guide` 的设计候选 | 人类问题、MainState、明确获准必要 refs → 人类解释 | 人类要求独立解释，避免污染 main | PR140 无外部 prompt seam；候选未执行，不能作为 approved_ref 提升为 system instruction |
| [rwb-control-format](skills/rwb-control-format/SKILL.md) | 可选的 control JSON 格式成形能力 | 已决定的配置、caller schemas → 既有 control JSON | 仅当测试明确选择此文件，并记录实际加载 bytes/hash | 不承担 intake baseline，不新增权限，不证明 Runtime Skill admission |
| [rwb-bounded-summary](skills/rwb-bounded-summary/SKILL.md) | 可选的有据摘要能力，child 内容层 | 精确获准材料 → summary 内容对象 | 原子 Task 要求摘要，并明确选择候选 | 不跨 refs 查找，不凭摘要判定来源或科学正确性 |
| [rwb-faithful-writing](skills/rwb-faithful-writing/SKILL.md) | 可选的保真写作能力，child 内容层 | 已有草稿与支持 refs → revised 内容对象 | 原子 Task 要求文字修改，并明确选择候选 | 不扩大事实/主张；不能替代证据提取或质量认证 |

[CALLING_CONTRACTS.md](CALLING_CONTRACTS.md) 记录可直接使用的接口与组合顺序。[neutral-note.md](materials/neutral-note.md) 是唯一人工内容材料，可供摘要和写作文件装配测试；它不是研究证据或 source admission fixture。

每次只加载所选 prompt 与所选 Skill 的完整 `SKILL.md`，以及该 Skill 明确需要的 reference；没有递归目录加载。角色数、子任务数、领域、预算、事件数、轮次由 caller 数据参数决定，资产不预设这些值。

资产 SHA256 由 **Root 在选择与冻结实际输入时**计算并写入测试记录。worker 的交付 hash 只证明交付文件字节，不替代 Root 的实际 request 装配与 Skill 身份/资格冻结。当前状态：待 Root 选择、冻结与测试。
