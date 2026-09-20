# M14-005 current-base rebase and next steps

Owner: Chengyue-Lu. Date: 2026-09-21 (Asia/Shanghai).
User request: 跟进到目前最新进度，M14-005有冲突待解决，然后说明下一步推进计划。

PR 80 old head: 47f518a164c59bb123541bc8c0705f2106ee513e; old base: b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22.
New base: 171d4654f88e926f239cdf25bc8168109b81f391; rebased checkpoint: 89614714e021d0f443f977ab6dda6d72c187c9bd.

All seven commits were replayed. STATUS conflicts retain the exact upstream Phase D row and the M14 READY
proposal. Coverage policy 2.3.0 includes every upstream 2.2.4 obligation plus the source-CI critical module,
test suite and independent positive/negative mapping. Removing only those additions reproduces the base
policy exactly. Removing only source_governance reproduces the base CI workflow exactly, including the
new diagnostic consumer-contract shadow job. Source-CI implementation/tests and witness maintenance
fixture repair match the prior reviewed head. All six existing M14 Attempts remain byte-identical.
Only M14-005 changes canonical Task status (BLOCKED to READY); definitions/dependencies remain unchanged.
Primary develop remains clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3.

Focused 157 PASS covers source-CI, documentation/public links, coverage policy, CI planner,
consumer-contract shadow and witness fixtures. Repository validation: 186/0/0. Governance and semantic
preservation checks PASS. The plan requires full behavioral, impact+repository coverage and both package
smokes. Four protection layers and effective rules match at 2026-09-20T20:13:49.664751+00:00; no mutation.
This checkpoint is earlier than the evidence commit: final-head hosted CI and renewed review belong in PR 80.

M14-001 through M14-004, M0-007 and M1-009 are accepted. The existing named v0.1.0 preparation decision
authorizes this READY proposal; M14-005 is not DONE and the release topology remains dormant.

1. Obtain exact final-head/base hosted CI and renewed cross-owner R2 review, then specific PR 80 merge
   authorization. Old-head CI and technical review remain historical evidence.
2. After authorized squash integration, verify the actual protected develop push and source governance,
   then execute live attest from that exact integrated source. Download the producer receipt separately
   for audit; it is not an attestation input or authority token.
3. Once that chain is accepted, implement the release-only workflow/checks, exact policy include and
   atomic topology cutover preparation in a subsequent M14-005 slice.
4. With all gates ready, freeze exact source/current-main parent, prove deterministic projection and
   prospective merge-tree equality, dual-Python install and public-surface closure. Final release PR,
   tag and artifact/hash closure require a separate named approval.

Capture gaps remain explicit. No release branch, tag, topology switch, merge or remote policy change occurred.
