import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.adapters import CodexRuntimeAdapter
from research_workbench.artifacts import hash_file
from research_workbench.capability import (
    AcceptedSkillRegistry,
    AgentProfile,
    ResolvedTask,
    ResolutionError,
    resolve_task,
    resolve_task_from_registry,
)
from research_workbench.contracts import ContractError, to_plain
from research_workbench.io import load_document
from research_workbench.tasks import FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import SchemaCatalog, check_handoff_against_task


ROOT = Path(__file__).resolve().parents[1]


class AcceptedRegistryTests(unittest.TestCase):
    def test_registry_pins_live_skill_content(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        self.assertEqual(3, len(registry.entries))
        self.assertEqual(64, len(registry.digest))
        self.assertNotIn("rc-papercheck", {entry.skill_id for entry in registry.entries})
        self.assertEqual(
            {
                "literature-evidence-extraction": "legacy",
                "simulation-vv": "legacy",
                "handoff-integrity": "deprecated",
            },
            {entry.skill_id: entry.lifecycle for entry in registry.entries},
        )
        self.assertEqual((), registry.active_manifests)

    def test_new_assignment_cannot_select_legacy_or_deprecated_skill(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        with self.assertRaises(ResolutionError) as context:
            resolve_task_from_registry(task, profile, registry)
        self.assertEqual({"SKILL-INACTIVE"}, {risk.code for risk in context.exception.risks})

    def test_historical_replay_requires_exact_version(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        exact_task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        unversioned_task = replace(
            exact_task,
            required_skills=("literature-evidence-extraction",),
        )
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        with self.assertRaises(ResolutionError) as context:
            resolve_task_from_registry(
                unversioned_task,
                profile,
                registry,
                resolution_purpose="historical-replay",
            )
        self.assertEqual(
            {"SKILL-VERSION-REQUIRED"},
            {risk.code for risk in context.exception.risks},
        )

    def test_existing_assignment_remains_self_verifiable(self) -> None:
        document = load_document(ROOT / "examples/vertical-slice/evidence-assignment.yaml")
        assignment = ResolvedTask.from_mapping(document)
        self.assertEqual("literature-evidence-extraction@0.1.0", assignment.skill_lock[0].identifier)
        self.assertEqual([], SchemaCatalog().validate("skill_assignment", document))

    def test_unversioned_direct_resolution_blocks_multiple_manifest_versions(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        manifest = next(
            entry.manifest
            for entry in registry.entries
            if entry.skill_id == "literature-evidence-extraction"
        )
        newer = replace(manifest, version="0.2.0")
        exact_task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        unversioned_task = replace(
            exact_task,
            required_skills=("literature-evidence-extraction",),
        )
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        with self.assertRaises(ResolutionError) as context:
            resolve_task(unversioned_task, profile, (manifest, newer))
        self.assertIn(
            "SKILL-VERSION-AMBIGUOUS",
            {risk.code for risk in context.exception.risks},
        )
        resolved = resolve_task(exact_task, profile, (manifest, newer))
        self.assertEqual("literature-evidence-extraction@0.1.0", resolved.skill_lock[0].identifier)

    def test_live_skill_drift_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "registry", root / "registry")
            shutil.copytree(ROOT / ".agents", root / ".agents")
            path = root / ".agents" / "skills" / "simulation-vv" / "SKILL.md"
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source content drift"):
                AcceptedSkillRegistry.load(project_root=root)

    def test_script_only_drift_is_blocked_by_package_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "registry", root / "registry")
            shutil.copytree(ROOT / ".agents", root / ".agents")
            path = root / ".agents" / "skills" / "simulation-vv" / "scripts" / "check_vv_report.py"
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "package drift"):
                AcceptedSkillRegistry.load(project_root=root)

    def test_two_vertical_slices_have_distinct_deterministic_assignments(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        evidence_task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        simulation_task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-simulation.yaml"))
        evidence_profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        simulation_profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/simulation-auditor.yaml"))
        evidence = resolve_task_from_registry(
            evidence_task, evidence_profile, registry, resolution_purpose="historical-replay"
        )
        repeated = resolve_task_from_registry(
            evidence_task, evidence_profile, registry, resolution_purpose="historical-replay"
        )
        simulation = resolve_task_from_registry(
            simulation_task, simulation_profile, registry, resolution_purpose="historical-replay"
        )
        self.assertEqual(evidence.assignment_id, repeated.assignment_id)
        self.assertNotEqual(evidence.assignment_id, simulation.assignment_id)
        self.assertEqual("literature-evidence-extraction", evidence.skill_lock[0].skill_id)
        self.assertEqual("simulation-vv", simulation.skill_lock[0].skill_id)
        self.assertEqual([], SchemaCatalog().validate("skill_assignment", to_plain(evidence)))

    def test_assignment_id_detects_tampered_execution_fields(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        document = to_plain(
            resolve_task_from_registry(
                task, profile, registry, resolution_purpose="historical-replay"
            )
        )
        document["output_contracts"] = ["unrelated-output"]
        with self.assertRaises(ContractError):
            ResolvedTask.from_mapping(document)

    def test_handoff_skill_summary_must_match_full_assignment(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        assignment = resolve_task_from_registry(
            task, profile, registry, resolution_purpose="historical-replay"
        )
        handoff = HandoffPacket.from_mapping(load_document(ROOT / "examples/handoff-evidence.yaml"))
        drifted = replace(handoff, skill_lock=("simulation-vv@0.1.0",))
        risks = check_handoff_against_task(task, drifted, project_root=ROOT, assignment=assignment)
        self.assertIn("HANDOFF-ASSIGNMENT-SKILL-DRIFT", {risk.code for risk in risks})


class CodexAdapterTests(unittest.TestCase):
    def test_project_layout_and_profiles_are_model_unpinned(self) -> None:
        adapter = CodexRuntimeAdapter(ROOT, platform_version="contract-test")
        self.assertEqual((), adapter.validate_project_layout())
        for name in ("coordinator", "evidence-scout", "simulation-auditor", "targeted-reviewer"):
            profile = AgentProfile.from_mapping(load_document(ROOT / f"registry/agents/{name}.yaml"))
            config = adapter.resolve_agent(profile)
            self.assertIsNone(config.model)

    def test_dispatch_prompt_contains_only_selected_skill_and_references(self) -> None:
        adapter = CodexRuntimeAdapter(ROOT)
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        assignment = resolve_task_from_registry(
            task, profile, registry, resolution_purpose="historical-replay"
        )
        prompt = adapter.render_task_prompt(task, profile, assignment)
        raw_source = (ROOT / "examples/fixtures/paper-001.txt").read_text(encoding="utf-8")
        self.assertIn("$literature-evidence-extraction", prompt)
        self.assertNotIn("$simulation-vv", prompt)
        self.assertNotIn(raw_source, prompt)
        self.assertLess(len(prompt), 2000)

    def test_untrusted_source_instructions_do_not_enter_dispatch_context(self) -> None:
        adapter = CodexRuntimeAdapter(ROOT)
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        original = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        source = ROOT / "tests/fixtures/adversarial/source-prompt-injection.txt"
        task = replace(
            original,
            input_refs=(
                FileReference(
                    "tests/fixtures/adversarial/source-prompt-injection.txt",
                    hash_file(source),
                ),
            ),
        )
        profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        assignment = resolve_task_from_registry(
            task, profile, registry, resolution_purpose="historical-replay"
        )
        prompt = adapter.render_task_prompt(task, profile, assignment)
        self.assertIn("source-prompt-injection.txt", prompt)
        self.assertNotIn("Ignore the Task Packet", prompt)


class RepositorySkillScriptTests(unittest.TestCase):
    def run_script(self, relative_script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, str(ROOT / relative_script), *map(str, arguments)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_evidence_checker_accepts_pinned_fixture(self) -> None:
        result = self.run_script(
            ".agents/skills/literature-evidence-extraction/scripts/check_evidence_record.py",
            "examples/objects/evidence/EVID-001-01.yaml",
            "--source",
            "examples/fixtures/paper-001.txt",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_evidence_checker_blocks_stale_source(self) -> None:
        result = self.run_script(
            ".agents/skills/literature-evidence-extraction/scripts/check_evidence_record.py",
            "examples/objects/evidence/EVID-001-01.yaml",
            "--source",
            "examples/fixtures/run-manifest.txt",
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("EVIDENCE-SOURCE-HASH", result.stdout)

    def test_vv_checker_blocks_claim_overreach_and_missing_evidence(self) -> None:
        valid = self.run_script(
            ".agents/skills/simulation-vv/scripts/check_vv_report.py",
            "tests/fixtures/valid/simulation-vv-report.yaml",
        )
        invalid = self.run_script(
            ".agents/skills/simulation-vv/scripts/check_vv_report.py",
            "tests/fixtures/invalid/simulation-vv-report.yaml",
        )
        self.assertEqual(0, valid.returncode, valid.stdout + valid.stderr)
        self.assertEqual(1, invalid.returncode)
        self.assertIn("claim_ceiling", invalid.stdout)

    def test_handoff_checker_accepts_structural_fixture(self) -> None:
        result = self.run_script(
            ".agents/skills/handoff-integrity/scripts/check_handoff.py",
            "examples/handoff-evidence.yaml",
            "--task",
            "examples/task-evidence.yaml",
            "--root",
            ".",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_handoff_checker_can_assess_transfer_manifest_without_semantic_overclaim(self) -> None:
        result = self.run_script(
            ".agents/skills/handoff-integrity/scripts/check_handoff.py",
            "examples/handoff-evidence.yaml",
            "--task",
            "examples/task-evidence.yaml",
            "--root",
            ".",
            "--audit",
            "examples/handoff-transfer-audit-evidence.yaml",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("verdict=structurally-ready", result.stdout)
        self.assertIn("HANDOFF-SEMANTIC-UNREVIEWED", result.stdout)


if __name__ == "__main__":
    unittest.main()
