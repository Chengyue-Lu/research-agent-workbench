# M8-003 验证证据

状态：DONE；PR #30 最终本地集成验证通过，远端 CI 待更新 head。

验收证据：八个 diagnostic case 各自固定 synthetic bounded TaskPacket，并通过 `task_id + revision +
raw-byte hash` 进入 Method Resolution。Validator 已覆盖 wrong Task hash、wrong Mode Action、Action Gate
删除/换名、additive Gate、Artifact evidence coverage、stop/block preservation 与 claim-effect override。
Skill Need 在没有实现时仍保持 `resolution_status: proceed`；`need-not-implemented` 与 `capability-gap`
不再属于 Method 层。

聚焦 Action→Method→Migration→Eligibility 与 routing 链测试共 45 项通过；最终本地完整测试：
334 passed、3 skipped；repository validation：`validated=124 errors=0 warnings=0`；
`git diff --check`：PASS；远端 CI 在提交后记录。
