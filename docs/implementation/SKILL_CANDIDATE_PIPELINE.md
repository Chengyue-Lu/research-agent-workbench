# Need-first Skill 候选与准入接口

Skill Evolution 是可选 Maintainer 外环；普通 no-Skill/direct Tool/procedure 执行不等待外环。
依据见 [ADR-0013](../decisions/0013-MODE-FIRST-SKILL-DERIVATION.md)与
[ADR-0019](../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md)。

## 触发与传递

```text
Task / Mode / Method 的能力需求或有界执行 Diagnostic
  → 独立 Maintainer triage
  → 可复用 Skill Need
  → scoped source snapshot / metadata discovery / quarantine
  → 最小 candidate / method-security-license triage
  → frozen trial / evaluation / independent review
  → named Human Admission / Lifecycle
  → immutable Release / SkillReleaseProjection
  → Capability Supply Report → Resolver 唯一选择 → Snapshot / Bundle / View
```

来源丰富、下载或 Runtime 失败不自动产生 Need；gap 也可通过 no-Skill/direct Tool、已有 Supply、修订 Task 或 Human Gate 解决。
历史来源 inventory 从 [来源归档](../workstreams/chengyue-lu-mode-skill/SKILL_SOURCE_INTAKE.md)、
[一方 triage](../workstreams/chengyue-lu-mode-skill/FIRST_PARTY_SKILL_TRIAGE.md)与
[社区 triage](../workstreams/chengyue-lu-mode-skill/COMMUNITY_SKILL_TRIAGE.md)查找，不作为当前施工队列。

## 隔离与准入

候选发现只读取声明的 metadata/内容；不默认安装、执行脚本、获取凭据或扩大读取集。
`discovered/triage/reference/quarantine/rejected/trial` 是候选工作状态，不能代替 versioned Lifecycle 的 runtime eligibility。
`trial` 仅表示限定试验资格，accepted Registry entry 仍不自动产生新绑定资格；Runtime 只消费合格 immutable projection。

准入至少核：来源/许可与 exact hashes、未解释安装/删除/上传/凭据行为、trigger/non-trigger、输入输出、权限交集、
成功及边界反例、frozen same-input baseline/with-Skill、必要独立评价和具名 Human Decision。
具体规则由 [Skill Need](SKILL_NEED_CONTRACT.md)、[evaluation protocol](SKILL_EVALUATION_PROTOCOL.md)、
[Lifecycle](SKILL_LIFECYCLE_V2.md)与 [Projection publication](SKILL_RELEASE_PROJECTION.md)定义；fixture-only 不产生 admission。

静态 archive auditor、source snapshots 和历史计数只帮助 triage，不证明安全、净收益或完整审计；
unsupported/skipped 文件与未执行事实保留。发现阶段不运行候选脚本，也不让 Registry 自动安装候选。

## 实际上下文载入

角色必需职责、Task/Profile/输入与预算始终明确；方法 Skill 是合法选择后的可选补充。
每个会话只载入本次 frozen selection 声明的 Skill 正文及必要 references，并保留 exact hash 与实际载入位置。
Skill 数量按 Task/Method/config 的授权上限选择，不把历史两个主 Skill/一个校验 Skill 实例写成平台规则。
旧 Skill-bound Assignment 仅见 [compatibility](../compatibility/README.md)，不作为所有新 Skill execution 的前置。

主协调者默认消费短 metadata、评价结论、冲突与下一步，按需定位原件；候选库规模不扩大任务上下文。
说明过长、职责重复、复核成本大或未观察到所声明增量时，先删减、拆分、拒绝或记录 unknown。
对当前 Run 的固定 Snapshot 不做自动更新、promotion、pruning 或重新选择。
