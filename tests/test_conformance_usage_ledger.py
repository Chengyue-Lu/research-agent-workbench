"""Bounded, synthetic process-local accounting; no Provider/transport use."""

import json
import threading
import traceback
import unittest
from dataclasses import FrozenInstanceError, replace

from research_workbench.adapters.models.conformance_ledger import (
    ConformanceLedgerError, ConformanceReservation, ConformanceUsageLedger,
    VerifiedUsageAccountingReceipt,
)
from research_workbench.adapters.models.port import Usage


class ConformanceUsageLedgerTests(unittest.TestCase):
    def ledger(self, total=1000, **options):
        return ConformanceUsageLedger(total_token_limit=total, **options)

    def sent(self, ledger, *, input_upper=20, output_upper=10):
        handle = ledger.reserve(input_upper_tokens=input_upper, output_upper_tokens=output_upper)
        ledger.mark_send_attempt(handle)
        return handle

    def known(self, ledger, *, successful=True, usage=Usage(12, 3)):
        handle = self.sent(ledger)
        ledger.settle(handle, usage=usage, successful=successful, response_received=True)
        return handle

    def test_explicit_total_limit_and_small_plan_limits(self):
        ledger = self.ledger(10_000_000)
        self.assertEqual(10_000_000, ledger.snapshot()["limits"]["total_token_limit"])
        for options in (
            {"total_token_limit": True}, {"total_token_limit": 0}, {"total_token_limit": 2**63},
            {"total_token_limit": 100, "max_attempts": 4},
            {"total_token_limit": 100, "max_invocations_per_attempt": 4},
            {"total_token_limit": 100, "max_output_tokens_per_invocation": 257},
        ):
            with self.subTest(options=options), self.assertRaises(ConformanceLedgerError):
                ConformanceUsageLedger(**options)

    def test_known_success_and_failure_both_count_input_plus_output(self):
        ledger = self.ledger()
        ledger.start_attempt()
        self.known(ledger)
        self.known(ledger, successful=False, usage=Usage(8, 2))
        result = ledger.snapshot()
        self.assertEqual((2, 2, 2, 1, 1), tuple(result[name] for name in (
            "provider_invocations", "http_send_attempts", "responses_received", "successful_responses", "failed_invocations"
        )))
        self.assertEqual((20, 5, 25), tuple(result[name] for name in ("known_input_tokens", "known_output_tokens", "known_total_tokens")))
        self.assertEqual("failed", result["attempts"][0]["status"])
        with self.assertRaises(ConformanceLedgerError):
            ledger.reserve(input_upper_tokens=1, output_upper_tokens=1)

    def test_cache_and_reasoning_are_subsets_not_extra_tokens(self):
        ledger = self.ledger()
        ledger.start_attempt()
        self.known(ledger, usage=Usage(12, 3, cached_input_tokens=10, reasoning_tokens=2))
        self.assertEqual(15, ledger.snapshot()["known_total_tokens"])

    def test_budget_preflight_rejects_before_any_send(self):
        ledger = self.ledger(29)
        ledger.start_attempt()
        with self.assertRaisesRegex(ConformanceLedgerError, "token-budget-exhausted"):
            ledger.reserve(input_upper_tokens=20, output_upper_tokens=10)
        result = ledger.snapshot()
        self.assertEqual(0, result["provider_invocations"])
        self.assertEqual(0, result["http_send_attempts"])
        self.assertEqual("failed", result["attempts"][0]["status"])

    def test_pending_reservation_reduces_remaining_capacity_and_disallows_parallel(self):
        ledger = self.ledger(50)
        ledger.start_attempt()
        handle = ledger.reserve(input_upper_tokens=20, output_upper_tokens=10)
        self.assertEqual((0, 30, 20), tuple(ledger.snapshot()[name] for name in (
            "known_total_tokens", "unresolved_reserved_tokens", "remaining_token_capacity"
        )))
        with self.assertRaisesRegex(ConformanceLedgerError, "reservation-still-active"):
            ledger.reserve(input_upper_tokens=1, output_upper_tokens=1)
        ledger.reject_before_send(handle)

    def test_unsent_rejection_releases_tokens_but_preserves_provider_failure(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = ledger.reserve(input_upper_tokens=20, output_upper_tokens=10)
        ledger.reject_before_send(handle)
        result = ledger.snapshot()
        self.assertEqual((1, 0, 1, 0, 1000), tuple(result[name] for name in (
            "provider_invocations", "http_send_attempts", "failed_invocations", "unresolved_reserved_tokens", "remaining_token_capacity"
        )))
        self.assertEqual("failed-before-send", result["calls"][0]["outcome"])

    def test_started_send_failure_cannot_be_released_or_erased_by_new_attempt(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        with self.assertRaisesRegex(ConformanceLedgerError, "cannot-release-started-send"):
            ledger.reject_before_send(handle)
        with self.assertRaisesRegex(ConformanceLedgerError, "usage-unavailable"):
            ledger.settle(handle, usage=None, successful=False, response_received=False)
        result = ledger.snapshot()
        self.assertTrue(result["blocked"])
        self.assertEqual(1, result["http_send_attempts"])
        self.assertEqual(30, result["unresolved_reserved_tokens"])
        with self.assertRaisesRegex(ConformanceLedgerError, "accounting-blocked"):
            ledger.start_attempt(repair_refreeze_confirmed=True)
        self.assertEqual(result, ledger.snapshot())

    def test_explicit_verified_receipt_can_resolve_unknown_but_does_not_start_retry(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        with self.assertRaises(ConformanceLedgerError):
            ledger.settle(handle, usage=None, successful=False, response_received=False)
        receipt = VerifiedUsageAccountingReceipt(1, 1, Usage(7, 1), verified=True)
        ledger.reconcile(handle, receipt=receipt)
        result = ledger.snapshot()
        self.assertFalse(result["blocked"])
        self.assertEqual(8, result["known_total_tokens"])
        self.assertEqual(1, len(result["attempts"]))
        self.assertEqual("failed", result["attempts"][0]["status"])
        self.assertIsNone(result["calls"][0]["reported_usage"])
        self.assertEqual(7, result["calls"][0]["verified_usage"]["input_tokens"])
        with self.assertRaisesRegex(ConformanceLedgerError, "fresh-refreeze"):
            ledger.start_attempt()
        self.assertEqual(2, ledger.start_attempt(repair_refreeze_confirmed=True))
        with self.assertRaisesRegex(ConformanceLedgerError, "reconciliation-not-eligible"):
            ledger.reconcile(handle, receipt=receipt)

    def test_unverified_wrong_call_bad_version_or_overbound_receipts_keep_halt(self):
        for receipt in (
            VerifiedUsageAccountingReceipt(1, 1, Usage(7, 1), verified=False),
            VerifiedUsageAccountingReceipt(2, 1, Usage(7, 1), verified=True),
            VerifiedUsageAccountingReceipt(1, 1, Usage(7, 1), verified=True, version="2.0.0"),
            VerifiedUsageAccountingReceipt(1, 1, Usage(21, 1), verified=True),
        ):
            ledger = self.ledger()
            ledger.start_attempt()
            handle = self.sent(ledger)
            with self.assertRaises(ConformanceLedgerError):
                ledger.settle(handle, usage=None, successful=False, response_received=False)
            before = ledger.snapshot()
            with self.subTest(receipt=receipt), self.assertRaises(ConformanceLedgerError):
                ledger.reconcile(handle, receipt=receipt)
            self.assertEqual(before, ledger.snapshot())

    def test_reservation_overrun_counts_reported_tokens_and_keeps_failure(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        with self.assertRaisesRegex(ConformanceLedgerError, "reservation-exceeded"):
            ledger.settle(handle, usage=Usage(25, 8), successful=True, response_received=True)
        result = ledger.snapshot()
        self.assertEqual(33, result["known_total_tokens"])
        self.assertTrue(result["blocked"])
        self.assertEqual(25, result["calls"][0]["reported_usage"]["input_tokens"])
        ledger.reconcile(handle, receipt=VerifiedUsageAccountingReceipt(1, 1, Usage(20, 8), verified=True))
        self.assertEqual(25, ledger.snapshot()["calls"][0]["reported_usage"]["input_tokens"])
        self.assertEqual(20, ledger.snapshot()["calls"][0]["verified_usage"]["input_tokens"])

    def test_global_overrun_is_counted_and_permanent_halt(self):
        ledger = self.ledger(30)
        ledger.start_attempt()
        handle = self.sent(ledger)
        with self.assertRaisesRegex(ConformanceLedgerError, "total-token-limit-exceeded"):
            ledger.settle(handle, usage=Usage(31, 2), successful=False, response_received=True)
        self.assertEqual(33, ledger.snapshot()["known_total_tokens"])
        self.assertEqual(0, ledger.snapshot()["remaining_token_capacity"])
        with self.assertRaises(ConformanceLedgerError):
            ledger.reconcile(handle, receipt=VerifiedUsageAccountingReceipt(1, 1, Usage(10, 1), verified=True))

    def test_known_prior_usage_stays_counted_when_later_unknown_call_holds_reservation(self):
        ledger = self.ledger(100)
        ledger.start_attempt()
        self.known(ledger)
        handle = self.sent(ledger)
        with self.assertRaises(ConformanceLedgerError):
            ledger.settle(handle, usage=Usage(), successful=False, response_received=True)
        result = ledger.snapshot()
        self.assertEqual((15, 30, 55), tuple(result[name] for name in (
            "known_total_tokens", "unresolved_reserved_tokens", "remaining_token_capacity"
        )))

    def test_invalid_usage_and_subsets_block_and_do_not_leak_bad_fields(self):
        for usage in (
            Usage(True, 1), Usage(-1, 1), Usage(float("inf"), 1), Usage(2**63, 1),
            Usage(10, 2, cached_input_tokens=True), Usage(10, 2, cached_input_tokens=11),
            Usage(10, 2, reasoning_tokens=3), Usage(10, 2, reasoning_tokens=-1),
        ):
            ledger = self.ledger()
            ledger.start_attempt()
            handle = self.sent(ledger)
            with self.subTest(usage=usage), self.assertRaises(ConformanceLedgerError):
                ledger.settle(handle, usage=usage, successful=False, response_received=True)
            result = ledger.snapshot()
            self.assertTrue(result["blocked"])
            self.assertEqual(30, result["unresolved_reserved_tokens"])
            self.assertIsNone(result["calls"][0]["reported_usage"])

    def test_unknown_cost_preserves_known_tokens_and_is_not_zero_or_estimated(self):
        ledger = self.ledger()
        ledger.start_attempt()
        self.known(ledger)
        result = ledger.snapshot()
        self.assertEqual(15, result["known_total_tokens"])
        self.assertFalse(result["blocked"])
        self.assertEqual(1, result["cost"]["unknown_call_count"])
        self.assertEqual({}, result["cost"]["amounts_by_currency"])
        self.assertFalse(result["cost"]["estimated_cost_computed"])
        self.assertIsNone(result["calls"][0]["reported_usage"]["provider_reported_cost"])

    def test_reported_costs_are_currency_separated_and_never_billing_verified(self):
        ledger = self.ledger()
        ledger.start_attempt()
        self.known(ledger, usage=Usage(12, 3, provider_reported_cost=0.1, currency="USD"))
        self.known(ledger, usage=Usage(12, 3, provider_reported_cost=0.2, currency="CNY"))
        cost = ledger.snapshot()["cost"]
        self.assertEqual({"USD": 0.1, "CNY": 0.2}, cost["amounts_by_currency"])
        self.assertFalse(cost["billing_settlement_verified"])

    def test_invalid_cost_and_currency_have_content_free_errors_and_reserved_halt(self):
        marker = "SYNTHETIC-PRIVATE-CURRENCY-AUTH"
        for usage in (
            Usage(12, 3, provider_reported_cost=True, currency="USD"),
            Usage(12, 3, provider_reported_cost=-1, currency="USD"),
            Usage(12, 3, provider_reported_cost=float("nan"), currency="USD"),
            Usage(12, 3, provider_reported_cost=10**1000, currency="USD"),
            Usage(12, 3, provider_reported_cost=0.1),
            Usage(12, 3, provider_reported_cost=0.1, currency=marker),
        ):
            ledger = self.ledger()
            ledger.start_attempt()
            handle = self.sent(ledger)
            with self.assertRaises(ConformanceLedgerError) as captured:
                ledger.settle(handle, usage=usage, successful=False, response_received=True)
            self.assertIsNone(captured.exception.__cause__)
            self.assertIsNone(captured.exception.__context__)
            self.assertNotIn(marker, str(captured.exception))
            result = ledger.snapshot()
            self.assertTrue(result["blocked"])
            self.assertEqual(30, result["unresolved_reserved_tokens"])
            self.assertNotIn(marker, json.dumps(result, allow_nan=False))

    def test_double_send_settle_reuse_and_foreign_handles_fail(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        with self.assertRaisesRegex(ConformanceLedgerError, "send-already-marked"):
            ledger.mark_send_attempt(handle)
        ledger.settle(handle, usage=Usage(12, 3), successful=True, response_received=True)
        for operation in (
            lambda: ledger.mark_send_attempt(handle),
            lambda: ledger.reject_before_send(handle),
            lambda: ledger.settle(handle, usage=Usage(0, 0), successful=True, response_received=True),
        ):
            with self.assertRaises(ConformanceLedgerError):
                operation()
        with self.assertRaisesRegex(ConformanceLedgerError, "foreign-reservation"):
            ledger.mark_send_attempt(ConformanceReservation(1, 1, 20, 10))
        self.assertEqual(15, ledger.snapshot()["known_total_tokens"])

    def test_settle_without_send_and_false_success_response_are_rejected(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = ledger.reserve(input_upper_tokens=20, output_upper_tokens=10)
        with self.assertRaisesRegex(ConformanceLedgerError, "send-marker-required"):
            ledger.settle(handle, usage=Usage(0, 0), successful=False, response_received=False)
        ledger.mark_send_attempt(handle)
        with self.assertRaisesRegex(ConformanceLedgerError, "invalid-response-outcome"):
            ledger.settle(handle, usage=Usage(1, 1), successful=True, response_received=False)

    def test_at_most_three_invocations_and_three_explicit_attempts(self):
        ledger = self.ledger()
        ledger.start_attempt()
        for _ in range(3):
            self.known(ledger)
        with self.assertRaisesRegex(ConformanceLedgerError, "invocation-budget-exhausted"):
            ledger.reserve(input_upper_tokens=1, output_upper_tokens=1)
        for _ in range(2):
            ledger.start_attempt(repair_refreeze_confirmed=True)
            handle = ledger.reserve(input_upper_tokens=1, output_upper_tokens=1)
            ledger.reject_before_send(handle)
        with self.assertRaisesRegex(ConformanceLedgerError, "attempt-budget-exhausted"):
            ledger.start_attempt(repair_refreeze_confirmed=True)
        self.assertEqual(45, ledger.snapshot()["known_total_tokens"])

    def test_input_bound_is_explicit_and_no_context_length_default_exists(self):
        ledger = self.ledger()
        ledger.start_attempt()
        with self.assertRaises(TypeError):
            ledger.reserve(output_upper_tokens=10)
        for value in (False, -1, 0, 1.5, "1000000"):
            candidate = self.ledger()
            candidate.start_attempt()
            with self.assertRaises(ConformanceLedgerError):
                candidate.reserve(input_upper_tokens=value, output_upper_tokens=10)

    def test_snapshot_and_limits_do_not_expose_mutable_internal_state(self):
        ledger = self.ledger()
        ledger.start_attempt()
        self.known(ledger)
        original = ledger.snapshot()
        changed = ledger.snapshot()
        changed["limits"]["total_token_limit"] = 10**9
        changed["calls"][0]["reported_usage"]["input_tokens"] = 0
        changed["attempts"].clear()
        exposed_limits = ledger.limits
        with self.assertRaises(FrozenInstanceError):
            exposed_limits.total_token_limit = 10**9
        object.__setattr__(exposed_limits, "total_token_limit", 10**9)
        self.assertEqual(original, ledger.snapshot())

    def test_two_threads_cannot_reserve_parallel_budget(self):
        ledger = self.ledger()
        ledger.start_attempt()
        barrier = threading.Barrier(3)
        accepted = []
        refused = []

        def reserve():
            barrier.wait()
            try:
                accepted.append(ledger.reserve(input_upper_tokens=20, output_upper_tokens=10))
            except ConformanceLedgerError as error:
                refused.append(error.code)

        workers = [threading.Thread(target=reserve) for _ in range(2)]
        for worker in workers:
            worker.start()
        barrier.wait()
        for worker in workers:
            worker.join()
        self.assertEqual(1, len(accepted))
        self.assertEqual(["reservation-still-active"], refused)
        self.assertEqual(1, ledger.snapshot()["provider_invocations"])

    def test_reported_cost_aggregation_never_returns_nonfinite_or_restarts_after_overflow(self):
        ledger = self.ledger()
        ledger.start_attempt()
        for _ in range(3):
            self.known(ledger, usage=Usage(12, 3, provider_reported_cost=1e308, currency="USD"))
        result = ledger.snapshot()
        self.assertIsNone(result["cost"]["amounts_by_currency"]["USD"])
        self.assertEqual("nonfinite-unavailable", result["cost"]["aggregation_status"])
        json.dumps(result, allow_nan=False)

    def test_total_budget_remains_cumulative_across_failed_fresh_attempts(self):
        ledger = self.ledger(40)
        ledger.start_attempt()
        self.known(ledger, successful=False, usage=Usage(18, 2))
        ledger.start_attempt(repair_refreeze_confirmed=True)
        with self.assertRaisesRegex(ConformanceLedgerError, "token-budget-exhausted"):
            ledger.reserve(input_upper_tokens=20, output_upper_tokens=10)
        result = ledger.snapshot()
        self.assertEqual(20, result["known_total_tokens"])
        self.assertEqual(1, result["provider_invocations"])
        self.assertEqual(["failed", "failed"], [item["status"] for item in result["attempts"]])

    def test_two_threads_cannot_settle_the_same_send_twice(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        barrier = threading.Barrier(3)
        accepted, refused = [], []

        def settle():
            barrier.wait()
            try:
                ledger.settle(handle, usage=Usage(12, 3), successful=True, response_received=True)
                accepted.append(True)
            except ConformanceLedgerError as error:
                refused.append(error.code)

        workers = [threading.Thread(target=settle) for _ in range(2)]
        for worker in workers:
            worker.start()
        barrier.wait()
        for worker in workers:
            worker.join()
        self.assertEqual([True], accepted)
        self.assertEqual(["reservation-already-settled-or-inactive"], refused)
        self.assertEqual(15, ledger.snapshot()["known_total_tokens"])

    def test_reflective_handle_mutation_does_not_change_private_reservation(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = ledger.reserve(input_upper_tokens=20, output_upper_tokens=10)
        object.__setattr__(handle, "input_upper_tokens", True)
        with self.assertRaisesRegex(ConformanceLedgerError, "reservation-integrity-failed"):
            ledger.mark_send_attempt(handle)
        result = ledger.snapshot()
        self.assertEqual(30, result["unresolved_reserved_tokens"])
        self.assertEqual(20, result["calls"][0]["input_upper_tokens"])
        self.assertEqual(0, result["http_send_attempts"])

    def test_caller_usage_mutation_after_settlement_cannot_change_accounting(self):
        ledger = self.ledger()
        ledger.start_attempt()
        usage = Usage(12, 3, provider_reported_cost=0.1, currency="USD")
        self.known(ledger, usage=usage)
        before = ledger.snapshot()
        object.__setattr__(usage, "input_tokens", 0)
        object.__setattr__(usage, "currency", "SYNTHETIC-PRIVATE-AUTH")
        self.assertEqual(before, ledger.snapshot())

    def test_non_usage_metadata_never_enters_snapshot_or_error(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        marker = "SYNTHETIC-PRIVATE-PROVIDER-ID-AUTH"
        with self.assertRaises(ConformanceLedgerError) as captured:
            ledger.settle(handle, usage={"provider_id": marker, "Authorization": marker}, successful=False, response_received=True)
        self.assertNotIn(marker, str(captured.exception))
        self.assertIsNone(captured.exception.__context__)
        self.assertNotIn(marker, json.dumps(ledger.snapshot(), allow_nan=False))
        self.assertEqual(30, ledger.snapshot()["unresolved_reserved_tokens"])

    def test_provider_exception_context_never_leaves_ledger_error_boundary(self):
        ledger = self.ledger()
        ledger.start_attempt()
        handle = self.sent(ledger)
        marker = "SYNTHETIC-PROVIDER-AUTH-ONLY"
        for operation in (
            lambda: ledger.settle(handle, usage=None, successful=False, response_received=False),
            lambda: ledger.start_attempt(repair_refreeze_confirmed=True),
            lambda: ConformanceUsageLedger(total_token_limit=False),
        ):
            try:
                raise RuntimeError(marker)
            except RuntimeError:
                try:
                    operation()
                except ConformanceLedgerError as error:
                    self.assertIsNone(error.__cause__)
                    self.assertIsNone(error.__context__)
                    self.assertTrue(error.__suppress_context__)
                    self.assertNotIn(marker, "".join(traceback.format_exception(error)))
                else:
                    self.fail("expected ledger error")
        self.assertTrue(ledger.snapshot()["blocked"])
        self.assertEqual(30, ledger.snapshot()["unresolved_reserved_tokens"])


if __name__ == "__main__":
    unittest.main()
