"""Reference deterministic validation runner (contract rwb-validation-runner-contract/1).

The trusted validation host invokes this runner as
``python deterministic_runner.py <manifest.json>`` in a fresh, scrubbed
subprocess.  The runner re-hashes the pinned checker source and every subject,
loads the checker module from its exact path, evaluates it, and writes a
canonical ``deterministic_check_report``.  A checker module must expose
``evaluate(subjects)`` returning a mapping with ``checks`` (list of
``{code, status, detail}``), ``scope`` and ``limitations``; each subject entry
carries ``path`` (absolute), ``relative_path`` and ``sha256``.  Checkers must
be byte-deterministic: no wall-clock, randomness, absolute paths, or host
details in the report content.

Exit codes: 0 = PASS report written, 1 = FAIL report written, 2 = runner fault.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import yaml

CONTRACT = "rwb-validation-runner-contract/1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_checker(source_path: Path):
    spec = importlib.util.spec_from_file_location("rwb_pinned_checker", source_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("checker source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: deterministic_runner.py <manifest.json>", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(Path(argv[1]).read_bytes().decode("utf-8"))
    except Exception as exc:
        print(f"manifest unreadable: {type(exc).__name__}", file=sys.stderr)
        return 2
    if not isinstance(manifest, dict) or manifest.get("contract") != CONTRACT:
        print("unsupported runner contract", file=sys.stderr)
        return 2
    checker = manifest["checker"]
    declared = checker["source_ref"]
    source_path = Path(checker["source_path"])
    declared_hash = str(declared["sha256"]).lower().removeprefix("sha256:")
    if not source_path.is_file() or _sha256(source_path) != declared_hash:
        print("checker source drift", file=sys.stderr)
        return 2
    subjects = []
    for item in manifest["subjects"]:
        subject_path = Path(item["path"])
        declared_subject = str(item["sha256"]).lower().removeprefix("sha256:")
        if not subject_path.is_file() or _sha256(subject_path) != declared_subject:
            print(f"subject drift: {item['relative_path']}", file=sys.stderr)
            return 2
        subjects.append(
            {
                "path": str(subject_path),
                "relative_path": item["relative_path"],
                "sha256": item["sha256"],
            }
        )
    try:
        module = _load_checker(source_path)
        evaluation = module.evaluate(subjects)
        checks = [
            {
                "code": str(check["code"]),
                "status": str(check["status"]),
                "detail": str(check["detail"]),
            }
            for check in evaluation["checks"]
        ]
        if not checks:
            raise ValueError("checker returned no checks")
        scope = str(evaluation["scope"])
        limitations = [str(item) for item in evaluation["limitations"]]
    except Exception as exc:
        print(f"checker fault: {type(exc).__name__}", file=sys.stderr)
        return 2
    status = "fail" if any(check["status"] == "fail" for check in checks) else "pass"
    report = {
        "schema_version": "0.1.0",
        "report_id": manifest["report_id"],
        "checker": {
            "checker_id": checker["checker_id"],
            "version": checker["version"],
            "source_ref": {"path": declared["path"], "sha256": declared["sha256"]},
        },
        "subject_refs": [
            {"path": subject["relative_path"], "sha256": subject["sha256"]}
            for subject in subjects
        ],
        "status": status,
        "checks": checks,
        "scope": scope,
        "limitations": limitations,
    }
    Path(manifest["report_out"]).write_bytes(
        yaml.safe_dump(report, sort_keys=True, allow_unicode=True).encode("utf-8")
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
