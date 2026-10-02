"""Direct offline profile/configuration boundaries; no account or API evidence."""
import copy
import hashlib
import json
import tempfile
import traceback
import unittest
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from unittest.mock import patch

from jsonschema import Draft202012Validator

from research_workbench.adapters.models.http import EnvironmentCredential
from research_workbench.adapters.models.port import CapabilityGap, ContentBlock, Message, ModelRequest
from research_workbench.adapters.models.profile_configuration import (
    ProviderAdapterConfigV2,
    ProviderApiProfile,
    ProfileConfigurationError,
    VENDOR_PROTOCOLS,
    load_profile_configurations,
    resolve_profile_configuration,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/provider_profile_configuration/vendors"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def profile_document():
    return read(FIXTURES / "deepseek/positive.profile.json")


def config_document():
    return read(FIXTURES / "deepseek/positive.config.json")


def apply_patches(document, patches):
    result = copy.deepcopy(document)
    for item in patches:
        target = result
        for part in item["path"][:-1]:
            target = target[part]
        target[item["path"][-1]] = item["value"]
    return result


class PoisonModelMap(Mapping):
    """A caller-provided fake model map that records forbidden early reads."""
    def __init__(self):
        self.reads = 0

    def __getitem__(self, key):
        self.reads += 1
        raise AssertionError("model mapping must not be read on this rejection")

    def __iter__(self):
        raise AssertionError("model mapping must not be enumerated")

    def __len__(self):
        return 0


class ProviderProfileConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile_schema = Draft202012Validator(read(ROOT / "schemas/v0.1.0/provider-api-profile.schema.json"))
        cls.config_schema = Draft202012Validator(read(ROOT / "schemas/v0.1.0/provider-adapters-v2.schema.json"))

    def setUp(self):
        # These are method guards, not environment/vault presence operations.
        self.resolve_guard = patch.object(EnvironmentCredential, "resolve", side_effect=AssertionError("real credential access forbidden"))
        self.available_guard = patch.object(EnvironmentCredential, "available", side_effect=AssertionError("presence checks forbidden"))
        self.resolve_mock = self.resolve_guard.start()
        self.available_mock = self.available_guard.start()
        self.addCleanup(self.resolve_guard.stop)
        self.addCleanup(self.available_guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.resolve_mock.assert_not_called()
        self.available_mock.assert_not_called()

    def load(self, document):
        path = self.directory / "config.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return load_profile_configurations(path)

    def pinned(self, profile=None, *, root=None):
        directory = root or self.directory
        doc = profile or profile_document()
        path = directory / "profile.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        adapter = config_document()["adapters"][0]
        adapter["profile_ref"] = {"path": "profile.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        return adapter

    def test_eleven_vendor_positive_schema_and_fixed_identity(self):
        directories = {path.name for path in FIXTURES.iterdir() if path.is_dir()}
        self.assertEqual(directories, set(VENDOR_PROTOCOLS))
        for vendor in sorted(directories):
            with self.subTest(vendor=vendor):
                directory = FIXTURES / vendor
                profile = read(directory / "positive.profile.json")
                config = read(directory / "positive.config.json")
                metadata = read(directory / "fixture.metadata.json")
                self.profile_schema.validate(profile)
                self.config_schema.validate(config)
                parsed = ProviderApiProfile.from_mapping(profile)
                self.assertEqual(parsed.provider, vendor)
                self.assertEqual(parsed.document["model"]["requested_id"], metadata["requested_id"])
                configs = load_profile_configurations(directory / "positive.config.json")
                self.assertEqual(len(configs), 1)
                self.assertEqual(configs[0].profile_ref, metadata["profile_ref"])
                self.assertEqual(read(ROOT / configs[0].profile_ref["path"]), profile)
                self.assertFalse(metadata["live_accepted"])

    def test_per_vendor_resolve_or_explicit_blocking_gap(self):
        for vendor in sorted(VENDOR_PROTOCOLS):
            with self.subTest(vendor=vendor):
                directory = FIXTURES / vendor
                config = load_profile_configurations(directory / "positive.config.json")[0]
                metadata = read(directory / "fixture.metadata.json")
                if metadata["resolve_expected"].startswith("reject-"):
                    model_map = PoisonModelMap()
                    with self.assertRaisesRegex(ProfileConfigurationError, "gap prevents resolution"):
                        resolve_profile_configuration(config, root=ROOT, model_environment=model_map)
                    self.assertEqual(model_map.reads, 0)
                else:
                    profile, resolved = resolve_profile_configuration(config, root=ROOT)
                    self.assertEqual(profile.provider, vendor)
                    self.assertEqual(resolved["model"], metadata["requested_id"])
                    self.assertEqual(set(resolved), {"adapter_id", "enabled", "model", "profile_ref", "credential_source", "capabilities", "transport", "conformance_ref"})
                    self.assertNotIn("model_selector", resolved)

    def test_independent_vendor_negative_fixtures(self):
        for vendor in sorted(VENDOR_PROTOCOLS):
            directory = FIXTURES / vendor
            for case in read(directory / "negative.patches.json"):
                with self.subTest(vendor=vendor, case=case["case_id"]):
                    source = read(directory / ("positive.profile.json" if case["target"] == "profile" else "positive.config.json"))
                    document = apply_patches(source, case["patches"])
                    if case["expected"].startswith("schema-and-parser-reject"):
                        validator = self.profile_schema if case["target"] == "profile" else self.config_schema
                        self.assertTrue(list(validator.iter_errors(document)))
                        with self.assertRaises(ProfileConfigurationError):
                            if case["target"] == "profile":
                                ProviderApiProfile.from_mapping(document)
                            else:
                                self.load(document)
                    else:
                        config = self.load(document)[0]
                        with self.assertRaises(ProfileConfigurationError):
                            resolve_profile_configuration(config, root=ROOT)

    def test_profile_deep_freeze_and_plain_copy_are_independent(self):
        original = profile_document()
        profile = ProviderApiProfile.from_mapping(original)
        original["model"]["requested_id"] = "mutated"
        original["implementation"]["capabilities"].append("streaming")
        self.assertEqual(profile.document["model"]["requested_id"], "deepseek-flash")
        self.assertNotIn("streaming", profile.document["implementation"]["capabilities"])
        with self.assertRaises(TypeError):
            profile.document["model"]["requested_id"] = "mutated"
        with self.assertRaises(AttributeError):
            profile.document["implementation"]["capabilities"].append("streaming")
        plain = profile.to_mapping()
        plain["model"]["allowed_observed_ids"].append("mutated")
        self.assertEqual(profile.document["model"]["allowed_observed_ids"], ("deepseek-flash",))
        json.dumps(plain)

    def test_config_and_resolved_nested_values_are_frozen(self):
        original = config_document()["adapters"][0]
        config = ProviderAdapterConfigV2.from_mapping(original)
        original["transport"]["redirect_policy"] = "follow"
        self.assertEqual(config.transport["redirect_policy"], "deny")
        with self.assertRaises(TypeError):
            config.credential_source["name"] = "mutated"
        profile, resolved = resolve_profile_configuration(config, root=ROOT)
        self.assertIsInstance(resolved, MappingProxyType)
        with self.assertRaises(TypeError):
            resolved["profile_ref"]["sha256"] = "0" * 64
        self.assertEqual(profile.provider, "deepseek")

    def test_explicit_model_environment_only_and_drift(self):
        adapter = config_document()["adapters"][0]
        adapter["model_selector"] = {"kind": "environment", "value": "RWB_SYNTHETIC_MODEL"}
        config = ProviderAdapterConfigV2.from_mapping(adapter)
        for model_map in (None, {}, {"RWB_SYNTHETIC_MODEL": "unlisted-model"}):
            with self.subTest(model_map=model_map), self.assertRaises(ProfileConfigurationError):
                resolve_profile_configuration(config, root=ROOT, model_environment=model_map)
        _, resolved = resolve_profile_configuration(config, root=ROOT, model_environment={"RWB_SYNTHETIC_MODEL": "deepseek-flash"})
        self.assertEqual(resolved["model"], "deepseek-flash")

    def test_selector_cannot_target_the_credential_variable(self):
        adapter = config_document()["adapters"][0]
        adapter["model_selector"] = {"kind": "environment", "value": adapter["credential_source"]["name"]}
        with self.assertRaises(ProfileConfigurationError):
            ProviderAdapterConfigV2.from_mapping(adapter)

    def test_disabled_config_does_not_skip_validation_or_read_model_map(self):
        doc = config_document()
        doc["adapters"][0]["enabled"] = False
        config = self.load(doc)[0]
        self.assertFalse(config.enabled)
        _, resolved = resolve_profile_configuration(config, root=ROOT)
        self.assertFalse(resolved["enabled"])
        doc["adapters"][0]["unexpected"] = "SYNTHETIC_ONLY"
        with self.assertRaises(ProfileConfigurationError):
            self.load(doc)

    def test_vault_and_unknown_credential_sources_are_rejected(self):
        for source in ({"kind": "os-vault", "reference": "synthetic-label"}, {"kind": "unknown", "name": "SYNTHETIC_NAME"}, {"kind": "environment", "name": "SYNTHETIC_NAME", "value": "SYNTHETIC_ONLY"}):
            with self.subTest(kind=source["kind"]):
                adapter = config_document()["adapters"][0]
                adapter["credential_source"] = source
                with self.assertRaises(ProfileConfigurationError):
                    ProviderAdapterConfigV2.from_mapping(adapter)

    def test_unknown_profile_versions_and_vendor_family_are_rejected(self):
        changes = ((["version"], "2.0.0"), (["protocol", "revision"], "2.0.0"), (["implementation", "codec_version"], "2.0.0"), (["identity", "provider"], "unknown"), (["identity", "provider"], "google"))
        for path, value in changes:
            with self.subTest(path=path, value=value), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":path,"value":value}]))

    def test_endpoint_userinfo_downgrade_port_and_operation_are_rejected(self):
        for origin in ("http://provider.invalid", "https://user:SYNTHETIC_ONLY@provider.invalid", "https://provider.invalid/", "https://provider.invalid?", "https://provider.invalid:0", "https://provider.invalid:70000", "https://"):
            with self.subTest(origin=origin), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":["endpoint","origin"],"value":origin}]))
        for path in ("/other", "/../responses", "//responses", "/%2e%2e/responses", "/responses?secret=SYNTHETIC_ONLY"):
            with self.subTest(path=path), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":["endpoint","operation_path"],"value":path}]))

    def test_every_nested_profile_object_is_closed(self):
        for section in ("identity", "protocol", "endpoint", "auth", "model", "generation", "mapping", "implementation", "data_policy_evidence"):
            with self.subTest(section=section), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":[section,"unexpected"],"value":True}]))
        with self.assertRaises(ProfileConfigurationError):
            ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":["implementation","limits","unexpected"],"value":True}]))

    def test_unknown_policies_modes_and_capabilities_are_rejected(self):
        patches = [(["mapping", "tool_policy_id"], "python:callback"), (["generation","parameter_profile_id"], "unknown"), (["generation","continuation_policy"], "remote-state"), (["generation","mode"], "standard"), (["implementation","capabilities"], ["text","reasoning"]), (["implementation","capabilities"], ["text","text"])]
        for path, value in patches:
            with self.subTest(path=path), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":path,"value":value}]))

    def test_observed_model_policy_is_frozen(self):
        for ids in ([], ["other-model"], ["deepseek-flash", "other-model"]):
            with self.subTest(ids=ids), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":["model","allowed_observed_ids"],"value":ids}]))
        doc = profile_document()
        doc["model"]["observed_policy"] = "explicit-allowlist"
        doc["model"]["allowed_observed_ids"] = ["explicit-revision"]
        self.assertEqual(ProviderApiProfile.from_mapping(doc).document["model"]["allowed_observed_ids"], ("explicit-revision",))

    def test_profile_hash_mismatch_precedes_explicit_model_access(self):
        adapter = self.pinned()
        adapter["profile_ref"]["sha256"] = "0" * 64
        adapter["model_selector"] = {"kind":"environment","value":"RWB_SYNTHETIC_MODEL"}
        model_map = PoisonModelMap()
        with self.assertRaisesRegex(ProfileConfigurationError, "source hash mismatch"):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory, model_environment=model_map)
        self.assertEqual(model_map.reads, 0)

    def test_literal_model_drift_rejected(self):
        adapter = self.pinned()
        adapter["model_selector"]["value"] = "unlisted-model"
        with self.assertRaisesRegex(ProfileConfigurationError, "differs from the frozen profile"):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory)

    def test_requested_capability_gap_is_explicit(self):
        doc = profile_document()
        doc["implementation"]["capabilities"] = ["text"]
        adapter = self.pinned(doc)
        adapter["capabilities"] = ["text", "tools"]
        with self.assertRaises(CapabilityGap):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory)

    def test_reference_paths_are_portable_and_hash_lowercase(self):
        for path in ("../profile.json", "/profile.json", "C:/profile.json", "profile\\other.json", "profile//other.json", "CON.json", "directory./file.json", "./profile.json", "profile%2ejson"):
            with self.subTest(path=path):
                adapter = config_document()["adapters"][0]
                adapter["profile_ref"]["path"] = path
                with self.assertRaises(ProfileConfigurationError):
                    ProviderAdapterConfigV2.from_mapping(adapter)
        adapter = config_document()["adapters"][0]
        adapter["profile_ref"]["sha256"] = "A" * 64
        with self.assertRaises(ProfileConfigurationError):
            ProviderAdapterConfigV2.from_mapping(adapter)

    def test_symlink_cannot_escape_allowed_root(self):
        outside = self.directory / "outside"
        allowed = self.directory / "allowed"
        outside.mkdir()
        allowed.mkdir()
        adapter = self.pinned(root=outside)
        link = allowed / "profile.json"
        try:
            link.symlink_to(outside / "profile.json")
        except OSError:
            self.skipTest("local Windows account cannot create a symlink")
        with self.assertRaisesRegex(ProfileConfigurationError, "outside the allowed root"):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=allowed)

    def test_duplicate_adapter_and_duplicate_conflicting_reference_paths_rejected(self):
        doc = config_document()
        doc["adapters"].append(copy.deepcopy(doc["adapters"][0]))
        with self.assertRaisesRegex(ProfileConfigurationError, "duplicate adapter IDs"):
            self.load(doc)
        doc["adapters"][1]["adapter_id"] = "different-id"
        for checksum in (doc["adapters"][0]["profile_ref"]["sha256"], "0" * 64):
            doc["adapters"][1]["profile_ref"]["sha256"] = checksum
            with self.assertRaisesRegex(ProfileConfigurationError, "reference paths"):
                self.load(doc)
        doc["adapters"][1]["profile_ref"]["path"] = doc["adapters"][0]["profile_ref"]["path"].upper()
        with self.assertRaisesRegex(ProfileConfigurationError, "reference paths"):
            self.load(doc)

    def test_data_and_conformance_references_are_hash_checked(self):
        evidence = self.directory / "evidence.json"
        evidence.write_text("{}", encoding="utf-8")
        ref = {"path":"evidence.json","sha256":hashlib.sha256(evidence.read_bytes()).hexdigest()}
        doc = profile_document()
        doc["data_policy_evidence"]["regions_ref"] = ref
        adapter = self.pinned(doc)
        profile, _ = resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory)
        self.assertEqual(profile.document["data_policy_evidence"]["regions_ref"], ref)
        evidence.write_text('{"changed":true}', encoding="utf-8")
        with self.assertRaisesRegex(ProfileConfigurationError, "source hash mismatch"):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory)
        adapter = self.pinned()
        adapter["conformance_ref"] = ref
        with self.assertRaisesRegex(ProfileConfigurationError, "source hash mismatch"):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory)

    def test_duplicate_reference_roles_do_not_create_ambiguous_closure(self):
        adapter = self.pinned()
        adapter["conformance_ref"] = copy.deepcopy(adapter["profile_ref"])
        with self.assertRaisesRegex(ProfileConfigurationError, "duplicate or conflicting"):
            resolve_profile_configuration(ProviderAdapterConfigV2.from_mapping(adapter), root=self.directory)

    def test_numeric_types_finite_limits_and_transport_policies(self):
        for key, value in (("timeout_seconds",True),("timeout_seconds",float("nan")),("timeout_seconds",0),("max_response_bytes",1.5),("max_response_bytes",False),("redirect_policy","follow"),("retry_policy","automatic")):
            with self.subTest(key=key, value=value):
                adapter = config_document()["adapters"][0]
                adapter["transport"][key] = value
                with self.assertRaises(ProfileConfigurationError):
                    ProviderAdapterConfigV2.from_mapping(adapter)
        for key, value in (("max_tools",9),("max_output_tokens",257),("max_tools",True)):
            with self.subTest(key=key), self.assertRaises(ProfileConfigurationError):
                ProviderApiProfile.from_mapping(apply_patches(profile_document(), [{"path":["implementation","limits",key],"value":value}]))

    def test_duplicate_json_and_yaml_keys_reject_without_echoing_input(self):
        for suffix, content in (("json", '{"SYNTHETIC_ONLY":"first","SYNTHETIC_ONLY":"second"}'), ("yaml", 'SYNTHETIC_ONLY: first\nSYNTHETIC_ONLY: second\n')):
            path = self.directory / ("duplicate." + suffix)
            path.write_text(content, encoding="utf-8")
            with self.subTest(suffix=suffix):
                try:
                    load_profile_configurations(path)
                except ProfileConfigurationError as error:
                    self.assertNotIn("SYNTHETIC_ONLY", str(error))
                    self.assertNotIn("SYNTHETIC_ONLY", "".join(traceback.format_exception(error)))
                else:
                    self.fail("duplicate keys accepted")

    def test_bad_json_and_yaml_errors_do_not_echo_body(self):
        for suffix, content in (("json", '{"SYNTHETIC_ONLY":'), ("yaml", 'SYNTHETIC_ONLY: [\n')):
            path = self.directory / ("malformed." + suffix)
            path.write_text(content, encoding="utf-8")
            with self.subTest(suffix=suffix):
                try:
                    load_profile_configurations(path)
                except ProfileConfigurationError as error:
                    self.assertNotIn("SYNTHETIC_ONLY", "".join(traceback.format_exception(error)))
                else:
                    self.fail("malformed document accepted")

    def test_old_configuration_is_not_guessed_as_v2(self):
        for version in ("1.0.0", "3.0.0", None):
            doc = config_document()
            if version is None:
                del doc["config_version"]
            else:
                doc["config_version"] = version
            with self.subTest(version=version), self.assertRaises(ProfileConfigurationError):
                self.load(doc)

    def test_extreme_json_numeric_and_depth_errors_are_safe(self):
        for content in ("9" * 5000, "[" * 3000 + "0" + "]" * 3000):
            path = self.directory / "bounded-synthetic.json"
            path.write_text(content, encoding="utf-8")
            with self.subTest(prefix=content[0]), self.assertRaises(ProfileConfigurationError):
                load_profile_configurations(path)

    def test_disabled_public_template_is_pinned_and_has_eleven_adapters(self):
        configs = load_profile_configurations(ROOT / "registry/providers/adapters-v2.disabled.json")
        self.assertEqual(len(configs), 11)
        self.assertTrue(all(not config.enabled for config in configs))
        self.config_schema.validate(read(ROOT / "registry/providers/adapters-v2.disabled.json"))
        for config in configs:
            path = ROOT / config.profile_ref["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), config.profile_ref["sha256"])

    def test_actual_registry_profile_to_wire_encode_decode(self):
        from research_workbench.adapters.models.wire_codecs import encode_profile_request, decode_profile_response
        for vendor in sorted(VENDOR_PROTOCOLS):
            with self.subTest(vendor=vendor):
                directory = FIXTURES / vendor
                metadata = read(directory / "fixture.metadata.json")
                config = load_profile_configurations(directory / "positive.config.json")[0]
                if metadata["resolve_expected"].startswith("reject-"):
                    with self.assertRaises(ProfileConfigurationError):
                        resolve_profile_configuration(config, root=ROOT)
                    continue
                profile, resolved = resolve_profile_configuration(config, root=ROOT)
                request = ModelRequest(model=resolved["model"], messages=(Message("user", (ContentBlock("text", text="synthetic profile shape"),)),), max_output_tokens=16)
                payload = encode_profile_request(request, profile.document)
                family = profile.document["protocol"]["family"]
                if family != "gemini-generate-content":
                    self.assertEqual(payload["model"], request.model)
                if profile.document["generation"]["mode"] == "nonthinking":
                    if vendor in {"deepseek", "minimax"} and family == "responses":
                        self.assertEqual(payload["reasoning"]["effort"], "none")
                    elif vendor == "alibaba-dashscope":
                        self.assertIs(payload["enable_thinking"], False)
                    else:
                        self.assertEqual(payload["thinking"]["type"], "disabled")
                document = read(ROOT / "tests/fixtures/provider_profile_configuration/wire" / (vendor + ".response.json"))
                response = decode_profile_response(request, document, profile.document)
                self.assertEqual(response.provider, vendor)
                self.assertEqual(response.model, request.model)
                self.assertEqual(tuple(block.text for block in response.output if block.kind == "text"), ("synthetic profile answer",))


if __name__ == "__main__":
    unittest.main()
