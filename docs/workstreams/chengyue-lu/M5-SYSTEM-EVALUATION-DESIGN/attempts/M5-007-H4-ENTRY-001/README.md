# M5-007 H4 entry preparation

Date: 2026-09-19. Task/Evaluation owner: Chengyue-Lu. Execution interface reviewer: let778750-cpu.
Risk: R2. Delegation: none. This record covers preparation requested by the user, not H4 implementation.

## Accepted baseline

- Develop: `171d4654f88e926f239cdf25bc8168109b81f391`, PR89 merged at `2026-09-18T09:00:46Z`.
- [Named H3 approval](https://github.com/Chengyue-Lu/research-agent-workbench/pull/89#pullrequestreview-5245682418)
  binds `d725f7eda335011a62e7c95a27db4b9d7c31b059` and base `51dc3ab477f21f18ac3829bf553b5b779d49a4fe`.
- Accepted merge tree equals the reviewed H3 candidate tree. [H3 CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35310496297)
  succeeded; the reviewer independently verified 1410 tests on each Python version and both coverage gates.
  These are accepted-baseline results, not evidence of H4 implementation.
- M5-006/M6-008/M11-004/006/007 are DONE; Gate B is SATISFIED; M5-007 is IN_PROGRESS and M5-008 remains BLOCKED.

## Prepared entry

Independent branch: `feature/m5-007-harness-evidence`, based directly on the accepted develop commit.
The primary develop checkout and prior H3 worktree are preserved. A fresh Python virtual environment
was created for this worktree; dependency/import/CLI and targeted baseline checks are recorded in the
work log and [verification.json](verification.json): [63 baseline tests](baseline-checks.txt),
[10 documentation tests](docs-checks.txt), and [repository validation 186/0/0](repository-checks.txt).
No copied virtual environment or old absolute import path is used.

The [H4 packet](../../M5-007_H4_PACKET.md) specifies H4a actual-fact reconciliation, H4b blind-review/reveal,
and H4c metric/analysis joins, with exact input responsibilities, bounded writes and negative acceptance.
The next implementation begins with H4a; preparation does not establish a new Task or complete M5-007.

This is a partial entry record, backed by Git/GitHub evidence and retained local check outputs. Initial
tool conversations/native events were not fully captured; no missing event chronology is reconstructed.
Before implementation, a separate H4 Attempt will freeze its inputs and capture policy. Previous H3
archives remain immutable. No real Provider/Tool execution, Human scoring, admission or merge is authorized
by this preparation record.
