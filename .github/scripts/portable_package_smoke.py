"""Build and install both distribution routes outside the source checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROBE = '''import json, sys
from pathlib import Path
import research_workbench
from research_workbench.resources import RuntimeResources, ResourceRoots
from research_workbench.capability.requirements import CapabilityRequirementSet
from research_workbench.capability.release_projection import SkillReleaseProjectionSet
from research_workbench.protocol.profiles import ProtocolProfileSet
from research_workbench.validation.schemas import SchemaCatalog
from research_workbench.io import load_document
from research_workbench.cli import main
assert Path(research_workbench.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
resources = RuntimeResources()
summary = resources.validate_catalog()
assert len(CapabilityRequirementSet.load().entries) == 4
assert len(ProtocolProfileSet.load().entries) == 2
assert SkillReleaseProjectionSet.load().entries == ()
for kind in ("research_mode", "mode_action", "decision_authority_matrix", "protocol_profile"):
    assert resources.documents(kind)
roots = ResourceRoots(Path.cwd(), resources, Path.cwd() / "integration")
assert roots.integration_path(".codex/config.toml") == Path.cwd() / "integration/.codex/config.toml"
task = Path.cwd() / "task.yaml"
assert main(["resources", "quickstart", "--output", str(task)]) == 0
assert load_document(task)["required_skills"] == []
assert not SchemaCatalog().validate("task_packet", load_document(task))
assert main(["validate", str(task), "--root", str(Path.cwd())]) == 0
summary["python"] = sys.version.split()[0]
print(json.dumps(summary, sort_keys=True))
'''


def run(args, *, cwd, env=None):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stdout)
    return result.stdout


def closure(wheel):
    with zipfile.ZipFile(wheel) as archive:
        prefix = "research_workbench/_runtime_data/"
        assets = {name.removeprefix(prefix): archive.read(name) for name in archive.namelist() if name.startswith(prefix)}
        manifest = json.loads(assets["manifest.json"])
        assert set(assets) == {entry["installed_path"] for entry in manifest["entries"]} | {"manifest.json"}
        for entry in manifest["entries"]:
            assert hashlib.sha256(assets[entry["installed_path"]]).hexdigest() == entry["sha256"]
        assert not any(".data/data/share/" in name for name in archive.namelist())
        return assets


def snapshot_sources(target):
    """Keep build hooks from replacing an editable install's live resources."""
    target.mkdir()
    shutil.copytree(ROOT / "src", target / "src", ignore=shutil.ignore_patterns(
        "_runtime_data", "_runtime_pin.py", "__pycache__", "*.egg-info", "*.pyc"))
    shutil.copytree(ROOT / "schemas", target / "schemas")
    paths = {"pyproject.toml", "MANIFEST.in", "README.md", "build_backend.py", "runtime-resources.json"}
    spec = json.loads((ROOT / "runtime-resources.json").read_bytes())
    for entry in spec["catalogs"]:
        paths.add(entry["path"])
        if "entry_kind" in entry:
            paths.update(row["document_path"] for row in json.loads((ROOT / entry["path"]).read_bytes())["entries"])
    paths.update(entry["path"] for entry in spec["release_assets"])
    for relative in paths:
        source = ROOT / relative
        assert source.resolve().is_relative_to(ROOT) and not source.is_symlink()
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", action="append", help="interpreter(s) used for fresh installs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.python:
        args.python = [str(Path(path).resolve()) for path in args.python]
    results = []
    with tempfile.TemporaryDirectory(prefix="rwb-portable-install-") as temporary:
        work = Path(temporary).resolve()
        assert not work.is_relative_to(ROOT)
        clean_env = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
        build_source = work / "source"
        snapshot_sources(build_source)
        direct, sdist, rebuilt = (work / name for name in ("direct", "sdist", "rebuilt"))
        for path in (direct, sdist, rebuilt):
            path.mkdir()
        run([sys.executable, "-m", "build", "--wheel", "--outdir", direct, build_source], cwd=work, env=clean_env)
        run([sys.executable, "-m", "build", "--sdist", "--outdir", sdist, build_source], cwd=work, env=clean_env)
        with tarfile.open(next(sdist.glob("*.tar.gz"))) as archive:
            archive.extractall(work / "unpacked", filter="data")
        source = next((work / "unpacked").iterdir())
        run([sys.executable, "-m", "build", "--wheel", "--outdir", rebuilt, source], cwd=work, env=clean_env)
        wheels = [next(path.glob("*.whl")) for path in (direct, rebuilt)]
        assert closure(wheels[0]) == closure(wheels[1]), "direct/sdist Runtime resources differ"
        for number, interpreter in enumerate(args.python or [sys.executable]):
            for route, wheel in zip(("direct", "sdist-wheel"), wheels):
                venv = work / f"venv-{number}-{route}"
                run([interpreter, "-m", "venv", venv], cwd=work, env=clean_env)
                python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                run([python, "-m", "pip", "install", wheel], cwd=work, env=clean_env)
                for isolated in (True, False):
                    project = work / f"project-{number}-{route}-{isolated}"
                    project.mkdir()
                    for directory in ("registry", "schemas", ".codex"):
                        poison = project / directory
                        poison.mkdir()
                        (poison / "poison.json").write_text("invalid")
                    env = dict(clean_env)
                    if not isolated:
                        env["PYTHONPATH"] = str(project / "registry")
                    output = run([python, *(["-I"] if isolated else []), "-c", PROBE], cwd=project, env=env)
                    summary = json.loads(output.splitlines()[-1])
                    summary.update(route=route, isolated=isolated)
                    results.append(summary)
                # Missing/corrupt package data cannot silently fall back to checkout/CWD.
                corrupt = '''from research_workbench.resources import RuntimeResources, ResourceError
r = RuntimeResources()
p = r.path("registry/skills/release-projections.json")
p.write_bytes(b"{}")
try:
    RuntimeResources()
except ResourceError:
    print("corrupt resource blocked")
else:
    raise AssertionError("corrupt resource accepted")
'''
                assert "blocked" in run([python, "-I", "-c", corrupt], cwd=work, env=clean_env)
        report = {"runtime_resources_identical": True, "manifest_sha256": hashlib.sha256(closure(wheels[0])["manifest.json"]).hexdigest(),
                  "installs": results, "merge_eligible": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
