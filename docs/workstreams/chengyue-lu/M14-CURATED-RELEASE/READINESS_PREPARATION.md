# M14-005 readiness preparation

当前接续：许可与 readiness preparation 已通过 [PR #78](https://github.com/Chengyue-Lu/research-agent-workbench/pull/78)
于 `e5827a1` 合入；M0-007 为 DONE，M14-005 仍为 BLOCKED。远端规则后续由
[PR #79](https://github.com/Chengyue-Lu/research-agent-workbench/pull/79) 分为 main/develop hard/review 四层：
hard 为 23305447 / 23305460，无 bypass；review 为 23192001 / 23192054，仅 Chengyue-Lu 的 PR-only 例外。
下文保留 2026-09-14 准备阶段的部署与验证快照；当前实现接续见 [source-CI 准备](SOURCE_CI.md)。

- 责任人：路诚钺（`Chengyue-Lu`）；风险 R2；Task：M0-007、M14-005。
- 分支：`feature/m14-005-readiness`；integration base：`develop`。
- 本轮工程基线：`f7a9715ed35787d3326283c22f834b1514c5c88c`，仅用于开发和演练定位。
- 授权：[Issue #57 推进路径](https://github.com/Chengyue-Lu/research-agent-workbench/issues/57#issuecomment-5635297678)
  及维护者 2026-09-14 的 readiness 路线指令；M14-005 保持 BLOCKED，准备工作不产生发布资格。

## 已接受的上游

[PR #74](https://github.com/Chengyue-Lu/research-agent-workbench/pull/74) 已合入 M1-009。
[PR #77](https://github.com/Chengyue-Lu/research-agent-workbench/pull/77) 于 2026-09-13 17:01:58 UTC
以 squash merge `f7a9715ed35787d3326283c22f834b1514c5c88c` 合入 M14-004。
被合并 head 为 `cbf646d1d4139da249277615a88f54d9cdf5586d`：CI 全绿。
cross-owner `let778750-cpu` 的 APPROVED review 绑定 `8e7e31a821eff587638295b992533323f8c04dff`；
owner 后续提出的 P1/P2 在 `992db5b` 修复、`cbf646d` 留证，本轮维护者明确指令合并该修复。
这份记录不将旧 review 描述为对 `cbf646d` 的新审批。

## R1：M0-007 MIT closure

维护者于 2026-09-14 明确选择 **MIT**，并确认：“已获得授权，可以随许可证选择落实”。
该确认覆盖现有相关权利人的原创贡献，包括路诚钺与黄毅的提交；这是具名维护者提供的权利依据，
Git 作者统计只用于贡献清单核对。

落实范围：

- 根目录 `LICENSE` 使用 MIT 正文，署名 `2026 Research Agent Workbench contributors`；
  原创代码、文档与原创 Skills 统一适用。
- `pyproject.toml` 声明 SPDX `MIT` 与 `license-files = ["LICENSE"]`；构建工具最低版本升至
  setuptools 77，以支持 PEP 639。`MANIFEST.in`、package-smoke source snapshot 与 public build-input
  closure 显式携带 LICENSE；direct wheel、sdist→wheel 和安装后元数据均验证许可。
- accepted index 中 3 个 repository-original Skill 及 sources index 中
  `rwb-derived-claim-preserving-rewrite-0.1.0` 的当前许可记录更新为 `MIT`；移除该原创 candidate
  的当前 unlicensed risk flag。manifest、Skill/package 内容、版本、hash、生命周期和准入决定保持原样。
- release surface 追加 policy `1.2.0`，只在 `1.1.0` 选择集上增加 LICENSE；历史 policy identity 不改写。
- 外部 source/candidate 的 license、reference-only/quarantined/rejected 状态保留；这些引用不是许可转授。
  Python 外部依赖由安装工具解析，其各自许可独立保留。生产 Skill Projection index 继续为空。

本 PR 提案 `M0-007: BLOCKED → DONE`，由 R2 review/merge 接受；许可闭合不批准 Skill 准入或发行。
许可与元数据参考：[MIT 正文](https://opensource.org/license/mit)、
[setuptools PEP 639 支持](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)。

## R2：远端保护

2026-09-14 启用并通过 GitHub REST 回读验证：

| 项目 | develop | main |
|---|---|---|
| active ruleset | [23192001](https://github.com/Chengyue-Lu/research-agent-workbench/rules/23192001) | [23192054](https://github.com/Chengyue-Lu/research-agent-workbench/rules/23192054) |
| ref 范围 | `refs/heads/develop` | `refs/heads/main` |
| 全局审批数 | 0 | 1 |
| Code Owner / conversation resolution | required | required |
| 新提交撤销旧审批 | enabled | enabled |
| last push approval | disabled | enabled |
| merge method | squash | merge commit |
| required checks | governance、test (3.11)、test (3.13) | 同左 |
| check 来源 | GitHub Actions app ID 15368 | 同左 |
| 与最新 base 测试 | required | required |
| direct / force / deletion | blocked | blocked |
| bypass actors | 空 | 空 |

创建前 rulesets 为空；创建后两个 branch API 均返回 `protected: true`，effective-rules API 与请求字段一致。
GitHub 另外返回默认 `required_reviewers: []`、`require_extra_approval_for_unattributed_changes: true`，
原值保留在证据中。develop 的 CODEOWNERS syntax API 无错误。
当前 main 尚无 CODEOWNERS；其全局 1 approval 仍生效，不能宣称 main 上存在额外路径 owner 映射。
配置前后 main/develop tips 相同；没有向受保护分支实际尝试破坏性 push。

这是当前外部配置闭合证据，发布前需 fresh readback；API 配置不替代 release workflow 的可信调用方、
frozen source CI attestation 或最终 Human release decision。审计入口为
[GitHub rules REST API](https://docs.github.com/en/rest/repos/rules)。

## R3：证据清单与演练

| 证据 | 使用方式与边界 |
|---|---|
| M14-001～004 / M1-009 accepted PRs | 既有实现验收依据；历史安装结果只绑定其记录的源码与工件 |
| PR #77 双 Python CI | `cbf646d` 的 PR rehearsal：各 1229 PASS；不能冒充本轮新源码 CI |
| 合并后的 develop push CI | [run 34770350764](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34770350764) 在 `f7a9715` SUCCESS；缺少 governance job，尚不满足 curated source required-check closure |
| 本轮 focused/full/coverage/repository | 与本轮候选 commit 和执行 receipt 绑定，见 Attempt 验证输出 |
| 重复 projection | 在隔离 Git fixture 中使用显式 synthetic CI，重复生成并检查 LICENSE/source bytes、公开链接和闭集 |
| 双 Python package smoke | direct wheel 与 sdist→wheel，在 checkout 外验证许可、资源、no-Skill scaffold 和 bounded 重建 |
| fail-closed evidence | 缺失/篡改许可证和许可元数据必须拒绝；既有 dormant topology 与 source/parent/tree 对抗测试继续通过 |
| 远端保护证据 | 请求、创建响应、effective rules、before/after tips 与当前 check app 身份 |

演练参数中的版本、source、parent 和 synthetic CI 只用于可重复性测试；不构成 release manifest 的
受信任输入。本轮不生成真实 release branch/tag，不改变 dormant topology。

当前 `CI` push workflow 没有 `governance` job；该 job 来自独立的 PR-only `CI governance` workflow。
而 dormant source trust policy 要求同一 source SHA、具名 `CI` run 与包括 governance 的 required-check
集合。因此不能把上述绿色 push run 包装成已满足的 release source-CI attestation。M14-005 的实现
slice 必须闭合这个 producer/consumer 缺口，并由可信调用方核验实际 run、job、commit 和仓库身份。

## 接续顺序与停止条件

本轮本地证据见 [Attempt index](../../../../work/M14-005/A-20260914-001/INDEX.yaml) 与
[验证汇总](../../../../work/M14-005/A-20260914-001/outputs/VERIFICATION.json)。
`e8d7e33` 的重复 projection 为 258 files byte-identical，双 Python 共 8 组安装 PASS；
`d71bce3` 仅修正 CI planner 的构建依赖变更夹具，产品/构建输入相同，32 项 focused PASS。
本地 full/coverage 在复现旧 setuptools 下限硬编码错误后停止，修复和失败均保留；完整验收以最新
PR head 的 hosted full/coverage 结果为准。Trace 校验无 BLOCK，仅保留 capture-gap warning。

[PR #78 owner review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/78#issuecomment-5655298378)
提出的风险旧状态与接续分层两项 P2 已在 `1170c4a` 修正；23 项文档/公开面检查、repository 186/0/0
与治理检查 PASS，canonical Task 行保持不变。修正证据见
[review correction Attempt](../../../../work/M14-005/A-20260914-002/INDEX.yaml)；最终 head CI 与 fresh
cross-owner R2 review 仍以 PR 当前记录为准。

### 第一层：external readiness remaining

1. 完成本 PR 的 exact-head CI 与 cross-owner R2 review，接受 M0-007 license closure 和 readiness evidence。
2. 合入 develop 后重新核实 M0-007、M1-009、M14-002～004 全部 DONE，并取得 fresh ruleset readback。
3. 取得具名维护者针对首发版本、范围和剩余限制的 Human release decision；全部外部 readiness 条件满足后，
   才可提案 M14-005 BLOCKED → READY。

### 第二层：M14-005 implementation 与首发验收

1. develop-side implementation slice 建立 protected source-CI producer/consumer attestation、release-only
   workflow/checks 和新增 policy include，闭合当前 source CI 缺少 governance 的已知缺口。
2. 在 R2 review 下原子启用 curated topology 并禁用 direct develop→main。
3. 全部门禁满足后冻结 exact develop source/current main parent，由 exporter 生成首发候选；验证重复生成、
   双 Python 安装、零内部材料泄漏、prospective merge tree 等于 projection/manifest 闭集。
4. release PR 获 R2 接受后 merge commit 到 main，再闭合 tag/artifact/hash；main 漂移即重建。

本轮完成条件为可审查的 license/protection/readiness PR 与其证据。发布授权、cutover 实现、真实 release
及其 tag/artifact closure 属于下一阶段。实时 Task 状态仅由 [`TASKS.md`](../../../TASKS.md) 维护。
