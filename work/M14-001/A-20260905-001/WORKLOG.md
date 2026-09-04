# M14-001 / A-20260905-001

- baseline: `docs/m14-curated-release-activation@12d05dd130c718dd179e011292f9ada9f97bdf74`
- owner: Chengyue-Lu
- actors: `main-agent`, `governance-design-auditor`, `test-auditor`, `archive-scope-auditor`; details in `ACTORS.yaml`
- goal: establish one bounded dormant release trust seam without opening a release path
- target paths: governance policy/checker/tests plus M14 release contributor and status documentation
- write scope: exact list in `TASK.yaml`
- handoff level: H1
- trace index: `INDEX.yaml`
- event ledger: `events.jsonl`

## Material log

| Order | Type | Decision or result | References |
|---|---|---|---|
| 1 | baseline | Continue from exact PR #58 head while that PR waits for review; do not modify or merge it from this branch. | `TASK.yaml` |
| 2 | scope | M14-001 recognizes and validates a dormant same-repository release topology; M14-002～005 implementation remains excluded. | `TASK.yaml` |
| 3 | delegation | Three independent read-only audits covered governance design, test/coverage closure, and archive requirements. | `messages/0001-*`, `messages/0002-*`, `messages/0003-*` |
| 4 | decision | A structurally valid release candidate must still produce a blocking dormant finding; existing exact `develop -> main` remains executable. | `messages/0004-*`, `messages/0005-*` |
| 5 | capture-gap | Initial delegated packets omitted predeclared Profile/Skills/budget metadata; subsequent work treats this as a recorded process gap, not implied authority. | `INDEX.yaml` |
| 6 | change | Added strict data-only policy, structural topology classification, protected-caller prerequisite validation, merge-free ancestry, raw manifest hash check, and fail-closed R2 orchestration. | `outputs/M14-001-IMPLEMENTATION-SUMMARY.md` |
| 7 | review | Three adversarial follow-ups identified and bounded trust-source, merge-history, coverage, naming, and archive gaps; accepted findings were remediated without entering M14-002. | `messages/0007-*` through `messages/0012-*` |
| 8 | check | Focused governance/documentation passed `122/122`; Coverage Policy v2 passed `750` total with global `91.53%` and checker `97.31/96.58`. | `checks/0001-*`, `checks/0002-*`, `checks/0003-*` |
| 9 | check | Full behavioral suite passed `811` total; repository validation was `183/0/0`; isolated wheel/package smoke passed with 63 installed Schemas. | `checks/0004-*`, `checks/0005-*` |
| 10 | commit | The stable tested governance/product tree was committed as `e560dbc`. | `outputs/M14-001-IMPLEMENTATION-SUMMARY.md` |
| 11 | safe-pause | Integration waits for PR #58 merge, then latest-develop rebase, hosted dual-Python CI, and cross-owner R2 review. | `handoffs/H1-SAFE-PAUSE.md` |
| 12 | trace remediation | The first trace validation exposed that the lightweight template archive was not Agent Trace v0.1 machine-valid. The archive was migrated to the accepted Index/envelope/event contracts; historical capture gaps remain explicit. | `checks/0006-trace-format-remediation.md`, `events.jsonl` |

## PR ledger

| Branch / PR | Base | Slice | Validation | Review / merge |
|---|---|---|---|---|
| `feature/m14-release-foundation` / not opened | `12d05dd...` stacked on PR #58 | M14-001 | local focused/full/coverage/repository/package validation PASS | wait for PR #58 merge, then rebase onto latest `develop` before opening the implementation PR |

## Closeout

- outputs: `outputs/M14-001-IMPLEMENTATION-SUMMARY.md`; tested implementation commit `e560dbc`
- handoff: `handoffs/H1-SAFE-PAUSE.md`; all visible delegated assignments/returns indexed in `INDEX.yaml`
- trace completeness: Agent Trace v0.1 `gapped`; explicit message/event/tool-result capture gaps are projected by `INDEX.yaml`
- validation: focused `122/122`; full `811` total with one Windows privilege skip; coverage-quality `750` total with one Windows privilege skip; global `91.53%`; checker `97.31%` line / `96.58%` branch; repository `183/0/0`; package smoke PASS
- limitations/unresolved: PR #58 merge, latest-base hosted Python 3.11/3.13 CI, exact PR-event governance, and cross-owner R2 review remain pending; M14-005 remains the sole future authority to activate curated-release merge eligibility
- next action: after PR #58 merges, rebase only the post-`12d05dd` M14-001 commits onto latest `origin/develop`, rerun exact-head CI, and open the R2 implementation PR
- Agent Trace validation: exit `0`; no `BLOCK`; one expected `TRACE-CAPTURE-DELAYED` warning preserves the declared historical capture gaps
