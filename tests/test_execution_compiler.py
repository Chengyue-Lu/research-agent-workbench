"""K-API-2 compiler contract tests.

The compiler is the pure boundary between frozen research contracts and a
fresh API session: it may only read the task inputs and the frozen skill
assignment, and must never carry main-agent history or unselected skills.
"""

import inspect
import shutil
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from research_workbench.adapters.models import Capability, ModelBinding
from research_workbench.capability.models import AgentProfile
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.execution import (
    CompileError,
    CompiledSession,
    ExecutionPolicy,
    compile_session,
)
from research_workbench.io import load_document
from research_workbench.tasks import TaskPacket


ROOT = Path(__file__).resolve().parents[1]

MAIN_HISTORY_SECRET = "MAIN-AGENT-SECRET-HISTORY-7f3a91"
UNSELECTED_SKILL_SECRET = "UNSELECTED-SKILL-SECRET-c91d55"


def build_project(destination: Path) -> Path:
    """Copy the minimal EVID-001 fixture set into an isolated project root."""

    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        ROOT / "examples" / "fixtures",
        destination / "examples" / "fixtures",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        ROOT / ".agents" / "skills" / "literature-evidence-extraction",
        destination / ".agents" / "skills" / "literature-evidence-extraction",
        dirs_exist_ok=True,
    )
    shutil.copy(
        ROOT / "examples" / "task-evidence.yaml",
        destination / "examples" / "task-evidence.yaml",
    )
    return destination


def load_contracts(root: Path) -> tuple[TaskPacket, AgentProfile, ResolvedTask]:
    task = TaskPacket.from_mapping(load_document(root / "examples" / "task-evidence.yaml"))
    profile = AgentProfile.from_mapping(
        load_document(ROOT / "registry" / "agents" / "evidence-scout.yaml")
    )
    assignment = ResolvedTask.from_mapping(
        load_document(ROOT / "examples" / "vertical-slice" / "evidence-assignment.yaml")
    )
    return task, profile, assignment


def worker_binding(**overrides) -> ModelBinding:
    values: dict = {
        "slot_id": "worker",
        "role": "worker",
        "provider_adapter": "fake-worker",
        "model": "worker-model",
        "capabilities": frozenset(
            {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
        ),
        "reasoning_effort": None,
        "specialties": (),
    }
    values.update(overrides)
    return ModelBinding(**values)


def compile_default(root: Path, **overrides) -> CompiledSession:
    binding_overrides = overrides.pop("binding", {})
    binding = (
        binding_overrides
        if isinstance(binding_overrides, ModelBinding)
        else worker_binding(**binding_overrides)
    )
    task, profile, assignment = load_contracts(root)
    return compile_session(task, profile, assignment, binding, root=root, **overrides)


class CompileSessionTests(unittest.TestCase):
    def test_compile_builds_minimal_fresh_request(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            compiled = compile_default(root)

            self.assertEqual("worker-model", compiled.request.model)
            self.assertEqual("fake-worker", compiled.provider_name)
            self.assertEqual(2, len(compiled.request.messages))
            self.assertEqual(
                ("system", "user"),
                tuple(message.role for message in compiled.request.messages),
            )
            # Bookkeeping fields live on CompiledSession, never on the wire
            # request: adapter metadata contracts are provider-specific
            # (Anthropic only transmits user_id; Gemini transmits none), so a
            # populated request.metadata makes live execution fail before the
            # first network round-trip.
            self.assertEqual({}, dict(compiled.request.metadata))
            task, _, assignment = load_contracts(root)
            self.assertEqual(task.task_id, compiled.task_id)
            self.assertEqual(assignment.assignment_id, compiled.assignment_id)
            self.assertEqual("worker", compiled.slot_id)
            self.assertTrue(compiled.attempt_id.startswith("A-"))

    def test_system_message_carries_goal_and_frozen_skill_instructions(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            compiled = compile_default(root)
            system_text = "".join(
                block.text or "" for block in compiled.request.messages[0].content
            )

            self.assertIn("Extract citable evidence for Q-001", system_text)
            self.assertIn("literature-evidence-extraction@0.1.0", system_text)
            self.assertIn(
                "Extract one atomic statement per Evidence object", system_text
            )
            self.assertIn("SA-9A9D7C442B60B3E8", system_text)

    def test_user_message_carries_only_declared_inputs(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            compiled = compile_default(root)
            user_text = "".join(
                block.text or "" for block in compiled.request.messages[1].content
            )

            self.assertIn("examples/fixtures/paper-001.txt", user_text)
            self.assertIn("Synthetic evidence fixture", user_text)
            self.assertIn("82ea6f0d2455b97cf98786d01b8b461953e1badba4491f168a04471b39820b67", user_text)

    def test_compile_does_not_inject_main_history_or_unselected_skills(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            history = root / "work" / "EVID-001" / "main-history.txt"
            history.parent.mkdir(parents=True, exist_ok=True)
            history.write_text(f"chat log: {MAIN_HISTORY_SECRET}", encoding="utf-8")
            decoy = root / ".agents" / "skills" / "decoy-unselected" / "SKILL.md"
            decoy.parent.mkdir(parents=True, exist_ok=True)
            decoy.write_text(f"decoy skill body {UNSELECTED_SKILL_SECRET}", encoding="utf-8")

            compiled = compile_default(root)
            rendered = "\n".join(
                message.role
                + "".join(
                    (block.text or "") + str(block.data or "") for block in message.content
                )
                for message in compiled.request.messages
            ) + "\n".join(tool.description for tool in compiled.request.tools)

            self.assertNotIn(MAIN_HISTORY_SECRET, rendered)
            self.assertNotIn(UNSELECTED_SKILL_SECRET, rendered)

    def test_compile_signature_only_accepts_frozen_contract_types(self) -> None:
        parameters = inspect.signature(compile_session).parameters
        self.assertEqual(
            ["task", "profile", "assignment", "binding", "root", "policy"],
            list(parameters),
        )
        keyword_only = {
            name
            for name, parameter in parameters.items()
            if parameter.kind == inspect.Parameter.KEYWORD_ONLY
        }
        self.assertEqual({"root", "policy"}, keyword_only)
        for name, parameter in parameters.items():
            if name in {"root", "policy"}:
                continue
            self.assertNotIn(
                "str",
                getattr(parameter.annotation, "__name__", str(parameter.annotation)),
                f"parameter {name} must not accept free-form strings",
            )

    def test_attempt_id_is_deterministic_and_sensitive(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            first = compile_default(root)
            second = compile_default(root)
            other_model = compile_default(root, binding={"model": "other-model"})

            self.assertEqual(first.attempt_id, second.attempt_id)
            self.assertNotEqual(first.attempt_id, other_model.attempt_id)

            from research_workbench.artifacts.integrity import hash_file

            paper = root / "examples" / "fixtures" / "paper-001.txt"
            paper.write_text(paper.read_text(encoding="utf-8") + "\nextra line", encoding="utf-8")
            task_document = load_document(root / "examples" / "task-evidence.yaml")
            task_document["input_refs"][0]["sha256"] = hash_file(paper)
            (root / "examples" / "task-evidence.yaml").write_text(
                yaml.safe_dump(task_document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            changed_input = compile_default(root)
            self.assertNotEqual(first.attempt_id, changed_input.attempt_id)

    def test_attempt_id_is_sensitive_to_session_limits(self) -> None:
        # Two runs under different execution bounds are different attempts:
        # they must never share a closeout batch or completion marker, so a
        # policy change cannot silently resume an already-closed batch.
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            first = compile_default(root)
            relaxed = compile_default(
                root, policy=replace(ExecutionPolicy(), max_parallel_tool_calls=2)
            )

            self.assertEqual(4, first.limits.max_parallel_tool_calls)
            self.assertEqual(2, relaxed.limits.max_parallel_tool_calls)
            self.assertNotEqual(first.attempt_id, relaxed.attempt_id)

    def test_task_budget_overrides_policy_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            compiled = compile_default(root)

            self.assertEqual(10, compiled.limits.max_model_turns)
            self.assertEqual(4096, compiled.limits.max_output_tokens_per_turn)
            self.assertEqual(600.0, compiled.limits.max_seconds)
            self.assertEqual(
                "task-budget", compiled.report.limit_sources["max_model_turns"]
            )
            self.assertEqual(
                "task-budget",
                compiled.report.limit_sources["max_output_tokens_per_turn"],
            )
            self.assertEqual(
                "policy-default", compiled.report.limit_sources["max_seconds"]
            )

    def test_policy_defaults_are_used_when_task_budget_is_absent(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task_document = load_document(root / "examples" / "task-evidence.yaml")
            task_document["budget"] = {}
            (root / "examples" / "task-evidence.yaml").write_text(
                yaml.safe_dump(task_document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            compiled = compile_default(root)

            self.assertEqual(6, compiled.limits.max_model_turns)
            self.assertEqual(4096, compiled.limits.max_output_tokens_per_turn)
            self.assertEqual(600.0, compiled.limits.max_seconds)
            self.assertEqual(8, compiled.limits.max_tool_calls)
            # Read-only per-turn fan-out default; side-effecting turns stay
            # serial regardless (see the session runner).
            self.assertEqual(4, compiled.limits.max_parallel_tool_calls)
            self.assertEqual(20000, compiled.limits.max_tool_result_chars)
            self.assertEqual(
                "policy-default", compiled.report.limit_sources["max_model_turns"]
            )

    def test_custom_policy_defaults_are_recorded(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            policy = replace(
                ExecutionPolicy(), default_max_model_turns=2, default_max_seconds=30.0
            )
            task_document = load_document(root / "examples" / "task-evidence.yaml")
            task_document["budget"] = {}
            (root / "examples" / "task-evidence.yaml").write_text(
                yaml.safe_dump(task_document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            compiled = compile_default(root, policy=policy)

            self.assertEqual(2, compiled.limits.max_model_turns)
            self.assertEqual(30.0, compiled.limits.max_seconds)
            self.assertEqual("policy-default", compiled.report.limit_sources["max_model_turns"])

    def test_stale_input_hash_blocks_compile(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            paper = root / "examples" / "fixtures" / "paper-001.txt"
            paper.write_text("tampered content", encoding="utf-8")

            with self.assertRaises(CompileError) as caught:
                compile_default(root)
            self.assertEqual("TASK-STALE-INPUT", caught.exception.code)

    def test_missing_input_file_blocks_compile(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            (root / "examples" / "fixtures" / "paper-001.txt").unlink()

            with self.assertRaises(CompileError) as caught:
                compile_default(root)
            self.assertEqual("COMPILE-INPUT-MISSING", caught.exception.code)

    def test_oversized_input_blocks_compile_without_truncation(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            policy = replace(ExecutionPolicy(), max_input_chars=64)

            with self.assertRaises(CompileError) as caught:
                compile_default(root, policy=policy)
            self.assertEqual("COMPILE-INPUT-TOO-LARGE", caught.exception.code)

    def test_skill_content_drift_blocks_compile(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            skill = root / ".agents" / "skills" / "literature-evidence-extraction" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8") + "\ndrifted instruction",
                encoding="utf-8",
            )

            with self.assertRaises(CompileError) as caught:
                compile_default(root)
            self.assertEqual("COMPILE-SKILL-DRIFT", caught.exception.code)

    def test_slot_capability_gap_blocks_compile(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            binding = worker_binding(
                capabilities=frozenset({Capability.TEXT, Capability.TOOLS})
            )
            with self.assertRaises(CompileError) as caught:
                compile_default(root, binding=binding)
            self.assertEqual("COMPILE-CAPABILITY-GAP", caught.exception.code)

    def test_tool_resolution_requires_intersection_and_implementation(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, profile, assignment = load_contracts(root)

            with self.assertRaises(CompileError) as unimplemented:
                compile_session(
                    task,
                    profile,
                    replace(assignment, resolved_tools=("web-search",)),
                    worker_binding(),
                    root=root,
                )
            self.assertEqual("COMPILE-TOOL-UNAVAILABLE", unimplemented.exception.code)

            with self.assertRaises(CompileError) as not_allowed:
                compile_session(
                    task,
                    replace(profile, allowed_tool_capabilities=("file-read",)),
                    assignment,
                    worker_binding(),
                    root=root,
                )
            self.assertEqual("COMPILE-TOOL-NOT-ALLOWED", not_allowed.exception.code)

            compiled = compile_default(root)
            self.assertEqual(("document-read",), tuple(tool.definition.name for tool in compiled.tools))
            self.assertEqual(
                {tool.definition.name for tool in compiled.tools},
                {tool.name for tool in compiled.request.tools},
            )
            self.assertTrue(all(tool.side_effect == "read-only" for tool in compiled.tools))

    def test_attempt_id_covers_the_task_body(self) -> None:
        """M-1 regression: editing the task goal without a revision bump must
        change the attempt identity instead of silently reusing the batch."""

        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            first = compile_default(root)

            import yaml as yaml_module

            task_document = load_document(root / "examples" / "task-evidence.yaml")
            task_document["goal"] = "Edited instruction that must not reuse the old attempt."
            (root / "examples" / "task-evidence.yaml").write_text(
                yaml_module.safe_dump(task_document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            edited = compile_default(root)

            self.assertNotEqual(first.attempt_id, edited.attempt_id)

    def test_evidence_contract_requires_at_least_one_input(self) -> None:
        """M-2 regression: a zero-input evidence task must fail at compile
        time, before the model session runs."""

        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            import yaml as yaml_module

            task_document = load_document(root / "examples" / "task-evidence.yaml")
            task_document["input_refs"] = []
            (root / "examples" / "task-evidence.yaml").write_text(
                yaml_module.safe_dump(task_document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            with self.assertRaises(CompileError) as caught:
                compile_default(root)
            self.assertEqual("COMPILE-INPUT-MISSING", caught.exception.code)

    def test_structured_output_contract_is_frozen(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            compiled = compile_default(root)

            self.assertEqual("json_schema", compiled.request.response_format.kind)
            self.assertEqual("evidence-extraction-result", compiled.request.response_format.name)
            required = set(compiled.request.response_format.schema["required"])
            self.assertEqual(
                {
                    "statement",
                    "source_locator",
                    "quality_flags",
                    "summary",
                    "facts",
                    "inferences",
                    "recommendations",
                    "limitations",
                    "unresolved",
                },
                required,
            )
            self.assertEqual("evidence-record", compiled.output_contract)
            self.assertEqual(frozenset({Capability.STRUCTURED_OUTPUT}), compiled.request.capability_requirements)


if __name__ == "__main__":
    unittest.main()
