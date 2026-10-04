"""Private exact nonsecret request binding and trusted input-bound observation.

Reuse the configured profile resolver and wire encoder. The explicitly supplied
input verifier is trusted caller authority, not a byte/token heuristic, remote
billing proof, Task grant or authenticated deserialized permit.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path

from research_workbench.adapters.models.configured import _endpoint
from research_workbench.adapters.models.http import json_body
from research_workbench.adapters.models.port import (
    Capability, ContentBlock, DataPolicy, Message, ModelRequest, ResponseFormat, ToolChoice, ToolDefinition,
)
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2, resolve_profile_configuration
from research_workbench.adapters.models.reserved_transport import transport_fail
from research_workbench.adapters.models.wire_codecs import encode_profile_request


class RequestAdmissionError(ValueError):
    pass


def _fail():
    transport_fail(RequestAdmissionError, "request-admission-failed")


def _safe(operation):
    failed, result = False, None
    try:
        result = operation()
    except Exception:
        failed = True
    if failed:
        _fail()
    return result


def _plain(value):
    if type(value) in (ModelRequest, Message, ContentBlock, ToolDefinition, ToolChoice, ResponseFormat, DataPolicy):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if type(value) is Capability:
        return value.value
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            _fail()
        return {key: _plain(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_plain(item) for item in value]
    if type(value) is frozenset and all(type(item) is Capability for item in value):
        return sorted(item.value for item in value)
    _fail()


def _canonical(value):
    return json.dumps(_plain(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True, repr=False)
class ProviderInputMaterial:
    """Private current encoder input/body; headers and secrets are absent."""

    root: str
    body: bytes = field(repr=False)
    state: bytes = field(repr=False)
    url: str = field(repr=False)
    timeout_seconds: float
    output_upper_tokens: int


@dataclass(frozen=True, slots=True)
class VerifiedInputUpperBound:
    """Trusted verifier result for the exact material root, not a file permit."""

    material_root: str
    input_upper_tokens: int

    def __post_init__(self):
        if (type(self.material_root) is not str or re.fullmatch(r"[0-9a-f]{64}", self.material_root) is None
                or type(self.input_upper_tokens) is not int or self.input_upper_tokens <= 0):
            _fail()


def _material(config, root, request, environment, maximum):
    if (type(config) is not ProviderAdapterConfigV2 or not config.enabled or type(request) is not ModelRequest
            or type(maximum) is not int or maximum <= 0 or type(request.max_output_tokens) is not int
            or request.max_output_tokens <= 0):
        _fail()
    profile, resolved = resolve_profile_configuration(config, root=root, model_environment=environment)
    if request.model != resolved["model"] or request.max_output_tokens > profile.document["implementation"]["limits"]["max_output_tokens"]:
        _fail()
    body = json_body(encode_profile_request(request, profile.document))
    if len(body) > maximum:
        _fail()
    url = _endpoint(profile.document)
    state = _canonical({"config": config.to_mapping(), "profile": profile.to_mapping(), "resolved": resolved,
                        "request": request, "url": url, "body_sha256": hashlib.sha256(body).hexdigest(),
                        "max_body_bytes": maximum})
    digest = hashlib.sha256(b"provider-input-material-v1\x00" + state).hexdigest()
    return ProviderInputMaterial(digest, body, state, url, resolved["transport"]["timeout_seconds"], request.max_output_tokens)


@dataclass(frozen=True, slots=True, repr=False)
class PreparedProviderRequest:
    config: ProviderAdapterConfigV2 = field(repr=False)
    root: Path = field(repr=False)
    request: ModelRequest = field(repr=False)
    environment: Mapping | None = field(repr=False)
    max_body_bytes: int
    material: ProviderInputMaterial = field(repr=False)
    bound: VerifiedInputUpperBound
    verifier: object = field(repr=False)

    def verify_material(self):
        """Recompute current local inputs without invoking an external port."""
        def check():
            if _material(self.config, self.root, self.request, self.environment, self.max_body_bytes) != self.material:
                _fail()
        return _safe(check)

    def verify(self, verifier):
        def check():
            if verifier is not self.verifier or not callable(verifier):
                _fail()
            self.verify_material()
            current = self.material
            observed = verifier(current)
            if type(observed) is not VerifiedInputUpperBound or observed != self.bound or observed.material_root != current.root:
                _fail()
            # The verifier may be slow or mutate local inputs. Recompute after
            # it returns before any caller crosses the next boundary.
            self.verify_material()
        return _safe(check)


def prepare_provider_request(config, *, root, request, input_upper_verifier, max_body_bytes, model_environment=None):
    """Freeze one current request via existing resolver/encoder, without a Key."""
    def prepare():
        if not callable(input_upper_verifier):
            _fail()
        material = _material(config, Path(root), request, model_environment, max_body_bytes)
        bound = input_upper_verifier(material)
        if type(bound) is not VerifiedInputUpperBound or bound.material_root != material.root:
            _fail()
        result = PreparedProviderRequest(config, Path(root), request, model_environment, max_body_bytes, material, bound, input_upper_verifier)
        result.verify(input_upper_verifier)
        return result
    return _safe(prepare)
