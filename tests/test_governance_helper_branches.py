from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock
import contextlib
import io

from tests.test_pr_governance import BASE_TASKS, governance, valid_body


def _codes(report: object) -> set[str]:
    return {item.code for item in report.findings}


class GovernanceHelperBranchTests(unittest.TestCase):
    def test_report_emission_covers_pass_warning_and_error_outcomes(self) -> None:
        reports = (
            governance.GovernanceReport(),
            governance.GovernanceReport(
                findings=[governance.Finding("WARNING", "WARN", "warning")],
                risk_reasons=["bounded reason"],
                requirements=["bounded requirement"],
            ),
            governance.GovernanceReport(
                findings=[governance.Finding("ERROR", "FAIL", "failure")]
            ),
        )
        output = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            for report in reports:
                report.emit()
        self.assertIn("governance: PASS", output.getvalue())
        self.assertIn("PASS WITH 1 WARNING", output.getvalue())
        self.assertIn("bounded requirement", output.getvalue())
        self.assertIn("governance: FAIL", errors.getvalue())

    def test_report_body_and_risk_parsers_cover_invalid_and_upgrade_paths(self) -> None:
        report = governance.GovernanceReport()
        with self.assertRaises(governance.GovernanceError):
            report.add("FATAL", "BAD", "bad")
        body = valid_body(shared_contract="yes", authority_impact="true")
        metadata, sections, shared, authority = governance.validate_body(body, report)
        self.assertTrue(shared)
        self.assertTrue(authority)
        self.assertIn("Verification evidence", sections)
        self.assertEqual("Chengyue-Lu", metadata["Accountable owner"])

        invalid = valid_body().replace("- **PR 类型**: feature", "- **PR 类型**: unknown")
        invalid = invalid.replace("- **风险等级**: R0", "- **风险等级**: R9")
        invalid = invalid.replace("- **责任人**: @Chengyue-Lu", "")
        bad_report = governance.GovernanceReport()
        governance.validate_body(invalid, bad_report)
        self.assertLessEqual({"META-MISSING", "PR-CLASS", "RISK-DECLARATION"}, _codes(bad_report))

        risk, reasons = governance.infer_minimum_risk(
            [r"docs\guide.md"], shared_contract=True, authority_impact=True
        )
        self.assertEqual("R2", risk)
        self.assertTrue(reasons)
        unknown = governance.GovernanceReport()
        self.assertEqual("R1", governance.resolve_effective_risk("unknown", "R1", unknown))
        upgraded = governance.GovernanceReport()
        self.assertEqual("R2", governance.resolve_effective_risk("R0", "R2", upgraded))
        self.assertIn("RISK-AUTO-UPGRADE", _codes(upgraded))

    def test_topology_task_row_and_dependency_parsers_fail_closed(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_topology(
            base_ref="other", head_ref="feature", base_repository="repo",
            head_repository="fork", pr_class="feature", report=report,
        )
        self.assertIn("TOPOLOGY-BASE", _codes(report))
        report = governance.GovernanceReport()
        governance.validate_topology(
            base_ref="main", head_ref="feature", base_repository="repo",
            head_repository="fork", pr_class="feature", report=report,
        )
        self.assertLessEqual({"TOPOLOGY-MAIN-SOURCE", "TOPOLOGY-RELEASE-CLASS"}, _codes(report))
        report = governance.GovernanceReport()
        governance.validate_topology(
            base_ref="develop", head_ref="feature", base_repository="repo",
            head_repository="repo", pr_class="release", report=report,
        )
        self.assertIn("TOPOLOGY-RELEASE-BASE", _codes(report))

        with self.assertRaises(governance.GovernanceError):
            governance.parse_task_rows("| M1-001 | INVALID | x | none | y |")
        with self.assertRaises(governance.GovernanceError):
            governance.parse_task_rows(
                "| M1-001 | READY | x | none | y |\n| M1-001 | READY | x | none | y |"
            )
        self.assertEqual(
            {"M8-002", "M8-003", "M8-004"},
            governance._dependency_ids("M8-002..004"),
        )
        rows = governance.parse_task_rows(
            "| M1-001 | READY | x | M1-999 | y |\n"
            "| M1-002 | READY | x | M1-003 | y |\n"
            "| M1-003 | PARKED | x | none | y |"
        )
        report = governance.GovernanceReport()
        governance._validate_dependencies(rows, rows, report)
        self.assertLessEqual(
            {"TASK-DEPENDENCY-UNKNOWN", "TASK-DEPENDENCY-NOT-DONE"}, _codes(report)
        )

    def test_mode_action_and_generic_published_identity_history_are_closed(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_mode_action_registry_history(
            {"entries": "bad"}, {"entries": ["bad", {"action_id": "A", "version": "1"}, {"action_id": "A", "version": "1"}]}, report
        )
        self.assertLessEqual({"ACTION-REGISTRY-SHAPE", "ACTION-REGISTRY-DUPLICATE"}, _codes(report))
        report = governance.GovernanceReport()
        governance.validate_mode_action_registry_history(
            {"entries": [{"action_id": "A", "version": "1", "path": "old"}]},
            {"entries": [{"action_id": "A", "version": "1", "path": "new"}]},
            report,
        )
        self.assertIn("ACTION-IDENTITY-MUTATED", _codes(report))
        report = governance.GovernanceReport()
        governance.validate_mode_action_registry_history(
            {"entries": [{"action_id": "A", "version": "1"}]}, {"entries": []}, report
        )
        self.assertIn("ACTION-IDENTITY-REMOVED", _codes(report))

        self.assertEqual("A", governance._top_level_scalar('{"action_id": "A"}', "action_id"))
        self.assertIsNone(governance._top_level_scalar("{bad", "action_id"))
        self.assertIsNone(governance._top_level_scalar("other: value", "action_id"))
        self.assertIsNone(governance._top_level_scalar("action_id: ''", "action_id"))
        report = governance.GovernanceReport()
        documents = {
            "registry/modes/actions/a.yaml": "action_id: A\nversion: 1.0.0\n",
            "registry/modes/actions/b.yaml": "action_id: A\nversion: 1.0.0\n",
            "registry/modes/actions/bad.yaml": "version: 1.0.0\n",
        }
        governance._index_published_documents(documents, report)
        self.assertLessEqual({"PUBLISHED-IDENTITY-SHAPE", "PUBLISHED-IDENTITY-DUPLICATE"}, _codes(report))

    def test_task_change_variants_preserve_definition_and_evidence_boundaries(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=BASE_TASKS,
            head_text=BASE_TASKS.replace("IN_PROGRESS", "INVALID", 1),
            pr_class="feature", changed_paths=["src/x.py"], declared_task_ids={"M8-002"},
            effective_risk="R2", verification_evidence="M8-002", report=report,
        )
        self.assertIn("TASK-PARSE", _codes(report))

        added = BASE_TASKS + "| M8-006 | DONE | New | none | acceptance |\n"
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=BASE_TASKS, head_text=added, pr_class="task-definition",
            changed_paths=["src/x.py"], declared_task_ids={"M8-006"}, effective_risk="R1",
            verification_evidence="M8-006", report=report,
        )
        self.assertLessEqual({"TASK-DEFINITION-DOCS", "TASK-DEFINITION-DONE"}, _codes(report))
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=BASE_TASKS, head_text=added, pr_class="feature",
            changed_paths=["docs/TASKS.md"], declared_task_ids=set(), effective_risk="R1",
            verification_evidence="none", report=report,
        )
        self.assertIn("TASK-DEFINITION-CLASS", _codes(report))

    def test_workstream_risk_git_and_main_boundaries_are_observable(self) -> None:
        for risk, code in (("R2", "WORKSTREAM-R2"), ("R1", "WORKSTREAM-R1")):
            report = governance.GovernanceReport()
            governance.validate_workstream(
                raw_workstream="none", owner="Chengyue-Lu", effective_risk=risk,
                head_sha="head", report=report,
            )
            self.assertIn(code, _codes(report))
        for path, code in (("../bad", "WORKSTREAM-PATH"), ("docs/workstreams/unknown/TASK", "WORKSTREAM-OWNER-PATH")):
            report = governance.GovernanceReport()
            governance.validate_workstream(
                raw_workstream=path, owner="Chengyue-Lu", effective_risk="R0",
                head_sha="head", report=report,
            )
            self.assertIn(code, _codes(report))
        report = governance.GovernanceReport()
        with mock.patch.object(governance, "_read_blob", side_effect=governance.GovernanceError("missing")):
            governance.validate_workstream(
                raw_workstream="docs/workstreams/chengyue-lu/TEST", owner="Chengyue-Lu",
                effective_risk="R2", head_sha="head", report=report,
            )
        self.assertIn("WORKSTREAM-EVIDENCE", _codes(report))

        report = governance.GovernanceReport()
        governance.validate_risk_requirements(
            effective_risk="R2", sections={}, raw_task_ids="none", report=report
        )
        self.assertLessEqual(
            {"TASK-ID-RISK", "R2-AUTHORITY-BASIS", "R2-ADVERSARIAL-EVIDENCE"}, _codes(report)
        )

        failed = SimpleNamespace(returncode=1, stderr="failed", stdout="")
        with mock.patch.object(governance.subprocess, "run", return_value=failed):
            with self.assertRaises(governance.GovernanceError):
                governance._git("status")
            self.assertFalse(governance._blob_exists("head", "missing"))
        with mock.patch.object(governance, "_git", return_value="a\n\n"):
            self.assertEqual("a", governance._merge_base("base", "head"))
            self.assertEqual(["a"], governance._changed_paths("base", "head"))
        with mock.patch.object(governance, "_git", return_value="registry/modes/actions/a.yaml\nREADME.md\n"), mock.patch.object(
            governance, "_read_blob", return_value="action_id: A\nversion: 1.0.0\n"
        ):
            self.assertEqual(["registry/modes/actions/a.yaml"], list(governance._published_documents_at("head")))

        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "push"}, clear=True):
            self.assertEqual(0, governance.main())
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "pull_request"}, clear=True):
            self.assertEqual(2, governance.main())
        with tempfile.TemporaryDirectory() as temporary:
            event = Path(temporary) / "event.json"
            event.write_text("not-json", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": str(event)},
                clear=True,
            ):
                self.assertEqual(2, governance.main())

    def test_pull_request_orchestrator_fails_closed_at_each_external_boundary(self) -> None:
        self.assertIn("EVENT-PR", _codes(governance.check_pull_request({})))
        self.assertIn(
            "EVENT-REFS",
            _codes(governance.check_pull_request({"pull_request": {}})),
        )

        event = {
            "pull_request": {
                "body": valid_body(),
                "base": {"ref": "develop", "sha": "a" * 40},
                "head": {"ref": "feature", "sha": "b" * 40},
                "mergeable": False,
            }
        }
        with mock.patch.object(
            governance, "_changed_paths", side_effect=governance.GovernanceError("diff")
        ), mock.patch.object(
            governance, "_read_blob", side_effect=governance.GovernanceError("read")
        ), mock.patch.object(
            governance, "_published_documents_at", side_effect=governance.GovernanceError("published")
        ):
            report = governance.check_pull_request(event)
        self.assertLessEqual(
            {
                "EVENT-REPOSITORY",
                "GIT-DIFF",
                "TASK-READ",
                "PUBLISHED-IDENTITY-READ",
                "MERGE-CONFLICT",
            },
            _codes(report),
        )

        complete = json.loads(json.dumps(event))
        complete["pull_request"]["base"]["repo"] = {"full_name": "owner/repo"}
        complete["pull_request"]["head"]["repo"] = {"full_name": "owner/repo"}
        with mock.patch.object(governance, "_changed_paths", return_value=[]), mock.patch.object(
            governance, "_merge_base", return_value="c" * 40
        ), mock.patch.object(governance, "_read_blob", return_value=BASE_TASKS), mock.patch.object(
            governance, "_published_documents_at", return_value={}
        ):
            report = governance.check_pull_request(complete)
        self.assertIn("BASE-STALE", _codes(report))


if __name__ == "__main__":
    unittest.main()
