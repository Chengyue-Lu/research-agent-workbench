from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from research_workbench.cli import main


ROOT = Path(__file__).resolve().parents[1]


def _run(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = main(arguments)
    return code, output.getvalue()


class CliCommandBranchTests(unittest.TestCase):
    def test_schema_inventory_and_document_render_in_process(self) -> None:
        code, output = _run(["schema", "list", "--root", str(ROOT / "schemas")])
        self.assertEqual(0, code)
        self.assertIn("task-packet\tdocument", output)

        code, output = _run(
            ["schema", "show", "task-packet", "--root", str(ROOT / "schemas")]
        )
        self.assertEqual(0, code)
        schema = json.loads(output)
        self.assertEqual("task_packet", schema["x-rwb-document-kind"])

    def test_skill_and_provider_inventory_text_and_json_paths(self) -> None:
        commands = (
            [
                "skills",
                "candidates",
                "--registry",
                str(ROOT / "registry" / "skills" / "candidates.json"),
                "--json",
            ],
            [
                "skills",
                "accepted",
                "--registry",
                str(ROOT / "registry" / "skills" / "accepted.json"),
                "--root",
                str(ROOT),
                "--json",
            ],
            [
                "providers",
                "list",
                "--registry",
                str(ROOT / "registry" / "providers" / "capabilities.json"),
                "--json",
            ],
        )
        for arguments in commands:
            with self.subTest(command=arguments[:2]):
                code, output = _run(arguments)
                self.assertEqual(0, code)
                self.assertTrue(json.loads(output))

    def test_codex_layout_and_prompt_render_use_repository_fixtures(self) -> None:
        code, output = _run(
            ["runtime", "codex", "validate", "--root", str(ROOT)]
        )
        self.assertEqual(0, code)
        self.assertEqual("codex", json.loads(output)["runtime"])

        with tempfile.TemporaryDirectory() as temporary:
            prompt_path = Path(temporary) / "dispatch.txt"
            code, output = _run(
                [
                    "runtime",
                    "codex",
                    "render",
                    str(ROOT / "examples" / "task-evidence.yaml"),
                    "--profile",
                    str(ROOT / "registry" / "agents" / "evidence-scout.yaml"),
                    "--registry",
                    str(ROOT / "registry" / "skills" / "accepted.json"),
                    "--root",
                    str(ROOT),
                    "--historical-replay",
                    "--output",
                    str(prompt_path),
                ]
            )
            self.assertEqual(0, code)
            self.assertIn("written", output)
            self.assertIn("EVID-001", prompt_path.read_text(encoding="utf-8"))

    def test_reference_handoff_and_claim_views_cover_optional_paths(self) -> None:
        handoff = ROOT / "examples" / "handoff-evidence.yaml"
        code, output = _run(
            ["handoff", "validate", str(handoff), "--root", str(ROOT)]
        )
        self.assertEqual(0, code)
        self.assertIn("no blocking", output)

        code, output = _run(
            ["reference", "check", str(handoff), "--root", str(ROOT)]
        )
        self.assertEqual(0, code)
        self.assertIn("no blocking", output)

        code, output = _run(
            [
                "claim",
                "trace",
                str(ROOT / "examples" / "objects" / "claim" / "CLAIM-001.yaml"),
                "--protocol",
                str(ROOT / "examples" / "project-protocol.yaml"),
            ]
        )
        self.assertEqual(0, code)
        self.assertIn('"claim_id"', output)
        self.assertIn("no blocking", output)


if __name__ == "__main__":
    unittest.main()
