"""M4-002 validation host producer tests.

The host (``run_validation_execution``) is the canonical producer of the
promotion validation triple: it actually invokes the pinned runner/checker in a
scrubbed subprocess and durably persists the report/execution/receipt
provenance metadata.  Authority and boundary faults raise ``ContractError``
before anything is written; runner/checker failures produce a durable
``outcome=fail`` triple that never confers promotion eligibility.  Eligibility
itself is a validity fact established at promotion time by deterministic
re-execution, not by these documents.
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
from research_workbench.artifacts.integrity import hash_file
from research_workbench.artifacts.promotion import check_promotion, execute_promotion
from research_workbench.artifacts.validation_host import run_validation_execution
from research_workbench.cli import main
from research_workbench.contracts.common import ContractError
from research_workbench.tasks.models import FileReference
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_RUNNER = REPO_ROOT / "registry" / "validation-tools" / "deterministic_runner.py"

# Real checker for the rwb-validation-runner-contract/1 ``evaluate`` contract.
# Uses bytes([10]) so no backslash escape ever enters the generated source.
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

RAISING_CHECKER_SOURCE = '''def evaluate(subjects):
    raise RuntimeError("synthetic checker fault")
'''

# Guard checker: fails unless the runner subprocess environment was scrubbed.
# No backslash escapes anywhere so the generated source stays byte-clean.
ENV_GUARD_CHECKER_SOURCE = '''import os

BANNED = ("RWB_TEST_SENTINEL", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP",
          "AWS_SECRET_ACCESS_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")


def evaluate(subjects):
    leaked = [name for name in BANNED if name in os.environ]
    ok = (
        not leaked
        and os.environ.get("PYTHONHASHSEED") == "0"
        and os.environ.get("PYTHONNOUSERSITE") == "1"
        and os.environ.get("TZ") == "UTC"
    )
    return {
        "checks": [{
            "code": "ENV-SCRUBBED",
            "status": "pass" if ok else "fail",
            "detail": "leaked: " + (",".join(leaked) if leaked else "none"),
        }],
        "scope": "Synthetic M4-002 env-scrub guard fixture only.",
        "limitations": ["Does not establish scientific correctness."],
    }
'''

FAULT_RUNNER_SOURCE = '''import sys

sys.exit(2)
'''

INVALID_REPORT_RUNNER_SOURCE = '''import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_bytes().decode("utf-8"))
Path(manifest["report_out"]).write_bytes(b"status: not-a-valid-report")
sys.exit(0)
'''

PASS_REPORT_BAD_EXIT_RUNNER_SOURCE = '''import json
import sys
from pathlib import Path

import yaml

manifest = json.loads(Path(sys.argv[1]).read_bytes().decode("utf-8"))
checker = manifest["checker"]
report = {
    "schema_version": "0.1.0",
    "report_id": manifest["report_id"],
    "checker": {
        "checker_id": checker["checker_id"],
        "version": checker["version"],
        "source_ref": checker["source_ref"],
    },
    "subject_refs": [
        {"path": subject["relative_path"], "sha256": subject["sha256"]}
        for subject in manifest["subjects"]
    ],
    "status": "pass",
    "checks": [{"code": "FIXTURE-BYTES-EXACT", "status": "pass", "detail": "pass claimed"}],
    "scope": "Synthetic M4-002 structural fixture only.",
    "limitations": ["Does not establish scientific correctness."],
}
Path(manifest["report_out"]).write_bytes(
    yaml.safe_dump(report, sort_keys=True, allow_unicode=True).encode("utf-8")
)
sys.exit(3)
'''

SLEEPING_RUNNER_SOURCE = '''import time

time.sleep(60)
'''


class ValidationHostFixture(unittest.TestCase):
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
    def _iso(moment: datetime) -> str:
        return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _file_ref(reference: dict) -> FileReference:
        return FileReference(reference["path"], reference["sha256"], reference.get("revision"))

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

    def repin_task_inputs(self) -> None:
        """Follow the frozen Task input pins to rewritten registry/policy bytes."""
        task = copy.deepcopy(self.task)
        task["input_refs"] = [self.ref(self.registry_path), self.ref(self.policy_path)]
        self.write_task(task)
        self.task = task

    def accept_components(
        self, *, checker_source: str | None = None, runner_source: str | None = None
    ) -> None:
        """Legitimately re-pin the whole authority chain to new component bytes."""
        policy = copy.deepcopy(self.policy)
        registry = copy.deepcopy(self.registry)
        accepted = registry["accepted_policies"][0]
        if checker_source is not None:
            self.checker.write_text(checker_source, encoding="utf-8", newline="\n")
            binding = {
                "checker_id": policy["checker"]["checker_id"],
                "version": policy["checker"]["version"],
                "source_ref": self.ref(self.checker),
            }
            policy["checker"] = copy.deepcopy(binding)
            accepted["checker"] = copy.deepcopy(binding)
        if runner_source is not None:
            self.runner.write_text(runner_source, encoding="utf-8", newline="\n")
            binding = {
                "runner_id": policy["runner"]["runner_id"],
                "version": policy["runner"]["version"],
                "source_ref": self.ref(self.runner),
            }
            policy["runner"] = copy.deepcopy(binding)
            accepted["runner"] = copy.deepcopy(binding)
        self.write_policy(policy)
        self.policy = policy
        accepted["policy_ref"] = self.ref(self.policy_path)
        self.write_registry(registry)
        self.registry = registry
        self.repin_task_inputs()

    def run_host(self, **overrides) -> validation_host.ValidationRunResult:
        kwargs = {
            "attempt_id": "A-001",
            "subjects": (self.rel(self.output), self.rel(self.negative)),
            "operator": "huangyi",
        }
        kwargs.update(overrides)
        return run_validation_execution(self.root, self.task_path, **kwargs)

    def make_record(self) -> dict:
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

    def write_record(self, record: dict) -> Path:
        path = self.workspace / "promotion.yaml"
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8", newline="\n")
        return path


class ValidationHostRunTest(ValidationHostFixture):
    def test_host_run_produces_schema_valid_pass_triple(self) -> None:
        result = self.run_host()
        self.assertEqual(result.outcome, "pass")
        self.assertEqual(result.report_path, "work/M4-002/A-001/checks/validation.yaml")
        self.assertEqual(result.execution_path, "runs/validation/M4-002/A-001/execution.yaml")
        self.assertEqual(result.receipt_path, "runs/validation/M4-002/A-001/receipt.json")
        report = yaml.safe_load((self.root / result.report_path).read_bytes())
        execution = yaml.safe_load((self.root / result.execution_path).read_bytes())
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        catalog = SchemaCatalog()
        self.assertEqual(catalog.validate("deterministic_check_report", report), [])
        self.assertEqual(catalog.validate("promotion_validation_execution", execution), [])
        self.assertEqual(catalog.validate("promotion_validation_host_receipt", receipt), [])
        self.assertEqual(infer_document_kind(report), "deterministic_check_report")
        self.assertEqual(infer_document_kind(execution), "promotion_validation_execution")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(execution["outcome"], "pass")
        self.assertEqual(receipt["outcome"], "pass")
        self.assertEqual(receipt["report_produced_by"], "runner")
        self.assertEqual(receipt["transcript"]["exit_code"], 0)
        self.assertEqual(
            execution["host_receipt_ref"],
            {"path": result.receipt_path, "sha256": hash_file(self.root / result.receipt_path)},
        )
        self.assertEqual(receipt["execution_id"], execution["execution_id"])
        self.assertEqual(
            receipt["transcript"]["report_sha256"], hash_file(self.root / result.report_path)
        )
        recomputed = validation_host._run_inputs_sha256(
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
        self.assertEqual(receipt["run_inputs_sha256"], recomputed)
        # Eligibility holds because promotion-time deterministic re-execution
        # independently confirms the recorded claim -- not because the triple
        # itself is trusted.
        self.assertEqual(check_promotion(self.root, self.make_record()), [])

    def test_runner_subprocess_environment_is_scrubbed(self) -> None:
        # The host must not leak the caller's session/agent environment
        # (credentials, PYTHONPATH poisoning knobs) into the pinned runner
        # subprocess; the guard checker reports fail if any banned variable
        # survives or the pinned determinism knobs are missing.
        self.accept_components(checker_source=ENV_GUARD_CHECKER_SOURCE)
        hostile = {
            "RWB_TEST_SENTINEL": "1",
            "PYTHONPATH": "/tmp/attacker-controlled",
            "AWS_SECRET_ACCESS_KEY": "AKIA-FIXTURE",
            "ANTHROPIC_API_KEY": "sk-fixture",
            "PYTHONHASHSEED": "random",  # hostile caller value must be overridden
        }
        with mock.patch.dict(os.environ, hostile):
            result = self.run_host()
        self.assertEqual(result.outcome, "pass")
        report = yaml.safe_load((self.root / result.report_path).read_bytes())
        self.assertEqual(report["checks"][0]["status"], "pass")
        self.assertEqual(report["checks"][0]["detail"], "leaked: none")

    def test_scrubbed_environment_allowlist_and_determinism_pins(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"RWB_TEST_SENTINEL": "1", "PYTHONPATH": "/tmp/attacker-controlled"},
        ):
            env = validation_host._scrubbed_environment()
        self.assertNotIn("RWB_TEST_SENTINEL", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("PYTHONHOME", env)
        self.assertEqual(env["PYTHONHASHSEED"], "0")
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")
        self.assertEqual(env["TZ"], "UTC")
        self.assertIn("PATH", {key.upper() for key in env})

    def test_runner_fault_without_report_produces_durable_fail_triple(self) -> None:
        self.accept_components(runner_source=FAULT_RUNNER_SOURCE)
        result = self.run_host()
        self.assertEqual(result.outcome, "fail")
        report = yaml.safe_load((self.root / result.report_path).read_bytes())
        execution = yaml.safe_load((self.root / result.execution_path).read_bytes())
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["checks"][0]["code"], "VALIDATION-RUNNER-EXECUTION")
        self.assertIn("no report", report["checks"][0]["detail"])
        self.assertEqual(execution["outcome"], "fail")
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["report_produced_by"], "host-failure-synthesis")
        catalog = SchemaCatalog()
        self.assertEqual(catalog.validate("deterministic_check_report", report), [])
        self.assertEqual(catalog.validate("promotion_validation_execution", execution), [])
        self.assertEqual(catalog.validate("promotion_validation_host_receipt", receipt), [])
        # A durable fail fact never confers promotion eligibility.
        record = self.make_record()
        codes = {risk.code for risk in check_promotion(self.root, record)}
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", codes)
        self.assertIn("VALIDATION-EXECUTION-UNPROVEN", codes)
        with self.assertRaises(ContractError):
            execute_promotion(self.root, self.write_record(record))

    def test_checker_exception_produces_durable_fail_triple(self) -> None:
        self.accept_components(checker_source=RAISING_CHECKER_SOURCE)
        result = self.run_host()
        self.assertEqual(result.outcome, "fail")
        report = yaml.safe_load((self.root / result.report_path).read_bytes())
        self.assertEqual(report["status"], "fail")
        self.assertIn("exit code 2", report["checks"][0]["detail"])
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["report_produced_by"], "host-failure-synthesis")
        self.assertIn(
            "VALIDATION-EXECUTION-UNPROVEN",
            {risk.code for risk in check_promotion(self.root, self.make_record())},
        )

    def test_schema_invalid_runner_report_produces_durable_fail_triple(self) -> None:
        self.accept_components(runner_source=INVALID_REPORT_RUNNER_SOURCE)
        result = self.run_host()
        self.assertEqual(result.outcome, "fail")
        # The runner's bytes are persisted verbatim as the fail-side report.
        self.assertEqual(
            (self.root / result.report_path).read_bytes(), b"status: not-a-valid-report"
        )
        execution = yaml.safe_load((self.root / result.execution_path).read_bytes())
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        self.assertEqual(execution["outcome"], "fail")
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["report_produced_by"], "runner")

    def test_pass_report_with_nonzero_exit_is_a_fail_fact(self) -> None:
        self.accept_components(runner_source=PASS_REPORT_BAD_EXIT_RUNNER_SOURCE)
        result = self.run_host()
        self.assertEqual(result.outcome, "fail")
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["report_produced_by"], "runner")
        self.assertEqual(receipt["transcript"]["exit_code"], 3)
        codes = {risk.code for risk in check_promotion(self.root, self.make_record())}
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", codes)
        self.assertIn("VALIDATION-EXECUTION-UNPROVEN", codes)

    def test_runner_timeout_produces_durable_fail_triple(self) -> None:
        self.accept_components(runner_source=SLEEPING_RUNNER_SOURCE)
        with mock.patch.object(validation_host, "VALIDATION_RUN_TIMEOUT_SECONDS", 1):
            result = self.run_host()
        self.assertEqual(result.outcome, "fail")
        report = yaml.safe_load((self.root / result.report_path).read_bytes())
        self.assertEqual(report["status"], "fail")
        self.assertIn("exceeded", report["checks"][0]["detail"])
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        self.assertEqual(receipt["outcome"], "fail")
        self.assertEqual(receipt["report_produced_by"], "host-failure-synthesis")
        self.assertEqual(receipt["transcript"]["exit_code"], -1)

    def test_authority_and_boundary_faults_raise_before_any_write(self) -> None:
        subjects = (self.rel(self.output), self.rel(self.negative))
        with self.assertRaisesRegex(ContractError, "file-bound"):
            run_validation_execution(
                self.root,
                {"task_id": "M4-002"},  # type: ignore[arg-type]
                attempt_id="A-001",
                subjects=subjects,
                operator="huangyi",
            )
        misplaced = self.root / "objects" / "tasks" / "M4-002" / "TASK.yaml"
        shutil.copyfile(self.task_path, misplaced)
        with self.assertRaisesRegex(ContractError, "canonical path"):
            run_validation_execution(
                self.root, misplaced, attempt_id="A-001", subjects=subjects, operator="huangyi"
            )

        task = copy.deepcopy(self.task)
        task["input_refs"] = [self.ref(self.registry_path)]
        self.write_task(task)
        with self.assertRaisesRegex(ContractError, "accepted policy"):
            self.run_host()
        task = copy.deepcopy(self.task)
        task["input_refs"] = [self.ref(self.policy_path)]
        self.write_task(task)
        with self.assertRaisesRegex(ContractError, "authority registry"):
            self.run_host()
        task = copy.deepcopy(self.task)
        task["write_scope"] = ["work/M4-002/other-attempt"]
        self.write_task(task)
        with self.assertRaisesRegex(ContractError, "write_scope"):
            self.run_host()
        self.write_task(self.task)

        self.registry_path.unlink()
        with self.assertRaisesRegex(ContractError, "missing or escapes"):
            self.run_host()
        self.write_registry(self.registry)

        self.registry_path.write_text("schema_version: 0.1.0\n", encoding="utf-8")
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "schema-invalid"):
            self.run_host()
        self.write_registry(self.registry)
        self.repin_task_inputs()

        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["task_revision"] = 2
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "exactly one"):
            self.run_host()
        registry = copy.deepcopy(self.registry)
        duplicate = copy.deepcopy(registry["accepted_policies"][0])
        duplicate["accepted_by"] = "second-acceptor"
        registry["accepted_policies"].append(duplicate)
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "exactly one"):
            self.run_host()

        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["accepted_at"] = self._iso(
            datetime.now(timezone.utc) + timedelta(hours=1)
        )
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "not accepted before"):
            self.run_host()
        self.write_registry(self.registry)
        self.repin_task_inputs()

        policy = copy.deepcopy(self.policy)
        policy["task_id"] = "M4-999"
        self.write_policy(policy)
        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["policy_ref"] = self.ref(self.policy_path)
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "another Task"):
            self.run_host()
        self.write_policy(self.policy)
        self.write_registry(self.registry)
        self.repin_task_inputs()

        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["checker"]["checker_id"] = "registry-only-checker"
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "policy checker differs"):
            self.run_host()
        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["runner"]["runner_id"] = "registry-only-runner"
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "policy runner differs"):
            self.run_host()
        self.write_registry(self.registry)
        self.repin_task_inputs()

        # An accepted policy that cannot be parsed or validated is refused.
        self.policy_path.write_text("schema_version: 0.1.0\n", encoding="utf-8")
        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["policy_ref"] = self.ref(self.policy_path)
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "schema-invalid"):
            self.run_host()
        self.write_policy(self.policy)
        self.write_registry(self.registry)
        self.repin_task_inputs()

        # Components pinned to missing sources are refused.
        missing_binding = {
            "checker_id": "missing-checker",
            "version": "1.0.0",
            "source_ref": {"path": "checks/promotion/missing-checker.py", "sha256": "0" * 64},
        }
        policy = copy.deepcopy(self.policy)
        policy["checker"] = copy.deepcopy(missing_binding)
        self.write_policy(policy)
        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["checker"] = copy.deepcopy(missing_binding)
        registry["accepted_policies"][0]["policy_ref"] = self.ref(self.policy_path)
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "validation checker"):
            self.run_host()
        self.write_policy(self.policy)
        self.write_registry(self.registry)
        self.repin_task_inputs()

        caller_checker = self.workspace / "checks" / "caller-checker.py"
        caller_checker.write_text(CHECKER_SOURCE, encoding="utf-8", newline="\n")
        binding = {
            "checker_id": "caller-checker",
            "version": "1.0.0",
            "source_ref": self.ref(caller_checker),
        }
        policy = copy.deepcopy(self.policy)
        policy["checker"] = copy.deepcopy(binding)
        self.write_policy(policy)
        registry = copy.deepcopy(self.registry)
        registry["accepted_policies"][0]["checker"] = copy.deepcopy(binding)
        registry["accepted_policies"][0]["policy_ref"] = self.ref(self.policy_path)
        self.write_registry(registry)
        self.repin_task_inputs()
        with self.assertRaisesRegex(ContractError, "repository-governed source zone"):
            self.run_host()
        self.write_policy(self.policy)
        self.write_registry(self.registry)
        self.repin_task_inputs()

        # No fault above may leave any validation fact behind.
        self.assertFalse(self.execution_dir.exists())
        self.assertFalse(self.report_path.exists())

    def test_subject_and_identity_boundary_faults_raise(self) -> None:
        with self.assertRaisesRegex(ContractError, "outside the exact validation workspace"):
            self.run_host(subjects=("checks/promotion/checker.py",))
        with self.assertRaisesRegex(ContractError, "missing or escapes"):
            self.run_host(subjects=("work/M4-002/A-001/outputs/missing.txt",))
        with self.assertRaisesRegex(ContractError, "duplicate validation subject"):
            self.run_host(subjects=(self.rel(self.output), self.rel(self.output)))
        with self.assertRaisesRegex(ContractError, "at least one"):
            self.run_host(subjects=())
        with self.assertRaisesRegex(ContractError, "non-empty string"):
            self.run_host(attempt_id="")
        with self.assertRaisesRegex(ContractError, "single safe path segment"):
            self.run_host(attempt_id="A/001")
        with self.assertRaisesRegex(ContractError, "accountable operator"):
            self.run_host(operator="  ")
        with self.assertRaisesRegex(ContractError, "inside the exact validation workspace"):
            self.run_host(report_path="checks/validation.yaml")
        self.assertFalse(self.execution_dir.exists())
        self.assertFalse(self.report_path.exists())

    def test_task_document_faults_raise_before_any_write(self) -> None:
        subjects = (self.rel(self.output), self.rel(self.negative))
        outside = self.root.parent / f"{self.root.name}-task.yaml"
        try:
            outside.write_text("schema_version: 0.1.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "outside the project root"):
                run_validation_execution(
                    self.root, outside, attempt_id="A-001", subjects=subjects, operator="huangyi"
                )
        finally:
            outside.unlink(missing_ok=True)
        with self.assertRaisesRegex(ContractError, "is missing"):
            run_validation_execution(
                self.root,
                "objects/tasks/M4-002/r1/TASK-missing.yaml",
                attempt_id="A-001",
                subjects=subjects,
                operator="huangyi",
            )
        for content, message in (
            ("[unterminated", "cannot be parsed"),
            ("- not\n- an\n- object\n", "must be an object"),
            ("schema_version: 0.1.0\n", "schema-invalid"),
        ):
            with self.subTest(message=message):
                self.task_path.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(ContractError, message):
                    self.run_host()
                self.write_task(self.task)
        # The bound workspace itself must exist as a real directory.
        shutil.rmtree(self.workspace)
        with self.assertRaisesRegex(ContractError, "workspace is missing or escapes root"):
            self.run_host()
        (self.workspace / "outputs").mkdir(parents=True)
        self.output.write_bytes(b"validated result\n")
        self.negative.write_bytes(b"validated null result\n")
        self.assertFalse(self.execution_dir.exists())

    def test_second_run_for_same_attempt_is_refused(self) -> None:
        result = self.run_host()
        self.assertEqual(result.outcome, "pass")
        original_execution = (self.root / result.execution_path).read_bytes()
        original_receipt = (self.root / result.receipt_path).read_bytes()
        with self.assertRaisesRegex(ContractError, "already exists"):
            self.run_host()
        self.assertEqual((self.root / result.execution_path).read_bytes(), original_execution)
        self.assertEqual((self.root / result.receipt_path).read_bytes(), original_receipt)

    def test_generated_fact_self_checks_are_fail_closed(self) -> None:
        real_catalog = validation_host._schema_catalog()

        class GuardCatalog:
            def __init__(self, failing_kind: str):
                self.failing_kind = failing_kind

            def validate(self, kind, document):
                if kind == self.failing_kind:
                    return [SimpleNamespace(pointer="$", message="simulated self-check fault")]
                return real_catalog.validate(kind, document)

        for failing_kind, message in (
            ("promotion_validation_host_receipt", "host receipt is schema-invalid"),
            ("promotion_validation_execution", "generated execution is schema-invalid"),
        ):
            with self.subTest(failing_kind=failing_kind):
                with mock.patch.object(
                    validation_host, "_schema_catalog", return_value=GuardCatalog(failing_kind)
                ):
                    with self.assertRaisesRegex(ContractError, message):
                        self.run_host()
                self.assertFalse(self.execution_dir.exists())
                self.assertFalse(self.report_path.exists())

    def test_persist_failure_rolls_back_partial_writes(self) -> None:
        real_write = validation_host._write_exclusive
        calls = 0

        def fail_second_write(path, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated disk fault")
            real_write(path, content)

        with mock.patch.object(validation_host, "_write_exclusive", side_effect=fail_second_write):
            with self.assertRaisesRegex(ContractError, "could not persist"):
                self.run_host()
        self.assertFalse(self.report_path.exists())
        self.assertFalse(self.execution_path.exists())
        self.assertFalse(self.receipt_path.exists())

    def test_symlinked_task_packet_is_refused(self) -> None:
        link = self.root / "objects" / "tasks" / "M4-002" / "r1" / "TASK-link.yaml"
        try:
            link.symlink_to(self.task_path)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        with self.assertRaisesRegex(ContractError, "symbolic-link"):
            run_validation_execution(
                self.root,
                link,
                attempt_id="A-001",
                subjects=(self.rel(self.output), self.rel(self.negative)),
                operator="huangyi",
            )

    def test_reexecute_validation_rejects_drifted_subject_and_components(self) -> None:
        result = self.run_host()
        self.assertEqual(result.outcome, "pass")
        report = yaml.safe_load((self.root / result.report_path).read_bytes())
        execution = yaml.safe_load((self.root / result.execution_path).read_bytes())
        receipt = json.loads((self.root / result.receipt_path).read_bytes())
        record = promotion.PromotionRecord.from_mapping(self.make_record())

        self.output.write_bytes(b"drifted after the host run\n")
        risks = validation_host.reexecute_validation(self.root, record, report, execution, receipt)
        self.assertTrue(
            any("subject drifted" in risk.message for risk in risks),
            [risk.message for risk in risks],
        )

        self.output.write_bytes(b"validated result\n")
        self.checker.write_text("def evaluate(subjects): return {}\n", encoding="utf-8")
        risks = validation_host.reexecute_validation(self.root, record, report, execution, receipt)
        self.assertTrue(
            any("checker source drifted" in risk.message for risk in risks),
            [risk.message for risk in risks],
        )


class ValidationHostHelperTest(unittest.TestCase):
    def test_evaluate_report_rejection_matrix(self) -> None:
        checker = (
            "fixture-byte-checker",
            "1.0.0",
            FileReference("checks/promotion/checker.py", "0" * 64),
        )
        subjects = [
            FileReference("work/M4-002/A-001/outputs/negative.txt", "1" * 64),
            FileReference("work/M4-002/A-001/outputs/result.txt", "2" * 64),
        ]
        good = {
            "schema_version": "0.1.0",
            "report_id": "M4-002-VALIDATION-A-001",
            "checker": {
                "checker_id": checker[0],
                "version": checker[1],
                "source_ref": {"path": checker[2].path, "sha256": checker[2].sha256},
            },
            "subject_refs": [{"path": item.path, "sha256": item.sha256} for item in subjects],
            "status": "pass",
            "checks": [{"code": "FIXTURE-BYTES-EXACT", "status": "pass", "detail": "ok"}],
            "scope": "Synthetic M4-002 structural fixture only.",
            "limitations": ["Does not establish scientific correctness."],
        }

        def evaluate(document) -> str | None:
            payload = yaml.safe_dump(document, sort_keys=True, allow_unicode=True).encode("utf-8")
            return validation_host._evaluate_report(
                payload, report_id=good["report_id"], checker=checker, subjects=subjects
            )

        self.assertIsNone(evaluate(good))
        self.assertIn(
            "cannot be parsed",
            validation_host._evaluate_report(
                b"[unterminated", report_id=good["report_id"], checker=checker, subjects=subjects
            ),
        )
        self.assertIn(
            "not an object",
            validation_host._evaluate_report(
                b"- just\n- a\n- list\n",
                report_id=good["report_id"],
                checker=checker,
                subjects=subjects,
            ),
        )
        self.assertIn("schema-invalid", evaluate({"schema_version": "0.1.0"}))
        wrong_id = copy.deepcopy(good)
        wrong_id["report_id"] = "M4-002-VALIDATION-A-999"
        self.assertIn("id differs", evaluate(wrong_id))
        wrong_checker = copy.deepcopy(good)
        wrong_checker["checker"]["checker_id"] = "substituted-checker"
        self.assertIn("checker differs", evaluate(wrong_checker))
        wrong_subjects = copy.deepcopy(good)
        wrong_subjects["subject_refs"] = wrong_subjects["subject_refs"][:1]
        self.assertIn("subjects differ", evaluate(wrong_subjects))
        failed = copy.deepcopy(good)
        failed["status"] = "fail"
        failed["checks"][0]["status"] = "fail"
        self.assertIn("checker reported fail", evaluate(failed))


class ValidationHostCliTest(ValidationHostFixture):
    def test_cli_validation_run_then_promotion_validate_and_execute(self) -> None:
        command = [
            "validation",
            "run",
            "--task",
            self.rel(self.task_path),
            "--attempt",
            "A-001",
            "--subject",
            self.rel(self.output),
            "--subject",
            self.rel(self.negative),
            "--operator",
            "huangyi",
            "--root",
            str(self.root),
        ]
        output = StringIO()
        with redirect_stdout(output):
            result = main(command)
        self.assertEqual(result, 0, output.getvalue())
        self.assertIn("report: work/M4-002/A-001/checks/validation.yaml", output.getvalue())
        self.assertIn("execution: runs/validation/M4-002/A-001/execution.yaml", output.getvalue())
        self.assertIn("receipt: runs/validation/M4-002/A-001/receipt.json", output.getvalue())
        self.assertIn("ok: validation run produced a PASS provenance triple (eligibility is established by promotion-time re-execution)", output.getvalue())

        # A second run for the same attempt is refused by the CLI as well.
        output = StringIO()
        with redirect_stdout(output):
            again = main(command)
        self.assertEqual(again, 1)
        self.assertIn("VALIDATION-EXECUTION-UNPROVEN", output.getvalue())

        record_path = self.write_record(self.make_record())
        output = StringIO()
        with redirect_stdout(output):
            validation = main(
                ["promotion", "validate", self.rel(record_path), "--root", str(self.root)]
            )
        self.assertEqual(validation, 0, output.getvalue())
        output = StringIO()
        with redirect_stdout(output):
            execution = main(["promotion", "execute", str(record_path), "--root", str(self.root)])
        self.assertEqual(execution, 0, output.getvalue())
        self.assertIn("promoted: objects/M4-002/result.txt", output.getvalue())
        self.assertEqual(
            (self.root / "objects" / "M4-002" / "result.txt").read_bytes(), b"validated result\n"
        )


if __name__ == "__main__":
    unittest.main()
