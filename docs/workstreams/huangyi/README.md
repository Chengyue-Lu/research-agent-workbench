# 黄毅 Workstream 入口

owner：黄毅（GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`，二者为同一账户）

本目录是黄毅负责的 Provider/API/Execution 相关优化与跨边界审计的过程入口。每个独立修改使用
`docs/workstreams/huangyi/<task-id-or-slug>/`，在同一 workstream 中持续更新范围、证据、风险和
审查，不为每次微调新建分支或散落一个新的顶层 Markdown。

当前具名 workstream：

- [`execution-runtime-recovery-audit/`](execution-runtime-recovery-audit/README.md)：
  Execution/Runtime 可恢复审计、PR #23 hard-block 证据及治理 rollout。

## 文件生命周期

1. 进行中的优化说明、来源 manifest、claim/risk ledger 和验证计划保存在对应 workstream；
2. 私有会议、完整聊天、个人原稿和机器绝对路径不直接提交，只在 workstream 保存最小脱敏摘要、
   哈希和来源限制；
3. feature 先经 `develop` 集成；未合并材料不能改变 Stable docs、STATUS 或 TASKS；
4. 发布到 `main` 后，详细结果、验证、限制和遗留项写入 [`docs/history/`](../../history/README.md)
   的具名 closeout Markdown，并反向链接原 workstream；
5. 原 workstream 路径冻结保留，避免移动造成证据断链。

`docs/history/` 是完成记录，`work/` 是被 Git 忽略的 Attempt Archive；二者都不能替代本目录的
审查上下文或 Git branch 的代码隔离。
