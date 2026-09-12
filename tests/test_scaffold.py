"""Installed-root initialization and actual offline reconstruction, not research efficacy."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import yaml

from research_workbench import scaffold
from research_workbench.artifacts.run_reconstruction import reproduce_run
from research_workbench.cli import main
from research_workbench.resources import ResourceError, RuntimeResources


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = self.parent / "project"

    def cli(self, *args):
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def test_default_template_closes_task_profile_and_installed_resources(self):
        code, output = self.cli("init", str(self.root), "--project-id", '研究 "project"', "--json")
        self.assertEqual(code, 0, output)
        created = json.loads(output)
        self.assertFalse(created["executed"])
        self.assertEqual(created["template"], "no-skill")
        self.assertEqual(Path(created["project_root"]), self.root)
        self.assertFalse((self.root / "registry").exists())
        metadata = tomllib.loads((self.root / "rwb-project.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project_id"], '研究 "project"')
        task = yaml.safe_load((self.root / "tasks/task.yaml").read_bytes())
        self.assertEqual(task["required_skills"], [])
        self.assertEqual(task["agent_profile"], "local-no-skill")
        self.assertEqual(self.cli("project", "check", str(self.root))[0], 0)
        self.assertEqual(self.cli("validate", str(self.root / "tasks/task.yaml"),
                                  str(self.root / "profiles/local-no-skill.yaml"), "--root", str(self.root))[0], 0)

    def test_each_template_and_legacy_checkpoint_flow_is_available(self):
        for template in scaffold.TEMPLATES:
            with self.subTest(template=template):
                root = self.parent / template
                code, output = self.cli("init", str(root), "--template", template)
                self.assertEqual(code, 0, output)
                self.assertIn("initialized", output)
                self.assertFalse(scaffold.check_project(root)["executed"])
                self.assertEqual((root / "tasks/task.yaml").exists(), template != "minimal")

    def test_offline_example_checks_without_execution_and_reproduces_in_fresh_process(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("initialization must not execute")):
            scaffold.initialize_project(self.root, template="offline-demo")
            self.assertFalse(scaffold.check_project(self.root)["executed"])
        manifest = self.root / scaffold.DEMO_PATH / "manifest.yaml"
        report = reproduce_run(self.root, manifest, attempt_dir="work/demo/A-001")
        self.assertEqual(report["status"], "matched")
        self.assertTrue(report["executed"])
        self.assertNotEqual(report["child_pid"], os.getpid())
        self.assertTrue(report["negative_result"])
        self.assertFalse(any(report["authority_boundaries"].values()))
        self.assertEqual(self.cli("validate", str(self.root / "work/demo/A-001/reconstruction-report.json"),
                                  "--root", str(self.root))[0], 0)

    def test_project_is_relocatable_and_ignores_unrelated_cwd_catalogs(self):
        scaffold.initialize_project(self.root, template="offline-demo")
        moved = self.parent / "relocated"
        shutil.copytree(self.root, moved)
        poison = self.parent / "poison"
        for name in ("registry", "schemas", "profiles", ".codex"):
            (poison / name).mkdir(parents=True)
            (poison / name / "poison.json").write_text("invalid")
        completed = subprocess.run([sys.executable, "-I", "-m", "research_workbench", "project", "check", str(moved)],
                                   cwd=poison, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(Path(json.loads(completed.stdout)["project_root"]), moved)

    def test_existing_contents_and_file_destination_are_never_overwritten(self):
        self.root.mkdir()
        saved = self.root / "keep.txt"
        saved.write_bytes(b"user data")
        self.assertEqual(self.cli("init", str(self.root))[0], 2)
        self.assertEqual(saved.read_bytes(), b"user data")
        self.assertEqual(self.cli("init", str(saved))[0], 2)
        self.assertEqual(list(self.root.iterdir()), [saved])

    def test_empty_destination_supported_and_rename_failure_restores_it(self):
        self.root.mkdir()
        with mock.patch.object(Path, "rename", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                scaffold.initialize_project(self.root)
        self.assertTrue(self.root.is_dir())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(list(self.parent.iterdir()), [self.root])
        scaffold.initialize_project(self.root)
        self.assertFalse(scaffold.check_project(self.root)["executed"])

    def test_invalid_template_or_id_writes_nothing(self):
        for kwargs in ({"template": "unknown"}, {"project_id": " "}):
            with self.assertRaises(ValueError):
                scaffold.initialize_project(self.root, **kwargs)
            self.assertFalse(self.root.exists())

    def test_custom_runtime_root_needs_exact_external_pin(self):
        resources = RuntimeResources()
        override = self.parent / "runtime"
        shutil.copytree(resources.root, override)
        digest = hashlib.sha256((override / "manifest.json").read_bytes()).hexdigest()
        args = ["--runtime-root", str(override)]
        self.assertEqual(self.cli("init", str(self.root), *args)[0], 2)
        self.assertFalse(self.root.exists())
        args += ["--manifest-sha256", digest]
        self.assertEqual(self.cli("init", str(self.root), *args)[0], 0)
        self.assertEqual(self.cli("project", "check", str(self.root), *args)[0], 0)
        (override / "manifest.json").write_bytes(b"{}")
        self.assertEqual(self.cli("project", "check", str(self.root), *args)[0], 2)

    def test_template_catalog_corruption_fails_before_destination_creation(self):
        template = self.parent / "template"
        shutil.copytree(scaffold.DEMO_ROOT, template)
        with mock.patch.object(scaffold, "DEMO_ROOT", template):
            catalog = template / "catalog.json"
            original = catalog.read_bytes()
            catalog.write_bytes(b"{}")
            with self.assertRaisesRegex(ResourceError, "catalog hash"):
                scaffold.initialize_project(self.root, template="offline-demo")
            catalog.write_bytes(original)
            (template / "unexpected.txt").write_bytes(b"extra")
            with self.assertRaisesRegex(ResourceError, "file closure"):
                scaffold.initialize_project(self.root, template="offline-demo")
            (template / "unexpected.txt").unlink()
            (template / "simulate.py.txt").write_bytes(b"bad code")
            with self.assertRaisesRegex(ResourceError, "asset hash"):
                scaffold.initialize_project(self.root, template="offline-demo")
        self.assertFalse(self.root.exists())

    def test_project_metadata_versions_and_runtime_pin_fail_closed(self):
        scaffold.initialize_project(self.root)
        path = self.root / "rwb-project.toml"
        original = path.read_text(encoding="utf-8")
        for key, value in (("format_version", "9.0.0"), ("template_version", "9.0.0"),
                           ("template", "unknown"), ("runtime_manifest_sha256", "0" * 64)):
            metadata = tomllib.loads(original)
            metadata[key] = value
            path.write_text("\n".join(f"{key} = {json.dumps(value)}" for key, value in metadata.items()), encoding="utf-8")
            self.assertEqual(self.cli("project", "check", str(self.root))[0], 2)
        path.write_text(original, encoding="utf-8")
        self.assertEqual(self.cli("project", "check", str(self.root))[0], 0)

    def test_changed_project_identity_profile_and_example_pins_are_rejected(self):
        scaffold.initialize_project(self.root, template="offline-demo")
        for name, key, value in (("project-protocol.yaml", "project_id", "other"),
                                 ("tasks/task.yaml", "agent_profile", "missing-profile"),
                                 ("profiles/local-no-skill.yaml", "schema_version", "9.0.0")):
            path = self.root / name
            original = path.read_bytes()
            document = yaml.safe_load(original)
            document[key] = value
            path.write_text(yaml.safe_dump(document), encoding="utf-8")
            self.assertEqual(self.cli("project", "check", str(self.root))[0], 2)
            path.write_bytes(original)
        (self.root / scaffold.DEMO_PATH / "inputs.json.txt").write_bytes(b"changed")
        self.assertEqual(self.cli("project", "check", str(self.root))[0], 2)

    def test_linked_destination_is_rejected_without_writing_target(self):
        target = self.parent / "target"
        target.mkdir()
        try:
            self.root.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks unavailable")
        self.assertEqual(self.cli("init", str(self.root))[0], 2)
        self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
