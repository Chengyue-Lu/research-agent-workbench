# 隔离合成桥接：报告与复用入口

2026-10-08 · AUDIT-RWB-CHAIN-002 · PR140 未合并开发候选。当前工作用于核对真实接口接合与实际产物消费，材料为隔离合成输入；不宣称真实科研、正式 Source/Human/Skill 资格或 M12 完成。

- [桥接报告](ROOT_REPORT.md)：实际输入、下游消费、真实 API 成功与停点。
- [覆盖与缺口](COVERAGE.md)：离线断言、真实路径和未覆盖边界。
- [接口使用说明](USAGE.md)：可复用调用顺序、显式配置与 trusted caller 责任。

以上报告保存测试数量与最新 Attempt 结果。本导航不重复这些会更新的数值。JSON、Trace 和事件是复验附件，先读可读报告。旧 COMPLETION 和 manifest 保留原 65 项离线/零付费 API、Tool 的历史范围；不同 Attempt 的局部结果不能拼成同一次全链成功。

角色职责使用内置必载 baseline，main 根据实际输出决定 0..N 个子 Task。外部 prompt 变体和三个方法 Skill 仍为 test-candidate，未加载、未准入；非空 required Skill 仍阻断。工具按实际 Task 需要显式开启，Guide 保持独立只读。
