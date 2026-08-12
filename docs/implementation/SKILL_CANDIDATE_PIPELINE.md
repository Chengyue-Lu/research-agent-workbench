# Skill 候选发现、评估与准入计划

## 1. 目标

把“搜集 Skills”做成供应链与方法评估流程，而不是把外部目录复制进 `.agents/skills`。候选可以很多，实际安装和单次任务加载必须很少。

```text
Source snapshot
  -> metadata-only discovery
  -> quarantine
  -> method / security / license triage
  -> derive or vendor a minimal candidate
  -> trigger + boundary + with/without eval
  -> trial in one Research Mode
  -> human admission
  -> accepted registry + pinned hash
```

状态含义：

| 状态 | 含义 | 可执行 |
|---|---|---|
| `discovered` | 只记录了来源和潜在价值 | 否 |
| `triage` | 已开始逐文件方法与风险审查 | 否 |
| `reference` | 只提取设计思路，不复制实现 | 否 |
| `quarantine` | 存在网络、凭据、许可或供应链高风险 | 否 |
| `rejected` | 与当前目标不符或净价值不足 | 否 |
| `trial` | 已完成基本审查，只在限定测试中运行 | 仅隔离测试 |
| `accepted` | 已通过准入并固定版本/哈希 | 可按 Task 显式加载 |

## 2. 当前来源

首轮来源与精确版本记录在 `registry/skills/sources.json`：

- 用户提供的 `research-copilot.zip`；
- K-Dense Scientific Agent Skills；
- Academic Research Agent Skill；
- agent-research-skills；
- Anthropic Skills 与 OpenAI Skills（只作为结构和平台规范参考）。

`research-copilot.zip` 的归档 SHA-256 为 `c69471fdec7164595b5d28a613a5421d549472585d8ace0f89b745b801ebe940`。清点得到 1005 个归档条目、18 个 `SKILL.md` 和 392 个 Python 文件。该归档未执行、未安装、未把脚本复制进本仓库。

仓库提供有界、只读的静态审计入口：

```powershell
rwb skills audit-archive <archive-path> `
  --source-id research-copilot-archive-1.0.0 `
  --expected-sha256 c69471fdec7164595b5d28a613a5421d549472585d8ace0f89b745b801ebe940 `
  --registry registry/skills/candidates.json `
  --output .rwb/research-copilot-archive-audit.json
```

本次审计扫描了 647 个受支持文本文件、共 4,197,764 字节；一个超过单文件上限的 catalog JSON 被明确记为 skipped，所以报告的 `text_scan_complete` 为 `false`，不能表述成“全文件审计”。审计器不解压文件到磁盘、不导入模块、不运行脚本或安装命令、不发起网络请求，也不在报告中保存正文、命中片段或本机绝对路径。报告只包含哈希、路径、计数、边界状态和静态风险信号；信号用于人工 triage，不等同于恶意或安全结论。

外部候选与本项目派生实现严格分离。独立重写、尚未准入的包放在 `skill-lab/candidates/`，该路径不参与 Codex Skill 自动发现；只有完成准入 Gate 后，才允许以新版本和新哈希进入 `.agents/skills` 与 accepted Registry。外部未知许可文本不复制到派生包。

候选的 with/without 证据遵循 [Skill 双臂评估协议](SKILL_EVALUATION_PROTOCOL.md)：同一输入、同一 provider/model/config，分别运行 baseline 与显式加载固定 Skill 的条件，持久化收据与上下文，再进行盲评。fixture 只能验证评估器，不能替代真实前向测试。

归档内的 science skill catalog 自称含 1391 个条目及 trust/review 标签。这些是来源方声明，不是本项目的准入结论；首版只把它视为发现索引，不导入全部条目。

## 3. 候选评分维度

候选不使用单一总分自动准入。以下维度分别记录，任何硬风险都可以阻断：

1. **研究价值**：是否解决一个明确研究活动，而非复述通用“多想一步”。
2. **模式适配**：适用于实验、仿真、推导、观察统计、证据综合中的哪些模式；不要求全局适用。
3. **可验证性**：是否存在确定性检查、成功 fixture、边界/失败 fixture。
4. **增量价值**：相对基础 Agent 提示或现有平台能力是否有稳定增益。
5. **上下文成本**：元数据、主说明、引用材料和示例分别多大；未加载正文不应进入 Agent 上下文。
6. **权限与数据**：文件、网络、外部上传、密钥、服务端工具与写操作边界。
7. **可移植性**：是否绑定模型名、SDK、CLI、绝对路径或单一 Agent 平台。
8. **供应链**：来源、提交/哈希、许可、脚本、二进制、安装命令和更新策略。
9. **失效模式**：会不会扩大 Claim、隐去负结果、引入循环校核或制造伪精确。

## 4. 首轮判断

首轮优先推进：

- `experiment-design`：提炼成实验模式下的最小设计 Skill，保留随机化/功效/DoE 的确定性脚本，但需要统计假设审查。
- `papercheck`：优先提取引用定位与 Claim-Source 的确定性检查，语义正确性不由脚本宣布。
- 本项目派生的 `claim-preserving-rewrite`：已在非发现路径实现最小 Skill 和数字、引用、否定、证据强度、因果措辞的表层确定性 Gate；仍须通过真实 with/without 与语义漂移评估后才能进入 `trial`。
- K-Dense `citation-management` 与 lingzhi `backward-traceability`：先做逐文件许可、网络和脚本审计。

只作参考：

- `research-baseline-builder` 的输入/输出/样本/基线分解；
- `skill-criticagent` 的 trigger、non-trigger、boundary、with/without 测试设计；
- `thesis-audit-reviewer` 的覆盖分母、问题定位和完成 Gate；
- `scispark` 的稳定假设/评审 ID 与阶段工件契约；
- `academic-writing` 的输出模板，但必须按 drafting/review/revision 拆分，不能整体准入；
- `scientific-humanization` 的事实、数字、引用和证据强度锁定思路；原包许可未知，只保留为来源参考，不复制实现；
- `manim-agent` 的工件与渲染 Gate，但不接纳仓库克隆、依赖安装、提供商绑定或生成代码执行；
- `mcp-criticagent` 的部署/协议/行为/维护分层裁决模式，但不引入执行任意 npm 包或常驻 AI critic；
- Academic Research Agent Skill 的人工 Gate 与 Claim verification。

继续 triage：

- `giiisp-paper-search-apis` 的请求规划、失败分类和结果归一化可以提炼；外部数据出口必须经过 provider-neutral Tool Adapter 与 Data Policy 协商，不能默认绑定该服务。

隔离或排除：

- `sci-employee-deep-research` 含硬编码明文 HTTP 服务和模型名，禁止执行或直接采用。
- `giiisp-scientific-image-generation` 含硬编码明文 HTTP、凭据读取、研究内容外传、外部模型绑定与脚本执行，保持隔离；仅保留 figure spec、lineage 和质量 Gate 作为设计参考。
- `visual-deck-builder` 单个 `SKILL.md` 达 623 行，且不属于第一验证切片，排除出近期核心路线。
- `practical-course-producer` 属于课程/视频制作工具链，不是当前科研方法或完整性需求，且带来 TTS、浏览器、FFmpeg 和脚本执行负担。
- `cognitive-profile` 引入长期个人画像与隐私/上下文负担，不属于科研方法层。
- `world-threads-entry` 操作外部社交账户、身份状态和积分互动，与科研质量无关且包含外部写副作用。

至此，归档中的 18 个 Skill 入口均有独立候选记录和固定内容哈希；完整逐项记录见 `registry/skills/candidates.json`。覆盖完整不代表任何候选已安装、已执行或已准入。

## 5. 准入 Gate

进入 `accepted` 前必须同时满足：

- 许可清晰，来源与内容哈希固定；
- 无未解释安装、删除、上传、明文传输、凭据读取或任意执行行为；
- frontmatter 与 Registry Manifest 分离且字段可验证；
- 明确 trigger 与 non-trigger；
- 至少一个成功、一个边界/越界失败 fixture；
- 与不加载 Skill 的基线对照，记录质量、token、时间和错误率；
- Skill 正文与引用按渐进披露组织；
- 权限不超过 Agent Profile、Task 和 Project Protocol 的交集；
- 在至少一个明确 Research Mode 中有净收益；
- 人工做最终准入 Decision。

首版不允许 Registry 自动安装候选，也不允许候选脚本在发现阶段运行。

## 6. 与上下文架构的关系

主 Agent 只接收候选的短元数据、评估结论、冲突和下一步；逐文件审计报告留在工件中。子 Agent 只加载本次 `Skill Assignment` 的至多两个主 Skill 与一个校验 Skill。候选目录规模不会自动增加任何会话上下文。

当 Skill 说明过长、多个 Skill 重复、复核成本超过产出成本或 with/without 无净收益时，优先删减、拆分或拒绝，而不是通过更多 Agent 校核来补救。
