"""Provider-neutral model API port.

The port normalizes only stable control-plane concepts. Provider-specific
features remain visible through capability negotiation and namespaced
extensions; adapters must not silently emulate unsupported features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable


class Capability(StrEnum):
    TEXT = "text"
    TOOLS = "tools"
    PARALLEL_TOOLS = "parallel_tools"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"
    REASONING = "reasoning"
    IMAGES = "images"
    FILES = "files"
    SERVER_TOOLS = "server_tools"
    PROMPT_CACHING = "prompt_caching"
    PROVIDER_STATE = "provider_state"


class FinishReason(StrEnum):
    COMPLETE = "complete"
    TOOL_CALL = "tool_call"
    LENGTH = "length"
    STOP = "stop"
    REFUSAL = "refusal"
    PAUSED = "paused"
    CONTEXT_LIMIT = "context_limit"
    ERROR = "error"
    UNKNOWN = "unknown"


class ProviderErrorCategory(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED = "unsupported"
    RATE_LIMIT = "rate_limit"
    TRANSIENT = "transient"
    SAFETY_REFUSAL = "safety_refusal"
    CONTEXT_LIMIT = "context_limit"
    CANCELLED = "cancelled"
    CONTRACT_VIOLATION = "contract_violation"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ContentBlock:
    kind: str
    text: str | None = None
    data: Mapping[str, Any] | None = None
    mime_type: str | None = None
    reference: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: tuple[ContentBlock, ...]
    name: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    strict: bool = True


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    name: str
    arguments: Mapping[str, Any]
    executed_by: str = "client"


@dataclass(frozen=True, slots=True)
class ResponseFormat:
    kind: str = "text"
    name: str | None = None
    schema: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class DataPolicy:
    local_only: bool = False
    zero_data_retention_required: bool = False
    training_opt_out_required: bool = False
    allowed_regions: tuple[str, ...] = ()
    allow_provider_server_tools: bool = False


@dataclass(frozen=True, slots=True)
class ModelRequest:
    model: str
    messages: tuple[Message, ...]
    tools: tuple[ToolDefinition, ...] = ()
    response_format: ResponseFormat = field(default_factory=ResponseFormat)
    max_output_tokens: int | None = None
    temperature: float | None = None
    reasoning_effort: str | None = None
    capability_requirements: frozenset[Capability] = frozenset()
    data_policy: DataPolicy = field(default_factory=DataPolicy)
    metadata: Mapping[str, str] = field(default_factory=dict)
    extensions: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    provider_reported_cost: float | None = None
    currency: str | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class ModelResponse:
    response_id: str
    provider: str
    model: str
    output: tuple[ContentBlock, ...]
    finish_reason: FinishReason
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)
    warnings: tuple[str, ...] = ()
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider: str
    adapter_version: str
    supported: frozenset[Capability]
    models: tuple[str, ...] = ()
    deployment: str = "remote"
    regions: frozenset[str] = frozenset()
    limits: Mapping[str, int | float | str] = field(default_factory=dict)
    data_controls: frozenset[str] = frozenset()
    known_gaps: tuple[str, ...] = ()

    def supports_model(self, model: str) -> bool:
        return not self.models or model in self.models

    def gaps_for(self, request: ModelRequest) -> tuple[Capability, ...]:
        return tuple(
            capability
            for capability in sorted(required_capabilities(request), key=str)
            if capability not in self.supported
        )

    def data_policy_gaps_for(self, policy: DataPolicy) -> tuple[str, ...]:
        gaps: list[str] = []
        if policy.local_only and self.deployment != "local":
            gaps.append("local_execution")
        if policy.zero_data_retention_required and "zero_data_retention" not in self.data_controls:
            gaps.append("zero_data_retention")
        if policy.training_opt_out_required and "training_opt_out" not in self.data_controls:
            gaps.append("training_opt_out")
        if policy.allowed_regions and not (set(policy.allowed_regions) & set(self.regions)):
            gaps.append("allowed_region")
        return tuple(gaps)


class CapabilityGap(ValueError):
    def __init__(self, provider: str, gaps: Iterable[Capability]):
        self.provider = provider
        self.gaps = tuple(gaps)
        rendered = ", ".join(str(gap) for gap in self.gaps)
        super().__init__(f"provider {provider!r} lacks required capabilities: {rendered}")


class ModelNotSupported(ValueError):
    def __init__(self, provider: str, model: str, configured_models: Iterable[str]):
        self.provider = provider
        self.model = model
        self.configured_models = tuple(configured_models)
        rendered = ", ".join(self.configured_models) or "none"
        super().__init__(f"provider {provider!r} is not configured for model {model!r}; configured: {rendered}")


class DataPolicyGap(ValueError):
    def __init__(self, provider: str, gaps: Iterable[str]):
        self.provider = provider
        self.gaps = tuple(gaps)
        rendered = ", ".join(self.gaps)
        super().__init__(f"provider {provider!r} does not satisfy data policy: {rendered}")


class ProviderError(RuntimeError):
    def __init__(
        self,
        category: ProviderErrorCategory,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        provider_code: str | None = None,
    ):
        self.category = category
        self.retryable = retryable
        self.status_code = status_code
        self.provider_code = provider_code
        super().__init__(message)


def required_capabilities(request: ModelRequest) -> frozenset[Capability]:
    required = {Capability.TEXT, *request.capability_requirements}
    if request.tools:
        required.add(Capability.TOOLS)
    if request.response_format.kind == "json_schema":
        required.add(Capability.STRUCTURED_OUTPUT)
    if request.reasoning_effort is not None:
        required.add(Capability.REASONING)
    for message in request.messages:
        for block in message.content:
            if block.kind == "image":
                required.add(Capability.IMAGES)
            elif block.kind == "file":
                required.add(Capability.FILES)
            elif block.kind in {"tool_call", "tool_result"}:
                required.add(Capability.TOOLS)
    return frozenset(required)


@runtime_checkable
class ModelProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities:
        """Return an auditable snapshot for this adapter configuration."""

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Execute one bounded request or raise a normalized ProviderError."""


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, name: str, provider: ModelProvider) -> None:
        if name in self._providers:
            raise ValueError(f"provider already registered: {name}")
        self._providers[name] = provider

    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"unknown provider: {name}") from exc

    def require(self, name: str, request: ModelRequest) -> ModelProvider:
        provider = self.get(name)
        snapshot = provider.capabilities()
        if not snapshot.supports_model(request.model):
            raise ModelNotSupported(name, request.model, snapshot.models)
        gaps = snapshot.gaps_for(request)
        if gaps:
            raise CapabilityGap(name, gaps)
        policy_gaps = snapshot.data_policy_gaps_for(request.data_policy)
        if policy_gaps:
            raise DataPolicyGap(name, policy_gaps)
        return provider

    def snapshots(self) -> tuple[ProviderCapabilities, ...]:
        return tuple(provider.capabilities() for provider in self._providers.values())
