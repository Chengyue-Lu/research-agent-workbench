"""One-shot delayed export of the available H4a tool spool; gaps stay explicit."""

import hashlib
import json
import subprocess
from pathlib import Path

from research_workbench.observability.trace import AgentTraceRecorder, validate_attempt_trace


class DelayedRecorder(AgentTraceRecorder):
    def _append_event(self, event_type, payload, **kwargs):
        if event_type == "attempt-status" and payload.get("reason") == "trace initialized before provider execution":
            payload = {**payload, "reason": "Delayed H4a export; timestamps describe export, not original actions."}
        return super()._append_event(event_type, payload, **kwargs)


def main():
    root = Path.cwd().resolve()
    archive = Path(__file__).resolve().parent
    trace = archive / "trace"
    if not archive.is_relative_to(root) or trace.exists():
        raise ValueError("Export requires a fresh trace directory within the worktree")
    task = (root / "docs/TASKS.md").read_bytes()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    recorder = DelayedRecorder(
        trace, task_id="M5-007", task_revision=1, attempt_id="M5-007-H4-001",
        task_snapshot={"task_id": "M5-007", "revision": 1, "snapshot_kind": "development-task-row",
            "source_ref": {"path": "docs/TASKS.md", "sha256": hashlib.sha256(task).hexdigest()},
            "source_row": next(line for line in task.decode().splitlines() if line.startswith("| M5-007 |")),
            "implementation_head": head, "owner": "Chengyue-Lu", "risk": "R2",
            "authorization": "User requested implementation of the prepared H4 packet; bounded to H4a.",
            "scope_ref": (archive / "README.md").relative_to(root).as_posix(),
            "required_skills": [], "delegation": False},
        accountable_owner="Chengyue-Lu", actor_id="codex-m5-h4a",
        runtime_identity="Codex local agent / delayed capture export", provider="OpenAI",
        read_allowlist=["AGENTS.md", "docs/**", "src/research_workbench/**", "schemas/**", "tests/**", ".github/**", ".rwb/**"],
        write_scope=["src/research_workbench/evaluation/harness_evidence.py", "src/research_workbench/validation/**",
                     "schemas/v0.1.0/evaluation-harness-evidence.schema.json", "tests/**", "docs/implementation/**",
                     "docs/STATUS.md", "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/**", ".rwb/**"],
        tool_allowlist=["shell", "apply_patch"],
    )
    recorder.record_capture_gap("events", "Partial tool spool only: initial intake, patches, some reads/waits and final publication are absent. Export timestamps do not reconstruct original timing; no write-before-use claim. Truncated output remains truncated.")
    recorder.record_capture_gap("messages", "Native Provider frames were unavailable. No hidden reasoning or invented inter-agent messages; this was a single-agent implementation.")
    rows = json.loads((root / ".rwb/h4-capture.json").read_text(encoding="utf-8"))
    for index, row in enumerate(rows, 1):
        result = row["result"]
        status = "unknown"
        if isinstance(result, dict) and result.get("exit_code") is not None:
            status = "succeeded" if result["exit_code"] == 0 else "failed"
        elif isinstance(result, dict) and result.get("session_id") is not None:
            status = "attempted"
        recorder.record_tool_call(operation_id=f"delayed-h4a-{index:04d}",
            tool_name="shell" if row["tool"] in {"exec_command", "write_stdin"} else "apply_patch",
            status=status, arguments=row["arguments"], result=result, result_entered_context=True)
    recorder.record_attempt_status("incomplete", reason="Partial implementation capture; PR acceptance and Task completion remain human-owned.")
    recorder.seal()
    result = validate_attempt_trace(root, trace)
    report = {"blocked": result.blocked, "risks": [{"code": r.code, "level": r.level.value, "message": r.message} for r in result.risks]}
    (archive / "trace-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report))
    return int(result.blocked)


if __name__ == "__main__":
    raise SystemExit(main())
