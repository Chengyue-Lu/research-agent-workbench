# Protocol Profile contract

`Protocol Profile` 是对既有 Research Mode / Mode Action 施加的、可版本化的有界方法标准约束。它回答：

- 该标准子集何时适用、何时不适用；
- 对已触发 Action 还需满足哪些标准特有的方法义务；
- 哪些证据类型与附加 Human Gate 将来应被 Method Resolution 或项目协议纳入。

它不回答执行顺序、供给选择或科研结论是否成立。

## 首批对象

完整性索引为 [`registry/protocol-profiles.json`](../../registry/protocol-profiles.json)，当前固定两份对象：

- `prisma-systematic-review-reporting@1.0.0`：用于明确声明为系统综述或 PRISMA-aligned 的有界证据综合；
- `simulation-vv-assurance@1.0.0`：用于需要数值误差、uncertainty、外部 validation 与 intended-use adequacy 判断的仿真任务。

两份对象都是 `bounded-subset`，且 `compliance_claim = not-established`。Profile 的结构验证通过不等于
PRISMA 或任何 V&V 行业标准的完整合规认证。

## 关系闭包

```text
Research Mode ref
       ↓ compatible boundary
Mode Action ref + exact Action hash
       ↓ scope only, no ordering
Protocol method obligation
       ├── Evidence expectation ref
       └── additive-only Human Gate expectation ref
```

索引固定 `profile_id + version + path + raw-file SHA-256`。Profile 中的 Action 引用也固定 exact
`action_ref + content_hash`。Repository validator 会阻断：

- 未知 Mode / Action 或 Action hash 漂移；
- Action 所属 Mode 不在 `compatible_mode_refs`；
- obligation 引用 Profile scope 外的 Action；
- 未声明的 evidence / Gate expectation；
- scope 中没有任何 obligation 覆盖的 Action；
- 重复 identity、path、Action、obligation、evidence 或 Gate；
- 未入索引、错误路径或索引 hash 漂移。

已发布的 `profile_id + version` 不可原地修改或移动；语义变化发布新版本并保留旧版本。

## 与 Mode、Action、Skill、Runtime 的边界

- Mode 定义证据类型、Claim ceiling 与学科方法差异；Profile 不复制这些规则。
- Action 定义 trigger、工件、Claim effect、Gate、stop/blocked semantics；Profile 只引用 Action，并增加
  标准特有义务与 Gate expectation。
- Profile 的 Action 列表是适用范围集合，不是步骤列表、依赖图或全局研究 DAG。
- Skill / Tool 可以帮助履行 obligation，但 Profile 不绑定或推荐任何供给。
- Provider / Adapter / Runtime 不读取 Profile 来自行路由，也不能借 Profile 放宽 Method、Claim、Gate、
  permission、data-egress 或 side-effect 边界。
- `additive-only` Gate expectation 只能增加待解析 Gate；不能删除、替换或视为已完成人类批准。

M9-004 只冻结 Profile contract、两份 bounded fixture 和确定性验证。如何由具体 Task/Project 显式选择
Profile、如何把其 obligation 合并入新的 Method Resolution，以及对应的执行留痕，留给后续独立契约；
本轮不修改 Phase A 已发布的八份 Method Resolution。
