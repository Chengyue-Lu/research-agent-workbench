# M14-004 public surface review handoff

Implementation: `c78c829276aea53ff6c673dd9bdf073aeaaafc06`; baseline: `11c3b57dfbf8af0dc2587fc421d097e2544941c3`.
Owner: Chengyue-Lu. R2 cross-owner reviewer: let778750-cpu.

Public navigation, support evidence vocabulary, source Changelog and immutable policy 1.1.0 are implemented.
All 7 public pages are source blobs. The prior 1.0.0 policy is unchanged; new policy closes the build backend,
Runtime specification and no-Skill input. Development-only history stays outside the 232-file projection.

Documentation 18 PASS; governance/documentation 102 PASS; release/documentation 56 PASS before isolation.
Repository validation: 186 / 0 errors / 0 warnings. Repeated isolated projection bytes match and links/build inputs close.
Direct wheel and sdist-to-wheel agree on Runtime resources on Python 3.11/3.13 with isolated/poisoned environments;
124 resources, 76 Schemas, 4 Modes and 0 Projections. Package execution belongs to `95df2be7aa792da2a2029880c9a44e95cf75ed77`;
all package input Git blobs/modes match this implementation, as recorded in checks/package-input-identity.json.
Local R2 governance passes. Hosted final-head full/coverage/package checks are pending PR CI.

Follow Issue #57 current lane: owner handles the preceding activation documentation commit; rebase onto it before integration.
M14-004 final Quickstart must consume M1-009's accepted real scaffold flow; this slice does not mark M14-004 DONE.
No M14-005 activation, real source freeze, release branch, tag, release, or self-merge is authorized here.
The projection CI expectations are explicitly synthetic fixture inputs.

The M14 branch now uses its own worktree. The primary checkout was restored clean on develop and receives no implementation edits.
22 obsolete local branch refs have a verified exact-SHA bundle before deletion; worktrees, ignored evidence and remote refs were retained.

Native capture is incomplete and declared gapped. Checks retain material verification results with hashes;
this archive does not claim complete native event provenance. Historical frozen attempts are unchanged.

Reproduce projected-source checks from repository root:
`python work/M14-004/A-20260911-001/outputs/verify_projection.py`
Add `--with-package --python <python-3.11> --python <python-3.13>` for clean installation checks.
