"""Non-secret provider adapter configuration and presence-only probing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from research_workbench.adapters.models.anthropic import AnthropicMessagesProvider
from research_workbench.adapters.models.base import _environment_name, _nonempty_string
from research_workbench.adapters.models.gemini import GeminiGenerateContentProvider
from research_workbench.adapters.models.openai import OpenAIResponsesProvider
from research_workbench.adapters.models.port import Capability
from research_workbench.io import load_document


# Adapter capabilities are single-sourced from the adapter classes. Adding a
# provider means registering its class here; conformance.py resolves live
# providers through this same registry.
PROVIDER_ADAPTERS = {
    adapter.provider_name: adapter
    for adapter in (
        OpenAIResponsesProvider,
        AnthropicMessagesProvider,
        GeminiGenerateContentProvider,
    )
}
SUPPORTED_PROVIDERS = frozenset(PROVIDER_ADAPTERS)
IMPLEMENTED_CAPABILITIES: dict[str, frozenset[Capability]] = {
    name: adapter.implemented_capabilities for name, adapter in PROVIDER_ADAPTERS.items()
}


@dataclass(frozen=True, slots=True)
class ProviderAdapterConfig:
    adapter_id: str
    provider: str
    enabled: bool
    base_url: str
    credential_env: str
    model_env: str
    capabilities: frozenset[Capability]
    live_conformance: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProviderAdapterConfig":
        required = {
            "adapter_id",
            "provider",
            "enabled",
            "base_url",
            "credential_env",
            "model_env",
            "capabilities",
            "live_conformance",
        }
        missing = sorted(required - set(value))
        unknown = sorted(set(value) - required)
        if missing:
            raise ValueError("provider adapter config lacks fields: " + ", ".join(missing))
        if unknown:
            raise ValueError("provider adapter config has unknown fields: " + ", ".join(unknown))
        adapter_id = _nonempty_string(value["adapter_id"], "adapter_id")
        provider = _nonempty_string(value["provider"], "provider")
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported provider adapter: {provider}")
        if not isinstance(value["enabled"], bool):
            raise ValueError(f"provider adapter {adapter_id!r} enabled must be boolean")
        base_url = _nonempty_string(value["base_url"], "base_url").rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError(f"provider adapter {adapter_id!r} base_url must be an HTTPS origin/path")
        credential_env = _environment_name(value["credential_env"], "credential_env")
        model_env = _environment_name(value["model_env"], "model_env")
        raw_capabilities = value["capabilities"]
        if not isinstance(raw_capabilities, list) or not raw_capabilities:
            raise ValueError(f"provider adapter {adapter_id!r} capabilities must be a non-empty array")
        try:
            capabilities = frozenset(Capability(item) for item in raw_capabilities)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"provider adapter {adapter_id!r} has an unknown capability") from exc
        if Capability.TEXT not in capabilities:
            raise ValueError(f"provider adapter {adapter_id!r} must include text capability")
        unimplemented = sorted(capabilities - IMPLEMENTED_CAPABILITIES[provider], key=str)
        if unimplemented:
            raise ValueError(
                f"provider adapter {adapter_id!r} claims unimplemented capabilities: "
                + ", ".join(str(item) for item in unimplemented)
            )
        live_conformance = _nonempty_string(value["live_conformance"], "live_conformance")
        if live_conformance not in {"pending", "passed", "failed"}:
            raise ValueError(
                f"provider adapter {adapter_id!r} live_conformance must be pending, passed, or failed"
            )
        return cls(
            adapter_id=adapter_id,
            provider=provider,
            enabled=value["enabled"],
            base_url=base_url,
            credential_env=credential_env,
            model_env=model_env,
            capabilities=capabilities,
            live_conformance=live_conformance,
        )

    def probe(self, *, check_environment: bool) -> dict[str, object]:
        if check_environment:
            credential_status = "present" if _present(self.credential_env) else "missing"
            model_status = "present" if _present(self.model_env) else "missing"
        else:
            credential_status = "unchecked"
            model_status = "unchecked"
        return {
            "adapter_id": self.adapter_id,
            "provider": self.provider,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "credential_source": f"env:{self.credential_env}",
            "credential_status": credential_status,
            "model_source": f"env:{self.model_env}",
            "model_status": model_status,
            "capabilities": sorted(str(item) for item in self.capabilities),
            "live_conformance": self.live_conformance,
        }


def load_provider_adapter_configs(path: str | Path) -> tuple[ProviderAdapterConfig, ...]:
    document = load_document(path)
    if not isinstance(document, Mapping) or document.get("registry_kind") != "provider_adapters":
        raise ValueError("provider adapter config must have registry_kind: provider_adapters")
    raw_adapters = document.get("adapters")
    if not isinstance(raw_adapters, list):
        raise ValueError("provider adapter config must contain an adapters array")
    adapters: list[ProviderAdapterConfig] = []
    seen: set[str] = set()
    for index, value in enumerate(raw_adapters):
        if not isinstance(value, Mapping):
            raise ValueError(f"provider adapter at index {index} must be an object")
        adapter = ProviderAdapterConfig.from_mapping(value)
        if adapter.adapter_id in seen:
            raise ValueError(f"duplicate provider adapter id: {adapter.adapter_id}")
        seen.add(adapter.adapter_id)
        adapters.append(adapter)
    return tuple(adapters)


def get_provider_adapter_config(path: str | Path, adapter_id: str) -> ProviderAdapterConfig:
    matches = [item for item in load_provider_adapter_configs(path) if item.adapter_id == adapter_id]
    if not matches:
        raise KeyError(f"unknown provider adapter: {adapter_id}")
    return matches[0]


def probe_provider_adapters(
    path: str | Path,
    *,
    check_environment: bool = False,
) -> dict[str, object]:
    adapters = load_provider_adapter_configs(path)
    return {
        "config": str(path),
        "environment_checked": check_environment,
        "note": (
            "presence-only check; credential and model values are never returned"
            if check_environment
            else "configuration-only check; no environment variables were read"
        ),
        "adapters": [adapter.probe(check_environment=check_environment) for adapter in adapters],
    }


def _present(name: str) -> bool:
    # This function is called only after an explicit --check-environment flag.
    # It intentionally collapses the value to a boolean at the boundary.
    return bool(os.environ.get(name))
