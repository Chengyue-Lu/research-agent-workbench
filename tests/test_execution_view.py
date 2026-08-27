import copy
import inspect
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    ExecutionViewValidationError,
    PinnedExecutionInput,
    load_runtime_bundle,
    produce_resolved_execution_view,
)
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog
from tests import test_runtime_bundle as runtime_bundle_fixtures


ROOT = Path(__file__).resolve().parents[1]


class ExecutionViewTests(unittest.TestCase):
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

    def _build(self, root: Path) -> tuple[object, dict[str, PinnedExecutionInput]]:
        helper = runtime_bundle_fixtures.RuntimeBundleTests(methodName="runTest")
        manifest_path = helper._build_bundle(root)
        bundle = load_runtime_bundle(
            manifest_path, project_root=root, schema_root=ROOT / "schemas"
        )
        return bundle, self._inputs(root)

    def _produce(self, root: Path, bundle: object, inputs: dict[str, PinnedExecutionInput]):
        return produce_resolved_execution_view(
            bundle,
            **inputs,
            execution_at="2026-08-26T00:00:00Z",
            view_id="VIEW-LOCAL-001",
            expected_bundle_sha256=hash_file(bundle.manifest_path),
            schema_root=ROOT / "schemas",
        )

    def _codes(self, raised: object) -> set[str]:
        return {item.code for item in raised.exception.issues}

    def test_supply_neutral_view_freezes_exact_binding_and_tightest_intersection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            view = self._produce(root, bundle, inputs)
            self.assertEqual(
                [], SchemaCatalog(ROOT / "schemas").validate("resolved_execution_view", view)
            )
            self.assertEqual("forbidden", view["effective_constraints"]["permissions"]["network"])
            self.assertFalse(view["effective_constraints"]["permissions"]["external_write"])
            self.assertEqual(
                ["work/TASK-MR-ES-FROZEN-001"],
                view["effective_constraints"]["permissions"]["allowed_roots"],
            )
            self.assertEqual("forbidden", view["effective_constraints"]["data_egress"]["policy"])
            self.assertEqual(
                ["task-local-check-report"],
                view["effective_constraints"]["side_effects"]["allowed_effects"],
            )
            self.assertEqual(
                {"max_output_tokens": 2048, "max_seconds": 120, "max_turns": 4},
                view["effective_constraints"]["budget"],
            )
            self.assertEqual(
                "supply-no-skill-contract-check@1.0.0",
                view["selected_supply_report_ref"]["ref"],
            )
            self.assertEqual(
                [],
                view["profile_constraints"]["required_tool_capabilities"],
            )
            self.assertEqual(
                ["deterministic-check-report"],
                view["profile_constraints"]["required_output_contracts"],
            )
            self.assertEqual(
                {
                    "supply_selection": False,
                    "automatic_fallback": False,
                    "permission_grant": False,
                    "method_decision": False,
                    "claim_effect": False,
                    "human_decision": False,
                    "task_completion": False,
                    "execution": False,
                },
                view["boundaries"],
            )

    def test_supply_reselection_profile_drift_and_input_hash_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            binding_path = root / inputs["execution_binding"].path
            binding = load_document(binding_path)
            binding["selected_supply_report_ref"] = "supply-other@1.0.0"
            inputs["execution_binding"] = self._write(root, inputs["execution_binding"].path, binding)
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-SUPPLY-RESELECTION", self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            profile_path = root / inputs["agent_profile"].path
            profile = load_document(profile_path)
            profile["agent_profile_id"] = "other-profile"
            inputs["agent_profile"] = self._write(root, inputs["agent_profile"].path, profile)
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-PROFILE-IDENTITY-MISMATCH", self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            (root / inputs["data_policy"].path).write_text("changed: true\n", encoding="utf-8")
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-INPUT-HASH-MISMATCH", self._codes(raised))

    def test_stale_supply_or_policy_and_bundle_pin_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            policy_path = root / inputs["host_policy"].path
            policy = load_document(policy_path)
            policy["valid_until"] = "2026-08-25T23:59:59Z"
            inputs["host_policy"] = self._write(root, inputs["host_policy"].path, policy)
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-PREFLIGHT-BLOCKED", self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            with self.assertRaises(ExecutionViewValidationError) as raised:
                produce_resolved_execution_view(
                    bundle,
                    **inputs,
                    execution_at="2026-08-26T00:00:00Z",
                    view_id="VIEW-LOCAL-001",
                    expected_bundle_sha256="0" * 64,
                    schema_root=ROOT / "schemas",
                )
            self.assertIn("EXECUTION-VIEW-BUNDLE-PIN-MISMATCH", self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            bundle.manifest_path.write_bytes(
                bundle.manifest_path.read_bytes() + b"\n# changed after validated load\n"
            )
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-BUNDLE-PIN-MISMATCH", self._codes(raised))

    def test_unavailable_supply_and_disjoint_write_scope_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            supply_path = root / "bundle/supply.yaml"
            supply = load_document(supply_path)
            supply["availability"]["status"] = "unavailable"
            supply_hash = self._write(root, "bundle/supply.yaml", supply).sha256
            resolution_path = root / "bundle/resolution.yaml"
            resolution = load_document(resolution_path)
            resolution["candidate_supply_report_refs"][0]["content_hash"] = "sha256:" + supply_hash
            resolution_hash = self._write(root, "bundle/resolution.yaml", resolution).sha256
            snapshot_path = root / "bundle/snapshot.yaml"
            snapshot = load_document(snapshot_path)
            snapshot["selected_supply_report_ref"]["content_hash"] = "sha256:" + supply_hash
            snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
            snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot).sha256
            manifest = load_document(bundle.manifest_path)
            manifest["entrypoint"]["sha256"] = snapshot_hash
            replacements = {
                "bundle/supply.yaml": supply_hash,
                "bundle/resolution.yaml": resolution_hash,
                "bundle/snapshot.yaml": snapshot_hash,
            }
            for item in manifest["documents"]:
                if item["path"] in replacements:
                    item["sha256"] = replacements[item["path"]]
            manifest_pin = self._write(root, "bundle/manifest.yaml", manifest).sha256
            bundle = load_runtime_bundle(
                "bundle/manifest.yaml", project_root=root, schema_root=ROOT / "schemas"
            )
            with self.assertRaises(ExecutionViewValidationError) as raised:
                produce_resolved_execution_view(
                    bundle,
                    **inputs,
                    execution_at="2026-08-26T00:00:00Z",
                    view_id="VIEW-LOCAL-001",
                    expected_bundle_sha256=manifest_pin,
                    schema_root=ROOT / "schemas",
                )
            self.assertIn("EXECUTION-VIEW-PREFLIGHT-BLOCKED", self._codes(raised))

    def test_profile_tool_output_model_and_host_subject_mismatch_fail_closed(self) -> None:
        cases = (
            (
                "agent_profile",
                lambda document: document.update({"output_contracts": []}),
                "EXECUTION-VIEW-PROFILE-OUTPUT-CONTRACT",
            ),
            (
                "execution_binding",
                lambda document: document["model"].update({"model_class": "unbounded"}),
                "EXECUTION-VIEW-PROFILE-MODEL-POLICY",
            ),
            (
                "host_policy",
                lambda document: document["subject_host"].update({"ref": "other-host"}),
                "EXECUTION-VIEW-HOST-POLICY-SUBJECT",
            ),
        )
        for input_name, mutate, expected_code in cases:
            with self.subTest(input_name=input_name, expected_code=expected_code):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    bundle, inputs = self._build(root)
                    path = root / inputs[input_name].path
                    document = load_document(path)
                    mutate(document)
                    inputs[input_name] = self._write(root, inputs[input_name].path, document)
                    with self.assertRaises(ExecutionViewValidationError) as raised:
                        self._produce(root, bundle, inputs)
                    self.assertIn(expected_code, self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            host_path = root / inputs["host_policy"].path
            host = load_document(host_path)
            host["permission_ceiling"]["allowed_roots"] = ["other-root"]
            inputs["host_policy"] = self._write(root, inputs["host_policy"].path, host)
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-PREFLIGHT-BLOCKED", self._codes(raised))

    def test_procedure_supply_does_not_treat_task_capabilities_as_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            profile_path = root / inputs["agent_profile"].path
            profile = load_document(profile_path)
            profile["allowed_tool_capabilities"] = []
            inputs["agent_profile"] = self._write(
                root, inputs["agent_profile"].path, profile
            )
            view = self._produce(root, bundle, inputs)
            self.assertEqual([], view["profile_constraints"]["required_tool_capabilities"])

    def test_final_policy_intersection_must_still_satisfy_selected_supply(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, inputs = self._build(root)
            host_path = root / inputs["host_policy"].path
            host = load_document(host_path)
            host["permission_ceiling"]["filesystem"] = "read-only"
            inputs["host_policy"] = self._write(root, inputs["host_policy"].path, host)
            with self.assertRaises(ExecutionViewValidationError) as raised:
                self._produce(root, bundle, inputs)
            self.assertIn("EXECUTION-VIEW-PREFLIGHT-BLOCKED", self._codes(raised))
            self.assertIn("below selected Supply", str(raised.exception))

    def test_supply_satisfiability_covers_egress_and_side_effects(self) -> None:
        from research_workbench.execution import execution_view

        permissions = {
            "filesystem": "read-only",
            "network": "forbidden",
            "external_write": False,
            "allowed_roots": [],
        }
        forbidden_egress = {
            "policy": "forbidden",
            "allowed_payloads": [],
            "forbidden_payloads": ["project-context"],
        }
        no_effects = {"policy": "none", "allowed_effects": []}
        with self.assertRaisesRegex(ValueError, "data-egress"):
            execution_view._require_supply_satisfiable(
                permissions,
                {
                    "policy": "allowlisted-only",
                    "allowed_payloads": ["public-query"],
                    "forbidden_payloads": ["project-context"],
                },
                no_effects,
                permissions,
                forbidden_egress,
                no_effects,
            )
        with self.assertRaisesRegex(ValueError, "side-effect"):
            execution_view._require_supply_satisfiable(
                permissions,
                forbidden_egress,
                {
                    "policy": "allowlisted-only",
                    "allowed_effects": ["temporary-cache"],
                },
                permissions,
                forbidden_egress,
                no_effects,
            )

    def test_view_producer_has_no_execution_fallback_or_skill_evolution_imports(self) -> None:
        from research_workbench.execution import execution_view

        source = inspect.getsource(execution_view)
        self.assertNotIn(".rglob(", source)
        self.assertNotIn("capability.lifecycle", source)
        self.assertNotIn("capability.skill_needs", source)
        self.assertNotIn("evaluation", source)
        self.assertNotIn("ProviderPort", source)
        self.assertNotIn("run_session", source)


if __name__ == "__main__":
    unittest.main()
