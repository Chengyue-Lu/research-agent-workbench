"""Shared M11 execution fixtures that are not unittest discovery targets.

Test modules may depend on these deterministic builders, but must not import
``TestCase`` classes from another ``test_*.py`` module.  Keeping the fixture
surface here prevents unittest from loading the same canonical test under both
``test_*`` and ``tests.test_*`` module identities.
"""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    ExecutionDriverResult,
    PinnedExecutionInput,
    load_runtime_bundle,
    produce_resolved_execution_view,
)
from research_workbench.io import load_document


ROOT = Path(__file__).resolve().parents[1]


class RuntimeBundleFixture:
    """Build the deterministic no-Skill Runtime Bundle used by M11 tests."""

    def _write(self, root: Path, relative: str, document: object) -> str:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return hash_file(path)

    def _build_bundle(self, root: Path) -> Path:
        task_path = "bundle/task.yaml"
        method_path = "bundle/method.yaml"
        requirement_path = "bundle/requirement.yaml"
        evidence_path = "bundle/conformance.yaml"
        supply_path = "bundle/supply.yaml"
        resolution_path = "bundle/resolution.yaml"
        snapshot_path = "bundle/snapshot.yaml"

        task = copy.deepcopy(
            load_document(ROOT / "examples/method-resolution-tasks/TASK-MR-ES-FROZEN-001.yaml")
        )
        task_hash = self._write(root, task_path, task)

        method = copy.deepcopy(
            load_document(ROOT / "examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml")
        )
        method["task_ref"]["sha256"] = task_hash
        method_hash = self._write(root, method_path, method)

        requirement = copy.deepcopy(
            load_document(ROOT / "registry/capabilities/requirements/research-contract-check.yaml")
        )
        requirement_hash = self._write(root, requirement_path, requirement)

        evidence = {
            "evidence_kind": "local-conformance",
            "evidence_id": "CONF-RUNTIME-NO-SKILL",
            "implementation_ref": "runtime-no-skill-contract-check",
            "implementation_version": "1.0.0",
            "capability_ids": ["research-contract-check"],
            "scope": {"scope_kind": "local-environment", "scope_ref": "test-runtime-host"},
            "checks": ["the bounded local procedure is available without a Skill package"],
            "result": "pass",
            "limitations": ["This test observation proves structural Runtime bundle closure only."],
        }
        evidence_hash = self._write(root, evidence_path, evidence)

        supply = copy.deepcopy(
            load_document(
                ROOT / "examples/capability-resolution/supply-reports/no-skill-contract-check.yaml"
            )
        )
        supply["observation_scope"] = "deterministic-local"
        supply["supply_identity"]["implementation_ref"] = "runtime-no-skill-contract-check"
        supply["supply_identity"]["components"][0]["component_ref"] = (
            "runtime-no-skill-contract-check"
        )
        supply["conformance_evidence"] = [
            {
                "evidence_id": evidence["evidence_id"],
                "evidence_class": "live",
                "artifact_kind": "capability-conformance-evidence",
                "artifact_ref": {"path": evidence_path, "sha256": evidence_hash},
            }
        ]
        supply["availability"] = {
            "status": "available",
            "scope": {"scope_kind": "local-environment", "scope_ref": "test-runtime-host"},
            "observed_at": "2026-08-26T00:00:00Z",
            "valid_until": "2099-12-31T23:59:59Z",
            "facts": ["The bounded no-Skill procedure is available in the named test host."],
        }
        supply["limitations"] = [
            "This local observation does not grant permission or scientific authority."
        ]
        supply_hash = self._write(root, supply_path, supply)

        resolution = copy.deepcopy(
            load_document(
                ROOT / "examples/capability-resolution/resolutions/no-skill-contract-check.yaml"
            )
        )
        resolution["qualification"] = "runtime-execution"
        resolution["method_resolution_ref"]["document_path"] = method_path
        resolution["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        resolution["requirement_ref"]["document_path"] = requirement_path
        resolution["requirement_ref"]["content_hash"] = "sha256:" + requirement_hash
        resolution["candidate_supply_report_refs"][0]["document_path"] = supply_path
        resolution["candidate_supply_report_refs"][0]["content_hash"] = "sha256:" + supply_hash
        resolution_hash = self._write(root, resolution_path, resolution)

        snapshot = copy.deepcopy(
            load_document(
                ROOT / "examples/capability-resolution/snapshots/no-skill-contract-check.yaml"
            )
        )
        snapshot["qualification"] = "runtime-execution"
        snapshot["task_ref"]["document_path"] = task_path
        snapshot["task_ref"]["content_hash"] = "sha256:" + task_hash
        snapshot["method_resolution_ref"]["document_path"] = method_path
        snapshot["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        snapshot["requirement_ref"]["document_path"] = requirement_path
        snapshot["requirement_ref"]["content_hash"] = "sha256:" + requirement_hash
        snapshot["resolution_ref"]["document_path"] = resolution_path
        snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
        snapshot["selected_supply_report_ref"]["document_path"] = supply_path
        snapshot["selected_supply_report_ref"]["content_hash"] = "sha256:" + supply_hash
        snapshot["supply_identity"] = copy.deepcopy(supply["supply_identity"])
        snapshot["conformance_evidence_refs"] = [
            {"path": evidence_path, "sha256": evidence_hash}
        ]
        snapshot["limitations"] = [
            "The Snapshot is qualified only for the bounded local Runtime bundle test."
        ]
        snapshot["boundaries"]["execution_input"] = True
        snapshot_hash = self._write(root, snapshot_path, snapshot)

        documents = [
            ("task_packet", task_path, task_hash),
            ("method_resolution", method_path, method_hash),
            ("capability_requirement", requirement_path, requirement_hash),
            ("capability_conformance_evidence", evidence_path, evidence_hash),
            ("capability_supply_report", supply_path, supply_hash),
            ("capability_resolution", resolution_path, resolution_hash),
            ("resolved_capability_snapshot", snapshot_path, snapshot_hash),
        ]
        imports = [
            (snapshot_path, task_path, "snapshot-task"),
            (snapshot_path, method_path, "snapshot-method"),
            (snapshot_path, requirement_path, "snapshot-requirement"),
            (snapshot_path, resolution_path, "snapshot-resolution"),
            (snapshot_path, supply_path, "snapshot-supply"),
            (snapshot_path, evidence_path, "snapshot-conformance"),
            (method_path, task_path, "method-task"),
            (resolution_path, method_path, "resolution-method"),
            (resolution_path, requirement_path, "resolution-requirement"),
            (resolution_path, supply_path, "resolution-candidate-supply"),
            (supply_path, evidence_path, "supply-conformance"),
        ]
        manifest = {
            "schema_version": "0.1.0",
            "bundle_id": "RB-NO-SKILL-LOCAL-001",
            "revision": 1,
            "profile": "runtime-bundle",
            "execution_scope": {
                "kind": "action-capability-slice",
                "action_ref": "ES-A4@1.0.0",
                "requirement_id": "research-contract-check",
                "task_capability_closure": {
                    "required": ["document-read", "research-contract-check"],
                    "closed": ["research-contract-check"],
                    "task_completion": False,
                },
            },
            "entrypoint": {
                "kind": "resolved_capability_snapshot",
                "path": snapshot_path,
                "sha256": snapshot_hash,
            },
            "documents": [
                {"kind": kind, "path": path, "sha256": digest}
                for kind, path, digest in documents
            ],
            "imports": [
                {"from_path": source, "to_path": target, "relation": relation}
                for source, target, relation in imports
            ],
            "skill_extension": {"enabled": False},
            "boundaries": {
                "supply_selection": False,
                "execution_authority": False,
                "permission_grant": False,
                "fallback_authority": False,
            },
        }
        manifest_path = root / "bundle/manifest.yaml"
        self._write(root, "bundle/manifest.yaml", manifest)
        return manifest_path


class ExecutionViewFixture:
    """Build deterministic Profile/Policy/Binding inputs and a resolved View."""

    def _write(self, root: Path, relative: str, document: object) -> PinnedExecutionInput:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return PinnedExecutionInput(relative, hash_file(path))

    def _inputs(self, root: Path) -> dict[str, PinnedExecutionInput]:
        profile = {
            "schema_version": "0.1.0",
            "agent_profile_id": "method-resolver",
            "version": "1.0.0",
            "purpose": "Bounded no-Skill method execution.",
            "model_policy": {
                "class": "bounded",
                "default_slot": "worker",
                "required_capabilities": ["structured-output"],
            },
            "permission_ceiling": {
                "filesystem": "worktree-write",
                "network": "search-and-fetch",
                "external_write": "forbidden",
                "allowed_roots": ["work"],
            },
            "allowed_tool_capabilities": ["document-read", "research-contract-check"],
            "default_context_policy": "isolated-task",
            "delegation": {"allowed": False},
            "output_contracts": ["deterministic-check-report"],
        }
        common_policy = {
            "schema_version": "0.1.0",
            "version": "1.0.0",
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": "2027-01-01T00:00:00Z",
            "permission_ceiling": {
                "filesystem": "worktree-write",
                "network": "search-and-fetch",
                "external_write": False,
                "allowed_roots": ["work"],
            },
            "data_egress": {
                "policy": "allowlisted-only",
                "allowed_payloads": ["public-query"],
                "forbidden_payloads": ["project-context"],
            },
            "side_effects": {
                "policy": "allowlisted-only",
                "allowed_effects": ["task-local-check-report", "temporary-cache"],
            },
            "budget_ceiling": {"max_turns": 10, "max_seconds": 120},
            "boundaries": {
                "permission_grant": False,
                "supply_selection": False,
                "fallback_authority": False,
            },
        }
        data_policy = copy.deepcopy(common_policy)
        data_policy.update({"policy_id": "DP-LOCAL", "policy_kind": "data-policy"})
        host_policy = copy.deepcopy(common_policy)
        host_policy.update({"policy_id": "HP-LOCAL", "policy_kind": "host-policy"})
        host_policy["permission_ceiling"]["allowed_roots"] = [
            "work/TASK-MR-ES-FROZEN-001"
        ]
        host_policy["budget_ceiling"] = {"max_turns": 4, "max_output_tokens": 2048}
        digest = "1" * 64
        binding = {
            "schema_version": "0.1.0",
            "binding_id": "BIND-LOCAL-001",
            "revision": 1,
            "selected_supply_report_ref": "supply-no-skill-contract-check@1.0.0",
            "provider": {"ref": "local", "version": "1", "content_hash": digest},
            "adapter": {"ref": "local-procedure", "version": "1.0.0", "content_hash": digest},
            "model": {
                "ref": "bounded-local-model",
                "version": "1.0.0",
                "content_hash": digest,
                "model_class": "bounded",
                "slot": "worker",
                "capabilities": ["structured-output"],
            },
            "runtime": {"ref": "python", "version": "3.11+", "content_hash": digest},
            "host": {"ref": "bounded-test-host", "version": "1", "content_hash": digest},
            "boundaries": {
                "supply_selection": False,
                "automatic_fallback": False,
                "permission_grant": False,
                "method_decision": False,
            },
        }
        host_policy["subject_host"] = copy.deepcopy(binding["host"])
        return {
            "agent_profile": self._write(root, "view/profile.yaml", profile),
            "data_policy": self._write(root, "view/data-policy.yaml", data_policy),
            "host_policy": self._write(root, "view/host-policy.yaml", host_policy),
            "execution_binding": self._write(root, "view/binding.yaml", binding),
        }

    def _build(self, root: Path) -> tuple[Any, dict[str, PinnedExecutionInput]]:
        manifest_path = RuntimeBundleFixture()._build_bundle(root)
        bundle = load_runtime_bundle(
            manifest_path, project_root=root, schema_root=ROOT / "schemas"
        )
        return bundle, self._inputs(root)

    def _produce(
        self,
        root: Path,
        bundle: Any,
        inputs: dict[str, PinnedExecutionInput],
    ) -> Any:
        return produce_resolved_execution_view(
            bundle,
            **inputs,
            execution_at="2026-08-26T00:00:00Z",
            view_id="VIEW-LOCAL-001",
            expected_bundle_sha256=hash_file(bundle.manifest_path),
            schema_root=ROOT / "schemas",
        )


class SequenceClock:
    def __init__(self, *timestamps: str):
        self._values = [
            datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps
        ]

    def now(self) -> datetime:
        return self._values.pop(0)


def plain(value: Any) -> Any:
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
    def binding(self) -> Any:
        return self._binding

    @property
    def selected_supply_report_ref(self) -> str:
        return self._supply_ref

    def execute(self, request: Any) -> ExecutionDriverResult:
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
                    "contract": "deterministic-check-report",
                    "path": "work/TASK-MR-ES-FROZEN-001/method-resolution.yaml",
                    "sha256": hash_file(artifact),
                },
            ),
        )


class RaisingDriver(RecordingDriver):
    def execute(self, request: Any) -> ExecutionDriverResult:
        self.calls += 1
        raise RuntimeError("private provider response must not enter the report")
