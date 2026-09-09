# Test-side evidence implementation closure

TEST-PERF-002 revision 20; owner Chengyue-Lu; cross-owner let778750-cpu; R2.
Implementation `599d090a3d481fecf970e8dc6cf98ef7f80688c5` on base `bdbac11a0c9a17fa221f8cc8bdd522c1bf4f9087`.

[Review input](checks/review.json) identifies indirect proof drift through Claim's
PromotionFixture and Projection's _live_evaluation. The direct proof modules and
IDs can remain unchanged while their test-side program changes.

The repair reuses the committed dependency graph to traverse test-side helper imports,
test package initializers and known literal fixture/resource inputs. Production paths
stay outside this identity closure. Every evidence path must match the accepted
contract anchor, current base and candidate by Git blob/mode. Candidate graph paths
can only add requirements, including newly added initializers or fixture inputs.
Exact deterministic substitutions apply the same check against exact base.
Drift restores ordinary consumer/proof closure; risk alone does not force FULL.

The fingerprint includes test resources so separately reviewed fixture-only edits
can establish a refreshed contract anchor. The policy excludes itself from its own
fingerprint. Candidate refresh cannot self-authorize narrower obligations.

Six added regression methods cover both actual helper programs, transitive/cyclic
test imports, package initialization, fixtures, base re-admission, deterministic
helper/resource drift, and added inputs. The previous committed planner reproduces
four failures across Claim, Projection and deterministic helper/resource cases.
An existing critical fixture now computes its fingerprint after accepting its policy.

[Focused proof](checks/summary.json): 125 tests PASS in 439.522 seconds,
critical 95/90 and changed statements/outgoing branches 100/100. Docs 9/9 and local
governance PASS. [Complete-repository plan replays](checks/real-plans.json) retain
focused + impact and one contract test module for each unchanged-proof source-only
Claim/Projection edit, with four/five test-side input files respectively. These are
plan checks, not new hosted performance measurements or runtime mutant execution.

Fresh final-head hosted full bootstrap, coverage and fixed-root witness are required
after the archive commit, followed by cross-owner review. M4/M14 formal branches and
release authority remain outside this repair. Log endings are normalized to LF and
terminal blank lines removed before hashing; native capture gaps remain explicit.
