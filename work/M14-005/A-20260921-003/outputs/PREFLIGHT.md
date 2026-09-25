# Trusted release preflight checkpoint

Implementation 2e628eb774a4e802ca0c4dcdba6569ee8f4e072d starts from repair candidate 1b94a38ae13eada52054cced7b5f22666cb506af (PR #97).
The repair remains separately governed; this new R2 slice has no merge waiver.

The accepted named v0.1.0 preparation decision and the maintainer's instruction to continue development
during CI authorize this work. The entry point joins live source CI, independent source/parent/version/run/
manifest pins, repeated projection and candidate/prospective-tree checks. It rechecks protected refs and
the live CI observation before exclusive receipt creation. Candidate code is never run. merge_eligible is false.

New preflight tests: 9 PASS, line/branch coverage 100/100. Existing source/surface integration: 54 PASS.
Documentation/policy/public surface: 44 PASS. Governance and bounded scope: PASS. Local fixtures use
controlled observer responses; they do not claim a real integrated-source or release-candidate acceptance.
Primary develop is clean and unchanged; source/surface checker semantics, Task definitions, dormant
topology, release policy and previous frozen Attempts are unchanged.

Next gates: accept repair PR #97 and observe its actual protected push/attest; review this composition;
prove a trusted first-main workflow bootstrap and exact versioned includes; add candidate public/installed
checks; then review atomic topology activation. Final release PR, tag and artifacts require separate approval.
No actual release ref/tag or remote protection mutation occurred. Capture gaps remain explicit.
