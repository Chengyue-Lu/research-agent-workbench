import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    CloseoutPin,
    GenericCloseoutValidationError,
    ExecutionDriverResult,
    ExecutionViewValidationError,
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

    def _validated_receipt(
        self,
        root: Path,
        path_kind: str,
        lifecycle: str = "completed",
        *,
        include_execution_fact: bool = True,
    ):
        bundle, view = self._bundle_and_view(root, path_kind)
        driver = host_fixtures.RecordingDriver(root, view.document["binding"])
        if path_kind == "direct-tool":
            driver = host_fixtures.RecordingDriver(
                root,
                view.document["binding"],
                tool_refs=("bounded-contract-check-tool",),
            )
        if lifecycle == "blocked":
            requested = host_fixtures.plain(view.document["binding"])
            requested["model"]["ref"] = "preflight-mismatched-model"
            driver = host_fixtures.RecordingDriver(root, requested)
        elif lifecycle == "failed":
            actual = host_fixtures.plain(view.document["binding"])
            actual["provider"]["ref"] = "observed-drift-provider"
            driver = host_fixtures.RecordingDriver(
                root,
                view.document["binding"],
                result=ExecutionDriverResult(
                    status="completed",
                    actual_binding=actual,
                    actual_supply_report_ref=(
                        "supply-no-skill-contract-check@1.0.0"
                    ),
                    facts_complete=True,
                ),
            )
        host_report = execute_frozen_view(
            view,
            driver,
            report_id=f"HOST-{path_kind}",
            attempt_id=f"ATTEMPT-{path_kind}",
            clock=host_fixtures.SequenceClock(
                "2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z"
            ),
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
            provider=(
                host_report.get("actual_binding")
                or host_report["requested_binding"]
            )["provider"]["ref"],
            read_allowlist=[],
            write_scope=[
                str(item).rstrip("/") + "/**"
                for item in view.document["effective_constraints"]["permissions"]["allowed_roots"]
            ],
            tool_allowlist=["bounded-contract-check-tool"] if path_kind == "direct-tool" else [],
            created_at="2026-08-26T00:00:00Z",
        )
        recorder.record_decision_snapshot(
            "execution-scope-binding",
            {
                "schema_version": "0.1.0",
                "record_kind": "execution-scope-binding",
                "view_ref": host_report["view_ref"],
                "execution_scope": host_report["execution_scope"],
            },
        )
        if host_report["execution_phase"] == "post-call" and include_execution_fact:
            recorder.record_execution_fact(
                fact_id=f"EXECUTION-FACT-{path_kind}",
                view_ref=host_report["view_ref"],
                actual_binding=host_report["actual_binding"],
                actual_supply_report_ref=host_report["actual_supply_report_ref"],
            )
        if path_kind == "direct-tool" and lifecycle == "completed":
            recorder.record_tool_call(
                operation_id="contract-check",
                tool_name="bounded-contract-check-tool",
                status="completed",
                arguments={},
                result={"status": "pass"},
            )
        recorder.record_attempt_status(
            host_report["status"], reason=f"bounded Host report {host_report['status']}"
        )
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

    def test_completed_failed_and_preflight_blocked_lifecycle_replay_end_to_end(self) -> None:
        for lifecycle in ("completed", "failed", "blocked"):
            with self.subTest(lifecycle=lifecycle), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _, receipt = self._validated_receipt(root, "no-skill", lifecycle)
                self.assertEqual(lifecycle, receipt.document["status"])
                host = load_document(root / receipt.document["host_report_ref"]["path"])
                if lifecycle == "completed":
                    self.assertEqual("post-call", host["execution_phase"])
                    self.assertEqual(
                        "action-capability-slice-only",
                        receipt.document["completion_claim"],
                    )
                elif lifecycle == "failed":
                    self.assertEqual("post-call", host["execution_phase"])
                    self.assertEqual("HOST-ACTUAL-BINDING-DRIFT", host["diagnostic"]["code"])
                    self.assertNotEqual(host["requested_binding"], host["actual_binding"])
                    self.assertEqual("none", receipt.document["completion_claim"])
                else:
                    self.assertEqual("preflight-blocked", host["execution_phase"])
                    self.assertNotIn("actual_binding", host)
                    self.assertNotIn("actual_supply_report_ref", host)
                    self.assertEqual("none", receipt.document["completion_claim"])

    def test_failed_post_call_receipt_requires_hash_pinned_trace_execution_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(GenericCloseoutValidationError) as raised:
                self._validated_receipt(
                    Path(temp),
                    "no-skill",
                    "failed",
                    include_execution_fact=False,
                )
            self.assertIn("typed hash-pinned Trace actual execution fact", str(raised.exception))

    def test_failed_receipt_trace_fact_covers_every_binding_component_and_supply(self) -> None:
        for component in ("provider", "adapter", "model", "runtime", "host", "supply"):
            with self.subTest(component=component), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                bundle, validated = self._validated_receipt(root, "no-skill", "failed")
                receipt = copy.deepcopy(validated.document)
                host_path = receipt["host_report_ref"]["path"]
                host = load_document(root / host_path)
                if component == "supply":
                    host["actual_supply_report_ref"] = "untraced-supply@9.9.9"
                else:
                    host["actual_binding"][component]["ref"] = f"untraced-{component}"
                rewritten = self._rewrite_closeout_subject(
                    root, receipt, host_path, host
                )
                with self.assertRaises(GenericCloseoutValidationError) as raised:
                    validate_generic_execution_receipt(
                        rewritten.path,
                        expected_sha256=rewritten.sha256,
                        bundle=bundle,
                        schema_root=ROOT / "schemas",
                    )
                self.assertIn(
                    "Trace actual execution fact does not corroborate Host binding and Supply",
                    str(raised.exception),
                )

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
                self.assertEqual(
                    "action-capability-slice-only", receipt["completion_claim"]
                )
                self.assertFalse(receipt["boundaries"]["task_completion"])
                self.assertEqual("absent", receipt["boundaries"]["skill_assignment"])
                self.assertNotIn("skill_assignment_ref", receipt)
                self.assertFalse(receipt["boundaries"]["claim_effect"])
                self.assertFalse(receipt["boundaries"]["human_decision"])

    def test_agent_profile_tool_allowlist_applies_to_actual_tool_supply(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = self._direct_tool_bundle(root)
            helper = view_fixtures.ExecutionViewTests(methodName="runTest")
            inputs = helper._inputs(root)
            profile_path = root / inputs["agent_profile"].path
            profile = load_document(profile_path)
            profile["allowed_tool_capabilities"] = []
            inputs["agent_profile"] = helper._write(
                root, inputs["agent_profile"].path, profile
            )
            with self.assertRaises(ExecutionViewValidationError) as raised:
                helper._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-PROFILE-TOOL-CAPABILITY", str(raised.exception))

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

    def _rewrite_closeout_subject(
        self,
        root: Path,
        receipt_document: dict,
        subject_path: str,
        subject_document: dict,
    ) -> CloseoutPin:
        subject_pin = self._write(root, subject_path, subject_document)
        validation_ref = receipt_document["validation_refs"][0]
        validation = load_document(root / validation_ref["path"])
        for item in validation["subject_refs"]:
            if item["path"] == subject_path:
                item["sha256"] = subject_pin.sha256
        validation_pin = self._write(root, validation_ref["path"], validation)
        receipt_document["host_report_ref"]["sha256"] = subject_pin.sha256
        receipt_document["validation_refs"][0]["sha256"] = validation_pin.sha256
        return self._write(root, "closeout/receipt-rewritten.yaml", receipt_document)

    def test_receipt_replay_rejects_rehashed_host_binding_and_supply_substitution(self) -> None:
        cases = (
            lambda host: host["actual_binding"]["provider"].update({"ref": "substituted"}),
            lambda host: host.update({"actual_supply_report_ref": "supply-substituted@1.0.0"}),
        )
        for mutate in cases:
            with self.subTest(mutation=mutate.__code__.co_firstlineno):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    bundle, validated = self._validated_receipt(root, "no-skill")
                    receipt = copy.deepcopy(validated.document)
                    host_path = receipt["host_report_ref"]["path"]
                    host = load_document(root / host_path)
                    mutate(host)
                    self.assertEqual(
                        [],
                        SchemaCatalog(ROOT / "schemas").validate(
                            "execution_host_report", host
                        ),
                    )
                    rewritten = self._rewrite_closeout_subject(
                        root, receipt, host_path, host
                    )
                    with self.assertRaises(GenericCloseoutValidationError):
                        validate_generic_execution_receipt(
                            rewritten.path,
                            expected_sha256=rewritten.sha256,
                            bundle=bundle,
                            schema_root=ROOT / "schemas",
                        )

    def test_host_tool_fact_without_trace_operation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, validated = self._validated_receipt(root, "no-skill")
            receipt = copy.deepcopy(validated.document)
            host_path = receipt["host_report_ref"]["path"]
            host = load_document(root / host_path)
            host["actual_facts"]["tool_invocations"] = 1
            host["actual_facts"]["tool_refs"] = ["untraced-tool"]
            self.assertEqual(
                [],
                SchemaCatalog(ROOT / "schemas").validate("execution_host_report", host),
            )
            rewritten = self._rewrite_closeout_subject(root, receipt, host_path, host)
            with self.assertRaises(GenericCloseoutValidationError) as raised:
                validate_generic_execution_receipt(
                    rewritten.path,
                    expected_sha256=rewritten.sha256,
                    bundle=bundle,
                    schema_root=ROOT / "schemas",
                )
            self.assertIn("tool invocation count", str(raised.exception))

    def test_host_provider_count_without_trace_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, validated = self._validated_receipt(root, "no-skill")
            receipt = copy.deepcopy(validated.document)
            host_path = receipt["host_report_ref"]["path"]
            host = load_document(root / host_path)
            host["actual_facts"]["provider_invocations"] = 1
            rewritten = self._rewrite_closeout_subject(root, receipt, host_path, host)
            with self.assertRaises(GenericCloseoutValidationError) as raised:
                validate_generic_execution_receipt(
                    rewritten.path,
                    expected_sha256=rewritten.sha256,
                    bundle=bundle,
                    schema_root=ROOT / "schemas",
                )
            self.assertIn("provider invocation count", str(raised.exception))

    def test_trace_provider_and_runtime_actor_identity_must_match_host_binding(self) -> None:
        actor_types = ("model-provider", "runtime-adapter")
        for actor_type in actor_types:
            with self.subTest(actor_type=actor_type):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    bundle, validated = self._validated_receipt(root, "no-skill")
                    receipt = copy.deepcopy(validated.document)
                    trace_path = receipt["trace_ref"]["path"]
                    trace = load_document(root / trace_path)
                    actors_relative = trace["actors_ref"]["path"]
                    actors_path = (
                        (root / trace_path).parent / actors_relative
                    ).relative_to(root).as_posix()
                    actors = load_document(root / actors_path)
                    actor = next(
                        item for item in actors["actors"] if item["actor_type"] == actor_type
                    )
                    actor["runtime_identity"] = "substituted-runtime-identity"
                    actors_pin = self._write(root, actors_path, actors)
                    trace["actors_ref"]["sha256"] = actors_pin.sha256
                    trace_pin = self._write(root, trace_path, trace)

                    validation_ref = receipt["validation_refs"][0]
                    validation = load_document(root / validation_ref["path"])
                    next(
                        item
                        for item in validation["subject_refs"]
                        if item["path"] == trace_path
                    )["sha256"] = trace_pin.sha256
                    validation_pin = self._write(root, validation_ref["path"], validation)
                    receipt["trace_ref"]["sha256"] = trace_pin.sha256
                    receipt["validation_refs"][0]["sha256"] = validation_pin.sha256
                    rewritten = self._write(root, "closeout/receipt-rewritten.yaml", receipt)

                    with self.assertRaises(GenericCloseoutValidationError) as raised:
                        validate_generic_execution_receipt(
                            rewritten.path,
                            expected_sha256=rewritten.sha256,
                            bundle=bundle,
                            schema_root=ROOT / "schemas",
                        )
                    self.assertIn("actor does not equal Host actual", str(raised.exception))

    def test_receipt_schema_distinguishes_completed_from_failed_or_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, validated = self._validated_receipt(root, "no-skill")
            catalog = SchemaCatalog(ROOT / "schemas")
            for status in ("failed", "blocked"):
                document = copy.deepcopy(validated.document)
                document["status"] = status
                document["completion_claim"] = "none"
                document["artifact_refs"] = []
                self.assertEqual([], catalog.validate("generic_execution_receipt", document))
            invalid = copy.deepcopy(validated.document)
            invalid["status"] = "failed"
            self.assertTrue(catalog.validate("generic_execution_receipt", invalid))

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
