# PR92 changed-order invocation correction

Owner Chengyue-Lu; Audit TEST-PERF-002; R2; Skills [].

Implementation `f3fb6aa07d1e1f25fc7bf21e1d75f9a1c2c2496c`, parent `99960397b0f1daa7c09f3575f8e5ef9bdb9d080c`,
accepted develop `b44a03e17c3d751c12667a39f6d5b7b6fcf91a1c`.
The working-tree validation below predates this commit; all three tested file hashes
were independently compared with the resulting immutable Git blobs and match.
This does not convert the local run into an exact-head hosted receipt.

The [cross-owner P2](https://github.com/Chengyue-Lu/research-agent-workbench/pull/92#pullrequestreview-5287223195)
reproduces on the original source and is rejected after this correction. The
existing same-command changed-selection acceptance assertion was replaced by
explicit negative tests and a separate legal unchanged-order control.

- Both Python3.11/3.13:18 related cases PASS; documentation10 PASS.
- Isolated pair-only coverage:9 cases PASS,125/125 executable lines and42/42 branches.
- Independent bounded review:three targeted cases PASS, no actionable finding.
- No selector, witness, worker, threshold, source measurement roots, exclusion,
  production activation or execution reuse authority changed.

The [validation](checks/validation.json), [before](checks/reproduced-before.json),
[after](checks/reproduced-after.json), [independent review](checks/pr92-fix-independent-review.md)
and [source identity](checks/pr92-fix-independent-sourcehash.json) retain their scopes.
The [raw archive](checks/raw-evidence.zip) and [manifest](checks/raw-manifest.json)
retain original logs, interpreter/argv records, source snapshots, initial inherited
coverage configuration warning/data and corrected one-script coverage data.
The initial local measurement is not repository coverage; it was not discarded.

The earlier native hosted run35817729318 remains evidence only for9996039. New
HEAD hosted obligations and renewed cross-owner approval remain necessary. This
archive does not resolve the GitHub CHANGES_REQUESTED review or authorize merge.

Trace capture begins after local work. The retained review/reproduction/results
and independent audit are source-bound; unrecorded tool/message details and later
publication are disclosed as capture gaps rather than reconstructed executions.
Original historical attempts remain unchanged.
