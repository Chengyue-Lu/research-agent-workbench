# Bounded CI diagnostic source changes

TEST-PERF-002 / Issue #87. Owner: Chengyue-Lu. Proposed base-side contract;
acceptance and measured execution are recorded separately in the Attempt evidence.

The offline CI diagnostic tools form a small consumer family. `ci_shadow_pair`
uses `ci_consumer_shadow`, which uses `ci_domain_audit`. A local change in this
family currently reaches business suites through conservative opaque-execution
edges. The base impact policy can instead maintain their complete proof suites
using the same reviewed function-body contract already used by Claim and
Projection modules.

| Source member | Complete behavioral and coverage proof modules |
| --- | --- |
| `ci_consumer_shadow.py` | `test_ci_consumer_shadow`, `test_ci_shadow_pair` |
| `ci_shadow_pair.py` | `test_ci_shadow_pair` |
| `ci_domain_audit.py` | `test_ci_domain_audit`, `test_ci_consumer_shadow`, `test_ci_shadow_pair` |

These are explicit source members under `.github/scripts/`. Shared planner,
dependency, input-fact and contract-shadow helpers retain their existing wider
obligations. Each member records positive and negative test identities in its
impact group. Other applicable critical mappings remain additive.

## What qualifies

The accepted `function_body_only` predicate permits a narrow logic change while
keeping definitions, surrounding initialization, names, imports, attributes,
call expressions and string inputs fixed. A changed function with opaque
execution does not qualify. New functions, changed command arguments, new imports,
resource paths, decorators, defaults or initialization restore ordinary selection.

The policy must come from the actual base. The existing authority-epoch anchor
and consumer fingerprint must match. Changed proof tests, known helpers,
resources or package membership invalidate the proof boundary. New and changed
consumers retain their old/new dependency union. Mixed changes keep all additional
obligations. There is no count-based cutoff, wildcard exemption or permission for
candidate metadata to reduce the machine minimum.

The group's package and repository smoke flags are false because these offline
diagnostics do not provide the public installed runtime. Flags from any other
affected surface or unresolved dependency still apply. Integration continues
full behavioral and repository-wide quality checks.

## Independent minimum

The separate minimum witness reconstructs the base-owned planner and its project
dependencies from exact Git objects in an isolated execution tree. It takes
repository, base, head, target and governance metadata from explicit external
inputs, then compares the candidate plan with `make_plan` and
`require_obligations` from that base. Candidate code and import paths are data.

The witness records the caller-pinned checker identity, accepted planner source
identity, dependency hashes, minimum and comparison. A source pin establishes
which code ran; the caller must separately establish that the checker commit was
accepted. The existing independent selection-authority FULL floor remains in
force. A candidate cannot certify its own new policy or checker as accepted.

## Execution acceptance

The isolated corpus contains one bounded correct logic change and one intentional
fault for each source member. The selected complete suites must pass the correct
variant and detect the corresponding fault. Additional controls cover candidate-only
contracts, changed imports/calls/initialization, proof and helper drift, new
consumers, missing anchors, and forged behavioral/coverage/smoke obligations.

Both B and C are collected and executed using the normal ordered producer and
projection rules. Changed lines and outgoing branches retain 100/100; critical
files retain their applicable 95/90 and repository authority retains global90.
The actual B union C must shrink; relabeling a broad plan focused is insufficient.

A fixture commit with this proposed policy is only a test of a possible future
base. Current PR checks continue to use the real accepted base. At least three
fresh same-environment hosted pairs establish the performance observation, with
native counts, failures, coverage, lifecycle, setup and elapsed cost retained.
After actual policy/checker acceptance, a subsequent bounded source change must
show reduced official plan and native execution before production reduction is
declared complete. The diagnostic reports themselves retain
`execution_authority=false` and do not authorize cross-commit reuse.
