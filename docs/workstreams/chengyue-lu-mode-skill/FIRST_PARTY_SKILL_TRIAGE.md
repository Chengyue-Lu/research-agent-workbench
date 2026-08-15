# 一方 Skill 逐项筛选结论

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 日期：2026-08-16
- 状态：19 个入口已固定哈希并写入候选 Registry
- 范围：OpenAI、Anthropic、Google Workspace CLI 的首批选定入口

本文件把原有分组式快速判断补齐为逐入口决策。官方身份减少来源真实性核验成本，不能替代许可、权限、数据出口、上下文、Tool/Skill 形态和增量价值判断。全部条目仍不可执行；本次没有写入 `trial` 或 `accepted`。

## 1. OpenAI

固定 revision：`49f948faa9258a0c61caceaf225e179651397431`。所选目录具有逐目录许可证文件。

| Skill | Registry | 处置 |
|---|---|---|
| `jupyter-notebook` | `reference` | 下沉为 portable notebook Tool 契约；模板、清洁执行、渲染和复现检查保留，路径/安装/runner 留在 binding |
| `pdf` | `reference` | 下沉为 PDF parser/renderer/output 契约；保留 render-and-inspect，不固化库和输出目录 |
| `screenshot` | `reference` | 下沉为 screen-capture Adapter；权限、隐私、捕获范围和保存位置显式化 |
| `imagegen` | `reference` | 下沉为 specialist image Adapter；公共层只保留视觉任务和不变量，模型/API key/上传留在 OpenAI binding |
| `skill-creator` | `reference` | 作为主要 authoring baseline；采用清晰 trigger、合理自由度、渐进披露和验证原则 |

## 2. Anthropic

固定 revision：`f6656c1256d5a8adfa37db9110046ef20bac644c`。`docx/pdf/pptx/xlsx` 为限制性 source-available；`skill-creator` 为可用的开放参考；`doc-coauthoring` 的逐文件许可仍未确认。

| Skill | Registry | 处置 |
|---|---|---|
| `doc-coauthoring` | `reference` | 只吸收读者测试和作者最终责任；不复制全流程访谈、connector 或 reviewer 编排 |
| `docx` | `reference` | 仅从公开格式和本项目需求独立实现结构、渲染与版式 QA 契约 |
| `pdf` | `reference` | 仅独立实现 PDF 读取、表单、生成、渲染和布局验证需求 |
| `pptx` | `reference` | 仅独立实现 slide render 和视觉 QA；不复制受限正文或脚本 |
| `skill-creator` | `reference` | 作为 evaluation reference；吸收 trigger、no-Skill baseline 和 blind review，移除平台编排 |
| `xlsx` | `reference` | 仅独立实现公式、结构和 workbook render 检查，不作为科研方法 Skill |

## 3. Google Workspace CLI

固定 revision：`a3768d0e82ad83cca2da97724e46bea4ff0e6dbd`；仓库级 Apache-2.0。

| Skill | Registry | 处置 |
|---|---|---|
| `gws-docs-write` | `reference` | 下沉为窄 external-write recipe；要求 dry-run、确认、数据策略和 Receipt |
| `gws-docs` | `reference` | 下沉为按需 Docs API schema reference，不常驻加载目录 |
| `gws-drive` | `reference` | 下沉为按需 Drive API reference；分开 read/write，限制搜索和数据出口 |
| `gws-shared` | `reference` | 作为 Adapter safety policy 参考；保留 schema discovery、dry-run、确认和 sanitize |
| `gws-sheets-read` | `reference` | 下沉为窄 read recipe；固定范围、分页和输出上限，不继承写权限 |
| `gws-sheets` | `reference` | 下沉为按需 Sheets API reference；先解析 read/write capability |
| `gws-slides` | `reference` | 下沉为按需 Slides API reference；创建和修改属于显式外部写 |
| `persona-researcher` | `rejected` | 拒绝把 Drive、Docs、Sheets、Gmail 和协作写入捆绑成宽泛研究人格 |

## 4. 汇总与架构含义

| 来源 | `reference` | `rejected` | 合计 |
|---|---:|---:|---:|
| OpenAI | 5 | 0 | 5 |
| Anthropic | 6 | 0 | 6 |
| Google | 7 | 1 | 8 |
| 合计 | 18 | 1 | 19 |

这些条目没有形成新的科研方法 dossier 候选。它们的主要作用是：

1. 文件处理能力下沉为 provider-neutral Tool capability；
2. API 目录按需读取，不作为常驻 Skill；
3. Provider、CLI、凭据和平台路径进入薄 runtime binding；
4. authoring/evaluation 原则进入本项目 Skill 评估规范；
5. 宽泛 persona 和跨服务权限捆绑被明确拒绝。

因此下一步仍从社区批次的 6 个 `triage` 项选择最多 4 个 dossier，而不是把一方工具 Skill 加入高成本科研方法测试。
