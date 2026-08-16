# OpenAI Responses Live Gate Runbook

This gate is a narrow, opt-in check of the repository's OpenAI Responses
adapter. It is not a research-quality evaluation and does not authorize use of
research data. Run it only from the intended real-user authorization context.

## Safety behavior

- `rwb providers openai-gate` reads no environment variables and sends no
  network requests. It emits a deterministic `not-run` report.
- `--execute` is the only switch that authorizes live requests.
- `--execute` requires an explicit new `--report` path. The CLI rejects a
  missing report before constructing a Provider or making a network request.
- The live model is read only from `RWB_WORKER_MODEL`; there is no CLI model
  override or fallback model.
- The credential is read only from `OPENAI_API_KEY`, at the adapter's outbound
  request boundary.
- If either variable is absent or empty, the result is deterministic
  `not-run`; no provider is constructed and no network request is attempted.
  Execute mode still requires the root, a new Attempt ID, the accountable
  owner, and a report path so the `not-run` report and adjacent Decision are
  durably recorded.
- Reports omit credential values, prompt and response bodies, tool arguments,
  provider response IDs, and provider error messages.
- Neither the adapter nor the gate retries a request.

## Fixed checks and budgets

The conformance phase performs, in order, one text probe, one JSON Schema
probe, and one forced client-tool-call probe. Each request is capped at 64
output tokens. The phase stops after its first failure.

Only after conformance passes, the project-level phase runs the public
`examples/task-evidence.yaml` H2 Task through `run_task_api_attempt`. Its
dedicated Gate protocol explicitly permits the remote provider for this public
synthetic input and does not claim ZDR or training opt-out controls. The
internally constructed Model Pool has exactly one enabled OpenAI worker slot
and no fallback. The Task may call only the read-only `document-read` client
tool, at most twice and never in parallel, over at most three model turns,
5,000 aggregate tokens, and USD 0.50 of provider-reported cost.

Successful Gate evidence includes Model Assignment, Attempt, Agent Trace,
Evidence, Handoff, Transfer Manifest, Transfer Audit, Execution Receipt, and
Main State. A fresh Python process must pass `context resume-check` using only
the published Main State and Gate protocol. The report stores only phase
status, published paths and hashes, and the fresh-process result. A missing
token or cost aggregate causes a conservative safe pause; the gate does not
estimate money from a model name or silently ignore unavailable usage.

The current OpenAI Responses adapter receives token counts but no monetary
cost field from the API. Unless an authorized provider boundary supplies a
real `provider_reported_cost`, the project-level phase therefore closes as
`safe-paused` with reason `cost-usage-unavailable`, and the overall Gate report
is `failed`. Such a closeout is auditable but must never be reported as a
passed live Gate.

Before the first conformance request, the gate exclusively publishes an
independent archive under `.rwb/openai-gates/<attempt-id>/` containing its
intent and explicit Model Assignment. It then archives the versioned,
redacted conformance check. Conformance failure still produces the archive,
the requested versioned Gate report, and a deterministic adjacent Gate
Decision, but produces no research Attempt. The Decision hash-pins the report
and conformance check; only an accepted Gate also pins Main State, Execution
Receipt, and Trace. It explicitly records no fallback and does not claim
scientific correctness.

## Commands

First inspect the policy without reading the environment:

```powershell
rwb providers openai-gate
```

In an authorized Windows Terminal, set the two process-scoped variables and
run the fixed gate with an explicit project root, a new Attempt ID, a new
report path, and the real accountable owner recorded in the Trace:

```powershell
$env:OPENAI_API_KEY = "<credential from the authorized secret source>"
$env:RWB_WORKER_MODEL = "<approved OpenAI model id>"
rwb providers openai-gate --execute `
  --root . `
  --attempt-id A-OPENAI-GATE-001 `
  --accountable-owner "<real person>" `
  --report runs/provider-conformance/openai-live-gate.yaml
```

The report target must use `.json`, `.yaml`, or `.yml`. Its Decision is
derived deterministically beside it (for example,
`openai-live-gate.decision.yaml`). Publication is exclusive; existing
different content is never replaced.

Exit status is `0` for `passed` and auditable `not-run`, `1` for a completed
gate that failed, and `2` for CLI/configuration or report-publication errors.
Inspect the report's `reason`, phase status, published references, resume-check
result, and fixed `policy` record. Never promote a `not-run` report as live
evidence.
