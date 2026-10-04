"""Actual deterministic readers over synthetic evidence; no live authority/API."""
import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from research_workbench.adapters.models.conformance_budget_anchor import ConformanceBudgetAnchor
from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.conformance_ledger import ConformanceUsageLimits
from research_workbench.adapters.models.port import Usage
from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.conformance_body import ConformanceBodyPolicy
from research_workbench.adapters.models.conformance_transport import GuardedConformanceTransport
from research_workbench.adapters.models.http import UrllibTransport
from research_workbench.adapters.models.provider_binding import read_provider_binding_manifest
from research_workbench.evaluation.live_preflight import compile_live_preflight
from research_workbench.evaluation.live_verification import (
    CurrentLiveObservation, LiveEvidenceVerifiers, LiveUseGuard,
    RetainedConformanceBudget, VerifiedPilotReservation, _context_commitment,
)
from research_workbench.evaluation.pins import EvaluationValidationError, digest
from tests.live_preflight_fixtures import LivePreflightFixture, JOURNAL_POLICY, TOKEN_CEILING
from tests.system_evaluation_fixtures import AT, ROOT
from tests import test_skill_evaluation as skill_helpers
from tests import test_profile_conformance_binding as m6_helpers


def ref(path, root):
    return {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def decision(owner, metadata):
    return {"schema_version": "0.1.0", "object_type": "decision", "object_id": "FIXTURE-DECISION",
            "revision": 1, "status": "accepted", "decision": "Synthetic test authority only.",
            "scope": ["M5-008", "FIXTURE-LIVE-RUN", "fixture-candidate"], "reason_refs": [], "actor": owner, "timestamp": AT,
            "metadata": {"decision_owner": "human", **metadata}}


class LiveEvidenceFixture:
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.template = LivePreflightFixture(Path(temporary.name)).build_live()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temporary.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)
        self.database, self.anchor = self.f.root / "live/history.sqlite", self.f.root / "live/history.anchor"
        with ConformanceUsageJournal.create(self.database, anchor_path=self.anchor, **JOURNAL_POLICY) as journal:
            journal.start_attempt()
            handle = journal.reserve(input_upper_tokens=1700, output_upper_tokens=44)
            journal.persist_send_intent(handle)
            journal.record_http_entry(handle)
            journal.settle(handle, usage=Usage(1700, 44), successful=True, response_received=True)
            journal.fail_attempt()
        limits = ConformanceUsageLimits(TOKEN_CEILING)
        anchor = ConformanceBudgetAnchor.open(self.anchor, database_path=self.database,
            namespace=JOURNAL_POLICY["namespace"], limits={
                "total_token_limit": TOKEN_CEILING, "max_attempts": 3,
                "max_invocations_per_attempt": 3, "max_output_tokens_per_invocation": 256})
        self.budget = RetainedConformanceBudget(self.database, self.anchor, JOURNAL_POLICY["namespace"],
                                                anchor.identity, limits)
        self.need_ref = self.f.raw("live/need.yaml", (ROOT /
            "registry/skill-needs/evidence-conflict-synthesis-1.0.0.yaml").read_bytes())
        self.closure_ref = self.f.write("live/unused-closure.json", {"fixture-only": True})
        self.human_calls = []

        def human(value):
            self.human_calls.append(copy.deepcopy(value))
            # Only this test's independently selected Decision bytes/operation.
            return value["accountable_human"] in {"fixture-pilot-owner", "fixture-provider-owner", "fixture-skill-owner"}
        self.human = human
        self.app_decision_ref = self.f.write("live/app-decision.json", decision("fixture-provider-owner", {}))
        self.admission_pins = {"protocol_ref": self.f.protocol_ref,
            "admission_case_closure_ref": self.f.protocol["admission_case_closure_ref"],
            "candidate_binding": self.f.overlay.get("candidate_binding", {}),
            "evaluation_ref": self.f.overlay["admission_evaluation_ref"],
            "decision_ref": self.f.overlay["admission_decision_ref"],
            "accountable_human": self.f.overlay["accountable_human"],
            "release_ref": self.f.overlay["release_ref"], "lifecycle_ref": self.f.overlay["lifecycle_ref"],
            "promotion_provenance_ref": self.f.overlay["promotion_provenance_ref"]}
        commitment = _context_commitment(self.f.context())
        self.f.authorization_ref = self.f.write("live/authorization.json", decision("fixture-pilot-owner", {
            "m5_live_pilot_authorization": {"task_id": "M5-008", "purpose": "live-pilot",
                "context": commitment, "executor_id": "fixture-executor"}}))
        self.f.trusted_context = self.f.context().value()
        self.observation = CurrentLiveObservation("0" * 40, self.f.doc("live/windows.json"),
                                                  tuple(self.f.scope["source_artifact_refs"]))
        self.factory = self.make_factory()

    def make_factory(self, **overrides):
        args = dict(context=self.f.context(), admission_evidence=self.admission_pins, need_ref=self.need_ref,
            admission_closure_ref=self.closure_ref, pilot_owner="fixture-pilot-owner", executor_id="fixture-executor",
            applicability_decision_ref=self.app_decision_ref, provider_owner="fixture-provider-owner",
            binding_ref=self.f.scope["provider_config_ref"], provider=None, retained_budget=self.budget,
            human_verifier=self.human, runtime_observer=lambda _: self.observation)
        args.update(overrides)
        return LiveEvidenceVerifiers(self.f.live_inputs(), **args)

    def argument(self, **changes):
        return {"context": self.f.context().value(), "checked_at": AT, "scope": self.f.scope,
                "protocol": self.f.protocol, "plan": self.f.plan} | changes

    def prepare_admission(self):
        # The old assessor's full deterministic fixture, with synthetic measured
        # receipts/review. It supplies no actual scientific or Human acceptance.
        before = {p.relative_to(self.f.root) for p in self.f.root.rglob("*") if p.is_file()}
        evaluation = skill_helpers._live_evaluation(self.f.root)
        evaluation["admission"] = {"status": "human-decided", "outcome": "accept",
            "decision_ref": "live/skill-decision.json", "rationale": "Fixture only."}
        evaluation_ref = self.f.write("live/skill-evaluation.json", evaluation)
        evidence_files = [ref(p, self.f.root) for p in self.f.root.rglob("*")
                          if p.is_file() and p.relative_to(self.f.root) not in before]
        self.closure_ref = self.f.write("live/skill-closure.json", {"version": "1.0.0",
            "purpose": "skill-admission-evidence", "evaluation_ref": evaluation_ref, "file_refs": evidence_files})
        admission_decision = decision("fixture-skill-owner", {
            "skill_evaluation_id": evaluation["evaluation_id"], "skill_candidate_id": evaluation["candidate_id"],
            "skill_admission_outcome": "accept", "m5_skill_need_evidence": {"need_ref": self.need_ref,
                "evaluation_ref": evaluation_ref, "admission_closure_ref": self.closure_ref}})
        # Evaluation receipts precede the synthetic acceptance; no hash cycle.
        admission_decision["timestamp"] = "2026-08-13T06:04:00Z"
        decision_ref = self.f.write("live/skill-decision.json", admission_decision)
        lifecycle = self.f.doc(self.admission_pins["lifecycle_ref"]["path"])
        lifecycle["need_refs"] = ["NEED-ES-CONFLICT-SYNTHESIS"]
        lifecycle["evaluation"].update(evaluation_record_ref=evaluation_ref["path"],
            baseline_ref=evaluation["cases"][0]["arms"]["baseline"]["execution_receipt_ref"],
            trial_ref=evaluation["cases"][0]["arms"]["with_skill"]["execution_receipt_ref"],
            promotion_evidence_refs=[evaluation["cases"][0]["arms"]["with_skill"]["output_ref"]["path"]])
        lifecycle["admission"]["decision_ref"] = decision_ref["path"]
        self.admission_pins.update(evaluation_ref=evaluation_ref, decision_ref=decision_ref,
            accountable_human="fixture-skill-owner", lifecycle_ref=self.f.write("live/skill-life.json", lifecycle))
        self.factory = self.make_factory()


class LiveEvidenceTests(LiveEvidenceFixture, unittest.TestCase):
    def test_selected_anchored_journal_replay_matches_frozen_actual_fixture_usage(self):
        before = (self.database.read_bytes(), self.anchor.read_bytes())
        actual = self.factory.budget_checkpoint(self.argument())
        self.assertEqual(1744, actual.known_total_tokens)
        self.assertTrue(actual.usage_complete)
        self.assertEqual(before, (self.database.read_bytes(), self.anchor.read_bytes()))
        self.assertNotIn(str(self.f.root), repr(self.budget))

    def test_unknown_usage_held_or_missing_selected_budget_is_not_recreated(self):
        with ConformanceUsageJournal.open(self.database, anchor_path=self.anchor, **JOURNAL_POLICY) as journal:
            journal.start_attempt(repair_refreeze_confirmed=True)
            handle = journal.reserve(input_upper_tokens=10, output_upper_tokens=2)
            journal.persist_send_intent(handle)
            journal.record_http_entry(handle)
            with self.assertRaises(ValueError):
                journal.settle(handle, usage=None, successful=False, response_received=True)
        with self.assertRaisesRegex(EvaluationValidationError, "external retained budget verifier failed"):
            self.budget.snapshot()
        missing = self.f.root / "not-created.sqlite"
        with self.assertRaises(EvaluationValidationError):
            replace(self.budget, database=missing).snapshot()
        self.assertFalse(missing.exists())

    def test_identity_anchor_prefix_and_known_total_substitution_denied(self):
        with self.assertRaises(EvaluationValidationError):
            replace(self.budget, journal_identity="00000000-0000-0000-0000-000000000000").snapshot()
        altered = self.f.doc("live/checkpoint.json")
        altered["known_total_tokens"] = 1700
        self.f.scope["budget_checkpoint_ref"] = self.f.write("live/checkpoint-altered.json", altered)
        with self.assertRaises(EvaluationValidationError):
            self.budget.checkpoint(self.f.live_inputs(), self.f.context())

    def test_named_pilot_decision_is_exactly_bound_without_self_hash_cycle(self):
        self.assertTrue(self.factory.authorization(self.argument()))
        call = self.human_calls[-1]
        self.assertEqual("m5-live-pilot", call["operation"])
        self.assertNotIn("authorization_ref", call["evidence"]["context"])
        with self.assertRaises(EvaluationValidationError):
            self.make_factory(human_verifier=lambda _: "approved").authorization(self.argument())
        with self.assertRaises(EvaluationValidationError):
            self.make_factory(executor_id="different-executor").authorization(self.argument())

    def test_kernel_decision_shape_and_named_status_never_replace_external_acceptance(self):
        for name, value in (("actor", "human"), ("status", "proposed"),
                            ("timestamp", "2026-09-12T10:00:00Z")):
            document = self.f.doc("live/authorization.json")
            document[name] = value
            reference = self.f.write("live/other-decision.json", document)
            with self.assertRaises(EvaluationValidationError):
                self.make_factory(context=replace(self.f.context(), authorization_ref=reference)).authorization(
                    self.argument(context=replace(self.f.context(), authorization_ref=reference).value()))

    def test_external_context_scope_plan_and_future_time_substitutions_denied(self):
        for changes in ({"context": self.f.context().value() | {"run_id": "different"}},
                        {"scope": self.f.scope | {"scope_id": "different"}},
                        {"plan": self.f.plan | {"status": "different"}},
                        {"checked_at": "2026-09-12T10:00:00Z"}):
            with self.assertRaises(EvaluationValidationError):
                self.factory.authorization(self.argument(**changes))

    def test_factory_and_observation_preserve_independent_immutable_inputs(self):
        data = {"python": {"version": "fixture-only"}}
        item = CurrentLiveObservation("0" * 40, data, tuple(self.f.scope["source_artifact_refs"]))
        data["python"]["version"] = "changed"
        self.assertEqual("fixture-only", item.value()["windows_context"]["python"]["version"])
        self.assertEqual("1" * 40, replace(item, source_commit="1" * 40).value()["source_commit"])
        with self.assertRaises(TypeError):
            item.windows_context["python"]["version"] = "changed"
        with self.assertRaises(FrozenInstanceError):
            self.factory.context = replace(self.f.context(), run_id="changed")

    def test_actual_skill_assessor_and_full_need_then_required_named_verifier(self):
        self.prepare_admission()
        self.assertTrue(self.factory.admission(self.admission_pins))
        self.assertEqual("skill-admission", self.human_calls[-1]["operation"])
        self.assertEqual("NEED-ES-CONFLICT-SYNTHESIS", self.human_calls[-1]["evidence"]["need"]["need_ref"])
        with self.assertRaises(EvaluationValidationError):
            self.make_factory(human_verifier=lambda _: False).admission(self.admission_pins)

    def test_self_declared_legacy_fixture_admission_cannot_pass_actual_assessor(self):
        with self.assertRaises(EvaluationValidationError):
            self.factory.admission(self.admission_pins)
        self.assertEqual([], self.human_calls)

    def test_transitive_receipt_pin_omission_and_changed_nested_evidence_denied(self):
        self.prepare_admission()
        closure = self.f.doc(self.closure_ref["path"])
        closure["file_refs"] = [r for r in closure["file_refs"] if r["path"] != "baseline-context.json"]
        other = self.f.write("live/closure-incomplete.json", closure)
        with self.assertRaisesRegex(EvaluationValidationError, "omits"):
            self.make_factory(admission_closure_ref=other).admission(self.admission_pins)
        (self.f.root / "baseline-context.json").write_bytes(b"{}")
        with self.assertRaises(EvaluationValidationError):
            self.factory.admission(self.admission_pins)

    def test_nested_evidence_drift_after_human_verification_is_detected(self):
        self.prepare_admission()
        def human(_):
            path = self.f.root / "with-skill-context.json"
            path.write_bytes(path.read_bytes() + b"\n")
            return True
        with self.assertRaises(EvaluationValidationError):
            self.make_factory(human_verifier=human).admission(self.admission_pins)

    def test_port_error_diagnostics_drop_original_context_and_payload(self):
        def failed(_):
            raise RuntimeError("sensitive fixture text must be discarded")
        with self.assertRaises(EvaluationValidationError) as error:
            self.make_factory(human_verifier=failed).authorization(self.argument())
        self.assertIsNone(error.exception.__context__)
        self.assertIsNone(error.exception.__cause__)
        self.assertNotIn("sensitive", str(error.exception))


class LiveUseGuardTests(LiveEvidenceFixture, unittest.TestCase):
    def guard(self, *, reservation=None, clock=lambda: "2026-09-11T10:00:00Z", official=lambda _: True):
        self.f.trusted_context = self.f.context().value()
        verifiers = self.f.verifiers(authorization=self.factory.authorization,
            budget_checkpoint=self.factory.budget_checkpoint,
            applicability=lambda a: a["context"] == self.f.trusted_context and a["checked_at"] in
                                      {AT, "2026-09-11T10:00:00Z"})
        record = compile_live_preflight(self.f.live_inputs(), **self.f.arguments(verifiers=verifiers))
        reference = self.f.write("live/guard-preflight.json", record)
        blocks = [b for b in self.f.plan["blocks"] if b["phase"] == "pilot"]
        self.slot = {**blocks[0]["arms"][0]["attempt_slots"][0], "arm_id": blocks[0]["arms"][0]["arm_id"]}
        self.reservation = reservation or VerifiedPilotReservation(self.slot["attempt_id"], 1744, 512, 64,
            0, TOKEN_CEILING, 1, 1, 0, 0, True, 1)
        guard = LiveUseGuard(self.factory, preflight_ref=reference, checked_at=AT, clock=clock,
            official_window_verifier=official, reservation_verifier=lambda _: self.reservation)
        # Only the observer/admission ports use the explicit old synthetic test
        # authority here. Real budget and Pilot Decision readers are exercised;
        # actual M6 graph/applicability is covered by the separate graph test.
        replacement = patch.object(LiveEvidenceVerifiers, "preflight_verifiers", return_value=verifiers)
        replacement.start()
        self.addCleanup(replacement.stop)
        return guard

    def test_current_recomputation_clock_pilot_slot_and_counted_reservation(self):
        guard = self.guard()
        self.assertTrue(guard.check(attempt_id=self.slot["attempt_id"], surface="provider"))
        self.assertGreaterEqual(len(self.human_calls), 3)

    def test_send_stage_needs_current_durable_intent_and_excludes_tool(self):
        guard = self.guard()
        for stage in ("send", "other"):
            with self.assertRaises(EvaluationValidationError):
                guard.check(attempt_id=self.slot["attempt_id"], surface="provider", provider_stage=stage)
        self.reservation = replace(self.reservation, send_intent_durable=True)
        with self.assertRaises(EvaluationValidationError):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
        self.assertTrue(guard.check(attempt_id=self.slot["attempt_id"], surface="provider", provider_stage="send"))
        with self.assertRaises(EvaluationValidationError):
            guard.check(attempt_id=self.slot["attempt_id"], surface="tool", provider_stage="send")

    def test_confirmatory_unknown_slot_and_a1_tool_denied(self):
        guard = self.guard()
        for attempt in ("unknown-slot", self.f.plan["blocks"][-1]["arms"][0]["attempt_slots"][0]["attempt_id"]):
            with self.assertRaises(EvaluationValidationError):
                guard.check(attempt_id=attempt, surface="provider")
        block = next(b for b in self.f.plan["blocks"] if b["phase"] == "pilot")
        a1 = next(a for a in block["arms"] if a["arm_id"] == "plain-agent")
        with self.assertRaisesRegex(EvaluationValidationError, "A1 Tool"):
            guard.check(attempt_id=a1["attempt_slots"][0]["attempt_id"], surface="tool")

    def test_unknown_held_limit_calls_request_and_elapsed_time_denied(self):
        guard = self.guard()
        original = self.reservation
        for changes in ({"usage_complete": False}, {"other_held_tokens": 1}, {"known_total_tokens": 1743},
                        {"known_total_tokens": TOKEN_CEILING}, {"reserved_output_tokens": 65},
                        {"provider_calls": 25}, {"attempt_calls": 4}, {"attempt_elapsed_seconds": 120},
                        {"run_elapsed_seconds": 1800}, {"reserved_input_tokens": 0}, {"attempt_id": "other"},
                        {"reservation_ordinal": None}):
            self.reservation = replace(original, **changes)
            with self.assertRaises(EvaluationValidationError):
                guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
        self.reservation = {"approved": True}
        with self.assertRaises(EvaluationValidationError):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")

    def test_clock_or_official_idle_window_denial_stops(self):
        guard = self.guard(official=lambda _: "yes")
        with self.assertRaises(EvaluationValidationError):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
        guard.clock = lambda: "2026-09-11T09:59:59Z"
        with self.assertRaises(EvaluationValidationError):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
        guard.clock = lambda: "2026-09-11T12:00:00Z"
        with self.assertRaises(EvaluationValidationError):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")

    def test_reservation_contract_rejects_boolean_numbers_and_nonexplicit_completeness(self):
        for values in (("slot", True, 1, 1, 0, TOKEN_CEILING, 1, 1, 0, 0, True),
                       ("slot", 1744, 1, 1, 0, TOKEN_CEILING, 1, 1, -1, 0, True),
                       ("slot", 1744, 1, 1, 0, TOKEN_CEILING, 1, 1, 0, 0, "true")):
            with self.assertRaises(EvaluationValidationError):
                VerifiedPilotReservation(*values)
        for value in (1, "true", None):
            with self.assertRaises(EvaluationValidationError):
                VerifiedPilotReservation("slot", 1744, 1, 1, 0, TOKEN_CEILING, 1, 1, 0, 0, True, 1, value)
        with self.assertRaises(EvaluationValidationError):
            VerifiedPilotReservation("slot", 1744, 1, 1, 0, TOKEN_CEILING, 1, 1, 0, 0, True, None, True)

    def test_slow_evidence_cannot_reuse_expired_window_or_changed_reservation(self):
        clock = iter(("2026-09-11T10:00:00Z", "2026-09-11T12:00:00Z"))
        guard = self.guard(clock=lambda: next(clock))
        with self.assertRaisesRegex(EvaluationValidationError, "outside frozen Beijing evening"):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
        clock = iter(("2026-09-11T10:00:00Z", "2026-09-11T10:00:00Z"))
        guard.clock = lambda: next(clock)
        snapshots = iter((self.reservation, replace(self.reservation, reserved_input_tokens=1)))
        guard.reservation_verifier = lambda _: next(snapshots)
        with self.assertRaisesRegex(EvaluationValidationError, "reservation changed"):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")

        guard.clock = lambda: "2026-09-11T10:00:00Z"
        current = replace(self.reservation, send_intent_durable=True)
        snapshots = iter((current, replace(current, send_intent_durable=False)))
        guard.reservation_verifier = lambda _: next(snapshots)
        with self.assertRaisesRegex(EvaluationValidationError, "send stage"):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider", provider_stage="send")
        guard.clock = lambda: "2026-09-11T10:00:00Z"
        snapshots = iter((self.reservation, replace(self.reservation, reservation_ordinal=2)))
        guard.reservation_verifier = lambda _: next(snapshots)
        with self.assertRaisesRegex(EvaluationValidationError, "reservation changed"):
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")

    def test_malformed_clock_return_drops_payload_and_exception_chain(self):
        guard = self.guard(clock=lambda: "sensitive-clock-fixture")
        with self.assertRaises(EvaluationValidationError) as error:
            guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
        self.assertNotIn("sensitive", str(error.exception))
        self.assertIsNone(error.exception.__context__)
        self.assertIsNone(error.exception.__cause__)


class LiveQualifiedEvidenceFixture(LiveEvidenceFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        source = m6_helpers.ProfileConformanceBindingTests
        source.setUpClass()
        cls.addClassCleanup(source.doClassCleanups)
        helper = source()
        helper.setUp()
        try:
            with ConformanceUsageJournal.create(helper.root / "selected-usage.sqlite",
                    anchor_path=helper.root / "selected-usage.anchor", **JOURNAL_POLICY) as journal:
                cls.m6_report = helper.run_driver(journal=journal)
            cls.m6_config, cls.m6_binding = helper.config, helper.reference
            temporary = tempfile.TemporaryDirectory()
            cls.addClassCleanup(temporary.cleanup)
            cls.m6_template = Path(temporary.name)
            shutil.copytree(helper.root / "binding", cls.m6_template / "binding")
            shutil.copyfile(helper.root / "profile.json", cls.m6_template / "profile.json")
        finally:
            helper.doCleanups()

    def setUp(self):
        super().setUp()
        shutil.copytree(self.m6_template / "binding", self.f.root / "binding")
        shutil.copyfile(self.m6_template / "profile.json", self.f.root / "profile.json")
        manifest = read_provider_binding_manifest(self.f.live_inputs(), self.m6_binding)
        document = manifest.to_mapping()
        database, anchor_path = self.f.root / "live/m6-history.sqlite", self.f.root / "live/m6-history.anchor"
        with ConformanceUsageJournal.create(database, anchor_path=anchor_path, **JOURNAL_POLICY) as journal:
            journal.start_attempt()
            for _ in range(3):
                handle = journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
                journal.persist_send_intent(handle)
                journal.record_http_entry(handle)
                journal.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
            journal.finish_attempt()
            checkpoint = journal.snapshot()
        anchor = ConformanceBudgetAnchor.open(anchor_path, database_path=database,
            namespace=JOURNAL_POLICY["namespace"], limits=checkpoint["limits"])
        self.database, self.anchor = database, anchor_path
        self.budget = RetainedConformanceBudget(database, anchor_path, JOURNAL_POLICY["namespace"],
            anchor.identity, ConformanceUsageLimits(TOKEN_CEILING))
        self.f.scope["budget"]["prior_tokens"] = checkpoint["known_total_tokens"]
        self.f.scope["budget_checkpoint_ref"] = self.f.write("live/m6-checkpoint.json", checkpoint)
        self.f.scope["provider_config_ref"] = document["resolved_config_ref"]
        self.f.scope["provider_applicability_ref"] = self.f.write("live/m6-report.json", self.m6_report)
        self.f.scope_ref = self.f.write("live/app-scope.json", self.f.scope)
        self.f.protocol["live_scope_ref"] = self.f.scope_ref
        self.f.protocol["execution_binding"]["adapter"] = {"ref": document["adapter_class"],
            "version": document["adapter_version"], "content_hash": manifest.root}
        self.f.protocol["execution_binding"]["model"]["ref"] = self.m6_report["requested_model"]
        self.f.protocol_ref = self.f.write("live/app-protocol.json", self.f.protocol)
        self.f.plan["request"]["protocol_ref"] = self.f.protocol_ref
        self.f.plan_ref = self.f.write("live/app-plan.json", self.f.plan)
        self.observation = CurrentLiveObservation("0" * 40, self.f.doc("live/windows.json"),
                                                  tuple(self.f.scope["source_artifact_refs"]))
        self.app_decision_ref = self.f.write("live/app-decision.json", decision("fixture-provider-owner", {
            "m5_live_provider_applicability": {"task_id": "M5-008", "purpose": "live-pilot",
                "context": _context_commitment(self.f.context()), "binding_ref": self.m6_binding,
                "runtime_observation_sha256": digest(self.observation.value())}}))
        self.journal = ConformanceUsageJournal.open(self.database, anchor_path=self.anchor, **JOURNAL_POLICY)
        self.addCleanup(self.journal.close)
        self.credential = m6_helpers._components().SyntheticCredential()
        self.transport = GuardedConformanceTransport(UrllibTransport(
            max_response_bytes=self.m6_config.to_mapping()["transport"]["max_response_bytes"]), self.journal,
            lambda *_: True, deadline=120, clock=m6_helpers._contract_monotonic,
            body_policy=ConformanceBodyPolicy(max_output_tokens=32))
        self.provider = build_profile_provider(self.m6_config, root=self.f.root, transport=self.transport,
            credential=self.credential, implementation_closure_ref=document["implementation_closure_ref"])
        self.factory = self.make_factory(binding_ref=self.m6_binding, provider=self.provider)


class LiveApplicabilityTests(LiveQualifiedEvidenceFixture, unittest.TestCase):
    def test_actual_bound_report_and_loaded_graph_are_checked_without_key_or_send(self):
        before = self.journal.snapshot()
        self.assertTrue(self.factory.applicability(self.argument()))
        self.assertEqual(0, self.credential.resolutions)
        self.assertEqual(before, self.journal.snapshot())
        self.assertEqual("m5-provider-applicability", self.human_calls[-1]["operation"])

    def test_actual_config_drift_is_denied_before_credentials(self):
        actual = self.provider.resolved_config
        changed = replace(self.provider, resolved_config=dict(actual) | {"adapter_id": "changed"})
        factory = self.make_factory(binding_ref=self.m6_binding, provider=changed)
        with self.assertRaises(EvaluationValidationError):
            factory.applicability(self.argument())
        self.assertEqual(0, self.credential.resolutions)

    def test_valid_report_still_requires_actual_human_acceptance(self):
        with self.assertRaises(EvaluationValidationError):
            self.make_factory(binding_ref=self.m6_binding, provider=self.provider,
                              human_verifier=lambda _: False).applicability(self.argument())
        self.assertEqual(0, self.credential.resolutions)
