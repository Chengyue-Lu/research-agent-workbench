# Component CI 结果身份迁移包

2026-09-27。负责人 Chengyue-Lu。状态：**文档候选；未 activation**。依据 [Issue87 路线说明](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87#issuecomment-5852428933) 与 [CI 重规划](CI_REPLAN.md)。本包将新执行集合、required checks 和 release source-CI 的含义一起迁移，不要求重新建立完整输入闭包或选测 witness。

本次只读现有实现并提出有序操作与直接契约用例；没有运行测试、CI、提交、推送或保护 API。路线已接受较低的日常覆盖强度；组件成功不是旧全量流程的等价证明。以下 prepare/accept/activate/rollback 是未来操作说明，不是已经完成的事件。

## 1. 现状与必须保留的解释

| 对象 | 当前约束 | 迁移边界 |
|---|---|---|
| 分支 required checks | 已有方向交接记录 `governance`、`test (3.11)`、`test (3.13)`，App15368，strict | 本轮未重新查询保护；activation 当时读取两分支/rulesets 的实际值并保存原配置 |
| 生产 workflow | `.github/workflows/ci.yml`，名称 `CI`；PR 内容事件、main/develop push、PR manual revalidation | prepare 不改此 workflow，不用旧 check 名包装更弱执行 |
| 新候选 | 独立 workflow `CI components candidate`；仅 `feature/ci-component-flow` push 与 manual | 结果名 `CI components result (candidate)`；不 required，不提供发布 source-CI |
| 旧 source-CI | `release_source_ci.py` 固定 workflow path/name、develop push、exact source SHA、App15368、run attempt/suite/job/check 身份 | 旧 receipt 继续按原规则解释；不补写新 profile，不根据新检查名重解释 |
| 旧 source jobs | 三个 required 名，加 plan、documentation、repository_smoke、两版 compatibility、coverage-quality(3.11)、两版 package-smoke | 当前 attestor 要求这些 producer 全部成功；仅换 REQUIRED 三名字不足以迁移 |
| 发布消费链 | release_preflight 两次 live attest，并检查 source/parent/projection/candidate 和竞态；`merge_eligible=False` | 保留实时观察、精确来源、projection、独立 pins、批准和发布权限 |

`governance-policy.json` 的 curated release 仍 dormant；`check_pr_governance.py` 同时硬编码其字段集、schema_version=1、CI 和旧 checks。`release-manifest.schema.json` 的 schema_version=0.1.0、workflow=CI、source_ci.additionalProperties=false。新字段不能直接塞入旧形状，也不能只修改 policy JSON。

## 2. 最小的新结果契约

建议将**格式版本**与**执行 profile**分开，初版只需一个小版本表和明确字段，避免把显示名称当执行强度。字段名在实现审核中一次冻结；本包建议新 CI 结果采用 `schema_version=1`、`contract_version=components-v1`，至少写入 `profile`、source/target SHA、event、选中组件/测试、适用 jobs、每 job 结论、首个失败 producer、coverage 的 diagnostic 属性。

| profile（建议固定值） | 证明含义 | 可否作为 release source-CI |
|---|---|---|
| `component-pr` | Python3.11 短 smoke 与适用组件/契约；纯文档只有适用文档检查 | 否 |
| `develop-fast` | 短安装/公共入口、真实集成身份核验 | 否 |
| `nightly-baseline` | 有新产品/依赖内容时的单一基线 Python 全仓 | 否；不是承诺版本/平台验收 |
| `release-checkpoint` | 精确 source 的完整基线、承诺版本/平台兼容、真实离线安装和发布专属断言 | 可以进入 source-CI 核验；仍不授予发布批准 |

候选结果保留其候选 workflow/name 身份，不能凭自行填 `release-checkpoint` 升级。metadata 事件只更新廉价 governance；内容结果绑定实际内容 SHA，不为正文/标题变更重跑业务。未来固定日常名称拟为 `CI result`，checkpoint 使用不同 aggregate 名（建议 `CI checkpoint result`）；最终名称与触发面由 activation 包一起冻结。

aggregate 始终执行 `always()`，读取计划和真实 needs/job 状态：应运行而 missing/skipped/failed/cancelled/timed_out 均不通过；仅计划明确不适用才接受 skipped。计划缺失或无法解析也失败，不把 upstream failure 引起的 skip 当不适用。不依赖 workflow 总体结论单独证明 profile。

## 3. source-CI v2 与旧 receipt

1. 保留原六字段 source_ci 形状及旧 schema/reader 的解释分支，称 `legacy-ci-v1`；这个名称是阅读标识，不回填历史字节。原保存 receipt 从来不是当前发布授权，仍须 live recheck。
2. 为新 source_ci 显式加 `schema_version=2`、`contract_version=components-v1`、`profile=release-checkpoint`；保留 repository、source SHA、workflow、run_id、conclusion、required_checks。新增身份至少含 workflow_path/id、event/ref、run_attempt、result artifact digest；observation 保留 suite/App/job/check IDs。required_checks 仅表示该版本的固定 aggregate/治理义务，不冒充旧两版 test checks。
3. release-manifest 用新的显式 schema revision（建议 0.2.0），保留 0.1.0 分支原意和历史字节；generator/validator 按版本选择，拒绝缺版本的新形状、未知 profile/version、混合旧新字段。无需迁移旧存量 manifest。
4. v2 accepted workflow/path/id/aggregate/profile/job 集来自受审的版本契约，不能由候选 manifest 或调用者自报。candidate、component-pr、develop-fast、nightly-baseline 成功均不能满足 release-checkpoint。
5. v2 可明确允许受信 checkpoint workflow 的 `workflow_dispatch`，但只接受真实 run.head_sha=预期 source、develop ref、相同 repository、完整 producer 身份及 artifact source/profile/job 记录。它与“PR required check 是否认可”是两种消费规则，不能放松旧 v1 的 push-only 分支。
6. checkpoint 必须在该 source 上重做现有 merged-source governance（实际 squash parent、关联 PR、reviewed tree、当前元数据）。新增入口应验证 checkpoint 的真实事件/ref/source；不能伪造 GITHUB_EVENT_NAME=push 来调用旧 producer。源码身份、当前保护与 source ancestry 检查继续保留。
7. run 观察前后重读 attempt/suite/status，preflight 前后重读保护 refs 与完整观察；各 producer 失败或结果 artifact 缺失/错版本/错 source 均不发布成功 receipt。新版本仍输出 `merge_eligible=False`。

这只需要版本分支、profile/job 身份表和直接检查，不增加全仓语义证明。新 reader 的“支持解析”与“允许用于当前发布”分开；保存 v1 回放能力不允许在 v2 激活后以旧弱/过期规则降级当前请求。

## 4. Prepare → Accept → Activate

**Prepare（当前切片）**

1. 保存当前 source-CI/schema/policy/测试版本，以及两分支保护待 activation 读取的清单；旧 CI 和 required 名完全保留。候选只在指定新分支 push/manual 执行，没有 release token 或写权限。
2. 冻结组件计划/runner/aggregate 与结果 contract/version/profile；准备 source-CI v2 reader、checkpoint producer、release manifest/generator/preflight/governance 的同一兼容迁移包。这个文档任务不代写那些受保护文件。
3. 新旧 source receipt 测试用具名 synthetic API rows 和现有小 Git fixture；保留原测试/旧六字段断言，新用例仅验证版本/profile/身份及失败处理。不重跑旧历史 PR 矩阵，不要求全输入 witness。

**Accept（可完成的有限验收）**

4. 完成第 6 节直接契约用例及候选一个真实 push 端到端作业，记录 exact SHA、实际集合和用时；manual 可验证入口，但不是 required 生效证明。审阅普通执行覆盖减少的代价和回退包，按现行 R2/cross-owner 或人类明确单 PR 例外处理。
5. acceptance 必须分开记：组件候选实现通过、source-CI v2/checkpoint 迁移是否就绪、哪些分支允许切换。可先接受组件候选并结束实现切片；未就绪的 release 路径不借此获授权。

**Activate（另行明确决定后）**

6. 先部署可同时报告新旧结果的生产触发配置；旧 producer 继续运行，新生产 `CI result` 在受保护分支适用的 PR/push 事件真实报告。候选名不充当正式名；避免 candidate 与生产/checkpoint 同名、同 SHA 竞争。无 workflow 级 paths 过滤；若启用 merge queue，触发契约另须覆盖 merge_group。
7. 在旧保护仍有效时，验证当前 PR 所需 head/test-merge SHA 的新结果确实关联该 PR 且被 required 机制识别；metadata/文档/组件/依赖的合法不适用和失败状态已覆盖。只看 branch/manual 绿色不够。
8. 由获授权维护者读取并保存当前 protection/rulesets；短暂停止自动合并/切换期间的合并操作，不改变审批、strict、App15368、权限和拓扑。先把新 `CI result` 加入旧 required 集，形成 `{governance, test (3.11), test (3.13), CI result}` 的短期交集；读回确认无旁路。
9. 在新旧都有效且 v2 release 消费链就绪后，再将 develop 的 required 收敛到 `{governance,CI result}`。旧生产名称从未被重解释。main 若尚未完成 release profile/专属义务切换，保持原 checks 与 producer；不把 develop 的普通 fast 规则复制给 main。
10. 新 required 读回和当前候选观察正确后，才停止该分支旧 producer。两分支分别记录切换点；跨 API/代码不能假设原子，因此保持“先可报告、再加要求、后删旧要求、最后停旧 producer”。若中途失败，保留已有有效旧要求并停止。
11. source-CI v2 acceptance 和相关保护变更不等于 curated-release activation、具体 PR merge 或发布批准。M14 activation_state/人类授权、release candidate 专属验收、当前 source/parent 等继续按现行规则独立处理。

GitHub 文档明确：workflow paths/branch/message 过滤可使 required Pending；失败依赖引起的 skipped job 需要 always 汇总。文档在 workflow_dispatch 的 PR-head 示例中写 “they do not satisfy a required status check in a branch ruleset.”，此规则针对 workflow jobs 创建的 checks，不泛指外部 App；最终以实际 PR 关联与 required 认可为验收。[Required checks 官方说明](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)

跨 workflow job 名必须避免歧义；切换时保持既有审批和限制，不临时关闭 required checks 来消除 Pending。[Protected branches 官方说明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## 5. Rollback

activation 前：候选失败保留失败身份，修对应原因或停止候选，旧门禁不受影响。activation 后：先暂停合并，恢复保存的旧 producer 配置并让当前适用 source/PR 真实产出旧检查；在新要求仍有效时加回旧 required，读回后才移除新 required。不能先删除新要求再等待旧 job 出现。

若旧 producer 暂时无法恢复，则保持合并阻断，明确报告恢复缺口；不借回退授权绕过保护。source-CI 当前版本选择随同受审契约回退，不把 v2 快速结果转写成 v1。若新 manifest/receipt 已生成，保留原版本和失败记录，重新生成对应旧 profile 的真实证据；不得改写历史 receipt。具体发布批准不随任何回退继承。

## 6. 直接契约测试清单与结束条件

| 用例 | 必须观察到的结果 |
|---|---|
| 原 v1 API rows/六字段 receipt/0.1.0 manifest | 原解释不变；原身份/竞态/权限负例保留 |
| v2 checkpoint 正常 producer | 同 source/版本/profile/事件/App/attempt/suite/job/result digest 通过，merge_eligible=false |
| candidate、component-pr、develop-fast、nightly-baseline 同 SHA success | release consumer 拒绝；不因绿色 aggregate 升级 |
| 缺版本/未知版本/profile；旧新字段拼接；名字同但 workflow/path/App 错 | 拒绝且不产出成功 receipt |
| 应运行 job missing/failed/cancelled/timed_out/skip；计划或 artifact 缺失/错 source | aggregate 与 source consumer 失败；指出首个 producer |
| 计划合法不适用、纯文档、metadata-only | 按 profile 判定；文档不虚称产品 smoke，多版本空集不虚称通过 |
| rerun 竞争、最终状态变化、source/parent/protected-ref 漂移 | 原实时重读守卫仍拒绝 |
| 新正式触发和保护模拟 | eligible 事件真实报告；新旧短期交集切换、读回、回退顺序；不调用真实保护 API |

有限结束点：上述实现直接检查、一个真实候选作业、迁移包审核与已授权 activation 完成即结束；没有自动追加全业务/full witness 的义务。真实 release-checkpoint 的全验收只在发布候选/既定 checkpoint 执行，不用本迁移文档触发一次。

## 7. 后续需共同修改的受保护文件

本轮只读八个源/配置：ci.yml、release_source_ci.py、governance-policy.json、release-manifest.schema.json、check_pr_governance.py、release_preflight.py、test_release_source_ci.py、test_release_preflight.py。

实现迁移必须协调这组 identity/schema/consumer 文件及新 workflow/result runner；`release_surface.py` 是 preflight 的实际 projection/manifest 消费入口，本轮因八文件上限未读，须在同步实现前核其版本分支。相应 schema 注册/随包资源与 source-CI caller 若受新版影响，应明确列入同次授权范围，不能靠放宽旧 schema 自动通过。当前任务未修改它们，也未修改保护、工作流或 release authority。
