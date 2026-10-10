# ADR-0026：正式 Compact Handoff 的生产与消费锁

状态：Candidate；2026-10-10；PR140 / M11-008 supporting extension。人类授权和范围见 [Task Packet](../workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/planning-handoff-004/TASK_PACKET.md)。本 ADR 不是合并、科学接受或 Skill 准入记录。

## 具体问题

现有 child 结果进入 fresh main，workflow report 进入 checkpoint，但没有独立 HandoffPacket 和完整性消费者。MainState 的 recent_handoffs 索引不能赋予普通报告 Handoff 身份。现有 typed parser 允许空 Skill lock，而 Handoff Schema 要求至少一项，导致真实 no-Skill 任务无法产生同时满足两者的正式交接。

Handoff 的普通 path refs 还不足以冻结这次 producer 的实际结果、Task、全部 Receipt 和校验工件。单纯填写“accepted”或调用成功均不能建立这条消费链。

## 决定

新增包内、确定性的 compact producer/consumer，复用既有 HandoffPacket 和 Task 关系检查。新 producer 发布独立 source record，锁定实际 Task、执行观察、输出、Receipt、限制及人类待决事项；新 Handoff 的可选 `producer_ref` 是该原件的 exact path/hash。新消费者要求此 provenance，并与调用方独立提供的预期 Task、结果和 pins 核对，重读全部实际文件；不只信 producer 自述。

child Handoff 必须先通过检查，其 pin 与内容才进入 fresh main。最终 workflow report 保持原身份与不可变 hash，由它产生最终 Handoff，再由 checkpoint 消费。引用方向是 report → Handoff → checkpoint，不向已锁 report 回填字段。调用事实与 Handoff 关联写入应用事件/工件，不改写已冻结的执行 Trace 或 Receipt。

no-Skill Task 允许 `skill_lock=[]`；有 required Skill 的 Task 仍需完整合法锁和对应执行证据。Compact 不放宽 Task 的 transfer policy：需要 Manifest/Audit 的任务若缺实际链则阻断，不填造审核结果。stage-completed、safe-paused、waiting 等状态与未解项保持原意，不能由结构检查升级为 Task completed 或 Human/Claim 接受。

## 版本、兼容和直接消费者

Schema 0.1.0 的允许集增加可选 `producer_ref`，并与 typed parser 对齐空锁。旧非空锁、无新增字段的文件仍可经旧通路验证；新 compact consumer 要求来源锁，不能静默将旧 packet 当作新生产物。旧 Schema 的 additionalProperties=false 会拒绝新增字段，不能宣称旧消费者能够读取新 packet。

新允许集与消费实现由 source commit、随包 resource manifest hash 和 frozen refs 区分；旧冻结原件、历史消费者和发行承诺不重写。Direct consumers 是 fresh main 的输入构建、checkpoint 和独立冷回放；每份 Receipt 按自己的 exact Bundle/View 验证。

交付数量依据唯一的实际产物 path/hash/contract，重复 Receipt 不增加数量；子 Task 的 Receipt 可保留为 lineage，不能算作父 Task 的交付。未经实际 Receipt 证明的必需输出形成未解项，并将完成表述保留为 safe-paused。最终 Handoff 聚合已检查的 child 限制、冲突、未解项和 Human 待决事项；checkpoint 的状态来自该 Handoff。

## 验证与接受边界

验证实际产物而非标签：独立 Task/结果/源 pins、Schema、input/Skill lock、所有输出与 Receipt、限制/冲突/未解项、Task transfer policy；替换、drift、跨 Task/attempt、缺 Skill、缺 transfer 与错误 Receipt 都应拒绝。checkpoint 与 Human 待办须消费这些已检查事实。实际 API 和模型零调用冷回放分别记录。

该扩展归 M11-008 的桥接支持；M1-010 原入口义务、定义中的 Core 不修改约束不在本 feature PR 改写。任务状态及未触发研究场景单列，不从本支持扩展直接宣布三项 Task DONE。
