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
    def test_successful_scenario_summary_keeps_checkpoints_without_a_failure_section(self):
        class Scenario(unittest.TestCase):
            def runTest(self):
                with self.subTest(checkpoint="validated"):
                    self.assertTrue(True)
        result = run_suite(unittest.TestSuite([Scenario()]))
        with tempfile.TemporaryDirectory() as directory:
            output, summary = Path(directory) / "result.json", Path(directory) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}), redirect_stdout(io.StringIO()):
                runner._write_summary(output, "focused", 0.1, result, 1)
            payload = json.loads(output.read_bytes())
            self.assertTrue(payload["successful"])
            self.assertEqual("passed", payload["tests"][0]["checkpoints"][0]["outcome"])
            self.assertFalse(payload["problems"])
            self.assertNotIn("Failed scenarios", summary.read_text())

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


def ordered_receipt(behavioral, load_coverage, p):
    execution = runner.OrderedCoverageExecution(behavioral, load_coverage)
    result = run_suite(execution)
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()):
        payload = runner._write_summary(Path(directory) / "results.json", "coverage-execution", 0.1,
                                        result, 2, p, execution.contract())
    payload["python_version"] = "3.11.16"
    return execution, payload


def project(p, execution, payload):
    with patch.object(runner.platform, "python_version", return_value="3.11.16"):
        return runner._project_execution(p, execution.behavioral_inventory, execution.coverage_inventory, payload)


class ExecutionReuseTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.case = scenarios(self.events)
        self.p = plan()

    def suites(self):
        return (unittest.defaultTestLoader.loadTestsFromTestCase(self.case),
                unittest.TestSuite([self.case("test_measured")]))

    def execution(self, p=None):
        return ordered_receipt(self.suites()[0], lambda: self.suites()[1], p or self.p)

    def test_one_execution_per_case_supplies_both_obligations(self):
        """Behavior keeps its ordered fixture lifecycle and supplies coverage evidence."""
        execution, payload = self.execution()
        self.assertEqual(["setup", "measured", "remaining", "teardown"], self.events)
        behavioral, coverage = project(self.p, execution, payload)
        self.assertEqual((2, 1), (behavioral["test_count"], coverage["test_count"]))
        self.assertTrue(behavioral["successful"])
        self.assertEqual(2, behavioral["execution"]["unique_executions"])
        self.assertEqual(1, self.events.count("measured"))
        self.assertEqual(1, self.events.count("remaining"))
        self.assertEqual(payload["execution_order"], behavioral["execution_order"])

    def test_all_coverage_obligations_and_empty_behavior_preserve_exact_scope(self):
        for obligations in (["impact"], ["repository"], ["impact", "repository"]):
            for empty_behavior in (False, True):
                with self.subTest(coverage=obligations, empty_behavior=empty_behavior):
                    p = plan(obligations)
                    if empty_behavior: p["behavioral_scope"] = "none"
                    b = unittest.TestSuite() if empty_behavior else self.suites()[0]
                    execution, payload = ordered_receipt(b, lambda: self.suites()[0], p)
                    behavioral, coverage = project(p, execution, payload)
                    self.assertEqual(0 if empty_behavior else 2, behavioral["test_count"])
                    self.assertEqual(2, coverage["test_count"])
                    self.assertEqual("coverage-quality" if "repository" in obligations else "impact", coverage["suite"])

    def test_receipt_tampering_cannot_hide_missing_failed_or_wrong_head_execution(self):
        execution, original = self.execution()
        mutations = {
            "old plan": lambda p: p.update(plan_id="old"),
            "old target": lambda p: p.update(target="old"),
            "old receipt schema": lambda p: p.update(schema_version="1.1.0"),
            "wrong suite": lambda p: p.update(suite="full"),
            "legacy split receipt": lambda p: p.update(suite="behavioral-remainder"),
            "wrong Python": lambda p: p.update(python_version="3.13.1"),
            "different Python patch": lambda p: p.update(python_version="3.11.15"),
            "failed producer": lambda p: p.update(successful=False),
            "missing fixture events": lambda p: p.pop("events"),
            "reported fixture error": lambda p: p["events"].update(errors=1),
            "reported failure event": lambda p: p["events"].update(failures=1),
            "missing obligation": lambda p: p.update(coverage_obligations=[]),
            "missing test": lambda p: p.update(tests=[]),
            "extra test": lambda p: p["tests"].append(copy.deepcopy(p["tests"][0])),
            "wrong count": lambda p: p.update(test_count=99),
            "unknown outcome": lambda p: p["tests"][0].update(outcome="unknown"),
            "failed test": lambda p: p["tests"][0].update(outcome="failed"),
            "forged runtime ID": lambda p: p["tests"][0].update(id="alias.test_fake"),
            "wrong source identity": lambda p: p["tests"][0].update(canonical_id="wrong-source"),
            "failed checkpoint": lambda p: p["tests"][0].update(checkpoints=[{"outcome": "failed"}]),
            "missing order contract": lambda p: p.pop("execution"),
            "wrong contract": lambda p: p["execution"].update(contract="split-producers"),
            "reordered behavior": lambda p: p["execution"]["behavioral_order"].reverse(),
            "missing coverage identity": lambda p: p["execution"].update(coverage_order=[]),
            "missing execution order": lambda p: p.pop("execution_order"),
            "reordered execution": lambda p: p["execution_order"].reverse(),
        }
        for checkpoint, mutate in mutations.items():
            with self.subTest(checkpoint=checkpoint):
                payload = copy.deepcopy(original)
                mutate(payload)
                with self.assertRaises(ValueError): project(self.p, execution, payload)

    def test_coverage_only_case_is_checked_without_claiming_it_in_behavioral_scope(self):
        def load_coverage():
            self.events.append("load coverage")
            return self.suites()[1]
        execution, payload = ordered_receipt(unittest.TestSuite([self.case("test_remaining")]), load_coverage, self.p)
        self.assertEqual(["setup", "remaining", "teardown", "load coverage", "setup", "measured", "teardown"], self.events)
        behavioral, coverage = project(self.p, execution, payload)
        self.assertEqual(1, behavioral["test_count"])
        self.assertEqual(1, behavioral["execution"]["coverage_only"])
        self.assertEqual(2, behavioral["execution"]["unique_executions"])
        self.assertEqual(["test_remaining"], [r["id"].rsplit(".", 1)[-1] for r in behavioral["tests"]])
        self.assertFalse(set(behavioral["execution_order"]) & set(coverage["execution_order"]))

    def test_unrequired_or_missing_coverage_receipt_cannot_be_reused(self):
        execution, payload = self.execution()
        with self.assertRaisesRegex(ValueError, "does not authorize"):
            project(plan([]), execution, payload)
        with self.assertRaises(ValueError): project(self.p, execution, None)

    def test_alias_imports_share_execution_and_preserve_behavioral_test_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.py"
            path.write_text("import unittest\nevents=[]\nclass Example(unittest.TestCase):\n def test_pass(self): events.append(__name__)\n")
            modules = []
            for name in ("reuse_original", "reuse_alias"):
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                self.addCleanup(sys.modules.pop, name, None)
                spec.loader.exec_module(module)
                modules.append(module)
            with patch.object(runner, "ROOT", Path(directory)):
                execution, payload = ordered_receipt(unittest.defaultTestLoader.loadTestsFromModule(modules[0]),
                    lambda: unittest.defaultTestLoader.loadTestsFromModule(modules[1]), self.p)
                b, c = project(self.p, execution, payload)
                self.assertEqual(1, b["execution"]["unique_executions"])
                self.assertEqual(["reuse_original"], modules[0].events)
                self.assertEqual([], modules[1].events)
                self.assertEqual("reuse_original.Example.test_pass", b["tests"][0]["id"])
                self.assertEqual("reuse_alias.Example.test_pass", c["tests"][0]["id"])
                self.assertEqual(b["tests"][0]["id"], c["tests"][0]["execution_id"])


class OrderedFixtureTests(unittest.TestCase):
    def load(self, source):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "cases.py"
        path.write_text(source)
        name = "ordered_fixture_case"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        return module

    def test_class_state_split_preserves_direct_full_failure_and_fixture_order(self):
        events = []
        class Example(unittest.TestCase):
            @classmethod
            def setUpClass(cls): cls.state = 0; events.append("setup")
            @classmethod
            def tearDownClass(cls): events.append("teardown")
            def test_a_mutates(self): type(self).state = 1; events.append("a")
            def test_b_observes(self): events.append("b"); self.assertEqual(0, type(self).state)
        def b(): return unittest.defaultTestLoader.loadTestsFromTestCase(Example)
        direct = run_suite(b()); expected_events = list(events); events.clear()
        execution, payload = ordered_receipt(b(), lambda: unittest.TestSuite([Example("test_a_mutates")]), plan())
        self.assertFalse(direct.wasSuccessful())
        self.assertFalse(payload["successful"])
        self.assertEqual(expected_events, events)
        self.assertEqual(1, payload["events"]["failures"])
        with self.assertRaises(ValueError): project(plan(), execution, payload)

    def test_module_state_split_preserves_direct_full_failure_and_fixture_order(self):
        module = self.load("""import unittest
events=[]
state=0
def setUpModule():
 global state
 state=0
 events.append('module setup')
def tearDownModule(): events.append('module teardown')
class A(unittest.TestCase):
 def test_a_mutates(self):
  global state
  state=1
  events.append('a')
class B(unittest.TestCase):
 def test_b_observes(self):
  events.append('b')
  self.assertEqual(0,state)
""")
        def b(): return unittest.defaultTestLoader.loadTestsFromModule(module)
        direct = run_suite(b()); expected_events = list(module.events); module.events.clear()
        execution, payload = ordered_receipt(b(), lambda: unittest.TestSuite([module.A("test_a_mutates")]), plan())
        self.assertFalse(direct.wasSuccessful())
        self.assertFalse(payload["successful"])
        self.assertEqual(expected_events, module.events)
        self.assertEqual(1, payload["events"]["failures"])
        with self.assertRaises(ValueError): project(plan(), execution, payload)

    def test_coverage_only_case_cannot_repair_behavioral_teardown_or_run_early(self):
        module = self.load("""import unittest
events=[]
state=0
def setUpModule():
 global state
 state=0
 events.append('setup')
def tearDownModule():
 events.append('teardown')
 if state: raise ValueError('behavioral teardown failed')
class Example(unittest.TestCase):
 def test_a_mutates(self):
  global state
  state=1
  events.append('a')
 def test_b_repairs(self):
  global state
  state=0
  events.append('b')
""")
        def b(): return unittest.TestSuite([module.Example("test_a_mutates")])
        direct = run_suite(b()); expected_events = list(module.events); module.events.clear()
        def c():
            module.events.append("coverage loaded")
            return unittest.defaultTestLoader.loadTestsFromModule(module)
        execution, payload = ordered_receipt(b(), c, plan())
        self.assertFalse(direct.wasSuccessful())
        self.assertFalse(payload["successful"])
        self.assertEqual(expected_events + ["coverage loaded", "setup", "b", "teardown"], module.events)
        self.assertEqual(1, payload["events"]["errors"])
        with self.assertRaises(ValueError): project(plan(), execution, payload)


class EntryPointTests(unittest.TestCase):
    def test_ordered_execution_and_projection_commands_bind_one_receipt_and_propagate_failure(self):
        events = []; case = scenarios(events); p = plan()
        def suites(*args):
            return unittest.defaultTestLoader.loadTestsFromTestCase(case), unittest.TestSuite([case("test_measured")])
        def load(args): return suites()[1] if args.suite == "coverage-plan" else suites()[0]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
             patch.object(runner.platform, "python_version", return_value="3.11.16"):
            root = Path(directory)
            args = ["--plan", str(root / "plan.json"), "--json-output", str(root / "execution.json"), "--verbosity", "0"]
            with patch.object(runner, "_verified_plan", return_value=p) as verify, patch.object(runner, "_suite_for", side_effect=load):
                producer = ["--suite", "coverage-execution", *args, "--coverage-results", str(root / "coverage.json")]
                self.assertEqual(0, runner.main(producer)); verify.assert_called_once()
                self.assertEqual(["setup", "measured", "remaining", "teardown"], events)
                consumer = ["--suite", "behavioral-evidence", "--plan", str(root / "plan.json"),
                            "--json-output", str(root / "behavior.json"), "--execution-results", str(root / "execution.json")]
                with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(root / "summary.md")}):
                    self.assertEqual(0, runner.main(consumer))
                self.assertEqual(0, runner.main(consumer))
                self.assertEqual(["setup", "measured", "remaining", "teardown"], events)
                self.assertEqual(2, json.loads((root / "behavior.json").read_bytes())["test_count"])
                with self.assertRaisesRegex(ValueError, "ordered execution receipt"):
                    runner.main(["--suite", "behavioral-evidence", *args])
                with self.assertRaisesRegex(ValueError, "--coverage-results"):
                    runner.main(["--suite", "coverage-execution", *args])
                payload = json.loads((root / "execution.json").read_bytes()); payload["successful"] = False
                (root / "execution.json").write_text(json.dumps(payload))
                with self.assertRaises(ValueError): runner.main(consumer)
                p["coverage_obligations"] = []
                with self.assertRaisesRegex(ValueError, "coverage obligations"): runner.main(producer)
                self.assertEqual(0, runner.main(["--suite", "full", *args]))
            with self.assertRaisesRegex(ValueError, "--plan"):
                runner.main(["--suite", "coverage-execution", "--json-output", str(root / "out.json")])
            class Broken(unittest.TestCase):
                def runTest(self): self.fail("intentional probe")
            with patch.object(runner, "_verified_plan", return_value=plan()), \
                 patch.object(runner, "_suite_for", side_effect=lambda args: unittest.TestSuite([Broken()])):
                self.assertEqual(1, runner.main(producer))
                self.assertFalse(json.loads((root / "execution.json").read_bytes())["successful"])
                self.assertEqual(1, runner.main(["--suite", "full", "--json-output", str(root / "failed.json"), "--verbosity", "0"]))

    def test_execution_scopes_load_only_required_suites(self):
        args = argparse.Namespace(suite="behavioral-evidence", plan=Path("plan.json"))
        for scope in ("full", "focused", "none", "invalid"):
            for obligations in ([], ["impact"]):
                with self.subTest(scope=scope, coverage=obligations):
                    p = plan(obligations); p["behavioral_scope"] = scope
                    with patch.object(runner, "_suite_for", side_effect=lambda args: unittest.TestSuite()) as load:
                        if scope == "invalid":
                            with self.assertRaises(ValueError): runner._execution_suites(args, p)
                            load.assert_not_called()
                        else:
                            runner._execution_suites(args, p)
                            self.assertEqual(([scope] if scope != "none" else []) + (["coverage-plan"] if obligations else []),
                                             [call.args[0].suite for call in load.call_args_list])


if __name__ == "__main__":
    unittest.main()
