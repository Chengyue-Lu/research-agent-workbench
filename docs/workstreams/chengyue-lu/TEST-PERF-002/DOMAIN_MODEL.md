# CI 领域与消费者边界盘点

TEST-PERF-002 / Issue #87；2A diagnostic；owner Chengyue-Lu。
盘点基线：`171d4654f88e926f239cdf25bc8168109b81f391`。
机器可读材料：[domain-model.json](domain-model.json)。

## 用途与字段

八个领域用于把 changed fact 路由到具名维护边界，再讨论具体 consumer 的必要证明。
领域不是测试执行单元：命中一个领域不表示应运行其中所有测试，也不表示可排除其他领域。
这份登记和每项派生诊断均为 `execution_authority=false`，`pilots` 暂为空；
现有 exact-base policy、外部 witness、worker、aggregate 和 integration baseline 继续决定执行。

`source_patterns` 定位实现，`test_patterns` 定位审查相关测试，`input_patterns` 包含资源、
配置、文档和 helper 路径。模式使用仓库相对 POSIX 路径：精确路径或 `*` / `**` 通配。
模式只用于诊断路由，不能成为 skip allowlist；重复命中按并集展示，不取第一个命中。
工具使用 `fnmatchcase`：大小写敏感，`*` 和 `**` 均可以跨 `/`，不是 shell 的分层 glob。
未命中、无法解析、mode/链接变化和未知动态输入应具名报告 unknown，并保留充分执行路径。
每个模式命中都必须保留字段来源，以免将 helper、实例数据、实现误当作同一类依赖。

`consumer_ids` 仅引用现有 [impact policy](../../../../tests/ci_impact_policy.yaml)
中的四个审查记录；不复制 pins、不生成新的安全排除凭据。
空列表表示尚未登记独立的 consumer record，不表示没有 consumer。
现有记录的来源、未闭合条件见 [Consumer contracts](CONSUMER_CONTRACTS_V1.md)。
owner 是领域协调与审查路由；文件与语义责任仍依 [DEVELOPMENT](../../../DEVELOPMENT.md)，
不能由这份诊断表重新分配。

## 领域与内部契约

| 领域 | 应分别审查的 consumer / subcontract | 现有依据与必须保留的交叉 |
| --- | --- | --- |
| `ci-governance` | planner/checker executable、selection witness、coverage authority、metadata、ordered runner | 选择权与覆盖权不同；固定 aggregate、external witness 和 exact target 由现有规则执行 |
| `research-core` | Kernel/IO、Protocol/Method、Capability/Skill、Context/Task、M4 admission/promotion/Claim、Research State、Trace | accepted `claim-local-function` 与 `projection-local-function` groups 仍有各自范围；parser/hash、authority 和初始化可能真实跨域 |
| `validation-catalog` | 输入实例读取、kind dispatch、各 registry 关系、schema/version inventory、capability root scan | 引用 `validation-document-instances`、`validation-schema-catalog`、`validation-capability-root-scan`；catalog 全量成员与跨文档闭包保持 |
| `provider-adapter` | wire、conformance、session、CLI 调用链 | 复用 accepted `provider-wire` → `provider-conformance` → `provider-session` → `provider-cli` groups；不能把 live 与 local evidence 混用 |
| `evaluation` | manifest/qualification、protocol、overlap/comparability、overlay、harness plan/preflight、execution/replay | M5 execution 调用 Execution/Provider；测试 helper 与科学效果验收分别登记 |
| `execution` | Bundle/View、Host、generic closeout、Skill extension、baseline transport、cold file replay | View/Skill 语义与执行事实分属具名 owner；共享 Trace、fixture 与初始化保留 |
| `release-runtime` | 各 CLI command、scaffold、installed resources、portable build、public source closure、release source checks | 引用 `cli-git-head-observation`、`validation-schema-catalog`；package inventory 和公开文档是真实输入 |
| `documentation-archive` | Markdown 链接/表面、治理字段、具名 archive/hash/ref 闭包 | 复用 accepted `documentation` group 作为已有依据；运行时消费的文档必须额外路由，归档暂无排除授权 |

这八组是首轮协调粒度，不要求后续业务模块按八组重写；减测激活必须落到 consumer 与 invocation，
不能把现有 FULL 换成固定“整域全测”。M4、M14、M5 等身份仍沿现有 TASKS/owner 边界。
原有 [模块盘点](MODULE_AUDIT.md) 的历史计数与本文基线不同，不直接沿用其数量作为当前 inventory。

本次 Git inventory 路由校验覆盖 115 个生产/CI/build Python 文件、98 个 `test_*.py` 模块、
10 个测试 helper/runner/initializer；这三类没有未路由项，模式均有当前 tracked 文件命中。
7 个源码文件和 6 个 helper 的重复命中按实际共享入口保留。此结果只证明登记可导航，
不证明输入闭包完整，也不把静态测试模块数当作实际执行 case 数；其他数据和未来新增路径仍需报告 unknown。

## 实际读取确认的边界

- [SchemaCatalog](../../../../src/research_workbench/validation/schemas.py) 对指定 version 目录的
  `*.schema.json` 全体成员逐个读取；默认构造先创建
  [RuntimeResources](../../../../src/research_workbench/resources.py)。这是实际全 inventory 工作，
  不能用“只改一个 schema”声明取消。若以后分区，应作为独立行为保持变更接受审查。
- [documents](../../../../src/research_workbench/validation/documents.py) 仍有跨领域 semantic
  dispatcher。某个输入实例经过该 reader，不证明每个调用 reader 的测试都消费该实例；
  caller roots、间接 refs、增加/删除/重命名和 alternate paths 仍待逐 invocation 绑定。
- [test_documentation](../../../../tests/test_documentation.py) 扫描仓库 Markdown 链接并检查 target
  存在；target 可以是 JSON、源码或目录。非 Markdown target 删除可能影响文档测试。
  同模块还调用 [public_surface_helpers](../../../../tests/public_surface_helpers.py) 验证公开文件与
  build closure，因此 `docs-only` 不是这些实际输入的充分说明。
- [harness_execution_fixtures](../../../../tests/harness_execution_fixtures.py) 直接使用 Provider models、
  execution ports 与 [harness_fixtures](../../../../tests/harness_fixtures.py)；
  [baseline_fixtures](../../../../tests/baseline_fixtures.py) 继承
  [system_evaluation_fixtures](../../../../tests/system_evaluation_fixtures.py)。这些真实 fixture 交叉
  被同时列入 evaluation/execution inputs，尚未宣称 helper 生命周期已经闭合。
- CLI、package `__init__.py`、默认资源构造和全局 catalog 保持共享入口地位。当前记录只描述
  两个 CLI Git 命令，不覆盖其他命令、环境和 executable lookup。

## Coverage 与 smoke 独立讨论

领域匹配没有 coverage scope 或 smoke 布尔值。每一候选 consumer 应分别给出：

| 义务 | 后续证据问题 | 本轮处理 |
| --- | --- | --- |
| Behavioral | 实际改变哪个行为、调用或生命周期；是否影响其他 consumer？ | 只报告候选 routing，accepted plan 照常执行 |
| Coverage | executable/critical semantics、coverage authority 是否改变；范围能否可靠界定？ | 沿现有 [coverage policy](../../../../tests/coverage_policy.yaml)，不复制阈值或新建 exclusions |
| Package smoke | packaging、安装入口、runtime assets、public build closure 是否被消费？ | 保留真实跨域；文档/领域名称不自动推导 false |
| Repository smoke | schema、registry、全仓 validation closure 是否变化？ | 保留 catalog/registry 实际闭包，未知继续充分执行 |

风险等级仍是审查强度。它既不替代上述事实判断，也不由领域表改写。
已接受 ordered B → C−B、critical 整文件证明、changed outgoing branches 与 repository baseline
仍由原有质量规则执行，诊断数量下降不能宣称这些证明已完成。

## 首个 docs/archive invocation pilot

2B 应先使用 #65、#68、#84、#86 的 exact Git snapshots，保存 base/head/target、模式、
policy/witness、测试/helper/environment 和真实执行结果。自然 PR 持续加入，但绿色结果本身
不足以证明安全排除。另看 [验收矩阵](CI_REPLAN_ACCEPTANCE.md) 中 C01–C05、C17–C20。

| 待闭合项目 | 必须取得的证据 |
| --- | --- |
| 文档输入实例 | 每个测试/validator 实际读取哪些文件、目录成员和非 Markdown link targets；新增/删除/重命名均验证 |
| Archive 消费者 | 验证的是哪一份 archive、哪个 hash/ref 闭包、使用什么 invocation；不能用 Trace 实现的全部消费者代替 |
| Runtime 与 public crossing | 被 runtime 读取的文档、发布清单和 installed catalog 成员明确保留，并有真实坏输入失败对照 |
| 精度对照 | 相关失败的 consumer 必须被预测选中；同类型但无关实例必须能具名解释潜在跳过 |
| Helper 与环境 | helper/import/fixture 生命周期、入口工具、Python/OS/依赖、目录生成与清理绑定 |
| 独立授权 | accepted record 与 candidate-independent witness 覆盖 exclusion；candidate 不能改 selector 和声明来自证 |

Shadow 输出应比较 predicted selected/skipped IDs 与 accepted 执行的 failures、coverage 和 smoke，
同时保存 unknown 新增范围及成本；报告中每个 skip 始终是候选诊断。单个真实漏检立即扩大/阻断，
无需凑齐多个案例；通常的减测优化再以独立真实场景、稳定语义与配对实测成本证明进入激活 review。

2A 交付仅为 inventory 与 gaps，2B 为 shadow 回放，2C 才是独立 witness/Gate 激活 PR。
本轮不改业务 M Task 的实现，也不把仍在审查的其他 PR 当成已接受的排除依据。

## 离线工具

[`ci_domain_audit.py`](../../../../.github/scripts/ci_domain_audit.py) 验证已提供 plan 的
exact Git 事实和 accepted minimum，读取 Git inventory，并把每个变更的 mode、对象 ID、
old/new bytes hash 与所有领域路由并列输出。Gitlink 不读取仓库之外的对象，保留 unknown。
输出路径不得覆盖 plan/model/receipt 输入。模型 digest 与包括治理器在内的 producer hashes
绑定报告；模型仍只是显式提供的诊断草案。

```sh
python .github/scripts/ci_domain_audit.py --plan ci-plan.json --output ci-domain-audit.json
```

可另传 `--receipt execution-test-results.json`，显示具名失败/缺证据、模块 case 耗时合计和
缺失耗时 ID。离线文件不能建立 GitHub 来源认证；该工具不将“接收到 receipt”宣称为执行证明。
2A 不产生 candidate selected/skipped，也不估算缩时；这些比较与实际 coverage/smoke 对照在 2B 交付。
