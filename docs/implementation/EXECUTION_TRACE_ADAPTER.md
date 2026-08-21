# M6-006 Legacy Execution Trace Adapter

## Contract boundary

This adapter is Part B of the Issue #13 integration split. It connects the
legacy v0.1 Skill-bound Attempt and Execution Receipt to the M3-008
file-authoritative Trace Core. It does not resolve or reinterpret Method,
Mode, Skill, Claim, Decision Authority, or Human Gate semantics.

Historical Attempt and Receipt files remain readable without `trace_ref`.
New model API executions cannot use that compatibility path: the traced
runner creates Trace before provider use, archive closeout injects matching
hash-bound references, and archive verification requires the complete Trace
and marker-last file set. This keeps old evaluators stable while making the
new execution path fail closed.

## Runtime loop

1. `run_traced_session` validates the project boundary, accountable owner,
   Profile identity, and a new Attempt directory.
2. `AgentTraceRecorder` publishes `TASK.yaml`, `ACTORS.yaml`, `INDEX.yaml`,
   and `events.jsonl` before the first provider request.
3. The isolated session runner uses one `SessionEventSink`:
   - provider requests are persisted before dispatch;
   - validated responses are persisted immediately;
   - tool attempts are recorded before execution;
   - tool results are persisted before entering model context;
   - cancellation, budget exits, provider failures, and capture failures are
     recorded as terminal status or capture-gap facts.
4. Provider-neutral sanitization occurs inside Trace Core. Credentials remain
   an HTTP-adapter concern, secret-shaped fields fail closed, and provider
   hidden reasoning is replaced with omission metadata.
5. `finalize_execution_archive` derives `session-transcript.json` from Trace,
   validates Attempt/Receipt relationships, then writes a manifest last. A
   failed validation or publication never produces a completion marker.
6. `rwb execute verify` replays only files and hashes. It does not trust an
   in-memory session result.

## Recovery rule

`rwb execute recovery-check` accepts only a committed, replay-valid,
safe-paused previous Attempt whose Handoff and Main State agree. It returns a
seed for a distinct, non-existing Attempt ID and directory; it never reopens
or mutates the previous Attempt. Recovery preflight itself creates no files.

## Failure and compatibility gates

- Trace failure before provider dispatch blocks the call.
- Trace failure after provider dispatch attempts a capture-gap and safe pause.
- If even the capture-gap cannot be stored, absence of the completion marker
  is the fail-closed signal.
- Oversized tool results are persisted as not delivered and never falsely
  marked as model context.
- Attempt, Receipt, Trace, transcript, and manifest identity/hash drift block
  replay.
- Existing v0.1 Skill assignments, including their non-empty Skill lock, are
  unchanged. No placeholder no-Skill assignment is introduced.

## Module acceptance loop

1. Run deterministic session ordering and fault-injection tests.
2. Run archive closeout, marker failure, tamper, and file-only replay tests.
3. Run recovery in a fresh Python process and require a new Attempt.
4. Re-run legacy Skill Evaluation to detect compatibility regressions.
5. Validate schemas, risk-code registries, examples, and registry entries.
6. Run the full Python 3.11/3.13 suite with repository coverage at least 80%.
7. Build the wheel and smoke-test it in a clean virtual environment.

Live OpenAI conformance and the public EVID/SIM SIR canaries remain separate
acceptance work. They require an explicitly authorized Windows environment and
must not be replaced with synthetic PASS evidence.
