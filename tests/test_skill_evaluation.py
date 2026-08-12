import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_directory, hash_file
from research_workbench.capability import SkillLock
from research_workbench.capability.resolver import _assignment_identifier
from research_workbench.cli import main
from research_workbench.context import (
    CONTEXT_METRIC_NAMES,
    ContextPolicySnapshot,
    ContextSnapshot,
    DEFAULT_CONTEXT_THRESHOLDS,
)
from research_workbench.evaluation import assess_skill_evaluation
from research_workbench.contracts import PermissionPolicy
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _file_ref(path: Path, root: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": hash_file(path)}


def _check_report(
    root: Path,
    path: Path,
    checker: Path,
    source: Path,
    output: Path,
    *,
    status: str,
) -> None:
    _write_json(
        path,
        {
            "schema_version": "0.1.0",
            "report_id": f"DCR-{path.stem}",
            "checker": {
                "checker_id": "fixture-checker",
                "version": "0.1.0",
                "source_ref": _file_ref(checker, root),
            },
            "subject_refs": [_file_ref(source, root), _file_ref(output, root)],
            "status": status,
            "checks": [
                {
                    "code": "FIXTURE-CHECK",
                    "status": status,
                    "detail": "fixture result",
                }
            ],
            "scope": "Unit-test surface check only.",
            "limitations": ["Synthetic fixture."],
        },
    )


def _context(root: Path, name: str, loaded: int, skill_chars: int) -> str:
    metrics = {metric: 0 for metric in CONTEXT_METRIC_NAMES}
    metrics["loaded_chars"] = loaded
    metrics["skill_instruction_chars"] = skill_chars
    snapshot = ContextSnapshot.create(
        snapshot_id=f"CTX-{name}",
        captured_at="2026-08-13T06:00:00Z",
        scope="task",
        measurement_source="runtime",
        metrics=metrics,
        unknown_metrics=(),
        handoff_ready=True,
        policy=ContextPolicySnapshot.from_mapping(
            {
                "proactive_checkpoint": True,
                "main_raw_material": "forbidden",
                "thresholds": DEFAULT_CONTEXT_THRESHOLDS,
            }
        ),
    )
    path = root / f"{name}-context.json"
    _write_json(path, snapshot.to_mapping())
    return path.name


def _profile(root: Path) -> str:
    path = root / "profile.json"
    _write_json(
        path,
        {
            "schema_version": "0.1.0",
            "agent_profile_id": "fixture-agent",
            "version": "0.1.0",
            "purpose": "Run a controlled paired Skill evaluation.",
            "model_policy": {"class": "fixture"},
            "permission_ceiling": {
                "filesystem": "read-only",
                "network": "forbidden",
                "external_write": False,
                "allowed_roots": [],
            },
            "allowed_tool_capabilities": ["file-read"],
            "default_context_policy": "fixture",
            "delegation": {"allowed": False},
            "output_contracts": ["fixture-output"],
        },
    )
    return path.name


def _assignment(root: Path, name: str, locks: tuple[SkillLock, ...]) -> str:
    path = root / f"{name}-assignment.json"
    permissions = PermissionPolicy("read-only", "forbidden", False, ())
    assignment_id = _assignment_identifier(
        task_id="SKILL-EVAL-001",
        task_revision=1,
        agent_profile="fixture-agent@0.1.0",
        skill_lock=locks,
        resolved_tools=("file-read",),
        effective_permissions=permissions,
        output_contracts=("fixture-output",),
        registry_digest=None,
    )
    _write_json(
        path,
        {
            "schema_version": "0.1.0",
            "assignment_id": assignment_id,
            "task_id": "SKILL-EVAL-001",
            "task_revision": 1,
            "agent_profile": "fixture-agent@0.1.0",
            "skill_lock": [
                {
                    "skill_id": lock.skill_id,
                    "version": lock.version,
                    "content_hash": lock.content_hash,
                    "source_locator": lock.source_locator,
                    "package_hash": lock.package_hash,
                }
                for lock in locks
            ],
            "resolved_tools": ["file-read"],
            "effective_permissions": {
                "filesystem": "read-only",
                "network": "forbidden",
                "external_write": False,
                "allowed_roots": [],
            },
            "output_contracts": ["fixture-output"],
            "resolution_reason": ["paired evaluation fixture"],
            "registry_digest": None,
        },
    )
    return path.name


def _attempt(
    root: Path,
    name: str,
    output: Path,
    source: Path,
    assignment_ref: str,
    locks: tuple[SkillLock, ...],
) -> str:
    path = root / f"{name}-attempt.json"
    _write_json(
        path,
        {
            "schema_version": "0.1.0",
            "task_id": "SKILL-EVAL-001",
            "task_revision": 1,
            "attempt_id": f"ATTEMPT-{name}",
            "status": "completed",
            "started_at": "2026-08-13T06:00:00Z",
            "finished_at": "2026-08-13T06:00:01Z",
            "trigger_reason": "paired evaluation",
            "input_lock": [_file_ref(source, root)],
            "skill_lock": [lock.identifier for lock in locks],
            "skill_assignment_ref": assignment_ref,
            "execution_receipt_ref": f"{name}-receipt.json",
            "artifact_refs": [output.name],
        },
    )
    return path.name


def _receipt(
    root: Path,
    name: str,
    output: Path,
    validation: Path,
    context_ref: str,
    attempt_ref: str,
    assignment_ref: str,
    profile_ref: str,
    *,
    provider: str = "fixture-provider",
    model: str = "fixture-model",
) -> str:
    path = root / f"{name}-receipt.json"
    _write_json(
        path,
        {
            "schema_version": "0.1.0",
            "receipt_id": f"XR-{name}",
            "execution_kind": "model-api",
            "attempt_ref": attempt_ref,
            "task_id": "SKILL-EVAL-001",
            "task_revision": 1,
            "agent_profile_ref": profile_ref,
            "skill_assignment_ref": assignment_ref,
            "context_snapshot_ref": context_ref,
            "started_at": "2026-08-13T06:00:00Z",
            "finished_at": "2026-08-13T06:00:01Z",
            "status": "completed",
            "runtime": {"name": "fixture-runtime", "version": "1", "adapter_version": "0.1.0"},
            "model_usage_status": "measured",
            "model_usage": [
                {
                    "provider": provider,
                    "model": model,
                    "requests": 1,
                    "input_tokens": 20,
                    "output_tokens": 10,
                }
            ],
            "coordination": {
                "delegated_attempts": 0,
                "handoff_count": 0,
                "review_rounds": 0,
                "max_parallel_observed": 0,
                "coordination_seconds": 0,
                "execution_seconds": 1,
            },
            "trace": {
                "mode": "disabled",
                "external": False,
                "sensitive_data_detected": False,
                "redactions_applied": 0,
            },
            "output_refs": [output.name],
            "validation_refs": [validation.name],
            "limitations": [],
        },
    )
    return path.name


def _live_evaluation(root: Path) -> dict[str, object]:
    skill_dir = root / "skill"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    checker = skill_dir / "checker.py"
    skill.write_text("---\nname: fixture\ndescription: fixture\n---\nPreserve claims.\n", encoding="utf-8")
    checker.write_text("# deterministic fixture checker\n", encoding="utf-8")
    base_skill_dir = root / "base-skill"
    base_skill_dir.mkdir()
    base_skill = base_skill_dir / "SKILL.md"
    base_skill.write_text("---\nname: base\ndescription: fixture\n---\nFollow the task.\n", encoding="utf-8")
    task = root / "task.txt"
    source = root / "source.txt"
    baseline_output = root / "baseline.txt"
    skill_output = root / "with-skill.txt"
    baseline_validation = root / "baseline-validation.json"
    skill_validation = root / "skill-validation.json"
    task.write_text("Rewrite without changing meaning.\n", encoding="utf-8")
    source.write_text("The result may be null.\n", encoding="utf-8")
    baseline_output.write_text("The result is positive.\n", encoding="utf-8")
    skill_output.write_text("The result may be null.\n", encoding="utf-8")
    _check_report(
        root,
        baseline_validation,
        checker,
        source,
        baseline_output,
        status="fail",
    )
    _check_report(root, skill_validation, checker, source, skill_output, status="pass")
    task_chars = len(task.read_text(encoding="utf-8-sig")) + len(source.read_text(encoding="utf-8-sig"))
    skill_chars = len(skill.read_text(encoding="utf-8-sig"))
    baseline_context = _context(root, "baseline", task_chars, 0)
    skill_context = _context(root, "with-skill", task_chars + skill_chars, skill_chars)
    profile_ref = _profile(root)
    base_lock = SkillLock(
        "base",
        "0.1.0",
        hash_file(base_skill),
        base_skill.relative_to(root).as_posix(),
        hash_directory(base_skill_dir),
    )
    candidate_lock = SkillLock(
        "fixture-skill",
        "0.1.0",
        hash_file(skill),
        skill.relative_to(root).as_posix(),
        hash_directory(skill_dir),
    )
    baseline_locks = (base_lock,)
    skill_locks = (base_lock, candidate_lock)
    baseline_assignment = _assignment(root, "baseline", baseline_locks)
    skill_assignment = _assignment(root, "with-skill", skill_locks)
    baseline_attempt = _attempt(
        root, "baseline", baseline_output, source, baseline_assignment, baseline_locks
    )
    skill_attempt = _attempt(
        root, "with-skill", skill_output, source, skill_assignment, skill_locks
    )
    baseline_receipt = _receipt(
        root,
        "baseline",
        baseline_output,
        baseline_validation,
        baseline_context,
        baseline_attempt,
        baseline_assignment,
        profile_ref,
    )
    skill_receipt = _receipt(
        root,
        "with-skill",
        skill_output,
        skill_validation,
        skill_context,
        skill_attempt,
        skill_assignment,
        profile_ref,
    )
    protocol = root / "project-protocol.json"
    _write_json(protocol, load_document(ROOT / "examples/project-protocol.yaml"))
    model_config = root / "model-config.json"
    _write_json(
        model_config,
        {
            "provider": "fixture-provider",
            "model": "fixture-model",
            "temperature": 0,
            "secrets": "excluded",
        },
    )
    config_hash = hash_file(model_config)
    return {
        "schema_version": "0.1.0",
        "evaluation_id": "SE-LIVE-001",
        "candidate_id": "fixture-candidate",
        "skill_id": "fixture-skill",
        "skill_version": "0.1.0",
        "skill_source_ref": _file_ref(skill, root),
        "skill_package_hash": hash_directory(skill_dir),
        "project_protocol_ref": _file_ref(protocol, root),
        "model_config_ref": _file_ref(model_config, root),
        "evaluation_scope": "live-forward-test",
        "generated_at": "2026-08-13T06:00:02Z",
        "protocol": {
            "design": "paired-same-input",
            "same_provider_model_required": True,
            "blinded_review_required": True,
            "decision_owner": "human",
            "minimum_live_cases": 1,
            "required_case_kinds": ["trigger"],
            "required_review_criteria": ["scientific-integrity", "task-success", "clarity"],
        },
        "cases": [
            {
                "case_id": "CASE-001",
                "case_kind": "trigger",
                "task_contract_ref": _file_ref(task, root),
                "input_ref": _file_ref(source, root),
                "arms": {
                    "baseline": {
                        "skill_loaded": False,
                        "output_ref": _file_ref(baseline_output, root),
                        "validation_ref": _file_ref(baseline_validation, root),
                        "deterministic_status": "fail",
                        "execution_receipt_ref": baseline_receipt,
                        "provider": "fixture-provider",
                        "model": "fixture-model",
                        "model_config_hash": config_hash,
                        "context": {
                            "status": "measured",
                            "task_input_characters": task_chars,
                            "skill_instruction_characters": 0,
                            "total_loaded_characters": task_chars,
                        },
                    },
                    "with_skill": {
                        "skill_loaded": True,
                        "output_ref": _file_ref(skill_output, root),
                        "validation_ref": _file_ref(skill_validation, root),
                        "deterministic_status": "pass",
                        "execution_receipt_ref": skill_receipt,
                        "provider": "fixture-provider",
                        "model": "fixture-model",
                        "model_config_hash": config_hash,
                        "context": {
                            "status": "measured",
                            "task_input_characters": task_chars,
                            "skill_instruction_characters": skill_chars,
                            "total_loaded_characters": task_chars + skill_chars,
                        },
                    },
                },
                "review": {
                    "status": "completed",
                    "reviewer_kind": "human",
                    "reviewer_independent": True,
                    "blinded": True,
                    "order_revealed_after_scoring": True,
                    "scored_at": "2026-08-13T06:02:00Z",
                    "revealed_at": "2026-08-13T06:03:00Z",
                    "label_order": ["with-skill", "baseline"],
                    "preference": "with-skill",
                    "criteria": [
                        {
                            "criterion_id": criterion,
                            "baseline_score": 1,
                            "with_skill_score": 4,
                            "scale": "0-worst-to-4-best",
                        }
                        for criterion in ("scientific-integrity", "task-success", "clarity")
                    ],
                    "baseline_substantive_errors": 1,
                    "with_skill_substantive_errors": 0,
                    "baseline_correction_minutes": 2,
                    "with_skill_correction_minutes": 0,
                    "limitations": [],
                },
            }
        ],
        "admission": {
            "status": "eligible-for-human-decision",
            "outcome": "pending",
            "rationale": "Paired evidence is complete; a human still owns admission.",
        },
        "limitations": ["Synthetic unit fixture only."],
    }


class SkillEvaluationTests(unittest.TestCase):
    def test_complete_live_pair_is_only_eligible_for_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            self.assertEqual([], SchemaCatalog().validate("skill_evaluation", document))
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("eligible-for-human-decision", assessment.verdict)
        self.assertEqual((), assessment.risks)

    def test_model_drift_blocks_paired_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            receipt_path = root / document["cases"][0]["arms"]["with_skill"]["execution_receipt_ref"]
            receipt = load_document(receipt_path)
            receipt["model_usage"][0]["model"] = "different-model"
            _write_json(receipt_path, receipt)
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn("EVAL-MODEL-DRIFT", {risk.code for risk in assessment.risks})

    def test_model_configuration_must_match_frozen_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            document["cases"][0]["arms"]["with_skill"]["model_config_hash"] = "b" * 64
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn("EVAL-MODEL-CONFIG-UNPINNED", {risk.code for risk in assessment.risks})

    def test_non_skill_context_drift_blocks_paired_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            arm = document["cases"][0]["arms"]["with_skill"]
            arm["context"]["total_loaded_characters"] += 1
            snapshot_path = root / arm["execution_receipt_ref"].replace("receipt", "context")
            snapshot = load_document(snapshot_path)
            snapshot["metrics"]["loaded_chars"] += 1
            _write_json(snapshot_path, snapshot)
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn("EVAL-BASE-CONTEXT-DRIFT", {risk.code for risk in assessment.risks})

    def test_checker_drift_blocks_paired_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            arm = document["cases"][0]["arms"]["with_skill"]
            report_path = root / arm["validation_ref"]["path"]
            report = load_document(report_path)
            report["checker"]["checker_id"] = "different-checker"
            _write_json(report_path, report)
            arm["validation_ref"] = _file_ref(report_path, root)
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn("EVAL-CHECKER-DRIFT", {risk.code for risk in assessment.risks})

    def test_with_skill_arm_requires_candidate_in_actual_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            document["skill_id"] = "unassigned-candidate"
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn(
            "EVAL-CANDIDATE-ASSIGNMENT-MISSING",
            {risk.code for risk in assessment.risks},
        )

    def test_receipt_must_bind_validation_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            arm = document["cases"][0]["arms"]["with_skill"]
            receipt_path = root / arm["execution_receipt_ref"]
            receipt = load_document(receipt_path)
            receipt["validation_refs"] = []
            _write_json(receipt_path, receipt)
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn(
            "EVAL-RECEIPT-VALIDATION-DRIFT",
            {risk.code for risk in assessment.risks},
        )

    def test_unavailable_tokens_warn_but_do_not_break_provider_neutral_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            for arm_name in ("baseline", "with_skill"):
                relative = document["cases"][0]["arms"][arm_name]["execution_receipt_ref"]
                receipt_path = root / relative
                receipt = load_document(receipt_path)
                receipt["model_usage_status"] = "unavailable"
                receipt["model_usage"] = []
                _write_json(receipt_path, receipt)
            assessment = assess_skill_evaluation(document, root=root)
        self.assertEqual("eligible-for-human-decision", assessment.verdict)
        self.assertEqual(
            {"EVAL-USAGE-NOT-MEASURED"},
            {risk.code for risk in assessment.risks},
        )

    def test_human_decision_must_bind_the_evaluation_candidate_and_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = _live_evaluation(root)
            decision = root / "decision.json"
            _write_json(
                decision,
                {
                    "schema_version": "0.1.0",
                    "object_type": "decision",
                    "object_id": "D-SKILL-001",
                    "revision": 1,
                    "status": "accepted",
                    "decision": "Admit the candidate.",
                    "scope": ["fixture-candidate"],
                    "reason_refs": ["SE-LIVE-001"],
                    "actor": "human-reviewer",
                    "timestamp": "2026-08-13T06:04:00Z",
                    "metadata": {"decision_owner": "human"},
                },
            )
            document["admission"] = {
                "status": "human-decided",
                "outcome": "accept",
                "decision_ref": decision.name,
                "rationale": "A human decided after blind review.",
            }
            assessment = assess_skill_evaluation(document, root=root)
            decision_value = load_document(decision)
            decision_value["metadata"] = {
                "decision_owner": "human",
                "skill_evaluation_id": "SE-LIVE-001",
                "skill_candidate_id": "fixture-candidate",
                "skill_admission_outcome": "accept",
            }
            _write_json(decision, decision_value)
            recorded = assess_skill_evaluation(document, root=root)
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn("EVAL-DECISION-DRIFT", {risk.code for risk in assessment.risks})
        self.assertEqual("human-decision-recorded", recorded.verdict)
        self.assertEqual((), recorded.risks)

    def test_fixture_example_is_valid_but_not_admission_evidence(self) -> None:
        path = ROOT / "examples/evals/claim-preserving-rewrite/fixture-evaluation.yaml"
        document = load_document(path)
        self.assertEqual([], SchemaCatalog().validate("skill_evaluation", document))
        assessment = assess_skill_evaluation(
            document,
            root=ROOT,
            candidate_registry="registry/skills/candidates.json",
        )
        self.assertEqual("not-eligible", assessment.verdict)
        self.assertIn("EVAL-FIXTURE-ONLY", {risk.code for risk in assessment.risks})

    def test_check_report_status_must_match_its_findings(self) -> None:
        report = load_document(
            ROOT / "examples/evals/claim-preserving-rewrite/with-skill-check.json"
        )
        report["checks"][0]["status"] = "fail"
        self.assertTrue(SchemaCatalog().validate("deterministic_check_report", report))

    def test_cli_returns_nonzero_for_incomplete_fixture_evidence(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(
                [
                    "skills",
                    "eval",
                    "assess",
                    str(ROOT / "examples/evals/claim-preserving-rewrite/fixture-evaluation.yaml"),
                    "--root",
                    str(ROOT),
                    "--registry",
                    str(ROOT / "registry/skills/candidates.json"),
                ]
            )
        self.assertEqual(1, code)
        self.assertIn("verdict: not-eligible", output.getvalue())
        self.assertIn("EVAL-CASE-COVERAGE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
