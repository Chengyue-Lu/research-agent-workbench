# Attempt invocation input boundaries

Owner Chengyue-Lu; TEST-PERF-002; R2; required Skills [].
Accepted base `5bf2227ca9b4d2f63f452e579185e7838028de78`; implementation `661c2ede26ea59122d3b048f453801d219e6c4c4`.

This extends the original checkout experiment with real default Trace input
observations. Twelve new named regressions share sixteen fresh-process scenarios:
directory/INDEX entry points, top-level message and recursive tool membership,
deleted/renamed/outside references, an unrelated sibling, alternate transcript
reader, unchanged-manifest schema and non-schema resource drift, and restoration.
The default reader verifies every packaged Runtime resource before its schema
catalog loads. Imported workbench modules are pinned to the independent package
copy. The validator, resources, hash reader and catalog are unchanged.

Both Python 3.11 and 3.13 passed 22 related tests (12 new, 8 prior checkout tests,
2 unchanged hash/ref controls), with no skips/errors/failures. These local runs
bind exact source bytes, before the implementation commit was created. They are
not hosted receipts. Shared scenario preparation keeps fixture cost bounded;
scenario failures now reach their named tests. A diagnostic-only saved-report
replay confirms one injected mismatch fails its owning test while a separate
unaffected test passes. That replay does not execute or substitute a business
reader and is separate from the real execution results.

The first local attempt is retained: outside-reference validation produced two
correct BLOCKs (schema and containment), while the experiment expected one.
The final check requires the exact two, retaining exact single-BLOCK checks for
other faults. Independent static review found and closed class-wide failure
attribution before the final dual-Python runs. The initial review-agent login
failure is a capture boundary; the later source review completed successfully.

Four unchanged tests were separately observed at rebased head `bbdb4d4`:
H4 CLI success, H4 post-seal tamper, blocked evaluation evidence, and M6 retained
validation tamper replay. All passed with their existing fixture behavior intact.
H4 opens archived executable exporters; this does not establish reads of every
adjacent historical Trace. Audit hooks record attempted operations, including
failed opens; missing events cannot prove safe exclusion. The historical source
map and addendum preserve their own source identities and limitations.

[Summary](checks/summary.json), [proposal](checks/consumer-proposal.json),
[raw evidence](checks/raw-evidence.zip) and [manifest](checks/manifest.json)
retain source pins, original failure, complete final observations, four existing
invocations and historical findings. The proposal validates the existing shadow
format and retains unknowns with `execution_authority=false`.

Production policy, selector, witness, workflows, existing tests and quality
thresholds are unchanged. Complete consumer closures, accepted independent
exclusion evidence and fresh B/C/coverage/smoke/lifecycle acceptance remain
separate requirements. No hosted speedup, safe exclusion or result reuse is
claimed. Final-head and hosted verification follow this seal under their own
identities.

Trace capture starts at evidence freeze. Earlier tool/inter-agent messages were
not continuously retained in full; findings and raw observations are preserved
with a truthful capture-gap warning. Publication is a subsequent external action.
