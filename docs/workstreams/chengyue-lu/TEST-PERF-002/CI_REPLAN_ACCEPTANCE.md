# CI 重规划：迁移顺序与验收矩阵

TEST-PERF-002 / Issue #48；PROPOSAL；2026-09-16。
依据：[规范](CI_REPLAN.md)、[模块盘点](MODULE_AUDIT.md)。
本文件给出可独立 review 的实施切片，不将规划项写成已完成的 M Task，也不授权本次合并或发布。

## 1. 实施顺序

| 阶段 | 交付 | 进入下一阶段的条件 |
| --- | --- | --- |
| P0 规范与盘点 | 统一当前目标、module inventory、真实 PR corpus、质量/精度/成本指标 | 具名 owner 评审输入类别、契约边界、例外和成本口径；用户已认可方向，P1 首版处于 Draft 审查 |
| P1 可信契约与 shadow planner | 扩展现有 base policy，分类统一、typed dependency；旧计划继续控制 CI，新计划仅报告差异 | PR84 与每类正反例通过；所有减测差异有依据；shadow 中漏选为阻断，不自动接受缩小 |
| P2 witness 与 Gate 接入 | 支持新契约的外部可信 witness、plan/receipt版本、aggregate义务校验 | 先完成可信执行根的独立 review/登记；candidate 不能自行变更根来验证自己；新旧版本不兼容时明确阻断 |
| P3 业务模块逐族迁移 | 每个契约登记 source/input/test/helper，必要的小型 API-preserving extraction | Provider、M4、M6/M11、M14、数据/文档逐族通过精度和故障矩阵；未迁移边界保守兜底 |
| P4 必需测试成本优化 | fixture 生命周期归因、场景合并、catalog初始化、选择性计量或已证明隔离的 batch | cold/warm、顺序污染、进程与负面检测无回归，现有 ordered B/C 证据完整；实际 runner 成本下降 |
| P5 跨提交证据复用评估 | 独立输入闭包/环境密钥、可信 receipt 和失效实验 | 另行 review；P0–P4 收益不依赖此阶段；integration 保留完整新鲜基线 |

涉及 CI authority 的实现仍按 R2 风险处理。
每个实现 PR 只接受一个可闭合边界；最终验收依据统一规范，避免每个 PR 自行追加一套互不一致的规则。

先修统一分类与 typed inputs，再登记契约。业务拆分与 selector 减测不要在同一 PR 相互证明：
结构迁移先保持旧公共行为并通过现有充分测试，后续已接受边界才可用于减测。

## 2. 必需 acceptance corpus

每个 case 保存 exact base/head/target、changed modes、policy/witness版本、期望契约、必需/禁止的
无关测试集合、理由和实测成本。真实 PR 需使用 immutable snapshot；重放到新基线须另给绑定与差异。
列表中的测试上限是具名集合约束，不是任意测试数量阈值；不存在“选到 20% 就停止”的算法。

| Case | 变化 | 应证明的范围 | 配套故障 / 反例 |
| --- | --- | --- | --- |
| C01 PR84 archive | docs/workstreams 中 Markdown、JSON/YAML/JSONL、局部 attributes | 文档/governance/本归档闭包，coverage none；无关 Provider/Host/baseline及安装测试不得入选 | 篡改 archive hash/ref 必须被本归档验证发现；换成执行脚本不能豁免 |
| C02 同语义不同目录 | 同一 evidence 在合法 work/docs archive roots；增删/重命名 | 保留对应引用和目录语义，义务只因真实消费变化而改变 | 目标目录被 runtime scan 或 installed catalog 消费时必须扩大 |
| C03 同名输出 | 修改 nested README；生成器把 README 当输出名 | 不应因输出名选入 scaffold/CLI；真实文档消费者保留 | 生成器改为真实读取该文件后，坏输入必须使被选中测试失败 |
| C04 docs 是输入 | 修改明确由 runtime/checker 读取的 Markdown | 真实消费者、输入类型与 closure | 常量期望故意改错，验证 selector 仍选中实际 failing consumer |
| C05 PR65 类测试变更 | test-only + reviewed consumer fingerprint refresh | 变化测试/下游；coverage none、无无关 smoke；risk独立 | 同时改 planner executable，则必须 authority bootstrap |
| C06 Provider leaf | serialization/parsing 函数体小 bugfix | 既有 Provider contract 和必要下游；双 Python + impact | 保留坏 wire/error mapping、边界逃逸与动态加载反例 |
| C07 M4 leaf | Claim localization / projection 的已接受局部修改 | 对应契约及 impact；无关 transport/evaluation 排除 | wrong hash、定位偏差和越界反例不能消失 |
| C08 M6 transport | bounded request/Tool availability 逻辑修复 | transport契约、资格/权限/actual fact边界；必要closeout integration | 使用前、Provider返回、Tool返回失效；不能用只测成功路径缩时 |
| C09 M6 file replay | receipt/creation/use ordering 局部修复 | replay/hash/closure正反例与必要producer→replay集成 | cold process、禁止重调Provider/Tool、backfill、rehash伪造仍失败 |
| C10 M11 split | generic/Skill closeout 同契约结构调整 | old/new API和角色绑定；generic no-Skill及Skill扩展各自闭合 | shared helper或初始化变化不能藏在“搬文件”中 |
| C11 小型跨文件重构 | move/rename helper并更新import | old/new消费者并集、API、初始化、序列化、副作用顺序、impact | 删除旧消费者/修改re-export/全局状态时扩大；AST不等于行为等价 |
| C12 新 Skill | candidate docs/data、published projection、runtime assets 分别变化 | 各自的结构/资格/发布/安装消费者 | candidate夹带脚本、authority drift、读写越界；不能靠目录名隐藏执行 |
| C13 Schema/Registry | 单一schema字段、`$ref`、索引/版本 | schema及实际注册/资源闭包；当前whole-catalog依赖保留 | 删除引用、旧version恢复、恶意路径、未知kind，保证未以局部化放松闭包 |
| C14 Shared fixture | 某一领域builder修改 | 真实helper消费者；无关fixture族排除 | 共享可变seed被污染、case顺序互换、并行拷贝隔离错误 |
| C15 纯 metadata | workflow注释、AST不变注释、普通审阅指纹 | 语义证明后的独立义务 | YAML类型、mode、coverage pragma、entrypoint/import变化不能被豁免 |
| C16 覆盖权威 | root/threshold/exclusion/critical inventory/negative semantics | repository；改源码同时impact | 下降阈值、漏critical、坐标漂移、missing module均阻断 |
| C17 选择权威攻击 | candidate同时修改selector与其bootstrap/verify | 外部固定根发现变化、FULL bootstrap、真实执行证据 | candidate将自身改动判docs；伪造plan/receipt/digest；缺失job仍阻断 |
| C18 未知与高扇出 | dynamic root/escaped callable/symlink/gitlink/import init | 明确fallback、真实consumer保留 | 解析失败或不认识路径不得变成空集合；负面scope不能静默缩小 |
| C19 integration | develop/main/release push | full双Python、repository及完整smoke基线 | stale base/target、cancel/missing/skip、旧receipt不能过aggregate |
| C20 同 plan 去重 | B、C相交，含setUpClass/module state | 实际唯一执行、原B顺序/生命周期、C−B独立追加 | poison state / lazy import / teardown / inherited IDs / retry差异均检测 |

先固定 C01–C05 和 C17–C20 的真实 Git 正反证明，再迁移业务族。不能只用最小玩具 fixture 宣称真实
模块已局部化；C06–C14 至少各有一个真实业务 snapshot、正确修改与故意错误的配对样例。
故意错误探针只在隔离测试中存在，不能合入业务 develop。

## 3. 质量、精度和性能分别验收

### 质量

- 既有 behavioral / integration / adversarial identity 保留；合并场景有逐条断言与反例映射。
- global 90%、critical 整文件 95/90、changed lines/outgoing branches 100/100；impact/repository 分别核验。
- PR metadata、candidate contract/fingerprint 与 candidate selector 不能降低可信 minimum。
- worker/aggregate 对 exact target、inventory、结果、环境及完整 receipts fail closed。
- 不将 fixture-only、工程CI、coverage或机器Gate升格为 Human acceptance、live efficacy 或 release authority。

### 精度

- corpus 中所有已证明有影响的 contract 必须选中，所有已证明无关的 contract 不得被通用名称/reader误选。
- 每条fallback归因到具体unknown，显示其新增测试与成本；同一unknown不再用扩展名特例反复绕过。
- C01 必须消除与文档/归档无关的业务 full；仅 coverage=none 或 FOCUSED 不算达标。
- 至少分别观察 source-only、test-only、fixture-only、registry/schema、mixed diff、rename/delete、新consumer。
- static/dynamic关系中的未知部分不在数量阈值处截断；缩范围的每条结论要有可复核的契约或失败对照。

### 性能

首先建立同一 Python、OS、依赖和 runner 类型的 paired baseline；至少 3 次 fresh execution，报告中位数、
范围、suite/job/setup与总compute。小样本不声称可靠 p95；p95 需积累更多 hosted runs。
selection 比较必须同一 Git事实；Python3.11 coverage与3.13plain的差值不直接归因instrumentation。

| 类别 | 拟验收目标 |
| --- | --- |
| 文档/已界定归档 | 无关业务case为0、coverage none、无无关smoke；真实PR hosted critical path较当前至少降低70%作为首轮工程目标 |
| 已接受局部bugfix/小型重构 | 每个代表契约较同环境full baseline的critical path至少降低50%作为工程目标，且无范围漏选 |
| 必需integration/full | 首先归因前3热点与setup；每个优化切片报告配对收益，整体目标在控制环境baseline后确定 |
| planner本身 | 记录cold/warm AST与Git成本，不能以优化选择器为名引入比测试更重的全仓分析/多层自检 |

百分比是待验证目标，不是本轮观测结果或减测阈值。达不到时不能删必需case：复核真实耦合与最慢工作，
给出具体未收敛原因；性能未达标就不能宣称该类“缩时完成”。

## 4. 测试合并与结构调整的证明包

每个拆分/合并包含：原case→新scenario/checkpoint映射、setup与前置输入、assertions/error codes、
进程边界、old/new test discovery IDs、negative faults、变化coverage坐标与exact-head结果。
至少验证 cold run、既有顺序、反向/指定污染顺序；只有 isolation 已证明的 batch 才讨论 sharding 或跨提交复用。
纯文件拆分不能利用新critical文件的空coverage或丢失旧exclusion坐标获得通过。

对慢test先做 runtime profile，区分真实domain判断、catalog构造、文件拷贝/hash、Git/subprocess与framework开销。
“调用一次即可覆盖”不能用于删掉不同输入/失败时机；“每个反例重新初始化整个仓库”也不是不可变要求。

## 5. 切换与回退

新协议先在 shadow 模式持续比较；激活前要有可信根、schema、worker、aggregate版本兼容说明。
出现漏选、未绑定输入、环境/receipt不一致时，阻断或恢复到原有充分执行路径；保留失败证据。
只因精度目标未达标不自动删边，继续旧full并记录本轮迁移未完成。
回退不得依赖被 candidate 同时修改的代码；保持 old plan reader 或显式拒绝不支持版本。

用户认可后已开始 [P1 shadow 首版](SHADOW_V1.md)，以 Draft PR 审查；每个切片按现有review/CI合并要求推进。历史PR的绿色结果不授权
新trusted root，也不证明本轮新协议已有效。
