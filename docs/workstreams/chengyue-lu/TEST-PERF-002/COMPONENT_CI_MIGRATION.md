# Component CI 结果身份迁移

2026-09-27；负责人 Chengyue-Lu。PR105准备日常PR门禁切换；线上保护尚未变更。
依据[Issue87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87#issuecomment-5852428933)，
日常较小测试集合的检出能力取舍见[执行说明](COMPONENT_CI.md)。

## 固定身份

| 结果 | 含义 | 发布消费 |
|---|---|---|
| CI / test (3.11)、test (3.13) | 现有生产工作流及原义务 | legacy-ci-v1的develop push |
| CI components / CI result | PR组件或develop短smoke | 不能满足发布source-CI |
| CI checkpoint / CI checkpoint result，profile=checkpoint | 3.11全仓，手动或夜间 | 不能满足发布source-CI |
| 同checkpoint workflow，profile=release-checkpoint | 两版全仓、两版安装smoke、真实合入源治理 | 可接受v2 live核验，仍不授予发布批准 |

旧candidate结果保留原义。新汇总schema=1、contract=components-v1，含source/base/plan digest、
事件/ref/run/attempt、实际范围、producer状态和耗时。coverage为diagnostic-only，当前自动采集为not-collected。

## source-CI 与 manifest 版本

[release_source_ci.py](../../../../.github/scripts/release_source_ci.py) 保留v1六字段receipt和原
CI/develop push/固定jobs/App/attempt/suite/实时重读规则，不迁移旧存量字节。

[release_checkpoint_ci.py](../../../../.github/scripts/release_checkpoint_ci.py) 增加v2：

- 显式schema_version=2、contract_version=components-v1、profile=release-checkpoint。
- 只接受canonical ci_checkpoint.yml、相同repository、workflow_dispatch/develop/exact source。
- 必须有checkpoint-plan、checkpoint (3.11)、checkpoint (3.13)、checkpoint-governance、CI checkpoint result
  的实际成功；每个job/check/App及run attempt/suite身份均核对。
- 结果artifact匹配API SHA-256/size，内部source/profile/run/attempt及两版结果一致；写出前重读run。
- 治理入口检查真实dispatch上下文，沿用实际squash parent、关联已合并PR、reviewed tree及当前治理元数据。
  没有伪造push事件。普通、candidate、nightly绿色不构成发布checkpoint。

[release-manifest v0.2.0](../../../../schemas/v0.2.0/release-manifest.schema.json) 与v0.1.0并列。
[release_surface.py](../../../../.github/scripts/release_surface.py) 显式分版本验证和确定性投影；
缺版本、混合字段、未知profile均拒绝。v1 manifest仍为0.1.0及原六字段source_ci。

当前解释由受审source的[版本配置](../../../../.github/source-ci-contract.json)选择，不能由candidate manifest自由选。
现在仍为legacy-ci-v1。其版本/workflow/checks必须与governance-policy一致，拒绝只切一边。
[preflight](../../../../.github/scripts/release_preflight.py)保留独立pins、两次投影、完整候选比较、
保护refs和两次live观察，始终merge_eligible=false。

未来激活v2须同步active_contract=components-v1和curated_release_topology schema_version=2、
source_ci_workflow=CI checkpoint、source_ci_required_checks=[checkpoint-governance, CI checkpoint result]。
解析器已支持此组合，现有policy仍v1/dormant；两版均拒绝将activation_state改为active。
格式迁移不批准release分支、tag、main发布或具体merge。

## 切换与回退顺序

第一阶段切换 develop PR；第二阶段才处理完整 checkpoint 的默认分支部署和 source-CI v2 激活。
第一阶段保留 develop push 的旧 full/repository/source-CI 与 main 原要求，确保部署间隔仍有真实完整基线。
普通 PR 减测不必等到一次 main 发布或变更仓库默认分支。

1. 在当前 PR 上核真实 `CI components` 运行、固定 `CI result` 和修改正文后的 `governance`。
   develop metadata 已改为核组件计划和真实API工件，不再要求成功的旧全量计划；main 保留旧校验。
   新绑定是 `plan-reference-only`，不能代替失败的 `CI result`；branch/manual结果不能冒充PR检查。
2. 请求 R2 跨 owner 复核，覆盖实现、保留的反例及本切换包。审核时列明：当前旧 required 仍阻断，
   旧失败/缺失不会被修改成成功。复核和切换授权分别确认，不使用 admin 或历史例外。
3. 获授权后暂停其他 PR 的合并，回读 exact PR/base/head、有效批准、零未解决阻断、两个新检查的当前成功、
   actual develop 与完整基线，以及实际 develop/main hard/review rulesets。漂移即停止并重新生成操作包。
4. 对 develop hard ruleset 先加入 App15368 的 `CI result`，保留三个旧要求形成短期交集，立即读回。
   该交集仍可能被旧 coverage 阻断；它不是要求再跑一遍已经决定退役的旧 PR 全量。
5. 确认新检查与审批满足已审定条件后，把该 hard ruleset 的 required 集合收敛为
   `governance` + `CI result`，其余全部字段保持，读回后正常 squash merge 当前匹配的 HEAD。
   本候选的 `ci.yml` 已将 PR 触发限定为 main，合入后无需再提交停用 develop PR 旧 producer 的补丁。
   其他旧分支缺新检查时继续阻断，迁到已合入基线后运行自己的新 CI；不复用本 PR 结果。
6. 验证真实 develop push 的新安装 smoke 与仍保留的旧 source-CI。保留 v1/dormant 配置。
   第二阶段经独立接受和实际 checkpoint 验证后，才同步切 source 契约并停止旧 develop producer。
7. 回退先暂停合并，通过当前分支的显式旧 `ci.yml` 恢复入口产生真实旧检查，再恢复旧 required 并读回，
   最后撤新 required；通过正常修复 PR 恢复旧自动触发。若已进入第二阶段，连同 source/governance 版本回退。
   不改写 v2 为 v1，也不为新提交重签旧结果。

实际保护API、具体merge、source契约激活与发布批准分别需要相应授权。本实现没有调用这些写接口。
历史PR94单次例外不适用于本轮。新路线取消coverage比例阻断，但实际测试失败仍阻断。

### 可复核操作包

[ci_ruleset_migration.py](../../../../.github/scripts/ci_ruleset_migration.py) 只有 GET 和本地输出，不能修改保护。
它拒绝非 develop 专属作用域、bypass、非 strict、缺硬保护、未知 required 集合或错误 App，
只改变 required-check 列表，完整保留其他规则和条件。

```sh
python .github/scripts/ci_ruleset_migration.py --repository Chengyue-Lu/research-agent-workbench --ruleset 23305447 --output .rwb/ci-cutover
```

输出 `before.json`、`intersection.json`、`components.json`、`rollback.json` 和 SHA-256 manifest。
审核包中的快照必须在操作前重读比较；过期包不能直接执行。获授权维护者才可依上序用
GitHub ruleset PUT 接口提交对应 JSON，每次写后核整份读回，不能只看接口返回成功。
见 [GitHub ruleset API](https://docs.github.com/en/rest/repos/rules#update-a-repository-ruleset)。
本切片会保存实际仓库的只读生成结果和 hosted metadata 绑定，未调用 PUT。

## Checkpoint部署

当前default branch是main。GitHub从默认分支登记schedule和workflow_dispatch；仅合入develop不能完成登记。
部署建议随下一次受治理的 `develop → main` 发布登记该 workflow；本PR不修改main或默认分支。
实际登记前继续保留 develop 的旧完整基线，不用外部定时器冒充已部署的 nightly。
此前nightly标记实现待部署；本地profile入口可用，不作为hosted发布证据。

工作日02:30 Asia/Shanghai对应UTC `30 18 * * 0-4`。夜间checkout develop，plan记录其真实SHA，
不把默认分支run的SHA当作被测内容。仅成功完成后上传marker；输入相同不生成新执行receipt。
近期30次成功记录均未匹配或artifact已过期则再次执行，不跨提交复用结果。
[GitHub事件说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

PR不使用workflow paths过滤；aggregate always执行并核适用producer。以后启用merge queue需另加merge_group契约。
[Required checks说明](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)

## 有限验收

直接回归覆盖旧六字段/新版本、真实Git投影、版本降级、普通或nightly误作发布、错workflow/App/事件/attempt、
缺失/错误artifact、失败/取消/跳过、真实squash治理、source-owned选择、纯文档及夜间输入未变。
保留原历史反例，不重启完整闭包/witness或全业务历史实验。

各HEAD的局部及hosted结果见PR正文。新PR producer成功、兼容回归通过和迁移包可审即为本实现切片交付点；
required切换、默认分支checkpoint登记、跨owner接受与具体merge分别记录，不以实现完成代称已生效。
