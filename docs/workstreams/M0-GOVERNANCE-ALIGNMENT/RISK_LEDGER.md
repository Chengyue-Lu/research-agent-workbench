# M0-008 风险与验证

日期：2026-10-10；R2；依据见 [Task Packet](TASK_PACKET.md)。本地与实际远端同步见 [结果](VERIFICATION.md)、[线上记录](REMOTE_SYNC_RECORD.md)；完成候选尚未合并。

| 风险 | 必须保持的边界 | 验证与当前缺口 |
|---|---|---|
| 人员规则撤销被扩大为无审核/无权限 | 风险、任务资格、实际授权和实质 blocker 继续适用 | 105项限定正反测试通过；review层同步且hard层不变，具体合并/发布另需指令 |
| Runtime 身份字段与开发人员混淆 | actor/授权/accountable 字段及历史接受原件不变 | diff 限于机器政策、模板、直接 tests 与进度文档；未改运行 Schema |
| 本地政策宣称远端已同步 | 在线 ruleset 才证明实际门禁 | fresh四before/两PUT response/四after完整保存并核对，actual after与提案一致 |
| 审核便利损坏 hard gates | PR、required checks、latest base、合法拓扑、conversation、force/delete 保护保留 | 两hard层不发PUT，after规范字段逐项等于before，active/零bypass；两review层bypass清空 |
| 文档合并被当实现完成 | PR141 仅接受定义，PR140 候选独立 | 本分支M0-008提出DONE，72旧DONE行保持原内容；PR142待合并，三桥接未改状态 |
