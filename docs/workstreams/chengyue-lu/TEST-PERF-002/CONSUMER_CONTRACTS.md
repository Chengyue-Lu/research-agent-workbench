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

| Subject | Required behavioral consumer suite | Impact proof suite | Consumer boundary basis |
|---|---|---|---|
| `src/research_workbench/artifacts/claim_trace.py` | `test_claim_trace` | `test_claim_trace`, including every existing claim-evidence-localization positive/negative ID | The suite exercises localization, actual promoted bytes, source/admission drift and both CLI validation/trace paths. Function-only changes do not change CLI/package initialization. |
| `src/research_workbench/capability/release_projection.py` | `test_skill_release_projection` | `test_skill_release_projection`, including every existing skill-release-projection-publication positive/negative ID | The suite exercises the publisher, accepted lifecycle, authority provenance, runtime projection and downstream registry validation. Shared package initialization remains outside the bounded edit domain. |
| `.github/scripts/release_surface.py` (isolated M14 proposal) | `test_release_surface` plus independent digest probes | `test_release_surface` and all existing release critical positive/negative IDs | Local digest logic is distinct from Git DAG auditing, export traversal and package/install changes. This script is absent from develop; its proposed contract is exercised only on the isolated M14 integration baseline. |

Exclusions cover unchanged consumers reviewed at the immutable fingerprint anchor whose
initialization and dependency boundaries are fixed by this edit domain. New or changed
consumers since that anchor add their downstream closure even when outside these suites.
A base fingerprint mismatch restores the broad closure. Ordinary graph edges are not deleted.

The exact pre-existing critical acceptance mappings remain authoritative, including their
negative cases. A proof suite can use exact deterministic IDs from an accepted mapping when
its behavioral module also owns slow integration cases. Absence of a reviewed narrower
mapping retains a complete module. An impact coverage failure remains blocking regardless
of the selected test count or repository-wide coverage result.

Real probes must establish a passing local edit and reject both a source fault and a fault
in a relevant downstream consumer using the same selected test suite. Timing on these
proposed future bases is conditional until the cross-owner accepts the contracts; the
intake's raw graph and hosted baseline remain the before measurements.
