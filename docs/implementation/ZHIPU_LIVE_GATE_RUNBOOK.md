# Zhipu Standard API Project Readiness Gate

This Gate is a narrow, opt-in readiness check for the Zhipu standard Chat
Completions adapter. It uses only the public synthetic evidence fixture. It is
not a scientific-quality evaluation and does not authorize research-data use.

## Fixed safety boundary

- `rwb providers zhipu-gate` reads no environment and performs no network call.
- `--execute` requires `--root`, `--attempt-id`, `--accountable-owner`, and a
  new `--report` path before a Provider can be constructed.
- Credentials come only from `ZHIPU_API_KEY`; the exact model comes only from
  `RWB_ZHIPU_MODEL`. There is no CLI model override or fallback.
- Only the standard endpoint under
  `https://open.bigmodel.cn/api/paas/v4/chat/completions` is allowed. Coding
  Plan and compatible third-party endpoints are not substitutes.
- The adapter and Gate retry zero times.
- The pre-call Model Assignment freezes `reasoning` capability and
  `reasoning_effort: low`; the adapter sends that exact control on every Gate
  request.
- The Gate permits one active Attempt only. Conformance and project execution
  use distinct short-lived Zhipu adapter instances and are never concurrent.
  Every exit path discards the adapter-private opaque continuation; an adapter
  instance must never be registered as a cross-Attempt singleton.
- Reports retain no credential, prompt/response body, Provider response ID,
  or tool arguments.

Before the first Provider request, the Gate exclusively archives its intent
and explicit Model Assignment under `.rwb/zhipu-gates/<attempt-id>/`. It then
archives the versioned redacted conformance report. A conformance failure still
produces the requested Gate report and adjacent Decision, but no research
Attempt.

## Checks and project closeout

Conformance runs fixed text, structured, and client-tool probes, each capped at
64 output tokens. Zhipu tool choice is `auto`; returned tool shape and arguments
remain locally validated. Structured output uses provider `json_object` mode
plus local JSON Schema validation, not provider-native strict JSON Schema.

After conformance passes, the Gate runs `examples/task-evidence.yaml` through
the normal evidence/H2 `run_task_api_attempt` path. Limits are three model
turns, two read-only `document-read` calls, one call at a time, 1,024 characters
per tool result, 256 output tokens per turn, 120 seconds, and 5,000 aggregate
tokens. Missing or excessive token usage still fails closed. No retry or
fallback can extend these ceilings.

The report's overall `status` has the fixed scope `technical-readiness`. The
current Zhipu response contract reports tokens but no monetary amount or
currency, so every executed report carries a separate required
`monetary_cost` dimension with `status: unavailable`, `provider_reported:
false`, and `blocks_technical_readiness: false`. A not-run report instead
records `monetary_cost.status: not-run`.

The v0.1.0 schemas continue to validate archived pre-split Zhipu documents
that contain neither `status_scope` nor `monetary_cost`. New generator output
always emits both fields; either field appearing alone is invalid, and the new
`bounded-technical-readiness-passed` result requires both.

The Gate never estimates or derives an amount or currency from a model name,
tariff, Coding Plan points, or any other price table. A technically passed Gate
therefore proves bounded adapter/project capability only; it does not prove a
monetary budget, scientific correctness, or the OpenAI-specific closure in
ADR-0013. The adjacent Decision may `accept` technical readiness while still
requiring `adr_0013_passed: false` and `monetary_cost.status: unavailable`.
Offline implementation of the adapter tool protocol likewise does not prove
live tool compatibility.

Safe-paused and failed project Attempts still publish their Model Assignment,
conformance evidence, Attempt, Trace, Handoff, Receipt, Main State, and a fresh
process resume-check result. The Gate Decision hash-pins those control-plane
artifacts and explicitly records no fallback, no scientific-correctness claim,
and the orthogonal monetary-cost status.

## Commands

Inspect the fixed zero-network plan:

```powershell
rwb providers zhipu-gate
```

Run only from the intended authorization context:

```powershell
$env:ZHIPU_API_KEY = Read-Host 'Authorized Zhipu API key' -MaskInput
try {
  $env:RWB_ZHIPU_MODEL = Read-Host 'Approved exact standard-API model id'
  rwb providers zhipu-gate --execute `
    --root . `
    --attempt-id A-ZHIPU-GATE-001 `
    --accountable-owner "<real person>" `
    --report runs/provider-conformance/zhipu-live-gate.yaml
} finally {
  Remove-Item Env:ZHIPU_API_KEY -ErrorAction SilentlyContinue
  Remove-Item Env:RWB_ZHIPU_MODEL -ErrorAction SilentlyContinue
}
```

Never paste the credential into chat, shell history, a command argument, a
report, or the repository. The key exists only in the current process
environment for the bounded command and is removed by the `finally` block.

The Decision path is derived beside the report, for example
`zhipu-live-gate.decision.yaml`. Publication is exclusive and never replaces
different existing content. Exit status is `0` for `passed` or auditable
`not-run`, `1` for `safe-paused` or `failed`, and `2` for CLI/configuration or
publication errors.

After, and only after, a live report validates as bounded technical readiness,
copy `registry/models/pool.example.yaml` to an ignored local configuration and
explicitly enable its `zhipu-worker` slot. The committed template keeps that
slot disabled, reads the exact model only from `RWB_ZHIPU_MODEL`, fixes
`reasoning_effort: low`, and never selects or falls back to it automatically.
