import copy
import inspect
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    ExecutionDriverResult,
    ExecutionHostValidationError,
    execute_frozen_view,
    load_resolved_execution_view,
)
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog
from tests import test_execution_view as execution_view_fixtures


ROOT = Path(__file__).resolve().parents[1]


def plain(value):
    if hasattr(value, "items"):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return copy.deepcopy(value)


class RecordingDriver:
    def __init__(
        self,
        root: Path,
        binding: object,
        result: ExecutionDriverResult | None = None,
        supply_ref: str = "supply-no-skill-contract-check@1.0.0",
        tool_refs: tuple[str, ...] = (),
    ):
        self.root = root
        self._binding = plain(binding)
        self.result = result
        self._supply_ref = supply_ref
        self._tool_refs = tool_refs
        self.calls = 0

    @property
    def binding(self):
        return self._binding

    @property
    def selected_supply_report_ref(self):
        return self._supply_ref

    def execute(self, request):
        self.calls += 1
        if self.result is not None:
            return self.result
        artifact = self.root / "work/TASK-MR-ES-FROZEN-001/method-resolution.yaml"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("status: bounded\n", encoding="utf-8")
        return ExecutionDriverResult(
            status="completed",
            actual_binding=self._binding,
            actual_supply_report_ref=self._supply_ref,
            turns=1,
            output_tokens=64,
            elapsed_seconds=0.5,
            tool_invocations=len(self._tool_refs),
            tool_refs=self._tool_refs,
            side_effects=("task-local-check-report",),
            artifacts=(
                {
                    "contract": "method-resolution",
                    "path": "work/TASK-MR-ES-FROZEN-001/method-resolution.yaml",
                    "sha256": hash_file(artifact),
                },
            ),
        )


class RaisingDriver(RecordingDriver):
    def execute(self, request):
        self.calls += 1
        raise RuntimeError("private provider response must not enter the report")


class ExecutionHostTests(unittest.TestCase):
    def _build(self, root: Path):
        helper = execution_view_fixtures.ExecutionViewTests(methodName="runTest")
        bundle, inputs = helper._build(root)
        view = helper._produce(root, bundle, inputs)
        view_path = root / "view/resolved-view.yaml"
        view_path.write_text(
            yaml.safe_dump(view, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        validated = load_resolved_execution_view(
            "view/resolved-view.yaml",
            expected_sha256=hash_file(view_path),
            bundle=bundle,
            schema_root=ROOT / "schemas",
        )
        return bundle, validated

    def _execute(self, bundle, view, driver):
        return execute_frozen_view(
            view,
            driver,
            report_id="HOST-REPORT-001",
            attempt_id="ATTEMPT-001",
            started_at="2026-08-26T00:00:01Z",
            completed_at="2026-08-26T00:00:02Z",
            schema_root=ROOT / "schemas",
        )

    def test_exact_view_load_and_single_driver_execution_report_actual_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, view = self._build(root)
            with self.assertRaises(TypeError):
                view.document["status"] = "changed"
            driver = RecordingDriver(root, view.document["binding"])
            report = self._execute(bundle, view, driver)
            self.assertEqual(1, driver.calls)
            self.assertEqual("completed", report["status"])
            self.assertTrue(report["actual_facts"]["complete"])
            self.assertEqual(0, report["actual_facts"]["tool_invocations"])
            self.assertEqual("method-resolution", report["artifacts"][0]["contract"])
            self.assertEqual(
                [], SchemaCatalog(ROOT / "schemas").validate("execution_host_report", report)
            )
            self.assertFalse(report["boundaries"]["automatic_fallback"])
            self.assertFalse(report["boundaries"]["topic5_recovery"])
            self.assertIn("freshness", report["enforcement"]["preventive_controls"])
            self.assertIn("data-egress", report["enforcement"]["detective_controls"])
            self.assertFalse(report["enforcement"]["driver_claims_trusted"])

    def test_hash_valid_view_rewrite_is_rejected_by_deterministic_recomputation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            helper = execution_view_fixtures.ExecutionViewTests(methodName="runTest")
            bundle, inputs = helper._build(root)
            view = helper._produce(root, bundle, inputs)
            view["binding"]["model"]["ref"] = "silently-rebound-model"
            path = root / "view/resolved-view.yaml"
            path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ExecutionHostValidationError):
                load_resolved_execution_view(
                    path,
                    expected_sha256=hash_file(path),
                    bundle=bundle,
                    schema_root=ROOT / "schemas",
                )

    def test_started_at_freshness_and_bound_bundle_drift_prevent_driver_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, view = self._build(root)
            driver = RecordingDriver(root, view.document["binding"])
            report = execute_frozen_view(
                view,
                driver,
                report_id="HOST-STALE",
                attempt_id="ATTEMPT-STALE",
                started_at="2100-01-01T00:00:00Z",
                completed_at="2100-01-01T00:00:01Z",
                schema_root=ROOT / "schemas",
            )
            self.assertEqual(0, driver.calls)
            self.assertEqual("blocked", report["status"])
            self.assertEqual("HOST-FRESHNESS-EXPIRED", report["diagnostic"]["code"])

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, view = self._build(root)
            task_path = next(path for path in bundle.documents if path.name == "task.yaml")
            task_path.write_bytes(task_path.read_bytes() + b"\n# post-view drift\n")
            driver = RecordingDriver(root, view.document["binding"])
            report = self._execute(bundle, view, driver)
            self.assertEqual(0, driver.calls)
            self.assertEqual("blocked", report["status"])
            self.assertEqual("HOST-RUNTIME-BUNDLE-DRIFT", report["diagnostic"]["code"])
            self.assertEqual(
                view.document["runtime_bundle_ref"], report["runtime_bundle_ref"]
            )

    def test_preflight_binding_mismatch_blocks_without_call_and_requests_reresolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, view = self._build(root)
            wrong = plain(view.document["binding"])
            wrong["model"] = dict(wrong["model"])
            wrong["model"]["ref"] = "other-model"
            driver = RecordingDriver(root, wrong)
            report = self._execute(bundle, view, driver)
            self.assertEqual(0, driver.calls)
            self.assertEqual("blocked", report["status"])
            self.assertEqual("HOST-BINDING-MISMATCH", report["diagnostic"]["code"])
            self.assertTrue(report["re_resolution_request"]["required"])

    def test_post_call_binding_boundary_budget_and_output_drift_fail_closed(self) -> None:
        cases = [
            ("binding", "HOST-ACTUAL-BINDING-DRIFT"),
            ("supply", "HOST-ACTUAL-SUPPLY-DRIFT"),
            ("egress", "HOST-DATA-EGRESS-VIOLATION"),
            ("side-effect", "HOST-SIDE-EFFECT-VIOLATION"),
            ("budget", "HOST-BUDGET-VIOLATION"),
            ("output", "HOST-REQUIRED-OUTPUT-MISSING"),
            ("write-scope", "HOST-ARTIFACT-WRITE-SCOPE"),
        ]
        for mutation, expected_code in cases:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                bundle, view = self._build(root)
                actual_binding = plain(view.document["binding"])
                if mutation == "binding":
                    actual_binding = plain(view.document["binding"])
                    actual_binding["host"]["ref"] = "other-host"
                artifact = root / "work/TASK-MR-ES-FROZEN-001/method-resolution.yaml"
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("status: bounded\n", encoding="utf-8")
                artifacts = (
                    {
                        "contract": "method-resolution",
                        "path": "work/TASK-MR-ES-FROZEN-001/method-resolution.yaml",
                        "sha256": hash_file(artifact),
                    },
                )
                if mutation == "write-scope":
                    outside = root / "outside/result.yaml"
                    outside.parent.mkdir(parents=True, exist_ok=True)
                    outside.write_text("status: bounded\n", encoding="utf-8")
                    artifacts = (
                        {
                            "contract": "method-resolution",
                            "path": "outside/result.yaml",
                            "sha256": hash_file(outside),
                        },
                    )
                result = ExecutionDriverResult(
                    status="completed",
                    actual_binding=actual_binding,
                    actual_supply_report_ref=(
                        "supply-other@1.0.0"
                        if mutation == "supply"
                        else "supply-no-skill-contract-check@1.0.0"
                    ),
                    turns=5 if mutation == "budget" else 1,
                    data_egress_payloads=("project-context",) if mutation == "egress" else (),
                    side_effects=("undeclared-effect",) if mutation == "side-effect" else (),
                    artifacts=() if mutation == "output" else artifacts,
                )
                driver = RecordingDriver(root, view.document["binding"], result)
                report = self._execute(bundle, view, driver)
                self.assertEqual(1, driver.calls)
                self.assertEqual("failed", report["status"])
                self.assertEqual(expected_code, report["diagnostic"]["code"])
                if mutation in {"binding", "supply"}:
                    self.assertEqual("re-resolution", report["diagnostic"]["recommended_next"])

    def test_driver_exception_is_one_call_content_free_capture_gap_not_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, view = self._build(root)
            driver = RaisingDriver(root, view.document["binding"])
            report = self._execute(bundle, view, driver)
            self.assertEqual(1, driver.calls)
            self.assertEqual("failed", report["status"])
            self.assertFalse(report["actual_facts"]["complete"])
            self.assertEqual(["driver-exception"], report["actual_facts"]["capture_gaps"])
            self.assertNotIn("private provider response", str(report))
            self.assertNotIn("re_resolution_request", report)
            self.assertFalse(report["boundaries"]["topic5_recovery"])

    def test_host_source_has_no_retry_fallback_routing_or_recovery_dependency(self) -> None:
        from research_workbench.execution import host

        source = inspect.getsource(host)
        self.assertNotIn("capability.lifecycle", source)
        self.assertNotIn("skill_needs", source)
        self.assertNotIn("model_pool", source)
        self.assertNotIn("handoff", source)
        self.assertNotIn("recovery", source.lower().replace("topic5_recovery", ""))
        self.assertNotIn("retry", source.lower())


if __name__ == "__main__":
    unittest.main()
