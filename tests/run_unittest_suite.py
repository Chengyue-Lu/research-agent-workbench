"""Run RWB unittest suites with deterministic duration evidence."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
import unittest
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
SOURCE = ROOT / "src"


class TimedTextResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._started: dict[str, float] = {}
        self.records: dict[str, dict[str, Any]] = {}

    def startTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        self._started[test.id()] = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        test_id = test.id()
        started = self._started.pop(test_id, time.perf_counter())
        record = self.records.setdefault(test_id, {"id": test_id, "outcome": "unknown"})
        record["duration_seconds"] = round(time.perf_counter() - started, 6)
        super().stopTest(test)

    def addSuccess(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        self._outcome(test, "passed")
        super().addSuccess(test)

    def addFailure(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]) -> None:  # noqa: N802
        self._outcome(test, "failed")
        super().addFailure(test, err)

    def addError(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]) -> None:  # noqa: N802
        self._outcome(test, "error")
        super().addError(test, err)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:  # noqa: N802
        self._outcome(test, "skipped", reason=reason)
        super().addSkip(test, reason)

    def _outcome(self, test: unittest.case.TestCase, outcome: str, **extra: Any) -> None:
        self.records.setdefault(test.id(), {"id": test.id()}).update(outcome=outcome, **extra)


def _load_policy(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("coverage policy must be a mapping")
    return raw


def _suite_for(args: argparse.Namespace) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(SOURCE) not in sys.path:
        sys.path.insert(0, str(SOURCE))
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    if args.suite == "full":
        return loader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))
    policy = _load_policy(args.policy)
    suite = policy.get("suites", {}).get("coverage-quality", {})
    modules = suite.get("modules", [])
    if not isinstance(modules, list) or not modules or not all(isinstance(item, str) for item in modules):
        raise ValueError("coverage-quality suite must declare a non-empty modules list")
    test_ids = suite.get("test_ids", [])
    if not isinstance(test_ids, list) or not all(isinstance(item, str) for item in test_ids):
        raise ValueError("coverage-quality test_ids must be an array of unittest names")
    names = [*modules, *test_ids]
    if len(names) != len(set(names)):
        raise ValueError("coverage-quality suite contains duplicate module/test names")
    return loader.loadTestsFromNames(names)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _write_summary(
    path: Path,
    suite_name: str,
    wall_seconds: float,
    result: TimedTextResult,
    slowest_count: int,
) -> None:
    records = sorted(result.records.values(), key=lambda item: item.get("duration_seconds", 0.0), reverse=True)
    durations = [float(item.get("duration_seconds", 0.0)) for item in records]
    payload = {
        "schema_version": "1.0.0",
        "suite": suite_name,
        "wall_seconds": round(wall_seconds, 6),
        "test_count": result.testsRun,
        "successful": result.wasSuccessful(),
        "outcomes": {
            "passed": sum(item.get("outcome") == "passed" for item in records),
            "failed": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
        },
        "duration_seconds": {
            "p50": round(statistics.median(durations), 6) if durations else 0.0,
            "p95": round(_percentile(durations, 0.95), 6),
        },
        "slowest": records[:slowest_count],
        "tests": records,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "suite_duration "
        f"suite={suite_name} tests={result.testsRun} wall_seconds={wall_seconds:.3f} "
        f"p50_seconds={payload['duration_seconds']['p50']:.3f} "
        f"p95_seconds={payload['duration_seconds']['p95']:.3f}"
    )
    print(f"slowest_{slowest_count}_tests")
    for item in records[:slowest_count]:
        print(f"{item.get('duration_seconds', 0.0):10.3f}s  {item['id']}  {item.get('outcome')}")
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        lines = [
            f"### Test suite: `{suite_name}`",
            "",
            f"- tests: {result.testsRun}",
            f"- wall_seconds: {wall_seconds:.3f}",
            f"- p50_seconds: {payload['duration_seconds']['p50']:.3f}",
            f"- p95_seconds: {payload['duration_seconds']['p95']:.3f}",
            "",
            f"#### Slowest {slowest_count}",
            "",
            "| Seconds | Test | Outcome |",
            "|---:|---|---|",
        ]
        lines.extend(
            f"| {item.get('duration_seconds', 0.0):.3f} | `{item['id']}` | {item.get('outcome')} |"
            for item in records[:slowest_count]
        )
        with Path(github_summary).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("full", "coverage-quality"), required=True)
    parser.add_argument("--policy", type=Path, default=TESTS / "coverage_policy.yaml")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--slowest", type=int, default=20)
    parser.add_argument("--verbosity", type=int, choices=(0, 1, 2), default=2)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=args.verbosity, resultclass=TimedTextResult)
    result = runner.run(_suite_for(args))
    wall_seconds = time.perf_counter() - started
    _write_summary(args.json_output, args.suite, wall_seconds, result, args.slowest)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
