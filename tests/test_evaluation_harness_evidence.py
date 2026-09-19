"""Evaluation actual evidence must come from independently replayed receipts."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models import ProviderError, ProviderErrorCategory
from research_workbench.evaluation.harness_evidence import (
    compile_harness_evidence, validate_harness_evidence, validator_identity, _targets, _observation, _comparison,
)
from research_workbench.evaluation.harness_execution import execute_harness
from research_workbench.evaluation.pins import EvaluationValidationError
from research_workbench.validation.document_kinds import infer_document_kind
from tests.harness_execution_fixtures import ExecutionFixture, FixedClock, LocalDriver, LocalProvider
from tests.system_evaluation_fixtures import ROOT


class HarnessEvidenceFixture(unittest.TestCase):
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

    def compile(self, ref):
        return compile_harness_evidence(self.f.inputs(), execution_ref=ref,
            context=self.f.context, evidence_id="H4-SYNTHETIC", admission_verifier=lambda _: True)

    def validate(self, document, ref, **kwargs):
        return validate_harness_evidence(self.f.inputs(), document, expected_execution_ref=ref,
            context=self.f.context, expected_evidence_id="H4-SYNTHETIC",
            admission_verifier=lambda _: True, **kwargs)


class HarnessEvidenceTests(HarnessEvidenceFixture):
    def test_failed_actual_binding_cannot_be_replaced_with_plan(self):
        ports = self.f.ports()

        def drift(view, recorder, destination):
            driver = LocalDriver(view, recorder, destination)
            driver.observed_binding["model"]["ref"] = "observed-different-model"
            return driver

        ref = execute_harness(self.f.inputs(), context=self.f.context,
            ports=replace(ports, core_driver=drift), clock=FixedClock(), admission_verifier=lambda _: True)
        evidence = self.compile(ref)
        failed = next(row for row in evidence["slots"] if row["lifecycle"] == "post-call-failed")
        observed = failed["slices"][0]
        self.assertEqual(observed["comparison"], "differs-from-frozen")
        self.assertEqual(observed["actual"]["binding"]["model"]["ref"], "observed-different-model")
        self.assertEqual(self.validate(evidence, ref), evidence)
        observed["actual"]["binding"] = copy.deepcopy(observed["frozen"]["binding"])
        observed["comparison"] = "matches-frozen"
        with self.assertRaisesRegex(EvaluationValidationError, "actual evidence differs"):
            self.validate(evidence, ref)

    def test_blocked_receipt_and_unstarted_slices_have_no_actual_facts(self):
        ref = execute_harness(self.f.inputs(), context=self.f.context, ports=self.f.ports(lifecycle="blocked"),
            clock=FixedClock(), admission_verifier=lambda _: True)
        evidence = self.compile(ref)
        blocked = next(row for row in evidence["slots"] if row["lifecycle"] == "preflight-blocked")
        self.assertEqual(sum(d.calls for d in self.f.drivers), 0)
        self.assertEqual([s["lifecycle"] for s in blocked["slices"]], ["preflight-blocked", "not-started"])
        self.assertTrue(all(s["actual"] is None for row in evidence["slots"] for s in row["slices"]))
        self.assertIsNotNone(blocked["slices"][0]["evidence"]["diagnostic"])
        self.assertIsNone(blocked["slices"][1]["receipt_ref"])
        self.assertEqual(self.validate(evidence, ref), evidence)

    def test_baseline_preflight_blocked_retains_zero_call_receipt(self):
        providers = []

        def changed_provider():
            provider = LocalProvider()
            changed = replace(provider.capabilities(), adapter_version="2.0.0")
            provider.capabilities = lambda: changed
            providers.append(provider)
            return provider

        ports = replace(self.f.ports(), baseline_provider=changed_provider)
        ref = execute_harness(self.f.inputs(), context=self.f.context, ports=ports,
            clock=FixedClock(), admission_verifier=lambda _: True)
        evidence = self.compile(ref)
        blocked = next(row for row in evidence["slots"] if row["lifecycle"] == "preflight-blocked")
        self.assertTrue(blocked["arm_id"].startswith("plain"))
        self.assertEqual(sum(len(p.requests) for p in providers), 0)
        self.assertIsNone(blocked["slices"][0]["actual"])
        self.assertEqual(self.validate(evidence, ref), evidence)

    def test_dispatch_deadline_retains_completed_and_zero_call_blocked_slices(self):
        from datetime import timedelta
        from research_workbench.evaluation.harness_runtime import replay_slice
        clock = FixedClock()

        def delayed_replay(*args, **kwargs):
            result = replay_slice(*args, **kwargs)
            if kwargs["skill"] and kwargs["attempt_id"].endswith("-S0"):
                clock.value = (clock.now() + timedelta(seconds=120)).isoformat()
            return result

        with patch("research_workbench.evaluation.harness_execution.replay_slice", delayed_replay):
            ref = execute_harness(self.f.inputs(), context=self.f.context, ports=self.f.ports(),
                clock=clock, admission_verifier=lambda _: True)
        evidence = self.compile(ref)
        failed = next(row for row in evidence["slots"] if row["lifecycle"] == "post-call-failed")
        self.assertEqual(failed["arm_id"], "mode-candidate-skill")
        self.assertEqual([s["lifecycle"] for s in failed["slices"]], ["completed", "preflight-blocked"])
        self.assertEqual(failed["slices"][1]["evidence"]["diagnostic"]["code"], "HOST-DISPATCH-BLOCKED")
        self.assertIsNotNone(failed["slices"][0]["actual"]["skill_consumption"])
        self.assertIsNone(failed["slices"][1]["actual"])
        self.assertEqual(evidence["execution_status"], "stopped")
        self.assertEqual(self.validate(evidence, ref), evidence)

    def test_replay_valid_skill_supply_projection_drift_remains_actual(self):
        from research_workbench.execution import validate_skill_execution_receipt
        from research_workbench.evaluation.harness_runtime import plain
        from research_workbench.evaluation.pins import EvaluationInputs
        from tests.skill_closeout_fixtures import SkillCloseoutFixture

        # Exercise the accepted Skill closeout's broader allowed-read fixture.
        # H3's narrow fixture only permits its frozen Bundle input paths.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = SkillCloseoutFixture(root, lifecycle="failed", drift="projection")
            pin = fixture.receipt()
            receipt = validate_skill_execution_receipt(pin.path, expected_sha256=pin.sha256,
                project_root=root, schema_root=ROOT / "schemas").document
            lifecycle, actual, evidence = _observation(EvaluationInputs(root, ROOT / "schemas"),
                {"path": pin.path, "sha256": pin.sha256}, False)
            frozen = {"binding": plain(fixture.view.document["binding"]),
                      "supply_report_ref": plain(fixture.view.document["selected_supply_report_ref"]),
                      "skill_consumption": plain(receipt["requested_skill_consumption"]),
                      "tool_implementation_refs": []}
            self.assertEqual(lifecycle, "post-call-failed")
            self.assertNotEqual(actual["skill_consumption"], frozen["skill_consumption"])
            self.assertEqual(_comparison(frozen, actual), "differs-from-frozen")
            self.assertEqual(actual["skill_consumption"]["projection_ref"]["ref"], "observed-drift-projection@1.0.0")
            self.assertIsNotNone(evidence["host_ref"])


class HarnessEvidenceReplayTests(HarnessEvidenceFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture = cls.prototype
        cls.good_ref = execute_harness(fixture.inputs(), context=fixture.context,
            ports=fixture.ports(provider_errors=(ProviderError(ProviderErrorCategory.TRANSIENT, "synthetic transient"),)),
            clock=FixedClock(), admission_verifier=lambda _: True)
        cls.good_evidence = compile_harness_evidence(fixture.inputs(), execution_ref=cls.good_ref,
            context=fixture.context, evidence_id="H4-SYNTHETIC", admission_verifier=lambda _: True)
        # Only immutable archived inputs are cloned; ProviderError and live
        # recorder handles are not fixture state required for independent replay.
        fixture.providers, fixture.drivers = [], []

    def test_four_arms_all_slices_and_failed_retry_replay(self):
        evidence = self.validate(self.good_evidence, self.good_ref)
        self.assertEqual(infer_document_kind(evidence), "evaluation_harness_evidence")
        self.assertEqual(evidence["execution_status"], "completed")
        self.assertEqual(len(evidence["slots"]), 16)
        started = [r for r in evidence["slots"] if r["lifecycle"] != "not-started"]
        self.assertEqual(len(started), 9)
        failed_index = next(i for i, r in enumerate(started) if r["lifecycle"] == "post-call-failed")
        self.assertEqual(started[failed_index]["retry_class"], "provider-transient")
        self.assertIsNone(started[failed_index]["slices"][0]["actual"]["binding"])
        self.assertEqual(started[failed_index + 1]["slot"]["retry_index"], 1)
        self.assertEqual({r["arm_id"] for r in started},
            {"plain-agent", "plain-agent-tool", "mode-no-skill", "mode-candidate-skill"})
        for row in evidence["slots"]:
            self.assertEqual(len(row["slices"]), 1 if row["arm_id"].startswith("plain") else 2)
            for slice_ in row["slices"]:
                if slice_["lifecycle"] == "completed":
                    self.assertEqual(slice_["comparison"], "matches-frozen")
                if row["lifecycle"] == "not-started":
                    self.assertIsNone(row["journal_ref"])
                    self.assertIsNone(slice_["receipt_ref"])
                    self.assertIsNone(slice_["actual"])
        self.assertFalse(any(evidence["boundaries"].values()))

    def test_actual_projection_supply_tool_and_binding_tampering_are_rejected(self):
        def skill_row(doc):
            return next(r for r in doc["slots"] if r["arm_id"] == "mode-candidate-skill" and r["lifecycle"] == "completed")["slices"][0]

        for field in ("projection", "supply", "binding", "tool"):
            with self.subTest(field=field):
                evidence = copy.deepcopy(self.good_evidence)
                actual = skill_row(evidence)["actual"]
                if field == "projection":
                    actual["skill_consumption"]["projection_ref"]["sha256"] = "f" * 64
                elif field == "supply":
                    actual["supply_report_ref"] = "OTHER-SUPPLY@1.0.0"
                elif field == "binding":
                    actual["binding"]["model"]["ref"] = "OTHER-MODEL"
                else:
                    actual["tool_implementation_refs"].append(self.good_ref)
                with self.assertRaisesRegex(EvaluationValidationError, "actual evidence differs"):
                    self.validate(evidence, self.good_ref)

    def test_missing_failure_slice_and_case_attempt_substitution_are_rejected(self):
        mutations = (
            lambda d: d["slots"].pop(next(i for i, r in enumerate(d["slots"]) if r["lifecycle"] == "post-call-failed")),
            lambda d: next(r for r in d["slots"] if len(r["slices"]) == 2)["slices"].pop(),
            lambda d: d["slots"][0].update(case_id="another-case"),
            lambda d: d["slots"][0]["slices"][0].update(attempt_id="another-attempt"),
        )
        for mutation in mutations:
            evidence = copy.deepcopy(self.good_evidence)
            mutation(evidence)
            with self.assertRaisesRegex(EvaluationValidationError, "actual evidence differs"):
                self.validate(evidence, self.good_ref)

    def test_external_run_context_and_validator_identity_cannot_be_self_selected(self):
        for field in ("execution_ref", "context", "evidence_id", "validator", "authority"):
            evidence = copy.deepcopy(self.good_evidence)
            if field == "execution_ref":
                evidence[field]["sha256"] = "f" * 64
            elif field == "context":
                evidence[field]["expected_run_id"] = "another-run"
            elif field == "evidence_id":
                evidence[field] = "another-evidence"
            elif field == "validator":
                evidence[field]["schemas_sha256"] = "f" * 64
            else:
                evidence["boundaries"]["analysis_eligibility"] = True
            with self.assertRaises(EvaluationValidationError):
                self.validate(evidence, self.good_ref)
        with self.assertRaises(EvaluationValidationError):
            compile_harness_evidence(self.f.inputs(), execution_ref=self.good_ref, context=self.f.context,
                evidence_id="H4-SYNTHETIC", admission_verifier=lambda _: False)

    def test_retained_artifact_and_hash_consistent_omitted_h3_attempt_fail_replay(self):
        artifact = next(s["evidence"]["artifact_refs"][0] for r in self.good_evidence["slots"]
                        for s in r["slices"] if s["lifecycle"] == "completed")
        path = self.f.root / artifact["path"]
        original = path.read_bytes()
        path.write_bytes(b"substituted artifact")
        with self.assertRaises(ValueError):
            self.validate(self.good_evidence, self.good_ref)
        path.write_bytes(original)
        result = self.f.doc(self.good_ref["path"])
        result["attempt_refs"].pop()
        changed = self.f.write(self.good_ref["path"], result)
        evidence = copy.deepcopy(self.good_evidence)
        evidence["execution_ref"] = changed
        with self.assertRaisesRegex(EvaluationValidationError, "omitted or unfinished"):
            self.validate(evidence, changed)

    def test_completed_drift_is_rejected_even_if_upstream_replay_is_bypassed(self):
        # Defence at the H4 boundary: a future upstream regression must not
        # permit completed actual summaries that differ from qualification.
        import research_workbench.evaluation.harness_evidence as module
        original = module._observation

        def drift(*args):
            lifecycle, actual, evidence = original(*args)
            if actual is not None and lifecycle == "completed":
                actual["binding"]["model"]["ref"] = "observed-drift"
            return lifecycle, actual, evidence

        with patch.object(module, "_observation", drift), self.assertRaisesRegex(EvaluationValidationError, "completed Harness slice"):
            self.compile(self.good_ref)

    def test_validator_mutation_during_compilation_is_rejected(self):
        identity = validator_identity(self.f.inputs())
        changed = {**identity, "version": "changed"}
        with patch("research_workbench.evaluation.harness_evidence.validator_identity", side_effect=[identity, changed]):
            with self.assertRaisesRegex(EvaluationValidationError, "changed during compilation"):
                self.compile(self.good_ref)

    def test_a2_target_filters_qualification_to_same_task(self):
        inputs = self.f.inputs()
        preflight = self.f.doc(self.f.preflight_ref["path"])
        case = {**self.f.plan["cases"][0], "task_ref": self.good_ref}
        target = _targets(inputs, preflight, case, "plain-agent-tool", self.f.doc(self.f.protocol_ref["path"]))
        self.assertEqual(target[0]["tool_implementation_refs"], [])

    def test_fresh_process_cold_replay_forbids_execution_and_project_code(self):
        evidence_ref = self.f.write("h4-evidence.json", self.good_evidence)
        script = r'''
import json,sys
from unittest.mock import patch
from research_workbench.evaluation.harness_execution import HarnessContext
from research_workbench.evaluation.harness_evidence import validate_harness_evidence
from research_workbench.evaluation.pins import EvaluationInputs
root,schemas,evidence,execution,context=sys.argv[1:]
def audit(event,args):
    if event in {"subprocess.Popen","socket.connect"}:
        raise AssertionError("execution during cold replay")
    if event == "exec" and args[0].co_filename.replace("\\","/").startswith(root.replace("\\","/")+"/"):
        raise AssertionError("project Tool/checker execution during cold replay")
sys.addaudithook(audit)
inputs=EvaluationInputs(root,schemas)
with patch("research_workbench.evaluation.harness_execution.run_baseline_session",side_effect=AssertionError("M6 called")), patch("research_workbench.evaluation.harness_runtime.execute_frozen_view",side_effect=AssertionError("Host called")):
    result=validate_harness_evidence(inputs,inputs.read(json.loads(evidence)),expected_execution_ref=json.loads(execution),context=HarnessContext(**json.loads(context)),expected_evidence_id="H4-SYNTHETIC",admission_verifier=lambda _:True)
print(result["execution_status"])
'''
        result = subprocess.run([sys.executable, "-c", script, str(self.f.root), str(ROOT / "schemas"),
            json.dumps(evidence_ref), json.dumps(self.good_ref), json.dumps(vars(self.f.context))],
            check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "completed")


class HarnessEvidenceReplicationTests(unittest.TestCase):
    def test_stopped_run_retains_distinct_pilot_and_confirmatory_replicates(self):
        class ReplicatedFixture(ExecutionFixture):
            def build_harness(self, **kwargs):
                return super().build_harness(**{**kwargs, "compact": False})

        with tempfile.TemporaryDirectory() as directory:
            fixture = ReplicatedFixture(Path(directory)).build_execution()

            def blocked_provider():
                provider = LocalProvider()
                changed = replace(provider.capabilities(), adapter_version="2.0.0")
                provider.capabilities = lambda: changed
                return provider

            ref = execute_harness(fixture.inputs(), context=fixture.context,
                ports=replace(fixture.ports(lifecycle="blocked"), baseline_provider=blocked_provider),
                clock=FixedClock(), admission_verifier=lambda _: True)
            evidence = compile_harness_evidence(fixture.inputs(), execution_ref=ref, context=fixture.context,
                evidence_id="REPLICATED", admission_verifier=lambda _: True)
            self.assertEqual(evidence["execution_status"], "stopped")
            self.assertEqual(len(evidence["slots"]), 64)
            self.assertEqual(len({r["slot"]["attempt_id"] for r in evidence["slots"]}), 64)
            self.assertEqual({r["phase"] for r in evidence["slots"]}, {"pilot", "confirmatory"})
            self.assertEqual({r["replicate"] for r in evidence["slots"]}, {1, 2, 3})
            self.assertEqual(sum(r["lifecycle"] == "not-started" for r in evidence["slots"]), 63)
            self.assertEqual(infer_document_kind(evidence), "evaluation_harness_evidence")
            self.assertEqual(validate_harness_evidence(fixture.inputs(), evidence, expected_execution_ref=ref,
                context=fixture.context, expected_evidence_id="REPLICATED", admission_verifier=lambda _: True), evidence)


if __name__ == "__main__":
    unittest.main()
