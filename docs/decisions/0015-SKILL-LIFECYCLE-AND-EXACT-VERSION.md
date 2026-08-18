# ADR-0015：Skill 准入历史、分配生命周期与精确版本

状态：Accepted

日期：2026-08-19

责任人：路诚钺

## 背景

M7-004 将三个 `0.1.0` Skill 原型迁移为历史对象：两个方法原型保留为 `legacy`，交接 wrapper
进入 `deprecated`。但原 accepted Registry 只有 `status: accepted`，同时承担了“曾经准入”、
“文件可解析”和“当前可分配”三种含义。Resolver 还只按 Skill ID 选择唯一版本，导致两类风险：

- 为保留历史 Assignment 而留在 Registry 的原型仍可能进入新任务；
- 引入修订版本时，未带版本的 Task 可能随 Registry 更新改变解释。

历史 Assignment 已经保存 `skill_id`、版本、内容哈希、包哈希和 Registry digest，因而不需要删除
旧包，也不应把历史回放伪装成普通新分配。

## 决定

### 1. admission status 与 lifecycle 分离

accepted Registry 条目继续使用 `status: accepted` 表示其准入历史，并新增：

- `active`：可进入新 Assignment，也可按精确版本回放；
- `legacy`：只为历史回放和审计保留，不进入新 Assignment；
- `deprecated`：已明确退役，只为历史回放和审计保留。

同一 `skill_id` 可以保存多个版本，但最多一个版本是 `active`。Registry digest 包含 lifecycle，
因此 eligibility 变化会改变新 Assignment 的 Registry lock。

### 2. Task 复用现有字符串表达精确版本

不新增 Task 字段；`required_skills` 和 `forbidden_skills` 的元素支持：

```text
skill-id
skill-id@1.2.3
```

新 Assignment 可以用无版本 ID 选择唯一 active 版本，也可以精确指定 active 版本；Resolver 最终
总是把选择归一化为精确版本并写入 Skill lock。若本地直接提供多个同 ID manifest，无版本 selector
返回 `SKILL-VERSION-AMBIGUOUS`，不能猜测。

### 3. 历史回放必须显式且精确

Registry Resolver 的默认目的为 `new-assignment`，只接受 active 条目。历史回放必须显式选择
`historical-replay`，且 Task 必须写 `skill-id@version`；回放禁止 auto-select。CLI 使用
`--historical-replay` 暴露该意图，不提供静默 fallback。

已有 Assignment 文档继续依靠自身的版本、hash 和 digest 做规范化验证。当前 Registry digest
变化不会改写旧 Assignment；从当前 Registry 重新生成回放 Assignment 会获得当前 lifecycle-aware
digest，但仍锁定同一历史 Skill 内容和包哈希。

### 4. 当前迁移

- `literature-evidence-extraction@0.1.0`：`legacy`；
- `simulation-vv@0.1.0`：`legacy`；
- `handoff-integrity@0.1.0`：`deprecated`。

当前没有 active accepted Skill。这是 Mode-first 迁移的有意结果：新的 Mode action 路由使用
Task/Tool/Human Gate 或尚未准入的 Need；不能为了让 Registry 非空而创建替代包。

## 后果

优点：

- 历史可重放不再等于新任务可选择；
- 多版本可以并存且不会让无版本任务静默漂移；
- lifecycle 变化进入 Registry digest 和确定性测试；
- 原型可以安全退役，无需删除审计证据或修改锁定包。

代价：

- 旧示例若要重新解析，必须增加精确版本和显式 replay 参数；
- 当前新任务不能从 accepted Registry 获得 Skill，直到某个 Mode-derived Need 独立通过准入；
- 直接 `--skill <manifest>` 路径不读取 accepted lifecycle，只适合明确的本地候选/开发输入，不能
  被描述为 Registry 准入或绕过发布 Gate。

## 边界

本 ADR 不授权创建新 Skill、修改锁定 Skill 包、自动迁移历史 Task、选择 Provider/模型、调用 API，
也不证明 lifecycle 机制带来科研质量提升。它只冻结本地 Registry/Resolver 的选择语义。

## 不采用

- 删除旧条目：会破坏历史解析与审计。
- 把 `status` 直接改为 `deprecated`：会混淆准入历史与当前 eligibility，并破坏原 Registry loader。
- 历史 replay 自动回退：会让普通任务在无 active Skill 时悄悄加载旧包。
- 为每个 lifecycle 建独立 Registry：会制造多份真值和 digest 对齐问题。
