# M8-004 验证证据

状态：DONE；PR #30 最终本地集成验证通过，远端 CI 待更新 head。

验收证据：v0.1/v0.2 Mode 与 Action 版本并存；两个 migration record 固定 source/target/action 的 exact
ref/path/raw-byte hash。迁移重放不再从当前 Registry 推断唯一或最新 Action 版本。负面测试覆盖 pinned
Action hash drift；正面测试证明向 `simulation@0.2.0` 追加 `SIM-A3@2.1.0`、旧 target Mode 仍固定
`SIM-A3@2.0.0` 时，旧 migration 继续通过。

最终本地完整测试：334 passed、3 skipped；repository validation：`validated=124 errors=0 warnings=0`；
`git diff --check`：PASS；远端 CI 在提交后记录。
