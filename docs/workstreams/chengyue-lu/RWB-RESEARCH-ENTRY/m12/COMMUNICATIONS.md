# PLAN-M12 COMMUNICATIONS

日期：2026-10-07（Asia/Shanghai）；本文件是 PLAN-M12 的可见指派与关键事件记录，非 Task/Phase/Topic 状态权威。Agent Profile：bounded continuity-planning agent；required-Skills=`[]`；无再委派。正式输出：[PLAN.md](PLAN.md) 与本文件。

## 1. 可见指派

来源：Codex create_thread delegation；source_thread_id=`01a1064a-eaef-7da0-aebd-962910ff42b8`。用户明确要求新开窗口考虑 M12；本 Task 的具名人类负责人按 Task Packet 为路诚钺，执行接口领域为黄毅。没有主动向其他任务发送消息；Root 将自行读取结果。

下列保存可见指派的操作内容。为保持文档 portable，原文的两个机器绝对 checkout 路径分别归一为“指定 checkout / primary checkout”；其余权限、基线、输出与停止条件完整保留。指定 checkout 的身份由 branch + exact HEAD + worktree metadata 确认，实际路径由本聊天工具回执保留。

> 用户明确要求新开窗口考虑 M12，当前仅执行 PLAN-M12 规划 Task，禁止恢复旧开发/付费测试。实际读写 checkout 为指定 checkout，branch codex/research-entry-integration，base develop d3c4d23206339ebc7f18b5621f3aa5453f96335e；不要使用 primary 旧 HEAD，不新建 branch 或 checkout。先读该 checkout 的 AGENTS、README、docs/README/DEVELOPMENT/ARCHITECTURE，再读 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/TASK_PACKET.md 及 README，按 PLAN-M12 的 Profile(required-Skills=[])/读域/独占两 MD/20 分钟 4 轮/stop 执行。primary PROJECT_MEMORY 只读 M12/M5 最新导航，不改；你不是唯一参与者，不覆盖其他窗口内容。输出仅 m12/PLAN.md、COMMUNICATIONS.md，内容包含实际接口、manual 续接和 Topic5 recovery 分界、PhaseC 与 task-definition/ADR 前置，以及可审阅候选任务名称/依赖/验收；不宣称 M12 解冻/具名接受、不改 PR137。0 代码/Schema/Registry/API/Tool/Key/账/安装/产品测试/Git commit/push/新子代理。Root 会读取结果，不需要主动发消息到其他任务。保存可见指派与关键事件，最终回两文件 hash 和 10 行内 Compact 结果后停止。

同 checkout 的 [Task Packet](../TASK_PACKET.md) 明确本窗 required-Skills=[]、独占两 MD、20 分钟/4 轮；共同 [README](../README.md) 明确本分支批准不解冻 M12/Topic5，当前 ENTRY 的各切片与角色/Guide 接合另由 Root 负责。

## 2. 四轮与关键事件

预算起点：2026-10-07T21:28:35+08:00；最晚停止：21:48:35+08:00。轮次是规划迭代，不是逐文件工具调用计数。

| 轮次 / 可观察时间 | 可见动作与结果 | 边界/处理 |
|---|---|---|
| 1，21:28:35–21:29:14 | 核对指定 branch/HEAD/worktree、既有 dirty paths；依序读 guidance 与 Task Packet；memory policy 为 generate_memories=false/use_memories=true；取得 primary 的 M12/M5 最新导航 | 初始仅已有 config 修改与本 workstream 未跟踪内容；不改 config/primary，不新建 checkout/branch |
| 2，21:29:14–21:31:16 | metadata 定位 context/recovery 真路径、直接 tests；阅读实际接口、canonical Gate 与 pinned PR137 参考候选；记录实际输入 SHA-256 | src/context 等 Task 简写路径及无扩展名模块名不实际存在，首次 rg 返回 path-not-found；改为 metadata 得到 src/research_workbench/context 与 06-CONTEXT_GOVERNANCE.md；无安装/修复 |
| 3，21:31:16–21:34:33 | 对齐人工再启动与 recovery 的行为/authority 分界，形成首个 frozen-action/fresh-process 候选、前置与最小验收；保存两 MD | 只写独占文件；与 Root ENTRY 关系是接口建议，未读取其他窗口的新实现 |
| 4，21:34:33–交付冻结 | 检查两文档链接、限定写域、基线/输入是否漂移，补读 transfer verdict 的 209–246 行，计算 final output hashes | 检查只证明交付结构与读取源身份；不运行产品 tests、不自填 Human/R2 acceptance |

可见用户进度通知已经说明：仅 PLAN-M12；resume-check 与 recovery preflight 不执行任务；首候选沿 PR137 而保持独立前置。没有调用 send_message_to_thread 或协作子代理工具；无新的 inter-agent transmission。

本窗可见进度通知原文：

> 我会在指定 checkout 中按 PLAN-M12 的读写范围完成规划，先核对任务包与当前导航，再保存两份可审阅文档和文件哈希。

> 已确认指定分支和基线，且 memory 配置符合项目政策。任务包将本窗限定为 M12 规划：接下来会核对 context/recovery 的实际接口，并把人工续接、Topic 5 恢复及其前置条件写清楚。

> 源码确认了一个关键分界：`resume-check` 只检查 checkpoint；现有 recovery preflight 只验证 safe-paused 旧 Attempt 并返回新 Attempt seed，不创建 Attempt 或执行任务。因此，当前入口可复用人工读取、检查和状态提交接口；自动换届、重试和恢复编排仍需独立的 Topic 5 授权。

> 首个 M12 候选可以保持很窄：旧 action 已闭合后，在新进程中执行一个已冻结的 next action，使用唯一新 Attempt。PR137 已有这份候选，我会引用它并核对与当前基线的接点；先保留 Phase C 具名收口、Topic 5 R2/ADR 和独立 task-definition 三项前置。

> 两份文档已保存，19 个本地 Markdown 链接检查通过，读取的源码与任务边界未发生漂移。验收范围仅为静态阅读和文档检查；我会冻结最终哈希并停止本窗工作。

关键观测：
- 指定 HEAD=`d3c4d23206339ebc7f18b5621f3aa5453f96335e`，primary HEAD metadata=`11c3b57dfbf8af0dc2587fc421d097e2544941c3`；primary 旧 HEAD 未作源码基线。
- 参考 worktree HEAD=`2f1b9850e0d40f18d3a9b95057a4d01d60b8a83e`；四参考文件为该 HEAD tracked blobs，读取后未有 diff。未读取原 Attempt archive/raw log/private oracle；没有借 hosted PASS 建立本轮资格。
- 读取时本页使用的 guidance/Task/ROADMAP/module/source/direct-test 路径相对 d3c4 无 diff。当前 checkout 没有 M12 候选正文，只到明确参考 worktree 定向读取索引所指四文件。
- 首次跨关键字 primary 导航检索匹配了附带历史长行，工具输出截断；后续只抽取 M12 行和 M5 最新段落，历史尾文不用于当前状态或授权。两次过长批量读取亦截断，缺失的 DEVELOPMENT 5.2、TASKS/ROADMAP Gate、候选 ADR/Task 验收段落均定向补读。此记录不宣称所有输出完整读取或原始消息归档无缺口。
- validator 文件 metadata 探索的 scripts/tools 目录不存在；未安装依赖或运行产品 suite。最终使用只读 PowerShell 小范围链接/路径检查，结果在下节补录。

## 3. 输入 pins 与实际读域

以下为 21:31:16 前后实际文件 SHA-256；除 reference 四项外，均位于指定 checkout。文件 hash 冻结实际字节，不表示已阅读全文、获得运行权限或完成语义审查。

| 路径 | SHA-256 | 实际读取范围 |
|---|---|---|
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/TASK_PACKET.md | a8a4b8a71f539fdb044f0fb2eb049c11e9ac3afc77888af439f26da07c41ffe2 | 全文；PLAN-M12 授权/读写/预算/停止 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/README.md | a9cf67dcddfd05aba4698a20b173220b6f16c985134a214ae6461446c8b657b7 | 全文；人类授权与 ENTRY/两个规划窗口边界 |
| docs/modules/06-CONTEXT_GOVERNANCE.md | 752f9e434c842da4d83c9979701ba11edd4f6321ae28c583ef4efa40bf59567c | 全文 |
| docs/TASKS.md | 6a75ec90b3e88d06b894eed6b30322ddbd2770a60a093f7349b7f1244bde7e54 | 1–35、75–93、185–214、232–248、296–341；过长段落截断后补读 Gate |
| docs/ROADMAP.md | fef83bb1456a4e59ba43a8a2f1493081bd6e6dac19f3de285032cb0f4a30ecd9 | metadata 定位；10–22、44–81、201–239，Phase C/Gate 定向补读 |
| docs/workstreams/chengyue-lu/PHASE-C-RESEARCH-STATE/README.md | fa0c1de11c9b57618fbfbcecbf23692545d425d470178355f9b8b9fad27f38e4 | 全文；当前 candidate/actual-binding/closeout 语义 |
| src/research_workbench/context/models.py | e601b697bd479a2144d577a89fd3116004039d8c4db0c3bfd1e63fbb2b19e5b1 | symbols；157–201、227–347、504–623 |
| src/research_workbench/context/handoff_transfer.py | b367b12283f62f65464893539403c25342d3b3a3b313b74dafa37ce7ad37ceb2 | symbols；44–120、209–246；风险/semantic/verdict branches 定位 |
| src/research_workbench/execution/recovery.py | 82f1d1e6a58e7b1fd35eb039d80a8346d66cd3f1e915db7448223b0ccbcc1d3a | 全文 |
| src/research_workbench/cli.py | 8f3f1cb860d4b33f6265278a3eabd80e1e2d17d6843c8bb3db1a03cfb6168d11 | symbols；90–115、1209–1348、1380–1499、1930–1975；仅直接消费者段落，1490 后未作为结论依据 |
| tests/test_m3_context_observability.py | b8647fe2d840e0028b442081207c394b3a5a04812f80ab604bd51cf28bc6e2fd | symbols；44–268，未运行 |
| tests/test_execution_trace_adapter.py | e5b3b8a2ba7eb7fbf3d454a9ce47b812a04478288c74f6ddbb9bc1c84804b37c | symbols；359–438、471–553，未运行 |
| tests/test_execution_archive_helpers.py | 558200a34cf0ab7808c82afcc614d27b9aa2ab454d75d318a93a8e13b3377875 | recovery symbols；450–510 mocked 正例，未运行 |
| tests/test_handoff_transfer.py | 3c7d3aa7e8c5b981e2d1b0943b4c06f86549110bc63beb00df7fc522d333e468 | test/判定/错误代码/assert 定位，未运行 |
| reference@2f1b9850:docs/workstreams/chengyue-lu/M12-BOUNDED-CONTINUITY/README.md | deb95ea74275cbe0edcb9f0abff61823ead035e809e41518d0977841b1b918b8 | 全文 |
| reference@2f1b9850:docs/workstreams/chengyue-lu/M12-BOUNDED-CONTINUITY/ADR_CANDIDATE.md | 3fb099cb43f64597925d435e6d56d9967fbb84592665e6d850479d0a57523b11 | headings/metadata 定位；17–81 正文，先前 truncated 部分以该定向读为准 |
| reference@2f1b9850:docs/workstreams/chengyue-lu/M12-BOUNDED-CONTINUITY/TASK_DEFINITION_CANDIDATE.md | 3f1326f4f5857cb6978655fd1e3c2fc760456fa454608b4acad0715f929fe5e3 | headings/候选表/依赖/path/步骤定位；72–107 验收及停止正文 |
| reference@2f1b9850:docs/workstreams/chengyue-lu/PHASE-C-RESEARCH-STATE/CLOSEOUT_CANDIDATE.md | 08aa75c17c5c8f943784d75ce357e25ca4b7b6f82ca3f73df13e9d0f925febf9 | 全文可见；旧 manifest/24-source/状态核验只作来源声明，本轮未重跑 |

其他明确读项：AGENTS、README、docs/README/DEVELOPMENT/ARCHITECTURE；STATUS 的 57–106 对应行；context/__init__ exports；memory policy 的三行与 primary M12/M5 最新导航。global MEMORY.md 仅通用规则 18–26，用于项目归属/UTF-8/不生成全局记忆；未写 memory，也未读其 rollout。

## 4. 文档检查与交付冻结

截至 2026-10-07T21:35:58+08:00：

- 两文件存在、UTF-8 正常，19 个本地 Markdown 链接全部解析到指定 repository 内既有文件；文档没有机器绝对路径。仅此结构检查为 PASS，未运行 repository/product suite。
- 首次机器路径 regex 把 `https://` 的协议名尾部误判为 drive token；确认后加词边界重新检查为零错误，未删除合法链接。该检查误报保留本条，不将初次结果改写为 PASS。
- 限定输入的 `git diff --name-only d3c4...` 返回 0 paths；Task Packet/README hashes 再核与输入 pins 相同。参考文件保持只读；没有把其他窗口修改认作本窗交付。
- 本窗写入清单仅 `docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/m12/PLAN.md` 与 `docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/m12/COMMUNICATIONS.md`；目录实际只有这两个文件。未 stage/commit/push、改 PR137 或 primary memory。
- PLAN.md final SHA-256：`e8e0fdbd1e6e261a653d2e8e4d12e200195e421de02ef80c77e6b69b29aff1fc`。本文件自己的 final SHA-256 在 Compact handoff 返回，避免自引用；最后一次只读检查/计算 hash 不再修改本文。

输出资格：PLAN-M12 的规划工件完整，可由 Root 按 pins 审阅；实施候选未启动、无 accepted M12 Task。Root proposed PROJECT_MEMORY entry 在 PLAN 第 10 节；本窗没有写 shared continuity summary。四轮在 20 分钟内结束，完成交付后停止。

## 5. Compact handoff 与停止条件

交付责任：此窗口只负责两份规划文档。Root 后续按 exact file hashes 读取并决定本分支 completion/index 与 shared primary memory 更新；PLAN 的 proposed entry 不是本窗口已写入的共享事实。

PLAN-M12 输出完成不意味着 M12 Task 已定义、READY/DONE、Phase C/Topic5 已接受或 PR137 已更新。没有新 Agent、产品调用、安装、科研材料/Key/账写入、Git stage/commit/push。最终回两 hash 和不超过 10 行 Compact 结果后停止。
