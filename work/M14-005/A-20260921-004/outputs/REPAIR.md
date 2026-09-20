# PR 97 CI portability repair

Checkpoint ef09089e3b64ca0e39101634fb02b3b852652c66; prior PR head 1b94a38ae13eada52054cced7b5f22666cb506af. Hosted run 35537749515 ran 1414 cases
on each Python execution, with two errors reading historical M11 source commits through Git.
The historical commits are absent from a normal fresh clone after squash integration.

Retain 26 hash-pinned historical blobs as offline ZIP test data (99577 bytes); change only the two
source-byte readers. Snapshot construction checked original Git commit/path bytes against every frozen
proof SHA-256. Historical source is never executed or extracted. Original archives and their hashes,
candidate acceptance/rejection semantics, source-CI API repair, product and policy remain unchanged.

Fresh clone with both old commits absent: before 2 errors, after 2 PASS. Tampering the ZIP member bytes
still fails the original proof hash check. Both affected modules: 43 PASS; docs/policy/public: 44 PASS.
The local editable environment initially had a stale built runtime catalog; rebuilding the existing
editable install restored current packaged schemas. The fresh clone generated its own runtime catalog
and imported product code from that clone. No product workaround was needed.

The current user report authorizes repair of PR 97 CI. Its existing small-fix review waiver remains
limited to PR 97; updated exact head, hosted CI and merge outcome belong in that PR. PR 98 is separate R2
work and is not automatically merged. Previous frozen Attempts and primary develop remain unchanged.
The former background automation was reported absent by the app; no background merge is assumed active.
Capture gaps remain explicit; no release refs, tags or remote rules were changed.
