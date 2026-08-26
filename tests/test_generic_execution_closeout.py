import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    CloseoutPin,
    GenericCloseoutValidationError,
    build_execution_core_gate,
    build_generic_execution_receipt,
    execute_frozen_view,
    load_resolved_execution_view,
    load_runtime_bundle,
    validate_generic_execution_receipt,
)
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt
from research_workbench.observability.trace import AgentTraceRecorder
from research_workbench.validation import SchemaCatalog
from tests import test_execution_host as host_fixtures
from tests import test_execution_view as view_fixtures
from tests import test_runtime_bundle as bundle_fixtures


ROOT = Path(__file__).resolve().parents[1]


class GenericExecutionCloseoutTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, document: object) -> CloseoutPin:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        return CloseoutPin(relative, hash_file(path))

    def _direct_tool_bundle(self, root: Path):
        bundle_helper = bundle_fixtures.RuntimeBundleTests(methodName="runTest")
        manifest_path = bundle_helper._build_bundle(root)
        evidence = load_document(root / "bundle/conformance.yaml")
        evidence["implementation_ref"] = "runtime-direct-tool-contract-check"
        evidence_hash = self._write(root, "bundle/conformance.yaml", evidence).sha256
        supply = load_document(root / "bundle/supply.yaml")
        supply["supply_identity"] = {
            "supply_kind": "tool",
            "implementation_ref": "runtime-direct-tool-contract-check",
            "implementation_version": "1.0.0",
            "content_hash": "2" * 64,
            "components": [
                {
                    "component_kind": "tool",
                    "component_ref": "bounded-contract-check-tool",
                    "version": "1.0.0",
                    "content_hash": "2" * 64,
                }
            ],
        }
        supply["conformance_evidence"][0]["artifact_ref"]["sha256"] = evidence_hash
        supply_hash = self._write(root, "bundle/supply.yaml", supply).sha256
        resolution = load_document(root / "bundle/resolution.yaml")
        resolution["candidate_supply_report_refs"][0]["content_hash"] = "sha256:" + supply_hash
        resolution_hash = self._write(root, "bundle/resolution.yaml", resolution).sha256
        snapshot = load_document(root / "bundle/snapshot.yaml")
        snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
        snapshot["selected_supply_report_ref"]["content_hash"] = "sha256:" + supply_hash
        snapshot["supply_identity"] = copy.deepcopy(supply["supply_identity"])
        snapshot["conformance_evidence_refs"][0]["sha256"] = evidence_hash
        snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot).sha256
        manifest = load_document(manifest_path)
        replacements = {
            "bundle/conformance.yaml": evidence_hash,
            "bundle/supply.yaml": supply_hash,
            "bundle/resolution.yaml": resolution_hash,
            "bundle/snapshot.yaml": snapshot_hash,
        }
        manifest["entrypoint"]["sha256"] = snapshot_hash
        for item in manifest["documents"]:
            if item["path"] in replacements:
                item["sha256"] = replacements[item["path"]]
        self._write(root, "bundle/manifest.yaml", manifest)
        return load_runtime_bundle(
            "bundle/manifest.yaml", project_root=root, schema_root=ROOT / "schemas"
        )

    def _bundle_and_view(self, root: Path, path_kind: str):
        helper = view_fixtures.ExecutionViewTests(methodName="runTest")
        if path_kind == "no-skill":
            bundle, inputs = helper._build(root)
        else:
            bundle = self._direct_tool_bundle(root)
            inputs = helper._inputs(root)
        view = helper._produce(root, bundle, inputs)
        view_pin = self._write(root, "view/resolved-view.yaml", view)
        validated_view = load_resolved_execution_view(
            view_pin.path,
            expected_sha256=view_pin.sha256,
            bundle=bundle,
            schema_root=ROOT / "schemas",
        )
        return bundle, validated_view

    def _validated_receipt(self, root: Path, path_kind: str):
        bundle, view = self._bundle_and_view(root, path_kind)
        driver = host_fixtures.RecordingDriver(root, view.document["binding"])
        host_report = execute_frozen_view(
            view,
            bundle,
            driver,
            report_id=f"HOST-{path_kind}",
            attempt_id=f"ATTEMPT-{path_kind}",
            started_at="2026-08-26T00:00:01Z",
            completed_at="2026-08-26T00:00:02Z",
            schema_root=ROOT / "schemas",
        )
        host_pin = self._write(root, "closeout/host-report.yaml", host_report)

        task = next(
            host_fixtures.plain(document)
            for path, document in bundle.documents.items()
            if path.name == "task.yaml"
        )
        trace_dir = root / "closeout/trace"
        recorder = AgentTraceRecorder(
            trace_dir,
            task_id=task["task_id"],
            task_revision=task.get("revision", 1),
            attempt_id=host_report["attempt_id"],
            task_snapshot=task,
            accountable_owner="M11 bounded test owner",
            actor_id="runtime-host",
            runtime_identity=view.document["binding"]["runtime"]["ref"],
            provider=view.document["binding"]["provider"]["ref"],
            read_allowlist=[],
            write_scope=[
                str(item).rstrip("/") + "/**"
                for item in view.document["effective_constraints"]["permissions"]["allowed_roots"]
            ],
            tool_allowlist=["bounded-contract-check-tool"] if path_kind == "direct-tool" else [],
            created_at="2026-08-26T00:00:00Z",
        )
        if path_kind == "direct-tool":
            recorder.record_tool_call(
                operation_id="contract-check",
                tool_name="bounded-contract-check-tool",
                status="completed",
                arguments={},
                result={"status": "pass"},
            )
        recorder.record_attempt_status("completed", reason="bounded Host report completed")
        recorder.seal()
        trace_pin = CloseoutPin(
            trace_dir.joinpath("INDEX.yaml").relative_to(root).as_posix(),
            hash_file(trace_dir / "INDEX.yaml"),
        )

        checker = root / "closeout/checker.py"
        checker.write_text("# deterministic bounded execution checker\n", encoding="utf-8")
        subjects = [
            {"path": host_pin.path, "sha256": host_pin.sha256},
            {"path": trace_pin.path, "sha256": trace_pin.sha256},
            *[
                {"path": item["path"], "sha256": item["sha256"]}
                for item in host_report["artifacts"]
            ],
        ]
        validation = {
            "schema_version": "0.1.0",
            "report_id": f"CHECK-{path_kind}",
            "checker": {
                "checker_id": "m11-generic-execution-checker",
                "version": "1.0.0",
                "source_ref": {
                    "path": "closeout/checker.py",
                    "sha256": hash_file(checker),
                },
            },
            "subject_refs": subjects,
            "status": "pass",
            "checks": [
                {
                    "code": "execution-contract-closed",
                    "status": "pass",
                    "detail": "Host facts, Trace and artifacts form the exact bounded subject set.",
                }
            ],
            "scope": "execution-contract-only",
            "limitations": ["This check does not assess scientific validity or Claim acceptance."],
        }
        validation_pin = self._write(root, "closeout/validation.yaml", validation)
        receipt = build_generic_execution_receipt(
            view,
            bundle,
            host_report=host_pin,
            trace_index=trace_pin,
            validations=(validation_pin,),
            receipt_id=f"RECEIPT-{path_kind}",
            schema_root=ROOT / "schemas",
        )
        receipt_pin = self._write(root, "closeout/receipt.yaml", receipt)
        validated = validate_generic_execution_receipt(
            receipt_pin.path,
            expected_sha256=receipt_pin.sha256,
            bundle=bundle,
            schema_root=ROOT / "schemas",
        )
        return bundle, validated

    def test_no_skill_and_direct_tool_close_and_form_core_gate_without_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, no_skill = self._validated_receipt(base / "no-skill", "no-skill")
            _, direct_tool = self._validated_receipt(base / "direct-tool", "direct-tool")
            gate = build_execution_core_gate(
                no_skill,
                direct_tool,
                gate_id="M11-CORE-GATE-001",
                schema_root=ROOT / "schemas",
            )
            self.assertEqual(
                [], SchemaCatalog(ROOT / "schemas").validate("execution_core_gate", gate)
            )
            self.assertEqual({"no-skill", "direct-tool"}, {item["path_kind"] for item in gate["paths"]})
            for receipt in (no_skill.document, direct_tool.document):
                self.assertEqual("execution-only", receipt["completion_claim"])
                self.assertEqual("absent", receipt["boundaries"]["skill_assignment"])
                self.assertNotIn("skill_assignment_ref", receipt)
                self.assertFalse(receipt["boundaries"]["claim_effect"])
                self.assertFalse(receipt["boundaries"]["human_decision"])

    def test_trace_or_validation_tamper_blocks_file_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, receipt = self._validated_receipt(root, "no-skill")
            validation_path = root / receipt.document["validation_refs"][0]["path"]
            validation_path.write_bytes(validation_path.read_bytes() + b"\n# drift\n")
            with self.assertRaises(GenericCloseoutValidationError):
                validate_generic_execution_receipt(
                    receipt.receipt_path,
                    expected_sha256=receipt.receipt_sha256,
                    bundle=bundle,
                    schema_root=ROOT / "schemas",
                )

    def test_generic_receipt_rejects_skill_claim_human_and_recovery_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, receipt = self._validated_receipt(root, "no-skill")
            catalog = SchemaCatalog(ROOT / "schemas")
            for field, value in (
                ("skill_assignment_ref", "fake-assignment.yaml"),
                ("claim_status", "accepted"),
                ("human_approved", True),
                ("recovery_ref", "resume.yaml"),
            ):
                mutated = copy.deepcopy(receipt.document)
                mutated[field] = value
                self.assertTrue(catalog.validate("generic_execution_receipt", mutated))

    def test_legacy_execution_receipt_schema_and_model_remain_unchanged(self) -> None:
        path = ROOT / "examples/observability/execution-evidence-contract.yaml"
        document = load_document(path)
        self.assertEqual([], SchemaCatalog(ROOT / "schemas").validate("execution_receipt", document))
        parsed = ExecutionReceipt.from_mapping(document)
        self.assertTrue(parsed.skill_assignment_ref)


if __name__ == "__main__":
    unittest.main()
