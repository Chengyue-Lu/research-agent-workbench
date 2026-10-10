# CHAIN-ASSET-002 可见通讯与范围记录

日期：2026-10-07；Profile=bounded role prompt/Skill package designer；required Skills=[skill-creator]。下列记录仅收录本资产任务的可见通讯、读域、产物和检查，不收录隐藏推理、秘密或其他代理域正文。

## 可见授权原文

Root → worker：

> 新有界资产准备 CHAIN-ASSET-002。Profile=bounded role prompt/Skill package designer；required Skills=[skill-creator]，读取 `skill-creator/SKILL.md`（运行环境提供）。代码基线 PR140 worktree `CODEWT`（PR140 checkout），先读 chain-proof-002/TASK_PACKET.md及原entry roles/intake/guide接口、对应Schema。独占只写 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/assets/ 及 ASSET_COMMUNICATIONS.md。你不独自在代码库，保留他人。准备少量必要可组合的系统提示词/role baseline变体和窄Skill候选：自然人类意图→control内部格式、Protocol→Task/Method配置、main动态0..N、child/handoff消费/状态提交、Guide独立只读；另准备通用摘要/写作类候选以便测试Skill文件真实装配。角色baseline属于职责要求，方法Skill optional；prompt参数化，不写死child数/事件/次数/真实研究领域。所有输出明确test-candidate/未准入；不改accepted registry或生产Skill/no source认证。SKILL.md采用skill-creator naming/frontmatter，引用现有输出格式必要时references；角色prompt不重复Schema大文本。资产索引列用途、调用位置、输入输出、启用条件、关闭/边界、sha由Root冻结；给Root可用接口建议。预算15分钟3轮，禁止产品/API/生产Tool/Key/账/安装/再委派/commit/push或其他写域。不用subagent forward-test，Root唯一测试者；只做资产静态格式/引用检查。完整落盘Compact hash后停止。

## Worker 可见更新（按发生顺序）

1. commentary：我会使用 `skill-creator` 准备可组合的角色提示词和窄 Skill 候选，先核对本轮 Task Packet 与 PR140 接口。资产会统一标为 test-candidate、未准入；只做静态格式和引用检查，运行测试留给 Root。
2. worker → Root：CHAIN-ASSET-002 已核 PR140 接口，准备 5 个职责 prompt 变体 + 3 个 optional 窄 Skill 候选（control JSON 成形、有据摘要、保真写作）。现有 build_role_request 的 instructions/context 是独立 user payload 数据，可装配非 Guide prompt；required_skills 非空仍明确阻断。build_guide_request 无外部 instructions 参数，且 generic Guide 拒绝 instructions/context；Guide 变体将标明“当前 seam 不支持加载”，不能把 approved_refs 当 system prompt 或冒称变体已执行。Root 可先验证内置 Guide baseline，外部候选真实加载需要另组有界 seam。资产不会改变 Registry、Schema 或 authority。
3. commentary：PR140 的角色 baseline 已覆盖五类职责。当前入口可接收非 Guide 的候选文本；Guide 使用专用只读接口，尚无外部提示词加载参数。我会在资产索引中写清这一区别，让后续测试分别证明文件装配和已支持的调用路径。
4. worker → Root：资产已落到 chain-proof-002/assets：INDEX.md、CALLING_CONTRACTS.md，prompts/{control-intake,protocol-task-method,main-orchestration,child-handoff-state,guide-read-only}.md，skills/{rwb-control-format,rwb-bounded-summary,rwb-faithful-writing}/SKILL.md。非 Guide 变体可作为 instructions；摘要/写作输出内容 JSON 可编码进 control.summary 字符串，避免改控制根 Schema。所选 Skill 的 SKILL.md+必要 reference 必须实际加载并记录 message 位置/bytes hash；正式 required_skills 在 PR140 仍阻断，文件装配不能冒称 Runtime admission。正在静态 frontmatter/链接检查，随后交付 Compact/hash。
5. commentary：已准备 5 个角色变体和 3 个窄 Skill 候选。静态检查通过：12 个文件均有候选标记，3 个 Skill 的 frontmatter 与目录名一致，26 个本地链接有效。接下来只整理交付记录；资产 SHA 由 Root 在实际选择并冻结输入时确定。

## 读域与源基线

本次实际正文读域：`chain-proof-002/TASK_PACKET.md`；required `skill-creator/SKILL.md`（授权的本地系统 Skill）；PR140 的 `src/research_workbench/entry/{roles,intake,guide}.py` 全文；`schemas/v0.1.0/{project-protocol,task-packet,method-resolution,capability-requirement}.schema.json` 全文。对 `main-state.schema.json` 和 `skill-manifest.schema.json` 只解析顶层 required/properties 元数据。其余读取仅本次自写 assets 静态检查；未读取其他代理 workstream 正文、Key、私有日志、CI 或账。

通过 `git branch --show-current` / `git rev-parse HEAD` 核定 branch=`codex/research-entry-integration`、HEAD=`d630f8e174846f4932d05a7a0d69076930b53ee1`。本任务 source 来自该 PR140 worktree，未读取 primary 旧源码。对 chain-proof-002 仅目录名称/模式发现，初始只有 TASK_PACKET.md。

写域仅 `chain-proof-002/assets/**` 与本文件。没有修改其他人的文件、entry source、Schema、Registry、状态权威或共享记忆。机器绝对路径只因授权原文和 Skill 位置审计保留在此通讯，不进入资产契约路径。

## 静态检查与结果

检查运行于授权 PR140 worktree 的 PowerShell：枚举本 worker 资产文件，使用 `System.IO.File.ReadAllText` 与严格 UTF-8 decoder；检查 `test-candidate` / `未准入` 标记；用 regex 提取 Markdown 本地链接，以当前文件目录拼接并 `GetFullPath`/`Test-Path -PathType Leaf` 校验；检查 `SKILL.md` 恰有 name/description 两字段 frontmatter、name 正则 `[a-z0-9]+(?:-[a-z0-9]+)*`、长度 <64、与文件夹名一致，description 为可解析的双引号标量且长度 ≤1024。双引号 description 以 `ConvertFrom-Json` 检查转义兼容，仅做字符串静态解析。

首轮输出：`asset_files=12 skill_frontmatters=3 local_links=26 issues=0`，exit 0。`git status --short -- docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/assets` 显示新增资产目录。此前根据层级直接修正 CALLING_CONTRACTS.md 的 source/Schema 相对路径，再进行此检查；没有留下 broken link。

静态检查不调用产品代码、Skill validator/forward-test、API、生产 Tool，不测试科学语义或 live conformance。Skill initializer/installer 没有运行；采用手写短 SKILL.md 与必要 reference。最终检查及交付 hash 在下方追加。

最终检查输出：`final asset_files=13 local_links=29 issues=0`，exit 0；新增 Compact 的 UTF-8、候选标记及本地链接均通过。交付 hash 由后续只读 `Get-FileHash -Algorithm SHA256` 读取 Compact/本文件，另送 Root；不把自身 hash 写入自身文件。所有 prompt/Skill 文件 SHA 仍由 Root 在实际选择时冻结。

Root 后续切换授权原文：

> 最新用户扩为全文档更新。先保存你原资产任务未完Compact与hash；随后切换 `DOCSWT`（PR141 checkout） 读 docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/DOCUMENTATION_TASK_PACKET.md、AGENTS/README。本任务 Profile bounded documentation worker，required-Skills=[]；Ownership README、docs/README、PUBLIC_GUIDE、SUPPORTED_FEATURES、GETTING_STARTED、STATUS + SURFACE_AUDIT/HANDOFF/COMMUNICATIONS。通读上述面，统一入口/证据等级/成熟度，PR140未合并不写成develop支持，去除历史candidatecurrent混写与重复细节，STATUS可用compact分类表+exact来源链接。不改受支持CLI或夸大live/fullchain；stable首接触面不载MTask进度。你不独自在仓库，保留他人更新。20分钟两轮，产品/API测试/Git/安装/config/Key/账/primarymemory全禁止。落盘实际阅读、修复和未决后停止；资产root保留测试候选不安装准入。

worker commentary：我先保存资产任务的最终检查与交付 hash，再切换到文档 worktree。文档更新会区分 develop 已支持能力、PR140 分支候选和测试证据，保留各页面的职责边界。

资产任务已交付，后续文档工作使用另一个 worktree 与独占读者面写域；不安装或准入本目录候选。

## 公开路径归一化

Root 将上述机器路径转换为运行环境 Skill 引用及 checkout 别名；逐字原件留在 ignored `.rwb/entry-archive/ASSET_COMMUNICATIONS_MACHINE_ORIGINAL.md`，SHA256 `d5304a555ba919797ef25e265d1896102ce865090753a529da3b9473886b3ea3`。别名不更改授权、读写范围或可见传递内容。
