"""Export available M5 tool evidence as a gapped, delayed Agent Trace v0.1.

This adapter preserves observed payloads. Export timestamps are not reconstructed
action timestamps, and missing events/results remain explicit capture gaps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from research_workbench.observability.trace import AgentTraceRecorder, validate_attempt_trace

class DelayedExportRecorder(AgentTraceRecorder):
    def _append_event(self, event_type, payload, **kwargs):
        if event_type == "attempt-status" and payload.get("reason") == "trace initialized before provider execution":
            payload = {**payload, "reason": "Delayed export initialized; original event timing was not captured."}
        return super()._append_event(event_type, payload, **kwargs)

def hash_bytes(content):
    return hashlib.sha256(content).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--attempt", default="docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-006-IMPLEMENTATION-001")
    parser.add_argument("--status", choices=("incomplete",), default="incomplete")
    args = parser.parse_args()
    root = args.root.resolve()
    attempt = (root / args.attempt).resolve()
    if not attempt.is_relative_to(root) or attempt.exists():
        raise ValueError("Archive must be a new path inside the declared root")
    task_bytes = (root / "docs/TASKS.md").read_bytes()
    task_row = next(line for line in task_bytes.decode().splitlines() if line.startswith("| M5-006 |"))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    recorder = DelayedExportRecorder(
        attempt, task_id="M5-006", task_revision=1, attempt_id=attempt.name,
        task_snapshot={
            "task_id": "M5-006", "revision": 1, "snapshot_kind": "development-task-row",
            "owner": "Chengyue-Lu", "risk": "R2", "source_ref": {
                "path": "docs/TASKS.md", "sha256": hash_bytes(task_bytes),
            }, "source_row": task_row, "implementation_head": head,
            "authorization": "User requested implementation of the M5 entry plan.",
            "required_skills": [], "delegation": False,
        },
        accountable_owner="Chengyue-Lu", actor_id="codex-m5-implementation",
        runtime_identity="Codex local agent / delayed export adapter", provider="OpenAI",
        read_allowlist=["AGENTS.md", "docs/**", "schemas/**", "src/research_workbench/**", "tests/**",
                        ".github/**", "registry/**", "examples/**", ".rwb/m5-006/**"],
        write_scope=["src/research_workbench/evaluation/**", "src/research_workbench/cli.py",
                     "src/research_workbench/validation/**", "schemas/v0.1.0/**", "tests/**",
                     "docs/implementation/**", "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/**",
                     "docs/TASKS.md", "docs/STATUS.md", ".rwb/m5-006/**"],
        tool_allowlist=["shell", "apply_patch"],
    )
    recorder.record_capture_gap(
        "events",
        "Delayed export from available tool spools. Initial setup reads, some patch results, wait completions, "
        "and unspooled tool calls were not retained. No original event timestamps or write-before-use guarantee "
        "are reconstructed. Truncated tool output is preserved as received, not expanded."
    )
    recorder.record_capture_gap(
        "messages",
        "Original provider request/response stream was not available to this export adapter. "
        "No hidden reasoning is captured. This was a single-agent task with no inter-agent transmissions."
    )
    number = 0
    uncaptured_results = []
    for spool in sorted((root / ".rwb/m5-006").glob("capture-*.json")):
        for item in json.loads(spool.read_text(encoding="utf-8")):
            number += 1
            result = item.get("result")
            if isinstance(result, dict) and result.get("status") == "fulfilled":
                result = result.get("value")
            arguments = item.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {"patch": arguments}
            if result is None:
                operation_id = f"delayed-capture-{number:04d}"
                uncaptured_results.append({"operation_id": operation_id, "tool": item.get("tool"), "arguments": arguments})
                recorder.record_capture_gap("tool-results", "Call arguments retained but original result not captured; no result-entry claim is reconstructed.", affected_ids=[operation_id])
                continue
            outcome = "unknown"
            if isinstance(result, dict) and "exit_code" in result:
                outcome = "succeeded" if result["exit_code"] == 0 else "failed"
            elif isinstance(result, dict) and "session_id" in result:
                outcome = "attempted"
            recorder.record_tool_call(
                operation_id=f"delayed-capture-{number:04d}",
                tool_name="shell" if item.get("tool") == "exec_command" else "apply_patch",
                status=outcome, arguments=arguments, result=result,
                result_entered_context=result is not None,
            )
    evidence = attempt / "evidence"
    evidence.mkdir()
    argument_path = evidence / "calls-with-uncaptured-results.json"
    argument_path.write_text(json.dumps(uncaptured_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    recorder.record_file_revision(argument_path.relative_to(root).as_posix(), action="created",
                                 new_sha256=hash_bytes(argument_path.read_bytes()), reason="Retained original arguments associated with explicit result capture gaps.")
    names = [
        "focused-tests.log", "overlay-tests.log", "documentation-tests.log",
        "repository-validation.log", "portable-package-results.json", "package-smoke.log",
        "ci-plan.json", "ci-plan-full.json", "coverage-focused-final.json",
        "coverage.json", "coverage-test-results.json", "full-test-results-3.11.json",
        "local-governance.log", "coverage-enforcement.log", "final-delta-tests.log",
    ]
    for name in names:
        path = root / ".rwb/m5-006" / name
        if path.is_file():
            destination = evidence / name
            shutil.copyfile(path, destination)
            relative = destination.relative_to(root).as_posix()
            recorder.record_file_revision(relative, action="created", new_sha256=hash_bytes(destination.read_bytes()),
                                          reason="Preserved actual local validation output; consult its own head/plan binding.")
    recorder.record_attempt_status(args.status, reason="Implementation evidence export; Task acceptance and PR review remain human-owned.")
    recorder.seal()
    shutil.copyfile(Path(__file__), attempt / "export_capture.py")
    (attempt / "README.md").write_text(
        "# M5-006 implementation evidence\n\n"
        "This is a delayed, gapped export of captured tool payloads plus local validation artifacts.\n"
        "Event timestamps describe export time. Missing original calls/results and provider messages remain\n"
        "capture gaps; no write-before-use or complete transcript claim is made. Initial status wording is\n"
        "adapted before serialization to identify the delayed export. Tool outcome is unknown when the\n"
        "retained response does not establish completion. No hidden reasoning or credentials are recorded.\n\n"
        "Task status in this archive describes the implementation attempt; acceptance, cross-owner review\n"
        "and all downstream execution/Human gates remain separate. Each evidence file retains its own\n"
        "commit/plan binding where available. Earlier diagnostic runs are not final-head acceptance.\n\n"
        "[Work log](../../WORKLOG.md) records current validation and handoff.\n",
        encoding="utf-8", newline="\n")
    result = validate_attempt_trace(root, attempt)
    report = {"blocked": result.blocked, "risks": [
        {"code": risk.code, "level": risk.level.value, "message": risk.message}
        for risk in result.risks
    ]}
    (attempt / "trace-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if result.blocked:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
