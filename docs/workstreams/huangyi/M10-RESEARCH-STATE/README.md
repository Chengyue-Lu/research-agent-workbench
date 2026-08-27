# M10 Phase C Candidate Workstream

- 实现责任人：黄毅（GitHub `let778750-cpu`）
- Task owner / R2 审查人：路诚钺（GitHub `Chengyue-Lu`）
- Tasks：`M10-001 → M10-002`（当前 PR 继续沿 module chain 推进）
- 基线：`develop@6b16129`
- 分支：`agent/m10-research-state`
- Authority basis：Issue #38 的 `R2 architecture review — ACCEPT`，只授权 bounded implementation

## Module progression

PR #44 先按 normalized governance 收缩并独立接受 M10-001；owner 随后明确允许在同一 module PR
按 `M10-002 → M3-009 → M10-003` 逐层扩展，每层保留独立 commit/evidence，最终按完整链重新审查。
旧完整 head 保存在 `archive/pr44-pre-split-20260826` 仅供审计，不构成 canonical 状态或后续合并来源。

当前两层包含 M10-001 Research State，以及 M10-002 Research Attempt lineage / Research Failure。
M10-002 不修改 legacy Attempt，而以 sidecar 精确 pin 已有归档；M3-009 Method Trace 与 M10-003
fresh-process Gate 尚未带入，状态保持 BLOCKED。

Human Decision 不再使用平行 record Schema，而是复用现有 kernel Decision research object。
最终表示、科学判断和 DONE 接受仍属于具名 Human/R2 审查。

详见 [M10-001 契约](../../../implementation/RESEARCH_STATE_CANDIDATE_CONTRACT.md)、
[M10-002 契约](../../../implementation/RESEARCH_ATTEMPT_FAILURE_CONTRACT.md)、
[风险台账](RISK_LEDGER.md)和[验证证据](VALIDATION.md)。
