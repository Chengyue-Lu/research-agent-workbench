# GOV-V2-001 风险台账

| ID | 风险 | 控制 | 状态 |
|---|---|---|---|
| GOV2-AUTH-001 | 把“减负”误成放松 DONE、Task definition、main release 或 authority/data/permission 门禁。 | 保留硬不变量并增加 R2 authority/adversarial evidence；负面测试覆盖。 | controlled |
| GOV2-INFER-001 | AI 低报 R0 绕过共享契约审查。 | changed paths 与声明取最大风险；Schema/Registry/协议/治理敏感路径自动升级。 | controlled |
| GOV2-SEMANTIC-001 | 路径分类无法证明 diff 的 Method/Claim/Gate 语义。 | 已知高风险文件列入 R2；authority declaration 可升级；R1/R2 cross-owner review 保留语义判断。 | accepted limitation |
| GOV2-CODEOWNER-001 | 只覆盖 R2 路径会让 R1 review 成为软要求；覆盖整个公共文件又产生 false positive。 | 第一版 CODEOWNERS 保守覆盖 R1/R2 shared surfaces，删除全局 `*`；模块拆分后再收窄。 | controlled |
| GOV2-STALE-001 | stale base 降为 warning 后，旧分支可能与新 shared contract 不兼容。 | PR diff 取 merge-base；GitHub merge ref、required CI、冲突检测与 merge 前复核承担集成阻断。 | controlled |
| GOV2-RULESET-001 | 仓库政策和 GitHub ruleset 不一致产生假保护或锁死分支。 | 代码先合并并确认 check 名；随后按 rollout 回读两份 ruleset，禁止提前写成完成。 | open until rollout |
| GOV2-TASK-001 | feature 置 DONE 会让机器结构检查被误称为完成判断。 | Verification 必填；文档明确结构资格与 owner judgment 分离；DONE 仍终态不可变。 | controlled |
| GOV2-HISTORY-001 | 删除逐 Task closeout 后失去关键决策证据。 | 重要 workstream/migration/governance/release/failure 继续触发 History；普通 PR 由 Git 保存。 | controlled |
