# 按组件执行的 CI 候选

2026-09-27。负责人 Chengyue-Lu；Audit ID TEST-PERF-002。**当前是隔离分支候选，尚未 hosted 执行或 activation。** 新方向依据 [Issue87 最新路线](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87#issuecomment-5852428933)：普通反馈采用单一基线 Python、短 smoke、组件测试；完整验收放到明确 checkpoint。未登记跨组件回归和其他版本差异可能延迟发现，候选不承诺与旧全量检出等价。

旧三组配对实验、完整输入闭包/独立选测 witness、global90/critical95/90/changed100/100 比例证明不再是本候选上线的前置条件；这一取舍来自最新 Issue 方向。旧证据保留原身份，现行生产 CI 和 required checks 在正式迁移前仍保持原义。迁移和发布边界见 [结果身份迁移包](COMPONENT_CI_MIGRATION.md)。

## 当前入口与执行方式

| 入口 | 当前行为 |
|---|---|
| [ci_components.py](../../../../.github/scripts/ci_components.py) | 纯路径计划；组件整组、直接修改测试、已登记共享 fixture 直接消费者；增删/重命名考虑两侧 |
| [run_component_ci.py](../../../../.github/scripts/run_component_ci.py) | 从 exact Git base/head、merge-base、候选 policy 和库存生成计划；消费时重算；复用现有测试计时记录，不调用旧图/witness/coverage 选择机制 |
| [ci_component_smoke.py](../../../../.github/scripts/ci_component_smoke.py) | 已安装 wheel 的短 smoke；fresh checkout 外目录、隔离解释器、120 秒总预算；失败即停并保留 JSON |
| [ci_components.yml](../../../../.github/workflows/ci_components.yml) | workflow `CI components candidate`；仅 `feature/ci-component-flow` push 与 manual；只读 contents 权限 |

候选结果名为 `CI components result (candidate)`。plan 和 execute 均须成功，aggregate 使用 always；失败、取消、缺失或 skip 不被当作成功。候选没有替换旧 `CI`，没有启用 pull_request、develop 定时任务或 required 保护，也不提供 release source-CI。

当前 planner 登记 15 个职责组件与 12 条共享 fixture 直接映射。没有归组的路径保留 `unknown_paths`，选择最近登记组件/现存同名测试及短 smoke，不自动升 FULL。CI 自身变更运行小回归；旧图/witness 测试文件仍存在并留在 checkpoint 库存。脚本自身 direct-test 映射的最后补充由协调方整合，不能把较早测试回执自动套到后续修改。

| 当前 profile 名 | 代码中的执行范围 | 当前验证边界 |
|---|---|---|
| `component` | 默认 Python3.11 的组件业务测试；依赖/构建变化追加3.13安装与 smoke，业务仍3.11 | 已有下列本地有限证据，hosted 未运行 |
| `integration-smoke` | 安装、短 smoke 与固定短回归 | 参数已实现；不是已上线 develop 流程 |
| `checkpoint` | 全部候选 test_ 模块，单一3.11 | 入口已实现；本轮未运行全仓或夜间任务 |
| `release-checkpoint` | 全部候选 test_ 模块与3.11/3.13安装 smoke | 入口已实现；未完成发布专属验收/授权，不是发布资格 |

计划/结果当前 schema 为 `0.1.0`，authority 是 `candidate-unaccepted`。计划标注 coverage diagnostic-only，结果明确 not-collected；本轮未收集 coverage。上表是实际候选命名，迁移包中未来版本/profile 的建议仍待 activation 包统一决定。

手动检查候选的入口如下；exact HEAD 必须已含候选 policy，以下不是本轮执行回执：

```sh
python .github/scripts/run_component_ci.py plan --base <exact-base-sha> --head <exact-head-sha> --profile component --output .rwb/plan.json
python .github/scripts/ci_component_smoke.py --python <fresh-wheel-environment-python> --output .rwb/smoke.json
<fresh-wheel-environment-python> .github/scripts/run_component_ci.py run --plan .rwb/plan.json --output .rwb/result.json
```

wheel 构建/新环境安装由 workflow 在 smoke 前完成；smoke 脚本自己不安装。纯文档走文档依赖和适用文档检查，不承担产品 smoke。测试结果不跨提交复用；plan digest 仅校验一致性，不提供独立授权。

## 已有本地阶段事实

| 证据 | 结果与口径 |
|---|---|
| planner 独立目标回归 | 初始12项 PASS；只运行分类器自身测试，没有执行被选择业务集合 |
| smoke runner 控制 | 3项 PASS，unittest 报告0.207秒；只验证正确负例、timeout、缺解释器的停止/报告行为 |
| root 构建 wheel | exit0，2.857秒 |
| root 创建 fresh venv | exit0，3.659秒 |
| root 安装 wheel[test] | exit0，6.174秒 |
| 首次真实 installed smoke | 失败；`SchemaValidationError.path` 不存在，首步停止；原 smoke.json 原样保留 |
| 修正后的真实 installed smoke | 改用 `pointer`；CPython3.11.16、8步 PASS，9.469秒；smoke-corrected.json 独立保存 |
| root 有界回归 | 6 runner + 10 documentation + 7既有定向回归，共23项 PASS、0失败/错误/skip；测试内部6.084秒，完整进程6.444秒 |

8步包括 installed import 与 Schema 正反例、Runtime资源、schema CLI、research-state命令注册、no-skill项目创建/检查/Task+Profile验证、真实 CLI 拒绝非法 timestamp。负例必须得到预期 exit1 和 timestamp 诊断，任意失败不能冒充通过。CLI 用 `python -I -m research_workbench`，没有声称验证生成的 console launcher。

七个既有回归覆盖 POSIX hash 顺序、路径/缺失/hash 守卫、disabled provider、缺可信发布期望、文档种类/Schema/dispatcher 和真实 research-state CLI。它们是 Issue 指定既有故障的定向控制，不是全业务、全平台或发布安全证明。

本地数字来自不同有界步骤，不相加冒充端到端 hosted 用时，也不推导相对旧 CI 的加速比。runner/YAML 静态检查通过，三项 review issue 已闭合。映射补轮保留19个已有脚本及 suite runner 的明确直接测试、registry 的职责子组；新增源码即使已落在组件内，也选其现存同名测试。没有递归调用图。

分类器当前15个方法：最终规则运行时12项通过，3个仓库成员测试因测试用库存过窄失败；修正为 Git tracked inventory 加新候选模块浅层清单后，只补跑这3项通过。失败原样保留。这也移除了测试辅助代码对整个 checkout 的递归扫描，避免遍历 workflow 内的安装环境；hosted 新目标仍须实际执行完整候选集合。

## 收尾与剩余事项

首个真实候选 push `a5a104a` 的 [run36294739603](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36294739603) 在安装 smoke 失败，aggregate 也正确失败。wheel 构建及安装已成功；smoke 的 `Path.resolve()` 跟随 Linux venv 解释器符号链接，改用了没有该 wheel 的 base Python。修正为保留 lexical absolute path，并新增真实 POSIX 符号链接回归；Windows 跳过这个特定平台用例。失败原身份保留，新提交仍需自己的 hosted 执行。

此候选停止于源码、有限回归和材料可审阅：当前未运行 hosted、nightly、全仓 checkpoint 或多版本完整业务；没有 commit/push、保护变更或发布操作由本记录任务产生。后续若开展候选真实 workflow 验证，应先冻结最终源码/映射并保留 exact source 身份与实际结果，不重启旧全闭包研究。

required-check 与 source-CI 迁移按独立文档 prepare/accept/activate/rollback；当前材料不要求立即实施 source-CI v2。R2审核、具体合并与发布批准继续由既有制度决定。Task revision51、拟归档 A-20260927-010 的本地草案只用于审阅范围和证据索引，尚未建原生 Trace 或改写项目 Task 权威。
