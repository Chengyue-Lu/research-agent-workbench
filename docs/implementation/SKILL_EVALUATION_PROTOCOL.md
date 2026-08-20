# Skill 双臂评估与准入证据协议

维护说明：路诚钺负责评估设计、冻结条件、checker、人工盲评和准入决定；黄毅可以通过 API/模型执行提供脱敏输出、Receipt 与 Agent Trace。路诚钺不为评估修改 API 实现或测试。

## 1. 目的

本协议回答一个窄问题：相对同一模型在同一任务上的基线，加载某个固定版本 Skill 是否产生可复现净收益。它不比较“哪个模型更聪明”，不自动批准 Skill，也不把 fixture、Schema PASS 或第二个 Agent 的主观赞同当成价值证据。

评估单位是同一输入上的一对执行：

```text
frozen task contract + frozen input
  ├─ baseline: same provider/model/config, Skill unavailable
  └─ with-Skill: same provider/model/config, exact Skill hash loaded

outputs -> deterministic reports -> blind human review -> reveal -> human Decision
```

机器契约为 `skill_evaluation`，确定性检查输出为 `deterministic_check_report`。`rwb skills eval assess` 只判断证据是否足以交给人类作准入决定，最高 verdict 是 `eligible-for-human-decision`，不会写入 accepted Registry。

## 2. 每个候选自行声明案例覆盖

不建立所有学科共用的一套固定题库。每份评估在 `protocol.required_case_kinds` 中声明适合该 Skill 的最小覆盖，可从以下类型选择：

- `trigger`：应该加载并产生价值；
- `non-trigger`：不应加载，或加载后不应改动结果；
- `missing-input`：缺少关键输入时应停止；
- `adversarial`：提示注入、诱导夸大或数据边界攻击；
- `boundary`：方法适用范围边缘；
- `regression`：历史失败案例；
- `routing`：与相近 Skill 的区分。

当前 `claim-preserving-rewrite` 至少需要 trigger、non-trigger、boundary 和 adversarial 四类；推导、实验设计、仿真 V&V 等 Skill 应使用各自方法相关的判据，而不是复用写作质量分数。

简单、单约束案例只能校准执行与 checker，不能单独证明 Skill 增量价值。历史困难任务设计、
compact-contract 诊断臂和停止规则见[原 K-MS-1 诊断计划](../workstreams/chengyue-lu-mode-skill/DIAGNOSTIC_FORWARD_TESTING.md)。
新的正式评测必须等待 Method Resolution/Skill Need，并采用 Plain、Plain+Tool、Mode+no-Skill 和
Mode+candidate Skill 四臂基线。

## 3. 配对控制

一对执行必须满足：

1. Task contract 与输入文件相同并固定 SHA-256；
2. provider、model、生成配置和 Runtime 相同；
3. baseline 的 `skill_instruction_characters` 为 0，且不能发现候选目录；
4. with-Skill 明确记录候选 source/package hash 与实际加载字符数；
5. 扣除冻结 Task/Input 与 Skill 指令后，两臂的其余基础上下文字符量相同；
6. 两臂使用同一固定版本、同一源码哈希的确定性 checker；
7. 两次执行使用新会话或新 API 请求，不能共享对方输出；
8. 执行顺序应跨案例随机或平衡，避免总是先跑 baseline；
9. 跨 provider 复现必须作为另一组配对，不能把两个 provider 放在同一 pair 中。

若平台不提供 token，用量写 `unavailable`，不得填 0。只要 provider/model 身份、配置哈希、Context Snapshot 和 wall time 可比，质量评估仍可继续，但 assessor 会警告且禁止声称 token 节省。

## 4. 正式证据

每个 arm 保存：

- 输出文件与哈希；
- 确定性检查报告及 checker/source/output 哈希；
- `Execution Receipt`；
- Receipt 引用的 Attempt、Agent Profile 与 Skill Assignment；baseline Assignment 不得包含候选，with-Skill Assignment 必须锁定候选 source/content/package hash，除此之外两份 Assignment 保持一致；
- runtime 或 mixed 来源的 `Context Snapshot`；
- 当前 `Project Protocol` 及其哈希，用于复核并发、协调成本、数据边界与 trace 约束；
- provider、model 与不含 prompt/密钥的脱敏配置工件及其哈希；两臂的 `model_config_hash` 必须回指该工件；
- token/请求/成本（若平台提供）与 wall time；
- 限制和失败状态。

报告不保存 Chain-of-Thought、凭据、完整 provider response、沙箱外令牌位置或非必要原文副本。

## 5. 盲评

执行者先把输出随机标为 A/B，独立人类在不知道条件的情况下按评估声明的 criteria 分别给 0–4 分，并记录实质错误数、人工纠正分钟数和偏好。完成评分后才揭示 `label_order`。同一个模型充当 reviewer 不能替代人类，也不能被标记为 independent human review。

评分不合成单一总分。任何 Claim 漂移、数据越界、必须条件遗漏或确定性失败都可以单独阻断；清晰度提升不能抵消科研完整性下降。

## 6. 真实 Windows 执行顺序

1. 在真实 Windows 用户上下文确认目标 provider/model；不要在 Codex 沙箱读取或导出令牌。
2. 先运行已实现的合成 provider conformance，确认 API shape，而不是把认证成功等同于模型兼容。
3. 从 fixture evaluation 复制一份到 `runs/skill-evals/<candidate>/<evaluation-id>/`，将 `evaluation_scope` 改为 `live-forward-test`。
4. 冻结 Project Protocol、Task、输入、Agent Profile、两份 Skill Assignment、Skill 和 model config 哈希；为每个 case 创建独立 baseline/with-Skill 会话。
5. 持久化 Attempt、输出、Context Snapshot、Execution Receipt 和确定性报告；不得只保存在聊天记录中。
6. 在揭示条件前完成盲评，再填写 review 与 admission 状态。
7. 执行：

```powershell
rwb validate runs/skill-evals/<candidate>/<evaluation-id> --root .
rwb skills eval assess `
  runs/skill-evals/<candidate>/<evaluation-id>/evaluation.yaml `
  --root . `
  --registry registry/skills/candidates.json
```

只有 assessor 无 BLOCK，且人类另行形成 Decision 后，才能讨论 `trial` 或 `accepted`。Decision 的 metadata 必须绑定 `skill_evaluation_id`、`skill_candidate_id`、`decision_owner: human` 与 `skill_admission_outcome`，避免借用无关批准。即使 outcome 为 accept，更新 accepted Registry 仍是独立、显式、带新哈希的变更。

## 7. 当前证据状态

`examples/evals/claim-preserving-rewrite/fixture-evaluation.yaml` 是故意不完整的 harness fixture。它证明：一个作者预先写好的成功输出和失败输出即使通过 Schema 与哈希检查，也会因 `fixture-only`、案例覆盖不足、无真实收据和无盲评而得到 `not-eligible`。它不是前向测试结果。

## 8. 停止或删减条件

- with-Skill 在科研完整性、任务成功和遗漏控制上没有稳定改善；
- 增加的上下文、时间或人工校核超过改写收益；
- non-trigger 经常误触发；
- 只有特定模型或泄漏预期答案时才有效；
- 确定性 Gate 误报导致大量人工绕过；
- Skill 与基础提示效果无可区分净收益。

出现上述情况时优先缩短、拆分、降级为 reference 或删除候选，不增加 reviewer 层数来挽救。

当前协议仍有明确边界：字符数相等不能证明提示语义完全相同，配置哈希依赖执行器诚实采集，少量 pair 不能支持统计推广，自述式时间戳和盲评字段也不等同于外部签名。高风险准入应增加预注册协议、独立保管的匿名输出、重复运行或跨模型复现；这些增强按候选风险触发，不下沉为所有学科的固定全局流程。
