# Public SIR canaries

`EVID-SIR-001` and `SIM-SIR-001` share `Q-SIR-001@1` and one Claim ceiling but preserve
separate evidence and simulation support. The Evidence task is bounded to DOI
`10.1098/rspa.1927.0118`, the supplied short excerpt, and its locator. The simulation task uses
the standard-library implementation in `research_workbench.examples.sir_canary`.

Passing either canary does not support a real epidemic forecast. Any statement about a real
population, disease, intervention, policy, or predictive accuracy requires a Human Gate.

The committed files are public, deterministic inputs. Live Provider Attempt archives remain
under `work/`, are scanned for credentials/headers/hidden reasoning/absolute user paths, and are
not promoted as M6-004 evidence until both `rwb trace validate` and `rwb execute verify` have no
BLOCK risk.

Current shared-interface blocker: Method Resolution can explicitly select `task-contract`/
`tool-only` with no Skill, while the compatibility Resolved Assignment schema and resolver still
require a non-empty Skill lock. The execution layer must not fabricate a Skill to bypass this.
The two live canaries therefore remain unexecuted until the Method/Core owner approves the
no-Skill Assignment migration seam during shared review.
