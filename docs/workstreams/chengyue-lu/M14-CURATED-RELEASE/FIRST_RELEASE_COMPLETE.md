# M14-005 首个 curated release 完成记录

- 责任人：路诚钺（`Chengyue-Lu`）
- 观察日期：2026-10-01
- Task：`M14-005`；风险 `R2`
- 发行：[v0.1.0 GitHub alpha prerelease](https://github.com/Chengyue-Lu/research-agent-workbench/releases/tag/v0.1.0)
- 来源：[Issue #57](https://github.com/Chengyue-Lu/research-agent-workbench/issues/57)、[ADR-0021](../../../decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md)

首发已完成最终 R2 审核、正常 main merge、annotated tag、分发包构建、实际安装验收和 GitHub 附件发布。
本 source-side feature PR 提出 `M14-005: READY -> DONE`，仍须独立正常审核接受；其完成证据来自已发生的
首发，不把 release branch 回并 develop，也不改变已发布的 source/tag/附件。

## Exact identity

| 对象 | 冻结身份 |
|---|---|
| repository | `Chengyue-Lu/research-agent-workbench` |
| accepted frozen develop source | `1ac70be6095f0c7aac5cf4de1cd30ca4ca959b60`（#118 正常 squash 集成） |
| release branch / final reviewed candidate | `release/v0.1.0` / `830083420ed0d2bd21030506813fe5baa44ceadf` |
| exact previous main parent | `b1d5a5a5850e0e7541e4c460f15384cd45357ab2` |
| policy / output count | `1.5.0` / 298 files，包含 release manifest |
| projection / actual merged main tree | `cf7169e47005ba705031c6e3207736b32cb0dd0b` |
| release PR / actual merge commit | [#116](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116) / `b5a99637e9c140df004dcd0cd07a4b6bbfcd4195` |
| merge parents | previous main `b1d5a5a5850e0e7541e4c460f15384cd45357ab2`，candidate `830083420ed0d2bd21030506813fe5baa44ceadf` |
| merged at | `2026-10-01T12:47:34Z` |
| annotated tag / tag object | `v0.1.0` / `9e662a8914016850ebf9ea3a7b102c4e0adeff26` |
| tag peeled target | actual main merge `b5a99637e9c140df004dcd0cd07a4b6bbfcd4195` |
| GitHub Release / published at | release `400966607`，`prerelease=true` / `2026-10-01T12:55:05Z` |
| final PR body SHA-256 | `00f84b02386b6124bc7ed33a71d18414696e97f6812e8618dddc6c2e207c977b` |
| release manifest SHA-256 | `8d7b521a8bc5cbd6b2f5ced7e33b076c9771bdd683e84513756a9b9c1cbbb3fa` |

内容信任来自 frozen develop Git blobs 与 source-owned checker；Git ancestry 来自 exact previous main。
重复 projection、candidate/prospective merge tree 与 closed output set 已验收；实际 merge 的两个 parent
和 tree 再次核对一致。公开 main 的精选 tip 不会删除旧 Git history。

## 审核、具名决定和保护

黄毅（`let778750-cpu`）的[最终 APPROVED review 5378427164](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116#pullrequestreview-5378427164)
绑定 exact candidate `8300834`，于 `2026-10-01T11:07:24Z` 提交，无可操作发现；合并前 live
`APPROVED / CLEAN / MERGEABLE`、两个 required checks 与零 unresolved conversations 满足。
用户随后指示“审核通过，继续推进”；[具体 main merge 决定](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116#issuecomment-5931777480)
绑定 source/base/head/policy/manifest，以正常 merge commit 集成。actual-main 安装验收通过后，另行记录
[具体 tag/artifact/publish 决定](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116#issuecomment-5931897933)，
再非 force 推送 annotated tag，创建 draft、上传、下载核验后公开 alpha prerelease；未向 PyPI 上传。

cutover 的[本次维护者责任决定](https://github.com/Chengyue-Lu/research-agent-workbench/pull/116#issuecomment-5929578523)
由路诚钺承担完整规则确认与执行责任，黄毅承担技术测试和最终 R2 审核。账户权限未变；不把审核人有限的
live API 字段可见性写成另一 owner 对完整远端载荷的认证。四层规则为 develop hard/review
`23305447 / 23192001`、main hard/review `23305460 / 23192054`。main hard 一次 PUT 替换为
`release preflight (3.11)` / `release preflight (3.13)`（App `15368`、strict）；其余三层完整 raw 未变，
双方 effective rules/protected flags 与载荷匹配。两个 hard bypass 为空，review/strict/conversation/
merge-method/force-delete 保护保留；本次实际 merge 不使用审核豁免。

main hard 更新后 payload SHA-256 为 `230a4c5ab7e5b534ca3ad098386b5e260b449bbb9d6d899588c7abe2ed118237`。
合并前、tag/publish 前及附件发布后完整回读未见保护漂移。

## CI 与对抗性证据

| Evidence | Actual identity / result |
|---|---|
| protected source CI | [36817707894](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36817707894)，source `1ac70be`、attempt 1，SUCCESS；clean exact-source live attestation PASS；source-CI contract `legacy-ci-v1` / schema 1 |
| source component push | [36817707881](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36817707881)，SUCCESS |
| final Ready release CI | [36850269507](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36850269507)，attempt 1、suite `99807683374`，双 required jobs SUCCESS，current body/live R2 governance 与 source/public/install 闭包通过 |
| required job / check identities | Python 3.11 `110329996407`；Python 3.13 `110329996749`；均 App `15368`，head `8300834` |
| 3.11 hosted install artifact ZIP | artifact `11155197032`，4970 bytes，SHA-256 `09fb05f73a64c6f94f13e401527344094e505284e608a6871d5d50b00ae4fa28` |
| 3.13 hosted install artifact ZIP | artifact `11154319709`，4970 bytes，SHA-256 `47010a95fa998ca8d1d85554e72370687bdcf75800f707137d04b32975d329dc` |
| real direct-develop negative | [PR119](https://github.com/Chengyue-Lu/research-agent-workbench/pull/119) / [36850013496](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36850013496)：两个 required jobs 实际执行，首步因 `HEAD_REF=develop` 在 checkout 前失败；required jobs 零 skipped，119 关闭未合并 |

source 既有真实 CI 证明 Python 3.11.16/3.13.15 各 `1621/1621 PASS`、零 skip/error/failure，同一行为集合；
global line `95.098084%`，governance checker line/branch `98.258345% / 98.051948%`，新增
release governance/install helper `100% / 100%`。本轮复用同一 accepted source 的证据，不将 actual-main
安装探针写成新 full/coverage run。早期 direct-develop/source/body/parent/manifest 负例和准备留痕仍在原
[cutover](CUTOVER.md)、[release checks](RELEASE_CHECKS.md)及 #116 审核链中保留。

## Actual-main 分发与附件闭包

分发包由实际 main merge 的 298 个 Git blob bytes 构建；direct wheel 与 sdist-derived wheel 的 logical
members、元数据及 Runtime resources 相同。两个 wheel 的 ZIP SHA 可因 ZIP metadata 不同，logical
byte equality 与实际上传 direct wheel SHA 分别核对，不把 sdist-derived wheel SHA 当作上传附件身份。

| Python | direct wheel | sdist → wheel | Runtime / scaffold |
|---|---|---|---|
| 3.11.16 | isolated + poisoned CWD/PYTHONPATH，两探针 PASS | isolated + poisoned CWD/PYTHONPATH，两探针 PASS | 155 resources / 106 schemas / 4 versioned Mode 文档 / 空 Projection；offline-demo reconstruction matched |
| 3.13.15 | isolated + poisoned CWD/PYTHONPATH，两探针 PASS | isolated + poisoned CWD/PYTHONPATH，两探针 PASS | 同上；offline-demo reconstruction matched |

八个实际安装探针均在新 venv、checkout 外运行。资源清单 SHA-256 为
`4e6b1be6107922e46354d5a3e23602ec724d76853d57434217184916960a4c54`。
GitHub draft 上传后重新下载，精确五件集合、实际字节 hash/size 与远端 asset digest/size 一致，才公开发行。

| Published asset | Bytes | SHA-256 |
|---|---:|---|
| `research_agent_workbench-0.1.0-py3-none-any.whl` | 568962 | `bbe742bf6d3f9b4843be985e068db79089f73cfc64e0dfcc644f1961a529a238` |
| `research_agent_workbench-0.1.0.tar.gz` | 480775 | `87336e7918954b807888a191dbf1441145ff4ba721d0916808cef0de4a1cfcaf` |
| `RELEASE_MANIFEST.json` | 323792 | `8d7b521a8bc5cbd6b2f5ced7e33b076c9771bdd683e84513756a9b9c1cbbb3fa` |
| `RELEASE_PROVENANCE.json` | 1735 | `7d9acdddeb602b25ff2fc98420b1dfc426653fe27e040dfc61a99d82ec38d95f` |
| `SHA256SUMS` | 396 | `4c67e7e5d063a00164152bcf57a4a7de95b59c852e95257c6251ec411b1d57cd` |

manifest 固定 projection 的 source/generated closure；`RELEASE_PROVENANCE.json` 再绑定 actual main/tag、
source/CI/manifest、两个分发包及具体审核/决定。`SHA256SUMS` 覆盖另四件附件；自身 digest 使用本表与
GitHub asset metadata 记录，避免自哈希循环。

## 完成边界与后续

首发继续定位为内部技术 alpha。八探针只证明独立安装、Runtime catalog 和固定离线工程重建；不证明
真实 Provider/session conformance、真实 Skill admission、M5 net-benefit 或科学有效性。当前 projection
index 为空；Human/Claim/research judgment 仍由各自 authority/Gate 负责。

已发布 `v0.1.0` tag 与附件保持原身份。后续产品修复回 develop，新的具名版本决定重新冻结 source/current
main parent，并经过完整 projection/source-CI/public/package 检查、R2 审核和独立 merge/tag/publish 决定。
release branch 不修改产品，也不回并 develop；本次批准不延伸为下一次发行或其他 Task 的授权。

调用方正式 Attempt `M14-005 / A-20261001-007` 保存脱敏可观察 action receipts、API readback、八探针、
下载字节与工作日志，保留 capture-gap 限制，不捕获隐藏推理。旧 A003～A006 和不可变 cutover evidence
commit `7416c41a24fea902c186e8881eed69e1cb07cadb` 未改写；仓库只保存可移植首发摘要和公开证据入口。
