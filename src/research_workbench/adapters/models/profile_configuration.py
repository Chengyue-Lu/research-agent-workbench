"""Closed, immutable API profiles and explicit non-secret configuration v2.

This module never inspects process environment or resolves credentials. File
references pin exact bytes beneath the caller's explicit root. Parsing validates
configuration, not account access, live conformance or registry acceptance.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping
from urllib.parse import unquote, urlsplit

import yaml

from research_workbench.adapters.models.port import Capability, CapabilityGap

PROTOCOL_FAMILIES = frozenset({"responses", "chat-completions", "anthropic-messages", "gemini-generate-content"})
VENDOR_PROTOCOLS = MappingProxyType({
    "openai": frozenset({"responses", "chat-completions"}),
    "anthropic": frozenset({"anthropic-messages"}),
    "google": frozenset({"gemini-generate-content"}),
    "deepseek": frozenset({"responses", "chat-completions", "anthropic-messages"}),
    "alibaba-dashscope": frozenset({"responses", "chat-completions"}),
    "zhipu": frozenset({"responses", "chat-completions", "anthropic-messages"}),
    "moonshot": frozenset({"responses", "chat-completions", "anthropic-messages"}),
    "minimax": frozenset({"responses", "chat-completions", "anthropic-messages"}),
    "siliconflow": frozenset({"chat-completions"}),
    "bytedance-ark": frozenset({"responses", "chat-completions"}),
    "openrouter": frozenset({"responses", "chat-completions"}),
})
PROFILE_CAPABILITIES = frozenset({Capability.TEXT, Capability.TOOLS, Capability.PARALLEL_TOOLS, Capability.STRUCTURED_OUTPUT})
_PROFILE_FIELDS = frozenset({"schema_version", "record_kind", "version", "profile_id", "identity", "protocol", "endpoint", "auth", "model", "generation", "mapping", "implementation", "data_policy_evidence", "documentation_refs"})
_ADAPTER_FIELDS = frozenset({"adapter_id", "enabled", "profile_ref", "model_selector", "credential_source", "capabilities", "transport", "conformance_ref"})
_ROOT_FIELDS = frozenset({"schema_version", "registry_kind", "config_version", "config_id", "adapters"})
_POLICY_FIELDS = ("role_policy_id", "tool_policy_id", "schema_policy_id", "usage_policy_id", "finish_policy_id", "error_policy_id")
POLICY_IDS = MappingProxyType({
    family: MappingProxyType({key: f"{family}:{key.removesuffix('_policy_id')}:v1" for key in _POLICY_FIELDS})
    for family in PROTOCOL_FAMILIES
})
_PATH_COMPONENT = re.compile(r"[A-Za-z0-9._-]+\Z")
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.IGNORECASE)
_HTTPS_ORIGIN = re.compile(r"https://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::[0-9]{1,5})?\Z")
_URL_PATH = re.compile(r"/(?:[A-Za-z0-9._~{}:-]+/)*[A-Za-z0-9._~{}:-]*\Z")


class ProfileConfigurationError(ValueError):
    """A safe local rejection without raw input values or credential content."""


def _reject(context: str, reason: str) -> None:
    raise ProfileConfigurationError(f"{context}: {reason}") from None


def _object(value: object, fields: frozenset[str] | set[str], context: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        _reject(context, "requires exactly the declared fields")
    return dict(value)


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        _reject(context, "requires a nonempty string without surrounding whitespace or controls")
    return value


def _choice(value: object, choices: object, context: str) -> str:
    result = _string(value, context)
    if result not in choices:
        _reject(context, "unsupported value")
    return result


def _array(value: object, context: str, *, nonempty: bool = True) -> list[object]:
    if not isinstance(value, (list, tuple)) or (nonempty and not value):
        _reject(context, "requires an array" + (" with at least one entry" if nonempty else ""))
    return list(value)


def _strings(value: object, context: str, *, nonempty: bool = True) -> list[str]:
    result = [_string(item, context) for item in _array(value, context, nonempty=nonempty)]
    if len(set(result)) != len(result):
        _reject(context, "duplicate entries")
    return result


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _reference(value: object, context: str) -> dict[str, object]:
    result = _object(value, {"path", "sha256"}, context)
    raw = _string(result["path"], context)
    parts = raw.split("/")
    if any(not _PATH_COMPONENT.fullmatch(part) or part in {".", ".."} or part.endswith(".") or _DEVICE.fullmatch(part) for part in parts):
        _reject(context, "requires a portable relative file path")
    if not isinstance(result["sha256"], str) or not _SHA256.fullmatch(result["sha256"]):
        _reject(context, "requires a lowercase SHA-256")
    return result


def _url_origin(value: object, context: str) -> str:
    raw = _string(value, context)
    try:
        parsed = urlsplit(raw)
        hostname, port = parsed.hostname, parsed.port
    except ValueError:
        _reject(context, "requires a valid HTTPS origin")
    if (not _HTTPS_ORIGIN.fullmatch(raw) or parsed.scheme != "https" or not hostname or parsed.username is not None or parsed.password is not None
            or parsed.path or parsed.query or parsed.fragment or "?" in raw or "#" in raw or "\\" in raw
            or any(c.isspace() for c in raw) or (port is not None and port < 1)):
        _reject(context, "requires a non-secret HTTPS origin")
    return raw


def _endpoint_path(value: object, context: str, *, empty: bool = False) -> str:
    if value == "" and empty:
        return ""
    raw = _string(value, context)
    if not _URL_PATH.fullmatch(raw) or raw.startswith("//") or any(c in raw for c in "?#\\") or any(c.isspace() for c in raw):
        _reject(context, "requires an absolute non-secret URL path")
    decoded = unquote(raw)
    if any(part in {".", ".."} for part in decoded.split("/")) or any(c in decoded for c in "?#\\"):
        _reject(context, "path traversal or encoded URL delimiters are forbidden")
    return raw


def _capabilities(value: object, context: str) -> list[str]:
    result = _strings(value, context)
    if any(item not in PROFILE_CAPABILITIES for item in result) or Capability.TEXT not in result:
        _reject(context, "requires text and only implemented offline capabilities")
    return result


def _positive_number(value: object, context: str, *, integer: bool = False, maximum: int | None = None) -> object:
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)) or value <= 0 or (maximum is not None and value > maximum):
        _reject(context, "requires a finite positive number within the declared limit")
    if isinstance(value, float) and not math.isfinite(value):
        _reject(context, "requires a finite positive number within the declared limit")
    return value


def _profile_mapping(value: object) -> dict[str, object]:
    doc = _object(value, _PROFILE_FIELDS, "profile")
    for field_name, expected in (("schema_version", "0.1.0"), ("record_kind", "provider_api_profile"), ("version", "1.0.0")):
        _choice(doc[field_name], {expected}, "profile version")
    _string(doc["profile_id"], "profile identity")
    identity = _object(doc["identity"], {"provider", "operator", "service", "model_publisher", "access_region", "deployment_region"}, "provider identity")
    vendor = _choice(identity["provider"], VENDOR_PROTOCOLS, "provider identity")
    for key in ("operator", "service", "model_publisher"):
        _string(identity[key], "provider identity")
    for key in ("access_region", "deployment_region"):
        if identity[key] is not None:
            _string(identity[key], "provider region")
    protocol = _object(doc["protocol"], {"family", "revision"}, "protocol")
    family = _choice(protocol["family"], VENDOR_PROTOCOLS[vendor], "vendor protocol")
    _choice(protocol["revision"], {"1.0.0"}, "protocol revision")
    endpoint = _object(doc["endpoint"], {"origin", "base_path", "operation_path", "api_version"}, "endpoint")
    _url_origin(endpoint["origin"], "endpoint origin")
    _endpoint_path(endpoint["base_path"], "endpoint base path", empty=True)
    operation = _endpoint_path(endpoint["operation_path"], "endpoint operation")
    expected_operation = {"responses": "/responses", "chat-completions": "/chat/completions", "anthropic-messages": "/messages", "gemini-generate-content": "/models/{model}:generateContent"}[family]
    if operation != expected_operation or "{" in endpoint["base_path"] or "}" in endpoint["base_path"]:
        _reject("endpoint operation", "unsupported protocol operation template")
    if endpoint["api_version"] is not None:
        _string(endpoint["api_version"], "endpoint API version")
    auth = _object(doc["auth"], {"kind", "header_name", "prefix", "public_parameters"}, "authentication")
    _choice(auth["kind"], {"api-key-header"}, "authentication")
    expected_auth = (("x-api-key", "", {"anthropic-version": "2023-06-01"}) if family == "anthropic-messages"
                     else ("x-goog-api-key", "", {}) if family == "gemini-generate-content"
                     else ("Authorization", "Bearer ", {}))
    if (auth["header_name"], auth["prefix"], auth["public_parameters"]) != expected_auth:
        _reject("authentication", "unsupported fixed authentication policy")
    model = _object(doc["model"], {"requested_id", "publisher", "observed_policy", "allowed_observed_ids", "documented_revision"}, "model binding")
    requested = _string(model["requested_id"], "model binding")
    _string(model["publisher"], "model publisher")
    observed = _choice(model["observed_policy"], {"exact", "explicit-allowlist"}, "observed model policy")
    allowlist = _strings(model["allowed_observed_ids"], "observed model IDs")
    if observed == "exact" and allowlist != [requested]:
        _reject("observed model policy", "exact policy requires only the requested model ID")
    if model["documented_revision"] is not None:
        _string(model["documented_revision"], "model documented revision")
    generation = _object(doc["generation"], {"mode", "parameter_profile_id", "continuation_policy"}, "generation")
    mode = _choice(generation["mode"], {"standard", "nonthinking"}, "generation mode")
    if vendor == "deepseek" and mode != "nonthinking":
        _reject("generation mode", "DeepSeek candidate requires native nonthinking")
    if vendor in {"openai", "anthropic", "google"} and mode != "standard":
        _reject("generation mode", "unsupported mode for this vendor profile")
    _choice(generation["parameter_profile_id"], {f"{family}:parameters:v1"}, "parameter policy")
    _choice(generation["continuation_policy"], {"local-messages-only"}, "continuation policy")
    mapping = _object(doc["mapping"], set(_POLICY_FIELDS), "wire policies")
    for key in _POLICY_FIELDS:
        _choice(mapping[key], {POLICY_IDS[family][key]}, "wire policy")
    implementation = _object(doc["implementation"], {"adapter_version", "codec_version", "capabilities", "limits", "known_gaps", "binding_policy_version"}, "implementation")
    for key in ("adapter_version", "codec_version"):
        _choice(implementation[key], {"1.0.0"}, "implementation version")
    _choice(implementation["binding_policy_version"], {"provider-binding-v2"}, "binding policy")
    _capabilities(implementation["capabilities"], "implementation capabilities")
    limits = _object(implementation["limits"], {"max_output_tokens", "max_tools"}, "implementation limits")
    _positive_number(limits["max_output_tokens"], "output token limit", integer=True, maximum=1024)
    _positive_number(limits["max_tools"], "tool limit", integer=True, maximum=8)
    _strings(implementation["known_gaps"], "known gaps", nonempty=False)
    evidence = _object(doc["data_policy_evidence"], {"regions_ref", "controls_ref"}, "data evidence")
    for item in evidence.values():
        if item is not None:
            _reference(item, "data evidence reference")
    for url in _strings(doc["documentation_refs"], "documentation references"):
        try:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None or "\\" in url or any(c.isspace() for c in url):
                _reject("documentation references", "requires non-secret official HTTPS references")
            _ = parsed.port
        except ValueError:
            _reject("documentation references", "requires valid HTTPS references")
    # Deep copy independently of every nested caller object before freezing.
    return _thaw(_freeze(doc))


def _adapter_mapping(value: object) -> dict[str, object]:
    doc = _object(value, _ADAPTER_FIELDS, "adapter configuration")
    _string(doc["adapter_id"], "adapter identity")
    if not isinstance(doc["enabled"], bool):
        _reject("adapter enabled", "requires a boolean")
    _reference(doc["profile_ref"], "profile reference")
    selector = _object(doc["model_selector"], {"kind", "value"}, "model selector")
    kind = _choice(selector["kind"], {"literal", "environment"}, "model selector")
    selected = _string(selector["value"], "model selector")
    if kind == "environment" and not _ENVIRONMENT_NAME.fullmatch(selected):
        _reject("model selector", "requires an environment variable name")
    credential = _object(doc["credential_source"], {"kind", "name"}, "credential source")
    _choice(credential["kind"], {"environment"}, "credential source")
    if not isinstance(credential["name"], str) or not _ENVIRONMENT_NAME.fullmatch(credential["name"]):
        _reject("credential source", "requires an environment variable name")
    if kind == "environment" and selected == credential["name"]:
        _reject("model selector", "cannot use the declared credential variable")
    _capabilities(doc["capabilities"], "requested capabilities")
    transport = _object(doc["transport"], {"timeout_seconds", "max_response_bytes", "redirect_policy", "retry_policy"}, "transport")
    _positive_number(transport["timeout_seconds"], "transport timeout")
    _positive_number(transport["max_response_bytes"], "transport response limit", integer=True)
    _choice(transport["redirect_policy"], {"deny"}, "redirect policy")
    _choice(transport["retry_policy"], {"none"}, "retry policy")
    if doc["conformance_ref"] is not None:
        _reference(doc["conformance_ref"], "conformance reference")
    return _thaw(_freeze(doc))


@dataclass(frozen=True, slots=True)
class ProviderApiProfile:
    document: Mapping[str, object] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "document", _freeze(_profile_mapping(self.document)))

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ProviderApiProfile:
        return cls(value)

    def to_mapping(self) -> dict[str, object]:
        return _thaw(self.document)

    @property
    def profile_id(self) -> str:
        return self.document["profile_id"]

    @property
    def provider(self) -> str:
        return self.document["identity"]["provider"]

    @property
    def capabilities(self) -> frozenset[Capability]:
        return frozenset(Capability(item) for item in self.document["implementation"]["capabilities"])


@dataclass(frozen=True, slots=True)
class ProviderAdapterConfigV2:
    document: Mapping[str, object] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "document", _freeze(_adapter_mapping(self.document)))

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ProviderAdapterConfigV2:
        return cls(value)

    def to_mapping(self) -> dict[str, object]:
        return _thaw(self.document)

    @property
    def adapter_id(self) -> str:
        return self.document["adapter_id"]

    @property
    def enabled(self) -> bool:
        return self.document["enabled"]

    @property
    def profile_ref(self) -> Mapping[str, object]:
        return self.document["profile_ref"]

    @property
    def capabilities(self) -> frozenset[Capability]:
        return frozenset(Capability(item) for item in self.document["capabilities"])

    @property
    def credential_source(self) -> Mapping[str, object]:
        return self.document["credential_source"]

    @property
    def transport(self) -> Mapping[str, object]:
        return self.document["transport"]


def _reject_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            _reject("document", "duplicate object keys")
        result[key] = value
    return result


class _ClosedLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(loader: _ClosedLoader, node: yaml.MappingNode, deep: bool = False) -> dict[str, object]:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            _reject("document", "requires unique string object keys")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_ClosedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def _document_bytes(path: Path, content: bytes) -> object:
    try:
        text = content.decode("utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text, object_pairs_hook=_reject_pairs, parse_constant=lambda _: _reject("document", "non-finite JSON values"))
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.load(text, Loader=_ClosedLoader)
    except ProfileConfigurationError:
        raise
    except (UnicodeError, ValueError, RecursionError, yaml.YAMLError):
        _reject("document", "invalid UTF-8 or document syntax")
    _reject("document", "requires JSON or YAML")


def load_profile_configurations(path: str | Path) -> tuple[ProviderAdapterConfigV2, ...]:
    file_path = Path(path)
    try:
        content = file_path.read_bytes()
    except OSError:
        _reject("configuration file", "unreadable file")
    doc = _object(_document_bytes(file_path, content), _ROOT_FIELDS, "configuration root")
    for key, expected in (("schema_version", "0.1.0"), ("registry_kind", "provider_adapters"), ("config_version", "2.0.0")):
        _choice(doc[key], {expected}, "configuration version")
    _string(doc["config_id"], "configuration identity")
    configs = tuple(ProviderAdapterConfigV2.from_mapping(item) for item in _array(doc["adapters"], "adapters"))
    if len({item.adapter_id for item in configs}) != len(configs):
        _reject("adapters", "duplicate adapter IDs")
    references = {}
    for item in configs:
        for reference in (item.profile_ref, item.document["conformance_ref"]):
            if reference is None:
                continue
            portable_path = reference["path"].casefold()
            if portable_path in references:
                _reject("file references", "duplicate or conflicting file reference paths")
            references[portable_path] = reference["sha256"]
    return configs


def _read_reference(reference: Mapping[str, object], root: Path) -> tuple[Path, bytes]:
    safe_ref = _reference(reference, "file reference")
    try:
        allowed_root = root.resolve(strict=True)
        if not allowed_root.is_dir():
            _reject("reference root", "requires an existing directory")
        target = allowed_root.joinpath(*PurePosixPath(safe_ref["path"]).parts).resolve(strict=True)
        if not target.is_relative_to(allowed_root) or not target.is_file():
            _reject("file reference", "target is outside the allowed root or is not a file")
        data = target.read_bytes()
    except (OSError, RuntimeError):
        _reject("file reference", "unreadable target beneath allowed root")
    if hashlib.sha256(data).hexdigest() != safe_ref["sha256"]:
        _reject("file reference", "source hash mismatch")
    return target, data


def resolve_profile_configuration(
    config: ProviderAdapterConfigV2,
    *,
    root: str | Path,
    model_environment: Mapping[str, str] | None = None,
) -> tuple[ProviderApiProfile, Mapping[str, object]]:
    """Resolve pinned profile and an explicit model map without touching a Key.

    The resolved closed mapping contains adapter_id/enabled/model/profile_ref/
    credential_source/capabilities/transport/conformance_ref. Arrays and nested
    mappings are immutable. Disabled parsing does not grant execution permission.
    """
    if not isinstance(config, ProviderAdapterConfigV2):
        _reject("configuration", "requires a validated v2 config")
    target, content = _read_reference(config.profile_ref, Path(root))
    profile = ProviderApiProfile.from_mapping(_document_bytes(target, content))
    if any(gap.startswith("blocking:") for gap in profile.document["implementation"]["known_gaps"]):
        _reject("profile execution", "documented binding or mode gap prevents resolution")
    gaps = config.capabilities - profile.capabilities
    if gaps:
        raise CapabilityGap(profile.provider, sorted(gaps, key=str))
    references = [config.profile_ref, config.document["conformance_ref"], *profile.document["data_policy_evidence"].values()]
    declared_paths = [item["path"].casefold() for item in references if item is not None]
    if len(set(declared_paths)) != len(declared_paths):
        _reject("file references", "duplicate or conflicting file reference paths")
    for reference in references[1:]:
        if reference is not None:
            _read_reference(reference, Path(root))
    selector = config.document["model_selector"]
    if selector["kind"] == "environment":
        if not isinstance(model_environment, Mapping):
            _reject("model selector", "requires an explicit non-secret model mapping")
        model = model_environment.get(selector["value"])
    else:
        model = selector["value"]
    model = _string(model, "resolved model")
    if model != profile.document["model"]["requested_id"]:
        _reject("model binding", "resolved model differs from the frozen profile")
    resolved = {key: value for key, value in config.to_mapping().items() if key != "model_selector"}
    resolved["model"] = model
    return profile, _freeze(resolved)
