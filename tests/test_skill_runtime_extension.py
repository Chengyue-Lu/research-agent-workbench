import copy
import inspect
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.projection_supply import (
    projection_is_runtime_eligible,
    projection_reference,
    projection_supply_fact_issues,
)
from research_workbench.capability.supply import (
    CapabilitySupplyReport,
    assess_supply,
    resolve_status,
)
from research_workbench.execution import (
    execute_frozen_view,
    load_runtime_bundle,
    load_resolved_execution_view,
    produce_resolved_execution_view,
)
from research_workbench.execution.runtime_bundle import RuntimeBundleValidationError
from research_workbench.io import load_document
from research_workbench.validation.capability_supply_registry import (
    validate_capability_supply_chain,
)
from tests.execution_fixtures import (
    ExecutionViewFixture,
    RecordingDriver,
    SequenceClock,
)
from tests.skill_runtime_fixtures import ROOT, SkillRuntimeBundleFixture


class SkillRuntimeExtensionTests(SkillRuntimeBundleFixture, unittest.TestCase):
    @staticmethod
    def _codes(raised: object) -> set[str]:
        return {issue.code for issue in raised.exception.issues}

    def test_projection_skill_uses_existing_resolution_snapshot_and_view_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_skill_bundle(root)
            bundle = load_runtime_bundle(
                manifest_path, project_root=root, schema_root=ROOT / "schemas"
            )
            self.assertEqual(8, len(bundle.documents))
            self.assertEqual(
                "skill",
                next(
                    document["supply_identity"]["supply_kind"]
                    for document in bundle.documents.values()
                    if "supply_identity" in document and "report_id" in document
                ),
            )
            self.assertFalse(any("lifecycle" in path.as_posix() for path in bundle.documents))

            inputs = ExecutionViewFixture()._inputs(root)
            binding_path = root / inputs["execution_binding"].path
            binding = load_document(binding_path)
            binding["selected_supply_report_ref"] = "supply-synthetic-runtime-skill@1.0.0"
            inputs["execution_binding"] = ExecutionViewFixture()._write(
                root, inputs["execution_binding"].path, binding
            )
            view = produce_resolved_execution_view(
                bundle,
                **inputs,
                execution_at="2026-08-26T00:00:00Z",
                view_id="VIEW-SKILL-LOCAL-001",
                expected_bundle_sha256=hash_file(bundle.manifest_path),
                schema_root=ROOT / "schemas",
            )
            self.assertEqual(
                "supply-synthetic-runtime-skill@1.0.0",
                view["selected_supply_report_ref"]["ref"],
            )
            self.assertFalse(view["boundaries"]["supply_selection"])
            self.assertFalse(view["boundaries"]["automatic_fallback"])
            self.assertEqual(
                ["work/TASK-MR-ES-FROZEN-001"],
                view["effective_constraints"]["permissions"]["allowed_roots"],
            )

            view_path = root / "view/resolved-skill-view.yaml"
            view_path.write_text(
                yaml.safe_dump(view, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            validated_view = load_resolved_execution_view(
                view_path,
                expected_sha256=hash_file(view_path),
                bundle=bundle,
                schema_root=ROOT / "schemas",
            )
            driver = RecordingDriver(
                root,
                validated_view.document["binding"],
                supply_ref="supply-synthetic-runtime-skill@1.0.0",
            )
            report = execute_frozen_view(
                validated_view,
                driver,
                report_id="HOST-REPORT-SKILL-001",
                attempt_id="ATTEMPT-SKILL-001",
                clock=SequenceClock(
                    "2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z"
                ),
                schema_root=ROOT / "schemas",
            )
            self.assertEqual("completed", report["status"])
            self.assertEqual(1, driver.calls)
            self.assertEqual(
                "supply-synthetic-runtime-skill@1.0.0",
                report["actual_supply_report_ref"],
            )

    def test_runtime_assessment_requires_projection_not_lifecycle_callback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._build_skill_bundle(root)
            requirement = CapabilityRequirement.from_mapping(
                load_document(root / "bundle/requirement.yaml")
            )
            report = CapabilitySupplyReport.from_mapping(
                load_document(root / "bundle/supply.yaml")
            )
            common = {
                "qualification": "runtime-execution",
                "evidence_check": lambda _identity, _evidence, _capability: "pass",
            }
            lifecycle_only = assess_supply(
                requirement,
                report,
                **common,
                runtime_eligibility_check=lambda _lifecycle, _eligibility: True,
            )
            self.assertEqual(("gap", None), resolve_status([lifecycle_only]))
            projected = assess_supply(
                requirement,
                report,
                **common,
                projection_eligibility_check=lambda reference: (
                    reference.ref == "synthetic-runtime-skill-1.0.0@1.0.0"
                ),
            )
            self.assertEqual(("satisfied", report.reference), resolve_status([projected]))

    def test_projection_supply_report_registry_facts_are_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._build_skill_bundle(root)
            projection_path = root / self.projection_path
            supply_path = root / "bundle/supply.yaml"
            evidence_path = root / "bundle/conformance.yaml"
            documents = {
                projection_path: load_document(projection_path),
                supply_path: load_document(supply_path),
                evidence_path: load_document(evidence_path),
            }
            self.assertEqual([], validate_capability_supply_chain(documents))

            mutations = (
                (
                    lambda values: values[supply_path]["supply_identity"][
                        "skill_release_projection_ref"
                    ].__setitem__("content_hash", "sha256:" + "0" * 64),
                    "CAPABILITY-SUPPLY-PROJECTION-HASH-MISMATCH",
                ),
                (
                    lambda values: values[supply_path].__setitem__(
                        "provided_capabilities", ["substituted-capability"]
                    ),
                    "SKILL-PROJECTION-SUPPLY-CONTRACT-DRIFT",
                ),
                (
                    lambda values: values[supply_path]["required_permissions"].__setitem__(
                        "network", "allowed"
                    ),
                    "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
                ),
            )
            for mutate, expected in mutations:
                with self.subTest(expected=expected):
                    changed = copy.deepcopy(documents)
                    mutate(changed)
                    self.assertIn(
                        expected,
                        {issue.code for issue in validate_capability_supply_chain(changed)},
                    )

    def test_runtime_bundle_rejects_projection_and_boundary_drift(self) -> None:
        cases = (
            (
                lambda projection, _supply, _method, _manifest: projection["runtime_contract"].__setitem__(
                    "provided_capabilities", ["substituted-capability"]
                ),
                {},
                "SKILL-PROJECTION-SUPPLY-CONTRACT-DRIFT",
            ),
            (
                lambda _projection, supply, _method, _manifest: supply[
                    "required_permissions"
                ].update({"allowed_roots": ["outside-projection"]}),
                {},
                "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
            ),
            (
                lambda _projection, supply, _method, _manifest: supply[
                    "data_egress_behavior"
                ].update(
                    {
                        "policy": "allowlisted-only",
                        "allowed_payloads": ["checked-documents"],
                    }
                ),
                {},
                "SKILL-PROJECTION-SUPPLY-EGRESS-EXCEEDED",
            ),
            (
                lambda _projection, supply, _method, _manifest: supply[
                    "side_effects"
                ].update(
                    {
                        "policy": "allowlisted-only",
                        "allowed_effects": ["external-write"],
                    }
                ),
                {},
                "SKILL-PROJECTION-SUPPLY-EFFECT-EXCEEDED",
            ),
            (
                lambda _projection, _supply, method, _manifest: method[
                    "skill_disposition"
                ].update({"status": "no-skill", "need_refs": []}),
                {},
                "RUNTIME-BUNDLE-METHOD-SKILL-DISPOSITION-MISMATCH",
            ),
            (
                lambda _projection, _supply, _method, manifest: manifest[
                    "skill_extension"
                ]["projection"].__setitem__("sha256", "0" * 64),
                {"refresh_manifest_projection_pin": False},
                "RUNTIME-BUNDLE-SKILL-PROJECTION-PIN-MISMATCH",
            ),
        )
        for mutate, options, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self._build_skill_bundle(root)
                manifest_path = self._rewrite_skill_bundle(root, mutate, **options)
                with self.assertRaises(RuntimeBundleValidationError) as raised:
                    load_runtime_bundle(
                        manifest_path,
                        project_root=root,
                        schema_root=ROOT / "schemas",
                    )
                self.assertIn(expected, self._codes(raised))

    def test_projection_supply_helper_is_total_and_fail_closed(self) -> None:
        projection = self.projection()
        supply = {
            "supply_identity": {
                "supply_kind": "skill",
                "implementation_ref": "synthetic-runtime-skill",
                "implementation_version": "1.0.0",
                "content_hash": "sha256:" + "a" * 64,
                "components": [
                    {
                        "component_kind": "skill",
                        "component_ref": "synthetic-runtime-skill",
                        "version": "1.0.0",
                        "content_hash": "sha256:" + "a" * 64,
                    }
                ],
            },
            "provided_capabilities": ["research-contract-check"],
            "supported_inputs": [
                "document-references",
                "schema-and-checker-version",
                "checked-subject-hashes",
                "project-root-boundary",
            ],
            "supported_outputs": [
                "deterministic-findings",
                "checked-subject-hashes",
                "declared-risk-codes",
            ],
            "required_permissions": {
                "filesystem": "worktree-write",
                "network": "forbidden",
                "external_write": False,
                "allowed_roots": ["work/task"],
            },
            "data_egress_behavior": {
                "policy": "forbidden",
                "allowed_payloads": [],
                "forbidden_payloads": [
                    "checked-documents",
                    "project-context",
                    "validation-results",
                ],
            },
            "side_effects": {
                "policy": "none",
                "allowed_effects": [],
            },
        }
        self.assertEqual(
            "synthetic-runtime-skill-1.0.0@1.0.0",
            projection_reference(projection),
        )
        self.assertTrue(projection_is_runtime_eligible(projection))
        self.assertEqual((), projection_supply_fact_issues(projection, supply))

        ineligible_cases = (
            None,
            {},
            {"state": "eligible", "scopes": ["historical-replay"]},
        )
        for eligibility in ineligible_cases:
            with self.subTest(eligibility=eligibility):
                changed = copy.deepcopy(projection)
                changed["eligibility"] = eligibility
                self.assertFalse(projection_is_runtime_eligible(changed))
        changed = copy.deepcopy(projection)
        changed["boundaries"]["grants_execution"] = True
        self.assertFalse(projection_is_runtime_eligible(changed))

        cases = (
            (
                lambda projected, _supply: projected.__setitem__("release", []),
                "SKILL-PROJECTION-SUPPLY-SHAPE",
            ),
            (
                lambda _projected, report: report["supply_identity"].__setitem__(
                    "implementation_ref", "substituted"
                ),
                "SKILL-PROJECTION-SUPPLY-IDENTITY-DRIFT",
            ),
            (
                lambda projected, _report: projected["runtime_contract"].__setitem__(
                    "dependencies", []
                ),
                "SKILL-PROJECTION-SUPPLY-COMPONENT-DRIFT",
            ),
            (
                lambda projected, _report: projected["runtime_contract"][
                    "dependencies"
                ].__setitem__("required_tools", ["missing-tool"]),
                "SKILL-PROJECTION-SUPPLY-COMPONENT-DRIFT",
            ),
            (
                lambda _projected, report: report["supply_identity"]["components"].append(
                    {"component_kind": "adapter", "component_ref": "hidden-adapter"}
                ),
                "SKILL-PROJECTION-SUPPLY-COMPONENT-DRIFT",
            ),
            (
                lambda _projected, report: report.__setitem__(
                    "supported_inputs", [{"not": "a string"}]
                ),
                "SKILL-PROJECTION-SUPPLY-CONTRACT-DRIFT",
            ),
            (
                lambda _projected, report: report.__setitem__(
                    "required_permissions", []
                ),
                "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
            ),
            (
                lambda _projected, report: report["required_permissions"].update(
                    {"filesystem": "invalid"}
                ),
                "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
            ),
            (
                lambda _projected, report: report["required_permissions"].update(
                    {"filesystem": "workspace-write"}
                ),
                "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
            ),
            (
                lambda _projected, report: report["required_permissions"].update(
                    {"allowed_roots": ["outside"]}
                ),
                "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
            ),
            (
                lambda _projected, report: report["data_egress_behavior"].update(
                    {"forbidden_payloads": []}
                ),
                "SKILL-PROJECTION-SUPPLY-EGRESS-EXCEEDED",
            ),
            (
                lambda _projected, report: report.__setitem__(
                    "data_egress_behavior", {"allowed_payloads": [["invalid"]]}
                ),
                "SKILL-PROJECTION-SUPPLY-EGRESS-EXCEEDED",
            ),
            (
                lambda _projected, report: report.__setitem__(
                    "data_egress_behavior", []
                ),
                "SKILL-PROJECTION-SUPPLY-EGRESS-EXCEEDED",
            ),
            (
                lambda _projected, report: report.__setitem__("side_effects", []),
                "SKILL-PROJECTION-SUPPLY-EFFECT-EXCEEDED",
            ),
            (
                lambda _projected, report: report["side_effects"].update(
                    {
                        "policy": "allowlisted-only",
                        "allowed_effects": ["external-write"],
                    }
                ),
                "SKILL-PROJECTION-SUPPLY-EFFECT-EXCEEDED",
            ),
            (
                lambda _projected, report: report.__setitem__(
                    "side_effects",
                    {"policy": "none", "allowed_effects": [["invalid"]]},
                ),
                "SKILL-PROJECTION-SUPPLY-EFFECT-EXCEEDED",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                changed_projection = copy.deepcopy(projection)
                changed_supply = copy.deepcopy(supply)
                mutate(changed_projection, changed_supply)
                self.assertIn(
                    expected,
                    {
                        code
                        for code, _message in projection_supply_fact_issues(
                            changed_projection, changed_supply
                        )
                    },
                )

        narrowed_projection = copy.deepcopy(projection)
        narrowed_supply = copy.deepcopy(supply)
        narrowed_projection["runtime_contract"]["data_egress_ceiling"] = {
            "policy": "allowlisted-only",
            "allowed_payloads": ["checked-documents"],
            "forbidden_payloads": ["source-content"],
        }
        narrowed_projection["runtime_contract"]["side_effect_ceiling"] = {
            "policy": "none",
            "allowed_effects": [],
        }
        narrowed_supply["data_egress_behavior"] = {
            "policy": "forbidden",
            "allowed_payloads": [],
            "forbidden_payloads": ["source-content"],
        }
        narrowed_supply["side_effects"] = {
            "policy": "none",
            "allowed_effects": [],
        }
        self.assertEqual(
            (),
            projection_supply_fact_issues(narrowed_projection, narrowed_supply),
        )

    def test_runtime_and_host_keep_no_skill_specific_dispatch_seam(self) -> None:
        from research_workbench.execution import execution_view, host, runtime_bundle

        runtime_source = inspect.getsource(runtime_bundle)
        self.assertNotIn("capability.lifecycle", runtime_source)
        self.assertNotIn("skill_needs", runtime_source)
        self.assertNotIn("evaluation", runtime_source)
        self.assertNotIn("SkillReleaseProjectionSet", runtime_source)
        for module in (execution_view, host):
            source = inspect.getsource(module)
            self.assertNotIn("skill_release_projection", source)
            self.assertNotIn("SkillReleaseProjection", source)


if __name__ == "__main__":
    unittest.main()
