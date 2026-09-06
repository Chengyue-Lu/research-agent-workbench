# M4-003 Verification

The targeted tests exercise actual pinned files, the existing CLI and a real
M4-002 producer. Independent review found and closed duplicate disk reads and
an inaccurate counterevidence fixture locator. Only those changes and new
contract checks triggered focused reruns; PR #60's full/coverage suites were
not repeated during the parallel review.

Local focused evidence: 14 tests PASS, including a real promotion consumer,
retained negative outcome, CLI/generic validation, identity/file drift and
actual open-count checks. The focused branch measurement gives the new
claim_trace.py line 99.32% and branch 98.39%, with no exclusions. Schema and
existing CLI compatibility checks passed during integration. The final
documentation/Schema/CLI selection passed 17 tests; a clean wheel installation
outside the checkout imports the installed package and lists the new Schema.

Full Python 3.11/3.13, global Coverage Policy v2, package and governance must
pass on the final hosted candidate. Local full/coverage suites are not
duplicated solely to repeat those CI jobs. The new module and actual
positive/negative tests are registered in the unchanged 90/95/90 policy.

TASKS DONE is this implementation PR's proposal until the named owner accepts
and merges it. Neither these tests nor the CI establish scientific correctness.
