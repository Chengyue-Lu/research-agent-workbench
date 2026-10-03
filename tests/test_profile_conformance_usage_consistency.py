"""Cold usage concordance from genuine bound, synthetic-only driver receipts."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from research_workbench.adapters.models.profile_conformance_report import (
    verify_profile_conformance_report, write_profile_conformance_report,
)
from tests import test_profile_conformance_binding as binding_helpers
from tests import test_profile_conformance_reporting as reporting_helpers

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")


class PartialUsageOpener(binding_helpers.SyntheticOpener):
    def open(self, request, *, timeout):
        original = super().open(request, timeout=timeout)
        document = json.loads(original.getvalue())
        document["usage"]["output_tokens"] = None
        response = io.BytesIO(json.dumps(document).encode())
        response.status = original.status
        response.headers = original.headers
        return response


class ProfileConformanceUsageConsistencyTests(unittest.TestCase):
    """Generate each genuine scenario once; cold mutations never send again."""

    @classmethod
    def setUpClass(cls):
        fixture_type = binding_helpers.ProfileConformanceBindingTests
        fixture_type.setUpClass()
        cls.addClassCleanup(fixture_type.doClassCleanups)

        def fixture():
            item = fixture_type()
            item.setUp()
            cls.addClassCleanup(item.doCleanups)
            return item

        cls.completed_fixture = fixture()
        cls.completed = cls.completed_fixture.run_driver()
        cls.partial_fixture = fixture()
        cls.partial_fixture.opener = PartialUsageOpener()
        cls.partial = cls.partial_fixture.run_driver()

        cls.history_fixture = fixture()
        cls.prior_failed = cls.history_fixture.run_driver(
            guard=lambda stage, ordinal: ordinal != 2)
        cls.prior_fake_calls = len(cls.history_fixture.opener.bodies)
        cls.history_fixture.opener = binding_helpers.SyntheticOpener()
        cls.with_history = cls.history_fixture.run_driver(repair_refreeze_confirmed=True)

        cls.unavailable_fixture = fixture()
        original_snapshot = cls.unavailable_fixture.journal.snapshot

        def unavailable_after_calls():
            if len(cls.unavailable_fixture.opener.bodies) == 3:
                raise OSError("synthetic accounting unavailable")
            return original_snapshot()

        with patch.object(cls.unavailable_fixture.journal, "snapshot", side_effect=unavailable_after_calls):
            cls.unavailable = cls.unavailable_fixture.run_driver()

        cls.fake_http_effects = (len(cls.completed_fixture.opener.bodies)
            + len(cls.partial_fixture.opener.bodies) + cls.prior_fake_calls
            + len(cls.history_fixture.opener.bodies) + len(cls.unavailable_fixture.opener.bodies))

    def verify(self, report, fixture):
        return verify_profile_conformance_report(report, root=fixture.root, schema_root=ROOT / "schemas")

    def rejected(self, report, fixture):
        with self.assertRaises(ValueError):
            self.verify(report, fixture)

    def test_genuine_complete_usage_and_fixed_fake_effect_budget(self):
        self.assertEqual(self.fake_http_effects, 11)
        self.assertEqual(self.completed["stop_code"], "completed")
        self.assertEqual(self.verify(self.completed, self.completed_fixture), self.completed)
        accounting = self.completed["accounting"]
        self.assertEqual((accounting["known_input_tokens"], accounting["known_output_tokens"],
            accounting["known_total_tokens"]), (15, 6, 21))
        for call, reservation in zip(self.completed["calls"], accounting["calls"]):
            self.assertIsNone(reservation["verified_usage"])
            self.assertEqual({field: call[field] for field in FIELDS},
                {field: reservation["reported_usage"][field] for field in FIELDS})

    def test_screenshot_nine_million_input_is_rejected_before_publication(self):
        report = copy.deepcopy(self.completed)
        report["calls"][0]["input_tokens"] = 9_000_000
        self.rejected(report, self.completed_fixture)
        destination = self.completed_fixture.root / "tampered-usage.json"
        with self.assertRaises(ValueError):
            write_profile_conformance_report(report, destination,
                root=self.completed_fixture.root, schema_root=ROOT / "schemas")
        self.assertFalse(destination.exists())

    def test_each_actual_token_field_must_match_complete_receipt(self):
        # Auxiliary values remain within their subsets, so shape alone cannot reject.
        for field, value in (("input_tokens", 6), ("output_tokens", 3),
                ("cached_input_tokens", 1), ("reasoning_tokens", 1)):
            with self.subTest(field=field):
                report = copy.deepcopy(self.completed)
                report["calls"][0][field] = value
                self.rejected(report, self.completed_fixture)

    def test_cache_and_reasoning_subset_cannot_be_forged_in_both_rows(self):
        for field, value in (("cached_input_tokens", 6), ("reasoning_tokens", 3)):
            with self.subTest(field=field):
                report = copy.deepcopy(self.completed)
                report["calls"][0][field] = value
                report["accounting"]["calls"][0]["reported_usage"][field] = value
                self.rejected(report, self.completed_fixture)

    def test_received_flag_matches_settled_receipt_on_a_genuine_failed_attempt(self):
        self.assertEqual(self.prior_failed["stop_code"], "guard-refused")
        self.assertEqual(self.verify(self.prior_failed, self.history_fixture), self.prior_failed)
        report = copy.deepcopy(self.prior_failed)
        report["calls"][0]["response_received"] = False
        report["actual_counts"]["responses_received"] = 0
        self.rejected(report, self.history_fixture)

    def test_each_ledger_total_is_recomputed_from_complete_receipts(self):
        for field in ("known_input_tokens", "known_output_tokens", "known_total_tokens"):
            with self.subTest(field=field):
                report = copy.deepcopy(self.completed)
                report["accounting"][field] += 1
                self.rejected(report, self.completed_fixture)

    def test_prior_attempt_known_usage_is_included_without_borrowing_its_calls(self):
        self.assertEqual(self.prior_fake_calls, 1)
        self.assertEqual(self.with_history["binding"]["attempt_ordinal"], 2)
        self.assertEqual(len(self.with_history["calls"]), 3)
        self.assertEqual(sum(call["input_tokens"] + call["output_tokens"]
            for call in self.with_history["calls"]), 21)
        accounting = self.with_history["accounting"]
        self.assertEqual((accounting["known_input_tokens"], accounting["known_output_tokens"],
            accounting["known_total_tokens"]), (20, 8, 28))
        self.assertEqual(self.verify(self.with_history, self.history_fixture), self.with_history)
        report = copy.deepcopy(self.with_history)
        report["accounting"].update(known_input_tokens=15, known_output_tokens=6, known_total_tokens=21)
        self.rejected(report, self.history_fixture)

    def test_historical_receipt_tamper_is_not_hidden_by_selected_attempt_totals(self):
        report = copy.deepcopy(self.with_history)
        self.assertEqual(report["accounting"]["calls"][0]["attempt_ordinal"], 1)
        report["accounting"]["calls"][0]["reported_usage"]["input_tokens"] += 1
        self.rejected(report, self.history_fixture)

    def test_partial_usage_remains_unknown_with_conservative_exposure(self):
        self.assertEqual(self.partial["stop_code"], "unknown-token-usage")
        call = self.partial["calls"][0]
        self.assertEqual(call["input_tokens"], 5)
        self.assertIsNone(call["output_tokens"])
        accounting = self.partial["accounting"]
        reservation = accounting["calls"][0]
        self.assertIsNone(reservation["reported_usage"])
        self.assertIsNone(reservation["verified_usage"])
        self.assertEqual(reservation["accounting_status"], "unresolved")
        self.assertEqual(accounting["known_total_tokens"], 0)
        self.assertEqual(accounting["unresolved_reserved_tokens"], 132)
        result = self.verify(self.partial, self.partial_fixture)
        self.assertEqual(result, self.partial)
        self.assertIsNone(result["calls"][0]["output_tokens"])

    def test_unknown_output_cannot_be_relabelled_as_known_zero(self):
        report = copy.deepcopy(self.partial)
        report["calls"][0]["output_tokens"] = 0
        self.rejected(report, self.partial_fixture)

    def test_unavailable_final_accounting_preserves_bound_observed_facts(self):
        self.assertEqual(self.unavailable["status"], "blocked")
        self.assertEqual(self.unavailable["stop_code"], "accounting-failed")
        self.assertIsNone(self.unavailable["accounting"])
        self.assertEqual(sum(call["input_tokens"] + call["output_tokens"]
            for call in self.unavailable["calls"]), 21)
        self.assertEqual(self.verify(self.unavailable, self.unavailable_fixture), self.unavailable)

    def test_closed_durable_report_cannot_acquire_verified_usage(self):
        report = copy.deepcopy(self.completed)
        report["accounting"]["calls"][0]["verified_usage"] = copy.deepcopy(
            report["accounting"]["calls"][0]["reported_usage"])
        self.rejected(report, self.completed_fixture)

    def test_legacy_1_0_replay_keeps_original_no_binding_semantics(self):
        fixture = reporting_helpers.ProfileConformanceReportingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with patch("research_workbench.adapters.models.profile_conformance_report.EvaluationInputs",
                side_effect=AssertionError("legacy replay must not load binding")):
            result = verify_profile_conformance_report(fixture.report,
                root=fixture.directory, schema_root=ROOT / "schemas")
        self.assertEqual(result, fixture.report)
        self.assertIsNot(result, fixture.report)


if __name__ == "__main__":
    unittest.main()
