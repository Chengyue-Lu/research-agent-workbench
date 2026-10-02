"""Closed profile/configuration composition for the model Provider port.

Construction resolves only non-secret configuration. Credentials are resolved
once, after local admission and binding checks, at the HTTP send boundary.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar
from urllib.parse import quote

from research_workbench.adapters.models.base import (
    perform_json_request,
    preflight,
    raise_provider_http_error,
    validate_adapter_capabilities,
    validate_response_contract,
)
from research_workbench.adapters.models.http import (
    CredentialProvider,
    EnvironmentCredential,
    HttpTransport,
    UrllibTransport,
    validate_https_endpoint,
)
from research_workbench.adapters.models.port import (
    Capability,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
)
from research_workbench.adapters.models.profile_configuration import (
    ProviderAdapterConfigV2,
    ProviderApiProfile,
    resolve_profile_configuration,
)
from research_workbench.adapters.models.wire_codecs import (
    CODEC_VERSION,
    decode_profile_response,
    encode_profile_request,
)


ADAPTER_VERSION = "1.0.0"
_IMPLEMENTED = frozenset({Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT})
# Official catalog status observed 2026-10-02, not an inferred shutdown date:
# https://ai.google.dev/gemini-api/docs/models
# https://ai.google.dev/gemini-api/docs/deprecations
_RETIRED_MODELS = MappingProxyType({"google": frozenset({"gemini-2.0-flash", "gemini-2.0-flash-001"})})


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _reject(message: str) -> None:
    raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, message)


def _preflight(request: ModelRequest, snapshot: ProviderCapabilities) -> None:
    failure: ProviderError | None = None
    try:
        preflight(request, snapshot)
    except ProviderError as exc:
        category = exc.category if isinstance(exc.category, ProviderErrorCategory) else ProviderErrorCategory.INVALID_REQUEST
        failure = ProviderError(category, "profile request admission failed")
    if failure is not None:
        raise failure


def _class_name(value: object) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _reference_bytes(root: Path, reference: Mapping[str, object]) -> bytes:
    """Recheck confinement, links and bytes before a credential can be read."""
    path = root / str(reference["path"])
    relative = Path(str(reference["path"]))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        _reject("provider reference is outside the allowed root")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            _reject("provider reference contains a filesystem link")
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        _reject("provider reference is unavailable inside the allowed root")
    content = resolved.read_bytes()
    if hashlib.sha256(content).hexdigest() != reference["sha256"]:
        _reject("provider reference bytes changed")
    return content


def _endpoint(profile: Mapping[str, object]) -> str:
    endpoint = profile["endpoint"]
    family = profile["protocol"]["family"]
    operation = endpoint["operation_path"]
    if family == "gemini-generate-content":
        operation = operation.replace("{model}", quote(profile["model"]["requested_id"], safe=""))
    url = endpoint["origin"] + endpoint["base_path"] + operation
    validate_https_endpoint(url, allow_query=False)
    return url


@dataclass(frozen=True, slots=True)
class ConfiguredProvider:
    profile: ProviderApiProfile
    resolved_config: Mapping[str, object]
    credential: CredentialProvider = field(repr=False)
    transport: HttpTransport = field(repr=False)
    _root: Path = field(repr=False)
    _binding_snapshot: Mapping[str, object] = field(init=False, repr=False)

    required_binding_modules: ClassVar[tuple[str, ...]] = tuple(
        f"research_workbench.adapters.models.{name}" for name in (
            "configured", "profile_configuration", "wire_codecs", "base", "http", "port", "provider_binding",
        )
    )

    def __post_init__(self) -> None:
        if type(self.profile) is not ProviderApiProfile:
            _reject("provider requires a validated API profile")
        profile = ProviderApiProfile.from_mapping(self.profile.to_mapping())
        config = _plain(self.resolved_config)
        if not isinstance(config, dict) or "model" not in config:
            _reject("provider requires a resolved v2 configuration")
        model = config.pop("model")
        config["model_selector"] = {"kind": "literal", "value": model}
        parsed = ProviderAdapterConfigV2.from_mapping(config)
        if not parsed.enabled:
            _reject("disabled provider configuration cannot execute")
        root = Path(self._root).resolve()
        if not root.is_dir():
            _reject("provider configuration root is unavailable")
        actual_profile, actual_config = resolve_profile_configuration(parsed, root=root)
        if actual_profile.to_mapping() != profile.to_mapping():
            _reject("provider profile differs from the pinned configuration")
        implementation = profile.document["implementation"]
        if model in _RETIRED_MODELS.get(profile.provider, frozenset()):
            raise ProviderError(ProviderErrorCategory.UNSUPPORTED, "profile model has been retired; a verified current profile is required")
        if implementation["adapter_version"] != ADAPTER_VERSION or implementation["codec_version"] != CODEC_VERSION:
            _reject("provider implementation version differs from the profile")
        supported = frozenset(Capability(item) for item in actual_config["capabilities"])
        validate_adapter_capabilities(supported, _IMPLEMENTED, profile.provider)
        if not supported <= profile.capabilities:
            _reject("provider configuration claims capabilities outside the profile")
        source = actual_config["credential_source"]
        if source["kind"] != "environment":
            _reject("provider credential source is not implemented")
        # Comparing only the controlled label does not probe presence or value.
        if self.credential.label != f"env:{source['name']}":
            _reject("provider credential reference differs from the configuration")
        options = actual_config["transport"]
        if type(getattr(self.transport, "max_response_bytes", None)) is not int or self.transport.max_response_bytes != options["max_response_bytes"]:
            _reject("provider transport differs from the configuration")
        object.__setattr__(self, "profile", profile)
        object.__setattr__(self, "resolved_config", _freeze(_plain(actual_config)))
        object.__setattr__(self, "_root", root)
        _endpoint(profile.document)
        from research_workbench.adapters.models.provider_binding import capture_configured_provider_binding
        object.__setattr__(self, "_binding_snapshot", capture_configured_provider_binding(self))

    @property
    def model(self) -> str:
        return self.resolved_config["model"]

    @property
    def timeout_seconds(self) -> float:
        return float(self.resolved_config["transport"]["timeout_seconds"])

    def capabilities(self) -> ProviderCapabilities:
        implementation = self.profile.document["implementation"]
        # Account retention/training and physical deployment are not inferred
        # from a brand, URL, advertised service, or a configuration reference.
        return ProviderCapabilities(
            provider=self.profile.provider,
            adapter_version=ADAPTER_VERSION,
            supported=frozenset(Capability(item) for item in self.resolved_config["capabilities"]),
            models=(self.model,),
            deployment="remote",
            regions=frozenset(),
            data_controls=frozenset(),
            limits=MappingProxyType(dict(implementation["limits"])),
            known_gaps=tuple(implementation["known_gaps"]),
        )

    def binding_descriptor(self) -> dict[str, object]:
        return {
            "adapter_class": _class_name(self),
            "adapter_version": ADAPTER_VERSION,
            "profile": self.profile.to_mapping(),
            "resolved_config": _plain(self.resolved_config),
            "credential_reference": _plain(self.resolved_config["credential_source"]),
            "transport_identity": {
                "class": _class_name(self.transport),
                "options": {"max_response_bytes": self.transport.max_response_bytes},
            },
        }

    def _assert_frozen_binding(self) -> None:
        from research_workbench.adapters.models.provider_binding import assert_configured_provider_binding
        assert_configured_provider_binding(self, self._binding_snapshot)
        # Construction independently parsed the pinned JSON/YAML profile. The
        # immutable actual profile is in the snapshot; its original bytes are
        # checked again without reinterpreting a file in a different dialect.
        _reference_bytes(self._root, self.resolved_config["profile_ref"])
        refs = [self.resolved_config["conformance_ref"], *self.profile.document["data_policy_evidence"].values()]
        for reference in refs:
            if reference is not None:
                _reference_bytes(self._root, reference)

    def generate(self, request: ModelRequest) -> ModelResponse:
        self._assert_frozen_binding()
        snapshot = self.capabilities()
        _preflight(request, snapshot)
        limits = snapshot.limits
        if request.max_output_tokens is None or type(request.max_output_tokens) is not int or request.max_output_tokens > limits["max_output_tokens"]:
            _reject("profile request requires an explicit bounded output token limit")
        if len(request.tools) > limits["max_tools"]:
            _reject("profile request exceeds the tool definition limit")
        payload = encode_profile_request(request, self.profile.document)
        auth = self.profile.document["auth"]
        headers = {"Content-Type": "application/json", **dict(auth["public_parameters"]),
                   auth["header_name"]: auth["prefix"] + "{API_KEY}"}
        response, document = perform_json_request(
            provider=self.profile.provider, transport=self.transport, credential=self.credential,
            url=_endpoint(self.profile.document), headers=headers, payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise_provider_http_error(provider=self.profile.provider, status_code=response.status_code,
                                      message="provider API request failed", provider_code=None)
        decoded = decode_profile_response(request, document, self.profile.document)
        if decoded.provider != self.profile.provider:
            raise ProviderError(ProviderErrorCategory.CONTRACT_VIOLATION, "observed provider identity differs from the profile")
        if decoded.model not in self.profile.document["model"]["allowed_observed_ids"]:
            raise ProviderError(ProviderErrorCategory.CONTRACT_VIOLATION, "observed model identity differs from the profile")
        return validate_response_contract(request, decoded)


def build_profile_provider(
    config: ProviderAdapterConfigV2,
    *,
    root: str | Path,
    model_environment: Mapping[str, str] | None = None,
    credential: CredentialProvider | None = None,
    transport: HttpTransport | None = None,
) -> ConfiguredProvider:
    if type(config) is not ProviderAdapterConfigV2 or not config.enabled:
        _reject("disabled or unvalidated provider configuration cannot execute")
    profile, resolved = resolve_profile_configuration(config, root=root, model_environment=model_environment)
    source = resolved["credential_source"]
    if source["kind"] != "environment":
        _reject("provider credential source is not implemented")
    return ConfiguredProvider(
        profile, resolved,
        credential if credential is not None else EnvironmentCredential(source["name"]),
        transport if transport is not None else UrllibTransport(max_response_bytes=resolved["transport"]["max_response_bytes"]),
        Path(root),
    )
