"""Granted Attempt4 and cold receipts from source-bound synthetic HTTP only."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from research_workbench.adapters.models import profile_conformance as driver
from research_workbench.adapters.models import conformance_budget_grant as grant_policy
from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.profile_conformance_report import (
    verify_profile_conformance_report, write_profile_conformance_report,
)
from research_workbench.evaluation.pins import EvaluationInputs
from tests import test_conformance_budget_extension as grant_helpers
from tests import test_profile_conformance_binding as binding_helpers

ROOT = Path(__file__).resolve().parents[1]


class ClosingOpener(binding_helpers.SyntheticOpener):
    def __init__(self, journal):
        super().__init__()
        self.journal = journal

    def open(self, request, *, timeout):
        response = super().open(request, timeout=timeout)
        self.journal.close()
        return response


class ProfileConformanceExtendedBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_type = binding_helpers.ProfileConformanceBindingTests
        fixture_type.setUpClass()
        cls.addClassCleanup(fixture_type.doClassCleanups)

        def fixture():
            item = fixture_type()
            item.setUp()
            cls.addClassCleanup(item.doCleanups)
            item.journal.close()
            item.journal = ConformanceUsageJournal.create(item.root / "granted.sqlite",
                anchor_path=item.root / "granted.anchor", namespace=str(uuid4()),
                total_token_limit=10_000_000)
            cls.addClassCleanup(item.journal.close)
            helper = grant_helpers.BudgetExtensionTests()
            helper.root, helper.journal = item.root, item.journal
            helper.namespace = item.journal.snapshot()["budget_namespace"]
            helper.history()
            helper.grant()
            return item

        cls.completed_fixture = fixture()
        cls.completed = cls.completed_fixture.run_driver(max_seconds=360, repair_refreeze_confirmed=True)
        cls.unavailable_fixture = fixture()
        original_snapshot = cls.unavailable_fixture.journal.snapshot

        def unavailable_after_calls():
            if len(cls.unavailable_fixture.opener.bodies) == 3:
                raise OSError("synthetic accounting unavailable")
            return original_snapshot()

        with patch.object(cls.unavailable_fixture.journal, "snapshot", side_effect=unavailable_after_calls):
            cls.unavailable = cls.unavailable_fixture.run_driver(max_seconds=360, repair_refreeze_confirmed=True)

        cls.closed_fixture = fixture()
        cls.closed_fixture.opener = ClosingOpener(cls.closed_fixture.journal)
        cls.closed = cls.closed_fixture.run_driver(max_seconds=360, repair_refreeze_confirmed=True)

        cls.construction_fixture = fixture()
        with patch.object(driver, "build_profile_provider", side_effect=ValueError("synthetic construction failure")):
            cls.construction = cls.construction_fixture.run_driver(max_seconds=360, repair_refreeze_confirmed=True)

    def verify(self, report, fixture):
        return verify_profile_conformance_report(report, root=fixture.root, schema_root=ROOT / "schemas")

    def test_granted_attempt_four_retains_prefix_and_cold_publication(self):
        report = self.completed
        self.assertEqual((report["report_version"], report["stop_code"], report["binding"]["attempt_ordinal"]),
                         ("1.2.0", "completed", 4))
        self.assertEqual(report["limits"]["max_seconds"], 360)
        self.assertTrue(all(report["assertions"].values()))
        self.assertEqual(report["actual_counts"]["responses_received"], 3)
        self.assertEqual(report["accounting"]["known_total_tokens"], 1226)
        self.assertEqual(report["accounting"]["unresolved_reserved_tokens"], 0)
        self.assertEqual(report["budget_extension"]["baseline_limits"]["max_attempts"], 3)
        self.assertEqual(report["budget_extension"]["effective_limits"]["max_attempts"], 10)
        self.assertFalse(report["live_qualified"])
        self.assertFalse(report["remote_strict_claim"])
        self.assertEqual(self.verify(report, self.completed_fixture), report)
        output = self.completed_fixture.root / "granted-report.json"
        write_profile_conformance_report(report, output, root=self.completed_fixture.root, schema_root=ROOT / "schemas")
        self.assertTrue(output.exists())

    def test_budget_helper_is_a_graph_member_and_post_guard_drift_blocks_before_credentials(self):
        # A completed Attempt closes this budget lineage. Use the prior
        # zero-call construction failure fixture to test a fresh Attempt4.
        fixture = self.construction_fixture
        report = self.construction
        graph = EvaluationInputs(fixture.root).read(report["binding"]["implementation_closure_ref"])
        module = "research_workbench.adapters.models.conformance_budget_grant"
        journal = "research_workbench.adapters.models.conformance_journal"
        self.assertIn(module, graph["modules"])
        self.assertIn(module, graph["modules"][journal]["dependencies"])
        previous_resolutions = fixture.credential.resolutions
        original_opener = fixture.opener
        fixture.opener = binding_helpers.SyntheticOpener()
        mutation = patch.object(grant_policy, "validate_grant", lambda *args, **kwargs: None)
        mutated = False

        def guard(stage, ordinal):
            nonlocal mutated
            if stage == "preinvoke" and ordinal != 1 and not mutated:
                mutation.start()
                mutated = True
            return True

        try:
            refused = fixture.run_driver(max_seconds=360, repair_refreeze_confirmed=True, guard=guard)
            self.assertEqual(refused["stop_code"], "guard-refused")
            self.assertEqual(refused["actual_counts"]["http_entry_observations"], 0)
            self.assertEqual(fixture.opener.bodies, [])
            self.assertEqual(fixture.credential.resolutions, previous_resolutions)
        finally:
            mutation.stop()
            fixture.opener = original_opener
        self.assertEqual(self.verify(refused, fixture), refused)

    def test_extended_report_cannot_drop_grant_binding_or_retained_facts(self):
        mutations = (
            lambda value: value.pop("binding"),
            lambda value: value.pop("budget_extension"),
            lambda value: value["budget_extension"]["effective_limits"].update(max_attempts=11),
            lambda value: value["accounting"]["calls"][0].update(response_received=False),
            lambda value: value["calls"][0].update(input_tokens=9_000_000),
        )
        for index, mutation in enumerate(mutations):
            value = copy.deepcopy(self.completed)
            mutation(value)
            output = self.completed_fixture.root / f"rejected-{index}.json"
            with self.subTest(index=index), self.assertRaises(ValueError):
                write_profile_conformance_report(value, output,
                    root=self.completed_fixture.root, schema_root=ROOT / "schemas")
            self.assertFalse(output.exists())

    def test_unavailable_final_snapshot_preserves_grant_and_three_received_usages(self):
        report = self.unavailable
        self.assertEqual((report["report_version"], report["status"], report["stop_code"]),
                         ("1.2.0", "blocked", "accounting-failed"))
        self.assertIsNone(report["accounting"])
        self.assertEqual(report["actual_counts"]["responses_received"], 3)
        self.assertEqual(sum(call["input_tokens"] + call["output_tokens"] for call in report["calls"]), 21)
        self.assertEqual(self.verify(report, self.unavailable_fixture), report)

    def test_closed_journal_after_response_preserves_known_facts_without_tool(self):
        report = self.closed
        self.assertEqual((report["report_version"], report["status"], report["stop_code"]),
                         ("1.2.0", "blocked", "accounting-failed"))
        self.assertIsNone(report["accounting"])
        self.assertEqual(report["actual_counts"]["responses_received"], 1)
        self.assertEqual(report["actual_counts"]["http_entry_observations"], 1)
        self.assertEqual(report["actual_counts"]["tool_executions"], 0)
        self.assertEqual((report["calls"][0]["input_tokens"], report["calls"][0]["output_tokens"]), (5, 2))
        self.assertEqual(self.verify(report, self.closed_fixture), report)

    def test_pre_attempt_failure_has_bound_extension_without_new_slots_or_credentials(self):
        report = self.construction
        self.assertEqual((report["report_version"], report["status"], report["stop_code"]),
                         ("1.2.0", "blocked", "provider-construction-refused"))
        self.assertIsNone(report["binding"]["attempt_ordinal"])
        self.assertEqual(report["calls"], [])
        self.assertEqual(report["accounting"]["known_total_tokens"], 1205)
        self.assertEqual(len(report["accounting"]["attempts"]), 3)
        self.assertEqual(self.construction_fixture.credential.resolutions, 0)
        self.assertEqual(self.verify(report, self.construction_fixture), report)


if __name__ == "__main__":
    unittest.main()
