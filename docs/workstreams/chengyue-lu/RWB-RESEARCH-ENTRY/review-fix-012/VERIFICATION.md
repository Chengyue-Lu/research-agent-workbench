# PR140：共享测试 helper 的 CI 消费者修复

2026-10-11；对应[最后 P2](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140#discussion_r4238260123)。本切片来自 `766bf45ccde4637684e2100480e9f1577cc61662`，修复后仍是未合并代码候选。

问题是 helper-only 修改命中了 direct-test 分支，但映射只列新增回归，遗漏已有直接消费者；entry 组件不会再补齐它们，因此计划可以绿色而没有选择受影响测试。

[组件映射](../../../../../tests/ci_components.json)现在补齐五个 helper 的直接消费者：[driver](../../../../../tests/test_entry_driver.py)的七个直接测试消费者，以及 bridge_flow→intake_call、caller→handoff、intake→cli、intake_call→caller。既有 deadline/constraints 边保持。两 support 的间接关系原样记录，本切片不引入递归 planner 算法或修改生产 Runtime。

## 实际验证

- 用 `766bf45` 的原始 policy 运行现有实际 planner：driver 漏六项，其余四个 helper 各漏一项，均无 unknown path；不是从评论生成的模拟结果。
- 用修正 policy 对同五个 helper-only 输入运行同一 planner：全部要求的消费者选中，unknown path 为空。
- [planner 回归](../../../../../tests/test_ci_components.py)与 [metadata 回归](../../../../../tests/test_ci_component_metadata.py)：32 项通过，0 failure/error/skip。包含全部直接消费者、既有消费者缺失和 helper 删除后的可见性。

测试由测试窗口统一执行；完整原 policy、计划对照、命令输出、测试汇总与 worker 通信保留在忽略档案 `.rwb/review-fix-012/`。旧 API、来源资格和运行证据不重跑或改标。

本切片仅更改映射、对应测试与本验收导航；没有产品代码、Schema、Registry、测试授权、Key、生产账本或付费调用。Ready for review 由 PR 实际状态单独记录，不代表 review 接受、merge 或整个 M Task DONE。
