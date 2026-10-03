"""Selected graph/body driving and cold report concordance; synthetic HTTPS only."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.conformance_body import ConformanceBodyPolicy
from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.conformance_transport import GuardedConformanceTransport
from research_workbench.adapters.models.http import UrllibTransport
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2
from research_workbench.adapters.models.profile_conformance import run_profile_conformance
from research_workbench.adapters.models.profile_conformance_report import (
    verify_profile_conformance_report, write_profile_conformance_report,
)
from research_workbench.adapters.models.provider_binding import stage_provider_binding
from tests import test_configured_provider as helpers
from tests.test_provider_binding_graph import _components

ROOT = Path(__file__).resolve().parents[1]


def _contract_monotonic():
    # These contract tests measure source/config/body binding, not CI host CPU
    # time. Advancing deadline and timeout failures have dedicated transport tests.
    return 0.0


class SyntheticOpener:
    def __init__(self):
        self.bodies = []

    def open(self, request, *, timeout):
        self.bodies.append(json.loads(request.data))
        ordinal = len(self.bodies)
        output = [{"type": "function_call", "status": "completed", "call_id": "synthetic-call-id",
                   "name": "add_ints", "arguments": '{"a":3,"b":4}'}] if ordinal == 1 else [
            {"type": "message", "role": "assistant", "status": "completed", "content": [
                {"type": "output_text", "text": "7" if ordinal == 2 else '{"sum":7}'}]}]
        raw = json.dumps({"id": "synthetic-only", "model": "deepseek-flash", "status": "completed",
            "usage": {"input_tokens": 5, "output_tokens": 2}, "output": output}).encode()
        response = io.BytesIO(raw)
        response.status = 200
        response.headers = {}
        return response


class ProfileConformanceBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = tempfile.TemporaryDirectory(prefix="rwb-bound-driver-template-")
        cls.addClassCleanup(cls.template.cleanup)
        cls.template_root = Path(cls.template.name)
        helper = helpers.ConfiguredProviderTests()
        helper.setUp()
        try:
            original = helper.build("deepseek")
            profile_path = cls.template_root / "profile.json"
            profile_path.write_bytes((helper.root / "profile.json").read_bytes())
            config = dict(original.resolved_config)
            config.pop("model")
            config["model_selector"] = {"kind": "literal", "value": original.model}
            config["credential_source"] = {"kind": "environment", "name": "RWB_BINDING_SYNTHETIC_KEY"}
            cls.config = ProviderAdapterConfigV2.from_mapping(config)
            journal = ConformanceUsageJournal.create(cls.template_root / "preparation.sqlite",
                namespace=str(uuid4()), total_token_limit=1000)
            try:
                transport = UrllibTransport(max_response_bytes=config["transport"]["max_response_bytes"])
                bounded = GuardedConformanceTransport(transport, journal, lambda stage, ordinal: True,
                    deadline=120, clock=_contract_monotonic,
                    body_policy=ConformanceBodyPolicy(max_output_tokens=32))
                provider = build_profile_provider(cls.config, root=cls.template_root,
                    transport=bounded, credential=_components().SyntheticCredential())
                cls.reference = stage_provider_binding(provider, root=cls.template_root, destination="binding",
                    source_closure=True, include_conformance=True)
            finally:
                journal.close()
        finally:
            helper.doCleanups()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rwb-bound-driver-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(self.template_root / "binding", self.root / "binding")
        shutil.copyfile(self.template_root / "profile.json", self.root / "profile.json")
        self.journal = ConformanceUsageJournal.create(self.root / "usage.sqlite",
            namespace=str(uuid4()), total_token_limit=1000)
        self.addCleanup(self.journal.close)
        self.credential = _components().SyntheticCredential()
        self.transport = UrllibTransport(max_response_bytes=self.config.to_mapping()["transport"]["max_response_bytes"])
        self.opener = SyntheticOpener()

    def run_driver(self, **overrides):
        options = dict(root=self.root, journal=self.journal, transport=self.transport,
            credential=self.credential, guard=lambda stage, ordinal: True,
            input_upper_tokens=(100, 100, 100), max_output_tokens=32, max_seconds=120,
            body_policy=ConformanceBodyPolicy(max_output_tokens=32), binding_manifest_ref=self.reference,
            clock=_contract_monotonic)
        options.update(overrides)
        with patch("urllib.request.build_opener", return_value=self.opener):
            return run_profile_conformance(self.config, **options)

    def assert_unsent(self, report):
        self.assertEqual(report["stop_code"], "provider-construction-refused")
        self.assertEqual(report["report_version"], "1.0.0")
        self.assertEqual(self.credential.resolutions, 0)
        self.assertEqual(self.opener.bodies, [])
        self.assertEqual(self.journal.snapshot()["attempts"], [])

    def test_actual_urllib_three_call_driver_and_cold_report_match_selected_graph(self):
        report = self.run_driver()
        self.assertEqual(report["stop_code"], "completed")
        self.assertEqual(report["report_version"], "1.1.0")
        self.assertEqual(self.credential.resolutions, 3)
        self.assertEqual(len(self.opener.bodies), 3)
        self.assertEqual(report["binding"]["input_upper_tokens"], [100, 100, 100])
        self.assertEqual(report["actual_counts"]["tool_executions"], 1)
        self.assertFalse(report["live_qualified"])
        self.assertFalse(report["remote_strict_claim"])
        output = self.root / "report.json"
        write_profile_conformance_report(report, output, root=self.root, schema_root=ROOT / "schemas")
        self.assertEqual(json.loads(output.read_bytes()), report)
        for key in ("config_ref", "implementation_closure_ref", "source_sha256", "policy_output", "input_bound"):
            altered = copy.deepcopy(report)
            if key == "config_ref":
                altered[key]["sha256"] = "0" * 64
            elif key == "implementation_closure_ref":
                altered["binding"][key]["sha256"] = "0" * 64
            elif key == "source_sha256":
                altered["source_refs"][0][key] = "0" * 64
            elif key == "policy_output":
                altered["binding"]["body_policy"]["max_output_tokens"] = 33
            else:
                altered["binding"]["input_upper_tokens"][0] = 101
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_profile_conformance_report(altered, root=self.root, schema_root=ROOT / "schemas")

    def test_bad_manifest_ref_never_reaches_credential_or_attempt(self):
        bad = dict(self.reference, sha256="0" * 64)
        self.assert_unsent(self.run_driver(binding_manifest_ref=bad))

    def test_missing_body_or_custom_delegate_never_uses_selected_manifest(self):
        self.assert_unsent(self.run_driver(body_policy=None))
        self.assert_unsent(self.run_driver(transport=_components().SyntheticTransport()))

    def test_configuration_drift_cannot_reuse_valid_manifest(self):
        config = self.config.to_mapping()
        config["transport"]["timeout_seconds"] += 1
        with patch.object(self, "config", ProviderAdapterConfigV2.from_mapping(config)):
            self.assert_unsent(self.run_driver())

    def test_post_send_guard_helper_drift_releases_unsent_and_preserves_cold_receipt(self):
        from research_workbench.adapters.models import wire_codecs, profile_conformance as driver
        ref_mutation = patch.object(driver, "_source_refs", side_effect=OSError("synthetic source unavailable"))
        mutation = patch.object(wire_codecs, "_usage", lambda *args: None)
        mutated = False
        def guard(stage, ordinal):
            nonlocal mutated
            if stage == "send" and not mutated:
                mutation.start()
                ref_mutation.start()
                mutated = True
            return True
        try:
            report = self.run_driver(guard=guard)
            self.assertEqual(report["report_version"], "1.1.0")
            self.assertEqual(report["stop_code"], "guard-refused")
            self.assertEqual(self.credential.resolutions, 1)
            self.assertEqual(self.opener.bodies, [])
            self.assertEqual(report["accounting"]["calls"][0]["accounting_status"], "released-before-send")
            # Cold replay derives archived code; it does not execute the mutated helper.
            self.assertEqual(verify_profile_conformance_report(report, root=self.root, schema_root=ROOT / "schemas"), report)
        finally:
            if mutated:
                ref_mutation.stop()
                mutation.stop()

    def test_fresh_second_attempt_uses_its_own_bounds_without_borrowing_failed_history(self):
        failed = self.run_driver(guard=lambda stage, ordinal: False, input_upper_tokens=(90, 90, 90))
        self.assertEqual(failed["stop_code"], "guard-refused")
        self.assertEqual(failed["binding"]["attempt_ordinal"], 1)
        self.assertEqual(verify_profile_conformance_report(failed, root=self.root, schema_root=ROOT / "schemas"), failed)
        report = self.run_driver(repair_refreeze_confirmed=True)
        self.assertEqual(report["stop_code"], "completed")
        self.assertEqual(report["binding"]["attempt_ordinal"], 2)
        self.assertEqual(verify_profile_conformance_report(report, root=self.root, schema_root=ROOT / "schemas"), report)
        altered = copy.deepcopy(report)
        altered["binding"]["attempt_ordinal"] = 1
        with self.assertRaises(ValueError):
            verify_profile_conformance_report(altered, root=self.root, schema_root=ROOT / "schemas")

    def test_archived_graph_drift_blocks_before_credentials(self):
        manifest = json.loads((self.root / self.reference["path"]).read_bytes())
        graph = json.loads((self.root / manifest["implementation_closure_ref"]["path"]).read_bytes())
        source = next(iter(graph["modules"].values()))["source_ref"]
        path = self.root / source["path"]
        path.write_bytes(path.read_bytes() + b"\n# synthetic archive drift\n")
        self.assert_unsent(self.run_driver())


if __name__ == "__main__":
    unittest.main()
