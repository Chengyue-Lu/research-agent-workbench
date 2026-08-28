from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
import tempfile
import unittest
from unittest import mock

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.execution import execution_view as view_module
from research_workbench.execution import generic_closeout as closeout_module
from research_workbench.execution import host as host_module
from research_workbench.execution import runtime_bundle as bundle_module
from research_workbench.observability import trace as trace_module
from research_workbench.io import load_document
from tests.test_runtime_bundle import RuntimeBundleTests


class _Catalog:
    def __init__(self, *, errors: bool = False) -> None:
        self.errors = errors

    def validate(self, kind: str, document: object) -> list[SimpleNamespace]:
        if self.errors:
            return [SimpleNamespace(pointer="/", message=f"bad {kind}")]
        return []


class ExecutionViewHelperTests(unittest.TestCase):
    def test_hash_timestamp_and_permission_parsers_fail_closed(self) -> None:
        digest = "a" * 64
        self.assertEqual(digest, view_module._normalized_hash("sha256:" + digest.upper()))
        for value in (None, "short", "z" * 64):
            self.assertIsNone(view_module._normalized_hash(value))
        for value in (None, "not-a-time", "2026-01-01T00:00:00"):
            with self.subTest(timestamp=value), self.assertRaises(ValueError):
                view_module._timestamp(value, "observed_at")

        self.assertTrue(view_module._normalized_external_write("allowed"))
        self.assertFalse(view_module._normalized_external_write("forbidden"))
        with self.assertRaises(ValueError):
            view_module._normalized_external_write("sometimes")
        for value in (None, {"filesystem": "bad", "network": "forbidden"}, {
            "filesystem": "read-only", "network": "forbidden", "allowed_roots": "root"
        }):
            with self.subTest(permissions=value), self.assertRaises(ValueError):
                view_module._permission_source(value, "test")

    def test_manifest_and_pinned_input_edges_are_explicit(self) -> None:
        root = Path("C:/synthetic-root")
        entry = {"kind": "task_packet", "path": "task.yaml", "sha256": "a" * 64}
        bundle = SimpleNamespace(
            project_root=root,
            manifest_path=root / "manifest.yaml",
            manifest={"documents": [entry, dict(entry)]},
            documents={},
        )
        with self.assertRaises(view_module.ExecutionViewValidationError):
            view_module._manifest_entry(bundle, "task_packet")
        bundle.manifest = {"documents": []}
        with self.assertRaises(view_module.ExecutionViewValidationError):
            view_module._manifest_entry(bundle, "task_packet")
        bundle.manifest = {"documents": [entry]}
        with self.assertRaises(view_module.ExecutionViewValidationError):
            view_module._bundle_document(bundle, "task_packet")

        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            directory = project / "directory"
            directory.mkdir()
            missing = view_module.PinnedExecutionInput("missing.yaml", "0" * 64)
            escaped = view_module.PinnedExecutionInput("../outside.yaml", "0" * 64)
            directory_pin = view_module.PinnedExecutionInput("directory", "0" * 64)
            for pin in (missing, escaped, directory_pin):
                with self.subTest(pin=pin.path), self.assertRaises(
                    view_module.ExecutionViewValidationError
                ):
                    view_module._load_pinned_input(
                        project, pin, schema_kind="agent_profile", catalog=_Catalog()
                    )

            path = project / "input.yaml"
            content = b"value: true\n"
            path.write_bytes(content)
            pin = view_module.PinnedExecutionInput("input.yaml", hash_bytes(content))
            with self.assertRaises(view_module.ExecutionViewValidationError):
                view_module._load_pinned_input(
                    project,
                    replace(pin, sha256="0" * 64),
                    schema_kind="agent_profile",
                    catalog=_Catalog(),
                )
            with mock.patch.object(view_module, "load_document_bytes", side_effect=ValueError("bad")):
                with self.assertRaises(view_module.ExecutionViewValidationError):
                    view_module._load_pinned_input(
                        project, pin, schema_kind="agent_profile", catalog=_Catalog()
                    )
            with mock.patch.object(view_module, "load_document_bytes", return_value=[]):
                with self.assertRaises(view_module.ExecutionViewValidationError):
                    view_module._load_pinned_input(
                        project, pin, schema_kind="agent_profile", catalog=_Catalog()
                    )
            with mock.patch.object(view_module, "load_document_bytes", return_value={"value": True}):
                with self.assertRaises(view_module.ExecutionViewValidationError):
                    view_module._load_pinned_input(
                        project,
                        pin,
                        schema_kind="agent_profile",
                        catalog=_Catalog(errors=True),
                    )

    def test_intersections_cover_tightening_and_unsatisfied_supply(self) -> None:
        self.assertEqual([], view_module._intersect_roots((("a",), ())))
        self.assertEqual(
            ["work/output"],
            view_module._intersect_roots((("work",), ("work/output",))),
        )
        with self.assertRaises(ValueError):
            view_module._intersect_permissions((
                {"filesystem": "worktree-write", "network": "allowed", "external_write": True, "allowed_roots": ("a",)},
                {"filesystem": "workspace-write", "network": "search-and-fetch", "external_write": True, "allowed_roots": ("b",)},
            ))

        forbidden = view_module._intersect_data_egress((
            {"policy": "forbidden", "forbidden_payloads": ("secret",)},
            {"policy": "allowlisted-only", "allowed_payloads": ("public",)},
        ))
        self.assertEqual("forbidden", forbidden["policy"])
        self.assertEqual(
            "allowlisted-only",
            view_module._intersect_data_egress((
                {"policy": "allowlisted-only", "allowed_payloads": ("public", "secret"), "forbidden_payloads": ("secret",)},
                {"policy": "allowlisted-only", "allowed_payloads": ("public",)},
            ))["policy"],
        )
        self.assertEqual(
            "forbidden",
            view_module._intersect_data_egress((
                {"policy": "allowlisted-only", "allowed_payloads": ("a",)},
                {"policy": "allowlisted-only", "allowed_payloads": ("b",)},
            ))["policy"],
        )
        self.assertEqual(
            "none",
            view_module._intersect_side_effects((
                {"policy": "none"}, {"policy": "allowlisted-only", "allowed_effects": ("write",)}
            ))["policy"],
        )
        self.assertEqual(
            "allowlisted-only",
            view_module._intersect_side_effects((
                {"policy": "allowlisted-only", "allowed_effects": ("write", "notify")},
                {"policy": "allowlisted-only", "allowed_effects": ("write",)},
            ))["policy"],
        )
        with self.assertRaises(ValueError):
            view_module._intersect_budget(({}, {}))

        supply_permissions = {
            "filesystem": "read-only", "network": "search-and-fetch", "external_write": True
        }
        effective_permissions = {
            "filesystem": "read-only", "network": "forbidden", "external_write": False
        }
        neutral_egress = {"policy": "forbidden", "allowed_payloads": (), "forbidden_payloads": ()}
        neutral_effects = {"policy": "none", "allowed_effects": ()}
        with self.assertRaisesRegex(ValueError, "network"):
            view_module._require_supply_satisfiable(
                supply_permissions, neutral_egress, neutral_effects,
                effective_permissions, neutral_egress, neutral_effects,
            )
        effective_permissions["network"] = "search-and-fetch"
        with self.assertRaisesRegex(ValueError, "external-write"):
            view_module._require_supply_satisfiable(
                supply_permissions, neutral_egress, neutral_effects,
                effective_permissions, neutral_egress, neutral_effects,
            )

        compatible = {"filesystem": "read-only", "network": "forbidden", "external_write": False}
        supply_egress = {"policy": "allowlisted-only", "allowed_payloads": ("abstract",)}
        with self.assertRaisesRegex(ValueError, "data-egress"):
            view_module._require_supply_satisfiable(
                compatible, supply_egress, neutral_effects,
                compatible, neutral_egress, neutral_effects,
            )
        effective_egress = {
            "policy": "allowlisted-only", "allowed_payloads": ("abstract",),
            "forbidden_payloads": ("abstract",),
        }
        with self.assertRaisesRegex(ValueError, "forbidden set"):
            view_module._require_supply_satisfiable(
                compatible, supply_egress, neutral_effects,
                compatible, effective_egress, neutral_effects,
            )
        with self.assertRaisesRegex(ValueError, "side-effect"):
            view_module._require_supply_satisfiable(
                compatible, neutral_egress,
                {"policy": "allowlisted-only", "allowed_effects": ("write",)},
                compatible, neutral_egress, neutral_effects,
            )

        self.assertEqual({"artifact", "report"}, view_module._required_output_contracts((
            "artifact", {"contract": "report", "min_count": 2}
        )))
        with self.assertRaises(ValueError):
            view_module._required_output_contracts((42,))


class ExecutionHostHelperTests(unittest.TestCase):
    def _view(self) -> dict[str, object]:
        return {
            "binding": {"provider": {"ref": "provider-a"}},
            "selected_supply_report_ref": {"ref": "supply-a@1.0.0"},
            "effective_constraints": {
                "permissions": {"external_write": False},
                "data_egress": {"policy": "forbidden", "allowed_payloads": [], "forbidden_payloads": ["secret"]},
                "side_effects": {"policy": "none", "allowed_effects": []},
                "budget": {"max_turns": 1, "max_output_tokens": 10, "max_seconds": 2},
            },
        }

    def _result(self, **changes: object) -> host_module.ExecutionDriverResult:
        values = {
            "status": "completed",
            "actual_binding": {"provider": {"ref": "provider-a"}},
            "actual_supply_report_ref": "supply-a@1.0.0",
        }
        values.update(changes)
        return host_module.ExecutionDriverResult(**values)

    def test_clock_hash_and_output_helpers_are_closed(self) -> None:
        digest = "b" * 64
        self.assertEqual(digest, host_module._normalized_hash("sha256:" + digest))
        for value in (None, "short", "x" * 64):
            self.assertIsNone(host_module._normalized_hash(value))
        self.assertIsNotNone(host_module.SystemHostClock().now().tzinfo)
        for value in ("bad", "2026-01-01T00:00:00"):
            with self.assertRaises(host_module.ExecutionHostValidationError):
                host_module._timestamp(value, "clock")
        for observed in (None, datetime(2026, 1, 1)):
            with mock.patch.object(SimpleNamespace(now=lambda: observed), "now") as now:
                now.return_value = observed
                with self.assertRaises(host_module.ExecutionHostValidationError):
                    host_module._observe_time(SimpleNamespace(now=now), "clock")

        artifacts = ({"contract": "report"}, {"contract": "report"})
        self.assertTrue(host_module._required_outputs_satisfied(({"contract": "report", "min_count": 2},), artifacts))
        self.assertFalse(host_module._required_outputs_satisfied(({"contract": "report", "min_count": 3},), artifacts))
        self.assertFalse(host_module._required_outputs_satisfied((42,), artifacts))

    def test_artifact_validation_covers_permission_scope_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "outputs/result.txt"
            output.parent.mkdir()
            output.write_bytes(b"result")
            artifact = {"path": "outputs/result.txt", "sha256": hash_bytes(b"result")}
            self.assertEqual(
                "HOST-ARTIFACT-WRITE-FORBIDDEN",
                host_module._validate_artifacts(root, (artifact,), {"filesystem": "read-only"}),
            )
            permissions = {"filesystem": "worktree-write", "allowed_roots": ("outputs",)}
            self.assertIsNone(host_module._validate_artifacts(root, (artifact,), permissions))
            self.assertEqual(
                "HOST-ARTIFACT-MISSING",
                host_module._validate_artifacts(root, ({"path": "outputs/missing", "sha256": "0" * 64},), permissions),
            )
            self.assertEqual(
                "HOST-ARTIFACT-WRITE-SCOPE",
                host_module._validate_artifacts(root, (artifact,), {**permissions, "allowed_roots": ("other",)}),
            )
            self.assertEqual(
                "HOST-ARTIFACT-HASH-MISMATCH",
                host_module._validate_artifacts(root, ({**artifact, "sha256": "0" * 64},), permissions),
            )

    def test_driver_result_violation_matrix_is_fail_closed(self) -> None:
        cases = (
            (self._result(status="pending"), "HOST-DRIVER-STATUS-INVALID", 0),
            (self._result(actual_binding={}), "HOST-ACTUAL-BINDING-DRIFT", 0),
            (self._result(actual_supply_report_ref="other"), "HOST-ACTUAL-SUPPLY-DRIFT", 0),
            (self._result(facts_complete=False), "HOST-FACT-CAPTURE-GAP", 0),
            (self._result(capture_gaps=("missing",)), "HOST-FACT-CAPTURE-GAP", 0),
            (self._result(tool_refs=("tool",)), "HOST-TOOL-FACT-MISMATCH", 0),
            (self._result(tool_invocations=1), "HOST-TOOL-FACT-MISMATCH", 0),
            (self._result(external_write=True), "HOST-EXTERNAL-WRITE-VIOLATION", 0),
            (self._result(data_egress_payloads=("public",)), "HOST-DATA-EGRESS-VIOLATION", 0),
            (self._result(side_effects=("write",)), "HOST-SIDE-EFFECT-VIOLATION", 0),
            (self._result(turns=2), "HOST-BUDGET-VIOLATION", 0),
            (self._result(), "HOST-BUDGET-VIOLATION", 3),
        )
        for result, code, elapsed in cases:
            with self.subTest(code=code):
                self.assertEqual(
                    code,
                    host_module._result_violation(self._view(), result, host_elapsed_seconds=elapsed),
                )
        allowed = self._view()
        allowed["effective_constraints"]["data_egress"] = {
            "policy": "allowlisted-only", "allowed_payloads": ["public"], "forbidden_payloads": ["secret"]
        }
        allowed["effective_constraints"]["side_effects"] = {
            "policy": "allowlisted-only", "allowed_effects": ["notify"]
        }
        self.assertIsNone(host_module._result_violation(
            allowed,
            self._result(data_egress_payloads=("public",), side_effects=("notify",)),
            host_elapsed_seconds=1,
        ))
        self.assertEqual(
            "HOST-DATA-EGRESS-VIOLATION",
            host_module._result_violation(
                allowed, self._result(data_egress_payloads=("secret",)), host_elapsed_seconds=1
            ),
        )


class RuntimeBundleHelperTests(unittest.TestCase):
    def test_hash_ref_and_identity_helpers_reject_ambiguous_values(self) -> None:
        digest = "c" * 64
        self.assertEqual(digest, bundle_module._normalized_hash("sha256:" + digest))
        for value in (None, "short", "z" * 64):
            self.assertIsNone(bundle_module._normalized_hash(value))
        valid = {"ref": "TASK@r1", "document_path": "task.yaml", "content_hash": digest}
        self.assertEqual(
            (("source.yaml", "task.yaml", "task"), ("task.yaml", digest)),
            bundle_module._ref_edge("source.yaml", valid, "task"),
        )
        self.assertIsNone(bundle_module._ref_edge("source.yaml", None, "task"))
        self.assertIsNone(bundle_module._ref_edge("source.yaml", {**valid, "document_path": 1}, "task"))
        self.assertIsNone(bundle_module._ref_edge("source.yaml", {**valid, "content_hash": "bad"}, "task"))
        self.assertEqual("TASK@r1", bundle_module._revisioned_identity({"task_id": "TASK", "revision": 1}, "task_id"))
        self.assertEqual("MODE@2.0.0", bundle_module._versioned_identity({"mode_id": "MODE", "version": "2.0.0"}, "mode_id"))

    def test_lineage_mutation_matrix_exercises_each_runtime_authority_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = RuntimeBundleTests(methodName="runTest")._build_bundle(root)
            manifest = load_document(manifest_path)
            kinds = {
                item["path"]: item["kind"] for item in manifest["documents"]
            }
            documents = {
                path: load_document(root / path) for path in kinds
            }

            def mutate_method_task(docs, _manifest):
                docs["bundle/method.yaml"]["task_ref"]["task_id"] = "OTHER"

            def mutate_resolution_method(docs, _manifest):
                docs["bundle/resolution.yaml"]["method_resolution_ref"]["ref"] = "OTHER@r1"

            def mutate_resolution_requirement(docs, _manifest):
                docs["bundle/resolution.yaml"]["requirement_ref"]["requirement_id"] = "other"

            def mutate_resolution_status(docs, _manifest):
                docs["bundle/resolution.yaml"]["resolution_status"] = "blocked"

            def mutate_method_requirement(docs, _manifest):
                for decision in docs["bundle/method.yaml"]["action_decisions"]:
                    decision["capability_requirements"] = ["document-read"]

            def mutate_execution_slice(_docs, changed_manifest):
                changed_manifest["execution_scope"]["kind"] = "task"

            def mutate_task_completion(_docs, changed_manifest):
                changed_manifest["execution_scope"]["task_capability_closure"]["task_completion"] = True

            def mutate_snapshot_task(docs, _manifest):
                docs["bundle/snapshot.yaml"]["task_ref"]["ref"] = "OTHER@r1"

            def mutate_snapshot_requirement(docs, _manifest):
                docs["bundle/snapshot.yaml"]["requirement_ref"]["requirement_id"] = "other"

            def mutate_snapshot_supply(docs, _manifest):
                docs["bundle/snapshot.yaml"]["selected_supply_report_ref"]["ref"] = "other@1.0.0"

            def mutate_snapshot_lineage(docs, _manifest):
                docs["bundle/snapshot.yaml"]["method_resolution_ref"]["document_path"] = "other.yaml"

            def mutate_snapshot_evidence(docs, _manifest):
                docs["bundle/snapshot.yaml"]["conformance_evidence_refs"] = []

            cases = (
                ("RUNTIME-BUNDLE-TASK-IDENTITY-MISMATCH", mutate_method_task),
                ("RUNTIME-BUNDLE-METHOD-IDENTITY-MISMATCH", mutate_resolution_method),
                ("RUNTIME-BUNDLE-REQUIREMENT-IDENTITY-MISMATCH", mutate_resolution_requirement),
                ("RUNTIME-BUNDLE-RESOLUTION-NOT-SATISFIED", mutate_resolution_status),
                ("RUNTIME-BUNDLE-METHOD-REQUIREMENT-MISSING", mutate_method_requirement),
                ("RUNTIME-BUNDLE-EXECUTION-SLICE-MISMATCH", mutate_execution_slice),
                ("RUNTIME-BUNDLE-TASK-COMPLETION-AUTHORITY", mutate_task_completion),
                ("RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH", mutate_snapshot_task),
                ("RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH", mutate_snapshot_requirement),
                ("RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH", mutate_snapshot_supply),
                ("RUNTIME-BUNDLE-SNAPSHOT-LINEAGE-DRIFT", mutate_snapshot_lineage),
                ("RUNTIME-BUNDLE-EVIDENCE-LINEAGE-DRIFT", mutate_snapshot_evidence),
            )
            for expected, mutate in cases:
                with self.subTest(code=expected):
                    changed_documents = copy.deepcopy(documents)
                    changed_manifest = copy.deepcopy(manifest)
                    mutate(changed_documents, changed_manifest)
                    issues = bundle_module._validate_lineage(
                        root, changed_manifest, changed_documents, kinds
                    )
                    self.assertIn(expected, {issue.code for issue in issues})


class GenericCloseoutHelperTests(unittest.TestCase):
    def _validated_view(self, root: Path) -> host_module.ValidatedExecutionView:
        view_path = root / "view.yaml"
        view_path.write_text("view: true\n", encoding="utf-8")
        document = {
            "view_id": "VIEW",
            "revision": 1,
            "runtime_bundle_ref": {"ref": "BUNDLE@r1"},
            "task_ref": {"ref": "TASK@r1"},
            "execution_scope": {"kind": "slice"},
            "binding": {"provider": {"ref": "provider-a"}},
            "selected_supply_report_ref": {"ref": "supply-a@1.0.0"},
        }
        return host_module.ValidatedExecutionView(
            root, view_path, hash_bytes(view_path.read_bytes()), MappingProxyType(document), None
        )

    def _host(self, view: host_module.ValidatedExecutionView) -> dict[str, object]:
        return {
            "view_ref": {"ref": "VIEW@r1", "path": "view.yaml", "sha256": view.view_sha256},
            "runtime_bundle_ref": {"ref": "BUNDLE@r1"},
            "task_ref": {"ref": "TASK@r1"},
            "execution_scope": {"kind": "slice"},
            "status": "completed",
            "execution_phase": "post-call",
            "actual_binding": {"provider": {"ref": "provider-a"}},
            "actual_supply_report_ref": "supply-a@1.0.0",
            "started_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:01Z",
        }

    def test_closeout_hash_time_artifact_and_ledger_guards(self) -> None:
        digest = "d" * 64
        self.assertEqual(digest, closeout_module._normalized_hash("sha256:" + digest))
        for value in (None, "short", "x" * 64):
            self.assertIsNone(closeout_module._normalized_hash(value))
        for value in (None, "bad", "2026-01-01T00:00:00"):
            with self.assertRaises(closeout_module.GenericCloseoutValidationError):
                closeout_module._timestamp(value, "time")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "artifact.txt"
            artifact.write_bytes(b"artifact")
            closeout_module._validate_artifact_refs(
                root, ({"path": "artifact.txt", "sha256": hash_bytes(b"artifact")},)
            )
            for reference in (
                {"path": "missing", "sha256": "0" * 64},
                {"path": "artifact.txt", "sha256": "0" * 64},
            ):
                with self.assertRaises(closeout_module.GenericCloseoutValidationError):
                    closeout_module._validate_artifact_refs(root, (reference,))

            trace_dir = root / "trace"
            trace_dir.mkdir()
            trace_path = trace_dir / "trace.json"
            trace_path.write_text("{}", encoding="utf-8")
            with self.assertRaises(closeout_module.GenericCloseoutValidationError):
                closeout_module._trace_relative_pin(root, trace_path, {"path": "../../escape"})
            ledger = trace_dir / "events.jsonl"
            ledger.write_text(json.dumps({"event": 1}) + "\n", encoding="utf-8")
            valid = {"event_ledger": {"path": "events.jsonl", "sha256": hash_bytes(ledger.read_bytes()), "event_count": 1}}
            self.assertEqual(1, len(closeout_module._load_trace_events(root, trace_path, valid)))
            for changed in (
                {"event_ledger": {"path": "missing", "sha256": "0" * 64, "event_count": 1}},
                {"event_ledger": {"path": "events.jsonl", "sha256": "0" * 64, "event_count": 1}},
                {"event_ledger": {"path": "events.jsonl", "sha256": hash_bytes(ledger.read_bytes()), "event_count": 2}},
            ):
                with self.assertRaises(closeout_module.GenericCloseoutValidationError):
                    closeout_module._load_trace_events(root, trace_path, changed)
            ledger.write_bytes(b"not-json\n")
            malformed = {"event_ledger": {"path": "events.jsonl", "sha256": hash_bytes(ledger.read_bytes()), "event_count": 1}}
            with self.assertRaises(closeout_module.GenericCloseoutValidationError):
                closeout_module._load_trace_events(root, trace_path, malformed)

    def test_host_view_lifecycle_closure_rejects_unsupported_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            view = self._validated_view(root)
            closeout_module._validate_host_view_closure(self._host(view), view)
            cases = []
            host = self._host(view); host["view_ref"] = {}; cases.append(host)
            host = self._host(view); host["execution_phase"] = "preflight-blocked"; cases.append(host)
            host = self._host(view); host.update(status="blocked", actual_binding={}); cases.append(host)
            host = self._host(view); host.update(status="failed", execution_phase="post-call"); host.pop("actual_binding"); cases.append(host)
            host = self._host(view); host.update(status="failed", execution_phase="post-call", diagnostic={"code": "HOST-ACTUAL-BINDING-DRIFT"}); cases.append(host)
            host = self._host(view); host.update(status="failed", execution_phase="post-call", diagnostic={"code": "HOST-ACTUAL-SUPPLY-DRIFT"}); cases.append(host)
            host = self._host(view); host.update(status="failed", execution_phase="driver-exception"); cases.append(host)
            host = self._host(view); host.update(status="failed", execution_phase="unknown"); cases.append(host)
            host = self._host(view); host.update(started_at="2026-01-01T00:00:02Z"); cases.append(host)
            for host in cases:
                with self.subTest(status=host.get("status"), phase=host.get("execution_phase")):
                    with self.assertRaises(closeout_module.GenericCloseoutValidationError):
                        closeout_module._validate_host_view_closure(host, view)


class TraceHelperBranchTests(unittest.TestCase):
    def _recorder(self, root: Path) -> trace_module.AgentTraceRecorder:
        return trace_module.AgentTraceRecorder(
            root / "attempt",
            task_id="TASK",
            task_revision=1,
            attempt_id="ATTEMPT",
            task_snapshot={"task_id": "TASK", "revision": 1},
            accountable_owner="Owner",
            actor_id="runtime",
            runtime_identity="local",
            provider="provider",
            read_allowlist=("inputs/**",),
            write_scope=("outputs/**",),
            tool_allowlist=("read_file",),
            created_at="2026-01-01T00:00:00Z",
        )

    def test_recorder_edge_events_and_transcript_pairing_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = self._recorder(root)
            recorder.record_external_action(
                action_id="publish",
                target_category="local",
                authorization_basis="human gate",
                side_effect_status="completed",
                receipt_ref={"path": "receipt.yaml", "sha256": "0" * 64},
            )
            recorder.record(
                "capture-gap",
                {"stream": "messages", "reason": "lost", "affected_ids": "not-a-list"},
            )
            with self.assertRaises(ValueError):
                recorder.record_decision_snapshot(
                    "secret", {"Authorization": "Bearer do-not-store-this-token"}
                )
            with mock.patch.object(trace_module, "sanitize_trace_value", return_value=([], ())):
                with self.assertRaises(ValueError):
                    recorder.record_decision_snapshot("not-object", {"value": True})
            recorder.record("provider-request", {"request": {"prompt": "bounded"}})
            recorder.record("provider-response", {"response": {"text": "ok"}})
            recorder.seal()
            with self.assertRaises(RuntimeError):
                recorder.record_decision_snapshot("sealed", {"value": True})
            self.assertEqual(
                ({"request": {"prompt": "bounded"}, "response": {"text": "ok"}},),
                trace_module.derive_session_transcript(recorder.attempt_dir),
            )

            second = self._recorder(root / "other")
            second.record("provider-response", {"response": {"text": "orphan"}})
            second.seal()
            with self.assertRaisesRegex(ValueError, "no preceding request"):
                trace_module.derive_session_transcript(second.attempt_dir)


if __name__ == "__main__":
    unittest.main()
