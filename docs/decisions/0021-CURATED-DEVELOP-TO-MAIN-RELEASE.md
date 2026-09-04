# ADR-0021：从 develop 确定性生成精选 main 发行视图

状态：Accepted upon merge of the M14 R2 task-definition

日期：2026-09-05

来源：[Issue #57](https://github.com/Chengyue-Lu/research-agent-workbench/issues/57)

## 背景

`develop` 已经同时承载产品源码、Schema、Registry、测试、治理器、Task/ROADMAP、workstream、内部审计和
候选材料。它是完整工程真相，但不是适合普通使用者直接消费的发行表面。当前治理只接受同仓库的 exact
`develop -> main`，因此 `main` 会继承全部开发侧材料；现有 wheel 又只携带 Schema，多项 Runtime/CLI
能力依赖 checkout-relative `registry/`、`.agents/skills/` 或 `.codex/` 路径。两种边界都不能证明一个从
checkout 外安装和使用的精选发行物。

M1-009 解决新项目 scaffold 与 `0.x` 兼容体验，M11 解决冻结执行输入、View、Host 与 Receipt。二者都不
拥有 release source trust、公开文件面、package resource、main topology 或 tag/release authority。因此这些
工作不能自然塞回 M1 或 M11，M14 作为独立 Product / Release Closure family 被正式激活。

当前 M5 真实案例与 system-level net-benefit 尚未闭合。这不阻止发布一个诚实标记为 `0.x` / internal
technical alpha 的结构契约发行版，但公开文档不得把未完成 Evaluation、真实 Provider 或科研净收益写成
已证明能力。

## 决定

采用内容来源与 Git ancestry 分离的稳定发布模型：

```text
content / provenance                         Git ancestry

develop (完整工程真相 + 完整 CI)             exact current main tip Mn
        |                                             |
        | freeze exact source Dn                      | create release/vX.Y.Z
        v                                             v
exporter reads Dn Git blobs ----------------> generated release branch
        |                                   (parent = Mn; tree = Tn)
        | deterministic complete projection          |
        v                                             | R2 PR / merge commit
curated tree Tn + RELEASE_MANIFEST                    v
                                             main Mn+1 (tree = Tn)
                                                     |
                                                     v
                                             tag / release artifact
```

### 1. 三个受信角色

- `develop` 是实现、测试、治理、施工文档和历史证据的完整工程真值；
- frozen develop commit `Dn` 是某次发布唯一的内容/provenance source truth；develop 后续前进不改变已冻结
  scope；
- exact current main tip `Mn` 是该次 release branch 的 Git parent，curated tree `Tn` 是确定性 projection 和合并后
  main 的精确目标；`Mn` 不提供产品 bytes，也不是第二条开发线。

release branch 从 exact `Mn` 创建，exporter 随后只从 frozen `Dn` 和声明的 deterministic generated inputs 构建
完整 curated tree；任何不属于新 closed output set 的继承路径必须删除。该分支不能接收业务修复、Schema/
Authority/permission/hash/contract 语义变化，也不得合并回 `develop`。任何修复先进入 `develop`，再从新的
exact source 与当时的 exact main parent 重建投影。

### 2. 信任锚与确定性

`RELEASE_MANIFEST` 至少固定 source repository、exact develop source commit/tree、exact main parent commit/tree、
release policy identity/version/hash、选入文件的 Git blob identity/byte hash、排除闭包、发行版本及 exact CI
evidence。导出器必须直接读取 frozen develop commit 的 Git blobs，不能复制当前 working tree；projection
staging 必须为空，manifest 最后生成，release branch 的最终 tree 必须完整替换为该 staging tree。

每个输出必须显式分类为 `source_blob` 或 `generated`，不能存在未分类第三类。source file 固定 path、Git
mode、blob OID、byte size 和 SHA-256；generated file 只能落在 exact generated-path allowlist，并固定 generator
identity/version/content hash 与全部确定性输入。`RELEASE_MANIFEST` 本身使用明示的 manifest-last 特例，不把
自哈希伪装成可闭合依赖。canonical encoding/order 不含 wall-clock timestamp、随机值或临时绝对路径；相同
source SHA、policy 与 release inputs 必须产生逐字节相同的完整 tree。

release checker 不能只相信 manifest 自报的 source/parent SHA 或文件 hash。受信调用方分别提供 expected
develop source SHA 与 expected current main parent SHA；checker 从 source commit 重新读取 policy、重算
selection 和输出闭集，并逐文件验证 source blob 与 release byte identity。它还必须确认 release branch 以
expected main 为父提交，并在合并前证明 prospective merge-result tree、release projection tree 与 manifest
closed output tree 完全相同。current main 一旦前进，旧 branch/manifest 失效，必须以新的 exact parent 重新生成。
额外、缺失、移动、隐藏或遗留文件、路径逃逸、symlink/gitlink、policy 漂移或同步重算后的伪 manifest 都必须
fail closed。

### 3. 发行表面采用 allowlist

首版发行面包含完整产品源码、全部已发布 Schema、Runtime 必需的公开 Registry、package/build metadata、
用户文档、少量 curated examples，以及 release manifest/validator。`.gitattributes` 属于字节稳定性输入，
必须被显式考虑。

release policy 本身采用 strict Schema 和 append-only identity/version；拒绝 unknown field、空/重复/重叠或
不存在的 exact include、file/tree ambiguity、绝对路径、反斜杠、`.`/`..`，以及 case-fold、Unicode normalization、
Windows reserved/trailing-dot-space collision。同版本 policy 不得原地改变语义。

默认不发布 tests、coverage policy、TASKS/ROADMAP/STATUS、M-series/Developer 施工地图、workstreams/history、
内部 audit/implementation plan、`work/`、Skill Candidate/Need/Evaluation/Lifecycle 历史、legacy
`accepted.json`/`sources.json` selector/source index 或平台本地 `.codex/**`。不能使用宽泛的 `registry/**`、
`.agents/**` 代替逐类公开边界。

accepted Skill package 只在许可证、immutable Release、Projection、runtime eligibility、引用闭包与 clean-install
Gate 全部满足时条件进入。生产 Projection index 为空时，no-Skill Core 仍可发行，且不得夹带 candidate 或
maintainer history。

### 4. Package 与 Runtime data 边界

安装后的默认资源必须来自显式、hash-pinned 的 packaged runtime catalog；项目或维护者根只能作为显式覆盖，
不能把当前工作目录当成隐式 fallback。公开 Runtime catalog 与 maintainer Registry 分开，Schema、Mode/Action、
Authority、Capability Requirement、Protocol Profile 和可选 Projection 必须在 checkout 外可加载。

`project/filesystem root`、immutable `runtime_resource_root` 与 platform `integration_config_root` 是三个不同
root：`rwb validate <用户路径>` 继续解释显式用户文件，Runtime catalog loader 使用 packaged default 或显式
resource override，`.codex/**` 始终只由 integration root 读取；project tree 中的 broad `.agents/**` 不作
packaged default，但 Projection exact 引用的 `.agents/skills/**` logical asset 可由 RuntimeResourceManifest 映射
为条件 Runtime Release asset。维护者 CLI 缺少 repository/config root 时可以明确失败，不能为保留旧 cwd
默认行为而把完整 Registry 或平台配置装入 wheel。

develop 的 repository/maintainer validation 重验 Lifecycle、Evaluation、Human Decision 等完整 publication
authority；installed-runtime validation 只消费独立 `RuntimeResourceManifest` 和已发布 Schema/index/hash/identity。
若 Projection index 非空，还必须通过 RuntimeResourceManifest 的 logical→installed path mapping 闭合
Projection exact 引用的 immutable accepted Skill manifest/package bytes，并拒绝 orphan/unindexed Skill asset；
这些单个 manifest/package 是条件 Runtime Release asset，不恢复 `accepted.json` 的 legacy selector authority。
`.agents/skills/**` 不整体发布；只有上述 exact closure 可映射到受控 installed namespace，`.codex/**` 始终
属于 integration config。release manifest 在后续投影中再 pin wheel、RuntimeResourceManifest 与 source-CI
provenance，不能为了 Runtime smoke 把 Need/Evaluation/Lifecycle history 一起发行。

wheel/sdist 的实际资源集合必须与 release policy 对账，并在 Python 3.11/3.13 的空目录环境证明安装、Schema
枚举、Registry/Projection load 和最小 no-Skill quickstart。测试不得通过把 cwd 或 `PYTHONPATH` 指回源码树
来伪造 portability。

### 5. CI 与远端治理

`develop` 继续运行完整 behavioral、coverage-quality 90/95/90、package-smoke、repository validation、
governance 与 negative/adversarial Gates。release/main 只复用冻结 source SHA 的已通过证据，并额外验证
manifest、allowlist、source-byte identity、双 Python clean-install、最小 no-Skill/Registry smoke 和开发材料
零泄漏。

M14-001 只建立 dormant topology/source-trust seam；M14-002 只交付 deterministic surface/manifest
export/check，M14-003/004 分别闭合 portable package 与 public docs。拓扑被识别不等于 release PR 获得 merge
资格：M14-001～004 完成后 `release/* -> main` 仍明确 fail closed，现行 exact `develop -> main` 仍是唯一可执行
路径。

M14-005 在 M0-007、M1-009、M14-002～004、source CI、release checks、远端保护与具名 Human release decision
全部满足后，才原子启用受控 `release/v* -> main` 并禁用 direct `develop -> main`，随后完成首次发行。该 Task
可包含独立可审计的 develop-side governance activation slice 与 release PR；Task identity 不要求和 PR 1:1，
但任何中间状态都不能留下两条可绕行路径或一条 readiness 未闭合却可 merge 的 release path。不能仅凭分支
前缀获得资格。main/develop 的禁止 direct push、force push、delete 及 required checks 还必须由 GitHub
ruleset/branch protection 实际落地，仓库文档或本地 checker 不能冒充远端执行证据。

## M14 任务映射

Issue #57 中的 `REL-*` 只是工作包别名；canonical implementation / acceptance identity 是：

| Issue 工作包 | Canonical Task | 职责 |
|---|---|---|
| REL-001 | M14-001 | release topology、source trust 与治理入口 |
| REL-002 | M14-002 | deterministic surface、manifest、export/check |
| REL-003 | M14-003 | portable package 与 Runtime data closure |
| REL-004 | M14-004 | public documentation surface |
| REL-005 | M14-005 | first curated release、main merge 与 tag |

精确状态、依赖、owner 与 acceptance 只在 [`TASKS.md`](../TASKS.md) 维护。

## 后果

优点：

- `develop` 不必为了发行而丢失测试、治理或审计真相；
- `main` 的每个字节都能追溯到 frozen source 或受控生成规则；
- release branch 继承 current main ancestry，但最终 tree 只由 frozen source projection 决定；
- 发行 review 不会随 develop 后续提交漂移；
- package/runtime 真实脱离 checkout，普通用户路径与维护者路径不再混用；
- 未获准入或未解决许可的 Skill 不会因目录复制意外进入发行物。

代价：

- release branch 是生成物，需要独立 manifest、surface checker 和 release CI；
- current main 在 review 期间前进时，release branch/tree/manifest 必须按新 parent 重新生成；
- 当前 exact `develop -> main` 治理必须迁移，且迁移期应 fail closed；
- README/navigation 需要公开版单一来源，不能继续链接被排除的施工文档；
- 首次 release 仍被许可证、人类 release 决定与远端 ruleset 阻断。

## 非目标

本决定不修改 Runtime、Method、Capability selection、Claim、Human Decision 或 permission 语义；不降低
develop CI；不清除 Git 历史；不在 release branch 修复功能；不通过 cherry-pick 拼装发行物；不授权
Topic 5、automatic fallback、routing 或 multi-Agent orchestration；也不把未完成的 Evaluation 写成产品价值证据。

## 接受边界

- 本 ADR 与 M14 task-definition 合并，只表示 M14 family 和 Task DAG 获得实施入口；
- `M14-001` 是唯一初始 `READY` Task；M14-002～004 仍按依赖保持 `PARKED`；
- `M14-005` 在许可证、scaffold、远端保护和所有 release closure 未满足前保持 `BLOCKED`；
- M14-001～004 只建立 dormant seam 与发行资产；在 M14-005 readiness/cutover 完成前，现有 `develop -> main`
  规则仍是执行事实，
  不能按目标架构手工发布。
