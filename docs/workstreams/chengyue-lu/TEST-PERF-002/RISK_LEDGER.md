# TEST-PERF-002 Risk Ledger

Owner: 路诚钺 (`Chengyue-Lu`); cross-owner: 黄毅 (`let778750-cpu`); R2.

| Risk | Control and evidence | Remaining review |
|---|---|---|
| A local contract hides initialization or a new dependency | New local-function contracts preserve module/class initialization, call expressions, string inputs and bindings; rejected changes restore ordinary consumers | Review [consumer inventories](CONSUMER_CONTRACTS.md), source/downstream mutants and exact future-base timings |
| Smaller impact selection omits necessary proof | Independent executable seeds, base proof mappings, conservative critical module fallback, mandatory positive/negative evidence and actual changed 100/100 checks | Review proof provenance and ensure reduced tests still achieve critical 95/90 |
| Candidate weakens accepted proof while preserving test IDs | Pin the test-side helper, package initializer and literal fixture closure to the fingerprint anchor; deterministic replacement uses exact base; byte/mode drift restores ordinary consumer and complete proof suites | Direct assertion weakening, actual Claim/Projection helpers, resource drift, added inputs and separately accepted refreshed contract regressions |
| A planned backend or archive executable is never collected | Keep canonical measurement roots and add planned external subject modules/directories; absent subject still blocks impact | Verify aliased backend execution is measured; archived oracle classification remains a separate integration question |
| Author narrows tests through metadata or candidate policy | Git-derived paths, base inventory/risk floor, immutable dependency proof, worker plan recomputation, adversarial reductions | Review planner trust boundary and workflow wiring |
| A new downstream consumer escapes selection | Union of exact base/head imports, resource references, opaque consumers and reviewed contract groups; new tests seed their own closure | Inspect inclusion chains and exclusions; unresolved closure retains explicit fallback |
| Bound execution functions hide a dynamic consumer | Passing or binding import, eval/exec, subprocess and loader capabilities retains opaque consumers; 11 alias and indirect-execution regressions | Review dynamic execution boundaries alongside direct literal-import selection |
| Selection authority narrows its own validation | An independently pinned, isolated witness reads exact Git blobs and rejects focused plans even after candidate planner and selector jointly delete the FULL guard; source/pin/binding drift blocks | Cross-owner accepts the execution root and fresh receipt; manual witness is not automatically enforced by existing required checks; see [execution procedure](SELECTION_WITNESS.md) |
| Reflected execution escapes consumer analysis | `getattr` over execution namespaces and loader capabilities retains opaque consumers across assignment, passing, storage and calls | Verify ordinary data access remains selective and reflected execution stays in the closure |
| Metadata cancels or replaces useful code CI | Separate content/governance concurrency and unique check producers | Hosted event/cancellation evidence |
| Old FAST result reused after risk/base changes | Exact binding/policy and obligation comparison against content artifact; explicit FULL dispatch | Retarget/risk-elevation fixture and hosted rerun behavior |
| Skipped or failed work appears green | Plan-aware fixed aggregates require every selected job to succeed | Adversarial missing/skip/cancel/failure matrix |
| Selective coverage weakens repository quality | Repository 90/95/90 at integration/coverage-authority boundaries; affected critical 95/90; changed code 100/100; no global PASS claim in impact report | Coverage obligation and impact adversarial evidence |
| A multiline continuation misses its branch origin | Map physical changes to the smallest enclosing statement span; verify mapped obligations; unmappable lines -> FULL | Real coverage arcs reject the missing branch and accept both paths |
| FULL recovery is attached to another trigger SHA | Require dispatch GITHUB_SHA == current PR head before planning; retain exact merge-parent and metadata matching | Wrong/stale trigger rejects early; fresh head and merge candidate pass |
| Tests are optimized by deleting behavior | Existing full suites preserved; selected groups use existing tests; new adversarial tests in full discovery | Compare suite inventory and negative acceptance |
| Local timings overstate hosted savings | Duration artifacts retained; suite time, critical path and total runner time distinguished | Hosted measurements remain separate evidence |
| Test fixtures inherit the outer workflow event | Synthetic PR CLI fixtures pass explicit event-name and run under PR/push/dispatch ambient contexts | Post-merge FULL must remain valid under push |
| Remote settings fail to enforce check results | Preserve fixed check identities and record actual protection state | Remote protection configuration is an independent maintainer action |
| Full behavior silently substitutes for missing coverage | Independent scope comparison and plan-aware gate requirements; metadata and job failure matrix | Review every lane and its reason |
| A test-only R2 change acquires unrelated repository cost | Exact PR #65 fixture requires affected behavioral tests, coverage none, both smokes false | Preserve machine minimum and separate integration proof |
| Candidate validator policy authorizes its own impact proof | CI validators use base critical inventory and acceptance mappings; monotonic local additions add proof; source dependency uncertainty retains fail-safe | Review base-side authority and changed-line evidence |
| Repository floors substitute for changed-code 100/100 | Coverage sets compare by inclusion; combined test union executes both checkers; repository-only reuse is rejected | Exact-head union and both-checker evidence |
| Coverage-authority edits erase executable analysis | Repository obligation is additive; base/head dependency and mode guards retain impact maps and base acceptance; missing proof blocks consumption | Combined source/authority and new-import adversarial regressions |

The user explicitly authorized PR #65's merge after successful exact-head CI. The new obligation PR remains
for cross-owner review. Quality thresholds, exclusions, product contracts and release authority retain their boundaries.
## Resource dependency repair (PR #68 investigation)

- False-positive scope: lexical path names and directory guards must not become content reads;
  replay the exact PR #68 path set and immutable complete snapshots.
- False-negative scope: relative roots, shadowing, returned/exported names, closures, rebinding,
  actual Markdown reads and archive imports must retain their consumers. Unknown roots remain conservative.
- Authority: parser edits require complete bootstrap, current-head independent witness and cross-owner
  review; candidate fingerprint refresh cannot approve this PR's own narrower scope.
- Performance: baseline case-duration attribution is not a hosted wall-time measurement. Remaining
  unresolved fixture and executable consumers retain their existing broad closure.

## Dependency analysis reuse

- Cache identity includes exact Python bytes and repository-relative path; cached facts are immutable.
  No test result, resolved graph, mutable branch identity or disk cache is trusted.
- Every graph rebuild resolves imports, basename matches and directory prefixes against the current
  inventory; added/removed inputs and moved consumers have dedicated adversarial regressions.
- Differential checks compare every graph field on three immutable snapshots and every PR #68 plan
  field. Local cold/warm measurements are distinct from hosted execution and total runner cost.
- Selection-authority bootstrap, all quality floors, independent witness and cross-owner review
  remain required. See [analysis performance](ANALYSIS_PERFORMANCE.md).

## Schema self-check reuse and test-cost audit

- Cache only successful schema self-validation by exact bytes and checker identity, with bounded
  process-local retention. Every catalog still performs current reads, resource integrity checks,
  fresh parsing/registry construction and actual document validation.
- Same-size/timestamp byte drift, invalid schema retries, checker changes, catalog mutation,
  different roots, rename/removal and malformed inputs have regression coverage.
- Profiling identified repeated schema self-checks rather than expensive fixture creation in the
  sampled Skill evaluation. No complete test was proven redundant; existing negative cases remain.
- Local before/after measurements do not establish the new hosted full-suite wall time. Remaining
  Runtime resource closure work and cross-commit evidence reuse have separate proof requirements;
  see [full-suite audit](FULL_SUITE_COST.md). Cross-commit result reuse is not enabled by this repair.

## Ordered behavioral execution repair

- Equal TestCase identity sets do not establish equivalent fixture/order semantics. Preserve
  the original B suite in one producer, then run C minus B. Real class/module state mutants
  must fail both direct full and the ordered producer.
- Delay coverage-only loading until B's top-level teardown completes. Start a fresh fixture
  lifecycle for extras and retain B's errors/failures on the same unittest result.
- Verify the raw ordered receipt against exact planned inventories, target, Python and
  outcomes, including fixture events and checkpoints. Legacy split receipts are rejected;
  projections preserve the raw digest and keep coverage-only cases outside behavioral scope.
- The previous `8c09f6c` hosted result proves identity completeness across two producers,
  not historical full execution equivalence. Fresh exact-head full, coverage, fixed aggregates,
  governance and independent selection witness remain required before cross-owner acceptance.
