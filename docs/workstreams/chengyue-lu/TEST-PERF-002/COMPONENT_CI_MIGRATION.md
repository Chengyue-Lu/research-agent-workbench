# Component CI 结果身份迁移

2026-09-27；负责人 Chengyue-Lu。PR105已实现可切换的producer/consumer，未activation。
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

1. 旧required仍有效时部署新PR/develop producer，核真实PR关联、合法无smoke、组件/依赖范围和失败汇总。
   branch/manual绿灯不能替代真实PR检查；metadata编辑不重跑内容。
2. R2审核通过后，获授权维护者保存实际develop/main保护；保持strict、App15368、审批、线程、权限与拓扑。
   先加入新CI result并读回，形成短期交集。
3. 确认v2兼容、当前版本选择及checkpoint部署边界后，再将develop required收敛为governance和CI result。
   最后停止该分支旧producer。失败即保留有效旧要求并停止切换。
4. main保留原要求，直至独立接受发布checkpoint/专属义务，不把日常component成功复制成main发布资格。
5. 回退时先暂停合并，恢复旧producer并为当前source/PR产出真实旧检查，再加回旧required并读回，最后移除新required。
   同步回退source契约/governance版本，不改写v2为v1，不重签旧receipt。

实际保护API、具体merge、source契约激活与发布批准分别需要相应授权。本实现没有调用这些写接口。
历史PR94单次例外不适用于本轮。新路线取消coverage比例阻断，但实际测试失败仍阻断。

## Checkpoint部署

当前default branch是main。GitHub从默认分支登记schedule和workflow_dispatch；仅合入develop不能完成登记。
维护者需另行接受默认分支上的workflow部署方式，本PR不修改main或默认分支。
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