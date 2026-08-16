import hashlib
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.adapters.models import (
    ApiSessionLimits,
    Capability,
    ClientTool,
    ModelBinding,
    ProviderCapabilities,
    load_provider_adapter_configs,
)
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.execution import (
    API_TASK_OUTPUT_SCHEMA,
    ApiExecutionCompilationError,
    DocumentReadBoundaryError,
    build_document_read_tool,
    compile_api_execution,
    verify_execution_material,
)
from research_workbench.execution.contracts import default_execution_contract_registry
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket

ROOT = Path(__file__).resolve().parents[1]


class ApiExecutionCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = ProjectProtocol.from_mapping(load_document(ROOT / "examples/project-protocol.yaml"))
        cls.task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        cls.profile = AgentProfile.from_mapping(
            load_document(ROOT / "examples/profiles/evidence-scout.yaml")
        )
        cls.assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/evidence-assignment.yaml")
        )

    def runtime_limits(self, **overrides) -> ApiSessionLimits:
        values = {
            "max_model_turns": 4,
            "max_tool_calls": 3,
            "max_parallel_tool_calls": 1,
            "max_tool_result_chars": 4096,
            "max_output_tokens_per_turn": 900,
            "max_seconds": 20,
            "max_total_tokens": 5000,
        }
        values.update(overrides)
        return ApiSessionLimits(**values)

    def binding(self, **overrides) -> ModelBinding:
        values = {
            "slot_id": "worker",
            "role": "worker",
            "provider_adapter": "fake-local",
            "model": "worker-model",
            "capabilities": frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            "reasoning_effort": None,
            "specialties": (),
        }
        values.update(overrides)
        return ModelBinding(**values)

    def provider(self, **overrides) -> ProviderCapabilities:
        values = {
            "provider": "fake-local",
            "adapter_version": "fixture-1",
            "supported": frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            "models": ("worker-model",),
            "deployment": "local",
        }
        values.update(overrides)
        return ProviderCapabilities(**values)

    def compile(
        self,
        *,
        root=ROOT,
        protocol=None,
        task=None,
        profile=None,
        assignment=None,
        binding=None,
        provider=None,
        limits=None,
        catalog=None,
    ):
        task = task or self.task
        assignment = assignment or self.assignment
        material = verify_execution_material(root, task, assignment)
        catalog = catalog or {"document-read": build_document_read_tool(root, task)}
        return compile_api_execution(
            protocol=protocol or self.protocol,
            task=task,
            profile=profile or self.profile,
            assignment=assignment,
            binding=binding or self.binding(),
            provider_capabilities=provider or self.provider(),
            verified_material=material,
            runtime_limits=limits or self.runtime_limits(),
            tool_catalog=catalog,
        )

    def test_happy_path_is_deterministic_and_contains_no_source_or_main_history(self) -> None:
        first = self.compile()
        second = self.compile()

        self.assertEqual(first.provider_name, second.provider_name)
        self.assertEqual(first.request, second.request)
        self.assertEqual(first.limits, second.limits)
        self.assertEqual("fake-local", first.provider_name)
        self.assertEqual("worker-model", first.request.model)
        self.assertEqual(API_TASK_OUTPUT_SCHEMA, first.request.response_format.schema)
        self.assertEqual(("document-read",), tuple(tool.name for tool in first.request.tools))
        prompt = "\n".join(
            block.text or "" for message in first.request.messages for block in message.content
        )
        source_text = (ROOT / "examples/fixtures/paper-001.txt").read_text(encoding="utf-8")
        self.assertNotIn(source_text.strip(), prompt)
        self.assertNotIn("Main State", prompt)
        self.assertIn("Selected Skill literature-evidence-extraction@0.1.0", prompt)
        self.assertIn("references/evidence-contract.md", prompt)
        self.assertEqual({}, first.request.extensions)

    def test_simulation_prompt_names_only_its_schema_and_tools(self) -> None:
        task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-simulation.yaml"))
        profile = AgentProfile.from_mapping(
            load_document(ROOT / "examples/profiles/simulation-auditor.yaml")
        )
        assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/simulation-assignment.yaml")
        )
        limits = self.runtime_limits(
            allowed_tool_side_effects=frozenset({"none", "read-only"})
        )
        contract = default_execution_contract_registry().require(task, assignment)
        tools = contract.build_tools(ROOT, task, limits)

        compiled = self.compile(
            task=task,
            profile=profile,
            assignment=assignment,
            limits=limits,
            catalog={tool.definition.name: tool for tool in tools},
        )
        prompt = "\n".join(
            block.text or ""
            for message in compiled.request.messages
            for block in message.content
        )

        self.assertIn("simulation_vv_api_output", prompt)
        self.assertIn("file-read", prompt)
        self.assertIn("bounded-compute", prompt)
        self.assertNotIn("api_task_output", prompt)
        self.assertNotIn("document-read", prompt)

    def test_budget_is_the_narrower_task_and_runtime_intersection(self) -> None:
        compiled = self.compile(limits=self.runtime_limits(max_model_turns=12, max_output_tokens_per_turn=3000, max_seconds=90))
        self.assertEqual(10, compiled.limits.max_model_turns)
        self.assertEqual(1800, compiled.limits.max_output_tokens_per_turn)
        self.assertEqual(90, compiled.limits.max_seconds)
        self.assertEqual(frozenset({"read-only"}), compiled.limits.allowed_tool_side_effects)

    def test_runtime_tool_side_effects_are_a_permission_ceiling(self) -> None:
        for label, allowed in (
            ("empty", frozenset()),
            ("only-none", frozenset({"none"})),
        ):
            with self.subTest(label=label), self.assertRaises(
                ApiExecutionCompilationError
            ) as raised:
                self.compile(
                    limits=self.runtime_limits(allowed_tool_side_effects=allowed)
                )
            self.assertEqual("TOOL-PERMISSION-ESCALATION", raised.exception.code)

        compiled = self.compile(
            limits=self.runtime_limits(
                allowed_tool_side_effects=frozenset({"read-only"})
            )
        )
        self.assertEqual(
            frozenset({"read-only"}), compiled.limits.allowed_tool_side_effects
        )

    def test_document_read_allows_only_frozen_refs_and_rechecks_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            tool = build_document_read_tool(root, self.task)
            value = tool.execute({"path": "examples/fixtures/paper-001.txt"})
            self.assertEqual(self.task.input_refs[0].sha256, value["sha256"])
            with self.assertRaisesRegex(DocumentReadBoundaryError, "DOCUMENT-READ-DENIED"):
                tool.execute({"path": "docs/CURRENT_HANDOFF.md"})
            (root / "examples/fixtures/paper-001.txt").write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(DocumentReadBoundaryError, "REF-HASH-MISMATCH"):
                tool.execute({"path": "examples/fixtures/paper-001.txt"})

    def test_document_read_enforces_the_explicit_byte_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            payload = (root / "examples/fixtures/paper-001.txt").read_bytes()

            exact = build_document_read_tool(
                root,
                self.task,
                max_bytes=len(payload),
            )
            self.assertEqual(
                self.task.input_refs[0].sha256,
                exact.execute({"path": "examples/fixtures/paper-001.txt"})["sha256"],
            )

            too_small = build_document_read_tool(
                root,
                self.task,
                max_bytes=len(payload) - 1,
            )
            with self.assertRaises(DocumentReadBoundaryError) as raised:
                too_small.execute({"path": "examples/fixtures/paper-001.txt"})
            self.assertEqual("DOCUMENT-READ-SIZE", raised.exception.code)

    def test_document_read_hashes_and_decodes_the_same_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            payload = b"\xff"
            (root / "examples/fixtures/paper-001.txt").write_bytes(payload)
            reference = replace(
                self.task.input_refs[0],
                sha256=hashlib.sha256(payload).hexdigest(),
            )
            task = replace(self.task, input_refs=(reference,))
            tool = build_document_read_tool(root, task)

            with self.assertRaisesRegex(DocumentReadBoundaryError, "DOCUMENT-READ-ENCODING"):
                tool.execute({"path": reference.path})

    def test_input_and_selected_skill_drift_block_before_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            (root / "examples/fixtures/paper-001.txt").write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(ApiExecutionCompilationError, "REF-HASH-MISMATCH"):
                verify_execution_material(root, self.task, self.assignment)
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            skill_ref = root / ".agents/skills/literature-evidence-extraction/references/evidence-contract.md"
            skill_ref.write_text(skill_ref.read_text(encoding="utf-8") + "\ndrift", encoding="utf-8")
            with self.assertRaisesRegex(ApiExecutionCompilationError, "ASSIGNMENT-SKILL-DRIFT"):
                verify_execution_material(root, self.task, self.assignment)

    def test_unselected_skill_canary_is_never_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            canary = root / ".agents/skills/final-synthesis/SKILL.md"
            canary.parent.mkdir(parents=True, exist_ok=True)
            canary.write_text("UNSELECTED-SKILL-CANARY-DO-NOT-INJECT", encoding="utf-8")
            compiled = self.compile(root=root)
            prompt = "\n".join(
                block.text or "" for message in compiled.request.messages for block in message.content
            )
            self.assertNotIn("UNSELECTED-SKILL-CANARY-DO-NOT-INJECT", prompt)

    def test_content_only_skill_lock_does_not_authorize_neighboring_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_material(Path(directory))
            canary = root / ".agents/skills/literature-evidence-extraction/UNLOCKED.md"
            canary.write_text("UNLOCKED-NEIGHBOR-CANARY", encoding="utf-8")
            content_only_lock = replace(self.assignment.skill_lock[0], package_hash=None)
            assignment = replace(self.assignment, skill_lock=(content_only_lock,))

            material = verify_execution_material(root, self.task, assignment)

            self.assertNotIn("UNLOCKED-NEIGHBOR-CANARY", material.skills[0].instructions)

    def test_slot_identity_and_capability_gaps_are_blocking_without_fallback(self) -> None:
        with self.assertRaisesRegex(ApiExecutionCompilationError, "MODEL-SLOT-MISMATCH"):
            self.compile(binding=self.binding(slot_id="primary"))
        with self.assertRaisesRegex(ApiExecutionCompilationError, "MODEL-CAPABILITY-GAP"):
            self.compile(binding=self.binding(capabilities=frozenset({Capability.TEXT})))
        with self.assertRaisesRegex(ApiExecutionCompilationError, "MODEL-NOT-SUPPORTED"):
            self.compile(provider=self.provider(models=("another-model",)))

    def test_real_adapter_ids_preserve_identity_and_capability_boundaries(self) -> None:
        adapters = load_provider_adapter_configs(ROOT / "registry/providers/adapters.yaml")
        zhipu = next(adapter for adapter in adapters if adapter.provider == "zhipu")
        self.assertTrue(
            {Capability.TOOLS, Capability.STRUCTURED_OUTPUT, Capability.REASONING}
            <= zhipu.capabilities
        )

        for adapter in adapters:
            with self.subTest(adapter_id=adapter.adapter_id, provider=adapter.provider):
                mutable_limits = {"requests_per_minute": 1}
                if Capability.TOOLS not in adapter.capabilities:
                    with self.assertRaisesRegex(
                        ApiExecutionCompilationError,
                        "MODEL-CAPABILITY-GAP: provider lacks: tools",
                    ):
                        self.compile(
                            binding=self.binding(provider_adapter=adapter.adapter_id),
                            provider=self.provider(
                                provider=adapter.provider,
                                supported=adapter.capabilities,
                                limits=mutable_limits,
                            ),
                        )
                    continue
                compiled = self.compile(
                    binding=self.binding(provider_adapter=adapter.adapter_id),
                    provider=self.provider(
                        provider=adapter.provider,
                        supported=adapter.capabilities,
                        limits=mutable_limits,
                    ),
                )

                self.assertEqual(adapter.adapter_id, compiled.adapter_id)
                self.assertEqual(adapter.adapter_id, compiled.provider_name)
                self.assertEqual(adapter.provider, compiled.provider_capabilities.provider)
                mutable_limits["requests_per_minute"] = 99
                self.assertEqual(1, compiled.provider_capabilities.limits["requests_per_minute"])
                with self.assertRaises(TypeError):
                    compiled.provider_capabilities.limits["requests_per_minute"] = 2

    def test_invalid_canonical_provider_identity_is_blocked(self) -> None:
        for provider_identity in ("", " anthropic"):
            with self.subTest(provider=provider_identity), self.assertRaisesRegex(
                ApiExecutionCompilationError, "PROVIDER-IDENTITY-INVALID"
            ):
                self.compile(provider=self.provider(provider=provider_identity))

    def test_local_only_project_rejects_remote_provider(self) -> None:
        with self.assertRaisesRegex(ApiExecutionCompilationError, "PROJECT-DATA-BOUNDARY"):
            self.compile(provider=self.provider(deployment="remote"))

    def test_remote_provider_requires_explicit_upload_approval_evidence(self) -> None:
        boundary = dict(self.protocol.data_boundary)
        boundary["local_only"] = False
        boundary["external_upload_requires_approval"] = True
        protocol = replace(self.protocol, data_boundary=boundary)
        with self.assertRaisesRegex(ApiExecutionCompilationError, "PROJECT-DATA-BOUNDARY"):
            self.compile(protocol=protocol, provider=self.provider(deployment="remote"))

    def test_closeout_requires_effective_worktree_write_permission(self) -> None:
        assignment = replace(
            self.assignment,
            effective_permissions=replace(
                self.assignment.effective_permissions,
                filesystem="read-only",
            ),
        )

        with self.assertRaisesRegex(ApiExecutionCompilationError, "TASK-PERMISSION-ESCALATION"):
            self.compile(assignment=assignment)

    def test_remote_provider_requires_effective_network_permission(self) -> None:
        boundary = dict(self.protocol.data_boundary)
        boundary["local_only"] = False
        boundary["external_upload_requires_approval"] = False
        protocol = replace(self.protocol, data_boundary=boundary)
        assignment = replace(
            self.assignment,
            effective_permissions=replace(
                self.assignment.effective_permissions,
                network="forbidden",
            ),
        )

        with self.assertRaisesRegex(ApiExecutionCompilationError, "TASK-PERMISSION-ESCALATION"):
            self.compile(
                protocol=protocol,
                assignment=assignment,
                provider=self.provider(deployment="remote"),
            )

    def test_mandatory_semantic_review_is_blocked_before_execution(self) -> None:
        task = replace(
            self.task,
            handoff_policy=replace(self.task.handoff_policy, semantic_review="required"),
        )
        with self.assertRaisesRegex(ApiExecutionCompilationError, "OUTPUT-CONTRACT-UNSUPPORTED"):
            self.compile(task=task)

    def test_compact_h1_handoff_is_blocked_until_risk_tiered_closeout_exists(self) -> None:
        task = replace(
            self.task,
            handoff_policy=replace(self.task.handoff_policy, require_transfer_manifest=False),
        )
        with self.assertRaisesRegex(ApiExecutionCompilationError, "OUTPUT-CONTRACT-UNSUPPORTED"):
            self.compile(task=task)

    def test_verified_material_seal_rejects_instruction_substitution(self) -> None:
        material = verify_execution_material(ROOT, self.task, self.assignment)
        forged_skill = replace(material.skills[0], instructions="FORGED-INSTRUCTIONS")
        forged_material = replace(material, skills=(forged_skill,))
        with self.assertRaisesRegex(ApiExecutionCompilationError, "ASSIGNMENT-SKILL-DRIFT"):
            compile_api_execution(
                protocol=self.protocol,
                task=self.task,
                profile=self.profile,
                assignment=self.assignment,
                binding=self.binding(),
                provider_capabilities=self.provider(),
                verified_material=forged_material,
                runtime_limits=self.runtime_limits(),
                tool_catalog={"document-read": build_document_read_tool(ROOT, self.task)},
            )

    def test_tool_scope_side_effect_and_missing_cumulative_ceiling_are_blocking(self) -> None:
        read_tool = build_document_read_tool(ROOT, self.task)
        write_tool = ClientTool(read_tool.definition, read_tool.execute, side_effect="local-write")
        with self.assertRaisesRegex(ApiExecutionCompilationError, "TOOL-PERMISSION-ESCALATION"):
            self.compile(catalog={"document-read": write_tool})
        with self.assertRaisesRegex(ApiExecutionCompilationError, "TOOL-UNAVAILABLE"):
            self.compile(catalog={"irrelevant": read_tool})
        with self.assertRaisesRegex(ApiExecutionCompilationError, "SESSION-BUDGET-UNBOUNDED"):
            self.compile(limits=self.runtime_limits(max_total_tokens=None))

    def test_assignment_identity_drift_is_rejected(self) -> None:
        drifted = replace(self.assignment, task_revision=99)
        with self.assertRaisesRegex(ApiExecutionCompilationError, "ASSIGNMENT-TASK-MISMATCH"):
            verify_execution_material(ROOT, self.task, drifted)

    @staticmethod
    def copy_material(destination: Path) -> Path:
        relative_files = (
            "examples/project-protocol.yaml",
            "examples/task-evidence.yaml",
            "examples/profiles/evidence-scout.yaml",
            "examples/vertical-slice/evidence-assignment.yaml",
            "examples/fixtures/paper-001.txt",
        )
        for relative in relative_files:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copytree(
            ROOT / ".agents/skills/literature-evidence-extraction",
            destination / ".agents/skills/literature-evidence-extraction",
        )
        return destination


if __name__ == "__main__":
    unittest.main()
