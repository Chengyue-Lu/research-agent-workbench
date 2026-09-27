#!/usr/bin/env python3
"""Short checks of an already wheel-installed interpreter; never installs packages."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/invalid/objects/decision.json"
PROFILE = "installed-component-smoke-v1"
INSTALLED_SCHEMA_PROBE = r'''
import copy, json, sys
from importlib.metadata import distribution
from pathlib import Path
import research_workbench
from research_workbench.validation.schemas import SchemaCatalog

package = Path(research_workbench.__file__).resolve()
if not package.is_relative_to(Path(sys.prefix).resolve()):
    raise RuntimeError("package must come from the supplied installed environment")
dist = distribution("research-agent-workbench")
direct = json.loads(dist.read_text("direct_url.json") or "{}")
if direct.get("dir_info", {}).get("editable"):
    raise RuntimeError("editable install is not an installed wheel smoke")
invalid = json.load(sys.stdin)
valid = copy.deepcopy(invalid)
valid["timestamp"] = "2026-01-02T03:04:05Z"
catalog = SchemaCatalog()
if catalog.validate("research_object", valid):
    raise RuntimeError("positive research-object schema control failed")
errors = catalog.validate("research_object", invalid)
if not any(error.validator == "format" and error.pointer == "$.timestamp" for error in errors):
    raise RuntimeError("installed schema accepted the invalid RFC3339 timestamp")
print(json.dumps({"python": sys.version.split()[0], "distribution": dist.version,
                  "package": str(package), "positive_schema": True,
                  "invalid_timestamp_rejected": True}, sort_keys=True))
'''


def run_step(name, argv, *, cwd, env, timeout, expected=0, needle=None, input_text=None):
    """Keep an exact expected exit status; an arbitrary failure is not a negative PASS."""
    started = time.monotonic()
    result = {"name": name, "expected_exit": expected, "status": "failure"}
    try:
        process = subprocess.run(argv, cwd=cwd, env=env, input=input_text,
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=max(0.001, timeout), check=False)
        result.update(exit_code=process.returncode, stdout=process.stdout[-6000:],
                      stderr=process.stderr[-6000:])
        if process.returncode == expected and (needle is None or needle in process.stdout):
            result["status"] = "success"
        else:
            result["reason"] = "unexpected exit status or missing required diagnostic"
    except subprocess.TimeoutExpired:
        result["reason"] = "smoke time budget exhausted"
    except OSError as exc:
        result["reason"] = f"cannot execute installed interpreter: {exc}"
    result["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return result


def smoke(python, *, timeout=120):
    started = time.monotonic()
    report = {"schema_version": 1, "profile": PROFILE, "python": str(python),
              "status": "failure", "steps": [], "scope": "installed short smoke"}
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        environment.pop(name, None)
    try:
        fixture = FIXTURE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="rwb-component-smoke-") as temporary:
            cwd = Path(temporary)
            (cwd / "invalid-decision.json").write_text(fixture, encoding="utf-8")
            cli = [str(python), "-I", "-m", "research_workbench"]
            steps = [
                ("installed-import-and-schema", [str(python), "-I", "-c", INSTALLED_SCHEMA_PROBE],
                 {"input_text": fixture}),
                ("runtime-resources", cli + ["resources", "check"], {}),
                ("schema-cli", cli + ["schema", "list"], {}),
                ("research-state-command", cli + ["research-state", "--help"], {}),
                ("offline-project-init", cli + ["init", "project", "--project-id", "ci-smoke"], {}),
                ("offline-project-check", cli + ["project", "check", "project"], {}),
                ("offline-task-validate", cli + ["validate", "project/tasks/task.yaml",
                    "project/profiles/local-no-skill.yaml", "--root", "project"], {}),
                ("invalid-timestamp-cli", cli + ["validate", "invalid-decision.json", "--root", "."],
                 {"expected": 1, "needle": "timestamp"}),
            ]
            for name, command, options in steps:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    report["steps"].append({"name": name, "status": "failure",
                        "reason": "smoke time budget exhausted", "elapsed_seconds": 0})
                    break
                step = run_step(name, command, cwd=cwd, env=environment,
                                timeout=remaining, **options)
                report["steps"].append(step)
                if step["status"] != "success":
                    break
            else:
                report["status"] = "success"
    except (OSError, ValueError) as exc:
        report["reason"] = str(exc)
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=120, help="total smoke budget in seconds")
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    report = smoke(args.python.resolve(), timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{PROFILE}: {report['status']} ({report['elapsed_seconds']:.3f}s)")
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
