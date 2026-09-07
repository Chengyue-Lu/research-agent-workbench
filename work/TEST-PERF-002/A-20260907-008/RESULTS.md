# M14 selective CI acceptance

Verdict: **hold the broad M14 speedup acceptance and merge preparation**. Documentation
scope shrinks substantially; the tested M14 executable edit does not. Current-head CI
and cross-owner acceptance remain separate gates.

## Baselines and isolation

- Live develop: `b8a38a1d0cea4e8422ade8481aec4c277250d6cb` (accepted M4-003 / PR #61).
- PR #62: `5141e6dfdb3ac25441933048eeaf3acb7477f3e6` already contains that develop commit;
  no M4 branch rewrite, additional M4 experiment or official-branch mutation was performed.
- PR #66 was rebased to `def9322d44dd7bd6161d244f81f7b1ee6a7adeb6`. Only additive
  coverage-policy entries conflicted; both accepted Claim and CI/witness mappings remain.
  Every other file matches the Git three-way expected tree. Current witness run
  [34081629939](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34081629939)
  passed from independently pinned root `1b543393ae71b9032359b739170d66ec0be08772`.
- Official M14 PR #60 remains at `5639da47c64e8207e972ba01a7844d8e6c56d958`.
  Its isolated rebase onto the proposed accepted #66 baseline is `c7233912e64b7dda81514197a9b3fb6e1f0b0b27`.
  The rebase preserves both implementation links, all coverage mappings, the independent
  package obligation and M14's dual-Python portable-package matrix. It is not a develop merge.

## Exact Git probes

The synthetic PR plans use the isolated M14 tree as their **proposed accepted base**.
They are local experiment bindings, not actual GitHub PR plans or merge eligibility.
All candidates retain R2. Each modifies one file and no policy/threshold/selector code.

| Probe | Resulting obligations | Observed result |
|---|---|---|
| Workstream Markdown comment only | behavioral none; coverage none; both smokes false | Real focused runner: 93/93 PASS, 3.309 seconds including plan validation/collection; tests themselves 0.145 seconds |
| `digest(data)` uses `memoryview(data)` with equivalent SHA-256 behavior | focused; impact; both smokes true | 1023 of 1035 tests in 72 modules selected; only 12 excluded, a **1.16% test-count reduction** |
| `digest(data)` returns 64 zeroes | Same broad focused/impact closure; release tests selected | Existing release-surface module: **37/37 PASS in 133.318 seconds despite the wrong hash** |
| `portable(path)` stops rejecting the reserved name NUL | Same broad closure; release attack matrix selected | Existing `test_portable_path_attack_matrix`: FAIL on `NUL.txt`, exit 1, 1.026 seconds |

No complete wall-clock result is claimed for the equivalent-function selected suite.
Its first launch lacked generated Runtime resources in the new checkout and was discarded.
After a normal editable install, the valid run was stopped once the scope acceptance failure
was established. The 1023-test plan would execute almost the whole inventory; a second full
coverage run would not resolve that scope problem. Interrupted runs are not PASS evidence.
Actual hosted critical-path and total runner-time savings have not been measured for these
synthetic PRs. The numbers above are local duration and exact selected-inventory evidence.

## Finding 1: M14 executable scope expands through an unresolved resource read

The selection certificate includes these chains:

```text
release_surface.py -> resources.py -> validation/schemas.py -> observability/trace.py
                  -> test_api_session_runner

release_surface.py -> resources.py -> capability/release_projection.py
                  -> capability/__init__.py -> adapters/codex.py -> adapters/__init__.py
                  -> test_provider_adapters
```

Thus `focused` alone does not establish a useful reduction. The resource-reader frontier
needs a bounded, reviewable input boundary before this M14 case can meet the requested
speedup. Preserve fail-closed behavior for truly unresolved inputs; do not exclude tests
or add candidate-approved exemptions to force the desired result.

## Finding 2: an independent SHA-256 assertion is missing

The mutated source was confirmed loaded from its own probe checkout. The standard SHA-256
vector for `b"abc"` is `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`.
The baseline returns this value, while the mutant returns 64 zeroes. `digest()` feeds release
manifest input, output, policy, tool and manifest hash fields, so the mutation changes an
observable contract. The existing 37-test module does not reject it. This is an assertion
gap, distinct from missing test selection. Add an independent vector and compare exported
manifest hash fields against independently computed source bytes in M14's regression suite.

## Rebase integrity checks

- Coverage-policy and documentation tests: 30 PASS; repository validation: 183/0/0.
- Portable package: PASS on CPython 3.11.16 and 3.13.15; direct wheel and sdist-to-wheel,
  isolated and non-isolated checkout-external consumption all pass (eight observations).
  Both routes contain identical Runtime resources: 121 resources, 73 schemas. All receipts
  retain `merge_eligible: false`; this does not authorize a release.
- Thresholds and previous acceptance mappings are preserved. No current M14 repository-wide
  coverage PASS is claimed from these probes.
- PR #66 full/coverage checks are running on the rebased head; require their exact-head
  success and cross-owner acceptance before any merge. No official M4/M14 branch, main,
  release, tag or protection settings were changed.
