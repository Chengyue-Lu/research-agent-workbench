"""Validate coverage and negative-acceptance evidence against one policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import yaml


CANONICAL_SOURCE_ROOT = "src/research_workbench"


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def _normalized_path(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _line_percent(summary: Mapping[str, Any]) -> float:
    statements = int(summary.get("num_statements", 0))
    covered = int(summary.get("covered_lines", 0))
    return 100.0 if statements == 0 else covered * 100.0 / statements


def _branch_percent(summary: Mapping[str, Any]) -> float:
    branches = int(summary.get("num_branches", 0))
    covered = int(summary.get("covered_branches", 0))
    return 100.0 if branches == 0 else covered * 100.0 / branches


def _source_line_percent(files: Mapping[str, Mapping[str, Any]], source_root: str) -> float:
    prefix = _normalized_path(source_root).rstrip("/") + "/"
    statements = 0
    covered = 0
    for path, item in files.items():
        if not path.startswith(prefix):
            continue
        summary = _mapping(item.get("summary"), f"coverage summary {path}")
        statements += int(summary.get("num_statements", 0))
        covered += int(summary.get("covered_lines", 0))
    if statements == 0:
        raise ValueError(f"coverage data has no files under source_root {source_root}")
    return covered * 100.0 / statements


def _actual_exclusions(files: Mapping[str, Mapping[str, Any]]) -> set[tuple[str, int]]:
    actual: set[tuple[str, int]] = set()
    for path, item in files.items():
        excluded_lines = item.get("excluded_lines", [])
        if not isinstance(excluded_lines, list):
            raise ValueError(f"coverage excluded_lines must be a list: {path}")
        for line in excluded_lines:
            if not isinstance(line, int) or isinstance(line, bool) or line < 1:
                raise ValueError(f"coverage excluded line must be a positive integer: {path}:{line}")
            actual.add((path, line))
    return actual


def _declared_exclusions(policy: Mapping[str, Any], failures: list[str]) -> set[tuple[str, int]]:
    exclusions = policy.get("justified_exclusions")
    if not isinstance(exclusions, list):
        failures.append("justified_exclusions must be a list")
        return set()

    declared: set[tuple[str, int]] = set()
    for index, exclusion in enumerate(exclusions):
        item = _mapping(exclusion, f"justified_exclusions[{index}]")
        if not all(item.get(key) for key in ("path", "lines", "reason", "owner")):
            failures.append(f"justified_exclusions[{index}] must name path, lines, reason, and owner")
        path = _normalized_path(str(item.get("path", "")))
        if any(symbol in path for symbol in ("*", "?", "[", "]", "{")) or path.endswith("/"):
            failures.append(f"justified_exclusions[{index}] path must be exact, not a wildcard or directory")
        lines = item.get("lines")
        if not isinstance(lines, list) or not lines:
            failures.append(f"justified_exclusions[{index}] lines must be a non-empty exact integer list")
            continue
        if any(not isinstance(line, int) or isinstance(line, bool) or line < 1 for line in lines):
            failures.append(f"justified_exclusions[{index}] lines must contain only positive integers")
            continue
        if len(lines) != len(set(lines)):
            failures.append(f"justified_exclusions[{index}] lines contain duplicates")
        for line in lines:
            key = (path, line)
            if key in declared:
                failures.append(f"justified exclusion is declared more than once: {path}:{line}")
            declared.add(key)
    return declared


def check_policy(policy: Mapping[str, Any], coverage: Mapping[str, Any], results: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if coverage.get("meta", {}).get("branch_coverage") is not True:
        failures.append("coverage data must be collected with branch coverage enabled")

    thresholds = _mapping(policy.get("thresholds"), "thresholds")
    global_threshold = _number(_mapping(thresholds.get("global"), "thresholds.global").get("line"), "global line")
    critical_thresholds = _mapping(thresholds.get("critical"), "thresholds.critical")
    critical_line = _number(critical_thresholds.get("line"), "critical line")
    critical_branch = _number(critical_thresholds.get("branch"), "critical branch")
    if global_threshold < 90 or critical_line < 95 or critical_branch < 90:
        failures.append("policy thresholds cannot be lower than global 90 / critical line 95 / critical branch 90")

    files = {
        _normalized_path(str(path)): _mapping(item, f"coverage file {path}")
        for path, item in _mapping(coverage.get("files"), "coverage files").items()
    }
    source_root = policy.get("source_root")
    if source_root != CANONICAL_SOURCE_ROOT:
        failures.append(f"source_root must be exactly {CANONICAL_SOURCE_ROOT}")
    global_line = _source_line_percent(files, CANONICAL_SOURCE_ROOT)
    print(f"global line={global_line:.2f}% threshold={global_threshold:.2f}%")
    if global_line + 1e-9 < global_threshold:
        failures.append(f"global line coverage {global_line:.2f}% is below {global_threshold:.2f}%")
    critical_modules = policy.get("critical_modules")
    if not isinstance(critical_modules, list) or not critical_modules:
        failures.append("critical_modules must be a non-empty list")
        critical_modules = []
    for path in critical_modules:
        normalized = _normalized_path(str(path))
        item = files.get(normalized)
        if item is None:
            failures.append(f"critical module missing from coverage data: {normalized}")
            continue
        summary = _mapping(item.get("summary"), f"coverage summary {normalized}")
        line = _line_percent(summary)
        branch = _branch_percent(summary)
        print(
            f"critical {normalized} line={line:.2f}%/{critical_line:.2f}% "
            f"branch={branch:.2f}%/{critical_branch:.2f}%"
        )
        if line + 1e-9 < critical_line:
            failures.append(f"{normalized} line coverage {line:.2f}% is below {critical_line:.2f}%")
        if branch + 1e-9 < critical_branch:
            failures.append(f"{normalized} branch coverage {branch:.2f}% is below {critical_branch:.2f}%")

    declared_exclusions = _declared_exclusions(policy, failures)
    actual_exclusions = _actual_exclusions(files)
    for path, line in sorted(actual_exclusions - declared_exclusions):
        failures.append(f"coverage contains undeclared excluded line: {path}:{line}")
    for path, line in sorted(declared_exclusions - actual_exclusions):
        failures.append(f"policy declares an excluded line absent from coverage data: {path}:{line}")

    if results.get("suite") != "coverage-quality" or results.get("successful") is not True:
        failures.append("coverage-quality test result must be successful")
    passed = {
        str(item.get("id"))
        for item in results.get("tests", [])
        if isinstance(item, Mapping) and item.get("outcome") == "passed"
    }
    covered_by_evidence: set[str] = set()
    evidence = policy.get("negative_acceptance")
    if not isinstance(evidence, list) or not evidence:
        failures.append("negative_acceptance must be a non-empty list")
        evidence = []
    for index, surface in enumerate(evidence):
        item = _mapping(surface, f"negative_acceptance[{index}]")
        name = str(item.get("surface", f"index-{index}"))
        modules = item.get("modules", [])
        positives = item.get("positive_tests", [])
        negatives = item.get("negative_tests", [])
        if not isinstance(modules, list) or not isinstance(positives, list) or not isinstance(negatives, list):
            failures.append(f"negative acceptance surface {name} modules and tests must be lists")
            continue
        if not modules or not positives or not negatives:
            failures.append(f"negative acceptance surface {name} requires modules and positive/negative tests")
            continue
        if not all(isinstance(value, str) and value for value in [*modules, *positives, *negatives]):
            failures.append(f"negative acceptance surface {name} modules and tests must be non-empty strings")
            continue
        if len(positives) != len(set(positives)):
            failures.append(f"negative acceptance surface {name} repeats positive test IDs")
        if len(negatives) != len(set(negatives)):
            failures.append(f"negative acceptance surface {name} repeats negative test IDs")
        overlap = sorted(set(positives) & set(negatives))
        if overlap:
            failures.append(
                f"negative acceptance surface {name} reuses tests as positive and negative evidence: {overlap}"
            )
        covered_by_evidence.update(_normalized_path(str(path)) for path in modules)
        for test_id in [*positives, *negatives]:
            if test_id not in passed:
                failures.append(f"negative acceptance surface {name} lacks passing evidence: {test_id}")
    for path in critical_modules:
        normalized = _normalized_path(str(path))
        if normalized not in covered_by_evidence:
            failures.append(f"critical module lacks explicit positive/negative acceptance mapping: {normalized}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--test-results", type=Path, required=True)
    args = parser.parse_args(argv)
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    results = json.loads(args.test_results.read_text(encoding="utf-8"))
    try:
        failures = check_policy(_mapping(policy, "policy"), _mapping(coverage, "coverage"), _mapping(results, "results"))
    except ValueError as exc:
        failures = [str(exc)]
    if failures:
        print("coverage-policy: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("coverage-policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
