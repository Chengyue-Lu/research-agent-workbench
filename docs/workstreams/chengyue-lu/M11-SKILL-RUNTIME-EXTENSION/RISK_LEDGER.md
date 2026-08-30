# M11 Skill Runtime Extension 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| M11-SRE-LEGACY-001 | fact | historical replay Skill 被 projection 重新解释为 new-binding eligible。 | publisher 要求 current Lifecycle、完整外部 evidence 与 named Human acceptance；生产 index 保持空。 | controlled by publisher/legacy negative tests |
| M11-SRE-SECOND-REGISTRY-001 | fact | projection 变成可独立编辑的第二套 Skill 真值。 | projection 必须由 exact Release/Lifecycle 确定性重算，index 固定 path/hash，published identity append-only。 | controlled by derivation/hash/governance tests |
| M11-SRE-HISTORY-001 | fact | Need/Evaluation/Lifecycle 历史泄漏进 Runtime context。 | Schema allowlist + forbidden-field adversarial tests；Runtime closure只含 projection。 | controlled by Schema/source/import tests |
| M11-SRE-AUTH-001 | fact | eligibility 或 boundary metadata 被当成 permission、Method、Claim 或 Human authority。 | projection/Supply/Bundle boundaries 全部 false；View 仍计算最严 intersection；Host 不授予 authority。 | controlled by Schema and View/Host reuse test |
| M11-SRE-BINDING-001 | fact | Supply Report 与 projection identity/required Tools/capability/I/O/boundary facts 漂移，或只比较粗粒度 policy 而漏掉 roots/forbidden set。 | exact path/hash ref + deterministic cross-object validator；roots 采用 segment containment，forbidden set 只能增强；任一 drift 仅使该 Skill candidate fail closed。 | controlled by Registry/Bundle adversarial matrix |
| M11-SRE-CORE-001 | fact | 可选 Skill extension 反向成为 no-Skill/direct Tool Core 前置。 | 空 projection index 合法；Core manifest 保持 `enabled:false`；独立 zero-Skill regression。 | local full suite controlled; hosted review pending |
| M11-SRE-RUNTIME-001 | fact | M11-006 形成 Skill-specific dispatcher/session/fallback。 | 只扩展 explicit Bundle closure 与 Supply qualification；View/Host/Trace/Receipt 不按 supply kind 分派。 | local full suite controlled; hosted/cross-owner review pending |
| M11-SRE-EVIDENCE-001 | fact | synthetic fixture 被误报为真实科研效益或 Provider 可用性。 | fixture scope 固定 synthetic bounded；文档与验收明确只证明 contract closure。 | active |
