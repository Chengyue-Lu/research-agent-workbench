# M0-008 远端同步记录

2026-10-10；用户明确授权“完成 M0-008 的剩余同步”。本记录证明本次线上配置变化，不授权代码合并或发布。

仅对两套 review 层执行各一次 PUT，随后 GET 重新读取。写前四层 fresh 配置与 before 比较无漂移，写后两套 hard 层规范字段与 before 完全一致。

| 层 | 实际变化与保留 |
|---|---|
| develop review 23192001 | Code Owner/额外审批要求取消，具名 User bypass 清空；active、develop 条件、squash、线程解决保留 |
| main review 23192054 | 数量审批/Code Owner/last-push/额外审批要求取消，具名 User bypass 清空；active、main 条件、merge、线程解决保留 |
| develop hard 23305447 | 未发 PUT；PR、governance/CI result、strict latest-base、squash、线程解决、force/delete 保护保持，active、零 bypass |
| main hard 23305460 | 未发 PUT；PR、两版本 release preflight、strict latest-base、merge、线程解决、force/delete 保护保持，active、零 bypass |

风险/Task/功能权限/来源及人类具体合并与发布决定仍适用；不由取消人员审核条件推导这些接受。

实际 readback 核验完成时间：`2026-10-10T09:15:02.305744+00:00`。实现前后完整原件、PUT response、窄审和通信在本次执行 archive 保留；下表给出不可变 hash，避免以摘要替代原件。

| Archive 相对路径 | SHA-256 |
|---|---|
| `.rwb/m0-sync-20261010/ruleset-23192001-after.json` | `5df09c9b34590151f7938ffdba4571d2c34caeb7001453c3e7428e77604a64ec` |
| `.rwb/m0-sync-20261010/ruleset-23192001-before.json` | `dff0110cb9a1f0e77e89265708c5d43c9722f9286909493910c92f6f6cfb168e` |
| `.rwb/m0-sync-20261010/ruleset-23192001-put-response.json` | `5df09c9b34590151f7938ffdba4571d2c34caeb7001453c3e7428e77604a64ec` |
| `.rwb/m0-sync-20261010/ruleset-23192054-after.json` | `cc3b375600e434b873d09254fca34be2aa631ef6e9e8f78e1acc48d002b6b281` |
| `.rwb/m0-sync-20261010/ruleset-23192054-before.json` | `d8bca84c47a1b2c6854d9c2aba9a0a76066838574719ad5c4919cd28450492aa` |
| `.rwb/m0-sync-20261010/ruleset-23192054-put-response.json` | `cc3b375600e434b873d09254fca34be2aa631ef6e9e8f78e1acc48d002b6b281` |
| `.rwb/m0-sync-20261010/ruleset-23305447-after.json` | `1aa29ed7db1859f710c569969345d0d099d9c9613c26a8b5a650ca1f812a0e69` |
| `.rwb/m0-sync-20261010/ruleset-23305447-before.json` | `f90fcd4b3e8d23e8e5af7a9b37caaefb53200172826cf275f96cbd76e77eb0f6` |
| `.rwb/m0-sync-20261010/ruleset-23305460-after.json` | `e36d35977ae0fb12fd56822c67d38d8df021828dbce674b9fb51c6a8c9ab76a2` |
| `.rwb/m0-sync-20261010/ruleset-23305460-before.json` | `eeec6615ba105e62c6239c4fe2673a64ffce5c8553392a87fe196c09c22327ff` |

现有本地治理/模板切片已完成105项限定检查，原head的hosted governance与component CI全部通过；本次后续提交以新head CI为准。M0-008 的实现/远端同步验收候选齐备，具体 PR142 合并仍待人类指令。
