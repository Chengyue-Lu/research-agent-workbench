"""Real cold graph comparisons and factory checks; all authority/calls synthetic."""

import copy
from dataclasses import replace
import shutil
import unittest

from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.http import UrllibTransport
from research_workbench.adapters.models.provider_binding import read_provider_binding_manifest, stage_provider_binding
from research_workbench.adapters.models.request_admission import VerifiedInputUpperBound
from research_workbench.evaluation.live_applicability import (
    LIMITATIONS, provider_applicability_candidate, read_provider_applicability_relation,
)
from research_workbench.evaluation.live_budget import PilotUsageJournal
from research_workbench.evaluation.live_preflight import VerifiedBudgetCheckpoint, validator_identity
from research_workbench.evaluation.live_transport import GuardedPilotTransport
from research_workbench.evaluation.live_verification import CurrentLiveObservation, _context_commitment
from research_workbench.evaluation.pins import EvaluationValidationError, digest
from tests import test_live_verification as live_helpers
from tests.system_evaluation_fixtures import AT


class DifferentFacadeApplicabilityTests(live_helpers.LiveQualifiedEvidenceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Use a separate complete upstream fixture for the temporary journal;
        # the report-reader fixture intentionally edits only its local argument
        # and is not a complete executable harness. Never weaken budget checks.
        journal_fixture = copy.deepcopy(self.template)
        journal_fixture.root = self.f.root / "journal-context"
        shutil.copytree(self.template.root, journal_fixture.root)
        self.pilot_book = PilotUsageJournal.create(self.f.root / "live/pilot.sqlite",
            self.f.root / "live/pilot.anchor", inputs=journal_fixture.live_inputs(), context=journal_fixture.context(),
            prior_reader=lambda: VerifiedBudgetCheckpoint(journal_fixture.context().budget_checkpoint_ref,
                1744, 0, 10_000_000, True),
            clock=lambda: "2026-09-11T10:00:00Z", journal_identity="5a1d31b4-59df-429b-8c59-cc7196d74f73")
        self.addCleanup(self.pilot_book.close)
        self.pilot_transport = GuardedPilotTransport(UrllibTransport(
            max_response_bytes=self.m6_config.to_mapping()["transport"]["max_response_bytes"]),
            self.pilot_book, lambda *_: True,
            input_upper_verifier=lambda m: VerifiedInputUpperBound(m.root, 32),
            deadline=120, clock=lambda: 0)
        unbound = build_profile_provider(self.m6_config, root=self.f.root, transport=self.pilot_transport,
                                        credential=self.credential)
        self.pilot_binding = stage_provider_binding(unbound, root=self.f.root,
                                                    destination="live/pilot-binding", source_closure=True)
        manifest = read_provider_binding_manifest(self.f.live_inputs(), self.pilot_binding)
        self.pilot_document = manifest.to_mapping()
        self.provider = build_profile_provider(self.m6_config, root=self.f.root, transport=self.pilot_transport,
            credential=self.credential, implementation_closure_ref=self.pilot_document["implementation_closure_ref"])
        self.qualified_report_ref = self.f.scope["provider_applicability_ref"]
        self.relation = provider_applicability_candidate(self.f.live_inputs(),
            qualified_report_ref=self.qualified_report_ref, pilot_binding_ref=self.pilot_binding)
        self.relation_ref = self.f.write("live/relation.json", self.relation)
        self.f.scope["provider_applicability_ref"] = self.relation_ref
        self.f.scope["provider_config_ref"] = self.pilot_document["resolved_config_ref"]
        self.f.scope_ref = self.f.write("live/relation-scope.json", self.f.scope)
        self.f.protocol["live_scope_ref"] = self.f.scope_ref
        self.f.protocol["execution_binding"]["adapter"] = {"ref": self.pilot_document["adapter_class"],
            "version": self.pilot_document["adapter_version"], "content_hash": manifest.root}
        self.f.protocol_ref = self.f.write("live/relation-protocol.json", self.f.protocol)
        self.f.plan["request"]["protocol_ref"] = self.f.protocol_ref
        self.f.plan_ref = self.f.write("live/relation-plan.json", self.f.plan)
        self.observation = CurrentLiveObservation("0" * 40, self.f.doc("live/windows.json"),
                                                  tuple(self.f.scope["source_artifact_refs"]))
        self.pins = {"task_id": "M5-008", "purpose": "live-pilot", "context": _context_commitment(self.f.context()),
            "binding_ref": self.pilot_binding, "runtime_observation_sha256": digest(self.observation.value()),
            "applicability_relation": {"ref": self.relation_ref,
                "qualified_report_ref": self.relation["qualified_report_ref"],
                "qualified_binding_ref": self.relation["qualified_binding_ref"],
                "pilot_binding_ref": self.relation["pilot_binding_ref"],
                "comparison_sha256": digest(self.relation["comparison"]), "limitations": list(LIMITATIONS)}}
        self.app_decision_ref = self.f.write("live/relation-decision.json", live_helpers.decision("fixture-provider-owner", {
            "m5_live_provider_applicability": self.pins}))
        self.factory = self.relation_factory()

    def relation_factory(self, **overrides):
        return self.make_factory(**({"binding_ref": self.pilot_binding, "provider": self.provider,
                                     "applicability_relation_ref": self.relation_ref} | overrides))

    def test_distinct_facades_cold_comparison_requires_named_human_and_no_key(self):
        before, pilot_before = self.journal.snapshot(), self.pilot_book.snapshot()
        self.assertTrue(self.factory.applicability(self.argument()))
        transmitted = self.human_calls[-1]["evidence"]
        self.assertEqual(self.relation, transmitted["relation"])
        self.assertEqual(self.m6_binding, self.relation["qualified_binding_ref"])
        self.assertNotEqual(self.m6_binding, self.relation["pilot_binding_ref"])
        self.assertNotEqual(transmitted["relation"]["comparison"]["qualified_transport"]["class"],
                            transmitted["relation"]["comparison"]["pilot_transport"]["class"])
        self.assertEqual(self.m6_report["warnings"], transmitted["report"]["warnings"])
        self.assertEqual(list(LIMITATIONS), transmitted["applicability_relation"]["limitations"])
        self.assertEqual(before, self.journal.snapshot())
        self.assertEqual(pilot_before, self.pilot_book.snapshot())
        self.assertEqual(0, self.credential.resolutions)

    def test_default_same_binding_path_cannot_decode_relation_as_report(self):
        # The unchanged M6 report reader owns the ValueError contract here;
        # real preflight wraps it through its existing safe verification port.
        with self.assertRaises(ValueError):
            self.make_factory(binding_ref=self.pilot_binding, provider=self.provider).applicability(self.argument())
        self.assertEqual([], self.human_calls)

    def test_relation_must_be_the_explicit_frozen_context_ref(self):
        with self.assertRaises(EvaluationValidationError):
            self.relation_factory(applicability_relation_ref=self.qualified_report_ref)

    def test_valid_relation_cannot_supply_human_authority(self):
        calls = []
        def reject(argument):
            calls.append(argument)
            return False
        with self.assertRaises(EvaluationValidationError):
            self.relation_factory(human_verifier=reject).applicability(self.argument())
        self.assertEqual(1, len(calls))
        self.assertEqual(self.relation, calls[0]["evidence"]["relation"])
        self.assertEqual(0, self.credential.resolutions)

    def test_old_same_binding_decision_cannot_accept_different_facade(self):
        old_pins = {k: v for k, v in self.pins.items() if k != "applicability_relation"}
        selected = self.f.write("live/old-decision.json", live_helpers.decision("fixture-provider-owner", {
            "m5_live_provider_applicability": old_pins}))
        with self.assertRaisesRegex(EvaluationValidationError, "named applicability"):
            self.relation_factory(applicability_decision_ref=selected).applicability(self.argument())
        self.assertEqual(1, len(self.human_calls))

    def test_comparison_omission_extra_approval_or_wrong_selected_binding_denied(self):
        for mutate in (lambda r: r.update(approved=True),
                       lambda r: r["comparison"]["modules"].pop(),
                       lambda r: r["limitations"].pop(),
                       lambda r: r.update(qualified_binding_ref=self.pilot_binding)):
            altered = copy.deepcopy(self.relation)
            mutate(altered)
            reference = self.f.write("live/altered-relation.json", altered)
            with self.assertRaises(EvaluationValidationError):
                read_provider_applicability_relation(self.f.live_inputs(), reference,
                                                    expected_pilot_binding_ref=self.pilot_binding)
        with self.assertRaises(EvaluationValidationError):
            read_provider_applicability_relation(self.f.live_inputs(), self.relation_ref,
                                                expected_pilot_binding_ref=self.m6_binding)

    def test_slow_human_cannot_mutate_actual_provider(self):
        def mutate(_):
            changed = replace(self.provider, resolved_config=dict(self.provider.resolved_config) | {"adapter_id": "drift"})
            object.__setattr__(self.factory, "provider", changed)
            return True
        object.__setattr__(self.factory, "human_verifier", mutate)
        with self.assertRaises(EvaluationValidationError):
            self.factory.applicability(self.argument())
        self.assertEqual(0, self.credential.resolutions)

    def test_slow_human_cannot_replace_relation_bytes(self):
        def mutate(_):
            (self.f.root / self.relation_ref["path"]).write_bytes(b'{}')
            return True
        with self.assertRaises(EvaluationValidationError):
            self.relation_factory(human_verifier=mutate).applicability(self.argument())
        self.assertEqual(0, self.credential.resolutions)

    def test_original_report_cannot_be_relabelled_as_pilot_qualification(self):
        report = copy.deepcopy(self.m6_report)
        report["binding"]["manifest_ref"] = self.pilot_binding
        report["binding"]["implementation_closure_ref"] = self.pilot_document["implementation_closure_ref"]
        reference = self.f.write("live/relabelled-report.json", report)
        with self.assertRaises((EvaluationValidationError, ValueError)):
            provider_applicability_candidate(self.f.live_inputs(), qualified_report_ref=reference,
                                            pilot_binding_ref=self.pilot_binding)

    def test_new_validator_identity_pins_relation_checker(self):
        identity = validator_identity(self.f.live_inputs())
        self.assertIn("research_workbench/evaluation/live_applicability.py", identity["sources"])
