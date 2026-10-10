# CHAIN-ASSET-002 Compact Handoff

日期：2026-10-07。状态：**test-candidate / 未准入**；资产准备完成，尚待 Root 冻结、真实 request 装配与测试。Agent Profile 为 bounded role prompt/Skill package designer；required Skills 为 `skill-creator`，已按其 naming/frontmatter/窄职责要求执行。没有后续委派。

交付范围为 [INDEX.md](INDEX.md)、[CALLING_CONTRACTS.md](CALLING_CONTRACTS.md)、五个职责变体、三个 optional Skill 候选、一个 Skill reference 和一个人工内容文件；完整可见消息、读域与检查记录在 [ASSET_COMMUNICATIONS.md](../ASSET_COMMUNICATIONS.md)。资产用途、接口、输入输出、启用/关闭条件由索引定义。

实际判断：intake baseline 承担人类意图与已有配置成形职责，可选 control-format Skill 仅测试窄格式方法装配，不承担准入；main 依任务与实际结果动态决定是否委派以及数量，child/handoff 保留不完整与失败事实，并只提出状态下一步；Guide 因隔离用途保持独立只读，不自动把问答送回 main。摘要与写作候选提供内容对象，可进入 control `summary` 字符串，避免改变既有控制根字段。

已核接口限制：PR140 `build_role_request` 支持非 Guide 的独立 `instructions/context` user payload，必载 system baseline 不被替换。非空 `required_skills` 明确阻断；只读取候选文本并不代表正式 Skill/Runtime admission。专用 Guide 没有外部 prompt 参数，generic Guide 拒绝 instructions/context；Guide 文件当前是设计候选，真实外部变体加载需另行有界 seam。approved_ref 只能成为数据，不应被提升为 system authority。

静态验证：UTF-8 strict decode、候选标记、三份 `SKILL.md` 的两字段 frontmatter/name/folder/description 字面值检查，以及全部本地 Markdown 链接解析，通过；第一轮为 12 文件、3 Skill、26 链接、0 问题。交付新增此 Compact 后由最终静态检查记录确认。未执行产品、API、Tool、Key、账、Skill forward-test、安装、commit 或 push；没有 source/Registry/Schema/生产 Skill 写入。

SHA256 责任：worker 仅交付本 Compact 与通讯文件的内容 hash，Root 对实际选用的 prompt/Skill/reference/material 文件计算并冻结 SHA。Root 应记录实际 request 的 bytes/hash/message 位置，不能从候选路径或文件存在推断加载成功。

Root 下一步：选定当前合法 Task/Protocol/Profile/预算，按调用约定捕获精确 refs；先证明非 Guide prompt 与所选 Skill 文本实际装配，保留 required Skill 阻断界限；Guide 先核内置独立 baseline，外部 seam 若未实现保持未验证。全链路执行、失败与桥接判断仍由 Root 唯一测试者完成。

供协调者写入 primary `PROJECT_MEMORY.md` 的精确建议条目（本 worker 无共享记忆写权）：

> 2026-10-07 CHAIN-ASSET-002：PR140 分支基线 d630f8e174846f4932d05a7a0d69076930b53ee1 上已准备 5 个角色 prompt 变体、3 个 optional 窄 Skill 候选与人工内容材料；来源为 chain-proof-002/assets/INDEX.md、HANDOFF.md 及 ASSET_COMMUNICATIONS.md。仅完成静态 frontmatter/UTF-8/本地引用检查，全部为 test-candidate/未准入，未证明 Runtime Skill admission 或全链路运行。Guide 外部 prompt seam 与正式 required Skill 加载仍未支持。下一步由 Root 选择并冻结实际输入 SHA、真实装配并执行已授权桥接测试；结果属于局部分支，未描述为 merged/accepted。
