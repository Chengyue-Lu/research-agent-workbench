import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERNAL_MILESTONE = re.compile(r"\b(?:K-[A-Z0-9-]+|M\d+-\d+)\b")

FIRST_CONTACT_SURFACES = (
    ROOT / "README.md",
    ROOT / "docs" / "PROJECT_CHARTER.md",
    ROOT / "docs" / "ARCHITECTURE.md",
    ROOT / "docs" / "GETTING_STARTED.md",
)


class DocumentationTests(unittest.TestCase):
    def test_public_projection_documentation_and_build_closure(self) -> None:
        from tests.public_surface_helpers import build_input_errors, documentation_errors, selected_files

        files = selected_files(ROOT)
        self.assertEqual([], documentation_errors(files))
        self.assertEqual([], build_input_errors(files))

    def test_first_contact_surfaces_do_not_own_internal_milestones(self) -> None:
        leaked: list[str] = []
        for document in FIRST_CONTACT_SURFACES:
            if INTERNAL_MILESTONE.search(document.read_text(encoding="utf-8")):
                leaked.append(str(document.relative_to(ROOT)))
        self.assertEqual([], leaked)

    def test_getting_started_uses_recommended_not_replay_path(self) -> None:
        text = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        self.assertNotIn("--historical-replay", text)


if __name__ == "__main__":
    unittest.main()
