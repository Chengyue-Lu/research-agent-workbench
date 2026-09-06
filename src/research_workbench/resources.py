"""Pinned installed resources, independent of project and integration roots."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


class ResourceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ResourceError(message)


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate resource metadata key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)


def portable(path):
    require(isinstance(path, str) and path and unicodedata.normalize("NFC", path) == path,
            "invalid resource path")
    require(not any(char in path for char in '\\:<>"|?*') and not any(ord(char) < 32 for char in path),
            "unsafe resource path")
    for part in path.split("/"):
        require(part not in ("", ".", "..") and part == part.rstrip(". "), "unsafe resource path component")
        require(not re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", part.split(".")[0]),
                "reserved resource path")
    return path


def no_link(path):
    require(not path.is_symlink() and not (hasattr(path, "is_junction") and path.is_junction()),
            "linked resource path")
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError as exc:
        raise ResourceError("missing or inaccessible resource path") from exc
    require(not (attributes & 0x400), "reparse resource path")


KINDS = {
    "schema": r"schemas/v[0-9.]+/[^/]+\.schema\.json",
    "research_mode": r"registry/modes/(?:v[0-9.]+/)?[^/]+\.yaml",
    "mode_action_registry": r"registry/modes/actions\.json",
    "mode_action": r"registry/modes/actions/.+\.yaml",
    "decision_authority_matrix": r"registry/authority/decision-authority-matrix\.yaml",
    "capability_requirement_index": r"registry/capabilities/requirements\.json",
    "capability_requirement": r"registry/capabilities/requirements/[^/]+\.yaml",
    "protocol_profile_index": r"registry/protocol-profiles\.json",
    "protocol_profile": r"registry/protocol-profiles/[^/]+\.yaml",
    "skill_release_projection_index": r"registry/skills/release-projections\.json",
    "skill_release_projection": r"registry/skills/release-projections/[^/]+\.(?:yaml|json)",
    "skill_manifest": r"registry/skills/accepted/[^/]+\.yaml",
    "skill_asset": r"\.agents/skills/[^/]+/.+",
    "task_packet": r"examples/quickstart/task-no-skill\.yaml",
}
INDEXES = {
    "mode_action_registry": ("mode_action", ("action_id", "version")),
    "capability_requirement_index": ("capability_requirement", ("requirement_id",)),
    "protocol_profile_index": ("protocol_profile", ("profile_id", "version")),
    "skill_release_projection_index": ("skill_release_projection", ("projection_id", "projection_version")),
}


class RuntimeResources:
    """A manifest pinned by package code, or an explicit caller-supplied digest.

    A custom resource root needs its own trusted digest. Nothing searches CWD,
    project parents, environment variables, or maintainer publication history.
    """

    def __init__(self, root: str | Path | None = None, *, expected_sha256: str | None = None):
        if root is None:
            from research_workbench._runtime_pin import MANIFEST_SHA256
            root = Path(__file__).parent / "_runtime_data"
            require(expected_sha256 is None or expected_sha256 == MANIFEST_SHA256,
                    "package manifest expectation mismatch")
            expected_sha256 = MANIFEST_SHA256
        require(Path(root).is_absolute(), "resource override root must be absolute")
        self.root = Path(root)
        for path in (self.root, *self.root.parents):
            no_link(path)
        require(isinstance(expected_sha256, str) and re.fullmatch(r"[a-f0-9]{64}", expected_sha256),
                "resource override requires an external manifest digest")
        manifest_path = self.root / "manifest.json"
        no_link(manifest_path)
        data = manifest_path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected_sha256, "Runtime resource manifest hash drift")
        self.manifest = strict_json(data)
        require(isinstance(self.manifest, dict) and isinstance(self.manifest.get("entries"), list),
                "invalid Runtime resource manifest")
        self.entries = {}
        installed = set()
        folded = {}
        for entry in self.manifest["entries"]:
            require(isinstance(entry, dict), "invalid resource entry")
            logical = portable(entry.get("logical_path"))
            mapped = portable(entry.get("installed_path"))
            require(logical not in self.entries and mapped not in installed, "duplicate resource mapping")
            for prefix, value in (("logical", logical), ("installed", mapped)):
                # Check every directory component too (A/x versus a/y).
                parts = value.split("/")
                for end in range(1, len(parts) + 1):
                    name = "/".join(parts[:end])
                    key = (prefix, name.casefold())
                    require(key not in folded or folded[key] == name,
                            "casefold resource collision")
                    folded[key] = name
            kind = entry.get("kind")
            require(kind in KINDS and re.fullmatch(KINDS[kind], logical), "resource outside public catalog class")
            require(mapped.startswith("releases/") if kind in ("skill_manifest", "skill_asset")
                    else mapped == "assets/" + logical, "invalid installed resource namespace")
            self.entries[logical] = entry
            installed.add(mapped)
            self.read(logical)
        actual = set()
        for base, dirs, names in os.walk(self.root, followlinks=False):
            for name in dirs + names:
                path = Path(base) / name
                no_link(path)
                relative = path.relative_to(self.root).as_posix()
                if name in dirs:
                    require(any(item.startswith(relative + "/") for item in installed), "orphan resource directory")
                else:
                    actual.add(relative)
        require(actual == installed | {"manifest.json"}, "Runtime resource file closure mismatch")
        from jsonschema import Draft202012Validator
        schema = strict_json(self.read("schemas/v0.1.0/runtime-resource-manifest.schema.json"))
        errors = list(Draft202012Validator(schema).iter_errors(self.manifest))
        require(not errors, "Runtime resource manifest schema invalid")
        require(list(self.entries) == sorted(self.entries), "Runtime resource order is not canonical")

    @property
    def schema_root(self):
        return self.root / "assets/schemas"

    @property
    def catalog_root(self):
        return self.root / "assets"

    def path(self, logical):
        portable(logical)
        require(logical in self.entries, "unindexed Runtime resource")
        result = self.root / self.entries[logical]["installed_path"]
        require(result.resolve().is_relative_to(self.root.resolve()), "Runtime resource path escapes root")
        for path in (result, *result.parents):
            no_link(path)
            if path == self.root:
                break
        require(result.is_file(), "missing Runtime resource")
        return result

    def read(self, logical):
        data = self.path(logical).read_bytes()
        entry = self.entries[logical]
        require(len(data) == entry.get("size") and hashlib.sha256(data).hexdigest() == entry.get("sha256"),
                "Runtime resource byte/hash drift")
        return data

    def validate_catalog(self):
        """Installed-runtime closure; never a publication/admission validator."""
        from research_workbench.io import load_document_bytes
        from research_workbench.validation.schemas import SchemaCatalog
        catalog = SchemaCatalog(self.schema_root, resource_reader=self)
        documents = {}
        identities = set()
        for logical, entry in self.entries.items():
            kind = entry["kind"]
            if kind in ("schema", "skill_asset"):
                continue
            document = load_document_bytes(Path(logical), self.read(logical))
            require(not catalog.validate(kind, document), f"Runtime catalog schema invalid: {logical}")
            documents[logical] = document
            if kind == "research_mode":
                key = (document["mode_id"], document["version"])
                require(key not in identities, "duplicate Mode identity")
                identities.add(key)
        indexed = set()
        for index_kind, (kind, fields) in INDEXES.items():
            indices = [key for key, entry in self.entries.items() if entry["kind"] == index_kind]
            require(len(indices) == 1, "Runtime catalog requires one index per class")
            seen = set()
            for entry in documents[indices[0]]["entries"]:
                logical = entry["document_path"]
                require(logical in documents and self.entries[logical]["kind"] == kind,
                        "indexed Runtime document missing or wrong kind")
                identity = tuple(entry[field] for field in fields)
                require(identity not in seen and logical not in indexed, "duplicate Runtime index identity/path")
                seen.add(identity)
                indexed.add(logical)
                document = documents[logical]
                require(tuple(document[field] for field in fields) == identity, "Runtime index identity drift")
                require(hashlib.sha256(self.read(logical)).hexdigest() == entry["content_hash"].removeprefix("sha256:"),
                        "Runtime index content hash drift")
                if kind == "mode_action":
                    require(document["mode_ref"] == entry["mode_ref"], "Runtime Action Mode drift")
                    require(tuple(document["mode_ref"].rsplit("@", 1)) in identities, "Runtime Action Mode missing")
                elif kind == "skill_release_projection":
                    require(entry["projection_ref"] == "@".join(identity)
                            and entry["release_ref"] == document["release"]["release_ref"], "Projection index reference drift")
            require({key for key, entry in self.entries.items() if entry["kind"] == kind} <= indexed,
                    "orphan Runtime catalog document")
        actions = {f"{document['action_id']}@{document['version']}": document["mode_ref"]
                   for path, document in documents.items() if self.entries[path]["kind"] == "mode_action"}
        for path, document in documents.items():
            if self.entries[path]["kind"] == "research_mode":
                mode_ref = f"{document['mode_id']}@{document['version']}"
                require(all(actions.get(ref) == mode_ref for ref in document.get("action_refs", [])),
                        "Runtime Mode Action reference missing or mismatched")
        self._validate_releases(documents)
        return {"resources": len(self.entries), "schemas": len(catalog.names),
                "modes": len(identities), "projections": sum(entry["kind"] == "skill_release_projection"
                                                            for entry in self.entries.values()),
                "validation_profile": "installed-runtime", "merge_eligible": False}

    def documents(self, kind):
        """Load published Mode/Action/Authority and other typed catalog inputs."""
        from research_workbench.io import load_document_bytes
        require(kind in KINDS and kind not in ("schema", "skill_asset"), "not a document resource class")
        self.validate_catalog()
        return tuple(load_document_bytes(Path(path), self.read(path))
                     for path, entry in self.entries.items() if entry["kind"] == kind)

    def _validate_releases(self, documents):
        referenced = set()
        releases = set()
        for path, entry in self.entries.items():
            if entry["kind"] != "skill_release_projection":
                continue
            release = documents[path]["release"]
            identity = (release["skill_id"], release["skill_version"])
            require(identity not in releases and release["release_ref"] == "@".join(identity), "duplicate or invalid Skill release")
            releases.add(identity)
            manifest_path = release["manifest_path"]
            require(manifest_path in documents and self.entries[manifest_path]["kind"] == "skill_manifest",
                    "Projection Skill manifest missing")
            referenced.add(manifest_path)
            require(hashlib.sha256(self.read(manifest_path)).hexdigest() == release["manifest_sha256"].removeprefix("sha256:"),
                    "Projection Skill manifest hash drift")
            manifest = documents[manifest_path]
            require((manifest["skill_id"], manifest["version"]) == identity, "Projection Skill manifest identity drift")
            source = manifest["source"]
            logical = portable(source["locator"])
            require(logical in self.entries and self.entries[logical]["kind"] == "skill_asset", "Projection Skill content missing")
            content_hash = hashlib.sha256(self.read(logical)).hexdigest()
            require(content_hash == release["content_hash"].removeprefix("sha256:")
                    == source["content_hash"].removeprefix("sha256:"), "Projection Skill content hash drift")
            prefix = logical.rsplit("/", 1)[0] + "/"
            digest = hashlib.sha256()
            for asset in sorted(key for key in self.entries if key.startswith(prefix)):
                require(self.entries[asset]["kind"] == "skill_asset", "invalid Skill package resource class")
                relative = asset.removeprefix(prefix).encode()
                digest.update(len(relative).to_bytes(8, "big"))
                digest.update(relative)
                digest.update(hashlib.sha256(self.read(asset)).digest())
                referenced.add(asset)
            require(digest.hexdigest() == release["package_hash"].removeprefix("sha256:")
                    == source.get("package_hash", "").removeprefix("sha256:"), "Projection Skill package hash drift")
        require(referenced == {key for key, entry in self.entries.items()
                               if entry["kind"] in ("skill_manifest", "skill_asset")}, "orphan Skill release asset")


@dataclass(frozen=True)
class ResourceRoots:
    project_root: Path
    runtime: RuntimeResources
    integration_config_root: Path | None = None

    def __post_init__(self):
        require(self.project_root.is_absolute(), "project root must be explicit and absolute")
        require(self.integration_config_root is None or self.integration_config_root.is_absolute(),
                "integration config root must be explicit and absolute")

    def integration_path(self, relative):
        require(self.integration_config_root is not None, "integration config root required")
        portable(relative)
        require(relative.startswith(".codex/"), "not an integration config path")
        result = self.integration_config_root / relative
        require(result.resolve().is_relative_to(self.integration_config_root.resolve()), "integration path escapes root")
        return result
