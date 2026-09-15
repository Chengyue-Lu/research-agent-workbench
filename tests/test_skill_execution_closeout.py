import copy
import contextlib
from dataclasses import replace
import hashlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    CloseoutPin, GenericCloseoutValidationError, SkillExecutionFactError,
    build_generic_execution_receipt, read_skill_execution_inputs,
    validate_generic_execution_receipt, validate_skill_execution_receipt,
    build_skill_execution_receipt, execute_frozen_view, ExecutionHostValidationError,
    SKILL_CLOSEOUT_CONTRACT,
)
from research_workbench.execution.skill_facts import validate_skill_consumption
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog
from research_workbench.validation.document_kinds import infer_document_kind
from tests.execution_fixtures import plain, RecordingDriver, RaisingDriver, SequenceClock
from tests.skill_closeout_fixtures import ROOT, SkillCloseoutFixture, write


class SkillExecutionCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def replay(self, fixture):
        pin = fixture.receipt()
        return validate_skill_execution_receipt(pin.path, expected_sha256=pin.sha256,
                                               project_root=self.root, schema_root=ROOT / "schemas")

    def rewrite_trace(self, fixture, mutate):
        index = load_document(fixture.trace_dir / "INDEX.yaml")
        events = [json.loads(line) for line in (fixture.trace_dir / "events.jsonl").read_text().splitlines()]
        mutate(index, events)
        path = fixture.trace_dir / "events.jsonl"
        path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8", newline="\n")
        index["event_ledger"]["sha256"] = hash_file(path)
        index["event_ledger"]["event_count"] = len(events)
        write(self.root, "closeout/trace/INDEX.yaml", index)
        fixture.refresh_validation()

    def test_completed_vertical_proof_replays_in_fresh_process(self):
        fixture = SkillCloseoutFixture(self.root)
        receipt = self.replay(fixture)
        self.assertEqual("completed", receipt.document["status"])
        self.assertEqual("action-capability-slice-only", receipt.document["completion_claim"])
        self.assertFalse(receipt.document["boundaries"]["task_completion"])
        self.assertEqual("synthetic-runtime-skill", fixture.driver.consumed_skill)
        self.assertEqual(1, fixture.driver.calls)
        self.assertEqual(1, fixture.host["actual_facts"]["provider_invocations"])
        script = """import json,sys
from research_workbench.execution import validate_skill_execution_receipt
r=validate_skill_execution_receipt(sys.argv[1],expected_sha256=sys.argv[2],project_root=sys.argv[3],schema_root=sys.argv[4])
print(json.dumps({'status':r.document['status'],'skill':r.document['actual_skill_consumption']['skill']['skill_id']}))
"""
        run = subprocess.run([sys.executable, "-I", "-c", script, str(receipt.receipt_path),
                              receipt.receipt_sha256, str(self.root), str(ROOT / "schemas")],
                             cwd=self.root, text=True, capture_output=True, check=True)
        self.assertEqual({"status": "completed", "skill": "synthetic-runtime-skill"}, json.loads(run.stdout))

    def test_failed_actual_binding_drift_remains_replay_valid(self):
        for field in ("provider", "adapter", "model", "runtime", "host"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixture = SkillCloseoutFixture(root, lifecycle="failed", drift=field)
                pin = fixture.receipt()
                receipt = validate_skill_execution_receipt(pin.path, expected_sha256=pin.sha256,
                                                           project_root=root, schema_root=ROOT / "schemas")
                self.assertEqual("failed", receipt.document["status"])
                self.assertEqual("none", receipt.document["completion_claim"])
                self.assertEqual("observed-drift-" + field, receipt.document["actual_binding"][field]["ref"])

    def test_failed_actual_supply_and_projection_are_preserved(self):
        for drift in ("supply", "projection"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixture = SkillCloseoutFixture(root, lifecycle="failed", drift=drift)
                pin = fixture.receipt()
                receipt = validate_skill_execution_receipt(pin.path, expected_sha256=pin.sha256,
                                                           project_root=root, schema_root=ROOT / "schemas")
                self.assertEqual("failed", receipt.document["status"])
                self.assertNotEqual(receipt.document["requested_skill_consumption"],
                                    receipt.document["actual_skill_consumption"])

    def test_preflight_blocked_has_no_actual_inputs_or_invocation(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle="blocked")
        receipt = self.replay(fixture)
        self.assertEqual("blocked", receipt.document["status"])
        self.assertEqual(0, fixture.driver.calls)
        self.assertNotIn("actual_skill_consumption", receipt.document)
        self.assertEqual("none", receipt.document["completion_claim"])

    def test_skill_tool_component_invocation_is_replayed(self):
        fixture = SkillCloseoutFixture(self.root, with_tool=True)
        receipt = self.replay(fixture)
        self.assertEqual("completed", receipt.document["status"])
        self.assertEqual(["synthetic-skill-tool"], fixture.host["actual_facts"]["tool_refs"])

    def test_driver_exception_is_not_receipt_eligible(self):
        fixture = SkillCloseoutFixture(self.root, exception=True)
        self.assertEqual("driver-exception", fixture.host["execution_phase"])
        with self.assertRaisesRegex(GenericCloseoutValidationError, "driver-exception"):
            fixture.build()

    def test_missing_actual_consumption_is_not_receipt_eligible(self):
        fixture = SkillCloseoutFixture(self.root, capture=False)
        self.assertFalse(fixture.host["actual_facts"]["complete"])
        with self.assertRaisesRegex(GenericCloseoutValidationError, "fact-complete"):
            fixture.build()

    def test_missing_typed_fact_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        self.rewrite_trace(fixture, lambda index, events: index["decision_refs"].pop())
        with self.assertRaisesRegex(GenericCloseoutValidationError, "exactly one"):
            fixture.build()

    def test_missing_actual_input_read_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        def mutate(index, events):
            for event in events:
                if event["event_type"] == "content-read":
                    event["payload"].pop("content_sha256")
        self.rewrite_trace(fixture, mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "hash-pinned Trace read"):
            fixture.build()

    def test_missing_fact_capture_event_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        def mutate(index, events):
            for event in events:
                if event["event_type"] == "file-revision":
                    event["payload"]["reason"] = "unrelated file"
                    event["payload"]["path"] = "closeout/unrelated.yaml"
        self.rewrite_trace(fixture, mutate)
        with self.assertRaises(GenericCloseoutValidationError):
            fixture.build()

    def test_capture_after_provider_invocation_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        def mutate(index, events):
            position = next(i for i, event in enumerate(events) if event["event_type"] == "file-revision")
            item = events.pop(position)
            events.insert(len(events) - 1, item)
            for sequence, event in enumerate(events, 1):
                event["sequence"] = sequence
        self.rewrite_trace(fixture, mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "after an execution invocation"):
            fixture.build()

    def test_host_actual_binding_cannot_replace_independent_trace_fact(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle="failed")
        fixture.host["actual_binding"]["adapter"]["ref"] = "unobserved-adapter"
        fixture.refresh_validation()
        with self.assertRaisesRegex(GenericCloseoutValidationError, "does not corroborate"):
            fixture.build()

    def test_rehashed_host_and_fact_identity_still_require_actual_input_bytes(self):
        fixture = SkillCloseoutFixture(self.root)
        # A failed lifecycle permits observed drift; it does not permit replacing
        # both report dictionaries while retaining unrelated input bytes.
        fixture.host["actual_skill_consumption"]["skill"]["skill_id"] = "invented-skill"
        def mutate(index, events):
            ref = index["decision_refs"][-1]
            path = fixture.trace_dir / ref["path"]
            fact = load_document(path)
            fact["actual_skill_consumption"]["skill"]["skill_id"] = "invented-skill"
            pin = write(self.root, path.relative_to(self.root).as_posix(), fact)
            old_hash = ref["sha256"]; ref["sha256"] = pin.sha256
            for event in events:
                if event["event_type"] == "file-revision" and event["payload"].get("new_sha256") == old_hash:
                    event["payload"]["new_sha256"] = pin.sha256
        self.rewrite_trace(fixture, mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "identity/component/pin drift"):
            fixture.build()

    def test_skill_input_reader_rejects_missing_outside_parse_and_schema_faults(self):
        fixture = SkillCloseoutFixture(self.root)
        for path, payload in (("outside/absent.yaml", None), ("../outside.yaml", None),
                              ("bundle/bad.yaml", "[unclosed"), ("bundle/bad.yaml", "{}")):
            with self.subTest(path=path, payload=payload):
                if payload is not None:
                    (self.root / path).write_text(payload, encoding="utf-8")
                pin = {"path": path, "sha256": hash_file(self.root / path) if payload is not None else "0" * 64}
                with self.assertRaises(SkillExecutionFactError):
                    read_skill_execution_inputs(self.root, pin, schema_root=ROOT / "schemas")

    def test_consumption_schema_identity_component_and_hash_drift_are_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        original = plain(fixture.host["actual_skill_consumption"])
        for key, field in (("projection_ref", "ref"), ("projection_ref", "sha256"),
                           ("skill", "skill_id"), ("skill", "skill_version"),
                           ("component", "component_ref"), ("supply_report_ref", "ref")):
            with self.subTest(key=key, field=field):
                mutated = copy.deepcopy(original)
                mutated[key][field] = "f" * 64 if field == "sha256" else "wrong-identity"
                with self.assertRaises(SkillExecutionFactError):
                    validate_skill_consumption(self.root, mutated, schema_root=ROOT / "schemas")

    def test_actual_input_bytes_are_immutable_after_read(self):
        fixture = SkillCloseoutFixture(self.root)
        observed = read_skill_execution_inputs(self.root, fixture.supply_pin, schema_root=ROOT / "schemas")
        with self.assertRaises(TypeError):
            observed.projection["release"]["skill_id"] = "mutated"
        path = self.root / "bundle/skill-projection.yaml"
        path.write_text("tampered bytes", encoding="utf-8")
        self.assertEqual("synthetic-runtime-skill", observed.projection["release"]["skill_id"])
        with self.assertRaisesRegex(SkillExecutionFactError, "hash mismatch"):
            read_skill_execution_inputs(self.root, fixture.supply_pin, schema_root=ROOT / "schemas")

    def test_validation_subject_closed_set_is_enforced(self):
        fixture = SkillCloseoutFixture(self.root)
        fixture.validation["subject_refs"].pop()
        fixture.validation_pin = write(self.root, "closeout/validation.yaml", fixture.validation)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "subjects must equal"):
            fixture.build()

    def test_artifact_corruption_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        (self.root / fixture.host["artifacts"][0]["path"]).write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(GenericCloseoutValidationError, "artifact hash"):
            fixture.build()

    def test_checker_pin_corruption_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        (self.root / "closeout/checker.py").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(GenericCloseoutValidationError, "checker source pin"):
            fixture.build()

    def test_core_closeout_does_not_silently_accept_skill_contract(self):
        fixture = SkillCloseoutFixture(self.root)
        with self.assertRaises(GenericCloseoutValidationError):
            build_generic_execution_receipt(fixture.view, fixture.bundle, host_report=fixture.host_pin,
                                            trace_index=fixture.trace_pin, validations=(fixture.validation_pin,),
                                            receipt_id="CORE-WRONG", schema_root=ROOT / "schemas")
        pin = fixture.receipt()
        with self.assertRaises(GenericCloseoutValidationError):
            validate_generic_execution_receipt(pin.path, expected_sha256=pin.sha256,
                                               bundle=fixture.bundle, schema_root=ROOT / "schemas")

    def test_receipt_recomputed_fields_cannot_be_self_reported(self):
        fixture = SkillCloseoutFixture(self.root)
        original = fixture.build()
        mutations = [lambda d: d["resolution_ref"].update(ref="wrong@r1"),
                     lambda d: d["actual_binding"]["model"].update(ref="invented"),
                     lambda d: d["requested_skill_consumption"]["skill"].update(skill_id="wrong")]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                doc = copy.deepcopy(original); mutate(doc)
                pin = write(self.root, "closeout/receipt.yaml", doc)
                with self.assertRaisesRegex(GenericCloseoutValidationError, "replay drift"):
                    validate_skill_execution_receipt(pin.path, expected_sha256=pin.sha256,
                                                       project_root=self.root, schema_root=ROOT / "schemas")

    def test_receipt_versions_and_authority_fields_fail_closed(self):
        fixture = SkillCloseoutFixture(self.root)
        original = fixture.build()
        for field, value in (("contract_version", "2.0.0"), ("skill_assignment_ref", "fake"),
                             ("human_approval", True), ("task_completion", True)):
            with self.subTest(field=field):
                mutated = copy.deepcopy(original); mutated[field] = value
                self.assertTrue(SchemaCatalog(ROOT / "schemas").validate("skill_execution_receipt", mutated))

    def test_generic_document_validation_dispatches_explicit_skill_kinds(self):
        self.assertEqual('system_evaluation_protocol',
                         infer_document_kind({'record_kind': 'system_evaluation_protocol'}))
        fixture = SkillCloseoutFixture(self.root)
        index = load_document(fixture.trace_dir / "INDEX.yaml")
        fact = load_document(fixture.trace_dir / index["decision_refs"][-1]["path"])
        cases = [(fixture.host, "skill_execution_host_report"),
                 (fixture.host["actual_skill_consumption"], "skill_execution_consumption"),
                 (fixture.build(), "skill_execution_receipt"), (fact, "skill_execution_trace_fact")]
        catalog = SchemaCatalog(ROOT / "schemas")
        for document, kind in cases:
            with self.subTest(kind=kind):
                self.assertEqual(kind, infer_document_kind(document))
                self.assertEqual([], catalog.validate(kind, document))
                invalid = copy.deepcopy(document); invalid["contract_version"] = "unpublished"
                self.assertEqual(kind, infer_document_kind(invalid))
                self.assertTrue(catalog.validate(kind, invalid))

    def test_receipt_absolute_path_and_bundle_pin_are_checked(self):
        fixture = SkillCloseoutFixture(self.root)
        pin = fixture.receipt()
        validated = validate_skill_execution_receipt(self.root / pin.path, expected_sha256=pin.sha256,
                                                     project_root=self.root, schema_root=ROOT / "schemas")
        self.assertEqual(pin.sha256, validated.receipt_sha256)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "outside project root"):
            validate_skill_execution_receipt(self.root.parent / "outside.yaml", expected_sha256=pin.sha256,
                                               project_root=self.root, schema_root=ROOT / "schemas")
        document = load_document(self.root / pin.path)
        document["runtime_bundle_ref"]["sha256"] = "0" * 64
        pin = write(self.root, pin.path, document)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "Runtime Bundle pin mismatch"):
            validate_skill_execution_receipt(pin.path, expected_sha256=pin.sha256,
                                               project_root=self.root, schema_root=ROOT / "schemas")

    def test_consumption_version_and_projection_supply_relationships_are_checked(self):
        fixture = SkillCloseoutFixture(self.root)
        consumption = plain(fixture.host["actual_skill_consumption"])
        consumption["contract_version"] = "unpublished"
        with self.assertRaisesRegex(SkillExecutionFactError, "schema-invalid"):
            validate_skill_consumption(self.root, consumption, schema_root=ROOT / "schemas")
        source = load_document(self.root / "bundle/supply.yaml")
        for mutation in ("projection-ref", "component-hash"):
            with self.subTest(mutation=mutation):
                supply = copy.deepcopy(source)
                if mutation == "projection-ref":
                    supply["supply_identity"]["skill_release_projection_ref"]["ref"] = "wrong@1.0.0"
                else:
                    supply["supply_identity"]["components"][0]["content_hash"] = "b" * 64
                pin = write(self.root, "bundle/invalid-supply.yaml", supply)
                with self.assertRaises(SkillExecutionFactError):
                    read_skill_execution_inputs(self.root, {"path": pin.path, "sha256": pin.sha256},
                                                schema_root=ROOT / "schemas")
        from tests.execution_fixtures import RuntimeBundleFixture
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); RuntimeBundleFixture()._build_bundle(root)
            with self.assertRaisesRegex(SkillExecutionFactError, "requires Skill Supply"):
                read_skill_execution_inputs(root, {"path": "bundle/supply.yaml", "sha256": hash_file(root / "bundle/supply.yaml")},
                                            schema_root=ROOT / "schemas")

    def test_skill_drift_diagnostic_must_describe_real_drift(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle="failed")
        fixture.host["diagnostic"]["code"] = "HOST-ACTUAL-SKILL-DRIFT"
        fixture.refresh_validation()
        with self.assertRaisesRegex(GenericCloseoutValidationError, "lacks actual drift"):
            fixture.build()

    def test_host_rejects_unknown_contract_and_unverifiable_consumption(self):
        fixture = SkillCloseoutFixture(self.root)
        driver = RecordingDriver(self.root, fixture.view.document['binding'],
                                 supply_ref=fixture.view.document['selected_supply_report_ref']['ref'])
        with self.assertRaisesRegex(ExecutionHostValidationError, 'unsupported'):
            execute_frozen_view(fixture.view, driver, report_id='HOST', attempt_id='ATTEMPT',
                                closeout_contract='skill-execution@unpublished')
        self.assertEqual(0, driver.calls)
        execute = driver.execute
        def corrupt(request):
            result = execute(request)
            consumption = plain(fixture.host['actual_skill_consumption'])
            consumption['contract_version'] = 'unpublished'
            return replace(result, actual_skill_consumption=consumption)
        driver.execute = corrupt
        with self.assertRaisesRegex(ExecutionHostValidationError, 'schema invalid'):
            execute_frozen_view(fixture.view, driver, report_id='HOST', attempt_id='ATTEMPT',
                                clock=SequenceClock('2026-08-26T00:00:01Z', '2026-08-26T00:00:02Z'),
                                closeout_contract=SKILL_CLOSEOUT_CONTRACT, schema_root=ROOT / 'schemas')

    def test_clock_regression_is_rejected_in_blocked_and_exception_lifecycles(self):
        fixture = SkillCloseoutFixture(self.root)
        for blocked in (True, False):
            binding = plain(fixture.view.document['binding'])
            if blocked:
                binding['model']['ref'] = 'different-model'
            driver_type = RecordingDriver if blocked else RaisingDriver
            driver = driver_type(self.root, binding, supply_ref=fixture.view.document['selected_supply_report_ref']['ref'])
            with self.subTest(blocked=blocked), self.assertRaisesRegex(ExecutionHostValidationError, 'moved backwards'):
                execute_frozen_view(fixture.view, driver, report_id='HOST', attempt_id='ATTEMPT',
                                    clock=SequenceClock('2026-08-26T00:00:02Z', '2026-08-26T00:00:01Z'),
                                    closeout_contract=SKILL_CLOSEOUT_CONTRACT, schema_root=ROOT / 'schemas')
            self.assertEqual(0 if blocked else 1, driver.calls)

    def test_receipt_rejects_bundle_from_another_project(self):
        fixture = SkillCloseoutFixture(self.root)
        view = replace(fixture.view, project_root=self.root / 'other-project')
        with self.assertRaisesRegex(GenericCloseoutValidationError, 'roots differ'):
            build_skill_execution_receipt(view, fixture.bundle, host_report=fixture.host_pin,
                                          trace_index=fixture.trace_pin, validations=(fixture.validation_pin,),
                                          receipt_id='RECEIPT', schema_root=ROOT / 'schemas')

    def test_actual_supply_scalar_cannot_diverge_from_consumed_supply(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle='failed')
        fixture.host['actual_supply_report_ref'] = 'unconsumed-supply@1.0.0'
        def mutate(index, events):
            ref = index['decision_refs'][-1]
            path = fixture.trace_dir / ref['path']
            fact = load_document(path)
            fact['actual_supply_report_ref'] = 'unconsumed-supply@1.0.0'
            pin = write(self.root, path.relative_to(self.root).as_posix(), fact)
            old_hash = ref['sha256']; ref['sha256'] = pin.sha256
            for event in events:
                if event['event_type'] == 'file-revision' and event['payload'].get('new_sha256') == old_hash:
                    event['payload']['new_sha256'] = pin.sha256
        self.rewrite_trace(fixture, mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, 'Host actual Supply differs'):
            fixture.build()

    def test_archived_candidate_pins_and_replay_are_portable(self):
        archive = ROOT / 'work/M11-007/A-20260915-002'
        proof = json.loads((archive / 'checks/vertical-proof.json').read_bytes())
        for ref in proof['source_refs']:
            content = subprocess.check_output(['git', 'show', proof['implementation_commit'] + ':' + ref['path']], cwd=ROOT)
            self.assertEqual(ref['sha256'], hashlib.sha256(content).hexdigest())
        self.assertEqual(proof['replay_script']['sha256'], hash_file(ROOT / proof['replay_script']['path']))
        for case in proof['cases']:
            with self.subTest(case=case['case']):
                for ref in case['files']:
                    self.assertEqual(ref['sha256'], hash_file(ROOT / ref['path']), ref['path'])
                output = io.StringIO()
                argv = [str(archive / 'replay.py'), str(ROOT / case['receipt']['path']),
                        case['receipt']['sha256'], str(ROOT / case['project_root'])]
                with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(output):
                    runpy.run_path(str(archive / 'replay.py'), run_name='__main__')
                self.assertEqual(case['result'], json.loads(output.getvalue()))

    def test_archived_checkers_reject_missing_outside_and_changed_subjects(self):
        archive = ROOT / 'work/M11-007/A-20260915-002'
        proof = json.loads((archive / 'checks/vertical-proof.json').read_bytes())
        for case in proof['cases']:
            with self.subTest(case=case['case']):
                root = ROOT / case['project_root']
                validation = load_document(root / 'closeout/validation.yaml')
                check = runpy.run_path(str(root / 'closeout/checker.py'))['check']
                self.assertTrue(check(root, validation['subject_refs']))
                for path, digest in [('missing.yaml', '0' * 64), ('../outside.yaml', '0' * 64),
                                     ('closeout/host.yaml', '0' * 64)]:
                    self.assertFalse(check(root, [{'path': path, 'sha256': digest}]))

    def test_same_supply_identity_does_not_hide_projection_drift_as_completed(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle="failed", drift="projection-identity")
        self.assertEqual("failed", fixture.host["status"])
        self.assertEqual("HOST-ACTUAL-SKILL-DRIFT", fixture.host["diagnostic"]["code"])
        fixture.host["status"] = "completed"
        fixture.host.pop("diagnostic")
        fixture.host.pop("re_resolution_request", None)
        def mutate(index, events):
            index["attempt_status"] = "completed"
            events[-1]["payload"]["to_status"] = "completed"
        self.rewrite_trace(fixture, mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, "differs from selected View"):
            fixture.build()


if __name__ == "__main__":
    unittest.main()
