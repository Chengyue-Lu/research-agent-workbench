"""Synthetic SQLite conformance budget tests; no credential or Provider I/O."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import traceback
import unittest
from pathlib import Path
from uuid import uuid4

from research_workbench.adapters.models.conformance_journal import (
    ConformanceJournalError, ConformanceJournalReservation, ConformanceUsageJournal,
)
from research_workbench.adapters.models.port import Usage


class ConformanceJournalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "budget.sqlite"
        self.namespace = str(uuid4())
        self.instances = []

    def tearDown(self):
        for journal in self.instances:
            journal.close()
        self.directory.cleanup()

    def create(self, total=1000, **options):
        journal = ConformanceUsageJournal.create(self.path, namespace=self.namespace, total_token_limit=total, **options)
        self.instances.append(journal)
        return journal

    def reopen(self, total=1000, **options):
        journal = ConformanceUsageJournal.open(self.path, namespace=self.namespace, total_token_limit=total, **options)
        self.instances.append(journal)
        return journal

    def sent(self, journal, input_upper=20, output_upper=10):
        handle = journal.reserve(input_upper_tokens=input_upper, output_upper_tokens=output_upper)
        journal.persist_send_intent(handle)
        journal.record_http_entry(handle)
        return handle

    def known(self, journal, usage=None, successful=True):
        handle = self.sent(journal)
        journal.settle(handle, usage=usage or Usage(12, 3), successful=successful, response_received=True)
        return handle

    def test_explicit_budget_namespace_and_human_ceiling(self):
        for namespace, total in (("SYNTHETIC-PRIVATE-AUTH", 1000), (self.namespace, True),
                                 (self.namespace, 10_000_001), (self.namespace, 0)):
            with self.subTest(total=total), self.assertRaises(ConformanceJournalError):
                ConformanceUsageJournal.create(self.path, namespace=namespace, total_token_limit=total)
        self.assertFalse(self.path.exists())
        self.assertEqual(10_000_000, self.create(10_000_000).snapshot()["limits"]["total_token_limit"])

    def test_reopen_keeps_success_failure_usage_and_fresh_attempt_budget(self):
        journal = self.create(50)
        journal.start_attempt()
        self.known(journal, successful=False)
        journal.close()
        restored = self.reopen(50)
        self.assertEqual(15, restored.snapshot()["known_total_tokens"])
        with self.assertRaisesRegex(ConformanceJournalError, "fresh-refreeze"):
            restored.start_attempt()
        restored.start_attempt(repair_refreeze_confirmed=True)
        self.known(restored, usage=Usage(18, 2), successful=False)
        self.assertEqual(35, restored.snapshot()["known_total_tokens"])
        restored.close()
        third = self.reopen(50)
        third.start_attempt(repair_refreeze_confirmed=True)
        with self.assertRaisesRegex(ConformanceJournalError, "token-budget-exhausted"):
            third.reserve(input_upper_tokens=20, output_upper_tokens=10)
        result = third.snapshot()
        self.assertEqual(35, result["known_total_tokens"])
        self.assertEqual(2, result["provider_invocations"])
        self.assertEqual(["failed"] * 3, [row["status"] for row in result["attempts"]])

    def test_cost_currency_missing_or_malformed_never_blocks_valid_tokens_or_persists_values(self):
        journal = self.create()
        journal.start_attempt()
        marker = "SYNTHETIC-AUTH-CURRENCY-ONLY"
        for usage in (Usage(12, 3), Usage(12, 3, provider_reported_cost=marker, currency=marker),
                      Usage(12, 3, provider_reported_cost=float("nan"), currency=marker)):
            self.known(journal, usage=usage)
        result = journal.snapshot()
        self.assertFalse(result["blocked"])
        self.assertEqual(45, result["known_total_tokens"])
        self.assertEqual("unknown", result["cost"]["status"])
        self.assertIsNone(result["cost"]["provider_reported_cost"])
        self.assertIsNone(result["cost"]["currency"])
        self.assertNotIn(marker, json.dumps(result, allow_nan=False))
        self.assertNotIn(marker, " ".join(row[0] for row in journal._connection.execute("SELECT payload FROM events")))

    def test_cached_and_reasoning_subsets_not_added_to_total(self):
        journal = self.create()
        journal.start_attempt()
        self.known(journal, usage=Usage(12, 3, cached_input_tokens=10, reasoning_tokens=2))
        self.assertEqual((12, 3, 15), tuple(journal.snapshot()[field] for field in (
            "known_input_tokens", "known_output_tokens", "known_total_tokens")))

    def test_intent_is_durable_before_http_observation_and_reopen_does_not_release(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.persist_send_intent(handle)
        journal.close()
        restored = self.reopen()
        result = restored.snapshot()
        self.assertEqual((1, 0, 30), tuple(result[field] for field in (
            "durable_send_intents", "http_entry_observations", "unresolved_reserved_tokens")))
        self.assertTrue(result["calls"][0]["may_have_sent"])
        self.assertTrue(result["recovery_required"])
        self.assertTrue(result["blocked"])
        for operation in (lambda: restored.start_attempt(repair_refreeze_confirmed=True),
                          lambda: restored.reserve(input_upper_tokens=1, output_upper_tokens=1),
                          lambda: restored.reject_before_send(handle),
                          lambda: restored.record_http_entry(handle)):
            with self.assertRaises(ConformanceJournalError):
                operation()
        self.assertEqual(result, restored.snapshot())

    def test_unsent_reservation_also_survives_close_and_cannot_be_stolen_on_reopen(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.close()
        restored = self.reopen()
        result = restored.snapshot()
        self.assertEqual(30, result["unresolved_reserved_tokens"])
        self.assertFalse(result["calls"][0]["may_have_sent"])
        with self.assertRaisesRegex(ConformanceJournalError, "foreign-reservation"):
            restored.reject_before_send(handle)

    def test_observed_http_without_settlement_keeps_observation_and_full_hold_after_reopen(self):
        journal = self.create()
        journal.start_attempt()
        self.sent(journal)
        journal.close()
        restored = self.reopen()
        result = restored.snapshot()
        self.assertEqual(1, result["http_entry_observations"])
        self.assertEqual(30, result["unresolved_reserved_tokens"])
        self.assertTrue(result["blocked"])

    def test_real_process_exit_after_intent_survives_windows_reopen(self):
        journal = self.create()
        journal.close()
        script = (
            "import os\n"
            "from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal\n"
            f"j=ConformanceUsageJournal.open({str(self.path)!r},namespace={self.namespace!r},total_token_limit=1000)\n"
            "j.start_attempt()\n"
            "r=j.reserve(input_upper_tokens=20,output_upper_tokens=10)\n"
            "j.persist_send_intent(r)\n"
            "os._exit(0)\n"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        restored = self.reopen()
        self.assertEqual(30, restored.snapshot()["unresolved_reserved_tokens"])
        self.assertEqual(0, restored.snapshot()["http_entry_observations"])
        self.assertTrue(restored.snapshot()["recovery_required"])

    def test_unknown_tokens_commit_failure_and_survive_new_instance(self):
        journal = self.create()
        journal.start_attempt()
        handle = self.sent(journal)
        with self.assertRaisesRegex(ConformanceJournalError, "usage-unavailable"):
            journal.settle(handle, usage=None, successful=False, response_received=False)
        journal.close()
        result = self.reopen().snapshot()
        self.assertEqual(30, result["unresolved_reserved_tokens"])
        self.assertEqual(1, result["failed_invocations"])
        self.assertEqual("failed", result["attempts"][0]["status"])
        self.assertTrue(result["blocked"])

    def test_intent_only_failure_closes_without_fabricating_actual_http_entry(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.persist_send_intent(handle)
        with self.assertRaisesRegex(ConformanceJournalError, "cannot-release-send-intent"):
            journal.reject_before_send(handle)
        journal.record_uncertain_failure(handle)
        result = journal.snapshot()
        self.assertEqual(0, result["http_entry_observations"])
        self.assertEqual(30, result["unresolved_reserved_tokens"])
        self.assertEqual("failed", result["attempts"][0]["status"])
        self.assertTrue(result["calls"][0]["may_have_sent"])
        self.assertTrue(result["blocked"])

    def test_definitely_unsent_release_preserves_invocation_failure_and_zero_http_observations(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.reject_before_send(handle)
        result = journal.snapshot()
        self.assertEqual((1, 1, 0, 0), tuple(result[field] for field in (
            "provider_invocations", "failed_invocations", "http_entry_observations", "unresolved_reserved_tokens")))
        self.assertEqual("failed", result["attempts"][0]["status"])
        journal.start_attempt(repair_refreeze_confirmed=True)

    def test_namespace_and_limit_conflicts_never_reset_existing_budget(self):
        journal = self.create()
        journal.start_attempt()
        self.known(journal, successful=False)
        before = journal.snapshot()
        for namespace, total in ((str(uuid4()), 1000), (self.namespace, 999)):
            with self.assertRaisesRegex(ConformanceJournalError, "budget-binding-conflict"):
                ConformanceUsageJournal.open(self.path, namespace=namespace, total_token_limit=total)
        with self.assertRaisesRegex(ConformanceJournalError, "journal-create-refused"):
            self.create()
        self.assertEqual(before, journal.snapshot())

    def test_open_missing_never_creates_a_new_store(self):
        with self.assertRaisesRegex(ConformanceJournalError, "journal-storage-unavailable"):
            self.reopen()
        self.assertFalse(self.path.exists())

    def test_two_connections_cannot_reserve_parallel_budget(self):
        first = self.create(50)
        second = self.reopen(50)
        first.start_attempt()
        barrier = threading.Barrier(3)
        accepted, refused = [], []

        def reserve(journal):
            barrier.wait()
            try:
                accepted.append(journal.reserve(input_upper_tokens=20, output_upper_tokens=10))
            except ConformanceJournalError as error:
                refused.append(error.code)

        workers = [threading.Thread(target=reserve, args=(journal,)) for journal in (first, second)]
        for worker in workers:
            worker.start()
        barrier.wait()
        for worker in workers:
            worker.join()
        self.assertEqual(1, len(accepted))
        self.assertEqual(["reservation-admission-refused"], refused)
        self.assertEqual(1, first.snapshot()["provider_invocations"])
        self.assertEqual(30, second.snapshot()["unresolved_reserved_tokens"])

    def test_duplicate_intent_http_entry_settlement_and_forged_handle_do_not_append(self):
        journal = self.create()
        journal.start_attempt()
        handle = self.sent(journal)
        before = journal.snapshot()["events_committed"]
        for operation in (lambda: journal.persist_send_intent(handle), lambda: journal.record_http_entry(handle),
                          lambda: journal.record_http_entry(ConformanceJournalReservation(1, 1, 20, 10))):
            with self.assertRaises(ConformanceJournalError):
                operation()
        self.assertEqual(before, journal.snapshot()["events_committed"])
        journal.settle(handle, usage=Usage(12, 3), successful=True, response_received=True)
        before = journal.snapshot()
        with self.assertRaises(ConformanceJournalError):
            journal.settle(handle, usage=Usage(0, 0), successful=True, response_received=True)
        self.assertEqual(before, journal.snapshot())

    def test_entry_requires_durable_intent_and_settlement_requires_entry(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        with self.assertRaisesRegex(ConformanceJournalError, "send-intent-required"):
            journal.record_http_entry(handle)
        journal.persist_send_intent(handle)
        with self.assertRaisesRegex(ConformanceJournalError, "send-marker-required"):
            journal.settle(handle, usage=Usage(12, 3), successful=True, response_received=True)
        self.assertEqual(0, journal.snapshot()["http_entry_observations"])
        self.assertEqual(30, journal.snapshot()["unresolved_reserved_tokens"])

    def test_invalid_usage_tokens_and_subsets_hold_and_never_persist_original_values(self):
        for usage in (Usage(True, 1), Usage(-1, 1), Usage(float("inf"), 1),
                      Usage(12, 3, cached_input_tokens=13), Usage(12, 3, reasoning_tokens=True)):
            with self.subTest(usage=usage):
                path = self.path.with_name(str(uuid4()) + ".sqlite")
                journal = ConformanceUsageJournal.create(path, namespace=self.namespace, total_token_limit=1000)
                self.instances.append(journal)
                journal.start_attempt()
                handle = self.sent(journal)
                with self.assertRaises(ConformanceJournalError):
                    journal.settle(handle, usage=usage, successful=False, response_received=True)
                result = journal.snapshot()
                self.assertTrue(result["blocked"])
                self.assertEqual(30, result["unresolved_reserved_tokens"])
                self.assertIsNone(result["calls"][0]["reported_usage"])
                json.dumps(result, allow_nan=False)

    def test_usage_reflective_mutation_after_commit_does_not_change_replayed_totals(self):
        journal = self.create()
        journal.start_attempt()
        usage = Usage(12, 3, cached_input_tokens=10)
        self.known(journal, usage=usage)
        before = journal.snapshot()
        object.__setattr__(usage, "input_tokens", 0)
        object.__setattr__(usage, "currency", "SYNTHETIC-PRIVATE-AUTH")
        self.assertEqual(before, journal.snapshot())
        journal.close()
        self.assertEqual(15, self.reopen().snapshot()["known_total_tokens"])

    def test_handle_and_public_limits_reflective_mutation_cannot_expand_budget(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        object.__setattr__(handle, "input_upper_tokens", 200)
        with self.assertRaisesRegex(ConformanceJournalError, "reservation-integrity-failed"):
            journal.persist_send_intent(handle)
        limits = journal.limits
        object.__setattr__(limits, "total_token_limit", 10**9)
        self.assertEqual(1000, journal.snapshot()["limits"]["total_token_limit"])
        self.assertEqual(30, journal.snapshot()["unresolved_reserved_tokens"])

    def test_overreservation_and_total_overrun_keep_reported_tokens_and_halt(self):
        for total in (30, 1000):
            path = self.path.with_name(str(uuid4()) + ".sqlite")
            journal = ConformanceUsageJournal.create(path, namespace=self.namespace, total_token_limit=total)
            self.instances.append(journal)
            journal.start_attempt()
            handle = self.sent(journal)
            with self.assertRaises(ConformanceJournalError):
                journal.settle(handle, usage=Usage(25, 8), successful=False, response_received=True)
            self.assertEqual(33, journal.snapshot()["known_total_tokens"])
            self.assertTrue(journal.snapshot()["blocked"])
            with self.assertRaises(ConformanceJournalError):
                journal.start_attempt(repair_refreeze_confirmed=True)

    def test_three_calls_three_failed_attempts_and_no_retry_after_success(self):
        journal = self.create()
        journal.start_attempt()
        for _ in range(3):
            self.known(journal)
        with self.assertRaisesRegex(ConformanceJournalError, "invocation-budget-exhausted"):
            journal.reserve(input_upper_tokens=1, output_upper_tokens=1)
        for _ in range(2):
            journal.start_attempt(repair_refreeze_confirmed=True)
            journal.fail_attempt()
        with self.assertRaisesRegex(ConformanceJournalError, "attempt-budget-exhausted"):
            journal.start_attempt(repair_refreeze_confirmed=True)
        self.assertEqual(45, journal.snapshot()["known_total_tokens"])
        path = self.path.with_name("success.sqlite")
        successful = ConformanceUsageJournal.create(path, namespace=self.namespace, total_token_limit=1000)
        self.instances.append(successful)
        successful.start_attempt()
        self.known(successful)
        successful.finish_attempt()
        with self.assertRaisesRegex(ConformanceJournalError, "failed-attempt-required"):
            successful.start_attempt(repair_refreeze_confirmed=True)

    def test_budget_preflight_refusal_is_durable_and_never_sends(self):
        journal = self.create(29)
        journal.start_attempt()
        with self.assertRaisesRegex(ConformanceJournalError, "token-budget-exhausted"):
            journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.close()
        result = self.reopen(29).snapshot()
        self.assertEqual(0, result["provider_invocations"])
        self.assertEqual(0, result["http_entry_observations"])
        self.assertEqual("failed", result["attempts"][0]["status"])

    def test_corrupt_closed_events_and_schema_reject_with_no_raw_error_or_chain(self):
        journal = self.create()
        journal.start_attempt()
        marker = "SYNTHETIC-PRIVATE-PROVIDER-AUTH"
        journal._connection.execute("UPDATE events SET payload=?", (json.dumps({"provider_id": marker}),))
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            with self.assertRaises(ConformanceJournalError) as captured:
                journal.snapshot()
        self.assertIsNone(captured.exception.__cause__)
        self.assertIsNone(captured.exception.__context__)
        self.assertNotIn(marker, "".join(traceback.format_exception(captured.exception)))

    def test_provider_except_unknown_failure_clears_actual_exception_context(self):
        journal = self.create()
        journal.start_attempt()
        handle = self.sent(journal)
        marker = "SYNTHETIC-PROVIDER-AUTH-CONTEXT"
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            try:
                journal.settle(handle, usage=None, successful=False, response_received=False)
            except ConformanceJournalError as error:
                self.assertIsNone(error.__cause__)
                self.assertIsNone(error.__context__)
                self.assertNotIn(marker, "".join(traceback.format_exception(error)))
            else:
                self.fail("expected accounting halt")
        self.assertEqual(30, journal.snapshot()["unresolved_reserved_tokens"])

    def test_detached_snapshot_changes_cannot_change_sqlite_state(self):
        journal = self.create()
        journal.start_attempt()
        self.known(journal)
        before = journal.snapshot()
        modified = journal.snapshot()
        modified["limits"]["total_token_limit"] = 10**9
        modified["calls"][0]["reported_usage"]["input_tokens"] = 0
        modified["attempts"].clear()
        self.assertEqual(before, journal.snapshot())

    def test_business_failure_closes_attempt_after_counting_known_tokens(self):
        journal = self.create()
        journal.start_attempt()
        self.known(journal)
        journal.fail_attempt()
        self.assertEqual("failed", journal.snapshot()["attempts"][0]["status"])
        self.assertEqual(15, journal.snapshot()["known_total_tokens"])
        with self.assertRaises(ConformanceJournalError):
            journal.reserve(input_upper_tokens=1, output_upper_tokens=1)

    def test_durability_setting_drift_refuses_every_new_event(self):
        journal = self.create()
        journal.start_attempt()
        journal._connection.execute("PRAGMA synchronous=OFF")
        with self.assertRaisesRegex(ConformanceJournalError, "journal-durability-settings-drift"):
            journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal._connection.execute("PRAGMA synchronous=FULL")
        self.assertEqual(0, journal.snapshot()["provider_invocations"])

    def test_database_lock_failure_is_content_free_and_does_not_reset_budget(self):
        journal = self.create()
        journal.start_attempt()
        self.known(journal, successful=False)
        locked = sqlite3.connect(self.path, isolation_level=None)
        locked.execute("BEGIN IMMEDIATE")
        try:
            with self.assertRaisesRegex(ConformanceJournalError, "journal-storage-unavailable") as captured:
                journal.start_attempt(repair_refreeze_confirmed=True)
            self.assertIsNone(captured.exception.__cause__)
            self.assertIsNone(captured.exception.__context__)
        finally:
            locked.rollback()
            locked.close()
        self.assertEqual(15, journal.snapshot()["known_total_tokens"])
        self.assertEqual(1, len(journal.snapshot()["attempts"]))


if __name__ == "__main__":
    unittest.main()
