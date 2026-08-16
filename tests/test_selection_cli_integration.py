from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from research_workbench.cli import main


ROOT = Path(__file__).resolve().parents[1]


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


class SelectionCliIntegrationTests(unittest.TestCase):
    def test_modes_cards_lists_exactly_the_two_registered_modes(self) -> None:
        code, output = run_cli(["modes", "cards", "--root", str(ROOT), "--json"])
        self.assertEqual(0, code, output)
        document = json.loads(output)
        self.assertEqual(2, document["registered_modes"])
        self.assertEqual(
            {"evidence-synthesis", "simulation"},
            {item["mode_id"] for item in document["cards"]},
        )
        self.assertEqual(0, document["errors"])

    def test_task_select_distinguishes_ready_and_human_gate_records(self) -> None:
        cases = (
            ("KMS-001-evidence-extraction.yaml", True, "ready"),
            ("KMS-004-ambiguous-published-simulation.yaml", False, "human-gate"),
        )
        for filename, ready, verdict in cases:
            with self.subTest(filename=filename):
                code, output = run_cli(
                    [
                        "task",
                        "select",
                        str(ROOT / "examples/mode-skill-selection" / filename),
                        "--root",
                        str(ROOT),
                        "--json",
                    ]
                )
                self.assertEqual(0, code, output)
                document = json.loads(output)
                self.assertIs(document["ready"], ready)
                self.assertEqual(verdict, document["verdict"])

    def test_ready_selection_can_resolve_but_human_gate_cannot(self) -> None:
        code, output = run_cli(
            [
                "task",
                "resolve",
                str(ROOT / "examples/mode-skill-selection/tasks/KMS-001.yaml"),
                "--profile",
                str(ROOT / "registry/agents/evidence-scout.yaml"),
                "--selection",
                str(ROOT / "examples/mode-skill-selection/KMS-001-evidence-extraction.yaml"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(0, code, output)
        assignment = json.loads(output)
        self.assertEqual(
            ["literature-evidence-extraction"],
            [item["skill_id"] for item in assignment["skill_lock"]],
        )

        code, output = run_cli(
            [
                "task",
                "resolve",
                str(ROOT / "examples/mode-skill-selection/tasks/KMS-004.yaml"),
                "--profile",
                str(ROOT / "registry/agents/evidence-scout.yaml"),
                "--selection",
                str(ROOT / "examples/mode-skill-selection/KMS-004-ambiguous-published-simulation.yaml"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(1, code, output)
        self.assertIn("SELECTION-NOT-EXECUTABLE", output)


if __name__ == "__main__":
    unittest.main()
