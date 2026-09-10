"""Build the same explicit Runtime resource closure for wheels and sdists."""
from __future__ import annotations

import hashlib
import json
import importlib.util
import re
import shutil
import sys
from pathlib import Path

from setuptools import build_meta as backend
from setuptools.command.sdist import sdist


ROOT = Path(__file__).resolve().parent


class RuntimeSdist(sdist):
    def make_release_tree(self, base_dir, files):
        manifest = json.loads((ROOT / "src/research_workbench/_runtime_data/manifest.json").read_bytes())
        files = sorted(set(files) | {entry["logical_path"] for entry in manifest["entries"]})
        super().make_release_tree(base_dir, files)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def generate(root: Path = ROOT):
    contract_spec = importlib.util.spec_from_file_location(
        "_rwb_build_resources", ROOT / "src/research_workbench/resources.py")
    contract = importlib.util.module_from_spec(contract_spec)
    sys.modules[contract_spec.name] = contract
    contract_spec.loader.exec_module(contract)
    spec = json.loads((root / "runtime-resources.json").read_bytes())
    selected = {path.relative_to(root).as_posix(): "schema"
                for path in (root / "schemas").glob("v*/*.schema.json")}
    for row in spec["catalogs"]:
        selected[row["path"]] = row["kind"]
        if "entry_kind" in row:
            index = json.loads((root / row["path"]).read_bytes())
            for entry in index["entries"]:
                path = entry["document_path"]
                if not path.startswith(row["entry_prefix"]):
                    raise ValueError("catalog entry outside declared resource class")
                selected[path] = row["entry_kind"]
    # Conditional release assets are exact paths, never a broad Skill tree.
    for row in spec["release_assets"]:
        if row["path"] in selected:
            raise ValueError("duplicate conditional resource")
        selected[row["path"]] = row["kind"]
    target = root / "src/research_workbench/_runtime_data"
    if target.is_symlink() or target.resolve() != root.resolve() / "src/research_workbench/_runtime_data":
        raise ValueError("unsafe generated resource target")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    entries = []
    for logical, kind in sorted(selected.items()):
        contract.portable(logical)
        if kind not in contract.KINDS or not re.fullmatch(contract.KINDS[kind], logical):
            raise ValueError("source resource outside public catalog class")
        source = root / logical
        contract.no_link(source)
        if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError("missing or unsafe source resource")
        for parent in source.parents[:source.parents.index(root)]:
            contract.no_link(parent)
        data = source.read_bytes()
        mapped = "assets/" + logical
        if kind in ("skill_manifest", "skill_asset"):
            mapped = "releases/" + hashlib.sha256(logical.encode()).hexdigest() + "/" + source.name
        destination = target / mapped
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        entries.append({"logical_path": logical, "installed_path": mapped, "kind": kind,
                        "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = canonical({"schema_version": "0.1.0", "kind": "runtime_resource_manifest",
                          "manifest_id": "rwb-runtime-resources", "version": "1.0.0", "entries": entries})
    (target / "manifest.json").write_bytes(manifest)
    pin = hashlib.sha256(manifest).hexdigest()
    (target.parent / "_runtime_pin.py").write_text(f'MANIFEST_SHA256 = "{pin}"\n', encoding="utf-8", newline="\n")
    return pin


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    generate()
    return backend.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    generate()
    return backend.build_sdist(sdist_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    generate()
    return backend.build_editable(wheel_directory, config_settings, metadata_directory)


get_requires_for_build_wheel = backend.get_requires_for_build_wheel
get_requires_for_build_sdist = backend.get_requires_for_build_sdist
get_requires_for_build_editable = backend.get_requires_for_build_editable
prepare_metadata_for_build_wheel = backend.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = backend.prepare_metadata_for_build_editable
