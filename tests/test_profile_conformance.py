"""Three-call fake profile driver, privacy and durable failures; no env/Key I/O."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.http import HttpResponse
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2
from research_workbench.adapters.models.profile_conformance import profile_conformance_plan, run_profile_conformance
from tests import test_configured_provider as configured_helpers


class NativeSequence:
    def __init__(self, model):
        self.model = model
        self.max_response_bytes = 8388608
        self.requests = []
        self.fail = False
        self.bad_text = False
        self.bad_schema = False
        self.unknown_usage = False
        self.identity_drift = False
        self.bad_money = False

    def send(self, request):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("synthetic secret-like provider detail")
        phase = len(self.requests)
        document = {"id": "synthetic-private-id", "model": self.model, "status": "completed",
                    "usage": {"input_tokens": 5, "output_tokens": 2}}
        if self.unknown_usage:
            document["usage"].pop("output_tokens")
        if self.identity_drift:
            document["model"] = "synthetic-other-model"
        if self.bad_money:
            document["usage"].update(cost="synthetic private money detail", currency="synthetic unavailable currency")
        if phase == 1:
            document["output"] = [{"type": "function_call", "status": "completed", "call_id": "synthetic-private-call-id",
                "name": "add_ints", "arguments": '{"a":3,"b":4}'}]
        else:
            text = ("8" if self.bad_text else "7") if phase == 2 else ('{"sum":8}' if self.bad_schema else '{"sum":7}')
            document["output"] = [{"type": "message", "role": "assistant", "status": "completed",
                                   "content": [{"type": "output_text", "text": text}]}]
        return HttpResponse(200, {}, json.dumps(document).encode())


class RejectingSummary:
    conformance_summary_version = "1.0.0"

    def record(self, kind, payload):
        if kind == "response-summary":
            raise OSError("synthetic private capture detail")


class ProfileConformanceTests(unittest.TestCase):
    def setUp(self):
        self.helper = configured_helpers.ConfiguredProviderTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        provider = self.helper.build("deepseek")
        original = dict(provider.resolved_config)
        original.pop("model")
        original["model_selector"] = {"kind": "literal", "value": provider.model}
        self.config = ProviderAdapterConfigV2.from_mapping(original)
        self.transport = NativeSequence(provider.model)
        self.path = self.helper.root / "conformance.sqlite"
        self.journal = ConformanceUsageJournal.create(self.path, namespace="22222222-2222-4222-8222-222222222222", total_token_limit=1000)
        self.addCleanup(self.journal.close)
        self.guard_stages = []

    def guard(self, stage, ordinal):
        self.guard_stages.append((stage, ordinal))
        return True

    def run_driver(self, **extra):
        options = dict(root=self.helper.root, journal=self.journal, transport=self.transport,
                       credential=self.helper.credential, guard=self.guard, input_upper_tokens=(100, 100, 100),
                       max_output_tokens=32, max_seconds=120)
        options.update(extra)
        return run_profile_conformance(self.config, **options)

    def test_plan_only_never_constructs_or_observes_credentials(self):
        with patch("research_workbench.adapters.models.profile_conformance.build_profile_provider", side_effect=AssertionError("factory called")):
            plan = profile_conformance_plan(self.config, root=self.helper.root)
        self.assertEqual(plan["max_provider_invocations"], 3)
        self.assertEqual(plan["readiness"], "ready")
        self.assertFalse(plan["live_qualified"])
        self.assertEqual(self.helper.credential.resolutions, 0)
        self.assertEqual(self.helper.credential.presence_checks, 0)

    def test_complete_three_call_path_exact_history_and_redacted_report(self):
        report = self.run_driver()
        self.assertEqual(report["stop_code"], "completed")
        self.assertEqual(report["actual_counts"], {"provider_invocations": 3, "http_entry_observations": 3,
                                                 "tool_executions": 1, "responses_received": 3})
        self.assertTrue(all(report["assertions"].values()))
        self.assertEqual(report["accounting"]["known_total_tokens"], 21)
        self.assertEqual(self.guard_stages, [("preinvoke", 1), ("send", 1), ("preinvoke", 2), ("send", 2),
                                           ("preinvoke", 3), ("send", 3)])
        first, second, third = [json.loads(item.body) for item in self.transport.requests]
        self.assertEqual(first["tool_choice"], {"type": "function", "name": "add_ints"})
        self.assertEqual(second["tool_choice"], "none")
        self.assertIn({"type": "function_call_output", "call_id": "synthetic-private-call-id", "output": "7"}, second["input"])
        self.assertEqual(third["text"]["format"]["schema"]["properties"]["sum"]["enum"], [7])
        text = json.dumps(report)
        for private in ("synthetic-private-id", "synthetic-private-call-id", "synthetic-offline-key", "synthetic private", "arguments"):
            self.assertNotIn(private, text)
        self.assertFalse(report["remote_strict_claim"])
        self.assertFalse(report["live_qualified"])
        self.assertEqual(self.helper.credential.presence_checks, 0)

    def test_explicit_bounds_required_and_guard_refusal_releases_unsent(self):
        report = self.run_driver(input_upper_tokens=None)
        self.assertEqual(report["stop_code"], "input-bounds-required")
        report = self.run_driver(guard=lambda stage, ordinal: False)
        self.assertEqual(report["stop_code"], "guard-refused")
        self.assertEqual(report["accounting"]["unresolved_reserved_tokens"], 0)
        self.assertEqual(self.helper.credential.resolutions, 0)
        self.assertEqual(self.transport.requests, [])

    def test_unknown_post_entry_failure_holds_and_reopen_blocks(self):
        self.transport.fail = True
        report = self.run_driver()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["accounting"]["unresolved_reserved_tokens"], 132)
        self.journal.close()
        reopened = ConformanceUsageJournal.open(self.path, namespace="22222222-2222-4222-8222-222222222222", total_token_limit=1000)
        self.addCleanup(reopened.close)
        again = self.run_driver(journal=reopened, repair_refreeze_confirmed=True)
        self.assertEqual(again["stop_code"], "journal-blocked")
        self.assertEqual(len(self.transport.requests), 1)

    def test_business_failure_stops_and_retains_known_tokens(self):
        self.transport.bad_text = True
        report = self.run_driver()
        self.assertEqual(report["stop_code"], "text-assertion-failed")
        self.assertEqual(report["accounting"]["known_total_tokens"], 14)
        self.assertEqual(len(self.transport.requests), 2)

    def test_schema_and_identity_failed_usage_is_retained(self):
        self.transport.bad_schema = True
        report = self.run_driver()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["accounting"]["known_total_tokens"], 21)
        self.assertEqual(report["calls"][2]["input_tokens"], 5)
        self.assertFalse(report["assertions"]["schema_exact"])

    def test_identity_failed_usage_retained_without_accepting_identity(self):
        self.transport.identity_drift = True
        report = self.run_driver()
        self.assertEqual(report["accounting"]["known_total_tokens"], 7)
        self.assertEqual(report["observed_models"], [])
        self.assertEqual(report["actual_counts"]["tool_executions"], 0)

    def test_capture_failure_settles_received_usage_before_stopping(self):
        report = self.run_driver(event_sink=RejectingSummary())
        self.assertEqual(report["stop_code"], "capture-gap")
        self.assertEqual(report["accounting"]["known_total_tokens"], 7)
        self.assertEqual(report["actual_counts"]["responses_received"], 1)
        self.assertEqual(len(self.transport.requests), 1)

    def test_unknown_usage_blocks_without_zero_or_next_call(self):
        self.transport.unknown_usage = True
        report = self.run_driver()
        self.assertEqual(report["stop_code"], "unknown-token-usage")
        self.assertIsNone(report["calls"][0]["output_tokens"])
        self.assertEqual(len(self.transport.requests), 1)
        self.assertEqual(report["accounting"]["unresolved_reserved_tokens"], 132)

    def test_send_guard_is_rechecked_after_credentials_and_releases_unsent(self):
        report = self.run_driver(guard=lambda stage, ordinal: stage == "preinvoke")
        self.assertEqual(report["stop_code"], "guard-refused")
        self.assertEqual(self.helper.credential.resolutions, 1)
        self.assertEqual(self.transport.requests, [])
        self.assertEqual(report["accounting"]["durable_send_intents"], 0)
        self.assertEqual(report["accounting"]["unresolved_reserved_tokens"], 0)

    def test_entry_storage_failure_preserves_numeric_receipt_and_held_intent(self):
        with patch.object(ConformanceUsageJournal, "record_http_entry", side_effect=OSError("synthetic storage failure")):
            report = self.run_driver()
        self.assertEqual(report["stop_code"], "accounting-failed")
        self.assertEqual(report["actual_counts"]["responses_received"], 1)
        self.assertEqual(report["calls"][0]["input_tokens"], 5)
        self.assertEqual(report["calls"][0]["output_tokens"], 2)
        self.assertEqual(report["accounting"]["unresolved_reserved_tokens"], 132)
        self.assertEqual(report["accounting"]["http_entry_observations"], 0)
        self.assertEqual(len(self.transport.requests), 1)

    def test_snapshot_failure_has_null_accounting_not_fabricated_zero(self):
        with patch.object(ConformanceUsageJournal, "snapshot", side_effect=OSError("synthetic private storage failure")):
            report = self.run_driver()
        self.assertEqual(report["stop_code"], "accounting-failed")
        self.assertIsNone(report["accounting"])
        self.assertEqual(report["actual_counts"]["provider_invocations"], 0)
        self.assertEqual(self.helper.credential.resolutions, 0)

    def test_failed_response_money_fields_do_not_erase_numeric_token_receipt(self):
        self.transport.bad_money = True
        report = self.run_driver()
        self.assertEqual(report["accounting"]["known_total_tokens"], 7)
        self.assertEqual(report["accounting"]["cost"]["status"], "unknown")
        self.assertNotIn("synthetic private money detail", json.dumps(report))
        self.assertEqual(len(self.transport.requests), 1)

    def test_initial_clock_exception_returns_fixed_redacted_block(self):
        def clock():
            raise OSError("synthetic private clock detail")
        report = self.run_driver(clock=clock)
        self.assertEqual(report["stop_code"], "deadline-exhausted")
        self.assertNotIn("synthetic private clock detail", json.dumps(report))
        self.assertEqual(self.helper.credential.resolutions, 0)

    def test_final_snapshot_failure_preserves_three_received_calls_and_blocks(self):
        original = self.journal.snapshot
        def snapshot():
            value = original()
            if value["attempts"] and value["attempts"][-1]["status"] == "completed":
                raise OSError("synthetic private final snapshot detail")
            return value
        with patch.object(self.journal, "snapshot", side_effect=snapshot):
            report = self.run_driver()
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["stop_code"], "accounting-failed")
        self.assertIsNone(report["accounting"])
        self.assertEqual(report["actual_counts"], {"provider_invocations": 3, "http_entry_observations": 3,
                                                 "tool_executions": 1, "responses_received": 3})
        self.assertEqual(len(report["calls"]), 3)
        self.assertEqual(sum(call["input_tokens"] + call["output_tokens"] for call in report["calls"]), 21)
        self.assertNotIn("synthetic private final snapshot detail", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
