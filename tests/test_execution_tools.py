"""K-API-2 client-tool boundary tests.

Client tools are the only executable surface the child session can reach.
They must stay read-only, read only declared paths or allowed roots, and
record every call for closeout evidence.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research_workbench.adapters.models import ClientTool
from research_workbench.execution import CompileError
from research_workbench.execution.tools import (
    DOCUMENT_READ_NAME,
    SessionToolLog,
    build_client_tools,
)


ROOT = Path(__file__).resolve().parents[1]
PAPER_PATH = "examples/fixtures/paper-001.txt"


def document_read(
    root: Path,
    *,
    readable_paths: tuple[str, ...] = (PAPER_PATH,),
    allowed_roots: tuple[str, ...] = ("work/EVID-001",),
    max_read_chars: int = 20000,
    log: SessionToolLog | None = None,
) -> tuple[ClientTool, SessionToolLog]:
    tool_log = log if log is not None else SessionToolLog()
    tools = build_client_tools(
        (DOCUMENT_READ_NAME,),
        root=root,
        readable_paths=readable_paths,
        allowed_roots=allowed_roots,
        max_read_chars=max_read_chars,
        log=tool_log,
    )
    return tools[0], tool_log


class DocumentReadTests(unittest.TestCase):
    def test_reads_declared_task_input_and_records_success(self) -> None:
        tool, log = document_read(ROOT)

        result = tool.execute({"path": PAPER_PATH})

        self.assertIn("Synthetic evidence fixture", str(result))
        self.assertEqual(1, len(log.records))
        record = log.records[0]
        self.assertEqual("document-read", record.name)
        self.assertTrue(record.ok)
        self.assertIsNone(record.error)
        self.assertEqual(len(str(result)), record.result_chars)

    def test_rejects_undeclared_paths_outside_inputs_and_roots(self) -> None:
        tool, log = document_read(ROOT)

        with self.assertRaises(PermissionError):
            tool.execute({"path": "examples/task-evidence.yaml"})
        with self.assertRaises(PermissionError):
            tool.execute({"path": "../outside.txt"})
        with self.assertRaises(PermissionError):
            tool.execute({"path": "registry/agents/evidence-scout.yaml"})

        self.assertEqual(3, len(log.failures))
        self.assertTrue(all(record.error == "PermissionError" for record in log.failures))

    def test_allowed_root_paths_stay_read_only_and_missing_files_fail(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            notes = root / "work" / "EVID-001" / "notes.txt"
            notes.parent.mkdir(parents=True, exist_ok=True)
            notes.write_text("working note", encoding="utf-8")
            tool, log = document_read(root)

            result = tool.execute({"path": "work/EVID-001/notes.txt"})
            self.assertEqual("working note", result)

            with self.assertRaises(FileNotFoundError):
                tool.execute({"path": "work/EVID-001/absent.txt"})
            self.assertEqual(1, len(log.failures))
            self.assertEqual("FileNotFoundError", log.failures[0].error)

    def test_oversized_documents_are_rejected_not_truncated(self) -> None:
        tool, log = document_read(ROOT, max_read_chars=16)

        with self.assertRaises(ValueError) as caught:
            tool.execute({"path": PAPER_PATH})
        self.assertIn("exceeds", str(caught.exception))
        self.assertEqual(1, len(log.failures))
        self.assertEqual("ValueError", log.failures[0].error)

    def test_unknown_tool_names_are_rejected(self) -> None:
        with self.assertRaises(CompileError) as caught:
            build_client_tools(
                ("web-search",),
                root=ROOT,
                readable_paths=(PAPER_PATH,),
                allowed_roots=("work/EVID-001",),
                max_read_chars=100,
                log=SessionToolLog(),
            )
        self.assertEqual("COMPILE-TOOL-UNAVAILABLE", caught.exception.code)

    def test_built_tools_declare_json_schema_and_read_only_side_effects(self) -> None:
        tool, _ = document_read(ROOT)

        self.assertEqual("read-only", tool.side_effect)
        self.assertEqual("document-read", tool.definition.name)
        schema = tool.definition.input_schema
        self.assertEqual("object", schema["type"])
        self.assertEqual(["path"], schema["required"])
        self.assertEqual(("path",), tuple(schema["properties"]))
        self.assertEqual((), SessionToolLog().records)
        self.assertEqual((), SessionToolLog().failures)


if __name__ == "__main__":
    unittest.main()
