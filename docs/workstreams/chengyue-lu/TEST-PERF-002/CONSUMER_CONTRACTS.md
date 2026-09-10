# Local-function consumer contracts

Owner: Chengyue-Lu; cross-owner: let778750-cpu; TEST-PERF-002 / R2.
These are proposed base-side contracts for review with the precision implementation.
They cannot reduce the obligations of the PR introducing them.

The frozen intake at `205559b25f7f0bd276094a4ac53db28354b7284d` selects 72/75 modules
for each seed. Diagnostic import-only closures contain 20 modules for claim trace and
62 for release projection. Those shared import edges remain in the ordinary graph.
The contract applies only to local function-body changes that preserve module/class
initialization, definitions/defaults/decorators, imports, referenced names, call expressions
and string/resource inputs. Changed opaque execution, new imports/consumers and other
changes restore the ordinary closure. Coverage still proves actual affected statements
and outgoing branches, plus whole critical-file 95/90 and existing acceptance.

This syntactic guard preserves initialization expressions, not their results. Admission
of a future subject must inspect whether module/class initialization calls an editable
function (for example, `CACHED = calculate(1)`) and whether consumers depend on that
result. The current Claim and Projection contracts were reviewed for their specific
edit domains; they do not authorize arbitrary future subjects through syntax alone.

| Subject | Required behavioral consumer suite | Impact proof suite | Consumer boundary basis |
|---|---|---|---|
| `src/research_workbench/artifacts/claim_trace.py` | `test_claim_trace` | `test_claim_trace`, including every existing claim-evidence-localization positive/negative ID | The suite exercises localization, actual promoted bytes, source/admission drift and both CLI validation/trace paths. Function-only changes do not change CLI/package initialization. |
| `src/research_workbench/capability/release_projection.py` | `test_skill_release_projection` | `test_skill_release_projection`, including every existing skill-release-projection-publication positive/negative ID | The suite exercises the publisher, accepted lifecycle, authority provenance, runtime projection and downstream registry validation. Shared package initialization remains outside the bounded edit domain. |
| `.github/scripts/release_surface.py` (isolated M14 proposal) | `test_release_surface` plus independent digest probes | `test_release_surface` and all existing release critical positive/negative IDs | Local digest logic is distinct from Git DAG auditing, export traversal and package/install changes. This script is absent from develop; its proposed contract is exercised only on the isolated M14 integration baseline. |

Exclusions cover unchanged consumers reviewed at the immutable fingerprint anchor whose
initialization and dependency boundaries are fixed by this edit domain. New or changed
consumers since that anchor add their downstream closure even when outside these suites.
A base fingerprint mismatch restores the broad closure. Ordinary graph edges are not deleted.

Every contract that reduces closure also requires unchanged evidence implementation.
Evidence modules are derived from the group's behavioral tests, coverage tests,
positive/negative IDs (including the global fallback), and applicable critical acceptance
mappings. The existing Git dependency graph recursively expands these roots through
`tests/**` helper imports, package initializers and known literal fixture/resource inputs.
Production dependencies remain outside this identity closure: their correctness is
proved by the source boundary and behavioral/impact checks. Evidence Git blobs and modes
must match the accepted fingerprint anchor, current base and candidate. Candidate graph
paths can only add obligations, including newly present initializers and fixture inputs.
Retaining test names while changing assertions, transitive helpers, fixtures, or even
comments invalidates this contract. Both behavioral and impact planning
then use the ordinary consumer closure and complete contract test suite; unresolved
ordinary closure retains the existing fail-safe. Risk alone does not force FULL.

A candidate fingerprint refresh cannot accept its own changed proof. After the evidence
and refreshed contract/fingerprint are accepted into a newer base, a subsequent bounded
source-only change can use that authority again. The consumer fingerprint includes test
resources as well as Python modules so a fixture-only refresh creates a new accepted
anchor; the impact policy itself is excluded from its own fingerprint. New or changed ordinary consumers
continue to add closure independently.

The exact pre-existing critical acceptance mappings remain authoritative, including their
negative cases. A proof suite can use exact deterministic IDs from an accepted mapping when
its behavioral module also owns slow integration cases. Absence of a reviewed narrower
mapping retains a complete module. An impact coverage failure remains blocking regardless
of the selected test count or repository-wide coverage result.
Substituting accepted deterministic IDs for a complete mixed module additionally requires
that module's complete test-side evidence closure to match the exact base. Candidate evidence drift keeps the
complete module, including its behavioral/integration cases, in the impact proof suite.

Real probes must establish a passing local edit and reject both a source fault and a fault
in a relevant downstream consumer using the same selected test suite. Timing on these
proposed future bases is conditional until the cross-owner accepts the contracts; the
intake's raw graph and hosted baseline remain the before measurements.
