from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.public_surface_helpers import PUBLIC_PAGES, build_input_errors, documentation_errors, selected_files


ROOT = Path(__file__).resolve().parents[1]


class PublicSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = selected_files(ROOT)

    def test_selected_source_has_closed_docs_and_build_inputs(self):
        self.assertEqual([], documentation_errors(self.files))
        self.assertEqual([], build_input_errors(self.files))

    def test_excluded_files_are_not_selected(self):
        excluded = ("tests/", "work/", "docs/workstreams/", "docs/history/", ".codex/", ".agents/")
        exact = {"docs/TASKS.md", "docs/STATUS.md", "docs/DEVELOPMENT.md", "docs/ROADMAP.md",
                 "DEVELOPMENT_HISTORY.md", "registry/skills/accepted.json", "registry/skills/sources.json"}
        self.assertEqual([], [name for name in self.files if name.startswith(excluded) or name in exact])

    def test_product_sources_and_schemas_are_complete(self):
        # Each policy version must select these whole source classes, never per-feature pruning.
        policy = json.loads(self.files[".github/release-surface.yml"])["policies"][-1]
        for path in ("src/research_workbench", "schemas"):
            self.assertIn({"path": path, "kind": "tree"}, policy["include"])

    def test_public_navigation_and_support_have_one_source(self):
        for name in PUBLIC_PAGES:
            if name not in ("CHANGELOG.md", "docs/SUPPORTED_FEATURES.md"):
                self.assertIn("SUPPORTED_FEATURES.md", self.files[name].decode())
        matrix = self.files["docs/SUPPORTED_FEATURES.md"].decode()
        for grade in ("structural", "bounded", "live", "evaluated"):
            self.assertIn(f"| {grade} |", matrix)
        self.assertEqual([], json.loads(self.files["registry/skills/release-projections.json"])["entries"])
        self.assertIn("生产 Projection index 为空", matrix)
        self.assertIn("真实对照实验尚未完成", matrix)
        self.assertIn("不承诺任何 live Provider binding", matrix)

    def test_missing_target_and_anchor_are_rejected(self):
        for link in ("[missing](missing.md)", "[bad](docs/PUBLIC_GUIDE.md#absent)",
                     "[escape](../outside.md)", "[windows](C:/secret.md)"):
            with self.subTest(link=link):
                files = {**self.files, "README.md": link.encode()}
                self.assertTrue(documentation_errors(files))

    def test_excluded_links_cannot_hide_in_reference_html_or_encoding(self):
        for link in ("[internal][state]\n\n[state]: docs/STATUS.md",
                     '<a href="docs/TASKS.md">internal</a>',
                     "[internal](docs/%53TATUS.md)",
                     "[internal](https://github.com/Example/project/blob/main/docs/STATUS.md)",
                     "[archive](work/demo/record.md)",
                     "[archive][a]\n\n[a]: work/demo/record.md",
                     '<a href="%77ork/demo/record.md">archive</a>',
                     "[archive](https://github.com/Example/project/blob/main/work/demo/record.md)"):
            with self.subTest(link=link):
                errors = documentation_errors({**self.files, "README.md": link.encode()})
                self.assertTrue(any("internal" in error for error in errors))

    def test_user_project_attempt_paths_are_not_repository_archive_links(self):
        files = {**self.files, "README.md": (
            "Read the generated `work/demo/A-001/reconstruction-report.json`.\n"
            "```shell\nrwb run reproduce manifest.yaml --root . --attempt-dir work/demo/A-001\n```\n"
        ).encode()}
        self.assertEqual([], documentation_errors(files))
        # An archive that exists in the supplied tree is still not public navigation.
        files["README.md"] = b"[archive](work/demo/record.md)"
        files["work/demo/record.md"] = b"private development evidence"
        self.assertTrue(any("internal" in error for error in documentation_errors(files)))

    def test_markdown_reference_html_and_unicode_anchor_resolve(self):
        files = {**self.files, "README.md": (
            '[guide][g]\n\n[g]: docs/PUBLIC_GUIDE.md#控制与能力\n'
            '<a href="docs/PUBLIC_GUIDE.md#执行与留痕">guide</a>\n'
            '[guide](docs/PUBLIC_GUIDE.md#%E7%8A%B6%E6%80%81%E4%B8%8E%E8%AF%81%E6%8D%AE)\n'
        ).encode()}
        self.assertEqual([], documentation_errors(files))

    def test_build_input_removal_is_rejected(self):
        action = json.loads(self.files["registry/modes/actions.json"])["entries"][0]["document_path"]
        for path in ("build_backend.py", "runtime-resources.json", "examples/quickstart/task-no-skill.yaml",
                     action):
            files = dict(self.files)
            files.pop(path)
            self.assertIn(f"missing build input: {path}", build_input_errors(files))


if __name__ == "__main__":
    unittest.main()
