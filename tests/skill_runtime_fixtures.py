"""Shared M11-006 Skill Runtime extension fixtures (not unittest-discovered)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.supply import (
    CapabilitySupplyReport,
    assess_supply,
)
from research_workbench.io import load_document
from tests.execution_fixtures import ROOT, RuntimeBundleFixture


class SkillRuntimeBundleFixture(RuntimeBundleFixture):
    projection_path = "bundle/skill-projection.yaml"

    @staticmethod
    def projection() -> dict[str, Any]:
        digest = "a" * 64
        return {
            "schema_version": "0.1.0",
            "projection_id": "synthetic-runtime-skill-1.0.0",
            "projection_version": "1.0.0",
            "release": {
                "skill_id": "synthetic-runtime-skill",
                "skill_version": "1.0.0",
                "release_ref": "synthetic-runtime-skill@1.0.0",
                "manifest_path": "maintainer/accepted/synthetic-runtime-skill.yaml",
                "manifest_sha256": "sha256:" + "b" * 64,
                "content_hash": "sha256:" + digest,
                "package_hash": "sha256:" + "c" * 64,
            },
            "runtime_contract": {
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
                "dependencies": {
                    "required_tools": [],
                    "optional_tools": [],
                },
                "compatibility": {
                    "applies_to_modes": ["evidence-synthesis"],
                    "excludes": ["claim-promotion"],
                    "incompatible_with": [],
                },
                "permission_ceiling": {
                    "filesystem": "worktree-write",
                    "network": "forbidden",
                    "external_write": False,
                    "allowed_roots": ["work"],
                },
                "data_egress_ceiling": {
                    "policy": "forbidden",
                    "allowed_payloads": [],
                    "forbidden_payloads": [
                        "checked-documents",
                        "project-context",
                        "validation-results",
                    ],
                },
                "side_effect_ceiling": {
                    "policy": "allowlisted-only",
                    "allowed_effects": ["task-local-check-report"],
                },
            },
            "eligibility": {
                "state": "eligible",
                "eligibility_ref": "RTE-SYNTHETIC-RUNTIME-1",
                "scopes": ["new-binding"],
            },
            "admission_provenance": {
                "lifecycle_ref": "synthetic-runtime-skill@1.0.0/lifecycle@1.0.0",
                "lifecycle_document_path": "maintainer/lifecycle/synthetic-runtime-skill.yaml",
                "lifecycle_content_hash": "sha256:" + "d" * 64,
                "decision_owner": "human",
                "decision_ref": "DECISION-SYNTHETIC-RUNTIME-1",
            },
            "boundaries": {
                "stores_need": False,
                "stores_candidate": False,
                "stores_trial_or_evaluation_results": False,
                "stores_metrics_or_deliberation": False,
                "stores_lifecycle_history": False,
                "selects_supply": False,
                "grants_execution": False,
                "grants_permission": False,
                "owns_fallback": False,
                "promotes_claim": False,
                "satisfies_human_gate": False,
            },
        }

    def _build_skill_bundle(self, root: Path) -> Path:
        manifest_path = self._build_bundle(root)
        projection = self.projection()
        projection_hash = self._write(root, self.projection_path, projection)

        method = load_document(root / "bundle/method.yaml")
        action = next(
            item
            for item in method["action_decisions"]
            if item.get("action_ref") == "ES-A4@1.0.0"
        )
        action["mechanisms"] = [
            "skill-need" if value == "no-skill" else value
            for value in action["mechanisms"]
        ]
        action["skill_need_refs"] = ["NEED-SYNTHETIC-RUNTIME"]
        method["skill_disposition"] = {
            "status": "skill-need",
            "need_refs": ["NEED-SYNTHETIC-RUNTIME"],
            "reason": "The already admitted synthetic Skill is supplied through Capability Resolution.",
        }
        method_hash = self._write(root, "bundle/method.yaml", method)

        evidence = load_document(root / "bundle/conformance.yaml")
        evidence["implementation_ref"] = "synthetic-runtime-skill"
        evidence["implementation_version"] = "1.0.0"
        evidence_hash = self._write(root, "bundle/conformance.yaml", evidence)

        supply = load_document(root / "bundle/supply.yaml")
        supply["report_id"] = "supply-synthetic-runtime-skill"
        supply["supply_identity"] = {
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
            "skill_release_projection_ref": {
                "ref": "synthetic-runtime-skill-1.0.0@1.0.0",
                "document_path": self.projection_path,
                "content_hash": "sha256:" + projection_hash,
            },
        }
        supply["conformance_evidence"][0]["artifact_ref"]["sha256"] = evidence_hash
        supply["required_permissions"]["allowed_roots"] = ["work"]
        supply["limitations"] = [
            "Synthetic Skill availability proves contract wiring only, not scientific benefit."
        ]
        supply_hash = self._write(root, "bundle/supply.yaml", supply)

        requirement = CapabilityRequirement.from_mapping(
            load_document(root / "bundle/requirement.yaml")
        )
        assessment = assess_supply(
            requirement,
            CapabilitySupplyReport.from_mapping(supply),
            qualification="runtime-execution",
            evidence_check=lambda _identity, _evidence, _capability: "pass",
            projection_eligibility_check=lambda _reference: True,
        )
        if not assessment.eligible:
            raise AssertionError("synthetic Skill Supply must be eligible")

        resolution = load_document(root / "bundle/resolution.yaml")
        resolution["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        selected_ref = "supply-synthetic-runtime-skill@1.0.0"
        resolution["candidate_supply_report_refs"] = [
            {
                "ref": selected_ref,
                "document_path": "bundle/supply.yaml",
                "content_hash": "sha256:" + supply_hash,
            }
        ]
        resolution["comparisons"] = [assessment.to_mapping()]
        resolution["selected_supply_report_ref"] = selected_ref
        resolution["limitations"] = [
            "Selection proves a bounded synthetic Skill candidate only."
        ]
        resolution_hash = self._write(root, "bundle/resolution.yaml", resolution)

        snapshot = load_document(root / "bundle/snapshot.yaml")
        snapshot["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
        snapshot["selected_supply_report_ref"] = {
            "ref": selected_ref,
            "document_path": "bundle/supply.yaml",
            "content_hash": "sha256:" + supply_hash,
        }
        snapshot["supply_identity"] = copy.deepcopy(supply["supply_identity"])
        snapshot["supply_required_permissions"] = copy.deepcopy(
            supply["required_permissions"]
        )
        snapshot["supply_data_egress"] = copy.deepcopy(
            supply["data_egress_behavior"]
        )
        snapshot["supply_side_effects"] = copy.deepcopy(supply["side_effects"])
        snapshot["conformance_evidence_refs"] = [
            {"path": "bundle/conformance.yaml", "sha256": evidence_hash}
        ]
        snapshot["limitations"] = [
            "The Skill Snapshot remains subject to the same final View/Host boundaries."
        ]
        snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot)

        manifest = load_document(manifest_path)
        manifest["bundle_id"] = "RB-SKILL-LOCAL-001"
        manifest["entrypoint"]["sha256"] = snapshot_hash
        changed = {
            "bundle/method.yaml": method_hash,
            "bundle/conformance.yaml": evidence_hash,
            "bundle/supply.yaml": supply_hash,
            "bundle/resolution.yaml": resolution_hash,
            "bundle/snapshot.yaml": snapshot_hash,
        }
        for item in manifest["documents"]:
            if item["path"] in changed:
                item["sha256"] = changed[item["path"]]
        manifest["documents"].append(
            {
                "kind": "skill_release_projection",
                "path": self.projection_path,
                "sha256": projection_hash,
            }
        )
        manifest["imports"].append(
            {
                "from_path": "bundle/supply.yaml",
                "to_path": self.projection_path,
                "relation": "supply-projection",
            }
        )
        manifest["skill_extension"] = {
            "enabled": True,
            "projection": {
                "kind": "skill_release_projection",
                "path": self.projection_path,
                "sha256": projection_hash,
            },
        }
        self._write(root, "bundle/manifest.yaml", manifest)
        return manifest_path

    def _rewrite_skill_bundle(
        self,
        root: Path,
        mutate: Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], None],
        *,
        refresh_supply_projection_pin: bool = True,
        refresh_manifest_projection_pin: bool = True,
    ) -> Path:
        projection = load_document(root / self.projection_path)
        supply = load_document(root / "bundle/supply.yaml")
        method = load_document(root / "bundle/method.yaml")
        manifest = load_document(root / "bundle/manifest.yaml")
        mutate(projection, supply, method, manifest)

        projection_hash = self._write(root, self.projection_path, projection)
        projection_ref = supply["supply_identity"]["skill_release_projection_ref"]
        if refresh_supply_projection_pin:
            projection_ref["content_hash"] = "sha256:" + projection_hash
        method_hash = self._write(root, "bundle/method.yaml", method)
        supply_hash = self._write(root, "bundle/supply.yaml", supply)

        resolution = load_document(root / "bundle/resolution.yaml")
        resolution["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        resolution["candidate_supply_report_refs"][0]["content_hash"] = "sha256:" + supply_hash
        resolution_hash = self._write(root, "bundle/resolution.yaml", resolution)

        snapshot = load_document(root / "bundle/snapshot.yaml")
        snapshot["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
        snapshot["selected_supply_report_ref"]["content_hash"] = "sha256:" + supply_hash
        snapshot["supply_identity"] = copy.deepcopy(supply["supply_identity"])
        snapshot["supply_required_permissions"] = copy.deepcopy(supply["required_permissions"])
        snapshot["supply_data_egress"] = copy.deepcopy(supply["data_egress_behavior"])
        snapshot["supply_side_effects"] = copy.deepcopy(supply["side_effects"])
        snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot)

        changed = {
            "bundle/method.yaml": method_hash,
            "bundle/supply.yaml": supply_hash,
            "bundle/resolution.yaml": resolution_hash,
            "bundle/snapshot.yaml": snapshot_hash,
            self.projection_path: projection_hash,
        }
        manifest["entrypoint"]["sha256"] = snapshot_hash
        for item in manifest["documents"]:
            if item["path"] in changed:
                item["sha256"] = changed[item["path"]]
        if refresh_manifest_projection_pin:
            manifest["skill_extension"]["projection"]["sha256"] = projection_hash
        self._write(root, "bundle/manifest.yaml", manifest)
        return root / "bundle/manifest.yaml"
