"""Contract tests for execution.compiler.compile_execution (K-API-2 §3)."""

from __future__ import annotations

import contextlib
import json
import unittest
from dataclasses import replace
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability import (
    AcceptedSkillRegistry,
    AgentProfile,
    ResolvedTask,
    resolve_task,
    resolve_task_from_registry,
)
from research_workbench.contracts import ContractError, to_plain
from research_workbench.execution import ExecutionPlan, ExecutionPlanError
from research_workbench.execution.compiler import compile_execution
from research_workbench.io import load_document
from research_workbench.tasks import TaskPacket

from support import ROOT, temporary_workspace

TASK_PATH = ROOT / "examples/task-evidence.yaml"
PROFILE_PATH = ROOT / "registry/agents/evidence-scout.yaml"
INPUT_PATH = ROOT / "examples/fixtures/paper-001.txt"
SKILL_SOURCE_PATH = ROOT / ".agents/skills/literature-evidence-extraction/SKILL.md"

MODEL_ENV = "RWB_WORKER_MODEL"
MODEL_VALUE = "claude-test-worker"
STARTED_AT = "2026-08-19T00:00:00Z"


def load_task() -> TaskPacket:
    return TaskPacket.from_mapping(load_document(TASK_PATH))


def load_profile() -> AgentProfile:
    return AgentProfile.from_mapping(load_document(PROFILE_PATH))


def resolve_assignment(task: TaskPacket | None = None, profile: AgentProfile | None = None) -> ResolvedTask:
    registry = AcceptedSkillRegistry.load(project_root=ROOT)
    return resolve_task_from_registry(
        task or load_task(),
        profile or load_profile(),
        registry,
        resolution_purpose="historical-replay",
    )


def pool_document(**slot_overrides: object) -> dict:
    slot = {
        "slot_id": "worker",
        "role": "worker",
        "provider_adapter": "anthropic-messages",
        "model_env": MODEL_ENV,
        "enabled": True,
        "capabilities": ["text", "tools", "structured_output"],
    }
    slot.update(slot_overrides)
    return {
        "schema_version": "0.1.0",
        "registry_kind": "model_pool",
        "pool_id": "compiler-test-pool",
        "selection_policy": "explicit-slot-only",
        "slots": [slot],
    }


ADAPTERS_DOCUMENT = {
    "schema_version": "0.1.0",
    "registry_kind": "provider_adapters",
    "adapters": [
        {
            "adapter_id": "anthropic-messages",
            "provider": "anthropic",
            "enabled": True,
            "base_url": "https://api.anthropic.com/v1",
            "credential_env": "ANTHROPIC_API_KEY",
            "model_env": "RWB_ANTHROPIC_MODEL",
            "capabilities": ["text", "tools", "structured_output"],
            "live_conformance": "pending",
        }
    ],
}


class CompileExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        self.workspace = self._stack.enter_context(temporary_workspace())
        self.assignment_path = self._write_yaml("assignment.yaml", to_plain(resolve_assignment()))
        self.pool_path = self._write_yaml("pool.yaml", pool_document())
        self.adapters_path = self._write_yaml("adapters.yaml", ADAPTERS_DOCUMENT)

    def _write_yaml(self, name: str, document: object) -> Path:
        path = self.workspace / name
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return path

    def _compile(self, **overrides: object) -> ExecutionPlan:
        arguments = {
            "task_path": TASK_PATH,
            "assignment_path": self.assignment_path,
            "slot": "worker",
            "pool_path": self.pool_path,
            "adapters_path": self.adapters_path,
            "root": ROOT,
            "environment": {MODEL_ENV: MODEL_VALUE},
            "started_at": STARTED_AT,
        }
        arguments.update(overrides)
        return compile_execution(**arguments)  # type: ignore[arg-type]

    def _compile_risk_codes(self, **overrides: object) -> set[str]:
        with self.assertRaises(ExecutionPlanError) as caught:
            self._compile(**overrides)
        return {risk.code for risk in caught.exception.risks}

    def test_compiles_frozen_task_into_execution_plan(self) -> None:
        plan = self._compile(attempt_id="A-ABCDEF012345")
        self.assertEqual("A-ABCDEF012345", plan.attempt_id)
        self.assertEqual("EVID-001", plan.task_id)
        self.assertEqual(1, plan.task_revision)
        self.assertEqual(str(ROOT), plan.root)
        self.assertEqual("work/EVID-001/A-ABCDEF012345", plan.attempt_dir)
        self.assertEqual(STARTED_AT, plan.started_at)

        binding = plan.model_binding
        self.assertEqual("worker", binding.slot_id)
        self.assertEqual("anthropic-messages", binding.provider_adapter)
        self.assertEqual("anthropic", binding.provider)
        self.assertEqual(MODEL_VALUE, binding.model)
        self.assertIsNone(binding.reasoning_effort)
        self.assertEqual("anthropic", plan.provider)

        limits = plan.limits
        self.assertEqual(10, limits.max_model_turns)
        self.assertEqual(1800, limits.max_output_tokens_per_turn)
        self.assertEqual(900.0, limits.max_seconds)
        self.assertEqual(12, limits.max_tool_calls)
        self.assertEqual(8, limits.max_parallel_tool_calls)
        self.assertEqual(8000, limits.max_tool_result_chars)
        self.assertEqual({"read-only", "local-write"}, set(limits.allowed_tool_side_effects))

        self.assertEqual(("literature-evidence-extraction@0.1.0",), plan.skill_lock)
        self.assertEqual(("examples/fixtures/paper-001.txt",), plan.readable_inputs)
        self.assertEqual(("work/EVID-001/**",), plan.write_scope)
        self.assertEqual(
            ("evidence-record", "handoff-transfer-manifest", "handoff-packet"),
            plan.required_outputs,
        )
        self.assertEqual(1, len(plan.input_lock))
        self.assertEqual(hash_file(INPUT_PATH), plan.input_lock[0].sha256)
        self.assertTrue(plan.handoff_policy.require_transfer_manifest)
        self.assertEqual("registry/agents/evidence-scout.yaml", plan.profile_ref)
        self.assertEqual(str(self.assignment_path), plan.assignment_ref)

        request = plan.request
        self.assertEqual(MODEL_VALUE, request.model)
        self.assertEqual(
            ["read_file", "write_artifact", "list_outputs"],
            [tool.name for tool in request.tools],
        )
        self.assertEqual("json_schema", request.response_format.kind)
        self.assertEqual("execution_closeout", request.response_format.name)
        self.assertEqual(["system", "user"], [message.role for message in request.messages])

        system_text = request.messages[0].content[0].text or ""
        user_text = request.messages[1].content[0].text or ""
        self.assertIn("evidence-scout@0.1.0", system_text)
        self.assertIn("Perform read-heavy evidence extraction", system_text)
        self.assertIn("literature-evidence-extraction@0.1.0", system_text)
        self.assertIn(SKILL_SOURCE_PATH.read_text(encoding="utf-8")[:200], system_text)
        self.assertIn("handoff-transfer-manifest", system_text)
        self.assertIn("require_transfer_manifest=true", system_text)

        self.assertIn("Extract citable evidence for Q-001", user_text)
        self.assertIn("examples/fixtures/paper-001.txt", user_text)
        self.assertIn(hash_file(INPUT_PATH), user_text)
        self.assertIn("work/EVID-001/**", user_text)
        self.assertIn("required_outputs_complete", user_text)

        raw_source = INPUT_PATH.read_text(encoding="utf-8").strip()
        self.assertNotIn(raw_source, system_text)
        self.assertNotIn(raw_source, user_text)
        json.dumps(plan.to_mapping())

    def test_attempt_id_defaults_to_prefixed_uppercase_hex(self) -> None:
        plan = self._compile()
        self.assertRegex(plan.attempt_id, r"^A-[0-9A-F]{12}$")
        self.assertEqual(f"work/EVID-001/{plan.attempt_id}", plan.attempt_dir)

    def test_model_override_binds_without_environment(self) -> None:
        plan = self._compile(environment={}, model_override="scripted-test-model")
        self.assertEqual("scripted-test-model", plan.model_binding.model)
        self.assertEqual("scripted-test-model", plan.request.model)

    def test_task_assignment_mismatch_blocks(self) -> None:
        drifted = self._write_yaml(
            "assignment-revision.yaml",
            to_plain(resolve_assignment(task=replace(load_task(), revision=2))),
        )
        self.assertEqual(
            {"EXEC-TASK-ASSIGNMENT-MISMATCH"},
            self._compile_risk_codes(assignment_path=drifted),
        )

    def test_profile_version_drift_blocks(self) -> None:
        drifted = self._write_yaml(
            "assignment-profile.yaml",
            to_plain(resolve_assignment(profile=replace(load_profile(), version="9.9.9"))),
        )
        self.assertEqual({"EXEC-PROFILE-MISMATCH"}, self._compile_risk_codes(assignment_path=drifted))

    def test_missing_profile_file_blocks(self) -> None:
        document = dict(load_document(TASK_PATH))
        document["agent_profile"] = "no-such-profile"
        task_path = self._write_yaml("task-unknown-profile.yaml", document)
        drifted_task = TaskPacket.from_mapping(document)
        drifted_profile = replace(load_profile(), agent_profile_id="no-such-profile")
        assignment_path = self._write_yaml(
            "assignment-unknown-profile.yaml",
            to_plain(resolve_assignment(task=drifted_task, profile=drifted_profile)),
        )
        self.assertEqual(
            {"EXEC-PROFILE-MISMATCH"},
            self._compile_risk_codes(task_path=task_path, assignment_path=assignment_path),
        )

    def test_stale_input_hash_blocks(self) -> None:
        document = dict(load_document(TASK_PATH))
        document["input_refs"] = [
            {"path": "examples/fixtures/paper-001.txt", "sha256": "0" * 64}
        ]
        task_path = self._write_yaml("task-stale-input.yaml", document)
        self.assertEqual({"EXEC-INPUT-STALE"}, self._compile_risk_codes(task_path=task_path))

    def test_skill_lock_drift_blocks(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        manifest = next(
            entry.manifest
            for entry in registry.entries
            if entry.skill_id == "literature-evidence-extraction"
        )
        drifted = replace(manifest, source_content_hash="f" * 64)
        assignment = resolve_task(load_task(), load_profile(), (drifted,))
        assignment_path = self._write_yaml("assignment-skill-drift.yaml", to_plain(assignment))
        self.assertEqual(
            {"EXEC-SKILL-DRIFT"},
            self._compile_risk_codes(assignment_path=assignment_path),
        )

    def test_missing_model_env_blocks(self) -> None:
        self.assertEqual({"EXEC-MODEL-UNBOUND"}, self._compile_risk_codes(environment={}))

    def test_disabled_slot_blocks(self) -> None:
        pool_path = self._write_yaml("pool-disabled.yaml", pool_document(enabled=False))
        self.assertEqual({"EXEC-MODEL-UNBOUND"}, self._compile_risk_codes(pool_path=pool_path))

    def test_unknown_slot_blocks(self) -> None:
        self.assertEqual({"EXEC-MODEL-UNBOUND"}, self._compile_risk_codes(slot="no-such-slot"))

    def test_unknown_adapter_blocks(self) -> None:
        pool_path = self._write_yaml(
            "pool-unknown-adapter.yaml",
            pool_document(provider_adapter="no-such-adapter"),
        )
        self.assertEqual({"EXEC-ADAPTER-MISMATCH"}, self._compile_risk_codes(pool_path=pool_path))

    def test_capability_superset_blocks(self) -> None:
        pool_path = self._write_yaml(
            "pool-superset.yaml",
            pool_document(capabilities=["text", "tools", "structured_output", "reasoning"]),
        )
        self.assertEqual({"EXEC-ADAPTER-MISMATCH"}, self._compile_risk_codes(pool_path=pool_path))

    def test_empty_write_scope_blocks(self) -> None:
        document = dict(load_document(TASK_PATH))
        document["write_scope"] = []
        task_path = self._write_yaml("task-empty-scope.yaml", document)
        self.assertEqual({"EXEC-WRITESCOPE-INVALID"}, self._compile_risk_codes(task_path=task_path))

    def test_absolute_write_scope_is_a_contract_error(self) -> None:
        document = dict(load_document(TASK_PATH))
        document["write_scope"] = ["/outside/the/root"]
        task_path = self._write_yaml("task-absolute-scope.yaml", document)
        with self.assertRaises(ContractError):
            self._compile(task_path=task_path)


if __name__ == "__main__":
    unittest.main()
