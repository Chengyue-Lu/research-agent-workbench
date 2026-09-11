"""Run RWB unittest suites with deterministic duration evidence."""

from __future__ import annotations

import argparse
import inspect
import importlib.util
import json
import math
import os
import platform
from pathlib import Path
import statistics
import sys
import time
import unittest
from typing import Any, Iterable

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
        self._record(test)
        super().startTest(test)

    def stopTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        test_id = test.id()
        started = self._started.pop(test_id, time.perf_counter())
        record = self.records.setdefault(test_id, {"id": test_id, "outcome": "unknown"})
        record["duration_seconds"] = round(time.perf_counter() - started, 6)
        super().stopTest(test)

    def addSuccess(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        outcome = "passed_with_skips" if any(
            point["outcome"] == "skipped" for point in self._record(test)["checkpoints"]) else "passed"
        self._outcome(test, outcome)
        super().addSuccess(test)

    def addFailure(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]) -> None:  # noqa: N802
        self._checkpoint(test, test, "failed", detail=str(err[1]))
        self._outcome(test, "failed", detail=str(err[1]))
        super().addFailure(test, err)

    def addError(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, object]) -> None:  # noqa: N802
        self._checkpoint(test, test, "error", detail=str(err[1]))
        self._outcome(test, "error", detail=str(err[1]))
        super().addError(test, err)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:  # noqa: N802
        parent = getattr(test, "test_case", None)
        if parent is None:
            self._outcome(test, "skipped", reason=reason)
        else:
            self._checkpoint(parent, test, "skipped", reason=reason)
            self._outcome(parent, "passed_with_skips")
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err) -> None:  # noqa: N802
        outcome = "passed" if err is None else (
            "failed" if issubclass(err[0], test.failureException) else "error")
        self._checkpoint(test, subtest, outcome, **({"detail": str(err[1])} if err else {}))
        if err is not None:
            self._outcome(test, outcome)
        super().addSubTest(test, subtest, err)

    def addExpectedFailure(self, test, err) -> None:  # noqa: N802
        self._outcome(test, "expected_failure", detail=str(err[1]))
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test) -> None:  # noqa: N802
        self._outcome(test, "unexpected_success")
        super().addUnexpectedSuccess(test)

    def _record(self, test) -> dict:
        return self.records.setdefault(test.id(), {
            "id": test.id(), "canonical_id": _evidence_test_id(test),
            "module": test.__class__.__module__,
            "scenario": test.shortDescription() or test.id(),
            "outcome": "unknown", "checkpoints": [],
        })

    def _checkpoint(self, test, subtest, outcome, **extra) -> None:
        self._record(test)["checkpoints"].append({"id": subtest.id(), "outcome": outcome, **extra})

    def _outcome(self, test: unittest.case.TestCase, outcome: str, **extra: Any) -> None:
        record = self._record(test)
        # A later successful checkpoint must never erase an earlier failure.
        if record["outcome"] not in {"failed", "error", "unexpected_success"}:
            record.update(outcome=outcome, **extra)


def _load_policy(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("coverage policy must be a mapping")
    return raw


def _iter_tests(suite: unittest.TestSuite) -> Iterable[unittest.case.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def _canonical_test_id(test: unittest.case.TestCase) -> str:
    """Identify one test independently of the module alias used to load it."""

    source = inspect.getsourcefile(test.__class__)
    source_identity = (
        str(Path(source).resolve()).casefold()
        if source is not None
        else f"module:{test.__class__.__module__}"
    )
    method = getattr(test, "_testMethodName", test.id())
    return f"{source_identity}::{test.__class__.__qualname__}.{method}"


def _evidence_test_id(test) -> str:
    """Portable identity for comparing receipts from separate runner checkouts."""
    source = inspect.getsourcefile(test.__class__)
    if source is not None and Path(source).resolve().is_relative_to(ROOT):
        path = Path(source).resolve().relative_to(ROOT).as_posix()
        return f"{path}::{test.__class__.__qualname__}.{getattr(test, '_testMethodName', test.id())}"
    return test.id()


def _verified_plan(path: Path) -> dict:
    scripts = str(ROOT / ".github/scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("ci_planner", ROOT / ".github/scripts/plan_ci.py")
    if spec is None or spec.loader is None:
        raise ValueError("CI planner could not be loaded")
    planner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(planner)
    plan = json.loads(path.read_text(encoding="utf-8"))
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event = json.loads(Path(event_path).read_text(encoding="utf-8")) if event_path else None
    planner.verify_plan(ROOT, plan, event, os.environ.get("GITHUB_EVENT_NAME", "pull_request"))
    return plan


def _assert_unique_tests(suite: unittest.TestSuite) -> None:
    runtime_ids: set[str] = set()
    by_canonical_id: dict[str, str] = {}
    failures: list[str] = []
    for test in _iter_tests(suite):
        runtime_id = test.id()
        canonical_id = _canonical_test_id(test)
        if runtime_id in runtime_ids:
            failures.append(f"runtime:{runtime_id}")
        runtime_ids.add(runtime_id)
        previous = by_canonical_id.get(canonical_id)
        if previous is not None:
            failures.append(f"{canonical_id}: {previous}, {runtime_id}")
        else:
            by_canonical_id[canonical_id] = runtime_id
    if failures:
        raise ValueError(
            "coverage-quality suite contains duplicate canonical tests: "
            + "; ".join(dict.fromkeys(failures))
        )


def _suite_for(args: argparse.Namespace) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(SOURCE) not in sys.path:
        sys.path.insert(0, str(SOURCE))
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    if args.suite == "full":
        loaded = loader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))
        _assert_unique_tests(loaded)
        return loaded
    if args.suite in {"focused", "impact", "coverage-plan"}:
        if args.plan is None:
            raise ValueError("focused suite requires --plan")
        plan = _verified_plan(args.plan)
        if args.suite == "focused" and plan["behavioral_scope"] not in {"none", "focused"}:
            raise ValueError("focused runner requires a selective plan")
        obligations = set(plan["coverage_obligations"])
        if args.suite == "coverage-plan":
            if not obligations:
                raise ValueError("coverage runner requires coverage obligations")
            suites = []
            if "repository" in obligations:
                repository_args = argparse.Namespace(**{**vars(args), "suite": "coverage-quality"})
                suites.append(_suite_for(repository_args))
            if "impact" in obligations:
                suites.append(loader.loadTestsFromNames(plan["coverage_tests"]))
            # Union by canonical identity: preserve all tests while avoiding repeated execution.
            unique = {}
            for suite in suites:
                for test in _iter_tests(suite):
                    unique.setdefault(_canonical_test_id(test), test)
            if loader.errors or not unique:
                raise ValueError("coverage union has missing or empty test groups")
            loaded = unittest.TestSuite(unique.values())
            _assert_unique_tests(loaded)
            return loaded
        if args.suite == "impact" and obligations != {"impact"}:
            raise ValueError("impact runner requires impact coverage")
        loaded = loader.loadTestsFromNames(plan["coverage_tests" if args.suite == "impact" else "tests"])
        if loader.errors or loaded.countTestCases() == 0:
            raise ValueError("focused plan has missing or empty test groups")
        _assert_unique_tests(loaded)
        return loaded
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
    loaded = loader.loadTestsFromNames(names)
    _assert_unique_tests(loaded)
    return loaded


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _execution_suites(args, plan):
    """Load both obligations before subtracting; preserve unittest fixture order."""
    if plan["behavioral_scope"] not in {"full", "focused"}:
        raise ValueError("behavioral execution requires a behavioral obligation")
    def load(name):
        return _suite_for(argparse.Namespace(**{**vars(args), "suite": name}))
    behavioral = load(plan["behavioral_scope"])
    measured = load("coverage-plan") if plan["coverage_obligations"] else unittest.TestSuite()
    return behavioral, measured


def _remainder(behavioral, measured):
    covered = {_canonical_test_id(test) for test in _iter_tests(measured)}
    return unittest.TestSuite(test for test in _iter_tests(behavioral)
                              if _canonical_test_id(test) not in covered)


def _receipt_records(payload, suite, expected, plan):
    """Execution reuse requires complete, successful evidence for this exact plan."""
    if (not isinstance(payload, dict) or payload.get("plan_id") != plan["plan_id"] or payload.get("target") != plan["binding"]["target"]
            or payload.get("coverage_obligations") != plan["coverage_obligations"]
            or payload.get("suite") != suite or payload.get("successful") is not True
            or not str(payload.get("python_version", "")).startswith("3.11.")):
        raise ValueError("execution receipt has a failed or mismatched binding")
    rows = payload.get("tests", [])
    by_id = {row.get("canonical_id"): row for row in rows}
    if (len(by_id) != len(rows) or len({row.get("id") for row in rows}) != len(rows)
            or set(by_id) != set(expected) or payload.get("test_count") != len(expected)):
        raise ValueError("execution receipt has missing, duplicate or unexpected tests")
    allowed = {"passed", "skipped", "passed_with_skips", "expected_failure"}
    for identity, row in by_id.items():
        if row.get("id") != expected[identity] or row.get("outcome") not in allowed:
            raise ValueError("execution receipt contains unsuccessful or aliased test evidence")
        points = row.get("checkpoints", [])
        if any(point.get("outcome") not in {"passed", "skipped"} for point in points):
            raise ValueError("execution receipt contains an unsuccessful checkpoint")
    return by_id


def _combine_behavioral(plan, behavioral, measured, remainder_payload, coverage_payload):
    def inventory(suite):
        return {_evidence_test_id(test): test.id() for test in _iter_tests(suite)}
    complete, coverage = inventory(behavioral), inventory(measured)
    remaining = inventory(_remainder(behavioral, measured))
    rows = _receipt_records(remainder_payload, "behavioral-remainder", remaining, plan)
    if plan["coverage_obligations"]:
        label = "coverage-quality" if "repository" in plan["coverage_obligations"] else "impact"
        rows.update(_receipt_records(coverage_payload, label, coverage, plan))
        if remainder_payload["python_version"] != coverage_payload["python_version"]:
            raise ValueError("execution receipts use different Python versions")
    elif coverage_payload is not None:
        raise ValueError("plan does not authorize coverage receipt reuse")
    result = {
        "schema_version": "1.1.0", "suite": plan["behavioral_scope"], "successful": True,
        "plan_id": plan["plan_id"], "target": plan["binding"]["target"],
        "coverage_obligations": plan["coverage_obligations"],
        "python_version": remainder_payload["python_version"],
        "test_count": len(complete),
        "tests": [{**rows[key], "id": value} for key, value in complete.items()],
        "execution": {
            "behavioral_only": len(remaining), "coverage": len(coverage),
            "reused_for_behavioral": len(set(complete) & set(coverage)),
            "unique_executions": len(set(complete) | set(coverage)),
            "producer_wall_seconds": {"behavioral_remainder": remainder_payload["wall_seconds"],
                                      "coverage": coverage_payload["wall_seconds"] if coverage_payload else 0},
        },
    }
    # The two producers run in parallel. Their durations are not workflow wall time.
    return result


def _write_summary(
    path: Path,
    suite_name: str,
    wall_seconds: float,
    result: TimedTextResult,
    slowest_count: int,
    plan: dict | None = None,
) -> None:
    records = sorted(result.records.values(), key=lambda item: item.get("duration_seconds", 0.0), reverse=True)
    durations = [float(item.get("duration_seconds", 0.0)) for item in records]
    payload = {
        "schema_version": "1.1.0",
        "suite": suite_name,
        "wall_seconds": round(wall_seconds, 6),
        "test_count": result.testsRun,
        "successful": result.wasSuccessful(),
        "outcomes": {
            "passed": sum(item.get("outcome") == "passed" for item in records),
            "failed": sum(item.get("outcome") == "failed" for item in records),
            "errors": sum(item.get("outcome") == "error" for item in records),
            "skipped": sum(item.get("outcome") == "skipped" for item in records),
            "passed_with_skips": sum(item.get("outcome") == "passed_with_skips" for item in records),
            "expected_failure": len(result.expectedFailures),
            "unexpected_success": len(result.unexpectedSuccesses),
        },
        "events": {"failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped)},
        "duration_seconds": {
            "p50": round(statistics.median(durations), 6) if durations else 0.0,
            "p95": round(_percentile(durations, 0.95), 6),
        },
        "slowest": records[:slowest_count],
        "tests": records,
    }
    problems = []
    for record in records:
        failed_points = [point for point in record.get("checkpoints", [])
                         if point["outcome"] in {"failed", "error"}]
        if record.get("outcome") in {"failed", "error", "unexpected_success"}:
            for point in failed_points or [record]:
                problems.append({"module": record.get("module", "fixture"),
                                 "scenario": record.get("scenario", record["id"]),
                                 "checkpoint": point["id"], "outcome": point["outcome"],
                                 "detail": point.get("detail", "")})
    payload["problems"] = problems
    if plan is not None:
        payload.update(plan_id=plan["plan_id"], target=plan["binding"]["target"],
                       python_version=platform.python_version(), coverage_obligations=plan["coverage_obligations"])
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "suite_duration "
        f"suite={suite_name} tests={result.testsRun} wall_seconds={wall_seconds:.3f} "
        f"p50_seconds={payload['duration_seconds']['p50']:.3f} "
        f"p95_seconds={payload['duration_seconds']['p95']:.3f}"
    )
    for problem in problems:
        print(f"FAILED {problem['module']} / {problem['scenario']} / {problem['checkpoint']} ({problem['outcome']}): {problem['detail']}")
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
        if problems:
            # HTML escaping prevents checkpoint parameters from breaking the report.
            import html
            failures = ["#### Failed scenarios and checkpoints", ""]
            for problem in problems:
                failures.append("- " + html.escape(
                    f"{problem['module']} / {problem['scenario']} / {problem['checkpoint']}: {problem['detail']}"))
            lines = [*failures, "", *lines]
        with Path(github_summary).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("full", "coverage-quality", "focused", "impact", "coverage-plan",
                                          "behavioral-remainder", "behavioral-union"), required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--policy", type=Path, default=TESTS / "coverage_policy.yaml")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--behavior-results", type=Path)
    parser.add_argument("--coverage-results", type=Path)
    parser.add_argument("--slowest", type=int, default=20)
    parser.add_argument("--verbosity", type=int, choices=(0, 1, 2), default=2)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    plan = _verified_plan(args.plan) if args.plan else None
    if args.suite in {"behavioral-remainder", "behavioral-union"}:
        if plan is None:
            raise ValueError("execution reuse requires --plan")
        behavioral, measured = _execution_suites(args, plan)
        if args.suite == "behavioral-union":
            if args.behavior_results is None or (plan["coverage_obligations"] and args.coverage_results is None):
                raise ValueError("execution reuse requires every producer receipt")
            combined = _combine_behavioral(plan, behavioral, measured,
                json.loads(args.behavior_results.read_bytes()),
                json.loads(args.coverage_results.read_bytes()) if args.coverage_results else None)
            args.json_output.write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
            explanation = json.dumps(combined["execution"], sort_keys=True)
            print("Verified behavioral union: " + explanation)
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as handle:
                    handle.write("### Verified behavioral execution\n\n" + explanation + "\n")
            return 0
        suite = _remainder(behavioral, measured)
    else:
        suite = _suite_for(args)
    runner = unittest.TextTestRunner(verbosity=args.verbosity, resultclass=TimedTextResult)
    result = runner.run(suite)
    wall_seconds = time.perf_counter() - started
    suite_name = args.suite
    if suite_name == "coverage-plan":
        suite_name = "coverage-quality" if "repository" in plan["coverage_obligations"] else "impact"
    _write_summary(args.json_output, suite_name, wall_seconds, result, args.slowest, plan)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
