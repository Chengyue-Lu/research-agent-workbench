# M14-005 source-CI preparation

- Owner Chengyue-Lu; R2; user requested continued M14-005 implementation.
- Baseline `0bebafd81f0116a8269c63ac97378038a1eb2a5d`; implementation `65978304329be2ac58326181f864e642b94df9c0`.
- Producer rechecks the exact merged PR and actual squash delta; consumer binds authentic GitHub run/attempt/job/check identities and catches rerun races. The inactive producer never shares the PR governance check name.
- 247 joint focused tests PASS; 15 source tests PASS; observer coverage 150/150 lines and 18/18 branches; repository 186/0/0; governance/plan PASS.
- Historical green develop CI is a live negative control: absence of governance fails closed. Real protected-push positive evidence follows acceptance of this implementation.
- Existing source/product/Schema/Registry/Skill/release-policy/topology and frozen Attempts are unchanged. Canonical Task rows remain unchanged; M14-005 is BLOCKED. Primary develop stays clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3.
- Next: final-head hosted CI and R2 review; then validate the integrated protected push before release-only checks/policy include. Named first-release decision and remaining readiness precede cutover/freeze/release.
- Capture gaps are explicit; no hidden reasoning or secrets retained. The PR body owns subsequent CI/review/merge receipts; this Attempt remains frozen.
