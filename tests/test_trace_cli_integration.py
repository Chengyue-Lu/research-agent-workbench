from __future__ import annotations

import contextlib
import copy
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts import hash_file
from research_workbench.cli import main
from research_workbench.context import MainStatePacket, checkpoint_digest
from research_workbench.contracts import ContractError
from research_workbench.io import load_document
from research_workbench.tasks import AttemptRecord


ROOT = Path(__file__).resolve().parents[1]
TRACE_FIXTURE = ROOT / "tests/fixtures/trace/valid/h1-complete"
TRACE_INDEX = TRACE_FIXTURE / "archive/TRACE-001/A-001/INDEX.yaml"
TRACE_ATTEMPT_RELATIVE = Path("archive/TRACE-001/A-001")
CANONICAL_ATTEMPT_RELATIVE = Path("work/TRACE-001/A-001")


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


def write_trace_link_documents(project: Path, directory: Path) -> dict[str, Path]:
    target = project / directory
    target.mkdir(parents=True, exist_ok=True)
    trace_index = project / TRACE_ATTEMPT_RELATIVE / "INDEX.yaml"
    trace_ref = {
        "path": trace_index.relative_to(project).as_posix(),
        "sha256": hash_file(trace_index),
    }
    documents = {
        "attempt.yaml": {
            "task_id": "TRACE-001",
            "task_revision": 1,
            "attempt_id": "A-001",
            "status": "completed",
            "agent_trace_index_ref": trace_ref,
        },
        "execution-receipt.yaml": {
            "task_id": "TRACE-001",
            "task_revision": 1,
            "status": "completed",
            "agent_trace_index_ref": trace_ref,
        },
        "main-state.yaml": {
            "task_id": "TRACE-001",
            "task_revision": 1,
            "agent_trace_index_refs": [trace_ref],
        },
    }
    paths: dict[str, Path] = {}
    for filename, document in documents.items():
        path = target / filename
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        paths[filename] = path
    return paths


def replace_trace_hash(path: Path, digest: str) -> None:
    document = copy.deepcopy(load_document(path))
    if path.name == "main-state.yaml":
        document["agent_trace_index_refs"][0]["sha256"] = digest
    else:
        document["agent_trace_index_ref"]["sha256"] = digest
    path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


class TraceCompatibilityTests(unittest.TestCase):
    def test_trace_cli_accepts_index_or_attempt_directory(self) -> None:
        for target in (TRACE_INDEX, TRACE_INDEX.parent):
            with self.subTest(target=target):
                code, output = run_cli(
                    ["trace", "validate", str(target), "--root", str(TRACE_FIXTURE)]
                )
                self.assertEqual(0, code, output)
                self.assertIn("trace=TRACE-TRACE-001-A-001", output)
                self.assertIn("errors=0 warnings=0 completeness=complete", output)

    def test_trace_cli_auto_discovers_same_or_canonical_attempt_documents(self) -> None:
        for link_directory in (TRACE_ATTEMPT_RELATIVE, CANONICAL_ATTEMPT_RELATIVE):
            with self.subTest(link_directory=link_directory), tempfile.TemporaryDirectory() as directory:
                project = Path(directory) / "project"
                shutil.copytree(TRACE_FIXTURE, project)
                write_trace_link_documents(project, link_directory)

                target = project / TRACE_ATTEMPT_RELATIVE
                code, output = run_cli(
                    ["trace", "validate", str(target), "--root", str(project)]
                )

                self.assertEqual(0, code, output)
                self.assertIn("errors=0 warnings=0", output)

    def test_trace_cli_auto_discovered_documents_enforce_three_way_links(self) -> None:
        for filename in ("attempt.yaml", "execution-receipt.yaml", "main-state.yaml"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                project = Path(directory) / "project"
                shutil.copytree(TRACE_FIXTURE, project)
                paths = write_trace_link_documents(project, CANONICAL_ATTEMPT_RELATIVE)
                replace_trace_hash(paths[filename], "0" * 64)

                code, output = run_cli(
                    [
                        "trace",
                        "validate",
                        str(project / TRACE_ATTEMPT_RELATIVE / "INDEX.yaml"),
                        "--root",
                        str(project),
                    ]
                )

                self.assertEqual(1, code, output)
                self.assertIn("TRACE-LINK-MISMATCH", output)

    def test_trace_cli_rejects_ambiguous_auto_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            shutil.copytree(TRACE_FIXTURE, project)
            write_trace_link_documents(project, CANONICAL_ATTEMPT_RELATIVE)
            same_directory = write_trace_link_documents(project, TRACE_ATTEMPT_RELATIVE)
            (same_directory["execution-receipt.yaml"]).unlink()
            (same_directory["main-state.yaml"]).unlink()

            code, output = run_cli(
                ["trace", "validate", str(project / TRACE_ATTEMPT_RELATIVE), "--root", str(project)]
            )

            self.assertEqual(1, code, output)
            self.assertIn("TRACE-LINK-AMBIGUOUS", output)
            self.assertIn("attempt.yaml", output)

    def test_trace_cli_explicit_document_has_priority_over_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            shutil.copytree(TRACE_FIXTURE, project)
            canonical = write_trace_link_documents(project, CANONICAL_ATTEMPT_RELATIVE)
            same_directory = write_trace_link_documents(project, TRACE_ATTEMPT_RELATIVE)
            (same_directory["execution-receipt.yaml"]).unlink()
            (same_directory["main-state.yaml"]).unlink()
            explicit_directory = Path("manual-links")
            explicit = write_trace_link_documents(project, explicit_directory)

            code, output = run_cli(
                [
                    "trace",
                    "validate",
                    str(project / TRACE_ATTEMPT_RELATIVE),
                    "--root",
                    str(project),
                    "--attempt",
                    str(explicit["attempt.yaml"]),
                ]
            )

            self.assertTrue(canonical["execution-receipt.yaml"].is_file())
            self.assertEqual(0, code, output)
            self.assertNotIn("TRACE-LINK-AMBIGUOUS", output)

    def test_trace_cli_rejects_explicit_link_document_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            project = temporary_root / "project"
            shutil.copytree(TRACE_FIXTURE, project)
            canonical = write_trace_link_documents(project, CANONICAL_ATTEMPT_RELATIVE)
            outside_attempt = temporary_root / "outside-attempt.yaml"
            shutil.copyfile(canonical["attempt.yaml"], outside_attempt)

            code, output = run_cli(
                [
                    "trace",
                    "validate",
                    str(project / TRACE_ATTEMPT_RELATIVE),
                    "--root",
                    str(project),
                    "--attempt",
                    str(outside_attempt),
                ]
            )

            self.assertEqual(1, code, output)
            self.assertIn("TRACE-REF-OUTSIDE-ROOT", output)

    def test_trace_cli_missing_bundle_is_a_validation_failure(self) -> None:
        code, output = run_cli(
            [
                "trace",
                "validate",
                "archive/missing/INDEX.yaml",
                "--root",
                str(TRACE_FIXTURE),
            ]
        )
        self.assertEqual(1, code, output)
        self.assertIn("PARSE-ERROR", output)

    def test_attempt_accepts_optional_hash_bound_trace_reference(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/attempt-evidence.yaml"))
        document["agent_trace_index_ref"] = {
            "path": "tests/fixtures/trace/valid/h1-complete/archive/TRACE-001/A-001/INDEX.yaml",
            "sha256": hash_file(TRACE_INDEX),
        }
        attempt = AttemptRecord.from_mapping(document)
        self.assertIsNotNone(attempt.agent_trace_index_ref)
        self.assertEqual(hash_file(TRACE_INDEX), attempt.agent_trace_index_ref.sha256)

    def test_main_state_rejects_duplicate_trace_reference_paths(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/main-state.yaml"))
        document["agent_trace_index_refs"] = [
            {"path": "archive/trace/INDEX.yaml", "sha256": "1" * 64},
            {"path": "archive/trace/INDEX.yaml", "sha256": "2" * 64},
        ]
        document["checkpoint_digest"] = checkpoint_digest(document)
        with self.assertRaisesRegex(ContractError, "agent_trace_index_refs"):
            MainStatePacket.from_mapping(document)

    def test_checkpoint_freezes_trace_and_resume_rejects_nonfrozen_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            code, output = run_cli(["init", str(project), "--project-id", "trace-demo"])
            self.assertEqual(0, code, output)
            shutil.copytree(TRACE_FIXTURE / "archive", project / "archive")
            trace_index = project / "archive/TRACE-001/A-001/INDEX.yaml"
            state_path = project / "checkpoints/MS-TRACE.yaml"
            code, output = run_cli(
                [
                    "context",
                    "checkpoint",
                    "--id",
                    "MS-TRACE",
                    "--protocol",
                    str(project / "project-protocol.yaml"),
                    "--root",
                    str(project),
                    "--agent-trace-index-ref",
                    str(trace_index),
                    "--next-action",
                    "Review the frozen trace.",
                    "--output",
                    str(state_path),
                ]
            )
            self.assertEqual(0, code, output)
            state = copy.deepcopy(load_document(state_path))
            self.assertEqual(
                "archive/TRACE-001/A-001/INDEX.yaml",
                state["agent_trace_index_refs"][0]["path"],
            )
            self.assertEqual(hash_file(trace_index), state["agent_trace_index_refs"][0]["sha256"])

            trace = copy.deepcopy(load_document(trace_index))
            trace["trace_status"] = "active"
            trace_index.write_text(
                yaml.safe_dump(trace, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            state["agent_trace_index_refs"][0]["sha256"] = hash_file(trace_index)
            state["checkpoint_digest"] = checkpoint_digest(state)
            state_path.write_text(
                yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            code, output = run_cli(
                [
                    "context",
                    "resume-check",
                    str(state_path),
                    "--protocol",
                    str(project / "project-protocol.yaml"),
                    "--root",
                    str(project),
                ]
            )
            self.assertEqual(1, code, output)
            self.assertIn("TRACE-NOT-FROZEN", output)


if __name__ == "__main__":
    unittest.main()
