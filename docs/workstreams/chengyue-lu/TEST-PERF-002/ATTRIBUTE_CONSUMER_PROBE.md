# Checkout attributes and a real Attempt consumer

Owner: Chengyue-Lu. Audit: TEST-PERF-002. This is the A-ATTR-03 experiment,
on the accepted implementation after H4a and release preflight. It supplies
regression evidence for the [input-boundary acceptance](CI_REPLAN_ACCEPTANCE.md).

## Question and actual consumer

Can a scoped `.gitattributes` edit change a real archive validator's result while
the archive data's Git blob remains identical? The experiment invokes the existing
`validate_attempt_trace(root, attempt)` with an explicit generated Attempt. Its
`INDEX.event_ledger` reference reaches `_checked_ref` and the binary `hash_file`
helper. A newline conversion can preserve parsed JSON events while breaking that
existing byte-level contract.

The fixture comes from the real `AgentTraceRecorder`; the reader, schema catalog,
hash function and assertion codes are unchanged. Each variant is materialized in
its own fresh tiny Git clone. The valid and repaired controls use the same
recorded INDEX and ledger blobs. Repair restores the checkout rule; it does not
rewrite the expected digest to accept corrupted bytes.

## Experiment and regression entry

The fixture builder, observation driver and independently named regression cases
are in [test_ci_attribute_consumers.py](../../../../tests/test_ci_attribute_consumers.py).
They serve this test module only. Unittest discovery keeps each canonical test ID;
the expensive immutable scenario observations are shared inside that class.
The command-line probe also exposes the observations for review, with explicit
invocation arguments, Git and materialized identities, risks and elapsed times.
With the normal test dependencies and generated runtime resources available:

```sh
python -m unittest discover -s tests -p test_ci_attribute_consumers.py -v
python tests/test_ci_attribute_consumers.py --root .ci-attribute-probe --probe-output attribute-probe.json
```

Both probe paths must be fresh; use the JSON on stdout with `--probe-output -`
if a file is unnecessary. The probe creates its own tiny fixture and does not
accept an existing user repository. Setup/copy time is separate from the reader
call, including the 1/10/100 unrelated-Attempt controls.

The controls distinguish:

- valid LF data, a whitespace-only attributes edit, and a fresh repaired checkout;
- EOL conversion of the same ledger blob, which must produce the specific existing
  `TRACE-HASH-MISMATCH` / `event-ledger-ref-hash` diagnostic;
- nested LF and out-of-scope controls;
- missing or renamed references and unsupported attribute semantics.

Local execution results and the exact command are retained in the new Attempt
archive accompanying this change. Timings separate fixture/setup work from the
real reader invocation. Measurements describe these generated inputs and this
environment; they are not hosted CI speedup estimates.

## What remains to establish

This reproduces an invocation-specific causal chain. It does not assert that a
historical PR84 or PR90 Attempt was consumed by an existing production test.
Adding this regression cannot retroactively establish such a relationship.
Likewise, a passing unrelated control is not a general exclusion witness.

The real reader still depends on the runtime schema catalog, INDEX references,
message membership and recursive tool-event membership. A record of one ledger
read is not its complete dependency closure. Unknown Git semantics, new readers,
changed directory membership, source changes and environment changes require
their own proof. The [consumer readiness boundary](CONSUMER_SHADOW_READINESS.md)
and complete B/C, coverage, smoke and lifecycle acceptance remain applicable.

Production planning, consumer policy, independent witnesses and coverage
thresholds retain their accepted behavior. The next boundary decision must use
real call-site mappings and independent evidence before it can change selection.

The follow-up [Attempt input boundary](ATTEMPT_INPUT_BOUNDARY.md) maps historical
call sites separately from current observations and exercises membership,
references and the whole Runtime resource constructor with real negative controls.
