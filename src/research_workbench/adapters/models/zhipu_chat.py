"""Conservative Zhipu standard Chat Completions API adapter.

The adapter intentionally implements only one-shot text and ``json_object``
responses.  It does not claim client tools, strict provider-side JSON Schema,
or reasoning handback.  Provider-returned reasoning content is never copied
into the normalized response.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from research_workbench.adapters.models.base import (
    perform_json_request,
    preflight,
    provider_extension,
    raise_provider_http_error,
    reject_unknown_extension_keys,
    require_list,
    require_object,
    validate_adapter_capabilities,
    validate_response_contract,
)
from research_workbench.adapters.models.http import (
    CredentialProvider,
    HttpTransport,
    UrllibTransport,
)
from research_workbench.adapters.models.port import (
    Capability,
    ContentBlock,
    FinishReason,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    Usage,
)

ZHIPU_STANDARD_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
ZHIPU_MAX_OUTPUT_TOKENS = 131_072
ZHIPU_MAX_SCHEMA_INSTRUCTION_BYTES = 16_384


class ZhipuChatCompletionsProvider:
    """One model-bound adapter for Zhipu's standard Chat Completions API."""

    provider_name = "zhipu"
    adapter_version = "0.1.0"
    implemented_capabilities = frozenset(
        {Capability.TEXT, Capability.STRUCTURED_OUTPUT}
    )

    def __init__(
        self,
        *,
        model: str,
        credential: CredentialProvider,
        transport: HttpTransport | None = None,
        supported: frozenset[Capability] = frozenset({Capability.TEXT}),
        base_url: str = ZHIPU_STANDARD_BASE_URL,
        timeout_seconds: float = 60.0,
        max_retries: int = 0,
        regions: frozenset[str] = frozenset(),
        data_controls: frozenset[str] = frozenset(),
    ) -> None:
        if not model.strip():
            raise ValueError("Zhipu model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(max_retries, bool) or max_retries != 0:
            raise ValueError("Zhipu adapter requires max_retries=0")
        normalized_base_url = base_url.rstrip("/")
        if normalized_base_url != ZHIPU_STANDARD_BASE_URL:
            raise ValueError(
                "Zhipu adapter accepts only the standard API base URL; "
                "Coding Plan and compatible third-party endpoints are not interchangeable"
            )
        validate_adapter_capabilities(
            supported,
            self.implemented_capabilities,
            self.provider_name,
        )
        self.model = model
        self.credential = credential
        self.transport = transport or UrllibTransport()
        self.supported = supported
        self.base_url = normalized_base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.regions = regions
        self.data_controls = data_controls

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.provider_name,
            adapter_version=self.adapter_version,
            supported=self.supported,
            models=(self.model,),
            deployment="remote",
            regions=self.regions,
            limits={"max_retries": self.max_retries},
            data_controls=self.data_controls,
            known_gaps=(
                "client tools, streaming, images, files, and server tools are not implemented",
                "json_schema requests use provider json_object mode and local JSON Schema validation",
                "reasoning controls and multi-turn reasoning handback are not implemented",
                "provider-reported currency cost is unavailable",
                "capability availability remains model/account specific and requires live conformance",
            ),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        preflight(request, self.capabilities())
        self._validate_sampling_controls(request)
        extension = provider_extension(request, self.provider_name)
        reject_unknown_extension_keys(
            extension,
            provider=self.provider_name,
            allowed=frozenset(),
        )
        payload = self._payload(request)
        http_response, document = perform_json_request(
            provider=self.provider_name,
            transport=self.transport,
            credential=self.credential,
            url=f"{self.base_url}/chat/completions",
            headers={
                "Authorization": "Bearer {API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "research-agent-workbench/0.1",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        if http_response.status_code >= 400:
            self._raise_api_error(http_response.status_code, document)
        response = self._parse_response(request, document)
        return validate_response_contract(request, response)

    def _payload(self, request: ModelRequest) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model,
            "messages": self._messages(request),
            "stream": False,
        }
        if request.response_format.kind == "json_schema":
            # The standard Chat API exposes json_object, not strict
            # provider-side JSON Schema.  The shared response validator checks
            # the requested schema locally before the result can be consumed.
            payload["response_format"] = {"type": "json_object"}
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        return payload

    def _messages(self, request: ModelRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.response_format.kind == "json_schema":
            assert isinstance(request.response_format.schema, Mapping)
            schema = json.dumps(
                request.response_format.schema,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            instruction = (
                "Return exactly one JSON object and no surrounding prose. "
                "The object must validate against this JSON Schema: "
                f"{schema}"
            )
            if len(instruction.encode("utf-8")) > ZHIPU_MAX_SCHEMA_INSTRUCTION_BYTES:
                raise ProviderError(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Zhipu structured-output schema instruction exceeds the bounded size",
                )
            messages.append({"role": "system", "content": instruction})
        for message in request.messages:
            if message.role not in {"system", "user", "assistant"}:
                raise ProviderError(
                    ProviderErrorCategory.UNSUPPORTED,
                    f"Zhipu adapter cannot serialize message role: {message.role}",
                )
            if message.name is not None:
                raise ProviderError(
                    ProviderErrorCategory.UNSUPPORTED,
                    "Zhipu message names are not implemented by this adapter",
                )
            parts: list[str] = []
            for block in message.content:
                if block.kind != "text":
                    raise ProviderError(
                        ProviderErrorCategory.UNSUPPORTED,
                        f"Zhipu adapter cannot serialize content block: {block.kind}",
                    )
                parts.append(block.text or "")
            messages.append({"role": message.role, "content": "\n".join(parts)})
        return messages

    def _parse_response(
        self,
        request: ModelRequest,
        document: Mapping[str, object],
    ) -> ModelResponse:
        response_id = document.get("id")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response lacks a non-empty id",
            )
        model = document.get("model")
        if not isinstance(model, str) or not model:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response lacks a non-empty model",
            )
        if model != request.model:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"Zhipu returned model {model!r} for exact request {request.model!r}",
            )

        choices = require_list(
            document.get("choices"),
            provider=self.provider_name,
            field="choices",
        )
        if len(choices) != 1:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response must contain exactly one choice",
            )
        choice = require_object(
            choices[0],
            provider=self.provider_name,
            field="choices[0]",
        )
        message = require_object(
            choice.get("message"),
            provider=self.provider_name,
            field="choices[0].message",
        )
        content = message.get("content")
        if not isinstance(content, str):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response message content must be text",
            )
        if message.get("tool_calls"):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu returned tool calls through an adapter that does not support tools",
            )

        raw_finish = choice.get("finish_reason")
        if raw_finish == "tool_calls":
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu reported a tool-call finish through an adapter that does not support tools",
            )
        finish_reason = _FINISH_REASONS.get(raw_finish, FinishReason.UNKNOWN)

        warnings: list[str] = []
        if request.metadata:
            warnings.append(
                "Canonical request metadata remained local and was not transmitted to Zhipu"
            )
        if message.get("reasoning_content") is not None:
            warnings.append(
                "Zhipu reasoning content was omitted; reasoning handback is not implemented"
            )
        if request.response_format.kind == "json_schema":
            warnings.append(
                "Zhipu enforced json_object only; requested JSON Schema was validated locally"
            )
        usage, reported_total = self._usage(document.get("usage"))
        metadata: dict[str, Any] = {"finish_reason": raw_finish}
        if isinstance(document.get("created"), int) and not isinstance(
            document.get("created"), bool
        ):
            metadata["created"] = document["created"]
        if reported_total is not None:
            metadata["reported_total_tokens"] = reported_total
        output = (
            ()
            if finish_reason == FinishReason.REFUSAL
            else (ContentBlock(kind="text", text=content),)
        )
        return ModelResponse(
            response_id=response_id,
            provider=self.provider_name,
            model=model,
            output=output,
            finish_reason=finish_reason,
            usage=usage,
            warnings=tuple(warnings),
            provider_metadata=metadata,
        )

    def _usage(self, value: object) -> tuple[Usage, int | None]:
        if value is None:
            return Usage(provider_reported_cost=None), None
        usage = require_object(value, provider=self.provider_name, field="usage")
        input_tokens = self._usage_integer(usage, "prompt_tokens")
        output_tokens = self._usage_integer(usage, "completion_tokens")
        total_tokens = self._usage_integer(usage, "total_tokens")
        details_value = usage.get("prompt_tokens_details")
        cached_tokens = None
        if details_value is not None:
            details = require_object(
                details_value,
                provider=self.provider_name,
                field="usage.prompt_tokens_details",
            )
            cached_tokens = self._usage_integer(
                details,
                "cached_tokens",
                path="usage.prompt_tokens_details.cached_tokens",
            )
        if (
            total_tokens is not None
            and input_tokens is not None
            and output_tokens is not None
            and total_tokens != input_tokens + output_tokens
        ):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu usage.total_tokens does not equal prompt_tokens plus completion_tokens",
            )
        return (
            Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_input_tokens=cached_tokens,
                provider_reported_cost=None,
                currency=None,
            ),
            total_tokens,
        )

    def _usage_integer(
        self,
        value: Mapping[str, Any],
        field: str,
        *,
        path: str | None = None,
    ) -> int | None:
        raw = value.get(field)
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"Zhipu response field {path or f'usage.{field}'} must be a non-negative integer",
            )
        return raw

    def _validate_sampling_controls(self, request: ModelRequest) -> None:
        output_tokens = request.max_output_tokens
        if output_tokens is not None and (
            isinstance(output_tokens, bool)
            or not isinstance(output_tokens, int)
            or not 1 <= output_tokens <= ZHIPU_MAX_OUTPUT_TOKENS
        ):
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                f"Zhipu max_output_tokens must be an integer between 1 and {ZHIPU_MAX_OUTPUT_TOKENS}",
            )
        temperature = request.temperature
        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(float(temperature))
            or not 0 <= temperature <= 1
            or round(float(temperature), 2) != float(temperature)
        ):
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "Zhipu temperature must be between 0 and 1 with at most two decimal places",
            )

    def _raise_api_error(
        self,
        status_code: int,
        document: Mapping[str, object],
    ) -> None:
        raw_error = document.get("error")
        error = raw_error if isinstance(raw_error, Mapping) else document
        raw_message = error.get("message") or error.get("msg")
        message = raw_message if isinstance(raw_message, str) else f"HTTP {status_code}"
        raw_code = error.get("code")
        provider_code = str(raw_code) if raw_code is not None else None
        override = None
        if provider_code in {"1000", "1001", "1002", "1003", "1004"}:
            override = ProviderErrorCategory.AUTHENTICATION
        elif provider_code in {
            "1110",
            "1111",
            "1112",
            "1113",
            "1121",
            "1220",
            "1309",
            "1311",
        }:
            override = ProviderErrorCategory.PERMISSION
        elif provider_code in {"1211", "1212", "1221", "1222"}:
            override = ProviderErrorCategory.UNSUPPORTED
        elif provider_code in {"1261", "context_length_exceeded", "max_tokens"}:
            override = ProviderErrorCategory.CONTEXT_LIMIT
        elif provider_code in {"1300", "1301", "content_filter", "safety"}:
            override = ProviderErrorCategory.SAFETY_REFUSAL
        elif provider_code == "1302":
            override = ProviderErrorCategory.RATE_LIMIT
        elif provider_code in {"1120", "1234", "500", "1305"}:
            override = ProviderErrorCategory.TRANSIENT
        elif provider_code in {"1304", "1308", "1310"}:
            raise ProviderError(
                ProviderErrorCategory.RATE_LIMIT,
                f"{self.provider_name} API request failed: {message}",
                retryable=False,
                status_code=status_code,
                provider_code=provider_code,
            )
        raise_provider_http_error(
            provider=self.provider_name,
            status_code=status_code,
            message=message,
            provider_code=provider_code,
            category_override=override,
        )


_FINISH_REASONS: dict[object, FinishReason] = {
    "stop": FinishReason.COMPLETE,
    "length": FinishReason.LENGTH,
    "content_filter": FinishReason.REFUSAL,
    "sensitive": FinishReason.REFUSAL,
    "network_error": FinishReason.ERROR,
    "model_context_window_exceeded": FinishReason.CONTEXT_LIMIT,
}
