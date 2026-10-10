# 架构与模块文档校准记录

任务：AUDIT-RWB-DOCS-003；Profile：bounded documentation worker；required-Skills：[]。
日期：2026-10-07。声明基线与分工来自 DOCUMENTATION_TASK_PACKET；本轮未运行 Git 核对、产品测试或真实执行。

## 阅读范围

通读本次输入：仓库 AGENTS.md、README.md、本工作流 DOCUMENTATION_TASK_PACKET.md；
随后通读以下拥有文档。较长输出按章节补读，未递归历史工作区。

| 文档 | 实际范围 |
|---|---|
| docs/ARCHITECTURE.md | 全文 |
| docs/DEVELOPER_ARCHITECTURE_MAP.md | 原§1–20全文；编辑后检查新接点和用语 |
| docs/PROJECT_CHARTER.md | 全文 |
| docs/modules/README.md | 全文 |
| docs/modules/01-RESEARCH_KERNEL.md | 全文 |
| docs/modules/02-PROTOCOL_AND_MODES.md | 全文 |
| docs/modules/03-AGENT_RUNTIME.md | 全文 |
| docs/modules/04-SKILL_SYSTEM.md | 全文，包括独立补读§7–10 |
| docs/modules/05-TASK_AND_HANDOFF.md | 全文 |
| docs/modules/06-CONTEXT_GOVERNANCE.md | 全文 |
| docs/modules/07-ARTIFACTS_AND_PROVENANCE.md | 全文 |
| docs/modules/08-VALIDATION_RISK_AND_GATES.md | 全文，包括补读§7–9 |
| docs/modules/09-ADAPTERS_AND_INTEGRATIONS.md | 全文，尾部补读 |
| docs/modules/10-OBSERVABILITY_EVALUATION_COST.md | 全文，分段读取 |

通过拥有文档明确引用核对：

- ADR-0016：前115行，重点§决定1–7的方法控制面、概念正交、Human和Trace边界。
- ADR-0019：前160行，重点双环、权威表、Snapshot/授权分离、验证profile与兼容边界；未重写ADR历史。
- ADR-0011：第15–43行，H0/H1/H2、受控读取与工作留痕；其他历史背景仅关键词定位。
- ADR-0010：关键词定位执行槽位、隔离会话及平台可选语义；不把历史API优先措辞覆盖最新portable baseline。
- 源码仅先做文件/public-function元数据发现，再读直接接口：
  capability/supply.py 330–383、440–459；execution/runtime_bundle.py 581–632；
  execution/execution_view.py 335–398；execution/host.py 429–492。
  recovery.py、observability/trace.py仅函数metadata定位；未深读其实现。
- 对 entry 目录仅检查是否存在；此基线目录不存在。因此未把独立PR140候选代码写成共享基线已有入口。
- 未读取rawlogs、Key、生产账、私有oracle、其他Agent工作目录或不相关历史正文。

## 问题与实际修改

| 原问题 | 修复 | 保留的必要限制 |
|---|---|---|
| 架构从Question/Mode/Task开始，用户入口和规划职责不清 | 补新需求/既有材料→Protocol/Task/Method/Requirement→冻结→执行→接收/接续→Human接点 | 草案不批准、缺失保持未知，既有材料不自动合格 |
| 职责、模块、Profile、会话和Skill易混淆 | 架构/章程/模块03、README与地图分开定义，职责允许合并会话 | 不增core Role identity；每次AI调用有职责指令，Skill可选 |
| 主Agent看似固定委派 | 明确主执行按独立工作价值及Protocol/Task决定0..N子Task | 委派、递归、并发、预算和写范围仍受原契约约束 |
| 子API已返回易被称为接通 | 写明消费实际工件refs、失败、限制、冲突，不能只收成功标记 | callback、fixture、会话数量不证明自动链路 |
| Guide与主执行接续边界不清 | 独立只读Main State/显式refs；回答不自动回传或写状态 | 建议需正常接收或Human决定后采用 |
| 地图旧成熟度/任务状态/数量与历史Gate重复且漂移 | 原661行地图压为183行逐跳producer/artifact/consumer/启用条件及契约导航 | 状态只链接STATUS/TASKS，方向/Gate只链接ROADMAP |
| 模块缺输入/输出和触发条件 | 10模块开头补接点，模块README增加横向接点表 | 研究和维护外环按Task启用，不强制科研DAG |
| no-Skill默认示例要求legacy Skill-bound Handoff | 默认Task改为引用检查报告；旧Handoff/Receipt字段和示例退到兼容链接 | generic Receipt不证明通用Handoff格式适配已完成 |
| 模块04/07/09/10夹杂旧实现日志 | 删除已实现/未来实现等重复快照；promotion细节收束到稳定边界和契约链接 | 不删原实现/历史证据，不弱化资格、Human或Source限制 |
| 模块09伪接口易被视为实际API | 对Bundle/View/Host使用真实public函数名，并注明省略参数与显式producer | 工具多轮不能借一次Driver掩盖多个请求；Skill metadata不证明加载 |
| Mode组合默认例混入候选theory | 改为两个formal Mode组合，移除未核定relation例 | 不新建Mode或Schema词汇 |

## 验证范围

仅执行文档静态检查：14份拥有文档全部相对Markdown文件目标存在；公开架构/章程/模块中
旧M任务DONE/PARKED/BLOCKED快照、当前已实现/本PR及本机路径搜索无命中。rg无命中的exit 1是预期。
未检查所有fragment锚点、未运行产品/CLI/API/Tool测试；Root负责最后统一文档和公开闭包检查。

核心保留：唯一Supply selection owner；Requirement/Report/Resolution/Snapshot责任；
Runtime Bundle→View→Thin Host portable baseline；View不重选；无fallback；最严权限/数据/副作用/预算交集；
planned与actual分离；Receipt slice-only；Human authority；Skill可选Maintainer外环；Phase C/Topic5独立Gate。

## 剩余项与待决

- 本轮没有提出新的core Schema、identity、Mode routing、Human或Runtime ownership决定，故无需额外架构批准。
- 实际入口/动态多会话/Tool或Skill加载/结果消费桥的开发与live验证仍按其独立Task和资格执行；本次文档修改不闭合它们。
- generic无Skill Handoff格式适配与Research State/Method Trace语义接受仍回到权威状态和原Gate，不能被文本或离线结果覆盖。
- 其他worker负责TASKS/ROADMAP/STATUS、公开阅读面与implementation；本窗口未修改这些拥有面，Root最后合并校准。

## 总审后修正：Skill Assignment边界

Root指出current projection/View/Skillcloseout并不要求Assignment。本窗口根据新增直接读取
execution/skill_facts.py 71–128与skill_closeout.py的public函数/字段metadata修正所有拥有面：Assignment只
属于legacy Skill-bound兼容缝；当前extension由合法Projection/Supply/Snapshot/View锁、actual consumption、
Trace和closeout闭合。Skill reader的metadata/pin检查不证明SKILL.md正文已加载，实际调用者须独立取证。
模块05Task YAML明确为字段示意，不能冒称完整可执行输入；Root负责随后Schema实测与最终全局检查。
