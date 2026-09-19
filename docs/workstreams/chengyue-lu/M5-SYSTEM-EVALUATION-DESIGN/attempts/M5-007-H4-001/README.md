# M5-007 H4a implementation Attempt

Owner: Chengyue-Lu. Execution interface reviewer: let778750-cpu. Risk: R2. Delegation: none.
User authorization: start implementing the prepared H4 packet, beginning with H4a actual evidence.
Accepted base: `171d4654f88e926f239cdf25bc8168109b81f391`; preparation head:
`baebdadc6619b171d99456835d32d9354fc5cdff`. Branch: `feature/m5-007-harness-evidence`.

## Task snapshot

Implement a versioned Evaluation-owned run-evidence record and independent verifier over accepted
H3 execution/replay. Bind every scheduled case/phase/replicate/arm/Attempt/slice to frozen qualification
and actual replay-valid M6/M11 evidence. Preserve failures, retry and unstarted slots. Reject planned
facts substituted for actual observations, incomplete closure and changed evidence.

Inputs/read set: the [H4 packet](../../M5-007_H4_PACKET.md), M5-007 Task and repository guidance,
H1-H3/Protocol/qualification/overlay/pin interfaces, their direct schemas/tests/fixtures, M6/M11 receipt
and fact consumers, Schema/catalog/validation/coverage/CI integration surfaces, this workstream.
Profile: main implementation agent accountable to Chengyue-Lu. Required Skills: none.
Write set: `evaluation/harness_evidence.py`, its new Schema and tests/fixtures, necessary catalog and
coverage/consumer records, implementation/status/workstream documentation and this Attempt.

Budget: one bounded H4a feature candidate, local synthetic execution only. Scoped correctness/coverage,
repository/package/governance checks precede push; hosted CI may run asynchronously. No live API,
Human scoring, release, or merge. Stop and retain evidence if a repair needs changing accepted treatment,
Runtime/Resolver/Human authority, an unclosed actual-fact contract, or unrelated worktree changes.
H4b/H4c and H5 remain subsequent implementation nodes; M5-007 stays IN_PROGRESS.

## Capture and verification

The initial intake was not fully captured. Subsequent retained tool arguments/results and local check
outputs are partial observable evidence; missing provider frames/native events or their timestamps
will not be reconstructed. Host paths are normalized; secrets and hidden reasoning are excluded.
Source pins and local verification are in [verification.json](verification.json). Logs have machine paths
normalized; both original local and archived hashes are retained. Initial diagnostic output is separated
from final verification and is not acceptance evidence.

## Delivered candidate and evidence

`evaluation_harness_evidence@1.0.0` records all frozen slots and required slices, reads actual facts only
after H3 independent replay, and recomputes the whole record under caller-owned expected pins/context.
Failed/retried/blocked/unstarted entries remain distinct. A completed slice must match its qualification;
replay-valid actual drift remains a failure. Public APIs and boundaries are in the
[Harness contract](../../../../../implementation/SYSTEM_EVALUATION_HARNESS.md).

- [Focused tests](h4-focused-final.log): 14 PASS, 606.769 seconds under branch coverage.
- [Multi-replicate delta](h4-replication.log): 1 PASS, 45.851 seconds; two cases, pilot plus three
  confirmatory replicates, 64 distinct reserved Attempts with 63 explicitly unstarted after a stop.
- [Coverage](h4-focused-coverage.json): new module 102/102 statements and 32/32 branches;
  all three changed source files have no uncovered changed lines/branches. These are scoped results.
- [Validation/Schema](h4-validation.log): 31 PASS; [contracts/documentation/policy](h4-contracts.log):
  49 PASS. Inventories include the new Schema/kind and critical module's positive/negative evidence.
- [Repository](h4-repository.log): 186 checked, zero errors/warnings.
- [Package](h4-package.json): direct wheel and sdist-wheel resources identical, four clean install probes PASS.

The [initial diagnostic run](h4-focused.log) failed because a fixture cloned a live ProviderError and a
resource regeneration overlapped a read. The final run removed live handles from the cloned fixture and
used stable resources; implementation source was unchanged. The replication delta adds coverage for a
different schedule. Full repository compatibility/global coverage remain the hosted CI obligation.

The delayed [capture exporter](export_capture.py) preserves available tool payloads with explicit gaps.
Implementation commit: `aa34d6a07c5e1b710cb156ed83e1453faccf739b`. [Governance](h4-governance.log) PASS;
[Trace validation](trace-validation.json) has no BLOCK and retains `TRACE-CAPTURE-DELAYED`.
The [Trace index](trace/INDEX.yaml) binds the partial captured payloads. Export timestamps describe
export time; initial reads, some patches/waits and final publication are explicit capture gaps.
Cross-owner review by Huang Yi and exact-head CI remain pending; M5-007 stays IN_PROGRESS.
