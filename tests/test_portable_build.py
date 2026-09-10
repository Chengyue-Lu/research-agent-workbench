"""Distribution closure and build orchestration contracts; installs run in CI smoke."""
import hashlib
import importlib.util
import io
import json
import runpy
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import build_backend

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portable_package_smoke", ROOT / ".github/scripts/portable_package_smoke.py")
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class PortableBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def source(self, *, catalogs=None, assets=None):
        spec = {"catalogs": catalogs or [], "release_assets": assets or []}
        (self.root / "runtime-resources.json").write_text(json.dumps(spec), encoding="utf-8")
        return self.root

    def test_build_rejects_catalog_escape_duplicate_missing_and_linked_sources(self):
        index = self.root / "index.json"
        index.write_text(json.dumps({"entries": [{"document_path": "elsewhere/item.yaml"}]}))
        self.source(catalogs=[{"path": "index.json", "kind": "mode_index", "entry_kind": "mode", "entry_prefix": "registry/"}])
        with self.assertRaisesRegex(ValueError, "outside declared resource class"):
            build_backend.generate(self.root)
        self.source(catalogs=[{"path": "same", "kind": "schema"}], assets=[{"path": "same", "kind": "schema"}])
        with self.assertRaisesRegex(ValueError, "duplicate conditional"):
            build_backend.generate(self.root)
        self.source(assets=[{"path": "schemas/v0.1.0/missing.schema.json", "kind": "schema"}])
        with self.assertRaisesRegex(ValueError, "missing or inaccessible"):
            build_backend.generate(self.root)
        missing = self.root / "schemas/v0.1.0/missing.schema.json"
        missing.mkdir(parents=True)
        self.source()
        with self.assertRaisesRegex(ValueError, "missing or unsafe"):
            build_backend.generate(self.root)
        missing.rmdir()
        target = self.root / "src/research_workbench/_runtime_data"
        with patch.object(Path, "is_symlink", autospec=True, side_effect=lambda p: p == target):
            with self.assertRaisesRegex(ValueError, "unsafe generated"):
                build_backend.generate(self.root)
        source = self.root / "schemas/v0.1.0/item.schema.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("{}")
        self.source()
        with patch.object(Path, "is_symlink", autospec=True, side_effect=lambda p: p == source.parent):
            with self.assertRaisesRegex(ValueError, "linked resource path"):
                build_backend.generate(self.root)

    def test_conditional_asset_mapping_and_sdist_source_closure(self):
        logical = ".agents/skills/synthetic/SKILL.md"
        source = self.root / logical
        source.parent.mkdir(parents=True)
        source.write_bytes(b"# synthetic\n")
        self.source(assets=[{"path": logical, "kind": "skill_asset"}])
        pin = build_backend.generate(self.root)
        generated = self.root / "src/research_workbench/_runtime_data"
        manifest = json.loads((generated / "manifest.json").read_bytes())
        entry, = manifest["entries"]
        self.assertEqual("releases/" + hashlib.sha256(logical.encode()).hexdigest() + "/SKILL.md", entry["installed_path"])
        self.assertEqual(source.read_bytes(), (generated / entry["installed_path"]).read_bytes())
        self.assertEqual(pin, hashlib.sha256((generated / "manifest.json").read_bytes()).hexdigest())
        with patch.object(build_backend, "ROOT", self.root), patch.object(build_backend.sdist, "make_release_tree") as parent:
            command = object.__new__(build_backend.RuntimeSdist)
            command.make_release_tree("dist", ["README.md", "README.md"])
            parent.assert_called_once_with("dist", [logical, "README.md"])

    def test_all_pep517_routes_generate_before_delegation(self):
        for name, arguments in (("build_wheel", ("wheel", {"key": "value"}, "metadata")),
                                ("build_sdist", ("sdist", {})), ("build_editable", ("editable", {}, None))):
            calls = []
            with self.subTest(route=name), patch.object(build_backend, "generate", side_effect=lambda: calls.append("generate")), patch.object(
                build_backend.backend, name, side_effect=lambda *args: calls.append(args) or "artifact"
            ):
                self.assertEqual("artifact", getattr(build_backend, name)(*arguments))
            self.assertEqual(["generate", arguments], calls)

    def test_snapshot_copies_explicit_closure_without_generated_editable_data(self):
        target = self.root / "source"
        smoke.snapshot_sources(target)
        self.assertEqual((ROOT / "runtime-resources.json").read_bytes(), (target / "runtime-resources.json").read_bytes())
        self.assertFalse((target / "src/research_workbench/_runtime_data").exists())
        self.assertFalse((target / "src/research_workbench/_runtime_pin.py").exists())
        spec = json.loads((target / "runtime-resources.json").read_bytes())
        # Exercise the conditional asset route using an explicit synthetic source.
        relative = ".agents/skills/synthetic/SKILL.md"
        asset = target / relative
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b"synthetic")
        spec["release_assets"] = [{"path": relative, "kind": "skill_asset"}]
        (target / "runtime-resources.json").write_text(json.dumps(spec))
        with patch.object(smoke, "ROOT", target):
            smoke.snapshot_sources(self.root / "second")
        self.assertEqual(b"synthetic", (self.root / "second" / relative).read_bytes())

    def wheel(self, path, *, corrupt=False):
        data = b"{}"
        manifest = {"entries": [{"installed_path": "assets/item.json", "sha256": hashlib.sha256(data).hexdigest()}]}
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("research_workbench/__init__.py", "")
            archive.writestr("research_workbench/_runtime_data/manifest.json", json.dumps(manifest))
            archive.writestr("research_workbench/_runtime_data/assets/item.json", b"bad" if corrupt else data)

    def test_wheel_closure_hashes_and_subprocess_failures(self):
        wheel = self.root / "fixture.whl"
        self.wheel(wheel)
        self.assertEqual({"manifest.json", "assets/item.json"}, set(smoke.closure(wheel)))
        self.wheel(wheel, corrupt=True)
        with self.assertRaises(AssertionError):
            smoke.closure(wheel)
        for code in (0, 1):
            with patch.object(smoke.subprocess, "run", return_value=subprocess.CompletedProcess([], code, "result")) as run:
                if code:
                    with self.assertRaisesRegex(RuntimeError, "result"):
                        smoke.run([self.root / "python"], cwd=self.root)
                else:
                    self.assertEqual("result", smoke.run(["python"], cwd=self.root, env={}))
                self.assertEqual(str(run.call_args.args[0][0]), run.call_args.args[0][0])

    def test_smoke_orchestrates_both_distribution_routes_and_isolation_modes(self):
        for interpreters in ([], ["--python", sys.executable]):
            calls = []

            def run(args, *, cwd, env):
                args = list(map(str, args))
                calls.append((args, Path(cwd), env))
                if "build" in args:
                    output = Path(args[args.index("--outdir") + 1])
                    if "--sdist" in args:
                        with tarfile.open(output / "fixture.tar.gz", "w:gz") as archive:
                            info = tarfile.TarInfo("fixture/pyproject.toml")
                            info.size = 2
                            archive.addfile(info, io.BytesIO(b"{}"))
                    else:
                        self.wheel(output / "fixture.whl")
                if "-c" in args:
                    return '{"python":"fixture"}\n' if args[-1] == smoke.PROBE else "corrupt resource blocked"
                return ""

            output = self.root / "report.json"
            with self.subTest(interpreters=interpreters), patch.object(sys, "argv", ["smoke", "--output", str(output), *interpreters]), patch.object(
                smoke, "run", side_effect=run
            ), patch.object(smoke, "snapshot_sources", side_effect=lambda p: p.mkdir()), redirect_stdout(io.StringIO()):
                smoke.main()
            report = json.loads(output.read_bytes())
            self.assertTrue(report["runtime_resources_identical"])
            self.assertFalse(report["merge_eligible"])
            self.assertEqual({(route, isolated) for route in ("direct", "sdist-wheel") for isolated in (True, False)},
                             {(row["route"], row["isolated"]) for row in report["installs"]})
            self.assertEqual(3, sum("build" in args for args, _, _ in calls))
            self.assertTrue(all("PYTHONHOME" not in env for _, _, env in calls))
            for args, cwd, env in calls:
                self.assertFalse(cwd.is_relative_to(ROOT))
                self.assertEqual("PYTHONPATH" in env, "-c" in args and args[-1] == smoke.PROBE and "-I" not in args)

    def test_script_entry_requires_report_destination(self):
        with patch.object(sys, "argv", ["portable_package_smoke.py"]), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            runpy.run_path(str(ROOT / ".github/scripts/portable_package_smoke.py"), run_name="__main__")
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
