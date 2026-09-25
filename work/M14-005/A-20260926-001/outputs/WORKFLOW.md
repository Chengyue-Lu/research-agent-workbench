# Diagnostic first-main release workflow slice

The workflow checks out an externally pinned develop source before any code
execution. It fetches a same-repository candidate as Git data, runs source-owned
live preflight, and then checks the candidate's public links, build inputs and
internal-path closure from Git blobs. No candidate program or action is run.
Its audit output is explicitly non-authoritative (`merge_eligible=false`).

Policy version 1.3.0 appends exact `.github/workflows/release.yml` and
`.github/scripts/release_public.py` includes; versions 1.0.0–1.2.0 retain their
original semantics. The candidate's complete tree must still match the frozen
source projection, including these workflow and validator bytes.

The first `main` PR may run the workflow from the candidate merge ref. That is
bootstrap execution, not bootstrap trust: the candidate cannot certify its own
workflow. An R2 reviewer must separately run the source-owned preflight from a
clean accepted source checkout, bind exact source/current-main parent, CI run,
policy, candidate and independently reviewed manifest hash, and compare the
GitHub run with effective remote rules. Repository variable pins are external
inputs and remain unset during preparation. The diagnostic job name is not a
required check; current main hard gates and dormant topology still block merge.

Unproven here: a real hosted first-main release PR trigger, dual-Python
checkout-outside install/quickstart, R2 topology cutover, actual release
candidate, final merge, tag and artifacts. The next slice must test those
without treating this diagnostic workflow or receipt as release authority.

Local evidence at source `4ce9404`: 76 focused tests passed, and the public
checker had 113/115 covered lines (98.26%) and 38/40 branches (95%). Repository
validation was 186 validated, zero errors or warnings. In a separate clean
full-history clone, policy 1.3.0 projected 281 files into tree
`3f3707c1abc6df0d6879e9884428ae989e14a637`; two exports agreed byte for
byte. A synthetic candidate commit over the then-current main parent matched
that tree and passed the public check. The source clone's develop tracking ref
was locally overridden to the unmerged source for this structural rehearsal;
the CI run ID was fake. This is not a live source-CI attestation or a release
approval. See the tool-event receipts in this archive.
