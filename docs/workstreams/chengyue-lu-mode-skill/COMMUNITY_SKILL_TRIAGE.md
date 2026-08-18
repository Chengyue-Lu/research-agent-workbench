# 社区 Skill 人工筛选结论

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 日期：2026-08-16
- 状态：已确认并写入候选 Registry
- 范围：首批来源中除 OpenAI、Anthropic、Google 以外的 35 个 `SKILL.md` 入口

本文件记录人工语义筛选结论，不表示安装、执行、`trial` 或 `accepted`。外部下载仍保存在忽略 Git 的 Attempt 隔离区；固定路径、内容哈希、能力、风险和机器可读 Decision 见 `registry/skills/candidates.json`。

## 1. 处置含义

| 人工处置 | Registry 状态 | 含义 |
|---|---|---|
| 改写候选 | `triage` | 进入详细 dossier；仍须许可、脚本/网络、trigger/non-trigger、困难任务和上下文成本评估 |
| 核心参考 | `reference` | 只提取架构、方法或失败模式，不原样加载 |
| 下沉 | `reference` | 转为 Tool capability、运行时不变量、Task 模板或确定性 checker |
| 暂缓/排除 | `quarantine` / `rejected` | 高风险项保持隔离；净价值不足或形态错误的 Skill 不进入当前路线 |

## 2. GitHub `awesome-copilot`

仓库由 GitHub 官方托管，但社区贡献不自动视为 GitHub 官方撰写。固定 revision：`a80885b76044550770f60f360f8a0e5ae3524a31`；仓库级 MIT。

| Skill | 处置 | 后续动作 |
|---|---|---|
| `audit-integrity` | 核心参考 | 保留失败证据和有界重试；移除自评分与持续记忆循环 |
| `build-evidence-map` | 改写候选 | 对齐本项目 Claim/Evidence/Unknown schema，形成最小证据图 Skill |
| `context-map` | 下沉 | 合并到 Task 读取范围与上下文申请模板 |
| `convert-excel-to-md` | 下沉 | 转为文档 Tool capability，写入位置和格式限制显式化 |
| `convert-pdf-to-md` | 下沉 | 转为 PDF parser/renderer capability；无 OCR 时明确失败 |
| `convert-word-to-md` | 下沉 | 转为 Word parser capability |
| `md-to-docx` | 下沉 | 转为文档输出 Tool，并要求渲染验证 |
| `microsoft-skill-creator` | 核心参考 | 只吸收稳定本地核心与动态官方查询的分层模式 |
| `mini-context-graph` | 排除 | 它是持久知识子系统，重复 Context/Artifact/Provenance 架构 |
| `what-context-needed` | 下沉 | 转为缺失输入和读取扩展请求模板 |

## 3. K-Dense `scientific-agent-skills`

固定 revision：`43a3e619a1dd8f053abdeb258c87ce81c53b424f`；仓库级 MIT。

| Skill | 处置 | 后续动作 |
|---|---|---|
| `citation-management` | 改写候选 | 拆成发现、元数据校验和引用完整性；移除 Provider 假设 |
| `experimental-design` | 改写候选 | 建立实验单位、随机化、重复和区组核心；增加学科路由与 Human Gate |
| `literature-review` | 核心参考 | 提取 protocol、screening ledger 和 PRISMA 记录；移除固定服务和强制制图 |
| `peer-review` | 改写候选 | 保留授权、保密、方法/统计/伦理分层；排除自主编辑裁决 |
| `research-lookup` | 核心参考 | 提取 provider-neutral query/source packet 和 counterevidence 契约 |
| `scientific-visualization` | 改写候选 | 拆分 figure integrity core 与绘图 Tool binding |
| `scientific-writing` | 核心参考 | 提取证据绑定、作者责任和确定性检查，不保留全论文大流程 |
| `statistical-analysis` | 核心参考 | 先按分析家族拆分；不得用通用表替代学科方法审查 |
| `statistical-power` | 改写候选 | 绑定已批准设计、效应量来源、聚类/流失假设和敏感性分析 |

## 4. lingzhi `agent-research-skills`

固定 revision：`9e6c085d65e313e475e921fdfe795ac11eb7589e`；未检测到许可证。所有可用结论只能支持独立设计，禁止复制文本或脚本。

| Skill | 处置 | 后续动作 |
|---|---|---|
| `atomic-decomposition` | 核心参考 | 独立设计有界的数学—代码追踪，不要求一一对应 |
| `backward-traceability` | 核心参考 | 用稳定 provenance ID 替代论文数值到代码行的脆弱链接 |
| `citation-management` | 隔离 | 存在硬编码凭据文件和命令暴露风险，不执行、不复制 |
| `data-analysis` | 排除 | 统计路由过度简化，固定四 reviewer 成本过高 |
| `experiment-design` | 核心参考 | 只保留 ML 消融规划问题模式 |
| `literature-review` | 排除 | 多 persona 固定轮询昂贵且不能替代系统综述方法 |
| `literature-search` | 隔离 | 存在硬编码凭据/绝对路径；搜索契约必须独立设计 |
| `math-reasoning` | 下沉 | 改为 theory Task action checklist，不作为全局 Skill |
| `novelty-assessment` | 排除 | 不接受二元创新认证；只允许输出最接近工作与剩余不确定性 |
| `paper-revision` | 核心参考 | 独立设计 concern-to-action revision ledger，保留研究者裁决 |
| `self-review` | 排除 | 相关 persona 与平均分不能构成独立评审证据 |
| `symbolic-equation` | 隔离 | 等待真实符号回归案例、安全 evaluator、单位与数值验证契约 |

## 5. Academic Research Agent Skill

固定 revision：`41c611c2e36461596c0c072e7641f9ddba251be8`；仓库级 MIT。

| Skill | 处置 | 后续动作 |
|---|---|---|
| `research-agent` | 核心参考 | 拆出 Reality Gate、Claim state、pilot authorization 和 plan-depth limit；不加载全生命周期总管 |

## 6. Superpowers

固定 revision：`b36e0829c6d0140e93cfef2ca599b1b07d4a7797`；仓库级 MIT。

| Skill | 处置 | 后续动作 |
|---|---|---|
| `systematic-debugging` | 核心参考 | 作为工程根因分析方法，不扩展为科研全局规则 |
| `verification-before-completion` | 下沉 | 转为运行时不变量和验收契约，以新鲜验证证据约束完成声明 |
| `writing-skills` | 核心参考 | 提取 baseline failure、pressure scenario 和 wording microtest；按风险与方差分配重复次数 |

## 7. 结果与下一 Gate

| 结果 | 数量 |
|---|---:|
| `triage` 改写候选 | 6 |
| `reference` 核心参考 | 13 |
| `reference` 下沉项 | 8 |
| `quarantine` / `rejected` | 8 |
| 合计 | 35 |

dossier 候选池的六项是：

1. GitHub `build-evidence-map`；
2. K-Dense `citation-management`；
3. K-Dense `experimental-design`；
4. K-Dense `peer-review`；
5. K-Dense `scientific-visualization`；
6. K-Dense `statistical-power`。

这六项不是同时重写清单。下一 Gate 先完成重叠、学科适用、权限/Tool、上下文成本和可验证性 dossier，再最多选择两个进行独立最小重写或困难任务测试。`research-agent` 与 `writing-skills` 只作为架构和评估方法参考，不作为两个重写名额。
