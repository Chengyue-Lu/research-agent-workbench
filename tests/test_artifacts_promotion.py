"""M4-002 fail-closed artifact promotion tests."""

from __future__ import annotations

import copy
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

from research_workbench.artifacts import promotion
from research_workbench.artifacts.integrity import hash_file
from research_workbench.artifacts.promotion import check_promotion, execute_promotion
from research_workbench.cli import main
from research_workbench.contracts.common import ContractError
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog


class PromotionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.workspace = self.root / "work" / "M4-002" / "A-001"
        self.output = self.workspace / "outputs" / "result.txt"
        self.negative = self.workspace / "outputs" / "negative.txt"
        self.checker = self.root / "checks" / "promotion" / "checker.py"
        self.runner = self.root / "checks" / "promotion" / "runner.py"
        self.host = self.root / "checks" / "promotion" / "host.py"
        self.report_path = self.workspace / "checks" / "validation.yaml"
        self.policy_path = (
            self.root / "registry" / "validation-policies" / "M4-002-promotion.yaml"
        )
        self.registry_path = self.root / "registry" / "validation-policies" / "accepted.yaml"
        self.task_path = self.root / "objects" / "tasks" / "M4-002" / "r1" / "TASK.yaml"
        self.execution_path = (
            self.root / "runs" / "validation" / "M4-002" / "A-001" / "execution.yaml"
        )
        self.output.parent.mkdir(parents=True)
        self.checker.parent.mkdir(parents=True)
        self.report_path.parent.mkdir(parents=True)
        self.policy_path.parent.mkdir(parents=True)
        self.task_path.parent.mkdir(parents=True)
        self.execution_path.parent.mkdir(parents=True)
        self.output.write_bytes(b"validated result\n")
        self.negative.write_bytes(b"validated null result\n")
        self.checker.write_text("def check(): return True\n", encoding="utf-8")
        self.runner.write_text("def run(): return 'deterministic'\n", encoding="utf-8")
        self.host.write_text("def validate(): return 'recorded-fact'\n", encoding="utf-8")
        self.report = self._report()
        self.policy = self._policy()
        self.registry = self._registry()
        self.task = self._task()
        self.execution = self._execution()
        self.record = self._record()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def ref(self, path: Path, *, revision: int | None = None) -> dict:
        reference = {"path": self.rel(path), "sha256": hash_file(path)}
        if revision is not None:
            reference["revision"] = revision
        return reference

    def _report(self) -> dict:
        report = {
            "schema_version": "0.1.0",
            "report_id": "M4-002-VALIDATION-A-001",
            "checker": {
                "checker_id": "fixture-byte-checker",
                "version": "1.0.0",
                "source_ref": self.ref(self.checker),
            },
            "subject_refs": [self.ref(self.output), self.ref(self.negative)],
            "status": "pass",
            "checks": [
                {
                    "code": "FIXTURE-BYTES-EXACT",
                    "status": "pass",
                    "detail": "Synthetic fixture bytes match their deterministic expectation.",
                }
            ],
            "scope": "Synthetic M4-002 structural fixture only.",
            "limitations": ["Does not establish scientific correctness."],
        }
        self.write_report(report)
        return report

    def write_report(self, report: dict) -> None:
        self.report_path.write_text(
            yaml.safe_dump(report, sort_keys=False), encoding="utf-8", newline="\n"
        )

    def _policy(self) -> dict:
        policy = {
            "schema_version": "0.1.0",
            "policy_id": "M4-002-PROMOTION-VALIDATION",
            "version": "1.0.0",
            "task_id": "M4-002",
            "policy_owner": "Chengyue-Lu",
            "checker": copy.deepcopy(self.report["checker"]),
            "runner": {
                "runner_id": "fixture-deterministic-runner",
                "version": "1.0.0",
                "source_ref": self.ref(self.runner),
            },
            "accepted_for": "artifact-promotion-validation",
            "authority_boundaries": {
                "checker_authority": True,
                "execution_fact": False,
                "claim_acceptance": False,
                "human_decision": False,
                "scientific_correctness": False,
            },
        }
        self.write_policy(policy)
        return policy

    def write_policy(self, policy: dict) -> None:
        self.policy_path.write_text(
            yaml.safe_dump(policy, sort_keys=False), encoding="utf-8", newline="\n"
        )

    def _registry(self) -> dict:
        registry = {
            "schema_version": "0.1.0",
            "registry_id": "RWB-PROMOTION-VALIDATION-AUTHORITY",
            "revision": 1,
            "accepted_policies": [
                {
                    "task_id": "M4-002",
                    "task_revision": 1,
                    "policy_ref": self.ref(self.policy_path),
                    "checker": copy.deepcopy(self.policy["checker"]),
                    "runner": copy.deepcopy(self.policy["runner"]),
                    "host": {
                        "host_id": "fixture-validation-host",
                        "version": "1.0.0",
                        "source_ref": self.ref(self.host),
                    },
                    "accepted_at": "2026-08-31T08:55:00+08:00",
                    "accepted_by": "Chengyue-Lu",
                }
            ],
            "authority_boundaries": {
                "pre_attempt_acceptance": True,
                "validation_execution_fact": False,
                "promotion_execution": False,
                "claim_acceptance": False,
                "human_decision": False,
                "scientific_correctness": False,
            },
        }
        self.write_registry(registry)
        return registry

    def write_registry(self, registry: dict) -> None:
        self.registry_path.write_text(
            yaml.safe_dump(registry, sort_keys=False), encoding="utf-8", newline="\n"
        )

    def _task(self) -> dict:
        task = {
            "schema_version": "0.1.0",
            "task_id": "M4-002",
            "revision": 1,
            "goal": "Promote exact validated artifact bytes.",
            "question_refs": [],
            "active_modes": [],
            "required_capabilities": [],
            "required_skills": [],
            "forbidden_skills": [],
            "agent_profile": "fixture-operator",
            "input_refs": [self.ref(self.registry_path), self.ref(self.policy_path)],
            "write_scope": ["work/M4-002/A-001"],
            "required_outputs": ["promotion_record"],
            "permissions": {},
            "delegation": {"allowed": False, "max_depth": 0, "max_parallel": 0},
            "budget": {"max_turns": 2},
            "atomic_boundary": "One exact promotion attempt.",
            "completion_checks": ["promotion record validates"],
            "safe_pause_conditions": ["authority closure unavailable"],
            "stop_conditions": ["any pin drift"],
            "stale_if": ["authority registry or policy changes"],
        }
        self.write_task(task)
        return task

    def write_task(self, task: dict) -> None:
        self.task_path.write_text(
            yaml.safe_dump(task, sort_keys=False), encoding="utf-8", newline="\n"
        )

    def _execution(self) -> dict:
        execution = {
            "schema_version": "0.1.0",
            "execution_id": "M4-002-VALIDATION-EXEC-A-001",
            "task_id": "M4-002",
            "attempt_id": "A-001",
            "task_ref": self.ref(self.task_path, revision=1),
            "authority_registry_ref": self.ref(self.registry_path),
            "policy_ref": self.ref(self.policy_path),
            "checker": copy.deepcopy(self.report["checker"]),
            "runner": copy.deepcopy(self.policy["runner"]),
            "host": copy.deepcopy(self.registry["accepted_policies"][0]["host"]),
            "report_ref": self.ref(self.report_path),
            "subject_refs": copy.deepcopy(self.report["subject_refs"]),
            "executor": "fixture-validation-host",
            "started_at": "2026-08-31T08:58:00+08:00",
            "finished_at": "2026-08-31T08:59:00+08:00",
            "outcome": "pass",
            "authority_boundaries": {
                "validation_execution_fact": True,
                "promotion_execution": False,
                "claim_acceptance": False,
                "human_decision": False,
                "scientific_correctness": False,
            },
        }
        self.write_execution(execution)
        return execution

    def write_execution(self, execution: dict) -> None:
        self.execution_path.write_text(
            yaml.safe_dump(execution, sort_keys=False), encoding="utf-8", newline="\n"
        )

    def repin_report(self, record: dict, report: dict | None = None) -> None:
        if report is not None:
            self.write_report(report)
            self.report = report
        record["validation_report"] = self.ref(self.report_path)
        self.execution["checker"] = copy.deepcopy(self.report["checker"])
        self.execution["report_ref"] = self.ref(self.report_path)
        self.execution["subject_refs"] = copy.deepcopy(self.report["subject_refs"])
        self.write_execution(self.execution)
        record["validation_execution"] = self.ref(self.execution_path)

    def repin_policy(self, record: dict, policy: dict) -> None:
        self.policy = policy
        self.write_policy(policy)
        record["validation_policy"] = self.ref(self.policy_path)
        self.execution["policy_ref"] = self.ref(self.policy_path)
        self.execution["checker"] = copy.deepcopy(policy["checker"])
        self.execution["runner"] = copy.deepcopy(policy["runner"])
        self.write_execution(self.execution)
        record["validation_execution"] = self.ref(self.execution_path)

    def repin_execution(self, record: dict, execution: dict) -> None:
        self.execution = execution
        self.write_execution(execution)
        record["validation_execution"] = self.ref(self.execution_path)

    def _record(self) -> dict:
        return {
            "schema_version": "0.1.0",
            "promotion_id": "PROMOTION-M4-002-A-001",
            "source_workspace": "work/M4-002/A-001",
            "task_ref": self.ref(self.task_path, revision=1),
            "validation_authority_registry": self.ref(self.registry_path),
            "validation_report": self.ref(self.report_path),
            "validation_policy": self.ref(self.policy_path),
            "validation_execution": self.ref(self.execution_path),
            "operator": "huangyi",
            "recorded_at": "2026-08-31T09:00:00+08:00",
            "entries": [
                {
                    "artifact": self.ref(self.output),
                    "disposition": "promote",
                    "negative_result": False,
                    "target": "objects/M4-002/result.txt",
                },
                {
                    "artifact": self.ref(self.negative),
                    "disposition": "retain-in-work",
                    "negative_result": True,
                    "reason": "Retain validated negative result without publication semantics.",
                },
            ],
            "authority_boundaries": {
                "structural_eligibility_only": True,
                "claim_acceptance": False,
                "human_decision": False,
                "publication": False,
                "source_deletion": False,
            },
        }

    def write_record(self, record: dict, name: str = "promotion.yaml") -> Path:
        path = self.workspace / name
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8", newline="\n")
        return path

    def execute(self, record: dict | None = None, *, executed_at: str | None = None):
        path = self.write_record(record or self.record)
        return execute_promotion(self.root, path, executed_at=executed_at)

    def codes(self, record: dict) -> set[str]:
        return {risk.code for risk in check_promotion(self.root, record)}


class PromotionValidationTest(PromotionFixture):
    def test_valid_record_closes_report_checker_subjects_and_entries(self) -> None:
        self.assertEqual(infer_document_kind(self.record), "promotion_record")
        self.assertEqual(
            infer_document_kind(self.registry), "promotion_validation_authority_registry"
        )
        self.assertEqual(infer_document_kind(self.policy), "promotion_validation_policy")
        self.assertEqual(infer_document_kind(self.execution), "promotion_validation_execution")
        self.assertEqual(SchemaCatalog().validate("promotion_record", self.record), [])
        self.assertEqual(
            SchemaCatalog().validate("promotion_validation_authority_registry", self.registry), []
        )
        self.assertEqual(SchemaCatalog().validate("task_packet", self.task), [])
        self.assertEqual(SchemaCatalog().validate("promotion_validation_policy", self.policy), [])
        self.assertEqual(
            SchemaCatalog().validate("promotion_validation_execution", self.execution), []
        )
        self.assertEqual(check_promotion(self.root, self.record), [])

    def test_self_consistent_fake_stable_zone_authority_cannot_bypass_frozen_task(self) -> None:
        fake_checker = self.root / "checks" / "promotion" / "fake-checker.py"
        fake_runner = self.root / "checks" / "promotion" / "fake-runner.py"
        fake_host = self.root / "checks" / "promotion" / "fake-host.py"
        fake_checker.write_text("def check(): return True\n", encoding="utf-8")
        fake_runner.write_text("def run(): return 'pass'\n", encoding="utf-8")
        fake_host.write_text("def validate(): return 'pass'\n", encoding="utf-8")

        report = copy.deepcopy(self.report)
        report["checker"] = {
            "checker_id": "fake-checker",
            "version": "1.0.0",
            "source_ref": self.ref(fake_checker),
        }
        self.write_report(report)
        policy = copy.deepcopy(self.policy)
        policy["checker"] = copy.deepcopy(report["checker"])
        policy["runner"] = {
            "runner_id": "fake-runner",
            "version": "1.0.0",
            "source_ref": self.ref(fake_runner),
        }
        self.write_policy(policy)
        registry = copy.deepcopy(self.registry)
        accepted = registry["accepted_policies"][0]
        accepted["policy_ref"] = self.ref(self.policy_path)
        accepted["checker"] = copy.deepcopy(policy["checker"])
        accepted["runner"] = copy.deepcopy(policy["runner"])
        accepted["host"] = {
            "host_id": "fake-validation-host",
            "version": "1.0.0",
            "source_ref": self.ref(fake_host),
        }
        self.write_registry(registry)
        execution = copy.deepcopy(self.execution)
        execution["authority_registry_ref"] = self.ref(self.registry_path)
        execution["policy_ref"] = self.ref(self.policy_path)
        execution["checker"] = copy.deepcopy(policy["checker"])
        execution["runner"] = copy.deepcopy(policy["runner"])
        execution["host"] = copy.deepcopy(accepted["host"])
        execution["executor"] = "fake-validation-host"
        execution["report_ref"] = self.ref(self.report_path)
        self.write_execution(execution)

        record = copy.deepcopy(self.record)
        record["validation_authority_registry"] = self.ref(self.registry_path)
        record["validation_policy"] = self.ref(self.policy_path)
        record["validation_report"] = self.ref(self.report_path)
        record["validation_execution"] = self.ref(self.execution_path)
        risks = check_promotion(self.root, record)
        self.assertTrue(
            any("Task Packet does not exact-pin" in risk.message for risk in risks),
            [risk.message for risk in risks],
        )

    def test_self_signed_work_checker_policy_or_execution_cannot_authorize_promotion(self) -> None:
        original_report = copy.deepcopy(self.report)
        original_policy = copy.deepcopy(self.policy)
        original_execution = copy.deepcopy(self.execution)
        caller_checker = self.workspace / "checks" / "caller-checker.py"
        caller_checker.write_text("def check(): return True\n", encoding="utf-8")
        record = copy.deepcopy(self.record)
        report = copy.deepcopy(self.report)
        report["checker"]["source_ref"] = self.ref(caller_checker)
        self.repin_report(record, report)
        policy = copy.deepcopy(self.policy)
        policy["checker"] = copy.deepcopy(report["checker"])
        self.repin_policy(record, policy)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

        self.report = original_report
        self.policy = original_policy
        self.execution = original_execution
        self.write_report(self.report)
        self.write_policy(self.policy)
        self.write_execution(self.execution)

        work_policy = self.workspace / "checks" / "caller-policy.yaml"
        work_policy.write_text(
            yaml.safe_dump(self.policy, sort_keys=False), encoding="utf-8", newline="\n"
        )
        policy_record = copy.deepcopy(self.record)
        policy_record["validation_policy"] = self.ref(work_policy)
        policy_execution = copy.deepcopy(self.execution)
        policy_execution["policy_ref"] = self.ref(work_policy)
        self.write_execution(policy_execution)
        policy_record["validation_execution"] = self.ref(self.execution_path)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(policy_record))

        work_execution = self.workspace / "checks" / "caller-execution.yaml"
        work_execution.write_text(
            yaml.safe_dump(self.execution, sort_keys=False), encoding="utf-8", newline="\n"
        )
        execution_record = copy.deepcopy(self.record)
        execution_record["validation_execution"] = self.ref(work_execution)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(execution_record))

    def test_validation_authority_identity_task_outcome_and_time_drift_fail_closed(self) -> None:
        for mutation in ("checker", "task", "outcome", "time", "recorded-before-finish"):
            with self.subTest(mutation=mutation):
                execution = copy.deepcopy(self.execution)
                record = copy.deepcopy(self.record)
                if mutation == "checker":
                    execution["checker"]["checker_id"] = "caller-substituted-checker"
                elif mutation == "task":
                    execution["task_id"] = "M4-999"
                elif mutation == "outcome":
                    execution["outcome"] = "fail"
                elif mutation == "time":
                    execution["started_at"] = "2026-08-31T09:00:00+08:00"
                    execution["finished_at"] = "2026-08-31T08:59:00+08:00"
                else:
                    record["recorded_at"] = "2026-08-31T08:58:30+08:00"
                self.write_execution(execution)
                record["validation_execution"] = self.ref(self.execution_path)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_validation_authority_cross_document_closure_matrix(self) -> None:
        base_report = copy.deepcopy(self.report)
        base_policy = copy.deepcopy(self.policy)
        base_execution = copy.deepcopy(self.execution)
        for mutation in (
            "policy-task",
            "report-checker",
            "attempt",
            "policy-ref",
            "report-ref",
            "runner",
            "duplicate-subject",
            "subject-set",
            "work-runner",
        ):
            with self.subTest(mutation=mutation):
                report = copy.deepcopy(base_report)
                policy = copy.deepcopy(base_policy)
                execution = copy.deepcopy(base_execution)
                record = copy.deepcopy(self.record)
                if mutation == "policy-task":
                    policy["task_id"] = "M4-999"
                elif mutation == "report-checker":
                    report["checker"]["checker_id"] = "substituted-report-checker"
                    execution["checker"] = copy.deepcopy(report["checker"])
                elif mutation == "attempt":
                    execution["attempt_id"] = "A-999"
                elif mutation == "policy-ref":
                    execution["policy_ref"]["sha256"] = "0" * 64
                elif mutation == "report-ref":
                    execution["report_ref"]["sha256"] = "0" * 64
                elif mutation == "runner":
                    execution["runner"]["runner_id"] = "substituted-runner"
                elif mutation == "duplicate-subject":
                    duplicate = copy.deepcopy(execution["subject_refs"][0])
                    duplicate["sha256"] = f"sha256:{duplicate['sha256']}"
                    execution["subject_refs"][1] = duplicate
                elif mutation == "subject-set":
                    execution["subject_refs"].pop()
                else:
                    work_runner = self.workspace / "checks" / "caller-runner.py"
                    work_runner.write_text("def run(): return 'pass'\n", encoding="utf-8")
                    policy["runner"]["source_ref"] = self.ref(work_runner)
                    execution["runner"] = copy.deepcopy(policy["runner"])

                self.write_report(report)
                record["validation_report"] = self.ref(self.report_path)
                execution["report_ref"] = (
                    execution["report_ref"]
                    if mutation == "report-ref"
                    else self.ref(self.report_path)
                )
                self.write_policy(policy)
                record["validation_policy"] = self.ref(self.policy_path)
                execution["policy_ref"] = (
                    execution["policy_ref"]
                    if mutation == "policy-ref"
                    else self.ref(self.policy_path)
                )
                self.write_execution(execution)
                record["validation_execution"] = self.ref(self.execution_path)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_task_registry_host_and_acceptance_time_drift_fail_closed(self) -> None:
        base_task = copy.deepcopy(self.task)
        base_registry = copy.deepcopy(self.registry)
        base_execution = copy.deepcopy(self.execution)

        for mutation in (
            "registry-path",
            "task-duplicate-input",
            "task-write-scope",
            "registry-entry",
            "execution-task-ref",
            "execution-registry-ref",
            "host",
            "executor",
            "accepted-after-execution",
        ):
            with self.subTest(mutation=mutation):
                task = copy.deepcopy(base_task)
                registry = copy.deepcopy(base_registry)
                execution = copy.deepcopy(base_execution)
                record = copy.deepcopy(self.record)
                registry_path = self.registry_path

                if mutation == "registry-path":
                    registry_path = self.registry_path.with_name("forged-accepted.yaml")
                elif mutation == "task-write-scope":
                    task["write_scope"].append("registry/validation-policies")
                elif mutation == "registry-entry":
                    registry["accepted_policies"][0]["task_revision"] = 2
                elif mutation == "host":
                    execution["host"]["host_id"] = "substituted-host"
                    execution["executor"] = "substituted-host"
                elif mutation == "executor":
                    execution["executor"] = "caller-claimed-host"
                elif mutation == "accepted-after-execution":
                    registry["accepted_policies"][0]["accepted_at"] = (
                        "2026-08-31T08:58:30+08:00"
                    )

                registry_path.write_text(
                    yaml.safe_dump(registry, sort_keys=False), encoding="utf-8", newline="\n"
                )
                record["validation_authority_registry"] = self.ref(registry_path)
                task["input_refs"] = [
                    copy.deepcopy(record["validation_authority_registry"]),
                    copy.deepcopy(record["validation_policy"]),
                ]
                if mutation == "task-duplicate-input":
                    task["input_refs"].append(copy.deepcopy(task["input_refs"][0]))
                self.write_task(task)
                record["task_ref"] = self.ref(self.task_path, revision=1)
                execution["task_ref"] = copy.deepcopy(record["task_ref"])
                execution["authority_registry_ref"] = copy.deepcopy(
                    record["validation_authority_registry"]
                )
                if mutation == "execution-task-ref":
                    execution["task_ref"]["sha256"] = "0" * 64
                elif mutation == "execution-registry-ref":
                    execution["authority_registry_ref"]["sha256"] = "0" * 64
                self.write_execution(execution)
                record["validation_execution"] = self.ref(self.execution_path)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_file_bound_record_and_receipt_identity_are_not_optional(self) -> None:
        root_record = self.root / "promotion.yaml"
        root_record.write_text(
            yaml.safe_dump(self.record, sort_keys=False), encoding="utf-8", newline="\n"
        )
        outside_workspace_ref = promotion.FileReference(
            "promotion.yaml", hash_file(root_record)
        )
        self.assertIn(
            "ARTIFACT-PROMOTION-BYPASS",
            {
                risk.code
                for risk in check_promotion(
                    self.root,
                    self.record,
                    record_reference=outside_workspace_ref,
                )
            },
        )

        collision = copy.deepcopy(self.record)
        collision["entries"][0]["target"] = (
            "runs/promotions/PROMOTION-M4-002-A-001/receipt.json"
        )
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(collision))

    def test_missing_or_drifted_validation_authority_files_fail_closed(self) -> None:
        self.execution_path.unlink()
        self.assertIn("REF-MISSING", self.codes(self.record))
        self.write_execution(self.execution)
        self.policy_path.write_text("changed after acceptance\n", encoding="utf-8")
        self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))

    def test_backslash_paths_normalize_to_one_cross_host_identity(self) -> None:
        report = copy.deepcopy(self.report)
        report["checker"]["source_ref"]["path"] = report["checker"]["source_ref"][
            "path"
        ].replace("/", "\\")
        for subject in report["subject_refs"]:
            subject["path"] = subject["path"].replace("/", "\\")
        record = copy.deepcopy(self.record)
        self.repin_report(record, report)
        record["source_workspace"] = record["source_workspace"].replace("/", "\\")
        for field in (
            "task_ref",
            "validation_authority_registry",
            "validation_report",
            "validation_policy",
            "validation_execution",
        ):
            record[field]["path"] = record[field]["path"].replace("/", "\\")
        for entry in record["entries"]:
            entry["artifact"]["path"] = entry["artifact"]["path"].replace("/", "\\")
            if "target" in entry:
                entry["target"] = entry["target"].replace("/", "\\")
        self.assertEqual(check_promotion(self.root, record), [])

    def test_cli_validate_accepts_exact_record(self) -> None:
        record_path = self.write_record(self.record)
        output = StringIO()
        with redirect_stdout(output):
            result = main(
                [
                    "promotion",
                    "validate",
                    self.rel(record_path),
                    "--root",
                    str(self.root),
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("no blocking deterministic risks", output.getvalue())

    def test_repository_validation_recognizes_promotion_authority_documents(self) -> None:
        record_path = self.write_record(self.record)
        paths = [
            str(self.task_path),
            str(self.registry_path),
            str(self.policy_path),
            str(self.execution_path),
            str(self.report_path),
            str(record_path),
        ]
        output = StringIO()
        with redirect_stdout(output):
            result = main(["validate", *paths, "--root", str(self.root)])
        self.assertEqual(result, 0, output.getvalue())
        self.assertIn("validated=6 errors=0 warnings=0", output.getvalue())

    def test_report_pin_subject_set_and_checker_drift_fail_closed(self) -> None:
        with self.subTest("report pin"):
            self.report_path.write_text("changed after pin\n", encoding="utf-8")
            self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))

        self.write_report(self.report)
        self.repin_report(self.record)
        with self.subTest("checker pin"):
            self.checker.write_text("def check(): return False\n", encoding="utf-8")
            self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))

        self.checker.write_text("def check(): return True\n", encoding="utf-8")
        changed_report = copy.deepcopy(self.report)
        changed_report["checker"]["source_ref"] = self.ref(self.checker)
        changed_report["subject_refs"][0]["sha256"] = "0" * 64
        self.repin_report(self.record, changed_report)
        with self.subTest("subject hash"):
            codes = self.codes(self.record)
            self.assertIn("ARTIFACT-HASH-MISMATCH", codes)
            self.assertIn("ARTIFACT-NEGATIVE-DROPPED", codes)

    def test_missing_entry_bytes_and_malformed_reports_fail_closed(self) -> None:
        self.output.unlink()
        self.assertIn("REF-MISSING", self.codes(self.record))
        self.output.write_bytes(b"validated result\n")

        for content in ("[unterminated", "- not\n- an\n- object\n", "schema_version: 0.1.0\n"):
            with self.subTest(content=content):
                self.report_path.write_text(content, encoding="utf-8")
                self.repin_report(self.record)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(self.record))

    def test_semantically_duplicate_report_subject_is_rejected_after_pin_normalization(self) -> None:
        report = copy.deepcopy(self.report)
        duplicate = self.ref(self.output)
        duplicate["sha256"] = f"sha256:{duplicate['sha256']}"
        report["subject_refs"][1] = duplicate
        self.repin_report(self.record, report)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(self.record))

    def test_extra_or_missing_entry_cannot_bypass_exact_subject_set(self) -> None:
        extra_path = self.workspace / "outputs" / "extra.txt"
        extra_path.write_bytes(b"not validated\n")
        extra = copy.deepcopy(self.record)
        extra["entries"].append(
            {
                "artifact": self.ref(extra_path),
                "disposition": "retain-in-work",
                "negative_result": False,
                "reason": "Extra entry must still be rejected.",
            }
        )
        missing = copy.deepcopy(self.record)
        missing["entries"].pop()
        self.assertIn("ARTIFACT-NEGATIVE-DROPPED", self.codes(extra))
        self.assertIn("ARTIFACT-NEGATIVE-DROPPED", self.codes(missing))

    def test_failed_report_is_not_promotion_eligible(self) -> None:
        failed = copy.deepcopy(self.report)
        failed["status"] = "fail"
        failed["checks"][0]["status"] = "fail"
        failed["checks"][0]["detail"] = "Synthetic check failed."
        self.repin_report(self.record, failed)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(self.record))

    def test_workspace_target_and_existing_target_boundaries_fail_closed(self) -> None:
        for workspace in ("work/M4-002", "work-copy/M4-002/A-001", "work/M4-002/A-001/outputs"):
            with self.subTest(workspace=workspace):
                record = copy.deepcopy(self.record)
                record["source_workspace"] = workspace
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

        for target in (
            "objects",
            "runs",
            "deliverables/candidates",
            "deliverables/accepted/result.txt",
            "objects-old/result.txt",
            "checks/result.txt",
        ):
            with self.subTest(target=target):
                record = copy.deepcopy(self.record)
                record["entries"][0]["target"] = target
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

        existing = self.root / "objects" / "M4-002" / "result.txt"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"must not be overwritten")
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(self.record))

    def test_prefix_lookalike_entry_is_not_inside_workspace(self) -> None:
        lookalike = self.root / "work" / "M4-002" / "A-001-old" / "result.txt"
        lookalike.parent.mkdir(parents=True)
        lookalike.write_bytes(b"lookalike")
        report = copy.deepcopy(self.report)
        report["subject_refs"][0] = self.ref(lookalike)
        record = copy.deepcopy(self.record)
        record["entries"][0]["artifact"] = self.ref(lookalike)
        self.repin_report(record, report)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_duplicate_artifact_and_target_identities_block(self) -> None:
        duplicate_artifact = copy.deepcopy(self.record)
        duplicate_artifact["entries"].append(
            {
                "artifact": self.ref(self.output),
                "disposition": "retain-in-work",
                "negative_result": False,
                "reason": "Duplicate path with a different disposition.",
            }
        )
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(duplicate_artifact))

        duplicate_target = copy.deepcopy(self.record)
        duplicate_target["entries"][1] = {
            "artifact": self.ref(self.negative),
            "disposition": "promote",
            "negative_result": True,
            "target": "objects/M4-002/result.txt",
        }
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(duplicate_target))

    def test_authority_boundaries_are_fixed_and_cannot_claim_acceptance(self) -> None:
        for key in ("claim_acceptance", "human_decision", "publication", "source_deletion"):
            with self.subTest(key=key):
                record = copy.deepcopy(self.record)
                record["authority_boundaries"][key] = True
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_mapping_models_reject_malformed_direct_callers(self) -> None:
        malformed_entries = (
            {},
            {"artifact": {}, "disposition": "promote", "negative_result": "no"},
        )
        for entry in malformed_entries:
            with self.subTest(entry=entry), self.assertRaises(ContractError):
                promotion.PromotionEntry.from_mapping(entry)

        for record in (
            {},
            {"task_ref": {}},
            {"task_ref": {}, "validation_authority_registry": {}},
            {
                "task_ref": {},
                "validation_authority_registry": {},
                "validation_report": {},
            },
            {
                "task_ref": {},
                "validation_authority_registry": {},
                "validation_report": {},
                "validation_policy": {},
            },
            {
                "task_ref": {},
                "validation_authority_registry": {},
                "validation_report": {},
                "validation_policy": {},
                "validation_execution": {},
                "entries": [],
            },
            {
                "task_ref": {},
                "validation_authority_registry": {},
                "validation_report": {},
                "validation_policy": {},
                "validation_execution": {},
                "entries": ["not-an-object"],
            },
        ):
            with self.subTest(record=record), self.assertRaises(ContractError):
                promotion.PromotionRecord.from_mapping(record)
        with self.assertRaises(ContractError):
            promotion._timestamp("2026-08-31T09:00:00", "recorded_at")

    def test_symlink_escape_blocks_source_and_target(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir(exist_ok=True)
        try:
            source_link = self.workspace / "outputs" / "outside-link"
            target_link = self.root / "objects" / "outside-link"
            target_link.parent.mkdir(parents=True, exist_ok=True)
            try:
                source_link.symlink_to(outside, target_is_directory=True)
                target_link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            outside_source = outside / "source.txt"
            outside_source.write_bytes(b"outside")
            source_record = copy.deepcopy(self.record)
            source_record["entries"][0]["artifact"] = {
                "path": self.rel(source_link / "source.txt"),
                "sha256": hash_file(outside_source),
            }
            self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(source_record))

            target_record = copy.deepcopy(self.record)
            target_record["entries"][0]["target"] = "objects/outside-link/result.txt"
            self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(target_record))
        finally:
            try:
                outside.rmdir()
            except OSError:
                pass


class PromotionExecutionTest(PromotionFixture):
    def test_defensive_reference_staging_and_record_loader_guards(self) -> None:
        outside_ref = promotion.FileReference("../outside.txt", "0" * 64)
        self.assertIn(
            "ARTIFACT-PROMOTION-BYPASS",
            {risk.code for risk in promotion._reference_risks(self.root, outside_ref, "outside")},
        )
        fake_ok = SimpleNamespace(
            status=SimpleNamespace(value="ok"),
            resolved_path=self.root / "different.txt",
        )
        with mock.patch.object(promotion, "check_file_reference", return_value=fake_ok):
            self.assertIn(
                "ARTIFACT-PROMOTION-BYPASS",
                {
                    risk.code
                    for risk in promotion._reference_risks(
                        self.root,
                        promotion.FileReference("expected.txt", "0" * 64),
                        "aliased",
                    )
                },
            )
        with self.assertRaises(ContractError):
            promotion._reference_keys(None, "subjects")
        with self.assertRaises(ContractError):
            promotion._component_binding("not-a-mapping", "checker")
        with self.assertRaises(ContractError):
            promotion._component_binding({"checker_id": "x", "version": "1.0.0"}, "checker")
        self.assertEqual(
            promotion._reference_mapping(promotion.FileReference("x", "0" * 64, 2))["revision"],
            2,
        )

        parsed = promotion.PromotionRecord.from_mapping(self.record)
        existing_target = self.root / "objects" / "M4-002" / "result.txt"
        existing_target.parent.mkdir(parents=True)
        existing_target.write_bytes(b"existing")
        with self.assertRaises(ContractError):
            promotion._stage_promotions(self.root, parsed)
        existing_target.unlink()

        real_resolve = promotion.resolve_within_root

        def hide_source(root, path):
            if path == self.rel(self.output):
                return None
            return real_resolve(root, path)

        with mock.patch.object(promotion, "resolve_within_root", side_effect=hide_source):
            with self.assertRaises(ContractError):
                promotion._stage_promotions(self.root, parsed)

        with self.assertRaises(ContractError):
            promotion._stage_bytes(self.root, "../receipt.json", b"receipt")
        existing_receipt = self.root / "runs" / "promotions" / "X" / "receipt.json"
        existing_receipt.parent.mkdir(parents=True)
        existing_receipt.write_bytes(b"existing")
        with self.assertRaises(ContractError):
            promotion._stage_bytes(self.root, "runs/promotions/X/receipt.json", b"receipt")

        with self.assertRaises(ContractError):
            promotion.load_promotion_record(self.root, "work/M4-002/A-001/missing.yaml")
        malformed = self.workspace / "malformed.yaml"
        malformed.write_text("[unterminated", encoding="utf-8")
        with self.assertRaises(ContractError):
            promotion.load_promotion_record(self.root, malformed)
        not_mapping = self.workspace / "list.yaml"
        not_mapping.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
        with self.assertRaises(ContractError):
            promotion.load_promotion_record(self.root, not_mapping)
        outside = self.root.parent / f"{self.root.name}-outside-promotion.yaml"
        try:
            outside.write_text("schema_version: 0.1.0\n", encoding="utf-8")
            with self.assertRaises(ContractError):
                promotion.load_promotion_record(self.root, outside)
        finally:
            outside.unlink(missing_ok=True)

    def test_execution_rejects_in_memory_record_and_record_drift(self) -> None:
        with self.assertRaisesRegex(ContractError, "file-bound"):
            execute_promotion(self.root, self.record)  # type: ignore[arg-type]

        record_path = self.write_record(self.record)
        original_stage = promotion._stage_promotions

        def mutate_record_after_staging(root: Path, record):
            staged = original_stage(root, record)
            record_path.write_text("changed after initial validation\n", encoding="utf-8")
            return staged

        with mock.patch.object(
            promotion,
            "_stage_promotions",
            side_effect=mutate_record_after_staging,
        ):
            with self.assertRaises(ContractError):
                execute_promotion(self.root, record_path)
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertFalse(
            (self.root / "runs" / "promotions" / "PROMOTION-M4-002-A-001" / "receipt.json").exists()
        )

    def test_execute_stages_publishes_without_overwrite_and_preserves_work(self) -> None:
        result = self.execute(executed_at="2026-08-31T09:01:00+08:00")
        self.assertEqual(result.targets, ("objects/M4-002/result.txt",))
        self.assertEqual((self.root / result.targets[0]).read_bytes(), self.output.read_bytes())
        receipt = yaml.safe_load((self.root / result.receipt).read_text(encoding="utf-8"))
        self.assertEqual(infer_document_kind(receipt), "promotion_execution_receipt")
        self.assertEqual(SchemaCatalog().validate("promotion_execution_receipt", receipt), [])
        self.assertEqual(receipt["promotion_record_ref"], self.ref(self.workspace / "promotion.yaml"))
        self.assertEqual(receipt["task_ref"], self.record["task_ref"])
        self.assertEqual(
            receipt["validation_authority_registry_ref"],
            self.record["validation_authority_registry"],
        )
        self.assertEqual(receipt["validation_report_ref"], self.record["validation_report"])
        self.assertEqual(receipt["source_artifact_refs"], [self.ref(self.output), self.ref(self.negative)])
        self.assertEqual(
            receipt["target_artifact_refs"][0]["target_ref"],
            {"path": "objects/M4-002/result.txt", "sha256": self.ref(self.output)["sha256"]},
        )
        self.assertEqual(receipt["operator"], "huangyi")
        self.assertEqual(receipt["outcome"], "succeeded")
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.negative.is_file())
        self.assertFalse((self.root / "deliverables" / "accepted").exists())
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(self.record))

    def test_receipt_repository_validation_rechecks_actual_target_bytes(self) -> None:
        result = self.execute(executed_at="2026-08-31T09:01:00+08:00")
        receipt_path = self.root / result.receipt
        output = StringIO()
        with redirect_stdout(output):
            validation = main(["validate", str(receipt_path), "--root", str(self.root)])
        self.assertEqual(validation, 0, output.getvalue())

        (self.root / result.targets[0]).write_bytes(b"drifted after promotion\n")
        output = StringIO()
        with redirect_stdout(output):
            validation = main(["validate", str(receipt_path), "--root", str(self.root)])
        self.assertEqual(validation, 1)
        self.assertIn("HASH", output.getvalue())

    def test_execution_timestamp_cannot_predate_record(self) -> None:
        with self.assertRaisesRegex(ContractError, "must not predate"):
            self.execute(executed_at="2026-08-31T08:59:30+08:00")
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertFalse(
            (self.root / "runs" / "promotions" / "PROMOTION-M4-002-A-001" / "receipt.json").exists()
        )

    def test_receipt_publication_failure_rolls_back_targets_and_receipt(self) -> None:
        real_link = os.link
        calls = 0

        def fail_receipt_link(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise FileExistsError("simulated receipt publication conflict")
            return real_link(source, target)

        with mock.patch.object(promotion.os, "link", side_effect=fail_receipt_link):
            with self.assertRaises(FileExistsError):
                self.execute()
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertFalse(
            (self.root / "runs" / "promotions" / "PROMOTION-M4-002-A-001" / "receipt.json").exists()
        )

    def test_existing_receipt_is_never_overwritten(self) -> None:
        result = self.execute()
        receipt_path = self.root / result.receipt
        original = receipt_path.read_bytes()
        with self.assertRaises(ContractError):
            self.execute()
        self.assertEqual(receipt_path.read_bytes(), original)

    def test_receipt_build_and_commit_drifts_fail_before_publication(self) -> None:
        real_parse = promotion._parse_referenced_document
        parse_calls = 0

        def drift_report_on_receipt_build(*args, **kwargs):
            nonlocal parse_calls
            parse_calls += 1
            if parse_calls == 7:
                return None, [
                    ContractRisk("ARTIFACT-HASH-MISMATCH", RiskLevel.BLOCK, "report drift")
                ]
            return real_parse(*args, **kwargs)

        with mock.patch.object(
            promotion,
            "_parse_referenced_document",
            side_effect=drift_report_on_receipt_build,
        ):
            with self.assertRaises(ContractError):
                self.execute()

        with self.assertRaisesRegex(ContractError, "must be an ISO-8601 date-time"):
            self.execute(executed_at="not-a-date-time")

        blocker = ContractRisk("ARTIFACT-HASH-MISMATCH", RiskLevel.BLOCK, "commit drift")
        with mock.patch.object(promotion, "check_promotion", side_effect=[[], [], [blocker]]):
            with self.assertRaises(ContractError):
                self.execute()

        real_stage_bytes = promotion._stage_bytes

        def corrupt_receipt_stage(root: Path, target_path: str, content: bytes):
            staged = real_stage_bytes(root, target_path, content)
            staged.temporary.write_bytes(b"corrupt receipt bytes")
            return staged

        with mock.patch.object(promotion, "_stage_bytes", side_effect=corrupt_receipt_stage):
            with self.assertRaises(ContractError):
                self.execute()
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())

    def test_cli_execute_reports_promoted_target(self) -> None:
        record_path = self.write_record(self.record)
        output = StringIO()
        with redirect_stdout(output):
            result = main(["promotion", "execute", str(record_path), "--root", str(self.root)])
        self.assertEqual(result, 0)
        self.assertIn("promoted: objects/M4-002/result.txt", output.getvalue())
        self.assertIn("receipt: runs/promotions/PROMOTION-M4-002-A-001/receipt.json", output.getvalue())

    def test_all_validated_negative_results_may_be_explicitly_retained(self) -> None:
        record = copy.deepcopy(self.record)
        record["entries"][0] = {
            "artifact": self.ref(self.output),
            "disposition": "retain-in-work",
            "negative_result": False,
            "reason": "No formal copy requested.",
        }
        result = self.execute(record)
        self.assertEqual(result.targets, ())
        self.assertTrue((self.root / result.receipt).is_file())
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertTrue(self.output.is_file())

    def test_source_race_and_partial_publish_roll_back(self) -> None:
        original_stage = promotion._stage_promotions

        def mutate_then_stage(root: Path, record):
            self.output.write_bytes(b"mutated between validation and staging\n")
            return original_stage(root, record)

        with mock.patch.object(promotion, "_stage_promotions", side_effect=mutate_then_stage):
            with self.assertRaises(ContractError):
                self.execute()
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())

        self.output.write_bytes(b"validated result\n")
        record = copy.deepcopy(self.record)
        record["entries"][1] = {
            "artifact": self.ref(self.negative),
            "disposition": "promote",
            "negative_result": True,
            "target": "runs/M4-002/negative.txt",
        }
        real_link = os.link
        calls = 0

        def fail_second_link(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise FileExistsError("simulated concurrent target")
            return real_link(source, target)

        with mock.patch.object(promotion.os, "link", side_effect=fail_second_link):
            with self.assertRaises(FileExistsError):
                self.execute(record)
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertFalse((self.root / "runs" / "M4-002" / "negative.txt").exists())
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.negative.is_file())

    def test_initial_or_final_validation_risk_never_publishes(self) -> None:
        invalid = copy.deepcopy(self.record)
        invalid["entries"][0]["target"] = "deliverables/accepted/result.txt"
        with self.assertRaises(ContractError):
            self.execute(invalid)

        blocker = ContractRisk("ARTIFACT-HASH-MISMATCH", RiskLevel.BLOCK, "simulated final drift")
        with mock.patch.object(promotion, "check_promotion", side_effect=[[], [blocker]]):
            with self.assertRaises(ContractError):
                self.execute()
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertEqual(list((self.root / "objects").rglob("*.tmp")), [])

    def test_staged_byte_drift_and_pre_publish_target_race_block(self) -> None:
        original_stage = promotion._stage_promotions

        def corrupt_staging(root: Path, record):
            staged = original_stage(root, record)
            staged[0].temporary.write_bytes(b"tampered staged bytes")
            return staged

        with mock.patch.object(promotion, "_stage_promotions", side_effect=corrupt_staging):
            with self.assertRaises(ContractError):
                self.execute()

        target = self.root / "objects" / "M4-002" / "result.txt"
        calls = 0

        def create_target_on_final_check(root, data, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                target.write_bytes(b"appeared during final validation")
            return []

        with mock.patch.object(promotion, "check_promotion", side_effect=create_target_on_final_check):
            with self.assertRaises(ContractError):
                self.execute()
        self.assertEqual(target.read_bytes(), b"appeared during final validation")

    def test_staging_helper_cleans_earlier_temp_when_later_source_drifts(self) -> None:
        record = copy.deepcopy(self.record)
        record["entries"][1] = {
            "artifact": {
                "path": self.rel(self.negative),
                "sha256": "0" * 64,
            },
            "disposition": "promote",
            "negative_result": True,
            "target": "runs/M4-002/negative.txt",
        }
        parsed = promotion.PromotionRecord.from_mapping(record)
        with self.assertRaises(ContractError):
            promotion._stage_promotions(self.root, parsed)
        self.assertEqual(list(self.root.rglob("*.tmp")), [])
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())

    def test_concurrent_target_is_never_overwritten(self) -> None:
        target = self.root / "objects" / "M4-002" / "result.txt"
        original_publish = promotion._publish_staged

        def create_target_then_publish(staged):
            target.write_bytes(b"concurrent owner")
            original_publish(staged)

        with mock.patch.object(promotion, "_publish_staged", side_effect=create_target_then_publish):
            with self.assertRaises(FileExistsError):
                self.execute()
        self.assertEqual(target.read_bytes(), b"concurrent owner")
        self.assertTrue(self.output.is_file())

    def test_temp_cleanup_error_does_not_misreport_successful_publication(self) -> None:
        with mock.patch.object(promotion.Path, "unlink", side_effect=OSError("simulated cleanup")):
            result = self.execute()
        self.assertEqual(result.targets, ("objects/M4-002/result.txt",))
        self.assertEqual((self.root / result.targets[0]).read_bytes(), b"validated result\n")


if __name__ == "__main__":
    unittest.main()
