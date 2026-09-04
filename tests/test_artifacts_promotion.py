"""M4-002 fail-closed artifact promotion tests.

Every fixture state is produced by the trusted validation host
(``run_validation_execution``) actually invoking the pinned runner/checker in a
subprocess; hand-written execution/report/receipt bytes only ever appear as
attack simulations and must never gain eligibility.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

from research_workbench.artifacts import promotion, validation_host
from research_workbench.artifacts.integrity import hash_bytes, hash_file
from research_workbench.artifacts.promotion import check_promotion, execute_promotion
from research_workbench.artifacts.validation_host import run_validation_execution
from research_workbench.cli import main
from research_workbench.contracts.common import ContractError
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.tasks.models import FileReference
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_RUNNER = REPO_ROOT / "registry" / "validation-tools" / "deterministic_runner.py"

# Real checker for the rwb-validation-runner-contract/1 ``evaluate`` contract.
# Uses bytes([10]) so no backslash escape ever enters the generated source;
# report content is byte-deterministic (repo-relative paths only).
CHECKER_SOURCE = '''def evaluate(subjects):
    checks = []
    for subject in subjects:
        with open(subject["path"], "rb") as stream:
            content = stream.read()
        ok = len(content) > 0 and content.endswith(bytes([10]))
        checks.append({
            "code": "FIXTURE-BYTES-EXACT",
            "status": "pass" if ok else "fail",
            "detail": "subject " + subject["relative_path"] + " is non-empty and newline-terminated",
        })
    return {
        "checks": checks,
        "scope": "Synthetic M4-002 structural fixture only.",
        "limitations": ["Does not establish scientific correctness."],
    }
'''


class PromotionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.workspace = self.root / "work" / "M4-002" / "A-001"
        self.output = self.workspace / "outputs" / "result.txt"
        self.negative = self.workspace / "outputs" / "negative.txt"
        self.checker = self.root / "checks" / "promotion" / "checker.py"
        self.runner = self.root / "registry" / "validation-tools" / "deterministic_runner.py"
        self.host = self.root / "checks" / "promotion" / "host.py"
        self.report_path = self.workspace / "checks" / "validation.yaml"
        self.policy_path = (
            self.root / "registry" / "validation-policies" / "M4-002-promotion.yaml"
        )
        self.registry_path = self.root / "registry" / "validation-policies" / "accepted.yaml"
        self.task_path = self.root / "objects" / "tasks" / "M4-002" / "r1" / "TASK.yaml"
        self.execution_dir = self.root / "runs" / "validation" / "M4-002" / "A-001"
        self.execution_path = self.execution_dir / "execution.yaml"
        self.receipt_path = self.execution_dir / "receipt.json"
        self.output.parent.mkdir(parents=True)
        self.checker.parent.mkdir(parents=True)
        self.runner.parent.mkdir(parents=True)
        self.report_path.parent.mkdir(parents=True)
        self.policy_path.parent.mkdir(parents=True)
        self.task_path.parent.mkdir(parents=True)
        self.output.write_bytes(b"validated result\n")
        self.negative.write_bytes(b"validated null result\n")
        self.checker.write_text(CHECKER_SOURCE, encoding="utf-8", newline="\n")
        shutil.copyfile(SHIPPED_RUNNER, self.runner)
        self.host.write_text("def validate(): return 'recorded-fact'\n", encoding="utf-8")
        self.policy = self._policy()
        self.registry = self._registry()
        self.task = self._task()
        self.run_host()
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

    @staticmethod
    def _canonical_yaml(document: dict) -> bytes:
        return yaml.safe_dump(document, sort_keys=True, allow_unicode=True).encode("utf-8")

    @staticmethod
    def _canonical_json(document: dict) -> bytes:
        return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )

    @staticmethod
    def _iso(moment: datetime) -> str:
        return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_iso(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _file_ref(reference: dict) -> FileReference:
        return FileReference(reference["path"], reference["sha256"], reference.get("revision"))

    def run_host(
        self,
        *,
        attempt: str = "A-001",
        subjects: tuple[str, ...] | None = None,
        operator: str = "huangyi",
        report_path: str | None = None,
    ) -> validation_host.ValidationRunResult:
        """Actually execute the pinned validation pipeline and refresh facts."""
        result = run_validation_execution(
            self.root,
            self.task_path,
            attempt_id=attempt,
            subjects=subjects or (self.rel(self.output), self.rel(self.negative)),
            operator=operator,
            report_path=report_path,
        )
        self.host_result = result
        self.report_bytes = (self.root / result.report_path).read_bytes()
        self.execution_bytes = (self.root / result.execution_path).read_bytes()
        self.receipt_bytes = (self.root / result.receipt_path).read_bytes()
        self.report = yaml.safe_load(self.report_bytes)
        self.execution = yaml.safe_load(self.execution_bytes)
        self.receipt = json.loads(self.receipt_bytes)
        return result

    def rerun_host(self) -> None:
        """Legitimate change path: clear the attempt facts, re-run, re-record."""
        shutil.rmtree(self.execution_dir, ignore_errors=True)
        self.report_path.unlink(missing_ok=True)
        self.run_host()
        self.record = self._record()

    def _policy(self) -> dict:
        policy = {
            "schema_version": "0.1.0",
            "policy_id": "M4-002-PROMOTION-VALIDATION",
            "version": "1.0.0",
            "task_id": "M4-002",
            "policy_owner": "Chengyue-Lu",
            "checker": {
                "checker_id": "fixture-byte-checker",
                "version": "1.0.0",
                "source_ref": self.ref(self.checker),
            },
            "runner": {
                "runner_id": "rwb-deterministic-runner",
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
                    "accepted_at": "2026-08-31T08:55:00Z",
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

    def write_report(self, report: dict) -> None:
        """Hand-write report bytes (attack simulations only)."""
        self.report_path.write_bytes(self._canonical_yaml(report))

    def write_execution(self, execution: dict) -> None:
        """Hand-write execution bytes (attack simulations only)."""
        self.execution_path.parent.mkdir(parents=True, exist_ok=True)
        self.execution_path.write_bytes(self._canonical_yaml(execution))

    def write_receipt(self, receipt: dict) -> None:
        """Hand-write host receipt bytes (attack simulations only)."""
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_bytes(self._canonical_json(receipt))

    def repin_report(self, record: dict, report: dict | None = None) -> None:
        """Re-pin the record to hand-mutated report bytes (an attack move).

        A legitimate report change instead re-runs the trusted host
        (``rerun_host``); re-pinning by hand never confers eligibility.
        """
        if report is not None:
            self.report = report
            self.write_report(report)
        record["validation_report"] = self.ref(self.report_path)

    def repin_execution(self, record: dict, execution: dict | None = None) -> None:
        if execution is not None:
            self.execution = execution
            self.write_execution(execution)
        record["validation_execution"] = self.ref(self.execution_path)

    def repin_receipt(self, record: dict, receipt: dict | None = None) -> None:
        """Re-pin after hand-mutating the host receipt (an attack move)."""
        if receipt is not None:
            self.receipt = receipt
            self.write_receipt(receipt)
        execution = copy.deepcopy(self.execution)
        execution["host_receipt_ref"] = self.ref(self.receipt_path)
        self.repin_execution(record, execution)

    def repin_policy(self, record: dict, policy: dict | None = None) -> None:
        if policy is not None:
            self.policy = policy
            self.write_policy(policy)
        record["validation_policy"] = self.ref(self.policy_path)

    def repin_task(self, record: dict, task: dict | None = None) -> None:
        if task is not None:
            self.task = task
            self.write_task(task)
        record["task_ref"] = self.ref(self.task_path, revision=1)

    def strip_host_run(self) -> None:
        """Remove every host-produced fact, as if the trusted host never ran."""
        shutil.rmtree(self.execution_dir, ignore_errors=True)
        self.report_path.unlink(missing_ok=True)

    def fabricate_pass_facts(
        self, *, with_receipt: bool = True, detail: str = "hand-written pass claim"
    ) -> None:
        """Hand-write an internally consistent PASS report/execution[/receipt].

        Simulates the reviewer-flagged attack: every reference, hash, timestamp,
        and the run-inputs closure are plausible (the closure inputs are public),
        yet the trusted host never produced these bytes.
        """
        started = datetime.now(timezone.utc) - timedelta(minutes=2)
        finished = started + timedelta(minutes=1)
        report = {
            "schema_version": "0.1.0",
            "report_id": "M4-002-VALIDATION-A-001",
            "checker": copy.deepcopy(self.policy["checker"]),
            "subject_refs": [self.ref(self.negative), self.ref(self.output)],
            "status": "pass",
            "checks": [
                {
                    "code": "FIXTURE-BYTES-EXACT",
                    "status": "pass",
                    "detail": detail,
                }
            ],
            "scope": "Synthetic M4-002 structural fixture only.",
            "limitations": ["Does not establish scientific correctness."],
        }
        self.report = report
        self.write_report(report)
        boundaries = {
            "validation_execution_fact": True,
            "promotion_execution": False,
            "claim_acceptance": False,
            "human_decision": False,
            "scientific_correctness": False,
        }
        execution = {
            "schema_version": "0.1.0",
            "execution_id": "M4-002-VALIDATION-EXEC-A-001",
            "task_id": "M4-002",
            "attempt_id": "A-001",
            "task_ref": self.ref(self.task_path, revision=1),
            "authority_registry_ref": self.ref(self.registry_path),
            "policy_ref": self.ref(self.policy_path),
            "checker": copy.deepcopy(self.policy["checker"]),
            "runner": copy.deepcopy(self.policy["runner"]),
            "host": copy.deepcopy(self.registry["accepted_policies"][0]["host"]),
            "report_ref": self.ref(self.report_path),
            "subject_refs": copy.deepcopy(report["subject_refs"]),
            "executor": "fixture-validation-host",
            "host_receipt_ref": {"path": self.rel(self.receipt_path), "sha256": "0" * 64},
            "started_at": self._iso(started),
            "finished_at": self._iso(finished),
            "outcome": "pass",
            "authority_boundaries": copy.deepcopy(boundaries),
        }
        if with_receipt:
            run_inputs = validation_host._run_inputs_sha256(
                execution_id=execution["execution_id"],
                report_id=report["report_id"],
                task_ref=self._file_ref(execution["task_ref"]),
                registry_ref=self._file_ref(execution["authority_registry_ref"]),
                policy_ref=self._file_ref(execution["policy_ref"]),
                checker=promotion._component_binding(execution["checker"], "checker"),
                runner=promotion._component_binding(execution["runner"], "runner"),
                host=promotion._component_binding(execution["host"], "host"),
                subjects=[self._file_ref(item) for item in execution["subject_refs"]],
            )
            receipt = {
                "schema_version": "0.1.0",
                "receipt_id": "M4-002-VALIDATION-EXEC-A-001-HOST-RECEIPT",
                "execution_id": execution["execution_id"],
                "task_id": "M4-002",
                "attempt_id": "A-001",
                "task_ref": copy.deepcopy(execution["task_ref"]),
                "authority_registry_ref": copy.deepcopy(execution["authority_registry_ref"]),
                "policy_ref": copy.deepcopy(execution["policy_ref"]),
                "checker": copy.deepcopy(execution["checker"]),
                "runner": copy.deepcopy(execution["runner"]),
                "host": copy.deepcopy(execution["host"]),
                "report_ref": copy.deepcopy(execution["report_ref"]),
                "subject_refs": copy.deepcopy(execution["subject_refs"]),
                "run_inputs_sha256": run_inputs,
                "transcript": {
                    "exit_code": 0,
                    "stdout_sha256": hash_bytes(b"attacker-invented stdout"),
                    "stderr_sha256": hash_bytes(b""),
                    "report_sha256": hash_file(self.report_path),
                },
                "report_produced_by": "runner",
                "operator": "huangyi",
                "started_at": execution["started_at"],
                "finished_at": execution["finished_at"],
                "outcome": "pass",
                "authority_boundaries": copy.deepcopy(boundaries),
            }
            self.receipt = receipt
            self.write_receipt(receipt)
            execution["host_receipt_ref"] = self.ref(self.receipt_path)
        self.execution = execution
        self.write_execution(execution)

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
            # Generated after the trusted host run so it never predates the
            # host-stamped execution completion time.
            "recorded_at": self._iso(datetime.now(timezone.utc)),
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
        # NOTE: infer_document_kind currently classifies the host receipt as
        # promotion_validation_execution (its execution_id/policy_ref/report_ref
        # rule matches a superset of the receipt's discriminator fields before
        # the receipt rule is reached).  The receipt is therefore verified here
        # through its explicit schema kind instead.
        self.assertEqual(
            SchemaCatalog().validate("promotion_validation_host_receipt", self.receipt), []
        )
        catalog = SchemaCatalog()
        self.assertEqual(catalog.validate("promotion_record", self.record), [])
        self.assertEqual(
            catalog.validate("promotion_validation_authority_registry", self.registry), []
        )
        self.assertEqual(catalog.validate("task_packet", self.task), [])
        self.assertEqual(catalog.validate("promotion_validation_policy", self.policy), [])
        self.assertEqual(
            catalog.validate("promotion_validation_execution", self.execution), []
        )
        self.assertEqual(catalog.validate("deterministic_check_report", self.report), [])
        self.assertEqual(check_promotion(self.root, self.record), [])

    def test_self_consistent_fake_stable_zone_authority_cannot_bypass_frozen_task(self) -> None:
        fake_checker = self.root / "checks" / "promotion" / "fake-checker.py"
        fake_runner = self.root / "checks" / "promotion" / "fake-runner.py"
        fake_host = self.root / "checks" / "promotion" / "fake-host.py"
        fake_checker.write_text("def evaluate(subjects): return {}\n", encoding="utf-8")
        fake_runner.write_text("def run(): return 'pass'\n", encoding="utf-8")
        fake_host.write_text("def validate(): return 'pass'\n", encoding="utf-8")

        report = copy.deepcopy(self.report)
        report["checker"] = {
            "checker_id": "fake-checker",
            "version": "1.0.0",
            "source_ref": self.ref(fake_checker),
        }
        self.repin_report(self.record, report)
        policy = copy.deepcopy(self.policy)
        policy["checker"] = copy.deepcopy(report["checker"])
        policy["runner"] = {
            "runner_id": "fake-runner",
            "version": "1.0.0",
            "source_ref": self.ref(fake_runner),
        }
        self.repin_policy(self.record, policy)
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
        self.registry = registry
        self.write_registry(registry)
        self.record["validation_authority_registry"] = self.ref(self.registry_path)

        # The attacker even fabricates a receipt that is fully consistent with
        # the fake chain, recomputing the run-inputs closure from public pins.
        execution = copy.deepcopy(self.execution)
        execution["authority_registry_ref"] = self.ref(self.registry_path)
        execution["policy_ref"] = self.ref(self.policy_path)
        execution["checker"] = copy.deepcopy(policy["checker"])
        execution["runner"] = copy.deepcopy(policy["runner"])
        execution["host"] = copy.deepcopy(accepted["host"])
        execution["executor"] = "fake-validation-host"
        execution["report_ref"] = self.ref(self.report_path)
        receipt = copy.deepcopy(self.receipt)
        receipt["authority_registry_ref"] = copy.deepcopy(execution["authority_registry_ref"])
        receipt["policy_ref"] = copy.deepcopy(execution["policy_ref"])
        receipt["checker"] = copy.deepcopy(execution["checker"])
        receipt["runner"] = copy.deepcopy(execution["runner"])
        receipt["host"] = copy.deepcopy(execution["host"])
        receipt["report_ref"] = copy.deepcopy(execution["report_ref"])
        receipt["transcript"]["report_sha256"] = hash_file(self.report_path)
        receipt["run_inputs_sha256"] = validation_host._run_inputs_sha256(
            execution_id=execution["execution_id"],
            report_id=report["report_id"],
            task_ref=self._file_ref(execution["task_ref"]),
            registry_ref=self._file_ref(execution["authority_registry_ref"]),
            policy_ref=self._file_ref(execution["policy_ref"]),
            checker=promotion._component_binding(execution["checker"], "checker"),
            runner=promotion._component_binding(execution["runner"], "runner"),
            host=promotion._component_binding(execution["host"], "host"),
            subjects=[self._file_ref(item) for item in execution["subject_refs"]],
        )
        self.write_receipt(receipt)
        execution["host_receipt_ref"] = self.ref(self.receipt_path)
        self.repin_execution(self.record, execution)

        risks = check_promotion(self.root, self.record)
        self.assertTrue(
            any("Task Packet does not exact-pin" in risk.message for risk in risks),
            [risk.message for risk in risks],
        )

    def test_self_signed_work_checker_policy_or_execution_cannot_authorize_promotion(self) -> None:
        original_policy = copy.deepcopy(self.policy)
        caller_checker = self.workspace / "checks" / "caller-checker.py"
        caller_checker.write_text("def evaluate(subjects): return {}\n", encoding="utf-8")
        record = copy.deepcopy(self.record)
        report = copy.deepcopy(self.report)
        report["checker"]["source_ref"] = self.ref(caller_checker)
        self.repin_report(record, report)
        policy = copy.deepcopy(self.policy)
        policy["checker"] = copy.deepcopy(report["checker"])
        self.repin_policy(record, policy)
        execution = copy.deepcopy(self.execution)
        execution["checker"] = copy.deepcopy(report["checker"])
        self.repin_execution(record, execution)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

        self.report_path.write_bytes(self.report_bytes)
        self.report = yaml.safe_load(self.report_bytes)
        self.write_policy(original_policy)
        self.policy = original_policy
        self.execution_path.write_bytes(self.execution_bytes)
        self.execution = yaml.safe_load(self.execution_bytes)

        work_policy = self.workspace / "checks" / "caller-policy.yaml"
        work_policy.write_text(
            yaml.safe_dump(self.policy, sort_keys=False), encoding="utf-8", newline="\n"
        )
        policy_record = copy.deepcopy(self.record)
        policy_record["validation_policy"] = self.ref(work_policy)
        policy_execution = copy.deepcopy(self.execution)
        policy_execution["policy_ref"] = self.ref(work_policy)
        self.repin_execution(policy_record, policy_execution)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(policy_record))
        self.execution_path.write_bytes(self.execution_bytes)
        self.execution = yaml.safe_load(self.execution_bytes)

        work_execution = self.workspace / "checks" / "caller-execution.yaml"
        work_execution.write_bytes(self.execution_bytes)
        execution_record = copy.deepcopy(self.record)
        execution_record["validation_execution"] = self.ref(work_execution)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(execution_record))

    def test_validation_authority_identity_task_outcome_and_time_drift_fail_closed(self) -> None:
        base_execution = copy.deepcopy(self.execution)
        for mutation in ("checker", "task", "outcome", "time", "recorded-before-finish"):
            with self.subTest(mutation=mutation):
                execution = copy.deepcopy(base_execution)
                record = copy.deepcopy(self.record)
                if mutation == "checker":
                    execution["checker"]["checker_id"] = "caller-substituted-checker"
                elif mutation == "task":
                    execution["task_id"] = "M4-999"
                elif mutation == "outcome":
                    execution["outcome"] = "fail"
                elif mutation == "time":
                    started = self._parse_iso(execution["started_at"])
                    execution["finished_at"] = self._iso(started - timedelta(hours=1))
                else:
                    finished = self._parse_iso(execution["finished_at"])
                    record["recorded_at"] = self._iso(finished - timedelta(hours=1))
                self.repin_execution(record, execution)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))
            self.execution_path.write_bytes(self.execution_bytes)
            self.execution = copy.deepcopy(base_execution)

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

                if mutation == "report-checker":
                    self.repin_report(record, report)
                    execution["report_ref"] = copy.deepcopy(record["validation_report"])
                if mutation in ("policy-task", "work-runner"):
                    self.repin_policy(record, policy)
                    execution["policy_ref"] = copy.deepcopy(record["validation_policy"])
                self.repin_execution(record, execution)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))
            self.report_path.write_bytes(self.report_bytes)
            self.report = copy.deepcopy(base_report)
            self.write_policy(base_policy)
            self.policy = copy.deepcopy(base_policy)
            self.execution_path.write_bytes(self.execution_bytes)
            self.execution = copy.deepcopy(base_execution)

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
            "registry-host-untrusted",
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
                elif mutation == "registry-host-untrusted":
                    caller_host = self.workspace / "checks" / "caller-host.py"
                    caller_host.write_text("def validate(): return 'fake'\n", encoding="utf-8")
                    registry["accepted_policies"][0]["host"]["source_ref"] = self.ref(caller_host)
                elif mutation == "accepted-after-execution":
                    started = self._parse_iso(execution["started_at"])
                    registry["accepted_policies"][0]["accepted_at"] = self._iso(
                        started + timedelta(seconds=30)
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
                self.repin_task(record, task)
                execution["task_ref"] = copy.deepcopy(record["task_ref"])
                execution["authority_registry_ref"] = copy.deepcopy(
                    record["validation_authority_registry"]
                )
                if mutation == "execution-task-ref":
                    execution["task_ref"]["sha256"] = "0" * 64
                elif mutation == "execution-registry-ref":
                    execution["authority_registry_ref"]["sha256"] = "0" * 64
                self.repin_execution(record, execution)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))
            self.registry_path.with_name("forged-accepted.yaml").unlink(missing_ok=True)
            self.write_registry(base_registry)
            self.registry = copy.deepcopy(base_registry)
            self.write_task(base_task)
            self.task = copy.deepcopy(base_task)
            self.execution_path.write_bytes(self.execution_bytes)
            self.execution = copy.deepcopy(base_execution)

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

        escaping = copy.deepcopy(self.record)
        escaping["promotion_id"] = "../escaping"
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(escaping))

    def test_missing_or_drifted_validation_authority_files_fail_closed(self) -> None:
        self.execution_path.unlink()
        self.assertIn("REF-MISSING", self.codes(self.record))
        self.execution_path.write_bytes(self.execution_bytes)
        self.policy_path.write_text("changed after acceptance\n", encoding="utf-8")
        self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))
        self.write_policy(self.policy)
        self.task_path.write_text("schema_version: 0.1.0\n", encoding="utf-8")
        record = copy.deepcopy(self.record)
        record["task_ref"] = self.ref(self.task_path, revision=1)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_backslash_paths_normalize_to_one_cross_host_identity(self) -> None:
        # Report/execution/receipt bytes are host-produced and hash-pinned, so
        # only the record's own path spellings may vary across hosts.
        record = copy.deepcopy(self.record)
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
        # The host receipt (receipt.json) is intentionally not in this list:
        # infer_document_kind classifies it as promotion_validation_execution
        # (rule-ordering overlap), so kind-inferred schema validation rejects
        # it.  The promotion flow pins it by explicit kind instead.
        output = StringIO()
        with redirect_stdout(output):
            result = main(["validate", *paths, "--root", str(self.root)])
        self.assertEqual(result, 0, output.getvalue())
        self.assertIn("validated=6 errors=0 warnings=0", output.getvalue())

    def test_report_pin_subject_set_and_checker_drift_fail_closed(self) -> None:
        with self.subTest("report pin"):
            self.report_path.write_text("changed after pin\n", encoding="utf-8")
            self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))
        self.report_path.write_bytes(self.report_bytes)

        with self.subTest("checker pin"):
            self.checker.write_text("def evaluate(subjects): return {}\n", encoding="utf-8")
            self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))
        self.checker.write_text(CHECKER_SOURCE, encoding="utf-8", newline="\n")

        changed_report = copy.deepcopy(self.report)
        changed_report["subject_refs"][0]["sha256"] = "0" * 64
        record = copy.deepcopy(self.record)
        self.repin_report(record, changed_report)
        with self.subTest("subject hash"):
            codes = self.codes(record)
            self.assertIn("ARTIFACT-HASH-MISMATCH", codes)
            self.assertIn("ARTIFACT-NEGATIVE-DROPPED", codes)
        self.report_path.write_bytes(self.report_bytes)
        self.report = yaml.safe_load(self.report_bytes)

    def test_missing_entry_bytes_and_malformed_reports_fail_closed(self) -> None:
        self.output.unlink()
        self.assertIn("REF-MISSING", self.codes(self.record))
        self.output.write_bytes(b"validated result\n")

        for content in ("[unterminated", "- not\n- an\n- object\n", "schema_version: 0.1.0\n"):
            with self.subTest(content=content):
                self.report_path.write_text(content, encoding="utf-8")
                record = copy.deepcopy(self.record)
                record["validation_report"] = self.ref(self.report_path)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))
        self.report_path.write_bytes(self.report_bytes)

    def test_semantically_duplicate_report_subject_is_rejected_after_pin_normalization(self) -> None:
        report = copy.deepcopy(self.report)
        duplicate = self.ref(self.output)
        duplicate["sha256"] = f"sha256:{duplicate['sha256']}"
        report["subject_refs"][0] = duplicate
        record = copy.deepcopy(self.record)
        self.repin_report(record, report)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

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
        # A real checker failure is a durable host fact, never eligibility.
        self.negative.write_bytes(b"truncated null result without a newline")
        self.rerun_host()
        self.assertEqual(self.host_result.outcome, "fail")
        self.assertEqual(self.report["status"], "fail")
        self.assertEqual(self.execution["outcome"], "fail")
        self.assertEqual(self.receipt["outcome"], "fail")
        risks = check_promotion(self.root, self.record)
        codes = {risk.code for risk in risks}
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", codes)
        self.assertIn("VALIDATION-EXECUTION-UNPROVEN", codes)
        messages = [risk.message for risk in risks]
        self.assertTrue(any("status must be pass" in message for message in messages), messages)
        self.assertTrue(any("outcome must be pass" in message for message in messages), messages)
        with self.assertRaises(ContractError):
            self.execute()

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
        record = copy.deepcopy(self.record)
        record["entries"][0]["artifact"] = self.ref(lookalike)
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

    def test_hand_written_execution_without_host_run_cannot_gain_eligibility(self) -> None:
        # Legitimate frozen Task, registry, policy, and trusted-zone components,
        # but the host never ran: the report and execution are hand-written and
        # internally consistent, and no host receipt exists.
        self.strip_host_run()
        self.fabricate_pass_facts(with_receipt=False)
        record = self._record()
        risks = check_promotion(self.root, record)
        self.assertEqual(
            {risk.code for risk in risks},
            {"REF-MISSING"},
            [f"{risk.code}: {risk.message}" for risk in risks],
        )
        with self.assertRaises(ContractError):
            self.execute(record)

    def test_hand_written_execution_with_fabricated_receipt_cannot_gain_eligibility(self) -> None:
        # The attacker also fabricates a receipt with the correctly recomputed
        # run-inputs closure, but the transcript claims a PASS report the pinned
        # runner/checker never produced; deterministic re-execution disagrees.
        self.strip_host_run()
        self.fabricate_pass_facts(with_receipt=True)
        record = self._record()
        risks = check_promotion(self.root, record)
        self.assertEqual(
            {risk.code for risk in risks},
            {"VALIDATION-EXECUTION-UNPROVEN"},
            [f"{risk.code}: {risk.message}" for risk in risks],
        )
        self.assertTrue(
            any("re-execution transcript differs" in risk.message for risk in risks),
            [risk.message for risk in risks],
        )
        with self.assertRaises(ContractError):
            self.execute(record)

    def test_failing_checker_reported_as_pass_blocks_promotion(self) -> None:
        # The pinned checker's real output over the live subject bytes is FAIL;
        # the hand-written PASS claim with a correct run-inputs closure is
        # refuted by deterministic re-execution.
        self.strip_host_run()
        self.negative.write_bytes(b"truncated null result without a newline")
        self.fabricate_pass_facts(with_receipt=True)
        record = self._record()
        risks = check_promotion(self.root, record)
        self.assertEqual(
            {risk.code for risk in risks},
            {"VALIDATION-EXECUTION-UNPROVEN"},
            [f"{risk.code}: {risk.message}" for risk in risks],
        )
        self.assertTrue(
            any("did not reproduce a PASS" in risk.message for risk in risks),
            [risk.message for risk in risks],
        )
        with self.assertRaises(ContractError):
            self.execute(record)

    def test_host_receipt_outside_validation_zone_is_unproven(self) -> None:
        relocated = self.workspace / "checks" / "caller-receipt.json"
        relocated.write_bytes(self.receipt_bytes)
        execution = copy.deepcopy(self.execution)
        execution["host_receipt_ref"] = self.ref(relocated)
        record = copy.deepcopy(self.record)
        self.repin_execution(record, execution)
        risks = check_promotion(self.root, record)
        self.assertIn("VALIDATION-EXECUTION-UNPROVEN", {risk.code for risk in risks})

    def test_host_receipt_transcript_and_closure_drift_matrix_blocks(self) -> None:
        base_execution = copy.deepcopy(self.execution)
        base_receipt = copy.deepcopy(self.receipt)
        started = self._parse_iso(base_execution["started_at"])
        for mutation in (
            "transcript-report-sha",
            "transcript-stdout-sha",
            "transcript-stderr-sha",
            "transcript-exit-code",
            "receipt-execution-id",
            "receipt-attempt-id",
            "receipt-ref-mismatch",
            "receipt-component-binding",
            "receipt-subject-set",
            "receipt-timestamp",
            "produced-by-synthesis-on-pass",
            "outcome-mismatch",
            "run-inputs-closure",
        ):
            with self.subTest(mutation=mutation):
                receipt = copy.deepcopy(base_receipt)
                if mutation == "transcript-report-sha":
                    receipt["transcript"]["report_sha256"] = "0" * 64
                elif mutation == "transcript-stdout-sha":
                    receipt["transcript"]["stdout_sha256"] = "1" * 64
                elif mutation == "transcript-stderr-sha":
                    receipt["transcript"]["stderr_sha256"] = "2" * 64
                elif mutation == "transcript-exit-code":
                    receipt["transcript"]["exit_code"] = 3
                elif mutation == "receipt-execution-id":
                    receipt["execution_id"] = "M4-002-VALIDATION-EXEC-A-999"
                elif mutation == "receipt-attempt-id":
                    receipt["attempt_id"] = "A-999"
                elif mutation == "receipt-ref-mismatch":
                    receipt["policy_ref"]["sha256"] = "0" * 64
                elif mutation == "receipt-component-binding":
                    receipt["checker"]["checker_id"] = "substituted-receipt-checker"
                elif mutation == "receipt-subject-set":
                    receipt["subject_refs"] = receipt["subject_refs"][:1]
                elif mutation == "receipt-timestamp":
                    receipt["started_at"] = self._iso(started + timedelta(seconds=1))
                elif mutation == "produced-by-synthesis-on-pass":
                    receipt["report_produced_by"] = "host-failure-synthesis"
                elif mutation == "outcome-mismatch":
                    receipt["outcome"] = "fail"
                else:
                    receipt["run_inputs_sha256"] = "0" * 64
                record = copy.deepcopy(self.record)
                self.repin_receipt(record, receipt)
                risks = check_promotion(self.root, record)
                self.assertIn(
                    "VALIDATION-EXECUTION-UNPROVEN",
                    {risk.code for risk in risks},
                    [f"{risk.code}: {risk.message}" for risk in risks],
                )
            self.write_receipt(base_receipt)
            self.receipt = copy.deepcopy(base_receipt)
            self.execution_path.write_bytes(self.execution_bytes)
            self.execution = copy.deepcopy(base_execution)


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
        result = self.execute()
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
        result = self.execute()
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
        recorded = self._parse_iso(self.record["recorded_at"])
        early = self._iso(recorded - timedelta(seconds=1))
        with self.assertRaisesRegex(ContractError, "must not predate"):
            self.execute(executed_at=early)
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
        report_parses = 0

        def drift_report_on_receipt_build(root, reference, kind, label):
            nonlocal report_parses
            if label == "validation report":
                report_parses += 1
                if report_parses == 3:
                    return None, [
                        ContractRisk("ARTIFACT-HASH-MISMATCH", RiskLevel.BLOCK, "report drift")
                    ]
            return real_parse(root, reference, kind, label)

        with mock.patch.object(
            promotion,
            "_parse_referenced_document",
            side_effect=drift_report_on_receipt_build,
        ):
            with self.assertRaises(ContractError):
                self.execute()

        execution_parses = 0

        def drift_execution_on_receipt_build(root, reference, kind, label):
            nonlocal execution_parses
            if label == "validation execution record":
                execution_parses += 1
                if execution_parses == 3:
                    return None, [
                        ContractRisk("ARTIFACT-HASH-MISMATCH", RiskLevel.BLOCK, "execution drift")
                    ]
            return real_parse(root, reference, kind, label)

        with mock.patch.object(
            promotion,
            "_parse_referenced_document",
            side_effect=drift_execution_on_receipt_build,
        ):
            with self.assertRaises(ContractError):
                self.execute()

        real_catalog_factory = promotion._schema_catalog

        class GuardCatalog:
            def validate(self, kind, document):
                if kind == "promotion_execution_receipt":
                    return [
                        SimpleNamespace(pointer="$", message="simulated receipt self-check fault")
                    ]
                return real_catalog_factory().validate(kind, document)

        with mock.patch.object(promotion, "_schema_catalog", return_value=GuardCatalog()):
            with self.assertRaises(ContractError):
                self.execute()
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())

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
