# PR140 审查边界修复

2026-10-10；M1-010 / M2-009 / M11-008；R2；PR140 候选。用户要求根据最新 comment 修复。输入为 e938dfab320124f56bd5fc9ae047bbb9eab168f6 上 2026-10-10T14:01:45Z 的四条具体现象，原评论与 PR/review metadata 保存在私有 `pr140-review-007`。不改 Task 定义、依赖或完成状态，不合并或发行。

## 修复与验收范围

1. intake 编译必须保留人类已提供的每个预算 ceiling，包括字段省略和 delegation sub-budget；只能保持或收窄。
2. 模型不能移除人类必需 Skill 或削弱 Handoff policy，包括可选字段省略。当前不支持的 Skill/H2 路径必须在执行前停止，不能靠下游恢复已丢失要求。
3. 原 deadline 与同一个可信单调时钟覆盖 factory、冻结、Host 准备和每次 Provider/Tool 派发；禁止重开相对计时器延长权限。到期后零派发，保留实际失败/usage/未开始，不自动 retry。
4. entry 包与两个共享测试 support 模块进入 component CI 直接消费者选择，源码单独改动也选择 entry 测试；原其他组件选择、安装 smoke 和未知路径行为保持。

Root 统一执行确定性反例/正常路径、实际离线 caller→factory→Host/Receipt→formal Handoff 链、安装消费、组件规划、文档链接与 R2 预检。此次可确定性验证的修复不需要付费重跑；历史 API/账本/原件保持原来源，不冒称新代码已获 live 接受。现有累计 10M 和测试授权不变。

## 有界协作 Packet

所有实施者都不独占代码库，保留其他变更；声明互斥写域。required Skills=[]。先读 AGENTS/README、Development、Architecture、本 Packet、exact M1-010/M2-009/M11-008，再读对应目标模块和直接依赖。持久化实施摘要、精确源 hash、全部可见收发，再返回 Compact Handoff。

- Intake Profile=bounded intake constraint implementer；写域 `entry/intake.py`、新 `tests/test_entry_intake_constraints.py`；读取 intake/caller/factory/executor、Task model/Schema、handoff consumers、现有 intake/caller tests 与两个 entry support 模块。修复评论 4237860714/716，并增加使用实际 package caller 的预算/Skill/H2 省略反例。预算 20 分钟/14000 tokens。
- Deadline Profile=bounded dispatch deadline implementer；写域 `entry/workflow.py`、`entry/executor.py`、`entry/driver.py`、必要直接 runtime runner/session 调度依赖及新 `tests/test_entry_deadline.py`；读取 caller/factory 与现有 workflow/executor/driver/runner tests 和两个 entry support。修复 4237860718，共享 absolute deadline/clock、Provider/Tool 前置核验与实际 fake-clock 调用链反例。涉及公共 Core 身份或 Schema 变化时报告具体原因并停该设计；预算 25 分钟/18000 tokens。
- CI Profile=bounded component ownership implementer；写域 `tests/ci_components.json`、`tests/test_ci_components.py`；读取 `.github/scripts/ci_components.py`、现有 CI 选择测试、entry/support 模块文件名与直接 import 元数据。修复 4237860723；包括两个新 entry 回归模块。预算 15 分钟/9000 tokens。

私有输出和通信分别为 `pr140-review-007/{INTAKE,DEADLINE,CI}_IMPLEMENTATION.md` / `*_COMMUNICATIONS.md`。Workers 不运行测试、API、生产 Tool、Git mutation，不读取 Key，不创建/预占实际账本；Root 仍为唯一测试操作者。遇到写域冲突或需扩展直接依赖时先报告；禁止用移除断言、放宽权限或修改 fixture 代替修复。Root 在代码冻结后可安排有界静态复核，独立接受与 merge/release 保留人类决定。

实施确认：两个新 regression 模块均直接消费两份 entry support。H2 在当前 compact 路径的限制原来只在收尾触发，Deadline 写域同时前移 `workflow._validate_task` 的同一支持条件；Intake tests 验证要求已保留时也零角色派发，互不修改同一文件。

必要直接依赖明确为 `adapters/models/session.py`：最终 Provider/Tool 派发核验必须在 durable capture、调用方 guard 和 conformance validation 之后。首轮静态复核发现 guard 自身耗时可使新增 Runner 接口晚派发；保留首轮来源后补齐最后核验，并由 Runner 在实际调用紧邻边界记录 per-run dispatch facts，Driver 不在准入 callback 提前计数。Core Schema/Result 字段不改。Root 另更新本 workstream 阅读索引，保留历史切片。

CI 必要扩展为 `.github/scripts/ci_components.py`：两新回归直接复用七份既有 `test_*.py` helper，原 planner 在 direct-test 分支提前返回而跳过已声明的 direct maps。保留自身选择、删除 owner、unknown 和 smoke，额外消费显式政策映射；只为两新回归的实际直接 imports 增加七条 exact path 映射，不建立隐式依赖图。先保留首轮 planner/policy 来源，待源码测试退出后再编辑；Root 随后单独验收 CI 最终来源。Root 另在原 Risk Ledger 链接本轮已观测风险及候选验收。

完整 333-case 回归发现现有 `test_entry_workflow.py` 的单个 deadline-after-call 用例按 clock 读取次数模拟时间。消除旧 `setdefault` 的冗余读取后，测试实际未推进到超时。允许仅该用例把同一 mutable clock 在真实 ScriptedExecutor 返回观察后推进至 t70，保留 safe-paused 并增加 actual1/known35/held0、真实 observation 与停止事件断言；取消前零派发/零用量也加强。产品 post-call 核验不改，不加无效 clock 读取；首败原件保留，Root 复测整个 workflow 模块。

## 输出

逐条评论→修复→实际消费者→反例/正例→结果的可读验收表；保留首轮失败和修复后的来源。更新 PR140 的实现、验收和剩余风险，以及主 checkout 单一项目摘要 own-row。结构通过不构成科学或 Source/Skill/Human 接受。
