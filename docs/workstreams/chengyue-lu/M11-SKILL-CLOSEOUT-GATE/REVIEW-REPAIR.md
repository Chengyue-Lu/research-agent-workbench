# PR81 execution-fact review repair

Review: [comment 5680907209](https://github.com/Chengyue-Lu/research-agent-workbench/pull/81#issuecomment-5680907209),
candidate `a60784d76d1f858296906c69b5a5f735757e6209`; base
`0bebafd81f0116a8269c63ac97378038a1eb2a5d`. The user requested these repairs.
Execution acceptance remains with Huang Yi; Evaluation/Skill identity acceptance remains with Chengyue-Lu.
The existing bounded implementation read/write scope applies; required Skills: []; delegation: false.

## Findings and repair

- P1: consume exact Supply/Projection/component inputs before invocation, then independently record
  observed Provider/Adapter/Model/Runtime/Host/Supply binding after invocation. The pre-use record
  contains no execution binding. Reuse the published Core post-call fact schema without changing it.
  Skill replay requires both records, their exact creation events and their temporal relationship to
  Provider requests/responses and Tool events. Failed drift is observed after the synthetic invocation.
- P1: before calling the Driver, assert that the already-selected frozen Supply has a valid Skill
  Projection closure. Wrong-kind Supply and invalid closure produce preflight-blocked with zero calls.
- P2: require exactly one hash-pinned content read for each consumed Supply/Projection path, including
  canonical path aliases. A later contradictory read remains invalid even if the file was restored.

## Evidence and boundaries

The original `A-20260915-002` archive is immutable evidence of the reviewed candidate. Its post-call
proof predates the two-stage repair and is not current acceptance evidence. New tests preserve its
source/file pins and reject its obsolete one-stage post-call facts under the corrected candidate.
A [fresh attempt](../../../../work/M11-007/A-20260915-003/README.md) holds the repaired vertical proof
and test evidence. The four new Skill kinds
are still an unaccepted PR candidate; published Core/legacy schemas and Task definitions remain unchanged.

Gate B remains UNSATISFIED, M11-007 IN_PROGRESS and M5-007 BLOCKED until exact-candidate owner acceptance.
Focused review regressions, shared Core/Host tests, impact/repository coverage and hosted CI bind the
new head. Development capture remains explicitly incomplete where original events were not retained.
