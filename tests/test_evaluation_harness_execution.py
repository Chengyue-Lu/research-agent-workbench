"""Four-arm execution, append-only failure retention and provider-free replay."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models import ProviderError, ProviderErrorCategory
from research_workbench.evaluation.harness_execution import (
    execute_harness, replay_harness, _archive, _destination, _slices, _can_retry,
)
from research_workbench.evaluation.pins import EvaluationValidationError
from research_workbench.execution import GenericCloseoutValidationError
from research_workbench.validation.document_kinds import infer_document_kind
from tests.harness_execution_fixtures import ExecutionFixture, FixedClock, LocalDriver, LocalProvider
from tests.system_evaluation_fixtures import AT


class HarnessExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = tempfile.TemporaryDirectory()
        cls.addClassCleanup(source.cleanup)
        cls.prototype = ExecutionFixture(Path(source.name)).build_execution()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.f = copy.deepcopy(self.prototype)
        self.f.root = Path(directory.name)
        shutil.copytree(self.prototype.root, self.f.root, dirs_exist_ok=True)

    def execute(self, **options):
        return execute_harness(self.f.inputs(), context=self.f.context, ports=self.f.ports(**options),
                               clock=FixedClock(), admission_verifier=lambda _: True)

    def replay(self, ref):
        return replay_harness(self.f.inputs(), ref, context=self.f.context, admission_verifier=lambda _: True)

    def test_four_arms_execute_all_slices_and_cold_replay(self):
        ref = self.execute()
        with patch.object(LocalProvider, "generate", side_effect=AssertionError("provider called")), \
             patch.object(LocalDriver, "execute", side_effect=AssertionError("driver called")), \
             patch("subprocess.Popen", side_effect=AssertionError("process called")):
            result = self.replay(ref)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(infer_document_kind(result), "evaluation_harness_execution")
        self.assertEqual(len(result["attempt_refs"]), 8)
        self.assertEqual(sum(len(p.requests) for p in self.f.providers), 6)
        self.assertEqual(sum(d.calls for d in self.f.drivers), 8)
        rows = [self.f.doc(r["path"]) for r in result["attempt_refs"]]
        self.assertEqual({r["arm_id"] for r in rows},
                         {"plain-agent", "plain-agent-tool", "mode-no-skill", "mode-candidate-skill"})
        self.assertEqual(len({r["slot"]["attempt_id"] for r in rows}), 8)
        for row in rows:
            self.assertEqual(len(row["receipts"]), 1 if row["arm_id"].startswith("plain") else 2)

    def test_transient_failure_retains_fresh_retry(self):
        ref = self.execute(provider_errors=(ProviderError(ProviderErrorCategory.TRANSIENT, "local transient"),))
        result = self.replay(ref)
        self.assertEqual(result["status"], "completed")
        rows = [self.f.doc(r["path"]) for r in result["attempt_refs"]]
        failed = next(i for i, r in enumerate(rows) if r["lifecycle"] == "post-call-failed")
        self.assertEqual(rows[failed]["retry_class"], "provider-transient")
        self.assertEqual(rows[failed + 1]["slot"]["retry_index"], 1)
        self.assertNotEqual(rows[failed]["slot"]["attempt_id"], rows[failed + 1]["slot"]["attempt_id"])
        self.assertEqual(len(rows), 9)
        result["attempt_refs"].pop(failed)
        changed = self.f.write(ref["path"], result)
        with self.assertRaisesRegex(EvaluationValidationError, "omitted or unfinished"):
            self.replay(changed)

    def test_nonretryable_and_exhausted_baseline_failures_stop_and_replay(self):
        errors = [ProviderError(ProviderErrorCategory.RATE_LIMIT, "local rate limit")] * 2
        ref = self.execute(provider_errors=errors)
        result = self.replay(ref)
        self.assertEqual(result["status"], "stopped")
        rows = [self.f.doc(r["path"]) for r in result["attempt_refs"]]
        self.assertEqual([r["slot"]["retry_index"] for r in rows[-2:]], [0, 1])
        self.assertEqual([r["lifecycle"] for r in rows[-2:]], ["post-call-failed"] * 2)
        self.assertFalse(_can_retry(self.f.plan, rows[-2]["slot"], "post-call-failed", None))
        self.assertFalse(_can_retry(self.f.plan, rows[-2]["slot"], "post-call-failed", "transport-interrupted"))

    def test_host_post_call_failure_is_retained_without_inferred_retry(self):
        ref = self.execute(lifecycle="failed")
        result = self.replay(ref)
        row = self.f.doc(result["attempt_refs"][-1]["path"])
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(row["lifecycle"], "post-call-failed")
        self.assertIsNone(row["retry_class"])
        self.assertEqual(len(row["receipts"]), 1)

    def test_host_preflight_blocked_makes_no_driver_call(self):
        result = self.replay(self.execute(lifecycle="blocked"))
        row = self.f.doc(result["attempt_refs"][-1]["path"])
        self.assertEqual(row["lifecycle"], "preflight-blocked")
        self.assertEqual(sum(d.calls for d in self.f.drivers), 0)

    def test_later_blocked_slice_is_an_arm_post_call_failure(self):
        result = self.replay(self.execute(later_blocked=True))
        row = self.f.doc(result["attempt_refs"][-1]["path"])
        self.assertEqual(row["lifecycle"], "post-call-failed")
        self.assertEqual([d.calls for d in self.f.drivers], [1, 0])
        self.assertEqual([self.f.doc(r["path"])["status"] for r in row["receipts"]], ["completed", "blocked"])

    def test_slices_share_the_frozen_arm_budget(self):
        result = self.replay(self.execute(turns=3))
        row = self.f.doc(result["attempt_refs"][-1]["path"])
        self.assertEqual(row["lifecycle"], "post-call-failed")
        self.assertEqual([self.f.doc(r["path"])["status"] for r in row["receipts"]], ["completed"] * 2)
        self.assertEqual(sum(d.turns for d in self.f.drivers), 6)

    def test_exhausted_arm_budget_stops_before_the_next_slice(self):
        result = self.replay(self.execute(turns=4))
        row = self.f.doc(result["attempt_refs"][-1]["path"])
        self.assertEqual(row["lifecycle"], "post-call-failed")
        self.assertEqual(len(row["receipts"]), 1)
        self.assertEqual(len(self.f.drivers), 1)

    def test_slice_gap_exhausts_deadline_for_core_and_skill_without_second_call(self):
        from research_workbench.evaluation.harness_runtime import replay_slice

        for skill, seconds in ((False, 120), (True, 121)):
            with self.subTest(skill=skill, seconds=seconds):
                if skill:
                    self.setUp()
                clock = FixedClock()

                def delayed_replay(*args, **kwargs):
                    result = replay_slice(*args, **kwargs)
                    if kwargs["skill"] == skill and kwargs["attempt_id"].endswith("-S0"):
                        clock.value = (datetime.fromisoformat(AT) + timedelta(seconds=seconds)).isoformat()
                    return result

                with patch("research_workbench.evaluation.harness_execution.replay_slice", delayed_replay):
                    ref = execute_harness(self.f.inputs(), context=self.f.context, ports=self.f.ports(),
                        clock=clock, admission_verifier=lambda _: True)
                with patch.object(LocalDriver, "execute", side_effect=AssertionError("driver called")), \
                     patch.object(LocalProvider, "generate", side_effect=AssertionError("provider called")):
                    result = self.replay(ref)
                row = self.f.doc(result["attempt_refs"][-1]["path"])
                self.assertEqual(result["status"], "stopped")
                self.assertEqual(row["arm_id"], "mode-candidate-skill" if skill else "mode-no-skill")
                self.assertEqual(row["lifecycle"], "post-call-failed")
                self.assertEqual([d.calls for d in self.f.drivers if d.skill == skill], [1, 0])
                receipts = [self.f.doc(r["path"]) for r in row["receipts"]]
                self.assertEqual([r["status"] for r in receipts], ["completed", "blocked"])
                host = self.f.doc(receipts[-1]["host_report_ref"]["path"])
                self.assertEqual(host["diagnostic"]["code"], "HOST-DISPATCH-BLOCKED")
                self.assertEqual(host["actual_facts"]["provider_invocations"], 0)
                self.assertIsNone(row["retry_class"])

    def test_host_preparation_time_is_checked_at_actual_driver_dispatch(self):
        from research_workbench.execution.host import load_runtime_bundle

        clock, loads = FixedClock(), []

        def delayed_load(*args, **kwargs):
            bundle = load_runtime_bundle(*args, **kwargs)
            loads.append(bundle)
            if len(loads) == 2:
                clock.value = (datetime.fromisoformat(AT) + timedelta(seconds=121)).isoformat()
            return bundle

        with patch("research_workbench.execution.host.load_runtime_bundle", delayed_load):
            ref = execute_harness(self.f.inputs(), context=self.f.context, ports=self.f.ports(),
                clock=clock, admission_verifier=lambda _: True)
        result = self.replay(ref)
        self.assertEqual(result["status"], "stopped")
        self.assertEqual([d.calls for d in self.f.drivers], [1, 0])
        row = self.f.doc(result["attempt_refs"][0]["path"])
        host = self.f.doc(self.f.doc(row["receipts"][-1]["path"])["host_report_ref"]["path"])
        self.assertEqual(datetime.fromisoformat(host["started_at"].replace("Z", "+00:00")), datetime.fromisoformat(AT))
        # A hash-consistent altered observation cannot justify this blocked Host.
        row["dispatch_checks"][-1]["checked_at"] = AT
        result["attempt_refs"][0] = self.f.write(result["attempt_refs"][0]["path"], row)
        forged = self.f.write(ref["path"], result)
        with self.assertRaisesRegex(EvaluationValidationError, "dispatch decision"):
            self.replay(forged)

    def test_driver_exception_preserves_unfinished_journal_and_host_trace(self):
        with self.assertRaises(GenericCloseoutValidationError):
            self.execute(exception=True)
        directory = _archive(self.f.inputs(), self.f.context)
        self.assertEqual(len(list(directory.glob("*-started.json"))), 1)
        self.assertFalse((directory / "result.json").exists())
        host = next(self.f.root.glob("work/**/host.json"))
        self.assertEqual(self.f.doc(host.relative_to(self.f.root))["execution_phase"], "driver-exception")
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_outer_authority_and_clock_reject_before_dispatch(self):
        ports = self.f.ports()
        with patch.object(LocalProvider, "generate", side_effect=AssertionError("called")), \
             patch.object(LocalDriver, "execute", side_effect=AssertionError("called")):
            with self.assertRaisesRegex(EvaluationValidationError, "admission verifier"):
                execute_harness(self.f.inputs(), context=self.f.context, ports=ports,
                                clock=FixedClock(), admission_verifier=None)
            with self.assertRaisesRegex(EvaluationValidationError, "clock precedes"):
                execute_harness(self.f.inputs(), context=self.f.context, ports=ports,
                                clock=FixedClock("2020-01-01T00:00:00Z"), admission_verifier=lambda _: True)

    def test_preexisting_attempt_is_never_overwritten(self):
        block = self.f.plan["blocks"][0]
        case = next(c for c in self.f.plan["cases"] if c["case_id"] == block["case_id"])
        path = _destination(self.f.inputs(), case, block["arms"][0]["attempt_slots"][0])
        path.mkdir(parents=True)
        sentinel = path / "original.txt"
        sentinel.write_text("retained")
        with self.assertRaisesRegex(EvaluationValidationError, "already exists"):
            self.execute()
        self.assertEqual(sentinel.read_text(), "retained")

    def test_reused_driver_is_refused_before_second_call(self):
        ports = self.f.ports()
        drivers = []
        original = ports.core_driver

        def shared(*args):
            if not drivers:
                drivers.append(original(*args))
            return drivers[0]

        with self.assertRaisesRegex(EvaluationValidationError, "fresh Provider/Driver"):
            execute_harness(self.f.inputs(), context=self.f.context, ports=replace(ports, core_driver=shared),
                            clock=FixedClock(), admission_verifier=lambda _: True)
        self.assertEqual(drivers[0].calls, 1)

    def test_unsafe_task_output_and_missing_task_slice_are_rejected(self):
        case = copy.deepcopy(self.f.plan["cases"][0])
        task = self.f.doc(case["task_ref"]["path"])
        slot = self.f.plan["blocks"][0]["arms"][0]["attempt_slots"][0]
        for scope in ("../escape", "C:/escape", "work/./nested", "work/*"):
            task["write_scope"] = [scope]
            case["task_ref"] = self.f.write("harness/unsafe-task.json", task)
            with self.assertRaises(EvaluationValidationError):
                _destination(self.f.inputs(), case, slot)
        task["write_scope"] = ["outside-permission"]
        case["task_ref"] = self.f.write("harness/unsafe-task.json", task)
        with self.assertRaisesRegex(EvaluationValidationError, "write permission"):
            _destination(self.f.inputs(), case, slot)
        with self.assertRaisesRegex(EvaluationValidationError, "no qualified Task slices"):
            _slices(self.f.inputs(), self.f.doc(self.f.preflight_ref["path"]), case, "mode-no-skill")


class HarnessReplayTests(unittest.TestCase):
    setUp = HarnessExecutionTests.setUp
    execute = HarnessExecutionTests.execute
    replay = HarnessExecutionTests.replay
    # The completed archive is built once. Each adversarial replay receives its
    # own copy, so evidence mutation never changes another test's starting point.
    @classmethod
    def setUpClass(cls):
        HarnessExecutionTests.setUpClass.__func__(cls)
        cls.good_ref = execute_harness(cls.prototype.inputs(), context=cls.prototype.context,
            ports=cls.prototype.ports(), clock=FixedClock(), admission_verifier=lambda _: True)
        cls.prototype.providers, cls.prototype.drivers = [], []

    def change_entry(self, mutate, index=0):
        result = self.f.doc(self.good_ref["path"])
        ref = result["attempt_refs"][index]
        entry = self.f.doc(ref["path"])
        mutate(entry)
        result["attempt_refs"][index] = self.f.write(ref["path"], entry)
        return self.f.write(self.good_ref["path"], result)

    def test_forged_lifecycle_retry_and_outer_context_rejected(self):
        ref = self.change_entry(lambda e: e.update(lifecycle="post-call-failed", retry_class="provider-transient"))
        with self.assertRaisesRegex(EvaluationValidationError, "self-reported"):
            self.replay(ref)

    def test_completed_arm_cannot_drop_a_required_slice(self):
        ref = self.change_entry(lambda e: (e["receipts"].pop(), e["dispatch_checks"].pop()))
        with self.assertRaisesRegex(EvaluationValidationError, "omits required slices"):
            self.replay(ref)

    def test_dispatch_observation_is_required_and_bounded_by_host_times(self):
        cases = (
            (lambda e: e["dispatch_checks"].pop(), "coverage mismatch"),
            (lambda e: e["dispatch_checks"].__setitem__(0, None), "observation missing"),
            (lambda e: e["dispatch_checks"][0].update(extra=True), "fields differ"),
            (lambda e: e["dispatch_checks"][0].update(checked_at="2020-01-01T00:00:00Z"), "clock regressed"),
            (lambda e: e["dispatch_checks"][0].update(checked_at="2030-01-01T00:00:00Z"), "follows Host completion"),
        )
        original = self.f.doc(self.good_ref["path"])
        entry_ref = original["attempt_refs"][0]
        entry = self.f.doc(entry_ref["path"])
        for mutate, message in cases:
            with self.subTest(message=message):
                self.f.write(entry_ref["path"], entry)
                self.f.write(self.good_ref["path"], original)
                ref = self.change_entry(mutate)
                with self.assertRaisesRegex(EvaluationValidationError, message):
                    self.replay(ref)

    def test_attempt_identity_cannot_be_replaced(self):
        ref = self.change_entry(lambda e: e["slot"].update(attempt_id="OTHER-ATTEMPT"))
        with self.assertRaisesRegex(EvaluationValidationError, "slot/arm"):
            self.replay(ref)

    def test_dropped_attempt_and_unfinished_marker_are_rejected(self):
        result = self.f.doc(self.good_ref["path"])
        result["attempt_refs"].pop()
        ref = self.f.write(self.good_ref["path"], result)
        with self.assertRaisesRegex(EvaluationValidationError, "omitted or unfinished"):
            self.replay(ref)

    def test_runtime_output_hash_drift_is_rejected(self):
        row = self.f.doc(self.f.doc(self.good_ref["path"])["attempt_refs"][0]["path"])
        receipt = self.f.doc(row["receipts"][0]["path"])
        artifact = self.f.root / receipt["artifact_refs"][0]["path"]
        artifact.write_text("tampered output")
        with self.assertRaises(ValueError):
            self.replay(self.good_ref)

    def test_completed_run_identity_cannot_be_reused(self):
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_fresh_process_replay_forbids_ports_tools_and_checker_execution(self):
        script = r'''
import json,sys
from unittest.mock import patch
from research_workbench.evaluation.harness_execution import HarnessContext,replay_harness
from research_workbench.evaluation.pins import EvaluationInputs
root,schemas,ref,context=sys.argv[1:]
def audit(event,args):
    if event in {"subprocess.Popen","socket.connect"}:
        raise AssertionError("external execution during cold replay")
    if event == "exec":
        name=args[0].co_filename.replace("\\","/")
        if name.startswith(root.replace("\\","/")+"/"):
            raise AssertionError("project Tool/checker executed during cold replay")
sys.addaudithook(audit)
with patch("research_workbench.evaluation.harness_execution.run_baseline_session",side_effect=AssertionError("M6 called")), patch("research_workbench.evaluation.harness_runtime.execute_frozen_view",side_effect=AssertionError("Host called")):
    result=replay_harness(EvaluationInputs(root,schemas),json.loads(ref),context=HarnessContext(**json.loads(context)),admission_verifier=lambda _:True)
print(result["status"])
'''
        from tests.system_evaluation_fixtures import ROOT
        result = subprocess.run([sys.executable, "-c", script, str(self.f.root), str(ROOT / "schemas"),
                                 json.dumps(self.good_ref), json.dumps(vars(self.f.context))],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "completed")

    def test_run_status_and_outer_context_cannot_be_self_certified(self):
        result = self.f.doc(self.good_ref["path"])
        result["status"] = "stopped"
        ref = self.f.write(self.good_ref["path"], result)
        with self.assertRaisesRegex(EvaluationValidationError, "run status"):
            self.replay(ref)
        result["context"]["expected_run_id"] = "forged-run"
        ref = self.f.write(self.good_ref["path"], result)
        with self.assertRaisesRegex(EvaluationValidationError, "outer context"):
            self.replay(ref)

    def test_hash_consistent_shortened_completed_run_still_fails(self):
        result = self.f.doc(self.good_ref["path"])
        removed = result["attempt_refs"].pop()
        entry = self.f.doc(removed["path"])
        (self.f.root / removed["path"]).unlink()
        (self.f.root / entry["started_ref"]["path"]).unlink()
        ref = self.f.write(self.good_ref["path"], result)
        with self.assertRaisesRegex(EvaluationValidationError, "dropped a scheduled"):
            self.replay(ref)


if __name__ == "__main__":
    unittest.main()
