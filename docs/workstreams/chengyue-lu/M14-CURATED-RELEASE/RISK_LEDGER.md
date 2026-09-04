# M14 Curated Release 风险台账

| ID | 类型 | 风险 | 控制 | 当前状态 |
|---|---|---|---|---|
| M14-GOV-001 | fact | 仅放行 `release/*` 分支名会绕过 source、surface 与 manifest 证明，或迁移期形成两条可绕行发布路径。 | M14-001 只建立 dormant same-repo/source-trust seam且 release path继续 BLOCK；M14-002 验收时原子启用 release/v* 并禁用 direct develop→main。 | open；等待 M14-001/002 |
| M14-SOURCE-001 | fact | 从 working tree 复制会吸收 dirty/untracked 文件或 Windows CRLF 转换，generated output 又可能脱离 provenance。 | M14-002 直接读取 frozen commit Git blobs；显式纳入 `.gitattributes`；每个输出分类 source/generated 并 pin blob/mode 或 generator/inputs；两次完整 tree 逐字节一致。 | open；等待 M14-002 |
| M14-MANIFEST-001 | fact | 攻击者同步改文件和 manifest hash 后伪造一致性。 | checker 接受外部 expected source SHA，重读 source commit/policy 并比较 Git blob bytes，不能只信 manifest。 | open；等待 M14-002 |
| M14-POLICY-001 | fact | allowlist 的 unknown/overlap/path collision 或同版本漂移改变公开面而未被识别。 | strict append-only policy Schema；拒绝 unknown、空/重复/重叠/不存在 include、file/tree ambiguity、case-fold/Unicode/Windows 路径冲突。 | open；等待 M14-002 |
| M14-SURFACE-001 | fact | denylist 或宽泛 `registry/**` 随仓库增长泄漏 tests、workstream、Need/Evaluation/Lifecycle/private 材料。 | versioned allowlist、closed output set、unexpected hidden/file/tree 对抗测试；Runtime 与 Maintainer Registry 分离。 | open；等待 M14-002/003 |
| M14-PACKAGE-001 | fact | wheel 在 checkout 内 smoke 通过，但独立安装缺 Registry/Projection 或借用了 cwd。 | 独立 RuntimeResourceManifest、project/runtime/integration 三 root、CWD/PYTHONPATH poison、direct wheel 与 sdist→wheel exact asset 对账、Python 3.11/3.13 空目录 smoke。 | open；等待 M14-003 |
| M14-VALIDATION-001 | fact | installed Runtime 复用 repository publication validator 会迫使 Need/Evaluation/Lifecycle 历史进入发行物，反向破坏 M11 data boundary。 | 分离 repository/maintainer publication Gate 与 installed-runtime catalog Gate；后者只消费 manifest-attested published bytes/index，不降低前者的完整 provenance 校验。 | open；等待 M14-003 |
| M14-SKILL-001 | fact | 未许可/未获准入 Skill 因目录复制进入发行物，或非空 Projection 未绑定实际随包 Skill bytes。 | no-Skill Core 为默认；不发布 legacy accepted selector/整个 `.agents` tree；非空 index 仅按 logical→installed mapping 闭合 exact accepted manifest/package bytes并拒绝 orphan/unindexed asset；license/publication truth 仍由 develop Gate。 | open；M0-007 与生产空 Projection index 继续阻断 Skill 发行 |
| M14-DOCS-001 | fact | 裁剪 TASKS/STATUS/workstream 后公开 README 产生断链，或把 bounded/synthetic 能力写成产品完成。 | M14-004 建立 public-doc single source、projection link checker 与 evidence-bounded supported-features 页面。 | open；等待 M14-004 |
| M14-REMOTE-001 | fact | 仓库内 checker 无法阻止 direct/force push，main/develop 当前远端保护未闭合。 | 首次发行前由具名人类启用并验证 GitHub ruleset/branch protection；保存 exact external evidence。 | BLOCKER；不得由本 PR 伪报 controlled |
| M14-LICENSE-001 | fact | 仓库与原创 Skills 没有可复用许可证，技术可安装不等于可合法发布。 | M0-007 保持 M14-005 hard dependency；具名人类决定项目/Skill 许可。 | BLOCKER；等待人类决定 |
| M14-EVAL-001 | fact | M5 真实 net-benefit 未完成却被 release 文案写成已证明价值。 | M14-004 support matrix 明确 structural/bounded/live/evaluated 层级；M14-005 review 校核 claim 不超证据。 | open；不阻塞机制实现，但阻断过度宣称 |
| M14-BRANCH-001 | fact | 在 release branch 修功能，或把精选删除反向合并到 develop。 | release branch 只由 exporter生成；语义修复回 develop 后重建；release branch 永不合并回 develop。 | open；等待 M14-001/002 enforcement |
| M14-FREEZE-001 | inference | 把计划分支 HEAD 当成首次发布 source SHA，导致 review 期间 scope 漂移。 | 只有 M14-005 在全部前置完成后冻结 source；task-definition/M14-001 不记录 release source manifest。 | controlled by current scope |
