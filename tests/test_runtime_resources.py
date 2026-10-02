from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import yaml

from research_workbench.cli import main
from research_workbench.resources import ResourceError, ResourceRoots, RuntimeResources, no_link, portable, strict_json
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class RuntimeResourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rwb-resource-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "resources"
        shutil.copytree(ROOT / "src/research_workbench/_runtime_data", self.root)
        self.manifest = json.loads((self.root / "manifest.json").read_bytes())

    def resource(self):
        if all(isinstance(entry, dict) and "logical_path" in entry for entry in self.manifest["entries"]):
            self.manifest["entries"].sort(key=lambda entry: entry["logical_path"])
        raw = (json.dumps(self.manifest, sort_keys=True) + "\n").encode()
        (self.root / "manifest.json").write_bytes(raw)
        return RuntimeResources(self.root, expected_sha256=hashlib.sha256(raw).hexdigest())

    def put(self, logical, data, kind=None):
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True).encode()
        entry = next((entry for entry in self.manifest["entries"] if entry["logical_path"] == logical), None)
        if entry is None:
            mapped = "assets/" + logical
            if kind in ("skill_asset", "skill_manifest"):
                mapped = "releases/" + hashlib.sha256(logical.encode()).hexdigest() + "/" + logical.rsplit("/", 1)[-1]
            entry = {"logical_path": logical, "installed_path": mapped, "kind": kind}
            self.manifest["entries"].append(entry)
        path = self.root / entry["installed_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entry.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        return entry

    def document(self, logical):
        entry = next(entry for entry in self.manifest["entries"] if entry["logical_path"] == logical)
        return yaml.safe_load((self.root / entry["installed_path"]).read_bytes())

    def add_release(self):
        from tests.skill_runtime_fixtures import SkillRuntimeBundleFixture
        projection = SkillRuntimeBundleFixture.projection()
        manifest = yaml.safe_load((ROOT / "registry/skills/accepted/literature-evidence-extraction.yaml").read_bytes())
        logical = ".agents/skills/synthetic-runtime-skill/SKILL.md"
        content = b"# Synthetic Skill\n"
        digest = hashlib.sha256()
        relative = b"SKILL.md"
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(hashlib.sha256(content).digest())
        content_hash = hashlib.sha256(content).hexdigest()
        manifest.update(skill_id="synthetic-runtime-skill", version="1.0.0")
        manifest["source"].update(locator=logical, content_hash=content_hash, package_hash=digest.hexdigest())
        manifest_path = "registry/skills/accepted/synthetic-runtime-skill.yaml"
        manifest_entry = self.put(manifest_path, manifest, "skill_manifest")
        self.put(logical, content, "skill_asset")
        projection["release"].update(manifest_path=manifest_path, manifest_sha256="sha256:" + manifest_entry["sha256"],
                                     content_hash="sha256:" + content_hash, package_hash="sha256:" + digest.hexdigest())
        path = "registry/skills/release-projections/synthetic-runtime-skill.json"
        entry = self.put(path, projection, "skill_release_projection")
        index_path = "registry/skills/release-projections.json"
        index = self.document(index_path)
        index["entries"] = [{"projection_ref": "synthetic-runtime-skill-1.0.0@1.0.0",
                             "projection_id": projection["projection_id"], "projection_version": "1.0.0",
                             "release_ref": projection["release"]["release_ref"], "document_path": path,
                             "content_hash": "sha256:" + entry["sha256"]}]
        self.put(index_path, index)
        return projection, path, manifest_path, logical

    def test_default_catalogs_and_three_roots_ignore_cwd_resources(self):
        from research_workbench.capability.requirements import CapabilityRequirementSet
        from research_workbench.capability.release_projection import SkillReleaseProjectionSet
        from research_workbench.protocol.profiles import ProtocolProfileSet
        poison = self.base / "project"
        poison.mkdir()
        for name in ("schemas", "registry", ".codex"):
            (poison / name).mkdir()
            (poison / name / "poison.json").write_text("invalid")
        previous = Path.cwd()
        try:
            os.chdir(poison)
            resources = RuntimeResources()
            summary = resources.validate_catalog()
            self.assertEqual(0, summary["projections"])
            self.assertEqual(4, summary["modes"])
            self.assertEqual(4, len(CapabilityRequirementSet.load().entries))
            self.assertEqual(2, len(ProtocolProfileSet.load().entries))
            self.assertEqual((), SkillReleaseProjectionSet.load().entries)
            self.assertTrue(SchemaCatalog().schema("task-packet"))
            self.assertEqual(32, len(resources.documents("mode_action")))
            roots = ResourceRoots(poison, resources, self.base / "integration")
            self.assertEqual(self.base / "integration/.codex/config.toml", roots.integration_path(".codex/config.toml"))
        finally:
            os.chdir(previous)
        for loader in (CapabilityRequirementSet, ProtocolProfileSet, SkillReleaseProjectionSet):
            with self.assertRaisesRegex(ValueError, "explicit project root"):
                loader.load("custom.json")

    def test_explicit_requirement_root_does_not_need_project_schemas(self):
        from research_workbench.capability.requirements import CapabilityRequirementSet
        project = self.base / "project"
        shutil.copytree(ROOT / "registry/capabilities/requirements", project / "registry/capabilities/requirements")
        shutil.copyfile(ROOT / "registry/capabilities/requirements.json", project / "registry/capabilities/requirements.json")
        self.assertEqual(4, len(CapabilityRequirementSet.load(project_root=project).entries))

    def test_override_needs_external_pin_and_rejects_manifest_drift(self):
        with self.assertRaisesRegex(ResourceError, "expectation mismatch"):
            RuntimeResources(expected_sha256="a" * 64)
        for root, pin in ((self.root, None), (Path("relative"), "a" * 64), (self.root, "a" * 64)):
            with self.subTest(root=str(root), pin=pin), self.assertRaises(ResourceError):
                RuntimeResources(root, expected_sha256=pin)
        with self.assertRaises(ResourceError):
            strict_json(b'{"x":1,"x":2}')
        resources = self.resource()
        with self.assertRaises(ResourceError):
            resources.read("registry/skills/accepted.json")
        with self.assertRaises(ResourceError):
            resources.documents("skill_asset")
        with self.assertRaisesRegex(ValueError, "Schema root differs"):
            SchemaCatalog(self.base, resource_reader=resources)
        schema = resources.path("schemas/v0.1.0/task-packet.schema.json")
        schema.write_bytes(b"{}")
        with self.assertRaisesRegex(ResourceError, "hash drift"):
            SchemaCatalog(resources.schema_root, resource_reader=resources)

    def test_missing_corrupt_extra_and_empty_directory_fail_closed(self):
        entry = self.manifest["entries"][0]
        path = self.root / entry["installed_path"]
        original = path.read_bytes()
        for data in (b"corrupt", None):
            if data is None:
                path.unlink()
            else:
                path.write_bytes(data)
            with self.assertRaises(ResourceError):
                self.resource()
            path.write_bytes(original)
        extra = self.root / "extra"
        extra.write_text("orphan")
        with self.assertRaisesRegex(ResourceError, "closure"):
            self.resource()
        extra.unlink()
        extra.mkdir()
        with self.assertRaisesRegex(ResourceError, "orphan resource directory"):
            self.resource()

    def test_portable_paths_namespace_duplicates_and_manifest_shape(self):
        for path in (None, "", "/absolute", "../escape", "a/./b", "a//b", "C:/bad", "a\\b", "NUL.txt", "x.", "x ", "a\x00", "e\u0301"):
            with self.subTest(path=path), self.assertRaises(ResourceError):
                portable(path)
        original = copy.deepcopy(self.manifest)
        changes = [lambda m: m.update(unknown=True), lambda m: m.update(entries=[False]),
                   lambda m: m["entries"].append(copy.deepcopy(m["entries"][0])),
                   lambda m: m["entries"][0].update(installed_path=".codex/config.toml"),
                   lambda m: m["entries"][0].update(kind="unknown"),
                   lambda m: m["entries"][0].update(logical_path="registry/skills/accepted.json"),
                   lambda m: m["entries"][0].update(size=True)]
        for change in changes:
            self.manifest = copy.deepcopy(original)
            change(self.manifest)
            with self.subTest(change=change), self.assertRaises(ResourceError):
                self.resource()
        self.manifest = copy.deepcopy(original)
        entry = copy.deepcopy(self.manifest["entries"][0])
        entry["logical_path"] = entry["logical_path"].replace("examples/", "Examples/")
        self.manifest["entries"].append(entry)
        with self.assertRaises(ResourceError):
            self.resource()

    def test_runtime_catalog_schema_hash_identity_index_and_orphan_attacks(self):
        index_path = "registry/capabilities/requirements.json"
        original = self.document(index_path)
        attacks = [lambda d: d["entries"][0].update(content_hash="sha256:" + "a" * 64),
                   lambda d: d["entries"][0].update(requirement_id="different"),
                   lambda d: d["entries"][0].update(document_path="registry/capabilities/requirements/missing.yaml"),
                   lambda d: d["entries"].append(copy.deepcopy(d["entries"][0])),
                   lambda d: d["entries"].pop(), lambda d: d.update(unknown=True)]
        for attack in attacks:
            document = copy.deepcopy(original)
            attack(document)
            self.put(index_path, document)
            with self.subTest(attack=attack), self.assertRaises(ResourceError):
                self.resource().validate_catalog()

    def test_conditional_skill_assets_map_outside_legacy_paths(self):
        _, _, _, logical = self.add_release()
        resource = self.resource()
        self.assertEqual(1, resource.validate_catalog()["projections"])
        self.assertIn("releases", resource.path(logical).parts)
        self.assertNotIn(".agents", resource.path(logical).parts)
        self.assertFalse((self.root / "assets/registry/skills/accepted.json").exists())

    def test_mode_action_reference_and_unindexed_skill_asset_are_rejected(self):
        path = "registry/modes/v0.2.0/evidence-synthesis.yaml"
        original = self.document(path)
        changed = copy.deepcopy(original)
        changed["action_refs"][0] = "ES-A1@99.0.0"
        self.put(path, changed)
        with self.assertRaisesRegex(ResourceError, "Mode Action reference"):
            self.resource().validate_catalog()
        self.put(path, original)
        self.put(".agents/skills/orphan/SKILL.md", b"orphan", "skill_asset")
        with self.assertRaisesRegex(ResourceError, "orphan Skill release asset"):
            self.resource().validate_catalog()

    def test_skill_release_asset_omission_orphan_and_byte_drift(self):
        projection, path, manifest_path, logical = self.add_release()
        for field in ("manifest_sha256", "content_hash", "package_hash"):
            changed = copy.deepcopy(projection)
            changed["release"][field] = "sha256:" + "e" * 64
            entry = self.put(path, changed)
            index = self.document("registry/skills/release-projections.json")
            index["entries"][0]["content_hash"] = "sha256:" + entry["sha256"]
            self.put("registry/skills/release-projections.json", index)
            with self.subTest(field=field), self.assertRaises(ResourceError):
                self.resource().validate_catalog()
        self.put(".agents/skills/orphan/SKILL.md", b"orphan", "skill_asset")
        index = self.document("registry/skills/release-projections.json")
        index["entries"].clear()
        self.put("registry/skills/release-projections.json", index)
        # Removing the projection from its index cannot admit leftover assets.
        with self.assertRaises(ResourceError):
            self.resource().validate_catalog()

    def test_links_and_root_escape_fail_closed(self):
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)):
            with self.assertRaisesRegex(ResourceError, "reparse"):
                no_link(self.root)
        with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(ResourceError):
            self.resource()
        if hasattr(Path, "is_junction"):
            with patch.object(Path, "is_junction", return_value=True), self.assertRaises(ResourceError):
                self.resource()
        resource = self.resource()
        for root, integration in ((Path("relative"), None), (self.base, Path("relative"))):
            with self.assertRaises(ResourceError):
                ResourceRoots(root, resource, integration)
        for roots, path in ((ResourceRoots(self.base, resource), ".codex/config.toml"),
                            (ResourceRoots(self.base, resource, self.base), "registry/file")):
            with self.assertRaises(ResourceError):
                roots.integration_path(path)

    def test_resource_cli_no_skill_quickstart_and_explicit_maintainer_config(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(["resources", "check"]))
            task = self.base / "project/task.yaml"
            self.assertEqual(0, main(["resources", "quickstart", "--output", str(task)]))
            document = yaml.safe_load(task.read_bytes())
            self.assertEqual([], document["required_skills"])
            self.assertEqual([], SchemaCatalog().validate("task_packet", document))
            self.assertEqual(2, main(["resources", "quickstart", "--output", str(task)]))
        for arguments in (["skills", "accepted"], ["skills", "candidates"], ["providers", "list"],
                          ["providers", "probe"], ["models", "probe"], ["runtime", "codex", "validate"]):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(arguments)

    def provider_resource(self):
        """Compose the new explicit provider rows in a private Runtime fixture."""
        spec = json.loads((ROOT / "runtime-resources.json").read_bytes())
        selected = [row for row in spec["catalogs"]
                    if row["kind"] in {"provider_api_profile", "provider_adapters_v2"}]
        self.assertEqual(13, len(selected))
        self.assertEqual(12, sum(row["kind"] == "provider_api_profile" for row in selected))
        self.put("schemas/v0.1.0/runtime-resource-manifest.schema.json",
                 (ROOT / "schemas/v0.1.0/runtime-resource-manifest.schema.json").read_bytes())
        for row in selected:
            self.put(row["path"], (ROOT / row["path"]).read_bytes(), row["kind"])
        return self.resource()

    def test_provider_catalog_preserves_bytes_disabled_templates_and_installed_resolution(self):
        from research_workbench.adapters.models.configured import build_profile_provider
        from research_workbench.adapters.models.port import ProviderError
        from research_workbench.adapters.models.profile_configuration import (
            load_profile_configurations, resolve_profile_configuration,
        )
        resource = self.provider_resource()
        result = resource.validate_catalog()
        self.assertFalse(result["merge_eligible"])
        profiles = resource.documents("provider_api_profile")
        self.assertEqual(12, len(profiles))
        self.assertEqual(11, len({p["identity"]["provider"] for p in profiles}))
        for logical, entry in resource.entries.items():
            if entry["kind"] in {"provider_api_profile", "provider_adapters_v2"}:
                self.assertEqual((ROOT / logical).read_bytes(), resource.read(logical))
        configs = load_profile_configurations(resource.path("registry/providers/adapters-v2.disabled.json"))
        self.assertEqual(11, len(configs))
        self.assertTrue(all(not c.enabled for c in configs))
        config = next(c for c in configs if c.profile_ref["path"].endswith("deepseek-responses-v1.json"))
        selector = config.document["model_selector"]
        profile, resolved = resolve_profile_configuration(
            config, root=resource.catalog_root,
            model_environment={selector["value"]: "deepseek-flash"},
        )
        self.assertEqual(("deepseek", "deepseek-flash"), (profile.provider, resolved["model"]))
        with patch("research_workbench.adapters.models.http.EnvironmentCredential.available",
                   side_effect=AssertionError("no credential presence allowed")), patch(
            "research_workbench.adapters.models.http.EnvironmentCredential.resolve",
            side_effect=AssertionError("no credential resolution allowed"),
        ), self.assertRaises(ProviderError):
            build_profile_provider(config, root=resource.catalog_root)

    def test_provider_catalog_rejects_profile_reference_hash_drift(self):
        self.provider_resource()
        logical = "registry/providers/adapters-v2.disabled.json"
        document = self.document(logical)
        document["adapters"][0]["profile_ref"]["sha256"] = "0" * 64
        self.put(logical, document)
        with self.assertRaisesRegex(ResourceError, "profile reference hash drift"):
            self.resource().validate_catalog()

    def test_provider_catalog_rejects_missing_or_wrong_kind_profile_target(self):
        for wrong_kind in (False, True):
            self.provider_resource()
            logical = "registry/providers/adapters-v2.disabled.json"
            document = self.document(logical)
            reference = document["adapters"][0]["profile_ref"]
            if wrong_kind:
                target = "registry/modes/evidence-synthesis.yaml"
                reference.update(path=target, sha256=hashlib.sha256(self.resource().read(target)).hexdigest())
            else:
                reference["path"] = "registry/providers/profiles/missing-profile.json"
            self.put(logical, document)
            with self.subTest(wrong_kind=wrong_kind), self.assertRaisesRegex(ResourceError, "target missing or wrong kind"):
                self.resource().validate_catalog()

    def test_provider_catalog_rejects_enabled_template(self):
        self.provider_resource()
        logical = "registry/providers/adapters-v2.disabled.json"
        document = self.document(logical)
        document["adapters"][0]["enabled"] = True
        self.put(logical, document)
        with self.assertRaisesRegex(ResourceError, "templates must remain disabled"):
            self.resource().validate_catalog()

    def test_provider_catalog_rejects_duplicate_profile_identity(self):
        self.provider_resource()
        logical = "registry/providers/profiles/google-gemma-content-v1.json"
        document = self.document(logical)
        document["profile_id"] = self.document("registry/providers/profiles/openai-responses-v1.json")["profile_id"]
        self.put(logical, document)
        with self.assertRaisesRegex(ResourceError, "duplicate Runtime Provider profile identity"):
            self.resource().validate_catalog()

    def test_provider_catalog_rejects_capability_enlargement(self):
        self.provider_resource()
        logical = "registry/providers/adapters-v2.disabled.json"
        document = self.document(logical)
        target = "registry/providers/profiles/google-gemma-content-v1.json"
        document["adapters"][0].update(
            profile_ref={"path": target, "sha256": hashlib.sha256(self.resource().read(target)).hexdigest()},
            capabilities=["text", "tools"],
        )
        self.put(logical, document)
        with self.assertRaisesRegex(ResourceError, "capabilities exceed"):
            self.resource().validate_catalog()

    def test_provider_catalog_closed_configuration_rejects_unimplemented_credential_backend(self):
        self.provider_resource()
        logical = "registry/providers/adapters-v2.disabled.json"
        document = self.document(logical)
        document["adapters"][0]["credential_source"] = {"kind": "os-vault", "reference": "synthetic-vault-reference"}
        self.put(logical, document)
        with self.assertRaisesRegex(ResourceError, "invalid closed Runtime Provider template"):
            self.resource().validate_catalog()

    def test_provider_catalog_rejects_duplicate_keys_adapter_ids_and_reference_paths(self):
        logical = "registry/providers/adapters-v2.disabled.json"
        self.provider_resource()
        raw = (ROOT / logical).read_bytes().replace(b'"config_version": "2.0.0",',
                                                   b'"config_version": "2.0.0", "config_version": "2.0.0",')
        self.put(logical, raw)
        with self.assertRaisesRegex(ResourceError, "duplicate resource metadata key"):
            self.resource().validate_catalog()
        for duplicate_id in (True, False):
            self.provider_resource()
            document = self.document(logical)
            if duplicate_id:
                document["adapters"][1]["adapter_id"] = document["adapters"][0]["adapter_id"]
            else:
                document["adapters"][1]["profile_ref"] = copy.deepcopy(document["adapters"][0]["profile_ref"])
            self.put(logical, document)
            with self.subTest(duplicate_id=duplicate_id), self.assertRaisesRegex(ResourceError, "duplicate Runtime Provider"):
                self.resource().validate_catalog()

    def test_build_regeneration_is_identical_and_removes_stale_output(self):
        import build_backend
        source = self.base / "source"
        source.mkdir()
        shutil.copyfile(ROOT / "runtime-resources.json", source / "runtime-resources.json")
        spec = json.loads((ROOT / "runtime-resources.json").read_bytes())
        logical_paths = {entry["logical_path"] for entry in self.manifest["entries"]}
        logical_paths.update(row["path"] for row in spec["catalogs"])
        logical_paths.update(path.relative_to(ROOT).as_posix()
                             for path in (ROOT / "schemas").glob("v*/*.schema.json"))
        for logical in sorted(logical_paths):
            path = source / logical
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / logical, path)
        pin = build_backend.generate(source)
        generated = source / "src/research_workbench/_runtime_data"
        generated_manifest = (generated / "manifest.json").read_bytes()
        (generated / "stale.txt").write_text("stale")
        self.assertEqual(pin, build_backend.generate(source))
        self.assertEqual(generated_manifest, (generated / "manifest.json").read_bytes())
        self.assertFalse((generated / "stale.txt").exists())
        resources = RuntimeResources(generated, expected_sha256=pin)
        self.assertEqual(0, resources.validate_catalog()["projections"])
        self.assertEqual(13, sum(e["kind"] in {"provider_api_profile", "provider_adapters_v2"}
                                 for e in resources.entries.values()))
        spec = json.loads((source / "runtime-resources.json").read_bytes())
        spec["catalogs"].append({"path": "registry/skills/accepted.json", "kind": "skill_asset"})
        (source / "runtime-resources.json").write_text(json.dumps(spec), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "outside public catalog class"):
            build_backend.generate(source)


if __name__ == "__main__":
    unittest.main()
