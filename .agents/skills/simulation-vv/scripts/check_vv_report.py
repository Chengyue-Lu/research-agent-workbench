#!/usr/bin/env python3
"""Check structural completeness and claim limits of a simulation V&V report."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping

from research_workbench.io import load_document


SHA256 = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
CHECKS = ("convergence", "sensitivity", "benchmark_comparison")
STATUSES = {"pass", "fail", "not-run", "blocked"}
CLAIMS = {"exploratory", "simulation_supported", "unresolved"}


def validate(document: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, Mapping):
        return ["report must be an object"]
    for field in ("run_ref", "model_version", "parameter_boundary"):
        if not isinstance(document.get(field), str) or not str(document[field]).strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ("assumptions", "limitations"):
        value = document.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"{field} must be an array of strings")
    if document.get("claim_ceiling") not in CLAIMS:
        errors.append("claim_ceiling exceeds or does not declare the simulation limit")
    lock = document.get("input_lock")
    if not isinstance(lock, list) or not lock:
        errors.append("input_lock must contain at least one pinned input")
    else:
        for index, item in enumerate(lock):
            if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                errors.append(f"input_lock[{index}] must contain path and sha256")
            elif not isinstance(item.get("sha256"), str) or not SHA256.fullmatch(item["sha256"]):
                errors.append(f"input_lock[{index}].sha256 is invalid")
    checks = document.get("checks")
    if not isinstance(checks, Mapping):
        errors.append("checks must be an object")
    else:
        for name in CHECKS:
            check = checks.get(name)
            if not isinstance(check, Mapping):
                errors.append(f"checks.{name} is required")
                continue
            status = check.get("status")
            refs = check.get("evidence_refs")
            if status not in STATUSES:
                errors.append(f"checks.{name}.status is invalid")
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                errors.append(f"checks.{name}.evidence_refs must be an array of strings")
            elif status == "pass" and not refs:
                errors.append(f"checks.{name} cannot pass without evidence_refs")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()
    errors = validate(load_document(args.report))
    for error in errors:
        print(f"ERROR VV-STRUCTURE {error}")
    if errors:
        return 1
    print("OK structural V&V checks passed; numerical and scientific correctness were not evaluated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
