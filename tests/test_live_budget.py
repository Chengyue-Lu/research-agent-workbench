"""Temporary Pilot accounting, synthetic prior authority, no Key/API/Tool."""
import copy
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models.port import Usage
from research_workbench.evaluation.live_budget import PilotBudgetError, PilotReservation, PilotUsageJournal
from research_workbench.evaluation.live_preflight import VerifiedBudgetCheckpoint
from research_workbench.evaluation.live_verification import VerifiedPilotReservation
from tests.live_preflight_fixtures import LivePreflightFixture
from tests import test_live_verification as retained_fixtures

NOW = "2026-09-11T10:00:00Z"
IDENTITY = "5a1d31b4-59df-429b-8c59-cc7196d74f73"


class LiveBudgetTests(unittest.TestCase):
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
        self.inputs, self.context = self.f.live_inputs(), self.f.context()
        self.database, self.anchor = self.f.root / "pilot.sqlite", self.f.root / "pilot.anchor"
        self.now = NOW
        self.prior = VerifiedBudgetCheckpoint(self.context.budget_checkpoint_ref, 1744, 0, 10_000_000, True)
        self.options = {"inputs": self.inputs, "context": self.context, "prior_reader": lambda: self.prior,
                        "clock": lambda: self.now, "journal_identity": IDENTITY}
        self.slots = [s["attempt_id"] for b in self.f.plan["blocks"] if b["phase"] == "pilot"
                      for a in b["arms"] for s in a["attempt_slots"]]
        self.book = PilotUsageJournal.create(self.database, self.anchor, **self.options)
        self.addCleanup(self.book.close)

    def reserve(self):
        self.book.start_attempt(self.slots[0])
        return self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)

    def sent(self, handle):
        self.book.persist_send_intent(handle)
        self.book.record_http_entry(handle)

    def test_complete_frozen_slots_with_fresh_attempts_inherit_usage(self):
        for slot in self.slots:
            self.book.start_attempt(slot)
            handle = self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)
            observed = self.book.observe(attempt_id=slot, surface="provider", handle=handle)
            self.assertIs(type(observed), VerifiedPilotReservation)
            self.assertEqual(0, observed.other_held_tokens)
            self.sent(handle)
            self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
            tool = self.book.observe(attempt_id=slot, surface="tool")
            self.assertEqual(0, tool.reserved_input_tokens + tool.reserved_output_tokens)
            self.book.finish_attempt(slot)
        snapshot = self.book.snapshot()
        self.assertEqual(1744 + 7 * len(self.slots), snapshot["known_total_tokens"])
        self.assertEqual(0, snapshot["held_total_tokens"])
        self.assertTrue(snapshot["usage_complete"])
        self.assertFalse(snapshot["stopped"])
        self.assertTrue(all(a["status"] == "completed" for a in snapshot["attempts"]))
        self.book.close()
        with PilotUsageJournal.open(self.database, self.anchor, **self.options) as cold:
            self.assertEqual(snapshot, cold.snapshot())

    def test_failed_observed_response_retains_usage_and_stops_all_slots(self):
        handle = self.reserve()
        self.sent(handle)
        self.book.settle(handle, usage=Usage(5, 2), successful=False, response_received=True)
        self.book.fail_attempt(self.slots[0])
        snapshot = self.book.snapshot()
        self.assertEqual(1751, snapshot["known_total_tokens"])
        self.assertEqual(0, snapshot["held_total_tokens"])
        self.assertTrue(snapshot["stopped"])
        self.assertEqual("failed", snapshot["attempts"][0]["status"])
        self.assertTrue(all(a["status"] == "not-started" for a in snapshot["attempts"][1:]))
        with self.assertRaises(PilotBudgetError):
            self.book.start_attempt(self.slots[1])
        self.assertEqual(snapshot, self.book.snapshot())

    def test_post_response_capture_failure_and_prior_failure_do_not_erase_usage(self):
        handle = self.reserve()
        self.sent(handle)
        self.prior = replace(self.prior, usage_complete=False)
        self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        self.book.fail_attempt(self.slots[0])
        self.assertEqual(1751, self.book.snapshot()["known_total_tokens"])
        with self.assertRaises(PilotBudgetError):
            self.book.observe(attempt_id=self.slots[0], surface="tool")

    def test_unknown_and_partial_usage_keep_hold_and_never_zero_fill(self):
        for usage, known in ((None, 1744), (Usage(5, None), 1749)):
            with self.subTest(usage=usage):
                path = self.f.root / ("unknown" if usage is None else "partial")
                with PilotUsageJournal.create(path, path.with_suffix(".anchor"), **self.options) as book:
                    book.start_attempt(self.slots[0])
                    handle = book.reserve(input_upper_tokens=32, output_upper_tokens=16)
                    book.persist_send_intent(handle)
                    book.record_http_entry(handle)
                    book.settle(handle, usage=usage, successful=False, response_received=True)
                    value = book.snapshot()
                    self.assertFalse(value["usage_complete"])
                    self.assertEqual(known, value["known_total_tokens"])
                    self.assertEqual(48, value["held_total_tokens"])
                    self.assertEqual("unknown", value["calls"][0]["status"])
                    with self.assertRaises(PilotBudgetError):
                        book.reserve(input_upper_tokens=1, output_upper_tokens=1)

    def test_intent_only_uncertainty_retains_hold_without_inventing_entry(self):
        handle = self.reserve()
        self.book.persist_send_intent(handle)
        self.book.settle(handle, usage=None, successful=False, response_received=False)
        value = self.book.snapshot()
        self.assertIsNone(value["calls"][0]["entry_at"])
        self.assertIsNotNone(value["calls"][0]["intent_at"])
        self.assertEqual(48, value["held_total_tokens"])
        self.assertFalse(value["calls"][0]["response_received"])

    def test_release_before_send_stops_and_release_after_intent_is_denied(self):
        handle = self.reserve()
        self.book.reject_before_send(handle)
        self.assertEqual(0, self.book.snapshot()["held_total_tokens"])
        self.assertTrue(self.book.snapshot()["stopped"])
        with self.assertRaises(PilotBudgetError):
            self.book.persist_send_intent(handle)

    def test_handle_reuse_forgery_and_mutation_denied(self):
        handle = self.reserve()
        for forged in (replace(handle), PilotReservation(handle.ordinal, handle.attempt_id, 1, 1)):
            with self.assertRaises(PilotBudgetError):
                self.book.persist_send_intent(forged)
        self.book.persist_send_intent(handle)
        for operation in (self.book.persist_send_intent, self.book.reject_before_send):
            with self.assertRaises(PilotBudgetError):
                operation(handle)
        self.book.record_http_entry(handle)
        with self.assertRaises(PilotBudgetError):
            self.book.record_http_entry(handle)
        self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        with self.assertRaises(PilotBudgetError):
            self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        self.assertEqual(1751, self.book.snapshot()["known_total_tokens"])

    def test_two_open_instances_serialize_and_never_transfer_handle(self):
        handle = self.reserve()
        with PilotUsageJournal.open(self.database, self.anchor, **self.options) as other:
            self.assertTrue(other.snapshot()["recovery_required"])
            with self.assertRaises(PilotBudgetError):
                other.reserve(input_upper_tokens=32, output_upper_tokens=16)
            with self.assertRaises(PilotBudgetError):
                other.persist_send_intent(handle)
        self.sent(handle)
        self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        self.book.finish_attempt(self.slots[0])
        with PilotUsageJournal.open(self.database, self.anchor, **self.options) as other:
            other.start_attempt(self.slots[1])
            self.assertEqual("open", self.book.snapshot()["attempts"][1]["status"])

    def test_separate_process_cannot_reserve_or_skip_a_held_slot(self):
        self.reserve()
        script = '''
import json, sys
from research_workbench.evaluation.live_budget import PilotUsageJournal, PilotBudgetError
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.live_preflight import FrozenLiveContext, VerifiedBudgetCheckpoint
v=json.loads(sys.stdin.read())
context=FrozenLiveContext(**v['context'])
inputs=LiveEvaluationInputs(v['root'],v['schemas'],cumulative_token_ceiling=10000000)
prior=VerifiedBudgetCheckpoint(context.budget_checkpoint_ref,1744,0,10000000,True)
with PilotUsageJournal.open(v['database'],v['anchor'],inputs=inputs,context=context,
    prior_reader=lambda:prior,clock=lambda:v['now'],journal_identity=v['identity']) as book:
    for action in (lambda:book.reserve(input_upper_tokens=1,output_upper_tokens=1),
                   lambda:book.start_attempt(v['next_slot'])):
        try: action()
        except PilotBudgetError: pass
        else: raise AssertionError('held reservation not respected')
    s=book.snapshot()
    assert s['recovery_required'] and s['held_total_tokens']==48
    print(json.dumps({'known_total_tokens':s['known_total_tokens'],'held_total_tokens':s['held_total_tokens']}))
'''
        values = {"context": self.context.value(), "root": str(self.f.root),
                  "schemas": str(Path(__file__).resolve().parents[1] / "schemas"),
                  "database": str(self.database), "anchor": str(self.anchor), "now": NOW,
                  "identity": IDENTITY, "next_slot": self.slots[1]}
        child = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", script], input=json.dumps(values),
                               capture_output=True, encoding="utf-8", timeout=60)
        self.assertEqual(0, child.returncode, child.stderr)
        self.assertEqual({"known_total_tokens": 1744, "held_total_tokens": 48}, json.loads(child.stdout))

    def test_concurrent_instances_commit_only_one_reservation(self):
        self.book.start_attempt(self.slots[0])
        with PilotUsageJournal.open(self.database, self.anchor, **self.options) as other:
            gate = Barrier(2)
            def reserve(book):
                gate.wait(timeout=10)
                try:
                    return book.reserve(input_upper_tokens=32, output_upper_tokens=16)
                except PilotBudgetError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(reserve, book) for book in (self.book, other)]
                results = [future.result(timeout=20) for future in futures]
            self.assertEqual(1, sum(r is not None for r in results))
            self.assertEqual(1, len(self.book.snapshot()["calls"]))

    def test_non_durable_connection_configuration_is_denied(self):
        self.book._connection.execute("PRAGMA synchronous=OFF")
        with self.assertRaises(PilotBudgetError):
            self.book.start_attempt(self.slots[0])

    def test_reopen_keeps_unfinished_reservation_and_old_handle_is_foreign(self):
        handle = self.reserve()
        self.book.persist_send_intent(handle)
        self.book.close()
        with PilotUsageJournal.open(self.database, self.anchor, **self.options) as reopened:
            self.assertEqual(48, reopened.snapshot()["held_total_tokens"])
            self.assertTrue(reopened.snapshot()["recovery_required"])
            with self.assertRaises(PilotBudgetError):
                reopened.reject_before_send(handle)
            with self.assertRaises(PilotBudgetError):
                reopened.start_attempt(self.slots[1])

    def test_confirmatory_unknown_and_out_of_order_slots_denied_without_event(self):
        confirmatory = next(s["attempt_id"] for b in self.f.plan["blocks"] if b["phase"] == "confirmatory"
                            for a in b["arms"] for s in a["attempt_slots"])
        for slot in (confirmatory, "unknown", self.slots[1]):
            with self.assertRaises(PilotBudgetError):
                self.book.start_attempt(slot)
        self.assertEqual(0, self.book.snapshot()["events_committed"])

    def test_request_turn_and_time_bounds_deny_new_send(self):
        self.book.start_attempt(self.slots[0])
        for inputs, outputs in ((True, 16), (0, 16), (513, 16), (32, 65)):
            with self.assertRaises(PilotBudgetError):
                self.book.reserve(input_upper_tokens=inputs, output_upper_tokens=outputs)
        for _ in range(3):
            handle = self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)
            self.sent(handle)
            self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        with self.assertRaises(PilotBudgetError):
            self.book.reserve(input_upper_tokens=1, output_upper_tokens=1)
        self.now = "2026-09-11T10:02:00Z"
        with self.assertRaises(PilotBudgetError):
            self.book.observe(attempt_id=self.slots[0], surface="tool")

    def test_reported_usage_above_bound_is_retained_and_stops(self):
        handle = self.reserve()
        self.sent(handle)
        self.book.settle(handle, usage=Usage(500, 100), successful=True, response_received=True)
        value = self.book.snapshot()
        self.assertEqual(2344, value["known_total_tokens"])
        self.assertEqual(0, value["held_total_tokens"])
        self.assertTrue(value["stopped"])
        with self.assertRaises(PilotBudgetError):
            self.book.finish_attempt(self.slots[0])

    def test_late_received_response_settles_then_stops_instead_of_losing_usage(self):
        handle = self.reserve()
        self.sent(handle)
        self.now = "2026-09-11T10:02:00Z"
        self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        self.book.fail_attempt(self.slots[0])
        value = self.book.snapshot()
        self.assertEqual(1751, value["known_total_tokens"])
        self.assertTrue(value["calls"][0]["time_exhausted"])
        self.assertTrue(value["stopped"])

    def test_tool_observation_requires_settled_response_and_no_handle(self):
        handle = self.reserve()
        with self.assertRaises(PilotBudgetError):
            self.book.observe(attempt_id=self.slots[0], surface="tool")
        self.sent(handle)
        self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
        with self.assertRaises(PilotBudgetError):
            self.book.observe(attempt_id=self.slots[0], surface="tool", handle=handle)

    def test_prior_checkpoint_drift_prevents_use_but_preserves_historical_report(self):
        handle = self.reserve()
        before = self.book.snapshot()
        for prior in (replace(self.prior, usage_complete=False), replace(self.prior, held_total_tokens=1),
                      replace(self.prior, known_total_tokens=0), True):
            self.prior = prior
            with self.assertRaises(PilotBudgetError):
                self.book.persist_send_intent(handle)
            self.assertEqual(before, self.book.snapshot())

    def test_use_callback_binds_context_executor_clock_and_current_owned_handle(self):
        handle = self.reserve()
        verify = self.book.use_verifier(executor_id="fixture-executor", current_handle=lambda _: handle)
        argument = {"context": self.context.value(), "executor_id": "fixture-executor", "checked_at": NOW,
                    "slot": {"phase": "pilot", "attempt_id": self.slots[0]}, "surface": "provider"}
        self.assertEqual(handle.ordinal, verify(argument).reservation_ordinal)
        for wrong in (argument | {"executor_id": "other"}, argument | {"checked_at": "2026-09-11T10:00:01Z"},
                      argument | {"context": self.context.value() | {"run_id": "other"}}):
            with self.assertRaises(PilotBudgetError):
                verify(wrong)
        self.book.persist_send_intent(handle)
        with self.assertRaises(PilotBudgetError):
            verify(argument)

    def test_expected_identity_and_context_substitution_denied(self):
        for options in (self.options | {"journal_identity": "5a1d31b4-59df-429b-8c59-cc7196d74f74"},
                        self.options | {"context": replace(self.context, run_id="substitution")}):
            with self.assertRaises(PilotBudgetError):
                PilotUsageJournal.open(self.database, self.anchor, **options)

    def test_missing_paths_do_not_recreate_and_existing_create_does_not_overwrite(self):
        before = self.anchor.read_bytes()
        with self.assertRaises(PilotBudgetError):
            PilotUsageJournal.open(self.f.root / "missing.sqlite", self.anchor, **self.options)
        self.assertFalse((self.f.root / "missing.sqlite").exists())
        with self.assertRaises(PilotBudgetError):
            PilotUsageJournal.create(self.database, self.anchor, **self.options)
        self.assertEqual(before, self.anchor.read_bytes())

    def test_database_rollback_and_anchor_truncation_fail_cold_read(self):
        handle = self.reserve()
        with closing(sqlite3.connect(self.database)) as db:
            db.execute("DELETE FROM events WHERE seq=2")
            db.commit()
        with self.assertRaises(PilotBudgetError):
            self.book.snapshot()
        self.assertIsNotNone(handle)

    def test_anchor_truncation_and_reflective_handle_drift_fail_closed(self):
        handle = self.reserve()
        object.__setattr__(handle, "input_upper_tokens", 1)
        with self.assertRaises(PilotBudgetError):
            self.book.persist_send_intent(handle)
        self.anchor.write_bytes(self.anchor.read_bytes().splitlines(keepends=True)[0])
        with self.assertRaises(PilotBudgetError):
            self.book.snapshot()

    def test_anchor_write_failure_keeps_hold_and_does_not_publish_send_intent(self):
        handle = self.reserve()
        with patch("research_workbench.evaluation.live_budget._write", side_effect=OSError("private secret")):
            with self.assertRaises(PilotBudgetError) as raised:
                self.book.persist_send_intent(handle)
        self.assertNotIn("private secret", str(raised.exception))
        self.assertIsNone(raised.exception.__context__)
        value = self.book.snapshot()
        self.assertEqual(48, value["held_total_tokens"])
        self.assertIsNone(value["calls"][0]["intent_at"])

    def test_clock_regression_and_hostile_callback_diagnostics_are_closed(self):
        handle = self.reserve()
        self.now = "2026-09-11T09:59:59Z"
        with self.assertRaises(PilotBudgetError):
            self.book.persist_send_intent(handle)
        self.options["prior_reader"] = lambda: (_ for _ in ()).throw(PilotBudgetError("private secret"))
        with self.assertRaises(PilotBudgetError) as raised:
            PilotUsageJournal.open(self.database, self.anchor, **self.options)
        self.assertNotIn("private secret", str(raised.exception))
        self.assertIsNone(raised.exception.__context__)

    def test_snapshot_is_detached_and_contains_no_cost_or_credentials(self):
        handle = self.reserve()
        self.sent(handle)
        self.book.settle(handle, usage=Usage(5, 2, provider_reported_cost=999, currency="unavailable"),
                         successful=True, response_received=True)
        value = self.book.snapshot()
        value["calls"][0]["usage"]["input_tokens"] = 0
        self.assertEqual(1751, self.book.snapshot()["known_total_tokens"])
        raw = json.dumps(self.book.snapshot())
        self.assertNotIn("provider_reported_cost", raw)
        self.assertNotIn("currency", raw)


class LiveBudgetRetainedTests(retained_fixtures.LiveEvidenceFixture, unittest.TestCase):
    def test_actual_m6_retained_reader_supplies_prefix_without_modifying_history(self):
        before = self.budget.snapshot()
        inputs, context = self.f.live_inputs(), self.f.context()
        database, anchor = self.f.root / "actual-prefix.sqlite", self.f.root / "actual-prefix.anchor"
        with PilotUsageJournal.create(database, anchor, inputs=inputs, context=context,
                prior_reader=lambda: self.budget.checkpoint(inputs, context), clock=lambda: NOW,
                journal_identity=IDENTITY) as book:
            self.assertEqual(before["known_total_tokens"], book.snapshot()["known_total_tokens"])
            slot = next(s["attempt_id"] for b in self.f.plan["blocks"] if b["phase"] == "pilot"
                        for a in b["arms"] for s in a["attempt_slots"])
            book.start_attempt(slot)
            handle = book.reserve(input_upper_tokens=32, output_upper_tokens=16)
            self.assertEqual(1744, book.observe(attempt_id=slot, surface="provider", handle=handle).known_total_tokens)
        self.assertEqual(before, self.budget.snapshot())

    def test_shared_use_guard_consumes_actual_book_observation_then_rejects_spent_handle(self):
        # Existing shared-gate fixture: actual M6 history and Pilot Decision;
        # admission/applicability/official-window authority is explicitly fake.
        guard = retained_fixtures.LiveUseGuardTests.guard(self)
        inputs, context = self.f.live_inputs(), self.f.context()
        with PilotUsageJournal.create(self.f.root / "guard-book.sqlite", self.f.root / "guard-book.anchor",
                inputs=inputs, context=context, prior_reader=lambda: self.budget.checkpoint(inputs, context),
                clock=lambda: NOW, journal_identity=IDENTITY) as book:
            book.start_attempt(self.slot["attempt_id"])
            handle = book.reserve(input_upper_tokens=32, output_upper_tokens=16)
            guard.reservation_verifier = book.use_verifier(executor_id=self.factory.executor_id,
                                                          current_handle=lambda _: handle)
            self.assertTrue(guard.check(attempt_id=self.slot["attempt_id"], surface="provider"))
            book.persist_send_intent(handle)
            book.record_http_entry(handle)
            book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
            from research_workbench.evaluation.pins import EvaluationValidationError
            with self.assertRaises(EvaluationValidationError):
                guard.check(attempt_id=self.slot["attempt_id"], surface="provider")
            self.assertEqual(1751, book.snapshot()["known_total_tokens"])


if __name__ == "__main__":
    unittest.main()
