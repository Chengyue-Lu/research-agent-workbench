# M4-004 Risk Ledger

| Risk | Current boundary and evidence | Disposition |
| --- | --- | --- |
| Checker replay mistaken for scientific Run reproduction | Core runner executes pinned case code in a fresh cwd; manifest/check/report reads never invoke M4-002 | Covered by actual process and read-only tests |
| Re-pinned Run changes logical refs while execution remains unchanged | Explicit ObjectRef-to-FileRef mappings close exact input/environment/output sets, revisions and declared object hashes; FileRefs independently bind bytes | Original three reviewer counterexamples now block before execution; independently reviewed |
| Scientific authority from matching bytes | All four authority flags are false; fixture is a synthetic recurrence and negative result | Owner reviews semantics; no Claim acceptance |
| Environment pin overstated | Exact CPython version/platform and environment-definition bytes only; no interpreter/OS build attestation | Explicit limitation, no new trust system |
| Session state leaks into reconstruction | `-I -S`, scrubbed environment, copied inputs and fresh cwd | Tested; trusted code can still access host resources |
| Failure or null result disappears | Reports, streams and partial outputs retained; negative marker carried from manifest | Nonzero/timeout/difference/zero-net-change tests |
| Receipt confused with present eligibility | Exact receipt schema and target binding only; does not authenticate history or recursively validate policies | Keeps M4-002 responsibility separate |
| Manifest/reports manually fabricated | File pin integrity does not establish author identity or authenticity of claimed historical process | No historical authority claimed |
| Untrusted program/resource exhaustion | Fixed stdlib single-file contract; timeout; no OS sandbox, child-tree containment or generalized quotas | Only trusted bounded code; broader execution is outside this Task |
| Main-process crash | Durable ordinary failures only; no recovery/atomic multi-file attempt transaction | Explicit residual limitation |

These limits do not amend M4 Task acceptance or introduce M5 case-freeze gates. Any broader scientific or core
contract interpretation remains a named-owner decision at review.
