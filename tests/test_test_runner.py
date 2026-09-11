"""Scenario reporting and exact-plan reuse of executed unittest evidence."""
from __future__ import annotations

import argparse
import copy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests import run_unittest_suite as runner


def run_suite(suite):
    return unittest.TextTestRunner(stream=io.StringIO(), resultclass=runner.TimedTextResult).run(suite)


def plan(obligations=None):
    return {"plan_id": "exact-plan", "binding": {"target": "exact-target"},
            "behavioral_scope": "full", "coverage_obligations": ["impact"] if obligations is None else obligations}


def receipt(suite, name, p):
    result = run_suite(suite)
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()):
        output = Path(directory) / "results.json"
        runner._write_summary(output, name, 0.1, result, 2, p)
        payload = json.loads(output.read_bytes())
    # The production verifier requires 3.11; synthetic receipts also run under 3.13 in CI.
    payload["python_version"] = "3.11.16"
    return payload


def scenarios(events):
    class Scenario(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            events.append("setup")

        @classmethod
        def tearDownClass(cls):
            events.append("teardown")

        def test_measured(self):
            events.append("measured")

        def test_remaining(self):
            events.append("remaining")

    return Scenario


class ScenarioReportTests(unittest.TestCase):
    def test_failures_keep_named_checkpoints_and_continue_to_later_checks(self):
        """One scenario reports both failed checkpoints and the later successful check."""
        class Scenario(unittest.TestCase):
            def runTest(self):
                """Validate archive lifecycle."""
                with self.subTest(checkpoint="admission", case="bad digest"):
                    self.assertEqual("actual", "expected")
                with self.subTest(checkpoint="promotion"):
                    raise ValueError("missing approval")
                with self.subTest(checkpoint="recovery"):
                    self.assertTrue(True)
        result = run_suite(unittest.TestSuite([Scenario()]))
        row = next(iter(result.records.values()))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual("failed", row["outcome"])
        self.assertEqual(["failed", "error", "passed"], [p["outcome"] for p in row["checkpoints"]])
        self.assertIn("bad digest", row["checkpoints"][0]["id"])
        with tempfile.TemporaryDirectory() as directory:
            output, summary = Path(directory) / "result.json", Path(directory) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}), redirect_stdout(io.StringIO()) as console:
                runner._write_summary(output, "focused", 1.0, result, 1)
            payload = json.loads(output.read_bytes())
            self.assertEqual(1, payload["test_count"])
            self.assertEqual(2, len(payload["problems"]))
            self.assertEqual(1, payload["outcomes"]["failed"])
            self.assertEqual({"failures": 1, "errors": 1, "skips": 0}, payload["events"])
            self.assertIn("Validate archive lifecycle.", summary.read_text())
            self.assertIn("missing approval", console.getvalue())
            self.assertLess(summary.read_text().index("Failed scenarios"), summary.read_text().index("Slowest"))

    def test_nested_and_skipped_checkpoints_do_not_claim_complete_pass(self):
        class Scenario(unittest.TestCase):
            def runTest(self):
                with self.subTest(checkpoint="outer"):
                    with self.subTest(case="unavailable"):
                        self.skipTest("platform fixture")
                    with self.subTest(case="available"):
                        self.assertTrue(True)
        result = run_suite(unittest.TestSuite([Scenario()]))
        row = next(iter(result.records.values()))
        self.assertTrue(result.wasSuccessful())
        self.assertEqual("passed_with_skips", row["outcome"])
        self.assertEqual(1, len(result.skipped))
        self.assertIn("outer", row["checkpoints"][0]["id"])
        self.assertIn("unavailable", row["checkpoints"][0]["id"])

    def test_scenario_errors_skips_and_expected_failures_remain_distinct(self):
        class Scenario(unittest.TestCase):
            def test_failure(self): self.fail("failure")
            def test_error(self): raise ValueError("error")
            @unittest.skip("platform")
            def test_skip(self): pass
            @unittest.expectedFailure
            def test_expected(self): self.fail("known")
            @unittest.expectedFailure
            def test_unexpected(self): pass
        result = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Scenario))
        outcomes = {row["id"].rsplit(".", 1)[-1]: row["outcome"] for row in result.records.values()}
        self.assertEqual({"test_failure": "failed", "test_error": "error", "test_skip": "skipped",
                          "test_expected": "expected_failure", "test_unexpected": "unexpected_success"}, outcomes)
        self.assertFalse(result.wasSuccessful())

    def test_class_fixture_failure_is_visible_without_fabricating_executed_tests(self):
        class Scenario(unittest.TestCase):
            @classmethod
            def setUpClass(cls): raise ValueError("fixture unavailable")
            def test_never_runs(self): self.fail("must not run")
        payload = receipt(unittest.defaultTestLoader.loadTestsFromTestCase(Scenario), "behavioral-remainder", plan())
        self.assertFalse(payload["successful"])
        self.assertEqual(0, payload["test_count"])
        self.assertEqual("error", payload["tests"][0]["outcome"])
        self.assertIn("fixture unavailable", payload["problems"][0]["detail"])

    def test_error_after_a_failed_checkpoint_retains_both_diagnostics(self):
        class Scenario(unittest.TestCase):
            def runTest(self):
                with self.subTest(checkpoint="first"):
                    self.fail("checkpoint failure")
                raise ValueError("body failure after checkpoint")
        payload = receipt(unittest.TestSuite([Scenario()]), "behavioral-remainder", plan())
        self.assertEqual(["checkpoint failure", "body failure after checkpoint"],
                         [p["detail"] for p in payload["problems"]])


class ExecutionReuseTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.case = scenarios(self.events)
        self.p = plan()

    def suites(self):
        return (unittest.defaultTestLoader.loadTestsFromTestCase(self.case),
                unittest.TestSuite([self.case("test_measured")]))

    def receipts(self, p=None):
        p = p or self.p
        behavioral, measured = self.suites()
        remainder = runner._remainder(behavioral, measured)
        return (receipt(remainder, "behavioral-remainder", p),
                receipt(measured, "coverage-quality" if "repository" in p["coverage_obligations"] else "impact", p))

    def test_one_execution_per_case_supplies_both_obligations(self):
        """Measured and remaining paths execute once, then receipts prove complete behavior."""
        remaining, measured = self.receipts()
        self.assertEqual(["setup", "remaining", "teardown", "setup", "measured", "teardown"], self.events)
        combined = runner._combine_behavioral(self.p, *self.suites(), remaining, measured)
        self.assertEqual(2, combined["test_count"])
        self.assertTrue(combined["successful"])
        self.assertEqual(1, combined["execution"]["reused_for_behavioral"])
        self.assertEqual(2, combined["execution"]["unique_executions"])
        self.assertEqual(1, self.events.count("measured"))
        self.assertEqual(1, self.events.count("remaining"))

    def test_empty_remainder_and_coverage_none_each_have_complete_evidence(self):
        for obligations in ([], ["impact"], ["repository"], ["impact", "repository"]):
            with self.subTest(coverage=obligations):
                p = plan(obligations)
                behavioral = unittest.defaultTestLoader.loadTestsFromTestCase(self.case)
                measured = unittest.defaultTestLoader.loadTestsFromTestCase(self.case) if obligations else unittest.TestSuite()
                remainder = receipt(runner._remainder(behavioral, measured), "behavioral-remainder", p)
                coverage = receipt(measured, "coverage-quality" if "repository" in obligations else "impact", p) if obligations else None
                behavioral = unittest.defaultTestLoader.loadTestsFromTestCase(self.case)
                measured = unittest.defaultTestLoader.loadTestsFromTestCase(self.case) if obligations else unittest.TestSuite()
                result = runner._combine_behavioral(p, behavioral, measured, remainder, coverage)
                self.assertEqual(2, result["test_count"])
                self.assertEqual(0 if obligations else 2, remainder["test_count"])

    def test_receipt_tampering_cannot_hide_missing_failed_or_wrong_head_execution(self):
        originals = self.receipts()
        mutations = {
            "old plan": lambda p: p.update(plan_id="old"),
            "old target": lambda p: p.update(target="old"),
            "wrong suite": lambda p: p.update(suite="full"),
            "wrong Python": lambda p: p.update(python_version="3.13.1"),
            "failed producer": lambda p: p.update(successful=False),
            "missing obligation": lambda p: p.update(coverage_obligations=[]),
            "missing test": lambda p: p.update(tests=[]),
            "extra test": lambda p: p["tests"].append(copy.deepcopy(p["tests"][0])),
            "wrong count": lambda p: p.update(test_count=99),
            "unknown outcome": lambda p: p["tests"][0].update(outcome="unknown"),
            "failed test": lambda p: p["tests"][0].update(outcome="failed"),
            "forged runtime ID": lambda p: p["tests"][0].update(id="alias.test_fake"),
            "wrong source identity": lambda p: p["tests"][0].update(canonical_id="wrong-source"),
            "failed checkpoint": lambda p: p["tests"][0].update(checkpoints=[{"outcome": "failed"}]),
        }
        for producer in (0, 1):
            for checkpoint, mutate in mutations.items():
                with self.subTest(producer=producer, checkpoint=checkpoint):
                    payloads = copy.deepcopy(originals)
                    mutate(payloads[producer])
                    with self.assertRaises(ValueError):
                        runner._combine_behavioral(self.p, *self.suites(), *payloads)
        altered = copy.deepcopy(originals)
        altered[1]["python_version"] = "3.11.15"
        with self.assertRaisesRegex(ValueError, "different Python"):
            runner._combine_behavioral(self.p, *self.suites(), *altered)

    def test_coverage_only_case_is_checked_without_claiming_it_in_behavioral_scope(self):
        behavioral, measured = self.suites()
        # Behavior requires one case; coverage independently requires the other.
        b = unittest.TestSuite([self.case("test_remaining")])
        rem, cov = self.receipts()
        result = runner._combine_behavioral(self.p, b, measured, rem, cov)
        self.assertEqual(1, result["test_count"])
        self.assertEqual(0, result["execution"]["reused_for_behavioral"])
        self.assertEqual(2, result["execution"]["unique_executions"])

    def test_unrequired_or_missing_coverage_receipt_cannot_be_reused(self):
        p = plan([])
        b, c = self.suites()
        rem = receipt(b, "behavioral-remainder", p)
        with self.assertRaisesRegex(ValueError, "does not authorize"):
            runner._combine_behavioral(p, self.suites()[0], unittest.TestSuite(), rem, {})
        with self.assertRaises(ValueError):
            runner._combine_behavioral(self.p, *self.suites(), self.receipts()[0], None)

    def test_alias_imports_share_execution_and_preserve_behavioral_test_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.py"
            path.write_text("import unittest\nclass Example(unittest.TestCase):\n def test_pass(self): pass\n")
            modules = []
            for name in ("reuse_original", "reuse_alias"):
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                self.addCleanup(sys.modules.pop, name, None)
                spec.loader.exec_module(module)
                modules.append(module)
            with patch.object(runner, "ROOT", Path(directory)):
                b = unittest.defaultTestLoader.loadTestsFromModule(modules[0])
                c = unittest.defaultTestLoader.loadTestsFromModule(modules[1])
                rem = receipt(runner._remainder(b, c), "behavioral-remainder", self.p)
                cov = receipt(c, "impact", self.p)
                b = unittest.defaultTestLoader.loadTestsFromModule(modules[0])
                c = unittest.defaultTestLoader.loadTestsFromModule(modules[1])
                result = runner._combine_behavioral(self.p, b, c, rem, cov)
                self.assertEqual(0, rem["test_count"])
                self.assertEqual("reuse_original.Example.test_pass", result["tests"][0]["id"])


class EntryPointTests(unittest.TestCase):
    def test_partition_and_join_commands_verify_plan_and_propagate_test_failure(self):
        events = []
        case = scenarios(events)
        p = plan()
        def suites(*args):
            return unittest.defaultTestLoader.loadTestsFromTestCase(case), unittest.TestSuite([case("test_measured")])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            root = Path(directory)
            args = ["--plan", str(root / "plan.json"), "--json-output", str(root / "out.json"), "--verbosity", "0"]
            with patch.object(runner, "_verified_plan", return_value=p) as verify, patch.object(runner, "_execution_suites", side_effect=suites):
                self.assertEqual(0, runner.main(["--suite", "behavioral-remainder", *args]))
                verify.assert_called_once()
                remainder = json.loads((root / "out.json").read_bytes())
                remainder["python_version"] = "3.11.16"
                (root / "remaining.json").write_text(json.dumps(remainder))
                measured = receipt(suites()[1], "impact", p)
                (root / "coverage.json").write_text(json.dumps(measured))
                join = ["--suite", "behavioral-union", *args, "--behavior-results", str(root / "remaining.json"),
                        "--coverage-results", str(root / "coverage.json")]
                with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(root / "summary.md")}):
                    self.assertEqual(0, runner.main(join))
                self.assertEqual(2, json.loads((root / "out.json").read_bytes())["test_count"])
                with self.assertRaisesRegex(ValueError, "every producer"):
                    runner.main(["--suite", "behavioral-union", *args])
                measured["successful"] = False
                (root / "coverage.json").write_text(json.dumps(measured))
                with self.assertRaises(ValueError): runner.main(join)
                # With no coverage obligation, the command must not request an artifact.
                p["coverage_obligations"] = []
                empty_coverage = lambda *args: (suites()[0], unittest.TestSuite())
                with patch.object(runner, "_execution_suites", side_effect=empty_coverage):
                    self.assertEqual(0, runner.main(["--suite", "behavioral-remainder", *args]))
                    remaining = json.loads((root / "out.json").read_bytes())
                    remaining["python_version"] = "3.11.16"
                    (root / "remaining.json").write_text(json.dumps(remaining))
                    self.assertEqual(0, runner.main(join[:-2]))
            with self.assertRaisesRegex(ValueError, "--plan"):
                runner.main(["--suite", "behavioral-remainder", "--json-output", str(root / "out.json")])
            class Broken(unittest.TestCase):
                def runTest(self): self.fail("intentional probe")
            with patch.object(runner, "_suite_for", return_value=unittest.TestSuite([Broken()])):
                self.assertEqual(1, runner.main(["--suite", "full", "--json-output", str(root / "failed.json"), "--verbosity", "0"]))

    def test_execution_scopes_load_only_required_suites(self):
        args = argparse.Namespace(suite="behavioral-remainder", plan=Path("plan.json"))
        for scope in ("full", "focused", "none"):
            for obligations in ([], ["impact"]):
                with self.subTest(scope=scope, coverage=obligations):
                    p = plan(obligations); p["behavioral_scope"] = scope
                    with patch.object(runner, "_suite_for", side_effect=lambda args: unittest.TestSuite()) as load:
                        if scope == "none":
                            with self.assertRaises(ValueError): runner._execution_suites(args, p)
                            load.assert_not_called()
                        else:
                            runner._execution_suites(args, p)
                            self.assertEqual([scope] + (["coverage-plan"] if obligations else []),
                                             [call.args[0].suite for call in load.call_args_list])


if __name__ == "__main__":
    unittest.main()
