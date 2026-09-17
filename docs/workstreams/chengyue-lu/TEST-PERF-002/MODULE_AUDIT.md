# 业务模块、测试和成本盘点

TEST-PERF-002；2026-09-16；[规范评审稿](CI_REPLAN.md)。
基线 `b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22`；原始数据与 producer 见
[Attempt](../../../../work/TEST-PERF-002/A-20260916-005/RESULTS.md)。

## 1. 口径

机器盘点全部 tracked `src/`、`tests/`、CI/build Python 的 AST、imports、函数长度及关键调用形态；
结合架构、M Task/实现导航、coverage/impact policy，并对下文的共享入口及慢测试读取实际实现。
这不是对每个函数语义、每个测试必要性或科学正确性的全面认证。

- 99 个生产 Python 文件，34,294 个物理行（含注释/空行）；92 个测试模块。
- AST 发现 1,341 个 `test_*` 方法，不能等同 unittest 执行数量；hosted discovery 实际执行 1,331 项。
- 8 个 tests 非 `test_*` Python 文件，包含 runner 和 initializer；不是 8 个独立 fixture。
- coverage policy 2.2.0：52 个 critical 文件（含 CI）、83 个 coverage-suite 模块、34 组 negative acceptance。
- 已接受 impact groups 只有 documentation、Provider 四段链、Claim 与 Projection 局部函数，共 7 组。
  因而大部分业务还没有独立的、可用于减测的可信契约边界。
- 下文静态 import reachability 含 package initialization；既不是实际调用次数，也不是安全删测清单。

## 2. 业务边界总表

源码路径均相对 `src/research_workbench/`；测试名相对 `tests/`。分组是本轮拟采用的 CI 契约族，
不改变 M Task 身份、代码 owner 或功能状态。数字来自 exact base 的 inventory。

| 契约族 / M 线 | 源码规模 | 主要输入输出与真实消费者 | 应保留的验证边界 / 下一步 |
| --- | --- | --- | --- |
| 基础对象与解析 / M1、M8 | kernel 2 文件/132 行；contracts 4/345；io 1/46 | object identity、typed records、parse/hash → 各业务 validator | `test_kernel`、`test_contracts`、critical helper；共用 parser/hash 改动可能真实高扇出，局部模型修复按明确消费者 |
| Protocol / Method / Authority / M8 | protocol 5/1,343 | Mode/Action/Profile/Matrix → Resolution / Task binding | mode_actions、method_resolutions、protocol_profiles、decision_authority；区分单条记录与 registry/authority 算法 |
| Capability / Skill lifecycle / M2、M7、M9 | capability 11/3,590 | Requirement、Supply、Resolution/Snapshot、Need/Lifecycle、Projection | resolver/ceiling 正反例、projection/admission；拆分 runtime supply 和 maintainer evolution，保留 no-Skill independence |
| Context / Task / M1、M3 | context 3/1,069；tasks 2/368 | bounded context、permissions、task/handoff/assignment | context branches、task/handoff、assignment 消费者；读写范围及 Human Gate 变化要查下游，文档措辞不等价于 runtime 变化 |
| Artifact / Provenance / M4 | artifacts 7/2,851 | source admission→promotion→Claim localization→Run reconstruction | admission/promotion/claim/run tests；数据实例改动验证实例，算法改动验证契约；fresh replay 和 source/hash 对抗保留 |
| Research State / M10 | research_state 5/1,941 | State、Attempt/Failure、Method Trace→bounded Gate | state/attempt/method trace/phase_c_gate；区分 closed-set reference helper 与启动真实新进程的 Gate |
| Evaluation / M5 | evaluation 10/3,270 | Manifest、qualification、protocol、overlap/comparability/overlay→eligibility | 资格/相等性/人类决定正反例；单领域比较逻辑不自动触发 Provider transport；科学效果验收独立 |
| Provider / Model / Session / M6 | adapters 14/3,683 | provider-neutral request、wire normalization、capability、error→session result | 现有四段 Provider contract；wire leaf、session loop、conformance 分开。mock/local transport 不替代 live conformance |
| Execution / M6、M11 | execution 13/5,289 | Bundle→View→Host→事实/Receipt；baseline transport→file replay | 细分 bundle/view、host、generic closeout、Skill extension、baseline transport/replay；authority、freshness、实际 Tool 使用和 cold replay 均保留 |
| Trace / Observability / M3、M11 | observability 3/2,560 | events/messages/refs→Index、validation result、transcript | producer、redaction、closure、replay、properties 分契约；单份归档输入不等于 Trace 实现改变 |
| Validation / 跨域 | validation 14/5,315 | schema + typed document set + cross refs→diagnostics | schema引擎、kind/shape、各 registry关系、总 dispatcher 分层；新 family 增加注册与有限集成测试，不自动把所有 family 测试相互依赖 |
| CLI / Scaffold / M1、M14 | cli 1/1,957；scaffold 1/235；包入口 2/8 | args→业务调用/生成项目文件 | command-family tests、help/exit/error兼容、少量完整 CLI 链；README 输出名不能形成输入边 |
| Runtime / Packaging / M14 | resources 1/292；另有 build backend 和 catalog | pinned installed resources、公开入口→checkout 外安装消费 | runtime_resources/portable_build/package smoke；目前全 manifest 验证是实际耦合，分区需独立业务契约变更 |
| CI / Governance / M0、Issue48 | `.github/scripts/`、runner、两份 policy、workflows | exact Git事实/可信政策→plan→execution receipts→aggregate | planner/dependencies/checker/witness negative acceptance；选择权变更 full bootstrap；成本自身纳入 profiling |
| Schema / Registry / Skill / docs 数据面 | 以 Git inventory、runtime-resources 与 schema refs 为准 | 版本 identity、数据 bytes、manifest 或明确 docs/evidence | 同一文件格式可承担不同职责；M12/M13 仍按实际获授权输入处理，不因 reservation 创建 runtime 测试义务 |

责任人沿 DEVELOPMENT 的具名边界：Provider/API/session/执行事实由黄毅参与审核；Method、Capability、
Skill、Trace policy、Research State 由路诚钺维护；跨域 extraction 和 CI authority 按 R2 cross-owner review。

## 3. 已定位的结构性传播点

| 入口 | 当前事实 | 对后续 bugfix / 小型重构的影响 | 处置建议 |
| --- | --- | --- | --- |
| `validation/documents.py` | 1,858 行；`validate_documents` 调用全部 domain validators；静态 import closure 达 75 测试模块 | 一个 family 的局部修改可能借总入口扩到其他 family | 抽出现有 kind / registry validators；总入口保留注册、闭包与跨域 integration；先保持 API/错误顺序 |
| `observability/trace.py` | 1,832 行；recorder、sanitize、message、Index、validator 同文件；closure 达 75 模块 | metadata、producer 与 validator 无法自然局部选测 | 先划 recorder/codec/validation/provenance 契约，再按 import compatibility 拆分；不可放宽 capture-gap 或 hash refs |
| `validation/__init__.py`、`evaluation/__init__.py`、`execution/__init__.py` | eager re-export 导入多个领域；execution 包同时暴露 generic 和 Skill closeout | 只导入一项 API 也进入共享初始化图 | 区分初始化依赖与调用依赖；后续 API-preserving extraction 需循环导入、cold import、monkeypatch、序列化对照，不直接忽略 initializer |
| `cli.py` | 1,957 行，多个 command family 与 schema/runtime 路径 | 小命令 bugfix 和 baseline/packaging 测试相互扩散 | 抽出 command handlers 和 parser family，保留入口、help/errors/exit code 和真实 CLI smoke |
| `RuntimeResources.__init__` | 遍历 manifest 每个 entry、读 hash、目录闭集、manifest schema；随后可再 validate_catalog | installed resource 改动可能真实影响每个默认 Runtime consumer | 先计量构造频次，评审 immutable catalog/session reuse；TOCTOU、字节替换、路径别名、symlink/junction、不同 roots 必须失效 |
| `SchemaCatalog._load` | 每次 fresh 读取/解析全部 schema、建引用 registry；schema 自检已有 bytes/checker cache | cache 已减少自检，但整 catalog 初始化仍发生 | 不重复做已完成的自检 cache；评估 scoped `$ref` closure 或显式只读 catalog 注入，保留实际文档每次验证 |
| `tests/test_baseline_replay_integrity.py` | 直接引用另一个 test 模块的 TestCase 构建真实 A2 archive，随后按 case clone/reset | transport test 文件变动连带 replay；test-as-helper 隐藏生命周期 | 将 ScriptedProvider/fixture builder 独立出来；重用 seed，维持每个 case fresh 文件、篡改和 rehash 反例 |
| `tests/execution_fixtures.py` | 16 个静态测试消费者；Skill helper 11 个；system evaluation helper 7 个 | helper 小改有真实跨模块影响 | 按 stable input contract 拆成组合 builder，避免每个分支都启动完整场景；共享可变实例不可直接缓存 |

这些 extraction 是后续独立实现切片，不在本次规范稿中修改产品。文件拆分本身不承诺缩时；
必须同时证明契约边界和真实 plan 的范围收敛。shared semantics 改变时扩大测试仍是必要行为。

## 4. PR84 实际执行成本

来源：[run 35092826503](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35092826503)。
head `dfe3165a90ebcef99d107aef8e790bf7abc0c13f`；target `7bc70fab34f947ff0e506d8a6b9450dba099589d`；
plan `b2a8eb54ba3b2fcc3d2f5028ecf70152d45695f1be726ffdbd8a8295f0896b34`。
其产品源码与本次基线一致，PR 只改 docs；完整 CI 已 success。

| 执行 | Python | 实际项数 | suite wall | case duration 总和 |
| --- | --- | ---: | ---: | ---: |
| plain full | 3.13.15 | 1,331 | 496.96 s | 479.90 s |
| ordered coverage execution | 3.11.16 | 1,331 | 950.24 s | 905.74 s |

这是不同 Python/runner 的观测，不能把差值直接当作 coverage 单项 overhead。
suite wall 含 lifecycle 等开销；模块列为 case duration 求和，不含所有 class/module setup。

| 测试模块 | cases | 3.11 coverage case 秒 | 3.13 plain case 秒 | 已读实现后的优化方向 |
| --- | ---: | ---: | ---: | --- |
| ci_plan | 73 | 109.03 | 50.75 | 大量真实 Git fixture；保留 planner/witness 对抗，减少纯规则断言重复建仓，必要真实 Git 场景独立 |
| baseline_replay_integrity | 19 | 98.69 | 42.95 | 已有 class seed/reset；进一步量化重复 replay/rehash，保留完整篡改证据与 fresh process |
| baseline_execution | 18 | 97.98 | 69.31 | Tool 使用前后与 provider-return 多时间点都是独立安全边界；优先复用不可变输入构建，不能删除这些点 |
| skill_execution_closeout | 33 | 68.17 | 33.83 | generic 与 Skill-specific 断言分层，保留 actual binding/failed-use/replay |
| evaluation_overlay | 19 | 42.16 | 19.28 | 比较 typed字段/closure 规则与完整评估链；同一必需路径具名 checkpoint 化 |
| generic_execution_closeout | 13 | 33.18 | 15.67 | 共享 Bundle/View/Trace 构建成本归因，保留 generic no-Skill E2E |
| skill_closeout_review | 10 | 28.75 | 13.72 | qualification/review predicates 与真实 gate integration 分开 |
| scaffold | 12 | 25.03 | 12.95 | catalog 初始化与命令行为分别计量；输出文件名误依赖独立修复 |

前三个模块共 305.71 s，占 coverage case 时间约 33.8%。这比笼统削减所有测试或旧排行榜更适合确定优先级。
单项最慢的 plain case 为 baseline 的四个 availability checkpoint（19.60 s）；
这些 checkpoints 的时机各不相同，当前没有证据证明可删除。

## 5. PR84 的选择精度验收缺口

9 个结构化归档输入触发 unclassified→full/repository/smoke；依赖图 91/92，81 条代表路径含资源回退。
本地 exact base/head 回放确认 hosted 的 selection/obligations/reasons。

仅诊断性修正分类仍选 91/92（coverage none）；关闭通用资源回退仍有 89；只保留 Markdown seeds 仍有 46。
`README.md→scaffold` 的输出名匹配、`ACTORS.yaml→trace→import` 的实例/代码混淆需要一并处理。
这些消融不是安全排除依据。

当前 `test_new_markdown_is_fast_but_document_data_is_full` 明确期待 docs YAML 为 full，
说明旧模型的验收与本轮目标不一致。重新规范必须同步更新这种预期，并增加真实数据消费者失败反例。

## 6. 本轮结论与待补测

完成了全生产文件的结构 inventory、全测试模块的导入关联、真实 full/coverage 成本归因和关键共享实现审查。
尚未逐项证明所有 tests 的最小性，也未对上述 extraction 做新旧 runtime 等价实验。
下一步先用可信契约覆盖 Provider/M4/M6/M11/M14 与 docs/证据典型场景，再逐族迁移；
需补测的 fixture/setup/instrumentation 时间、有效故障检测与缩时目标由配套验收稿明确，而不靠承诺分钟数收口。
