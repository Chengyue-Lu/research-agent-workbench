# M0-008 风险与验证

日期：2026-10-08；R2；依据见 [Task Packet](TASK_PACKET.md)。本地切片验证见 [结果](VERIFICATION.md)，实际远端规则未修改，完整任务保持 IN_PROGRESS。

| 风险 | 必须保持的边界 | 验证与当前缺口 |
|---|---|---|
| 人员规则撤销被扩大为无审核/无权限 | 风险、任务资格、实际授权和实质 blocker 继续适用 | 人员解耦正例与路径/证据/任务/拓扑等反例在105项限定测试中通过；远端同步待闭合 |
| Runtime 身份字段与开发人员混淆 | actor/授权/accountable 字段及历史接受原件不变 | diff 限于机器政策、模板、直接 tests 与进度文档；未改运行 Schema |
| 本地政策宣称远端已同步 | 在线 ruleset 才证明实际门禁 | 实际四层 before JSON已只读保存；尚未修改，无 after 证明 |
| 审核便利损坏 hard gates | PR、required checks、latest base、合法拓扑、conversation、force/delete 保护保留 | 本地正反检查通过；线上修改前 hard 层 active且零bypass，尚未同步，未来须再比较 |
| 文档合并被当实现完成 | PR141 仅接受定义，PR140 候选独立 | M0-008 未置 DONE，72 原 DONE 行完全一致；三项桥接未改状态 |
