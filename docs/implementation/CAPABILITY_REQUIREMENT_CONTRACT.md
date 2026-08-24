# Capability Requirement Contract

状态：Active implementation contract

## 1. 结论

`Capability Requirement` 是 Method 输出的不可变需求身份。它只回答“后续供给必须满足什么”，不回答
“当前有什么可用、由谁实现或选择哪一个实现”。正式边界为：

```text
Task.required_capabilities
        =
Method Resolution.action_decisions[].capability_requirements
        ↓ exact requirement_id
Capability Requirement integrity index
        ↓ exact path + raw-byte SHA-256
Capability Requirement demand contract
```

八个 M8 Method Resolution 共引用四个重复需求：`document-read`、`literature-search`、
`bounded-compute`、`research-contract-check`。跨 Task 复用证明了独立身份的必要性，因此 M9-001
采用四份独立文档和一个小型完整性索引；没有建立 supply discovery、active/latest、fallback 或路由
Registry，也没有修改任何 M8 Task、Mode、Action 或 Resolution 身份与原始字节。

## 2. 身份与演化

- `requirement_id` 是精确、不可变的需求身份；`schema_version` 只是文档语法版本，不是“当前版本”指针；
- 完整性索引 `registry/capabilities/requirements.json` 为每个身份固定唯一文档路径和原始字节 SHA-256；
- 已进入 `develop` 的同一 `requirement_id` 受 published identity policy 保护，不能删除、移动或原地改写；
- 需求语义变化必须创建新的 `requirement_id`，保留旧身份；旧→新解释由 M9-006 的显式 migration 处理；
- 当前 M8 的裸字符串不是模糊 selector：它只能解析到索引中的唯一不可变身份，不存在 active/latest 选择。

这套规则避免为四个稳定需求提前引入通用版本解析框架，同时保证历史 Resolution 不会随索引更新而
静默改变含义。

## 3. 最小需求语义

每份 Requirement 必须声明：

| 区域 | 含义 |
|---|---|
| `objective` | 目标能力，不描述实现者 |
| `applies_when` / `not_applicable_when` | 有界适用与排除条件 |
| `required_inputs` / `required_outputs` / `required_artifacts` | 供给必须消费和产生的契约 |
| `constraints.permission_ceiling` | 文件、网络和外部写入上限；不能授予 Task/Human 未授予的权限 |
| `constraints.data_egress` | 禁止或 allowlist-only 的数据出口上限 |
| `constraints.side_effects` | 无副作用或 allowlist-only 的副作用上限 |
| `verification_expectations` | deterministic、semantic、Human 三类期望；不等于验证已经发生 |
| `unsatisfied_requirement` | Method 保持不变、禁止 supply binding，并交给后续 Capability Resolution |

`unsatisfied_requirement` 不产生 `available / gap / blocked` 状态。尤其“当前没有实现”不能修改
Method Resolution 的 `resolution_status`；供给发现、差距和阻断属于后续 Capability Resolution / Snapshot。

## 4. 确定性验证

Repository validation 会检查：

- Requirement 与完整性索引分别符合 JSON Schema；
- index identity/path 不重复，所有路径都能解析到已加载的 Requirement；
- index identity 与文档 identity 一致，raw-byte SHA-256 无漂移；
- 每份已加载 Requirement 都在 index 中，index 不遗漏已发布文档；
- Method Resolution 中每个 `capability_requirements` ID 都能闭合到 index；
- 对同一 Task，Task `required_capabilities` 与各 Action Decision 的 Requirement 并集精确相等；
- Schema 拒绝 Provider、Model、Adapter、具体 Tool/Skill、availability、gap、blocked、fallback 和价格路由字段；
- Governance 将 Schema、Python contract、index 和文档视为 R2，并保护发布后的 `requirement_id`。

Schema 通过只证明需求文档结构、引用和边界可重复，不证明某个供给实际可用、符合约束或具有科研净
收益。实际 supply conformance 和替换 fixture 分别属于 M9-005/M9-006。

## 5. Python 消费面

`CapabilityRequirementSet.load()` 读取完整性索引，验证路径、identity 和 raw-byte hash；
`require([...])` 只按精确 `requirement_id` 返回需求对象。该接口没有 candidate、Provider、Model、
Adapter、availability 或 fallback 参数，因此不同供给实现可以消费同一需求对象，但不能反向修改需求。

M9-001 不把该对象接入现有 legacy `resolve_task()`，因为后者仍生成 Skill-bound 兼容 Assignment。
正式供给绑定必须等待共享的 Resolved Capability Snapshot 接口，而不是把 M9-001 偷接到 Runtime。
