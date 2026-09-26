# Accepted Git input for consumer shadow proposals

Owner: Chengyue-Lu. TEST-PERF-002 / R2 / [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).

The existing shadow evaluator accepts a caller-supplied proposal. That remains
useful for exploration, but a candidate can also rewrite that proposal's pins,
test ownership and unknowns. A proposal alone cannot supply independent evidence
for excluding its own tests.

The additional input mode reads a template from an explicitly selected Git base
using the existing [consumer shadow tool](../../../../.github/scripts/ci_consumer_shadow.py).
It preserves the existing proposal evaluator, ordered inventories and coverage
and smoke obligations. It does not modify production planning or worker inputs.

## Source identity and evaluation identity

A committed template contains `version`, `execution_authority: false` and
`consumers`, using the existing consumer field definitions. It omits `baseline`:
a file cannot contain the SHA of the commit that includes that same file.

The reviewer supplies an exact base commit and a portable JSON path. The reader
requires that commit to match the observed plan base and reads the regular Git
blob there. Local worktree bytes and candidate declarations cannot replace it.
Duplicate keys, unexpected fields, authority injection, unsupported file modes,
missing files and mismatched commit identities are rejected.

The effective proposal adds that explicit base as its `baseline`; all original
consumers, source pins, assumptions and unknowns are preserved. The report records
the template commit/path/blob and raw-byte hash separately from the effective
proposal digest. This is an explicit binding operation. It neither refreshes a
stale source pin nor certifies an input contract for a new environment.

For a template already recorded in the selected base, invoke:

```text
python .github/scripts/ci_consumer_shadow.py \
  --repo <repository> --plan <observed-plan.json> \
  --accepted-base <exact-base-commit> \
  --accepted-proposal-template <committed/template.json> \
  --inventory <inventory.json> --receipt <receipt.json> --output <report.json>
```

The existing `--proposal <file>` mode retains its original API and output.
The two input modes are mutually exclusive. A template introduced only by the
candidate is not available through the accepted-base mode.

## What this establishes

The new mode establishes where a declaration came from. It prevents local or
candidate rewrites from silently supplying a different declaration to this mode.
It does not establish that every real consumer or filesystem input was declared.
An unresolved accepted declaration remains unresolved after loading it.

The diagnostic tool itself is still executed from the caller's checkout. Its
reported source hashes are observations, not independent authentication of its
entire executable dependency chain. The word "accepted" names the commit chosen
by the reviewer: Git ancestry alone is not proof of human approval. This new code
must itself be reviewed and accepted before a separate trusted runner can rely
on it. The existing accepted-base selection-floor witness remains unchanged.

Reports keep `execution_authority=false` and `activation.eligible=false`.
No report enables production exclusions or reuses a previous execution receipt.
Independent checker provenance, complete materialized inputs and environment,
old/new membership and alternate consumers, coverage/smoke/lifecycle proof and
fresh same-environment hosted pairs remain prerequisites for activation.

## Verification

Real Git tests distinguish committed base declarations from local rewrites while
the actual Git change remains document-only. This avoids mistaking the existing
non-Markdown fail-safe for proof of trusted declaration loading. Separate cases
cover missing/candidate-only templates, non-regular modes, malformed JSON and
identity mismatches; report digests and unchanged execution requirements are
checked. [Attempt A003](../../../../work/TEST-PERF-002/A-20260926-003/RESULTS.md)
retains exact source identities, local outcomes and the actual-base rejection.

The [Attempt input observations](ATTEMPT_INPUT_BOUNDARY.md) continue to govern
materialization claims. Whole Runtime resources and real directory membership
remain dependencies; a declaration source pin cannot erase them.
