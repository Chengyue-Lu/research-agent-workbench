# 测试与证据策略

先验证契约、引用和边界，再验证实际集成消费；模型行为、Skill 评价与科研正确性分别取证。
测试围绕能改变判断的具体风险，保留失败/unknown，不将测试框架扩展为第二套控制平面。
日常组件/安装/多版本检查规则见 [Development](../DEVELOPMENT.md#6-变更检查清单)。

## 证据层级

| 层级 | 必须看到什么 | 能证明什么 |
|---|---|---|
| 结构与契约 | Schema、identity/revision/hash、引用闭包、权限/输出/预算正反例 | 文件与确定性不变量合格 |
| 单模块行为 | 正常产物、真实故障反例、调用前/后停止行为 | 该模块的实现行为 |
| 桥接集成 | producer 实际返回 refs → consumer 重载/使用 → 下游输出；fresh 角色及实际交接 | 声明模块之间接合可达 |
| live API/Tool | exact source/config/Task/permission、实际请求/响应/Tool/usage/failed/unknown、独立冷回放 | 被测 binding 与场景的实际执行 |
| Skill 增量 | 合格冻结同输入 baseline/with-Skill、独立评价与预先冻结判断规则 | 该范围的 Skill 评价结果 |
| 系统科研评价 | 获批 case/provenance、完整 runset、盲审与人类判断 | 有边界的质量/效率或净增量结论 |

fixture 只能证明相应结构/行为，不能产生 live/source/Skill admission。Slice Receipt `completed` 也不产生
whole-Task completion、Claim accepted 或 Human approved。平台测试另核实际 permission/sandbox、launch/collect/cancel；
提示词声明不能替代执行约束。

## 最小桥接测试记录

每例明确目的、启用模块、实际输入、producer 输出、contract、消费方与输出断言。人工合成材料足以测试接口，
真实科研案例留给科研评价；不要求每例开启全部 Source/Evidence/Claim/Skill 分支，也不固定角色或研究 DAG。

main 的 0..N child 决定、fresh child 请求、child 结果/工件 refs 与新 main 消费分别留证。
测试中的 child 数、预算、事件和深度是配置实例；未开始、失败、取消和 unknown 不写成完成。
每个 Task 和整 Run 统一累计实际 attempted calls/usage/预占/wall time，不因 fresh Session 或阶段切换重置。

关键负例覆盖真正边界：未授权输入/读写、hash drift、未知 Method/Mode、Human Gate 未决、所需 Skill 未载入、
Supply gap/ambiguous、actual binding drift、输出/Trace 缺口和预算不足。先核整 wave，再允许 child 出站。
冷回放只重载文件与重做确定性检查，不调用 Provider/Tool。

## 模型与人类评价

固定输入/来源、必须和禁止的事实关系、Claim ceiling、必要工件及人类决定点；避免把措辞快照当作正确答案。
Skill paired 评价和 system-level 四臂评价按各自 [Skill protocol](SKILL_EVALUATION_PROTOCOL.md)、
[系统 Protocol](SYSTEM_EVALUATION_PROTOCOL.md)/[Harness](SYSTEM_EVALUATION_HARNESS.md)执行，通用桥接测试不替代这些 Gate。

真实 kill/恢复、长期 Human waiting、跨项目检索与新平台行为只在有相应授权 Task 和场景时测试；
历史注入样例从 [compatibility/history](../history/README.md)查找，不自动扩大本轮矩阵。

提交前复核适用测试、链接/公开发行闭包和未证明范围。删除已失效的实现快照测试、与平台重复且无新保证的检查，
以及不会改变判断的指标或多层自检；保留有决策价值的失败反例和正常消费路径。
