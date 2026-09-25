# M14-005 release workflow handoff

Started from accepted `develop@eb49093` in an isolated worktree. PR #98, its
protected push CI 36164963118 and clean-source live attestation were confirmed
before this slice. The primary local develop checkout was not changed.

This attempt adds a diagnostic release-only PR workflow, a source-owned public
candidate validator, policy 1.3.0 and focused tests. The first candidate's
workflow file may come from its own merge ref; its green check is not an
independent trust anchor. The branch remains release-ineligible. See
`outputs/WORKFLOW.md` for the trust boundary and verification result.

No subagents or external messages were sent. Early exploratory tool outputs and
the first failing focused run were not captured verbatim; their outcomes are
recorded in `events.jsonl` and the later complete green logs. This capture gap
does not conceal a known code failure; the failing assertion was repaired and
rerun.

Verification at implementation commit `4ce940433e43f246b92dde602658ad3aeac0ef96`:
focused release/public/documentation tests 76 PASS; public checker focused
coverage 113/115 lines and 38/40 branches; repository validation 186/0/0.
An initial repository run used an older editable environment with `PYTHONPATH`
and failed to load generated `_runtime_pin`; the branch-local clean editable
install passed on rerun. Both outcomes have retained logs. The synthetic
projection and first-main candidate rehearsal used a separate clean clone,
with a locally overridden develop tracking ref and fake CI run ID 1; both are
structural evidence only, with `merge_eligible=false` and no live source
attestation. No real release branch, PR to main, tag, ruleset change or
publication occurred.

One exploratory `plan_ci.py` call omitted its required GitHub event and failed
before producing a plan; hosted PR CI will supply that event. A broad `rwb
validate .` exploratory invocation scanned the local virtualenv and unrelated
repository documents, so its errors were not treated as repository validation.
The documented `rwb validate examples registry` invocation passed 186/0/0.
`rwb trace validate` reports only the intentional `TRACE-CAPTURE-DELAYED`
BLOCK for the indexed capture gaps; no archive hash or reference mismatch
remains. This archive is frozen for review, not evidence of a complete trace.
