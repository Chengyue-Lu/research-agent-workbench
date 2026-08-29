from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from tests import run_unittest_suite


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "tests" / "coverage_policy.yaml"
SCRIPT = ROOT / ".github" / "scripts" / "check_coverage_policy.py"
SPEC = importlib.util.spec_from_file_location("check_coverage_policy", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


MODULE = "src/research_workbench/protocol/authority.py"
POSITIVE = "test_policy.Example.test_allow"
NEGATIVE = "test_policy.Example.test_block"


def policy() -> dict:
    return {
        "source_root": "src/research_workbench",
        "thresholds": {
            "global": {"line": 90},
            "critical": {"line": 95, "branch": 90},
        },
        "critical_modules": [MODULE],
        "negative_acceptance": [
            {
                "surface": "authority",
                "modules": [MODULE],
                "positive_tests": [POSITIVE],
                "negative_tests": [NEGATIVE],
            }
        ],
        "justified_exclusions": [],
    }


def coverage(*, branch: bool = True, global_covered: int = 90, line_covered: int = 95, branch_covered: int = 90) -> dict:
    noncritical_covered = 2 * global_covered - line_covered
    return {
        "meta": {"branch_coverage": branch},
        "totals": {"num_statements": 100, "covered_lines": global_covered},
        "files": {
            MODULE: {
                "excluded_lines": [],
                "summary": {
                    "num_statements": 100,
                    "covered_lines": line_covered,
                    "num_branches": 100,
                    "covered_branches": branch_covered,
                }
            },
            "src/research_workbench/cli.py": {
                "excluded_lines": [],
                "summary": {
                    "num_statements": 100,
                    "covered_lines": noncritical_covered,
                    "num_branches": 0,
                    "covered_branches": 0,
                }
            },
        },
    }


def results(*, include_negative: bool = True) -> dict:
    tests = [{"id": POSITIVE, "outcome": "passed"}]
    if include_negative:
        tests.append({"id": NEGATIVE, "outcome": "passed"})
    return {"suite": "coverage-quality", "successful": True, "tests": tests}


class CoveragePolicyCheckerTests(unittest.TestCase):
    def test_exact_thresholds_and_positive_negative_evidence_pass(self) -> None:
        self.assertEqual(CHECKER.check_policy(policy(), coverage(), results()), [])

    def test_branch_collection_is_mandatory(self) -> None:
        failures = CHECKER.check_policy(policy(), coverage(branch=False), results())
        self.assertTrue(any("branch coverage enabled" in item for item in failures))

    def test_global_line_threshold_is_fail_closed(self) -> None:
        failures = CHECKER.check_policy(policy(), coverage(global_covered=89), results())
        self.assertTrue(any("global line coverage" in item for item in failures))

    def test_each_critical_file_has_independent_line_and_branch_gates(self) -> None:
        failures = CHECKER.check_policy(
            policy(), coverage(line_covered=94, branch_covered=89), results()
        )
        self.assertTrue(any("line coverage" in item for item in failures))
        self.assertTrue(any("branch coverage" in item for item in failures))

    def test_missing_negative_acceptance_result_is_blocking(self) -> None:
        failures = CHECKER.check_policy(policy(), coverage(), results(include_negative=False))
        self.assertTrue(any(NEGATIVE in item for item in failures))
        failed_result = results()
        failed_result["tests"][1]["outcome"] = "failed"
        failures = CHECKER.check_policy(policy(), coverage(), failed_result)
        self.assertTrue(any(NEGATIVE in item for item in failures))

    def test_missing_critical_file_is_blocking(self) -> None:
        report = coverage()
        report["files"].pop(MODULE)
        failures = CHECKER.check_policy(policy(), report, results())
        self.assertTrue(any("critical module missing" in item for item in failures))

    def test_coverage_suite_supports_exact_test_selectors_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "policy.yaml"
            document = {
                "suites": {
                    "coverage-quality": {
                        "modules": ["test_integrity"],
                        "test_ids": [
                            "test_kernel.KernelObjectTests.test_revision_is_part_of_object_reference"
                        ],
                    }
                }
            }
            path.write_text(yaml.safe_dump(document), encoding="utf-8")
            args = argparse.Namespace(suite="coverage-quality", policy=path)
            self.assertEqual(2, run_unittest_suite._suite_for(args).countTestCases())
            document["suites"]["coverage-quality"]["test_ids"] = ["test_integrity"]
            path.write_text(yaml.safe_dump(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                run_unittest_suite._suite_for(args)

    def test_coverage_suite_rejects_same_canonical_test_loaded_through_module_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "policy.yaml"
            document = {
                "suites": {
                    "coverage-quality": {
                        "modules": ["test_kernel"],
                        "test_ids": ["tests.test_kernel"],
                    }
                }
            }
            path.write_text(yaml.safe_dump(document), encoding="utf-8")
            args = argparse.Namespace(suite="coverage-quality", policy=path)
            with self.assertRaisesRegex(ValueError, "duplicate canonical tests"):
                run_unittest_suite._suite_for(args)

    def test_policy_cannot_downgrade_the_quality_floor(self) -> None:
        manifest = policy()
        manifest["thresholds"]["critical"]["branch"] = 89
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("cannot be lower" in item for item in failures))

    def test_source_root_is_canonical_and_cannot_be_narrowed(self) -> None:
        manifest = policy()
        manifest["source_root"] = "src/research_workbench/protocol"
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("source_root must be exactly" in item for item in failures))

    def test_positive_and_negative_evidence_must_be_disjoint(self) -> None:
        manifest = policy()
        manifest["negative_acceptance"][0]["negative_tests"] = [POSITIVE]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("reuses tests" in item for item in failures))

    def test_positive_and_negative_evidence_reject_internal_duplicates(self) -> None:
        manifest = policy()
        manifest["negative_acceptance"][0]["positive_tests"] = [POSITIVE, POSITIVE]
        manifest["negative_acceptance"][0]["negative_tests"] = [NEGATIVE, NEGATIVE]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("repeats positive" in item for item in failures))
        self.assertTrue(any("repeats negative" in item for item in failures))

    def test_positive_and_negative_evidence_must_be_nonempty_lists(self) -> None:
        manifest = policy()
        manifest["negative_acceptance"][0]["positive_tests"] = []
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("requires modules" in item for item in failures))
        manifest["negative_acceptance"][0]["positive_tests"] = POSITIVE
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("must be lists" in item for item in failures))
        manifest["negative_acceptance"][0]["positive_tests"] = [""]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("non-empty strings" in item for item in failures))

    def test_declared_exclusions_exactly_match_coverage_json(self) -> None:
        manifest = policy()
        manifest["justified_exclusions"] = [
            {
                "path": MODULE,
                "lines": [7, 9],
                "reason": "Protocol-only declarations have no executable body",
                "owner": "Chengyue-Lu",
            }
        ]
        report = coverage()
        report["files"][MODULE]["excluded_lines"] = [7, 9]
        self.assertEqual(CHECKER.check_policy(manifest, report, results()), [])

    def test_undeclared_actual_and_nonexistent_declared_exclusions_fail(self) -> None:
        report = coverage()
        report["files"][MODULE]["excluded_lines"] = [7]
        failures = CHECKER.check_policy(policy(), report, results())
        self.assertTrue(any("undeclared excluded line" in item for item in failures))

        manifest = policy()
        manifest["justified_exclusions"] = [
            {"path": MODULE, "lines": [8], "reason": "exact", "owner": "Chengyue-Lu"}
        ]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("absent from coverage data" in item for item in failures))

    def test_exclusion_line_shape_and_duplicates_are_fail_closed(self) -> None:
        manifest = policy()
        manifest["justified_exclusions"] = [
            {"path": MODULE, "lines": [7, 7], "reason": "exact", "owner": "Chengyue-Lu"},
            {"path": MODULE, "lines": [7], "reason": "exact", "owner": "Chengyue-Lu"},
            {"path": "src/research_workbench/", "lines": "1-3", "reason": "broad", "owner": "owner"},
        ]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("lines contain duplicates" in item for item in failures))
        self.assertTrue(any("declared more than once" in item for item in failures))
        self.assertTrue(any("non-empty exact integer list" in item for item in failures))
        self.assertTrue(any("wildcard or directory" in item for item in failures))

    def test_malformed_coverage_exclusions_fail_closed(self) -> None:
        report = coverage()
        report["files"][MODULE]["excluded_lines"] = "7"
        with self.assertRaisesRegex(ValueError, "excluded_lines must be a list"):
            CHECKER.check_policy(policy(), report, results())
        report["files"][MODULE]["excluded_lines"] = [True]
        with self.assertRaisesRegex(ValueError, "positive integer"):
            CHECKER.check_policy(policy(), report, results())

    def test_repository_policy_covers_bounded_capability_validation_surfaces(self) -> None:
        manifest = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
        critical = set(manifest["critical_modules"])
        self.assertIn("src/research_workbench/validation/capability.py", critical)
        self.assertIn(
            "src/research_workbench/validation/capability_registry.py", critical
        )
        self.assertIn("src/research_workbench/validation/document_core.py", critical)
        self.assertIn(".github/scripts/check_coverage_policy.py", critical)
        self.assertIn("src/research_workbench/validation/authority_registry.py", critical)
        self.assertIn(
            "src/research_workbench/validation/capability_supply_registry.py", critical
        )
        self.assertIn(
            "src/research_workbench/validation/method_resolution_registry.py", critical
        )
        self.assertIn("src/research_workbench/validation/phase_b_gate.py", critical)
        self.assertNotIn("src/research_workbench/validation/documents.py", critical)
        omitted = {
            item["module"]
            for item in manifest["suites"]["coverage-quality"]["omitted_modules"]
        }
        self.assertTrue(
            {
                "test_generic_execution_closeout",
                "test_execution_host",
                "test_execution_trace_adapter",
                "test_m3_context_observability",
            }.issubset(omitted)
        )

    def test_exclusion_requires_exact_auditable_location(self) -> None:
        manifest = policy()
        manifest["justified_exclusions"] = [
            {
                "path": "src/research_workbench/**",
                "lines": [1],
                "reason": "too broad",
                "owner": "Chengyue-Lu",
            }
        ]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("not a wildcard" in item for item in failures))

    def test_checker_main_reports_pass_and_fail_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy_path = root / "policy.yaml"
            coverage_path = root / "coverage.json"
            results_path = root / "results.json"
            policy_path.write_text(yaml.safe_dump(policy()), encoding="utf-8")
            coverage_path.write_text(json.dumps(coverage()), encoding="utf-8")
            results_path.write_text(json.dumps(results()), encoding="utf-8")
            argv = [
                "--policy", str(policy_path),
                "--coverage", str(coverage_path),
                "--test-results", str(results_path),
            ]
            self.assertEqual(0, CHECKER.main(argv))
            coverage_path.write_text("[]", encoding="utf-8")
            self.assertEqual(1, CHECKER.main(argv))

    def test_checker_helpers_and_structural_failures_are_explicit(self) -> None:
        self.assertEqual("a/b.py", CHECKER._normalized_path("./a\\b.py"))
        self.assertEqual(100.0, CHECKER._line_percent({"num_statements": 0}))
        self.assertEqual(100.0, CHECKER._branch_percent({"num_branches": 0}))
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            CHECKER._mapping([], "sample")
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            CHECKER._number(True, "sample")
        with self.assertRaisesRegex(ValueError, "no files"):
            CHECKER._source_line_percent({}, CHECKER.CANONICAL_SOURCE_ROOT)

        manifest = policy()
        manifest["critical_modules"] = []
        manifest["negative_acceptance"] = []
        manifest["justified_exclusions"] = None
        report = coverage(branch=False, global_covered=89, line_covered=94, branch_covered=89)
        evidence = {"suite": "wrong", "successful": False, "tests": []}
        failures = CHECKER.check_policy(manifest, report, evidence)
        self.assertTrue(any("critical_modules" in item for item in failures))
        self.assertTrue(any("negative_acceptance" in item for item in failures))
        self.assertTrue(any("justified_exclusions" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
