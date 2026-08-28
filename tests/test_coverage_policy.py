from __future__ import annotations

import argparse
import importlib.util
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
                "summary": {
                    "num_statements": 100,
                    "covered_lines": line_covered,
                    "num_branches": 100,
                    "covered_branches": branch_covered,
                }
            },
            "src/research_workbench/cli.py": {
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

    def test_repository_policy_covers_bounded_capability_validation_surfaces(self) -> None:
        manifest = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
        critical = set(manifest["critical_modules"])
        self.assertIn("src/research_workbench/validation/capability.py", critical)
        self.assertIn(
            "src/research_workbench/validation/capability_registry.py", critical
        )
        self.assertIn("src/research_workbench/validation/document_core.py", critical)
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
                "lines": "1-9999",
                "reason": "too broad",
                "owner": "Chengyue-Lu",
            }
        ]
        failures = CHECKER.check_policy(manifest, coverage(), results())
        self.assertTrue(any("not a wildcard" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
