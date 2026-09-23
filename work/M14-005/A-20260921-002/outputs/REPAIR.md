# M14-005 source API contract repair

PR #80 merged as ea7d6c8cb619b392f79be439fc1ee214f6928cd9. The actual develop push
35536949452 failed source governance: REST 2026-03-10 removed merge_commit_sha from both PR
endpoints. The producer requires that identity and correctly rejected its absence.

Pin the supported 2022-11-28 response contract. Preserve all source/parent/repository/tree checks.
The transport-plus-producer regression fails before the patch and passes after it; missing identity
remains rejected. Focused 16 PASS, documentation/policy 31 PASS, source module line/branch 100/100.
Authenticated live reads using the repaired transport return the exact PR #80 merge identity.
These reads are not a successful full source attestation; that requires the repaired protected push.

Maintainer instructions in this task, retained verbatim:

> 小修复给予审核豁免。

> 或者还有一种方案，这个修复你先做，然后CI时间过长不等待，直接授权合入触发新CI，然后你执行新开发，不在这种过小流程问题上拖时间。

This named authorization covers this small repair and immediate integration where remote rules permit.
It is not a claim of cross-owner approval or reviewer unavailability. Exact base/head and merge outcome
belong to the repair PR record. GitHub hard rules remain active. Development preparation may proceed
on a separate branch during CI; source-CI closure still requires a successful integrated-source observation.
Release-only checks/policy preparation is the next slice. Final release PR, tag, live topology cutover
and any protection mutation remain separately gated. Existing archives and primary develop stay unchanged.
